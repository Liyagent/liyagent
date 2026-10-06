"""`tiq` — the command line for TicketIQ.

The console is where an operator looks; this is where they automate. Every
subcommand is a thin call to the same REST API the console uses, so there is
no second implementation of anything and nothing here can drift into being the
only way to do something.

Two deliberate choices:

* **A session, not the API key.** These are console-plane endpoints behind
  per-permission checks; the instance API key is deliberately scoped to the
  agent surface. Widening that key so a CLI could use it would enlarge the
  blast radius of a credential that already has no scopes — so the CLI signs
  in the way a person does and gets exactly the permissions of the account it
  used. Credentials come from TICKETIQ_CLI_USER / TICKETIQ_CLI_PASSWORD, and
  nothing is written to disk.
* **`--json` on everything.** The human-readable tables are for reading; the
  JSON is for piping. A tool whose output only a person can parse gets screen
  scraped, and then its formatting becomes an API nobody documented.

One command is the exception to "a thin call to the API": ``audit verify``
never talks to a server at all. An evidence bundle is only worth something if
it can be checked by someone who does not trust the instance that issued it,
so the verifier reads the zip and nothing else — no sign-in, no network.

    tiq agents                       # what exists, and what each runs on
    tiq ask copilot "why is X down"  # run one agent, print the reply
    tiq usage --days 30              # spend and tokens
    tiq policies                     # who may do what
    tiq policy get NAME              # one policy; --fields trims it
    tiq trigger fire <token> "..."   # exercise an inbound endpoint
    tiq audit verify bundle.zip      # check an audit evidence bundle, offline
    tiq eval run --dataset D --fail-on-regression   # the CI gate: exit 1 on a regression

Lifecycle verbs, for a pipeline (exit 0 nothing pending, 2 pending or
invalid, 1 error — see "lifecycle verbs" below):

    tiq export copilot -o copilot.json   # an agent as a bundle file
    tiq plan -f copilot.json             # what apply would change (0 / 2 / 1)
    tiq apply -f copilot.json            # make it so; --dry-run is plan
    tiq delete -f copilot.json           # delete the agents a file names
    tiq agent create --from-blueprint B NAME | start | stop | delete NAME
    tiq policy validate p.cedar          # exit 2 when the policy is invalid
    tiq trigger pause | resume NAME
    tiq replay --candidate C --fail-on-regression

In CI, TICKETIQ_TOKEN=svc/<name>:<secret> signs in as a governance service
account (Access → Service accounts) — no person's password, and it works
where SSO is enforced. examples/ci/ticketiq.yml is a GitHub Actions workflow.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from typing import Any
from urllib.parse import quote

DEFAULT_URL = "http://127.0.0.1:8787"


class CliError(RuntimeError):
    """A failure worth printing plainly and exiting non-zero for.

    `code` is the kind of failure, for `liya`'s exit status (commands.EXIT_*):
    1 anything else, 2 a request the server (or the CLI) found invalid, 3 a
    credential refused or a permission missing, 4 a thing that does not
    exist. A script tells "fix the input" from "fix the token" from "it is
    gone" without parsing the message. `tiq` keeps exiting 1 for all of
    them, as it always has."""

    def __init__(self, message: str = "", code: int = 1):
        super().__init__(message)
        self.code = code


def _http(args) -> Any:
    """The HTTP client every command talks through. One seam, so a test can
    hand the CLI an in-process app instead of a socket."""
    import httpx
    return httpx.Client(base_url=args.url.rstrip("/"), timeout=args.timeout)


def _token(args) -> str:
    """The service-account credential, if this run uses one: --token, else
    TICKETIQ_TOKEN — unless --user was given, which says a person is at the
    keyboard and means it."""
    if args.token:
        return args.token
    if args.user:
        return ""
    return os.environ.get("TICKETIQ_TOKEN", "")


def _bearer(client, token: str) -> str:
    """A bearer for `token`. A service account's client credentials —
    ``svc/<name>:<secret>``, the one value a CI secret store holds — are
    exchanged for a one-hour session (POST /api/service-accounts/token); any
    other value is taken to be such a session already (one a previous step
    minted), and used as it is."""
    client_id, sep, secret = token.partition(":")
    if not (sep and client_id.startswith("svc/")):
        return token
    r = client.post("/api/service-accounts/token", json={
        "grant_type": "client_credentials", "client_id": client_id,
        "client_secret": secret})
    if r.status_code != 200:
        # The server says invalid_client for every cause on purpose; the
        # likely ones are named here, where only the credential's holder reads it.
        raise CliError(f"the service account {client_id!r} was refused ({r.status_code}) "
                       "— a wrong or expired secret, a deleted service account, or its "
                       "account disabled, given a password or made an owner", code=3)
    return r.json()["access_token"]


def _client(args) -> Any:
    """A signed-in client, or a clear refusal.

    The session is held in memory for the life of the command and never
    persisted — a CLI that caches a cookie in the home directory is a
    credential nobody remembers to revoke.

    Two ways in. A person: TICKETIQ_CLI_USER / TICKETIQ_CLI_PASSWORD, signed
    in as the console signs in. A pipeline: TICKETIQ_TOKEN, a governance
    service account's credential (svcaccounts.py) — scoped to the role of
    the account it is bound to, and working on an instance where SSO is
    enforced and no password would be accepted.
    """
    token = _token(args)
    client = _http(args)
    if token:
        try:
            client.headers["Authorization"] = f"Bearer {_bearer(client, token)}"
        except BaseException:
            client.close()
            raise
        return client
    user = args.user or os.environ.get("TICKETIQ_CLI_USER", "")
    password = args.password or os.environ.get("TICKETIQ_CLI_PASSWORD", "")
    if not (user and password):
        client.close()
        raise CliError(
            "no credentials — set TICKETIQ_CLI_USER and TICKETIQ_CLI_PASSWORD, "
            "or pass --user/--password; in CI, set TICKETIQ_TOKEN to a service "
            "account's svc/<name>:<secret>. The instance API key is not accepted "
            "here: it is scoped to the agent surface, and these commands read "
            "the governance plane.")
    r = client.post("/api/login", json={"username": user, "password": password})
    if r.status_code != 200:
        client.close()
        raise CliError(f"sign-in failed for {user!r} ({r.status_code})")
    # The session rides as a bearer as well as the cookie: a client whose
    # base URL is not the cookie's host (a test app, a proxy) still sends it.
    token = (r.json() or {}).get("token", "")
    if token:
        client.headers["Authorization"] = f"Bearer {token}"
    return client


@contextlib.contextmanager
def _session(args):
    """Sign in, hand over the client, always close it.

    httpx refuses to re-enter a client that has already issued a request, and
    _client signs in before returning — so callers get this wrapper rather
    than `with _client(...)`, which raised "Cannot open a client instance more
    than once" on every command.
    """
    client = _client(args)
    try:
        yield client
    finally:
        client.close()


def _get(client, path: str, params: dict[str, Any] | None = None) -> Any:
    # An unset option is left off rather than sent empty. And params go only
    # when something is left: httpx replaces a path's own query string with
    # any params mapping, an empty one included, so a `?days=30` written into
    # the path reached the server as no window at all.
    q = {k: v for k, v in (params or {}).items() if v not in (None, "")}
    r = client.get(path, params=q or None)
    return _checked(r, path)


def _refused(r, path: str) -> None:
    """401 and 403 said apart: an expired or revoked token is fixed by a new
    one, a missing permission by a different role — and a pipeline log that
    called both "lacks the permission" sent people to the wrong place."""
    if r.status_code == 401:
        raise CliError(f"{path}: not signed in — the session or token was refused "
                       "(expired, or its service account deleted?)", code=3)
    if r.status_code == 403:
        why = _detail(r)
        raise CliError(f"{path}: this account lacks the permission for it"
                       + (f" ({why})" if why else ""), code=3)


def _detail(r) -> str:
    """The server's reason. A bundle's refusal is {message, at} — where in
    the file it was — and both halves are the point, so neither is dropped."""
    try:
        detail = r.json().get("detail", "")
    except Exception:
        return r.text[:200]
    if isinstance(detail, dict):
        msg = str(detail.get("message") or json.dumps(detail, sort_keys=True))
        return msg + (f" (at {detail['at']})" if detail.get("at") else "")
    return str(detail)


def _checked(r, path: str) -> Any:
    _refused(r, path)
    if r.status_code >= 400:
        # The server's reason: a refused filter names the field and the
        # character it stopped at, which a bare status hides.
        raise CliError(f"{path} failed ({r.status_code}): {_detail(r)}",
                       code=_status_code(r.status_code))
    return r.json()


def _status_code(status: int) -> int:
    """The CliError code an HTTP failure is: 404 not found (4), a request
    the server refused as malformed or invalid (400, 422: 2), else 1."""
    return 4 if status == 404 else 2 if status in (400, 422) else 1


def _post(client, path: str, body: dict) -> Any:
    r = client.post(path, json=body)
    return _checked(r, path)


def _emit(args, payload: Any, table: list[tuple[str, ...]] | None = None) -> None:
    """JSON when asked, otherwise the table. Never both — a stream that is
    sometimes JSON and sometimes prose cannot be piped."""
    if args.json or table is None:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return
    if not table:
        print("(nothing to show)")
        return
    widths = [max(len(str(row[i])) for row in table) for i in range(len(table[0]))]
    for i, row in enumerate(table):
        print("  ".join(str(cell).ljust(w) for cell, w in zip(row, widths)).rstrip())
        if i == 0:
            print("  ".join("-" * w for w in widths))


# ---- commands ----

def cmd_agents(args) -> int:
    with _session(args) as c:
        data = _get(c, "/api/agents")
    rows: list[tuple[str, ...]] = [("AGENT", "STAGE", "MODEL-DRIVEN", "PROVIDER", "MODEL")]
    for a in data.get("agents", []):
        eff = a.get("effective") or {}
        rows.append((a["key"], a.get("stage", "-"),
                     "yes" if a.get("llm") else "no",
                     eff.get("provider") or ("global" if a.get("llm") else "-"),
                     eff.get("model") or "-"))
    _emit(args, data, rows)
    return 0


def cmd_ask(args) -> int:
    """Run one agent through the governed path and print what it said."""
    with _session(args) as c:
        out = _post(c, f"/api/agents/{args.agent}/playground",
                    {"message": args.message})
    if args.json:
        _emit(args, out)
        return 0
    if out.get("skipped"):
        # Non-zero: a refusal is a failure for a script, even though the HTTP
        # call succeeded. Silently printing an apology and exiting 0 would make
        # a capped agent look like a working one in a pipeline.
        print(f"no reply — {out['skipped']}", file=sys.stderr)
        return 2
    print(out.get("reply", ""))
    return 0


def cmd_usage(args) -> int:
    with _session(args) as c:
        data = _get(c, "/api/usage", {"days": args.days})
    t = data.get("totals", {})
    rows = [("METRIC", "VALUE"),
            ("calls", t.get("calls", 0)), ("errors", t.get("errors", 0)),
            ("input", t.get("input", 0)), ("output", t.get("output", 0)),
            ("cost_usd", f"{t.get('cost_usd', 0):.4f}")]
    for agent, cell in (data.get("by_agent") or {}).items():
        rows.append((f"agent:{agent}", cell.get("calls", 0)))
    _emit(args, data, rows)
    return 0


# `policies system` and `policies action-groups`: the RBAC projection's two
# lists (ADP's ListSystemPolicies / ListActionGroups), under the names the
# server reserves for them (_SHADOWED_POLICY_NAMES) — the key each answers
# its rows under, and the columns a row is shown as.
_SYSTEM_LISTS = {
    "system": ("system_policies", ("PRINCIPAL", "ROLE", "ENABLED", "NAME"),
               lambda r: (r["principal"], r["role"], "yes" if r.get("enabled", True) else "no",
                          r["name"])),
    "action-groups": ("action_groups", ("GROUP", "MEMBERS", "BINDINGS", "BUILTIN"),
                      lambda r: (r["name"], len(r.get("member_actions") or []),
                                 r.get("bindings", 0), "yes" if r.get("builtin") else "no")),
}


def cmd_system_policies(args) -> int:
    """The role bindings as system policies, or the roles as action groups:
    filtered and paged on the server, by name (their only order)."""
    if args.order_by:
        raise CliError(f"policies {args.which} is ordered by name only; drop --order-by")
    key, head, cells = _SYSTEM_LISTS[args.which]
    with _session(args) as c:
        data = _get(c, f"/api/policies/{args.which}", {
            "filter": args.filter, "page_size": args.page_size, "page_token": args.page_token})
    rows: list[tuple[str, ...]] = [head] + [cells(r) for r in data.get(key, [])]
    _emit(args, data, rows)
    if data.get("next_page_token") and not args.json:
        print(f"{len(data[key])} of {data.get('total_size', '?')} shown; next page: "
              f"--page-token {data['next_page_token']}", file=sys.stderr)
    return 0


def cmd_policies(args) -> int:
    """The policy list, narrowed and ordered on the server. With no option it
    is the whole list by name, as it always was."""
    if getattr(args, "which", None):
        return cmd_system_policies(args)
    with _session(args) as c:
        data = _get(c, "/api/policies", {
            "filter": args.filter, "order_by": args.order_by,
            "page_size": args.page_size, "page_token": args.page_token})
    rows: list[tuple[str, ...]] = [("POLICY", "ENABLED", "ABOUT")]
    for p in data.get("policies", []):
        rows.append((p["name"], "yes" if p.get("enabled", True) else "no",
                     (p.get("about") or "")[:48]))
    if not data.get("engine", True):
        print("warning: the Cedar engine is not installed; governed resources "
              "will be denied", file=sys.stderr)
    _emit(args, data, rows)
    if data.get("next_page_token") and not args.json:
        # On stderr, so the table on stdout stays only the table; --json
        # carries the token in the payload.
        print(f"{len(data['policies'])} of {data.get('total_size', '?')} shown; next page: "
              f"--page-token {data['next_page_token']}", file=sys.stderr)
    return 0


# GET /api/policies/system, /action-groups and /effective are reads of their
# own, so a policy with one of those names (stored before they were reserved)
# is not reachable at /api/policies/{name}; the list, filtered to that exact
# name, returns the same row.
_SHADOWED_POLICY_NAMES = ("system", "effective", "action-groups")


def cmd_policy_get(args) -> int:
    """One policy: every field, or those --fields names (the name always)."""
    with _session(args) as c:
        if args.name in _SHADOWED_POLICY_NAMES:
            found = _get(c, "/api/policies", {"filter": f'name = "{args.name}"',
                                              "read_mask": args.fields})["policies"]
            if not found:
                raise CliError(f"no such policy {args.name!r}")
            data = found[0]
        else:
            # Quoted whole: a name is one path segment, never a path.
            path = f"/api/policies/{quote(args.name, safe='')}"
            r = c.get(path, params={"read_mask": args.fields} if args.fields else None)
            if r.status_code == 404:
                raise CliError(f"no such policy {args.name!r}")
            data = _checked(r, path)
    rows: list[tuple[str, ...]] = [("FIELD", "VALUE")]
    for k, v in data.items():
        text = v if isinstance(v, str) else json.dumps(v, sort_keys=True, default=str)
        rows.append((k, text if "\n" not in text else text.replace("\n", " ")))
    _emit(args, data, rows)
    return 0


def cmd_network(args) -> int:
    with _session(args) as c:
        data = _get(c, "/api/network", {"days": args.days})
    rows: list[tuple[str, ...]] = [("FROM", "TO", "CALLS", "TOKENS")]
    for e in data.get("edges", []):
        rows.append((e["from"], e["to"], e["calls"], e["tokens"]))
    _emit(args, data, rows)
    return 0


def cmd_trigger_fire(args) -> int:
    """Exercise an inbound endpoint exactly as the external system would."""
    import httpx
    url = f"{args.url.rstrip('/')}/api/hook/{args.token}"
    r = httpx.post(url, json={"message": args.message}, timeout=args.timeout)
    if r.status_code == 404:
        raise CliError("unknown or disabled trigger")
    r.raise_for_status()
    out = r.json()
    if args.json:
        _emit(args, out)
        return 0
    print(out.get("reply", ""))
    return 0 if not out.get("skipped") else 2


def cmd_eval_run(args) -> int:
    """Run an evaluation dataset on the instance, wait for it, and gate on
    the verdict: exit 1 on a regression against the baseline — or on a run
    that did not complete (failed, or made invalid by a config change) —
    with --fail-on-regression. A pipeline that cannot tell "worse" from
    "could not check" must treat both as a stop, so both are 1 here, and the
    message says which."""
    import time
    body: dict[str, Any] = {"dataset": args.dataset, "baseline": args.baseline}
    for key in ("version", "agent", "split", "allowed_drop"):
        value = getattr(args, key)
        if value not in (None, ""):
            body[key] = value
    if args.evaluator:
        body["evaluators"] = list(args.evaluator)
    with _session(args) as c:
        started = _post(c, "/api/evals/runs", body)
        run_id, job_id = started["run"]["id"], started["job"]["id"]
        deadline = time.monotonic() + args.wait
        while True:
            job = _get(c, f"/api/jobs/{quote(job_id, safe='')}")["job"]
            if job.get("status") != "running":
                break
            if time.monotonic() > deadline:
                raise CliError(f"run {run_id} still running after {args.wait:g} s")
            time.sleep(1.0)
        run = _get(c, f"/api/evals/runs/{quote(run_id, safe='')}")
    if args.json:
        _emit(args, run)
    else:
        cmp_ = run.get("comparison") or {}
        rows: list[tuple[str, ...]] = [("METRIC", "VALUE", "N", "BASELINE", "DELTA", "")]
        for m, v in (run.get("metrics") or {}).items():
            if m == "passed_items":
                continue
            c_ = (cmp_.get("metrics") or {}).get(m) or {}
            rows.append((m, f"{v['value']:.3f}", str(v["n"]),
                         "-" if c_.get("baseline") is None else f"{c_['baseline']:.3f}",
                         "-" if c_.get("delta") is None else f"{c_['delta']:+.3f}",
                         "REGRESSED" if c_.get("regressed") else ""))
        print(f"run {run_id}: {run.get('dataset')} v{run.get('dataset_version')} — "
              f"{run.get('status')}"
              + (f", {'PASS' if cmp_.get('passed') else 'REGRESSION'} against "
                 f"{cmp_.get('baseline')}" if cmp_ else ", no baseline"))
        _emit(args, run, rows)
    if run.get("status") != "completed":
        print(f"run {run_id} is {run.get('status')}: {run.get('error') or job.get('error')}",
              file=sys.stderr)
    if args.fail_on_regression and (run.get("status") != "completed"
                                    or run.get("passed") is False):
        return 1
    return 0


def cmd_audit_verify(args) -> int:
    """Check an evidence bundle offline with the standalone verifier: the
    Ed25519 signature against the instance's published keys, the hash chain,
    archive segments and file hashes. Exit 0 verified, 2 a finding, 3 intact
    but no key to trust the signer by, 1 unreadable."""
    from . import verify_bundle
    argv = [args.bundle]
    if getattr(args, "audit_keys", ""):
        argv += ["--keys", args.audit_keys]
    for fp in getattr(args, "fingerprint", None) or []:
        argv += ["--fingerprint", fp]
    return verify_bundle.main(argv)

def _read_text(path: str) -> str:
    """A file's text, or stdin's for "-"."""
    try:
        if path == "-":
            return sys.stdin.read()
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError as e:
        raise CliError(f"{path}: {e.strerror or e}") from None


def _read_bundle(path: str) -> dict[str, Any]:
    try:
        b = json.loads(_read_text(path))
    except ValueError as e:
        raise CliError(f"{path}: not JSON ({e})") from None
    if not isinstance(b, dict) or b.get("kind") not in ("AgentBundle", "AgentBundleList"):
        raise CliError(f"{path}: not an agent bundle — expected kind AgentBundle or "
                       "AgentBundleList (tiq export writes one)")
    return b


def _bundle_names(b: dict[str, Any]) -> list[str]:
    items = b.get("items") if b.get("kind") == "AgentBundleList" else [b]
    names = [str(((i or {}).get("metadata") or {}).get("name") or "")
             for i in (items or []) if isinstance(i, dict)]
    if not names or not all(names):
        raise CliError("every bundle in the file needs metadata.name")
    return names


def cmd_export(args) -> int:
    """The agent (or, with no name, every agent the caller may read) as a
    bundle: the server's own bytes — keys sorted, secrets as references — so
    two exports diff cleanly in Git."""
    path = (f"/api/agents/{quote(args.agent, safe='')}/export" if args.agent
            else "/api/export")
    with _session(args) as c:
        r = c.get(path, params={"sections": args.sections} if args.sections else None)
        if r.status_code == 404:
            raise CliError(f"no such agent {args.agent!r}")
        _checked(r, path)
        text = r.text
    if args.output and args.output != "-":
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(text if text.endswith("\n") else text + "\n")
        except OSError as e:
            raise CliError(f"{args.output}: {e.strerror or e}") from None
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(text.rstrip("\n"))
    return EXIT_OK


def _pending(agent: dict[str, Any]) -> list[str]:
    """What a plan row would change: 'create' for a new agent, else each
    section whose action is not a no-op."""
    if agent.get("created"):
        return ["create"]
    return [s for s, d in (agent.get("plan") or {}).items()
            if isinstance(d, dict) and d.get("action") != "noop"]


def _apply(args, dry_run: bool) -> dict[str, Any]:
    body = {"bundle": _read_bundle(args.file), "dry_run": dry_run, "reason": args.reason}
    with _session(args) as c:
        return _post(c, "/api/agents/apply", body)


def cmd_plan(args) -> int:
    """What applying the file would change, with every gate an apply meets
    checked and nothing written (the apply route's dry run). Exit 0 when the
    instance already matches the file, 2 when changes or drift are pending,
    1 when the apply would be refused."""
    out = _apply(args, dry_run=True)
    pending = {a["agent"]: _pending(a) for a in out.get("agents", [])}
    if args.json:
        _emit(args, out)
    else:
        for a in out.get("agents", []):
            what = pending[a["agent"]]
            state = ("no changes" if not what else "would be created" if what == ["create"]
                     else "would change " + ", ".join(what))
            print(f"{a['agent']}: {state}" + ("" if a.get("valid", True) else " — REFUSED"))
    if not out.get("valid", True):
        for a in out.get("agents", []):
            ref = a.get("refusal")
            if ref:
                d = ref.get("detail")
                msg = (str(d.get("message", "")) + (f" (at {d['at']})" if d.get("at") else "")
                       if isinstance(d, dict) else str(d))
                print(f"tiq: {a['agent']}: refused ({ref.get('status')}): {msg}",
                      file=sys.stderr)
        return EXIT_ERROR
    return EXIT_PENDING if any(pending.values()) else EXIT_OK


def cmd_apply(args) -> int:
    """Make the instance what the file says, in one transaction. --dry-run is
    `plan`, exit codes and all."""
    if args.dry_run:
        return cmd_plan(args)
    out = _apply(args, dry_run=False)
    if args.json:
        _emit(args, out)
        return EXIT_OK
    for a in out.get("agents", []):
        changed = a.get("changed") or []
        state = ("created" if a.get("created") else
                 "updated " + ", ".join(changed) if changed else "no changes")
        print(f"{a['agent']}: {state}"
              + (f" (version {a['version_id']})" if a.get("version_id") else ""))
    return EXIT_OK


def _delete_agent(c, name: str, args) -> dict[str, Any] | None:
    """DELETE one agent; None when it is not there and --ignore-not-found."""
    path = f"/api/gateway/agents/{quote(name, safe='')}"
    params = {k: "true" for k in ("dry_run", "force") if getattr(args, k)}
    r = c.request("DELETE", path, params=params or None,
                  json={"reason": args.reason} if args.reason else None)
    if r.status_code == 404:
        if args.ignore_not_found:
            return None
        raise CliError(f"no such agent {name!r}")
    return _checked(r, path)


def _report_delete(args, results: dict[str, Any]) -> int:
    if args.json:
        _emit(args, results)
        return EXIT_OK
    for name, out in results.items():
        if out is None:
            print(f"{name}: not there")
        elif args.dry_run:
            # The preview: what the delete would touch, shown whole — a list
            # of named dependants is for a person to read.
            print(f"{name}: would delete —")
            print(json.dumps(out, indent=2, sort_keys=True, default=str))
        else:
            print(f"{name}: deleted")
    return EXIT_OK


def cmd_delete(args) -> int:
    """Delete every agent the bundle file names (kubectl delete -f). The
    server's own refusals hold: a delete that would leave policies or other
    agents' workflows naming the agent is refused unless --force, and an
    agent under change control is offboarded, not deleted."""
    names = _bundle_names(_read_bundle(args.file))
    with _session(args) as c:
        results = {n: _delete_agent(c, n, args) for n in names}
    return _report_delete(args, results)


def cmd_agent_delete(args) -> int:
    with _session(args) as c:
        results = {args.agent: _delete_agent(c, args.agent, args)}
    return _report_delete(args, results)


def cmd_agent_create(args) -> int:
    """A new agent from a blueprint (Gateway → Blueprints): the same install,
    permissions and Cedar `create` gate as the console's button."""
    body: dict[str, Any] = {"agent_id": args.name, "provider": args.provider,
                            "model": args.model, "tags": list(args.tag or [])}
    path = f"/api/gateway/blueprints/{quote(args.from_blueprint, safe='')}/install"
    with _session(args) as c:
        out = _checked(c.post(path, json=body), path)
    if args.json:
        _emit(args, out)
    else:
        print(f"created {out.get('agent')} from blueprint {args.from_blueprint}")
    return EXIT_OK


def _agent_lifecycle(args, verb: str) -> int:
    path = f"/api/agents/{quote(args.agent, safe='')}/{verb}"
    with _session(args) as c:
        r = c.post(path, json={})
        if r.status_code == 404:
            raise CliError(f"no managed agent {args.agent!r} — only a managed agent is "
                           "started and stopped here")
        out = _checked(r, path)
    if args.json:
        _emit(args, out)
    else:
        life = out.get("lifecycle") or {}
        print(f"{args.agent}: {life.get('state', '?')}"
              + (f" — {life['reason']}" if life.get("reason") else ""))
    return EXIT_OK


def cmd_agent_start(args) -> int:
    return _agent_lifecycle(args, "start")


def cmd_agent_stop(args) -> int:
    return _agent_lifecycle(args, "stop")


def cmd_policy_validate(args) -> int:
    """Compile a Cedar policy on the instance, storing nothing, against the
    schema the instance enforces with. Exit 0 valid, 2 invalid (or, with
    --strict, carrying a warning: a statement that compiles and can never
    match), 1 when it could not be checked. The file is Cedar text, or JSON
    with the policy's `body` (as a policy's GET returns it)."""
    text = _read_text(args.file)
    if args.file.endswith(".json"):
        try:
            doc = json.loads(text)
        except ValueError as e:
            raise CliError(f"{args.file}: not JSON ({e})") from None
        if not isinstance(doc, dict) or not isinstance(doc.get("body"), str):
            raise CliError(f"{args.file}: a JSON policy file carries its Cedar as `body`")
        text = doc["body"]
    with _session(args) as c:
        out = _post(c, "/api/policies/validate", {"body": text})
    findings = out.get("diagnostics") or []
    warned = [f for f in findings if f.get("severity") == "warning"]
    ok = bool(out.get("valid")) and not (args.strict and warned)
    if args.json:
        _emit(args, out)
    else:
        for f in findings:
            where = f"line {f['line']}" if f.get("line") else "policy"
            print(f"{args.file}: {where}: {f.get('severity', 'error')}: "
                  f"{f.get('code', '')} {f.get('message', '')}".rstrip(), file=sys.stderr)
        if not out.get("valid") and not findings:
            print(f"{args.file}: {out.get('error') or 'invalid'}", file=sys.stderr)
        print(f"{args.file}: {'valid' if ok else 'INVALID'}")
    return EXIT_OK if ok else EXIT_PENDING


def _trigger_toggle(args, verb: str) -> int:
    path = f"/api/triggers/{quote(args.name, safe='')}/{verb}"
    with _session(args) as c:
        r = c.post(path, json={})
        if r.status_code == 404:
            raise CliError(f"no such trigger {args.name!r}")
        out = _checked(r, path)
    if args.json:
        _emit(args, out)
    else:
        print(f"{args.name}: {'resumed' if verb == 'resume' else 'paused'}"
              + ("" if out.get("changed", True) else " (already)"))
    return EXIT_OK


def cmd_trigger_pause(args) -> int:
    return _trigger_toggle(args, "pause")


def cmd_trigger_resume(args) -> int:
    return _trigger_toggle(args, "resume")


def cmd_replay(args) -> int:
    """Replay the newest decided tickets under the configuration in force and
    under a settings candidate (Settings → Candidates), and gate on it: exit
    1 with --fail-on-regression when the replay's acceptance failed — a
    labelled field right on fewer tickets, an agent erroring, or nothing to
    replay. That replay is the evidence the promotion gate asks for."""
    with _session(args) as c:
        rep = _post(c, "/api/replays", {"candidate_id": args.candidate,
                                        "tickets": args.tickets})
    acc = rep.get("acceptance") or {}
    passed = bool(acc.get("passed"))
    if args.json:
        _emit(args, rep)
    else:
        print(f"replay {rep.get('id')}: {rep.get('tickets', 0)} ticket(s), "
              f"{rep.get('changed_tickets', 0)} changed — "
              f"{'PASS' if passed else 'REGRESSION'}")
        rows: list[tuple[str, ...]] = [("CHECK", "BASELINE", "CANDIDATE", "")]
        for chk in acc.get("checks") or []:
            rows.append((chk.get("check", ""),
                         str(chk.get("baseline", chk.get("value", "-"))),
                         str(chk.get("candidate", "-")),
                         "" if chk.get("passed") else "FAILED"))
        _emit(args, rep, rows)
    if args.fail_on_regression and not passed:
        return EXIT_ERROR
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tiq", description="Command line for a TicketIQ instance.")
    p.add_argument("--url", default=os.environ.get("TICKETIQ_URL", DEFAULT_URL),
                   help=f"instance base URL (default {DEFAULT_URL})")
    p.add_argument("--user", default="", help="username; else TICKETIQ_CLI_USER")
    p.add_argument("--password", default="",
                   help="password; else TICKETIQ_CLI_PASSWORD")
    p.add_argument("--token", default="",
                   help="a service account's svc/<name>:<secret> (or a session it "
                        "minted); else TICKETIQ_TOKEN. For CI, and SSO-only instances")
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--json", action="store_true", help="machine-readable output")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("agents", help="list agents and their bindings").set_defaults(fn=cmd_agents)

    ask = sub.add_parser("ask", help="run one agent and print its reply")
    ask.add_argument("agent")
    ask.add_argument("message")
    ask.set_defaults(fn=cmd_ask)

    usage = sub.add_parser("usage", help="tokens and spend")
    usage.add_argument("--days", type=int, default=7)
    usage.set_defaults(fn=cmd_usage)

    pols = sub.add_parser("policies", help="Cedar policies")
    pols.add_argument("which", nargs="?", choices=tuple(_SYSTEM_LISTS),
                      help="the role bindings (system) or the roles (action-groups) "
                           "instead of the Cedar policies")
    pols.add_argument("--filter", default="",
                      help='AIP-160 filter, e.g. \'scope.effect = forbid AND tags.env = prod\'')
    pols.add_argument("--order-by", default="",
                      help="name, display_name, created_at or updated_at; asc or desc")
    pols.add_argument("--page-size", type=int, default=None,
                      help="1-100 (system lists: up to 1000, default 50); default every match")
    pols.add_argument("--page-token", default="", help="the next page, from the previous one")
    pols.set_defaults(fn=cmd_policies)

    pol = sub.add_parser("policy", help="one Cedar policy")
    pol_sub = pol.add_subparsers(dest="policy_command", required=True)
    pol_get = pol_sub.add_parser("get", help="show one policy")
    pol_get.add_argument("name")
    pol_get.add_argument("--fields", default="",
                         help="comma-separated fields to return (the name always is)")
    pol_get.set_defaults(fn=cmd_policy_get)
    pol_val = pol_sub.add_parser(
        "validate", help="compile a policy file on the instance; exit 2 if invalid")
    pol_val.add_argument("file", help="Cedar text, or JSON with `body`; - for stdin")
    pol_val.add_argument("--strict", action="store_true",
                         help="also fail on a warning (a statement that can never match)")
    pol_val.set_defaults(fn=cmd_policy_validate)

    net = sub.add_parser("network", help="which agent calls which provider")
    net.add_argument("--days", type=int, default=7)
    net.set_defaults(fn=cmd_network)

    trig = sub.add_parser("trigger", help="inbound trigger endpoints")
    trig_sub = trig.add_subparsers(dest="trigger_command", required=True)
    fire = trig_sub.add_parser("fire", help="post a message to a trigger")
    fire.add_argument("token")
    fire.add_argument("message")
    fire.set_defaults(fn=cmd_trigger_fire)
    for verb, fn, what in (("pause", cmd_trigger_pause, "stop a trigger acting, keeping it"),
                           ("resume", cmd_trigger_resume, "switch a paused trigger back on")):
        t = trig_sub.add_parser(verb, help=what)
        t.add_argument("name")
        t.set_defaults(fn=fn)

    ev = sub.add_parser("eval", help="offline evaluation runs")
    ev_sub = ev.add_subparsers(dest="eval_command", required=True)
    ev_run = ev_sub.add_parser("run", help="run a dataset and compare it with a baseline")
    ev_run.add_argument("--dataset", required=True)
    ev_run.add_argument("--version", type=int, default=None)
    ev_run.add_argument("--agent", default="", help="AGENT or AGENT@VERSION_ID")
    ev_run.add_argument("--split", default="", choices=("", "calibrate", "holdout"))
    ev_run.add_argument("--evaluator", action="append", default=None)
    ev_run.add_argument("--baseline", default="",
                        help="a run id, 'pinned', 'latest' or 'none' (default: pinned, if any)")
    ev_run.add_argument("--max-drop", dest="allowed_drop", type=float, default=None)
    ev_run.add_argument("--fail-on-regression", action="store_true")
    ev_run.add_argument("--wait", type=float, default=1800.0,
                        help="seconds to wait for the run (default 1800)")
    ev_run.set_defaults(fn=cmd_eval_run)

    exp = sub.add_parser("export", help="an agent (or every agent) as a bundle file")
    exp.add_argument("agent", nargs="?", default="", help="omit for every agent")
    exp.add_argument("--sections", default="", help="comma-separated sections only")
    exp.add_argument("-o", "--output", default="", help="write here instead of stdout")
    exp.set_defaults(fn=cmd_export)

    def bundle_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("-f", "--file", required=True, help="the bundle; - for stdin")
        sp.add_argument("--reason", default="",
                        help="why, for a change that weakens a control")

    plan = sub.add_parser("plan", help="what applying a bundle would change: "
                                       "exit 0 none, 2 pending, 1 refused")
    bundle_args(plan)
    plan.set_defaults(fn=cmd_plan)
    app = sub.add_parser("apply", help="make the instance what a bundle says")
    bundle_args(app)
    app.add_argument("--dry-run", action="store_true", help="plan only (plan's exit codes)")
    app.set_defaults(fn=cmd_apply)

    def delete_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--dry-run", action="store_true",
                        help="show what the delete would touch; change nothing")
        sp.add_argument("--force", action="store_true",
                        help="delete even with policies or workflows naming the agent")
        sp.add_argument("--reason", default="")
        sp.add_argument("--ignore-not-found", action="store_true")

    dele = sub.add_parser("delete", help="delete every agent a bundle file names")
    dele.add_argument("-f", "--file", required=True)
    delete_args(dele)
    dele.set_defaults(fn=cmd_delete)

    agent = sub.add_parser("agent", help="one agent's lifecycle")
    agent_sub = agent.add_subparsers(dest="agent_command", required=True)
    a_create = agent_sub.add_parser("create", help="a new agent from a blueprint")
    a_create.add_argument("name", nargs="?", default="",
                          help="the new agent's id (default: the blueprint's)")
    a_create.add_argument("--from-blueprint", required=True)
    a_create.add_argument("--provider", default="")
    a_create.add_argument("--model", default="")
    a_create.add_argument("--tag", action="append", default=None, help="key=value")
    a_create.set_defaults(fn=cmd_agent_create)
    for verb, fn in (("start", cmd_agent_start), ("stop", cmd_agent_stop)):
        a = agent_sub.add_parser(verb, help=f"{verb} a managed agent")
        a.add_argument("agent")
        a.set_defaults(fn=fn)
    a_del = agent_sub.add_parser("delete", help="delete an agent")
    a_del.add_argument("agent")
    delete_args(a_del)
    a_del.set_defaults(fn=cmd_agent_delete)

    rp = sub.add_parser("replay", help="replay decided tickets under a settings candidate")
    rp.add_argument("--candidate", required=True, help="the candidate id")
    rp.add_argument("--tickets", type=int, default=50, help="how many (1-200)")
    rp.add_argument("--fail-on-regression", action="store_true",
                    help="exit 1 when the replay's acceptance fails")
    rp.set_defaults(fn=cmd_replay)

    audit = sub.add_parser("audit", help="the audit log's evidence")
    audit_sub = audit.add_subparsers(dest="audit_command", required=True)
    verify = audit_sub.add_parser(
        "verify", help="check an evidence bundle offline (no server, no network)")
    verify.add_argument("bundle", help="the zip from Audit Log → Evidence bundle")
    verify.add_argument("--fingerprint", action="append", default=[], metavar="HEX",
                        help="trust the signing key with this fingerprint (repeatable)")
    verify.add_argument("--audit-keys", metavar="FILE", default="",
                        help="the instance's published audit signing keys (GET "
                             "/api/audit/signing-key, saved as JSON): the manifest's "
                             "Ed25519 attestation must verify under one of them")
    verify.set_defaults(fn=cmd_audit_verify)

    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as e:
        # argparse exits 2 on a usage error — the code `plan` gives for
        # "changes pending". A mistyped flag in a pipeline must read as the
        # error it is, not as drift, so it is 1 here (--help stays 0).
        return 0 if e.code in (0, None) else 1
    try:
        return int(args.fn(args) or 0)
    except CliError as e:
        print(f"tiq: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # pragma: no cover - last resort
        print(f"tiq: {e.__class__.__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
