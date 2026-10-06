"""`liya` — the command line for Liyagent / TicketIQ.

Every resource command is a thin call to the REST API the console uses (see
docs-site/content/cli/reference.md for the endpoint behind each one), so the
CLI can never become the only way to do something, and a server that lacks an
endpoint answers "not supported by this server version" instead of a stack
trace.

    liya auth login                      # hidden token prompt, or LIYA_TOKEN
    liya env use demo                    # switch instance
    liya status                          # the command-center summary
    liya agents list -o yaml
    liya agents chat copilot "VPN drops hourly"
    liya audit search outcome=denied --since 24h
    liya export -o infra/ && liya apply -f infra/ --dry-run

It absorbs `tiq` (ticketiq/cli/tiq.py), the earlier command line: its HTTP
error handling, service-account exchange, bundle plan/apply and offline audit
verification are reused as they are, and every `tiq` verb that `liya` does not
define itself (ask, usage, plan, policy, network, trigger, eval, agent,
replay, delete) is forwarded to it unchanged — `python -m liya plan -f
x.json` and the `./tiq` wrapper keep working.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

from . import config, gitops, tiq
from .client import CliError, Session, q, since_timestamp
from .output import FORMATS, emit, note, paint, state

PROG = "liya"
# What a script reads from the exit status, each failure kind its own: 2 the
# input was invalid (a usage error, a 400 or 422, a file that does not
# parse), 3 the credential was refused or a permission is missing, 4 the
# thing named does not exist — and 1 anything else. 5 is no failure: a
# deliberate "no" (changes pending on apply --dry-run, a guardrail test that
# would block, an agent that declined), kept apart from an invalid manifest
# so a pipeline can never read one as the other. CliError.code carries the
# kind from wherever it was raised.
EXIT_OK, EXIT_ERROR, EXIT_INVALID, EXIT_AUTH, EXIT_NOT_FOUND, EXIT_PENDING = 0, 1, 2, 3, 4, 5
# `tiq` verbs liya does not define itself; forwarded to tiq.main unchanged.
TIQ_VERBS = {"ask", "usage", "plan", "policy", "network", "trigger", "eval", "agent",
             "replay", "delete"}


# ---- plumbing ----

def _fmt(args) -> str:
    return getattr(args, "output", None) or os.environ.get("LIYA_OUTPUT") or "table"


def _session(args) -> Session:
    return Session(env=args.env, url=args.url, token=args.token, timeout=args.timeout,
                   verbose=bool(getattr(args, "verbose", False)))


def _run(args, fn: Callable[[Session], int | None]) -> int:
    s = _session(args)
    try:
        return int(fn(s) or 0)
    finally:
        s.close()


def _read_secret(prompt: str, from_stdin: bool = False) -> str:
    """A secret from stdin (piped, or --stdin) or a hidden prompt. Never an
    argument: argv is visible to every user on the machine via ps."""
    if from_stdin or not sys.stdin.isatty():
        value = sys.stdin.read().rstrip("\r\n")
    else:
        value = getpass.getpass(prompt)
    if not value:
        raise CliError("no value given", code=EXIT_INVALID)
    return value


def _confirm(args, what: str) -> None:
    if getattr(args, "yes", False) or not sys.stdin.isatty():
        return
    answer = input(f"{what}? [y/N] ").strip().lower()
    if answer not in ("y", "yes"):
        raise CliError("cancelled")


def _text_arg(value: str) -> str:
    """'-' reads the text from stdin."""
    return sys.stdin.read() if value == "-" else value


# ---- auth ----

def cmd_auth_login(args) -> int:
    s = _session(args)
    try:
        c = s.anonymous()
        token = ""
        # 1. A device-code flow, where the server advertises one (RFC 8628).
        if not (args.token_stdin or args.username or os.environ.get("LIYA_TOKEN")):
            token = _device_flow(s)
        # 2. A token from the environment, stdin, or a hidden prompt.
        if not token and os.environ.get("LIYA_TOKEN") and not args.username:
            token = os.environ["LIYA_TOKEN"]
        if not token and args.username:
            password = _read_secret(f"Password for {args.username}@{s.env}: ",
                                    args.password_stdin)
            r = c.post("/api/login", json={"username": args.username, "password": password})
            if r.status_code != 200:
                raise CliError(f"sign-in failed for {args.username!r} ({r.status_code}): "
                               f"{tiq._detail(r)}",
                               code=EXIT_AUTH if r.status_code in (401, 403) else EXIT_ERROR)
            token = (r.json() or {}).get("token", "")
            if not token:
                raise CliError("the server signed in but returned no session token")
        if not token:
            token = _read_secret(f"API token for {s.env} ({s.url}): ", args.token_stdin)
        # Prove it works before keeping it.
        c.headers["Authorization"] = f"Bearer {tiq._bearer(c, token)}"
        r = c.get("/api/me")
        if r.status_code != 200:
            raise CliError(f"the token was refused by {s.url} ({r.status_code})",
                           code=EXIT_AUTH if r.status_code in (401, 403) else EXIT_ERROR)
        me = r.json()
        config.save_credential(s.env, {"token": token, "kind": config.token_kind(token),
                                       "user": me.get("username", ""), "url": s.url,
                                       "saved_at": int(time.time())})
        note(f"Logged in to {s.env} ({s.url}) as {me.get('username')} "
             f"[{me.get('role', '?')}]. Credential saved to {config.credentials_path()} (0600).")
        return EXIT_OK
    finally:
        s.close()


def _device_flow(s: Session) -> str:
    """RFC 8628, when the server's OAuth metadata names a device endpoint.
    TicketIQ servers that do not advertise one fall through to the token
    prompt."""
    try:
        meta = s.anonymous().get("/.well-known/oauth-authorization-server")
        meta = meta.json() if meta.status_code == 200 else {}
    except Exception:
        return ""
    endpoint = meta.get("device_authorization_endpoint")
    token_url = meta.get("token_endpoint")
    if not (endpoint and token_url):
        return ""
    c = s.anonymous()
    start = c.post(endpoint, data={"client_id": "liya-cli"})
    if start.status_code != 200:
        return ""
    d = start.json()
    note(f"Open {d.get('verification_uri_complete') or d.get('verification_uri')} "
         f"and enter code {d.get('user_code')}")
    try:
        import webbrowser
        webbrowser.open(d.get("verification_uri_complete") or d.get("verification_uri"))
    except Exception:
        pass
    interval = int(d.get("interval", 5))
    deadline = time.monotonic() + int(d.get("expires_in", 600))
    while time.monotonic() < deadline:
        time.sleep(interval)
        r = c.post(token_url, data={"grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                                    "device_code": d.get("device_code"), "client_id": "liya-cli"})
        body = r.json() if r.content else {}
        if r.status_code == 200 and body.get("access_token"):
            return body["access_token"]
        err = body.get("error")
        if err == "slow_down":
            interval += 5
        elif err != "authorization_pending":
            raise CliError(f"device sign-in failed: {err or r.status_code}", code=EXIT_AUTH)
    raise CliError("device sign-in timed out", code=EXIT_AUTH)


def cmd_auth_logout(args) -> int:
    s = _session(args)
    try:
        entry = config.load_credentials().get(s.env) or {}
        if entry.get("kind") == "session" and entry.get("token"):
            try:  # best effort: end the session server-side too
                s.anonymous().post("/api/logout",
                                   headers={"Authorization": f"Bearer {entry['token']}"})
            except Exception:
                pass
        removed = config.delete_credential(s.env)
    finally:
        s.close()
    note(f"Logged out of {s.env}." if removed else f"No stored credential for {s.env}.")
    return EXIT_OK


def cmd_auth_status(args) -> int:
    def run(s: Session) -> int:
        token, source = s.token_source()
        out: dict[str, Any] = {"env": s.env, "url": s.url, "logged_in": False,
                               "credential_source": source or None,
                               "credential_kind": config.token_kind(token) if token else None,
                               "credentials_file": str(config.credentials_path()),
                               "credentials_mode": (oct(config.credentials_mode())
                                                    if config.credentials_mode() is not None
                                                    else None)}
        if token:
            try:
                me = s.get("/api/me")
                out.update(logged_in=True, user=me.get("username"), role=me.get("role"),
                           permissions=len(me.get("permissions") or []))
            except CliError as e:
                out["error"] = str(e)
        emit(_fmt(args), out)
        return EXIT_OK if out["logged_in"] else EXIT_ERROR
    return _run(args, run)


# ---- environments ----

def cmd_env_list(args) -> int:
    cfg = config.load_config()
    creds = config.load_credentials()
    envs = [{"name": n, "url": e["url"], "current": n == cfg["current"],
             "logged_in": bool((creds.get(n) or {}).get("token"))}
            for n, e in sorted(cfg["environments"].items())]
    emit(_fmt(args), envs, ("", "name", "url", "logged in"),
         [("*" if e["current"] else " ", e["name"], e["url"], e["logged_in"]) for e in envs])
    return EXIT_OK


def cmd_env_use(args) -> int:
    try:
        config.use_env(args.name)
    except KeyError:
        raise CliError(f"unknown environment {args.name!r} — `liya env add {args.name} "
                       "--url URL` first", code=EXIT_NOT_FOUND) from None
    note(f"Now using {args.name} ({config.load_config()['environments'][args.name]['url']}).")
    return EXIT_OK


def cmd_env_add(args) -> int:
    if not args.url.startswith(("http://", "https://")):
        raise CliError("--url must start with http:// or https://", code=EXIT_INVALID)
    config.add_env(args.name, args.url)
    if args.use:
        config.use_env(args.name)
    note(f"Added {args.name} ({args.url})" + (" and switched to it." if args.use else "."))
    return EXIT_OK


def cmd_env_remove(args) -> int:
    if not config.remove_env(args.name):
        raise CliError(f"unknown environment {args.name!r}", code=EXIT_NOT_FOUND)
    config.delete_credential(args.name)
    note(f"Removed {args.name} and its stored credential.")
    return EXIT_OK


# ---- agents ----

def _agent_row(a: dict[str, Any]) -> tuple:
    eff = a.get("effective") or {}
    return (a.get("key"), a.get("label"), a.get("stage", "-"), bool(a.get("llm")),
            eff.get("provider") or ("global" if a.get("llm") else "-"), eff.get("model") or "-")


def cmd_agents_list(args) -> int:
    def run(s: Session) -> None:
        data = s.get("/api/agents")
        agents = data.get("agents", [])
        if args.stage:
            agents = [a for a in agents if a.get("stage") == args.stage]
        emit(_fmt(args), {"agents": agents}, ("id", "name", "stage", "llm", "provider", "model"),
             [_agent_row(a) for a in agents])
    return _run(args, run)


def cmd_agents_get(args) -> int:
    def run(s: Session) -> None:
        found = [a for a in s.get("/api/agents").get("agents", []) if a.get("key") == args.id]
        if not found:
            raise CliError(f"no such agent {args.id!r}", code=EXIT_NOT_FOUND)
        agent = dict(found[0])
        r = s.request("GET", f"/api/agents/{q(args.id)}/runtime", check=False)
        if r.status_code == 200:
            agent["runtime"] = r.json()
        emit(_fmt(args), agent)
    return _run(args, run)


def cmd_agents_create(args) -> int:
    def run(s: Session) -> None:
        body = {"agent_id": args.name, "provider": args.provider, "model": args.model,
                "tags": list(args.tag or [])}
        path = f"/api/gateway/blueprints/{q(args.from_blueprint)}/install"
        r = s.request("POST", path, json=body, check=False)
        if r.status_code == 404:
            names = [b.get("key") for b in s.get("/api/gateway/blueprints").get("blueprints", [])]
            raise CliError(f"no blueprint {args.from_blueprint!r}; available: "
                           + (", ".join(names) or "none"), code=EXIT_NOT_FOUND)
        out = tiq._checked(r, path)
        if _fmt(args) != "table":
            emit(_fmt(args), out)
        else:
            agent = out.get("agent") or args.name
            note(f"created agent {agent} from blueprint {args.from_blueprint}")
            note(_new_agent_access(agent))
    return _run(args, run)


def _new_agent_access(agent: str) -> str:
    """What a new agent may do, and who may use it — said as it is, since
    "no access until a policy names it" is what people assume and is not
    how Cedar is applied here: a resource no policy names is ungoverned
    (policy.check), so roles alone decide, and a policy that names it
    governs it completely."""
    return (f"Access: {agent} can already call the LLM provider it is bound to and the "
            f"tools of every MCP server attached to it — Cedar governs a provider or "
            f"server only once some policy names it. People reach {agent} through their "
            f"roles until a policy names {agent}; then only what policies permit. Bind a "
            f"template: liya policies create NAME --agent {agent} --template "
            f"readonly|sandboxed|standard|full --principal group:TEAM "
            f"(add --agent-tools to also bound {agent}'s own tool calls).")


def cmd_agents_update(args) -> int:
    body: dict[str, Any] = {}
    for key in ("provider", "model", "max_tokens", "effort", "agent_timeout", "reason"):
        v = getattr(args, key)
        if v not in (None, ""):
            body["timeout" if key == "agent_timeout" else key] = v
    if args.enabled is not None:
        body["enabled"] = args.enabled
    if not [k for k in body if k != "reason"]:
        raise CliError("nothing to update — pass --provider, --model, --max-tokens, "
                       "--effort, --agent-timeout, --enable or --disable", code=EXIT_INVALID)

    def run(s: Session) -> None:
        out = s.put(f"/api/agents/{q(args.id)}", body)
        emit(_fmt(args), out) if _fmt(args) != "table" else note(
            f"updated {args.id}: " + ", ".join(f"{k}={v}" for k, v in body.items()
                                               if k != "reason"))
    return _run(args, run)


def cmd_agents_delete(args) -> int:
    if not args.dry_run:
        _confirm(args, f"Delete agent {args.id}")

    def run(s: Session) -> None:
        params = {k: "true" for k in ("dry_run", "force") if getattr(args, k)}
        out = s.request("DELETE", f"/api/gateway/agents/{q(args.id)}", params=params,
                        json={"reason": args.reason} if args.reason else None,
                        not_found=f"no such agent {args.id!r}")
        if _fmt(args) != "table" or args.dry_run:
            emit(_fmt(args) if _fmt(args) != "table" else "yaml", out)
        else:
            note(f"deleted {args.id}")
    return _run(args, run)


def _lifecycle(verb: str, shown: str) -> Callable[[Any], int]:
    def cmd(args) -> int:
        def run(s: Session) -> None:
            out = s.post(f"/api/agents/{q(args.id)}/{verb}", {},
                         not_found=f"no managed agent {args.id!r} — only a managed agent "
                                   f"is {shown}")
            life = out.get("lifecycle") or {}
            emit(_fmt(args), out, ("agent", "state", "reason"),
                 [(args.id, state(life.get("state", "?")), life.get("reason"))])
        return _run(args, run)
    return cmd


cmd_agents_pause = _lifecycle("stop", "paused")
cmd_agents_resume = _lifecycle("start", "resumed")


def cmd_agents_chat(args) -> int:
    def run(s: Session) -> int:
        body = {"message": _text_arg(args.message), "session": args.session,
                "system": args.system, "ticket": args.ticket}
        out = s.post(f"/api/agents/{q(args.id)}/playground",
                     {k: v for k, v in body.items() if v},
                     not_found=f"no such agent {args.id!r}")
        if _fmt(args) != "table":
            emit(_fmt(args), out)
        elif out.get("skipped"):
            note(paint(f"no reply: {out['skipped']}", "yellow"))
        else:
            print(out.get("reply", ""))
            meta = [f"{k}={out[k]}" for k in ("provider", "model", "latency_ms") if out.get(k)]
            if meta:
                note(paint(" ".join(meta), "dim"))
        # A refusal is a failure for a script even though the call succeeded.
        return EXIT_PENDING if out.get("skipped") else EXIT_OK
    return _run(args, run)


def cmd_agents_eval(args) -> int:
    def run(s: Session) -> int:
        dataset = args.dataset
        if not dataset:
            sets = s.get("/api/evals/datasets").get("datasets", [])
            mine = [d["name"] for d in sets
                    if d.get("agent") == args.id or (d.get("origin") or {}).get("agent") == args.id
                    or d["name"] in (args.id, f"{args.id}-evals", f"{args.id}-eval")]
            if len(mine) != 1:
                raise CliError(
                    f"{'no' if not mine else 'more than one'} eval set for {args.id!r} — "
                    "pass --dataset NAME (available: "
                    + (", ".join(d["name"] for d in sets) or "none") + ")",
                    code=EXIT_NOT_FOUND if not mine else EXIT_INVALID)
            dataset = mine[0]
        body: dict[str, Any] = {"dataset": dataset, "agent": args.id, "baseline": args.baseline}
        started = s.post("/api/evals/runs", body)
        run_id, job_id = started["run"]["id"], started["job"]["id"]
        deadline = time.monotonic() + args.wait
        job: dict[str, Any] = {}
        while True:
            job = s.get(f"/api/jobs/{q(job_id)}")["job"]
            if job.get("status") != "running":
                break
            if time.monotonic() > deadline:
                raise CliError(f"eval run {run_id} still running after {args.wait:g}s")
            time.sleep(1.0)
        result = s.get(f"/api/evals/runs/{q(run_id)}")
        cmp_ = result.get("comparison") or {}
        completed = result.get("status") == "completed"
        passed = completed and result.get("passed") is not False and cmp_.get("passed", True)
        rows = []
        for m, v in (result.get("metrics") or {}).items():
            if m == "passed_items" or not isinstance(v, dict):
                continue
            c_ = (cmp_.get("metrics") or {}).get(m) or {}
            rows.append((m, f"{v.get('value', 0):.3f}", v.get("n"),
                         "-" if c_.get("baseline") is None else f"{c_['baseline']:.3f}",
                         state("regressed") if c_.get("regressed") else state("pass")))
        if _fmt(args) != "table":
            emit(_fmt(args), result)
        else:
            emit("table", result, ("metric", "value", "n", "baseline", "result"), rows)
            verdict = state("PASS") if passed else state("FAIL")
            print(f"\n{args.id} on {dataset} (run {run_id}): {verdict}"
                  + ("" if completed else f" — run {result.get('status')}: "
                     f"{result.get('error') or job.get('error') or ''}"))
        return EXIT_OK if passed else EXIT_ERROR
    return _run(args, run)


# ---- tickets ----

def _ticket_row(t: dict[str, Any]) -> tuple:
    return (t.get("id"), state(t.get("status", "")), t.get("priority"), t.get("team"),
            t.get("category"), t.get("title"))


def cmd_tickets_list(args) -> int:
    def run(s: Session) -> None:
        data = s.get("/api/tickets", params={"status": args.status, "team": args.team,
                                             "category": args.category, "q": args.query,
                                             "limit": args.limit, "offset": args.offset})
        emit(_fmt(args), data, ("id", "status", "priority", "team", "category", "title"),
             [_ticket_row(t) for t in data.get("tickets", [])])
        if _fmt(args) == "table" and data.get("total", 0) > len(data.get("tickets", [])):
            note(f"{len(data['tickets'])} of {data['total']} shown; --offset "
                 f"{args.offset + len(data['tickets'])} for more")
    return _run(args, run)


def cmd_tickets_get(args) -> int:
    def run(s: Session) -> None:
        emit(_fmt(args), s.get(f"/api/tickets/{q(args.id)}",
                               not_found=f"no such ticket {args.id!r}"))
    return _run(args, run)


def cmd_tickets_create(args) -> int:
    def run(s: Session) -> None:
        body = {"title": args.title, "description": _text_arg(args.description or ""),
                "requester": args.requester}
        out = s.post("/api/tickets", body)
        t = out.get("ticket", out)
        emit(_fmt(args), out, ("id", "status", "priority", "team", "category", "title"),
             [_ticket_row(t)])
    return _run(args, run)


def cmd_tickets_comment(args) -> int:
    def run(s: Session) -> None:
        out = s.post(f"/api/tickets/{q(args.id)}/replies",
                     {"author": args.author, "body": _text_arg(args.text),
                      "public": not args.internal},
                     not_found=f"no such ticket {args.id!r}")
        emit(_fmt(args), out) if _fmt(args) != "table" else note(
            f"{'internal note' if args.internal else 'reply'} added to {args.id}")
    return _run(args, run)


def cmd_tickets_close(args) -> int:
    def run(s: Session) -> None:
        body = {"status": args.status}
        if args.resolution:
            body["resolution"] = args.resolution
        out = s.patch(f"/api/tickets/{q(args.id)}", body,
                      not_found=f"no such ticket {args.id!r}")
        t = out.get("ticket", out)
        emit(_fmt(args), out, ("id", "status", "priority", "team", "category", "title"),
             [_ticket_row(t)])
    return _run(args, run)


# ---- triggers ----

def cmd_triggers_list(args) -> int:
    def run(s: Session) -> None:
        path = f"/api/agents/{q(args.agent)}/triggers" if args.agent else "/api/triggers"
        data = s.get(path)
        rows = [(t.get("name"), t.get("agent"), t.get("kind"),
                 state("enabled" if t.get("enabled", True) else "paused"),
                 t.get("schedule") or ",".join(t.get("events") or []) or "-", t.get("about"))
                for t in data.get("triggers", [])]
        emit(_fmt(args), data, ("name", "agent", "kind", "state", "when", "about"), rows)
    return _run(args, run)


def cmd_triggers_create(args) -> int:
    body: dict[str, Any] = {"agent": args.agent, "kind": args.kind, "about": args.about,
                            "schedule": args.schedule, "timezone": args.timezone,
                            "input": args.input, "events": args.event,
                            "enabled": not args.disabled}
    body = {k: v for k, v in body.items() if v not in (None, "", [])}

    def run(s: Session) -> None:
        r = s.request("GET", f"/api/triggers/{q(args.name)}", check=False)
        if r.status_code == 200 and not args.replace:
            raise CliError(f"trigger {args.name!r} exists — pass --replace to overwrite it",
                           code=EXIT_INVALID)
        out = s.put(f"/api/triggers/{q(args.name)}", body)
        emit(_fmt(args), out) if _fmt(args) != "table" else note(
            f"trigger {args.name} saved ({args.kind} → {args.agent})")
    return _run(args, run)


def cmd_triggers_delete(args) -> int:
    _confirm(args, f"Delete trigger {args.name}")

    def run(s: Session) -> None:
        s.delete(f"/api/triggers/{q(args.name)}", not_found=f"no such trigger {args.name!r}")
        note(f"deleted trigger {args.name}")
    return _run(args, run)


# ---- providers & models ----

def cmd_providers_list(args) -> int:
    def run(s: Session) -> None:
        data = s.get("/api/llm/providers")
        health = {}
        r = s.request("GET", "/api/llm/provider-health", check=False)
        if r.status_code == 200:
            health = r.json().get("providers") or {}
        provs = data.get("providers") or {}
        rows = [(n, p.get("kind"), p.get("default_model"), p.get("base_url"),
                 state("enabled" if p.get("enabled", True) else "disabled"),
                 state((health.get(n) or {}).get("state") or (health.get(n) or {}).get("status")
                       or "-"))
                for n, p in sorted(provs.items())]
        emit(_fmt(args), data, ("name", "kind", "model", "base url", "state", "health"), rows)
    return _run(args, run)


def cmd_providers_test(args) -> int:
    def run(s: Session) -> int:
        out = s.post(f"/api/llm/providers/{q(args.name)}/test", {},
                     not_found=f"no such provider {args.name!r}")
        ok = bool(out.get("ok", out.get("success", False)))
        emit(_fmt(args), out, ("provider", "result", "model", "latency ms", "detail"),
             [(args.name, state("pass" if ok else "fail"), out.get("model"),
               out.get("latency_ms"), out.get("error") or out.get("detail") or out.get("reply"))])
        return EXIT_OK if ok else EXIT_ERROR
    return _run(args, run)


def cmd_providers_add(args) -> int:
    body: dict[str, Any] = {"kind": args.kind, "base_url": args.base_url,
                            "default_model": args.model, "display_name": args.display_name,
                            "about": args.about}
    if args.api_key_stdin or args.prompt_key:
        body["api_key"] = _read_secret(f"API key for provider {args.name}: ",
                                       args.api_key_stdin)
    body = {k: v for k, v in body.items() if v not in (None, "")}

    def run(s: Session) -> None:
        r = s.request("GET", f"/api/llm/providers/{q(args.name)}", check=False)
        if r.status_code == 200 and not args.replace:
            raise CliError(f"provider {args.name!r} exists — pass --replace to overwrite it",
                           code=EXIT_INVALID)
        s.put(f"/api/llm/providers/{q(args.name)}", body)
        note(f"provider {args.name} saved ({args.kind})"
             + (" with an API key (stored sealed, not shown)" if "api_key" in body else ""))
    return _run(args, run)


def cmd_models_list(args) -> int:
    def run(s: Session) -> None:
        if args.provider:
            data = s.get(f"/api/llm/providers/{q(args.provider)}/models",
                         not_found=f"no such provider {args.provider!r}")
            models = data.get("models") or []
        else:
            models, token = [], ""
            while True:
                data = s.get("/api/llm/models", params={"page_token": token})
                models += data.get("models") or []
                token = data.get("next_page_token") or ""
                if not token or len(models) >= args.limit:
                    break
        models = models[: args.limit]
        rows = []
        for m in models:
            m = m if isinstance(m, dict) else {"name": m}
            price = m.get("default_pricing") or m.get("pricing") or {}
            rows.append((m.get("name") or m.get("id"), m.get("publisher") or m.get("provider_type"),
                         m.get("max_input_tokens"),
                         f"{price['input']}/{price['output']}" if "input" in price else "-"))
        emit(_fmt(args), {"models": models}, ("model", "publisher", "context", "$/Mtok in/out"),
             rows)
    return _run(args, run)


# ---- guardrails ----

def cmd_guardrails_list(args) -> int:
    def run(s: Session) -> None:
        data = s.get("/api/guardrails")
        rows = [(n, g.get("kind"), state(g.get("mode") or "enforce"), g.get("action"),
                 ",".join(g.get("stages") or []) or g.get("direction"),
                 state("enabled" if g.get("enabled", True) else "disabled"))
                for n, g in sorted((data.get("guardrails") or {}).items())]
        emit(_fmt(args), data, ("name", "kind", "mode", "action", "stages", "state"), rows)
    return _run(args, run)


def cmd_guardrails_test(args) -> int:
    def run(s: Session) -> int:
        out = s.post("/api/guardrails/preview", {"text": _text_arg(args.text),
                                                  "agent": args.agent,
                                                  "direction": args.direction})
        rows = [(f.get("policy"), f.get("category") or f.get("family"), f.get("action"),
                 f.get("score"), "shadow" if f.get("shadow") else "enforced")
                for f in out.get("findings") or []]
        if _fmt(args) != "table":
            emit(_fmt(args), out)
        else:
            emit("table", out, ("guardrail", "finding", "action", "score", "mode"), rows)
            verdict = state("blocked") if out.get("blocked") else state("allowed")
            print(f"\nverdict: {verdict}" + (f" — {out['reason']}" if out.get("reason") else ""))
        return EXIT_PENDING if out.get("blocked") else EXIT_OK
    return _run(args, run)


# ---- secrets ----

def cmd_secrets_list(args) -> int:
    def run(s: Session) -> None:
        data = s.get("/api/secrets")
        secrets = data.get("secrets") or {}
        rows = [(label, (m or {}).get("about"), ",".join((m or {}).get("tags") or []),
                 (m or {}).get("updated_at") or (m or {}).get("created_at"))
                for label, m in sorted(secrets.items())]
        emit(_fmt(args), data, ("label", "about", "tags", "updated"), rows)
    return _run(args, run)


def cmd_secrets_set(args) -> int:
    value = _read_secret(f"Value for secret {args.label} (hidden): ", args.stdin)

    def run(s: Session) -> None:
        body: dict[str, Any] = {"value": value, "about": args.about}
        if args.tag:
            body["tags"] = list(args.tag)
        s.put(f"/api/secrets/{q(args.label)}", body)
        note(f"secret {args.label} stored (value not shown)")
    return _run(args, run)


def cmd_secrets_delete(args) -> int:
    _confirm(args, f"Delete secret {args.label}")

    def run(s: Session) -> None:
        s.delete(f"/api/secrets/{q(args.label)}", not_found=f"no such secret {args.label!r}")
        note(f"deleted secret {args.label}")
    return _run(args, run)


# ---- policies ----

def cmd_policies_list(args) -> int:
    def run(s: Session) -> None:
        data = s.get("/api/policies", params={"filter": args.filter})
        rows = [(p.get("name"), state("enabled" if p.get("enabled", True) else "disabled"),
                 p.get("mode") or "enforce", (p.get("about") or "")[:60])
                for p in data.get("policies", [])]
        emit(_fmt(args), {"policies": data.get("policies", [])},
             ("name", "state", "mode", "about"), rows)
    return _run(args, run)


def cmd_policies_get(args) -> int:
    def run(s: Session) -> None:
        emit(_fmt(args), s.get(f"/api/policies/{q(args.name)}",
                               not_found=f"no such policy {args.name!r}"))
    return _run(args, run)


def cmd_policies_apply(args) -> int:
    """A policy file: gitops Policy documents, or a bare {name, body, …}."""
    import yaml
    path = Path(args.file)
    try:
        raw = list(yaml.safe_load_all(sys.stdin.read() if args.file == "-"
                                      else path.read_text(encoding="utf-8")))
    except OSError as e:
        raise CliError(f"{args.file}: {e.strerror or e}", code=EXIT_INVALID) from None
    docs = []
    for d in raw:
        if not isinstance(d, dict):
            continue
        if d.get("kind") == "Policy":
            docs.append(dict(d, _file=args.file))
        elif d.get("name"):
            spec = {k: v for k, v in d.items() if k != "name"}
            docs.append(dict(gitops.doc("Policy", d["name"], spec), _file=args.file))
        else:
            raise CliError(f"{args.file}: expected kind: Policy documents or a mapping with "
                           "`name` and `body`", code=EXIT_INVALID)
    return _run(args, lambda s: _report_apply(args, gitops.apply(s, docs, args.dry_run,
                                                                 args.reason)))


# The built-in templates (policy.TEMPLATES) by the names the command takes:
# `readonly` is the server's read_only.
POLICY_TEMPLATES = {"readonly": "read_only", "read_only": "read_only",
                    "sandboxed": "sandboxed", "standard": "standard", "full": "full"}
# What each template implies for the agent's OWN reach (--agent-tools), the
# other side of the bundle its people get. A template is what a PERSON may do
# with the agent (policy.TEMPLATES: read; read and run; run and reconfigure;
# everything) — Cedar's call_tool and call_model are what the agent itself
# may do, decided by separate policies with the agent as principal:
#   readonly, sandboxed  the agent may call none of its attached servers'
#                        tools — it answers from its model alone
#   standard             it may call its attached servers' tools
#   full                 that, and its bound LLM provider by name
AGENT_TOOL_EFFECT = {"read_only": "forbid", "sandboxed": "forbid", "standard": "permit",
                     "full": "permit"}
_PRINCIPAL_KINDS = ("user", "group", "role")


def _principal(text: str) -> dict[str, str] | None:
    """--principal any | user:ID | group:ID | role:ID → the link's slot, or
    None for anyone."""
    text = (text or "any").strip()
    if text == "any":
        return None
    kind, sep, ident = text.partition(":")
    if not sep or kind not in _PRINCIPAL_KINDS or not ident.strip():
        raise CliError(f"--principal {text!r}: use any, user:NAME, group:NAME or role:NAME",
                       code=EXIT_INVALID)
    return {"kind": kind, "id": ident.strip()}


def _slug(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9-]+", "-", text.lower()).strip("-")[:40] or "x"


def _policy_drafts(s: Session, args, template: str,
                   principal: dict[str, str] | None) -> list[dict[str, Any]]:
    """The policies `policies create` writes: the template bound to the
    agent for its people, and — with --agent-tools — one per attached MCP
    server (and, for full, the bound provider) for the agent itself. Each is
    one Cedar statement, as the server stores them; each draft carries the
    builder spec it compiles to, which /policies/analyze reads."""
    drafts = [{"name": args.name, "side": "people",
               "body": {"name": args.name,
                        "template_link": {"template": template,
                                          "resource": {"kind": "agent", "id": args.agent},
                                          **({"principal": principal} if principal else {})},
                        "about": args.about or (f"{template} access to {args.agent} for "
                                                + (f"{principal['kind']} {principal['id']}"
                                                   if principal else "anyone"))},
               "spec": {"effect": "permit", "template": template,
                        "principal": principal or {"kind": "any", "id": ""},
                        "resource": {"kind": "agent", "id": args.agent}, "conditions": []}}]
    if not args.agent_tools:
        return drafts
    runtime = s.get(f"/api/agents/{q(args.agent)}/runtime",
                    not_found=f"no such agent {args.agent!r}")
    servers = list(((runtime.get("config") or {}).get("mcp_servers")) or [])
    effect = AGENT_TOOL_EFFECT[template]
    agent = {"kind": "agent", "id": args.agent}

    def own(name: str, action: str, resource: str, about: str) -> dict[str, Any]:
        spec = {"effect": effect, "principal": agent, "actions": [action],
                "resource": {"id": resource}}
        return {"name": name, "side": "agent",
                "body": {"name": name, "spec": spec, "about": about}, "spec": spec}

    for server in servers:
        drafts.append(own(f"{args.name}-tools-{_slug(server)}", "call_tool", server,
                          f"{args.agent} {'may' if effect == 'permit' else 'may not'} call "
                          f"{server}'s tools ({template})"))
    if not servers:
        note(f"{args.agent} has no MCP server attached — no tool policy to write")
    if template == "full":
        found = [a for a in s.get("/api/agents").get("agents", []) if a.get("key") == args.agent]
        provider = ((found[0].get("effective") or {}).get("provider") if found else "") or ""
        if provider and provider != "global":
            drafts.append(own(f"{args.name}-model-{_slug(provider)}", "call_model", provider,
                              f"{args.agent} may call LLM provider {provider} (full)"))
    return drafts


def _impact(s: Session, draft: dict[str, Any]) -> dict[str, Any]:
    """/policies/analyze on one draft: who gains and loses what, and whether
    it leaves an agent no owner may configure or contain. {} when the
    server cannot answer (an older server, or no permission to analyse) —
    the caller decides whether that may stand."""
    r = s.request("POST", "/api/policies/analyze",
                  json={"draft": {"name": draft["name"], "spec": draft["spec"]}}, check=False)
    if r.status_code != 200:
        return {}
    return r.json() or {}


def _collateral(impact: dict[str, Any], agent: str) -> list[str]:
    """The principals other than `agent` an agent-side draft takes access
    from. A policy that names a server or provider governs it for every
    agent (policy.governs), so a permit for one agent is, for every other
    agent using that server with no permit of its own, a loss."""
    out = []
    for row in impact.get("diff") or []:
        p = row.get("principal") or {}
        if p.get("kind") == "Agent" and p.get("id") == agent:
            continue
        if row.get("lost_count"):
            what = ", ".join(f"{x['action']} {x['resource']['type']} {x['resource']['id']}"
                             for x in row.get("lost") or [])
            out.append(f"{p.get('kind')} {p.get('id')} loses {row['lost_count']}: {what}")
    return out


def cmd_policies_create(args) -> int:
    """Bind a built-in template to an agent: what PEOPLE may do with it, and,
    with --agent-tools, what the agent may reach itself (AGENT_TOOL_EFFECT).
    Every draft is analysed first (/policies/analyze): a lockout, or an
    agent-side policy that takes a server or provider from another agent,
    is refused without --yes."""
    template = POLICY_TEMPLATES[args.template]
    principal = _principal(args.principal)

    def run(s: Session) -> int:
        drafts = _policy_drafts(s, args, template, principal)
        problems: list[str] = []
        rows = []
        for d in drafts:
            impact = _impact(s, d)
            gained = sum(r.get("gained_count", 0) for r in impact.get("diff") or [])
            lost = sum(r.get("lost_count", 0) for r in impact.get("diff") or [])
            if not impact:
                if d["side"] == "agent":
                    problems.append(f"{d['name']}: the server could not analyse it, so whether "
                                    "it takes a server from another agent is unknown")
                shown = "not analysed"
            elif "diff" not in impact:
                shown = "who gains and loses is withheld (needs access.read)"
                if d["side"] == "agent":
                    problems.append(f"{d['name']}: {shown}")
            else:
                shown = f"+{gained} / -{lost} permissions"
            if impact.get("lockout"):
                problems.append(f"{d['name']}: leaves an agent no owner may configure or contain")
            if d["side"] == "agent":
                problems += [f"{d['name']}: {c}" for c in _collateral(impact, args.agent)]
            rows.append((d["name"], d["side"], d["spec"].get("effect"),
                         ",".join(d["spec"].get("actions") or [template]),
                         (d["spec"].get("resource") or {}).get("id"), shown))
        for p_ in problems:
            note(paint(f"! {p_}", "yellow"))
        if problems and not args.yes and not args.dry_run:
            raise CliError("not created — review the impact above, then pass --yes to create "
                           "the policies anyway", code=EXIT_INVALID)
        if args.dry_run:
            emit(_fmt(args), {"dry_run": True, "policies": [d["body"] for d in drafts],
                              "warnings": problems},
                 ("policy", "for", "effect", "actions", "resource", "impact"), rows)
            return EXIT_PENDING
        created = []
        for d in drafts:
            created.append(s.post("/api/policies", {**d["body"], "reason": args.reason}))
        if _fmt(args) != "table":
            emit(_fmt(args), {"policies": created, "warnings": problems})
        else:
            emit("table", created, ("policy", "for", "effect", "actions", "resource", "impact"),
                 rows)
            who = f"{principal['kind']} {principal['id']}" if principal else "anyone"
            note(f"{who} now has {template} access to {args.agent}; {args.agent} is governed "
                 f"from here on — people without a permit lose what their roles gave them.")
            if args.agent_tools:
                note(f"{args.agent}'s own tool calls: "
                     + ("refused on its attached servers" if AGENT_TOOL_EFFECT[template]
                        == "forbid" else "permitted on its attached servers")
                     + ". Those servers are governed for every agent now.")
            else:
                note(f"{args.agent}'s own tool and model calls are unchanged (a template is "
                     f"what people may do with it); --agent-tools bounds them too.")
        return EXIT_OK
    return _run(args, run)


# ---- audit ----

def cmd_audit_search(args) -> int:
    def run(s: Session) -> None:
        params: dict[str, Any] = {"q": " ".join(args.query), "limit": args.limit,
                                  "offset": args.offset, "facets": "false",
                                  "timeline": "false", "order": args.order}
        if args.since:
            params["since"] = since_timestamp(args.since)
            params["window"] = "all"
        if args.until:
            params["until"] = since_timestamp(args.until)
        data = s.get("/api/audit/query", params=params)
        rows = [(e.get("ts"), e.get("actor"), e.get("action"),
                 state(e.get("outcome") or (e.get("detail") or {}).get("outcome") or "-"),
                 e.get("subsystem") or e.get("resource") or "-",
                 json.dumps(e.get("detail") or {}, sort_keys=True, default=str)[:60])
                for e in data.get("events", [])]
        emit(_fmt(args), data, ("time", "actor", "action", "outcome", "subsystem", "detail"),
             rows)
        if _fmt(args) == "table":
            note(f"{len(rows)} of {data.get('total', len(rows))} events"
                 + (f" since {params['since']}" if args.since else ""))
    return _run(args, run)


def cmd_audit_verify(args) -> int:
    """Offline, no server — tiq's verifier as it is."""
    ns = argparse.Namespace(bundle=args.bundle, audit_keys=args.audit_keys,
                            fingerprint=args.fingerprint)
    return tiq.cmd_audit_verify(ns)


# ---- budgets ----

def cmd_budgets_list(args) -> int:
    def run(s: Session) -> None:
        data = s.get("/api/budgets")
        rows = [(agent, st.get("status"), f"{st.get('spent_usd', 0):.2f}",
                 f"{st.get('limit_usd', 0):.2f}" if st.get("limit_usd") else "uncapped",
                 st.get("period"), st.get("period_resets_at"))
                for agent, st in sorted((data.get("state") or {}).items())]
        emit(_fmt(args), data, ("agent", "status", "spent $", "limit $", "period", "resets"),
             rows)
    return _run(args, run)


def cmd_budgets_set(args) -> int:
    def run(s: Session) -> None:
        body = {"limit_usd": args.limit, "period": args.period, "agent": args.agent,
                "warn_pct": args.warn_pct}
        out = s.put("/api/budgets", body)
        emit(_fmt(args), out) if _fmt(args) != "table" else note(
            f"budget for {args.agent or 'default'}: ${args.limit:g}/{args.period}"
            + (f", warn at {args.warn_pct:g}%" if args.warn_pct else ""))
    return _run(args, run)


# ---- tenant solutions ----
#
# Which solutions a tenant has (IT service desk, SAP, HR, Finance). TENANT ""
# is the instance's own row: every tenant without one, and the only row a
# single-tenant install has.

def _solutions_path(tenant: str) -> str:
    return f"/api/tenants/{q(tenant)}/solutions" if tenant else "/api/instance/solutions"


def _solutions_table(args, data: dict[str, Any]) -> None:
    mods = data.get("modules") or {}
    rows = [(s, ", ".join(mods.get(s) or []) or "—") for s in data.get("solutions") or []]
    emit(_fmt(args), data, ("solution", "modules"), rows)
    if _fmt(args) == "table":
        whose = {"tenant": "its own row", "instance": "the instance's row",
                 "default": "no row: every GA solution"}.get(data.get("from"), "")
        cap = data.get("ceiling")
        note(f"{data.get('tenant') or '(instance)'}: {whose}"
             + (f"; deployment ceiling {','.join(cap)}" if cap else ""))


def cmd_tenant_solutions_show(args) -> int:
    def run(s: Session) -> None:
        _solutions_table(args, s.get(_solutions_path(args.tenant), not_found=(
            f"no such tenant: {args.tenant}")))
    return _run(args, run)


def cmd_tenant_solutions_set(args) -> int:
    if args.default == bool(args.solutions):
        raise CliError("name the solutions (e.g. itsm sap sap.s4), or --default to remove "
                       "the row", code=EXIT_INVALID)

    def run(s: Session) -> None:
        # The tenant is named on the command line, which is the "typed again"
        # a change turning something off asks for (confirm_id).
        body = {"solutions": None if args.default else args.solutions, "reason": args.reason,
                "plan": args.plan or "", "confirm_id": args.tenant}
        path = _solutions_path(args.tenant) + ("?dry_run=true" if args.dry_run else "")
        data = s.put(path, body, not_found=f"no such tenant: {args.tenant}")
        _solutions_table(args, data)
        if _fmt(args) == "table":
            imp = data.get("impact") or {}
            if imp.get("turned_on") or imp.get("turned_off"):
                note(f"{'would turn' if args.dry_run else 'turned'} on: "
                     f"{', '.join(imp.get('turned_on') or []) or '—'}; off: "
                     f"{', '.join(imp.get('turned_off') or []) or '—'} (no data is deleted)")
    return _run(args, run)


def cmd_tenant_solutions_infer(args) -> int:
    """What each tenant's use suggests its row should be; --apply writes the
    proposals, each through PUT …/solutions with the reason "migration
    infer" (audited). Never proposes taking away what a tenant uses."""
    def run(s: Session) -> None:
        data = s.get("/api/tenants/solutions/infer")
        rows = [(p["tenant"], ", ".join(p["current"]) or "—", ", ".join(p["keys"]) or "—",
                 ", ".join(p["would_remove"]) or "—",
                 "; ".join(f"{k}: {', '.join(v)}" for k, v in p["ambiguous"].items()) or "—")
                for p in data.get("tenants") or []]
        emit(_fmt(args), data, ("tenant", "now", "proposed", "would turn off", "ambiguous"),
             rows)
        if not args.apply:
            if _fmt(args) == "table":
                note("dry run: nothing written (--apply writes each proposal, audited)")
            return
        for p in data.get("tenants") or []:
            if sorted(p["keys"]) == sorted(p["current"]) and not p["would_remove"]:
                continue
            s.put(f"/api/tenants/{q(p['tenant'])}/solutions",
                  {"solutions": p["keys"], "reason": "migration infer",
                   "confirm_id": p["tenant"]},
                  not_found=f"no such tenant: {p['tenant']}")
            if _fmt(args) == "table":
                note(f"{p['tenant']}: wrote {', '.join(p['keys'])}")
    return _run(args, run)


def cmd_tenant_adopt_legacy(args) -> int:
    """Adopt the instance's legacy (unstamped) history into a home tenant
    (POST /api/tenants/{id}/adopt-legacy). --dry-run counts every step and
    writes nothing; without it the run is applied, audited as
    tenant.legacy.adopt."""
    if not args.dry_run and not str(args.reason or "").strip():
        raise CliError("adopting changes who can read the instance's history: give --reason",
                       code=EXIT_INVALID)

    def run(s: Session) -> None:
        body = {"dry_run": bool(args.dry_run), "reason": args.reason or "",
                "triggers": args.triggers, "grant_users": not args.no_grant_users,
                "adopt_sources": not args.no_sources, "confirm": args.tenant}
        data = s.post(f"/api/tenants/{q(args.tenant)}/adopt-legacy", body,
                      not_found=f"no such tenant: {args.tenant}")
        rows = [(k, v) for k, v in (data.get("records") or {}).items()]
        emit(_fmt(args), data, ("records", "count"), rows)
        if _fmt(args) == "table":
            note(f"{'DRY RUN — nothing written' if data.get('dry_run') else 'applied'}: "
                 f"{data.get('records_total', 0)} record(s) into {data.get('tenant')}; "
                 f"audit rows up to id {data.get('audit_rows_readable_up_to_id')} readable "
                 f"there; cut-off {data.get('cutoff')}")
            note("triggers bound: " + (", ".join(data.get("triggers_bound") or []) or "none"))
            note("accounts granted: " + (", ".join(data.get("users_granted") or []) or "none"))
            note("sources claimed: " + (", ".join(data.get("sources_claimed") or []) or "none")
                 + ("; the unsourced intake" if data.get("unsourced_intake_claimed") else ""))
            if data.get("deflection_bound"):
                note("the deflection door (/api/answer, Teams outgoing) bound to it")
            if data.get("pending_reask"):
                note(f"{data['pending_reask']} pending SAP confirmation(s) will have to be "
                     "asked again")
    return _run(args, run)


# ---- connectors ----

def _connectors(s: Session) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    r = s.request("GET", "/api/integrations", check=False)
    if r.status_code == 200:
        for i in r.json().get("integrations") or []:
            out.append({"name": i.get("name") or i.get("id"), "id": i.get("id"),
                        "type": i.get("kind", "webhook"), "family": "integration",
                        "enabled": i.get("enabled", True),
                        "detail": ",".join(i.get("events") or [])})
    r = s.request("GET", "/api/mcp/servers", check=False)
    if r.status_code == 200:
        for name, m in sorted((r.json().get("servers") or {}).items()):
            out.append({"name": name, "id": name,
                        "type": m.get("managed_type") or m.get("template") or m.get("transport"),
                        "family": "mcp", "enabled": not m.get("paused") and m.get("enabled", True),
                        "detail": m.get("url") or m.get("about") or ""})
    r = s.request("GET", "/api/integrations/teams-inbound", check=False)
    if r.status_code == 200:
        t = r.json()
        if t.get("configured") or t.get("enabled"):
            out.append({"name": "teams-inbound", "id": "teams-inbound", "type": "teams",
                        "family": "channel", "enabled": t.get("enabled", True), "detail": ""})
    return out


def cmd_connectors_list(args) -> int:
    def run(s: Session) -> None:
        cons = _connectors(s)
        emit(_fmt(args), {"connectors": cons}, ("name", "type", "family", "state", "detail"),
             [(c["name"], c["type"], c["family"],
               state("enabled" if c["enabled"] else "disabled"), c["detail"]) for c in cons])
    return _run(args, run)


def cmd_connectors_test(args) -> int:
    def run(s: Session) -> int:
        match = [c for c in _connectors(s) if args.name in (c["name"], c["id"])]
        if not match:
            raise CliError(f"no connector {args.name!r} — `liya connectors list` shows them",
                           code=EXIT_NOT_FOUND)
        c = match[0]
        if c["family"] == "integration":
            r = s.request("POST", f"/api/integrations/{q(c['id'])}/test", json={}, check=False)
        elif c["family"] == "mcp":
            r = s.request("GET", f"/api/mcp/servers/{q(c['id'])}/tools", check=False)
        else:
            r = s.request("GET", "/api/integrations/teams-inbound", check=False)
        body = r.json() if r.content else {}
        ok = r.status_code < 400 and body.get("ok", True) is not False
        detail = (body.get("error") or body.get("detail") or
                  (f"{len(body.get('tools') or [])} tools" if c["family"] == "mcp" else
                   body.get("status") or ""))
        emit(_fmt(args), {"connector": c, "status_code": r.status_code, "result": body},
             ("connector", "type", "result", "detail"),
             [(c["name"], c["type"], state("pass" if ok else "fail"), detail)])
        return EXIT_OK if ok else EXIT_ERROR
    return _run(args, run)


# ---- knowledge base ----

def cmd_kb_search(args) -> int:
    def run(s: Session) -> None:
        data = s.get("/api/files/search", params={"q": " ".join(args.query),
                                                  "limit": args.limit})
        rows = [(h.get("score") and f"{h['score']:.3f}", h.get("title") or h.get("file")
                 or h.get("name") or h.get("source"),
                 (h.get("snippet") or h.get("text") or "")[:80])
                for h in data.get("hits", [])]
        emit(_fmt(args), data, ("score", "source", "snippet"), rows)
    return _run(args, run)


# ---- status & doctor (the command center) ----

def _status(s: Session) -> dict[str, Any]:
    out: dict[str, Any] = {"env": s.env, "url": s.url}
    health = s.get("/api/health", auth=bool(s.token_source()[0]), check=False)
    out["gateway"] = {"status_code": health.status_code,
                      **(health.json() if health.content else {})}
    if not s.token_source()[0]:
        return out
    try:
        out["whoami"] = s.get("/api/me")
    except CliError as e:
        out["whoami"] = {"error": str(e)}
        return out
    for key, path in (("providers", "/api/llm/provider-health"),
                      ("breakers", "/api/llm/breakers"),
                      ("kill_switches", "/api/kill-switches"),
                      ("agents", "/api/agents")):
        r = s.request("GET", path, check=False)
        out[key] = r.json() if r.status_code == 200 else {"status_code": r.status_code}
    out["connectors"] = _connectors(s)
    return out


def cmd_status(args) -> int:
    def run(s: Session) -> int:
        st = _status(s)
        if _fmt(args) != "table":
            emit(_fmt(args), st)
            return EXIT_OK if st["gateway"].get("status") == "ok" else EXIT_ERROR
        g = st["gateway"]
        who = st.get("whoami") or {}
        print(paint(f"Liyagent command center — {s.env} ({s.url})", "bold"))
        if who.get("username"):
            print(f"signed in as {who['username']} [{who.get('role')}]")
        elif "whoami" not in st:
            print(paint("not logged in — showing public health only (liya auth login)", "yellow"))
        rows = [("gateway", state(g.get("status", "down")),
                 f"v{g['version']}" if g.get("version") else f"HTTP {g.get('status_code')}"),
                ("database", state("ok" if g.get("db_ok") else "down"),
                 (g.get("db") or {}).get("engine", "") + (
                     f" {(g.get('db') or {}).get('latency_ms')}ms"
                     if (g.get("db") or {}).get("latency_ms") is not None else "")),
                ("vector store", state("ok" if g.get("vector_ok") else "down"),
                 g.get("embedding_backend") or "")]
        llm = (g.get("llm") or {}).get("backend")
        if llm:
            rows.append(("llm backend", state("disabled" if llm == "disabled" else "ok"), llm))
        if "whoami" in st:
            provs = (st.get("providers") or {}).get("providers") or {}
            breakers = (st.get("breakers") or {}).get("breakers") or {}
            open_ = [n for n, b in breakers.items() if (b or {}).get("state") == "open"]
            unhealthy = [n for n, p in provs.items()
                         if (p or {}).get("state") not in (None, "healthy", "ok")]
            # Nothing to call: no provider saved and the global backend off.
            empty = not provs and llm in (None, "", "disabled")
            rows.append(("model chain",
                         state("degraded" if (open_ or unhealthy or empty) else "ok"),
                         ("no provider configured and the global backend is disabled"
                          if empty else f"{len(provs)} providers")
                         + (f", open breakers: {', '.join(open_)}" if open_ else "")
                         + (f", unhealthy: {', '.join(unhealthy)}" if unhealthy else "")))
            for n, p in sorted(provs.items()):
                rows.append((f"  provider {n}", state((p or {}).get("state") or "-"),
                             (p or {}).get("reason") or ""))
            cons = st.get("connectors") or []
            rows.append(("connectors", state("ok" if all(c["enabled"] for c in cons) else
                                             "degraded"),
                         f"{len(cons)} configured" if cons else "none configured"))
            for c in cons:
                rows.append((f"  {c['type']} {c['name']}",
                             state("enabled" if c["enabled"] else "disabled"), c["detail"]))
            agents = (st.get("agents") or {}).get("agents") or []
            ks = st.get("kill_switches") or {}
            engaged = ks.get("engaged") or []
            rows.append(("agents", state("ok"), f"{len(agents)} registered, "
                         f"{sum(1 for a in agents if a.get('llm'))} model-driven"))
            rows.append(("kill switches", state("open" if engaged else "ok"),
                         f"{len(engaged)} engaged" if engaged else "none engaged"))
        for w in g.get("warnings") or ([g["warning"]] if g.get("warning") else []):
            rows.append(("warning", state("warn"), w))
        print(emit_table(("component", "state", "detail"), rows))
        return EXIT_OK if g.get("status") == "ok" else EXIT_ERROR
    return _run(args, run)


def emit_table(header, rows) -> str:
    from .output import render_table
    return render_table(header, rows, max_width=90)


def cmd_doctor(args) -> int:
    checks: list[tuple[str, str, str]] = []

    def add(name: str, ok: str, detail: str) -> None:
        checks.append((name, ok, detail))

    import platform
    add("python", "ok" if sys.version_info >= (3, 10) else "fail", platform.python_version())
    for mod in ("httpx", "yaml"):
        try:
            __import__(mod)
            add(f"module {mod}", "ok", "installed")
        except ImportError:
            add(f"module {mod}", "fail", "missing — pip install " +
                ("pyyaml" if mod == "yaml" else mod))
    h = config.home()
    add("config dir", "ok" if h.exists() else "warn",
        f"{h}" + ("" if h.exists() else " (created on first login)"))
    mode = config.credentials_mode()
    if mode is None:
        add("credentials file", "warn", "none yet — liya auth login")
    else:
        add("credentials file", "ok" if mode & 0o077 == 0 else "fail",
            f"mode {oct(mode)}" + ("" if mode & 0o077 == 0 else
                                   f" — too open; chmod 600 {config.credentials_path()}"))
    if "NO_COLOR" in os.environ:
        add("colour", "ok", "disabled by NO_COLOR")
    s = _session(args)
    try:
        add("environment", "ok", f"{s.env} → {s.url}")
        if s.url.startswith("http://") and not any(
                h_ in s.url for h_ in ("127.0.0.1", "localhost", "[::1]")):
            add("transport", "warn", "plain http to a non-local host: tokens travel unencrypted")
        t0 = time.monotonic()
        try:
            r = s.anonymous().get("/api/health")
            ms = (time.monotonic() - t0) * 1000
            add("reachability", "ok" if r.status_code in (200, 503) else "fail",
                f"HTTP {r.status_code} in {ms:.0f} ms")
            add("server health", state_word(r.json().get("status") if r.content else "down"),
                r.json().get("status", "?") if r.content else "no body")
        except Exception as e:
            add("reachability", "fail", f"{e.__class__.__name__}: {e}")
        else:
            token, source = s.token_source()
            if not token:
                add("auth", "warn", "not logged in — liya auth login")
            else:
                try:
                    me = s.get("/api/me")
                    add("auth", "ok", f"{me.get('username')} [{me.get('role')}] via "
                        f"{config.token_kind(token)} from {source}")
                    hh = s.get("/api/health")
                    from . import __version__
                    sv = hh.get("version") or "?"
                    add("version", "ok" if sv == __version__ else "warn",
                        f"client {__version__}, server {sv}")
                    spec = s.openapi()
                    add("api schema", "ok" if spec.get("paths") else "warn",
                        f"{len(spec.get('paths') or {})} endpoints" if spec.get("paths")
                        else "openapi.json unavailable; unsupported-feature checks are off")
                except CliError as e:
                    add("auth", "fail", str(e))
    finally:
        s.close()
    emit(_fmt(args), [{"check": c, "result": r, "detail": d} for c, r, d in checks],
         ("check", "result", "detail"), [(c, state(r), d) for c, r, d in checks])
    return EXIT_ERROR if any(r == "fail" for _, r, _ in checks) else EXIT_OK


def state_word(status: str | None) -> str:
    return {"ok": "ok", "degraded": "warn"}.get(status or "", "fail")


# ---- gitops ----

def _report_apply(args, out: dict[str, Any]) -> int:
    rows = [(r["resource"], state(r["action"]) if r["action"] in ("refused", "skipped")
             else paint(r["action"], {"create": "green", "update": "yellow"}.get(r["action"],
                                                                                  "dim")),
             r["detail"]) for r in out["results"]]
    emit(_fmt(args), out, ("resource", "plan" if out["dry_run"] else "result", "detail"), rows)
    if _fmt(args) == "table":
        summ = ", ".join(f"{n} {k}" for k, n in sorted(out["summary"].items())) or "nothing"
        note(("dry run: " if out["dry_run"] else "applied: ") + summ)
    if out["summary"].get("refused"):
        return EXIT_ERROR
    if out["dry_run"] and (out["summary"].get("create") or out["summary"].get("update")):
        return EXIT_PENDING
    return EXIT_OK


def cmd_apply(args) -> int:
    docs = gitops.load(Path(args.file))
    return _run(args, lambda s: _report_apply(args, gitops.apply(s, docs, args.dry_run,
                                                                 args.reason)))


def cmd_export(args) -> int:
    def run(s: Session) -> None:
        out = gitops.export(s, Path(args.dir), args.kind)
        rows = [(k, len(v), ", ".join(v)[:70]) for k, v in out["written"].items()]
        rows += [(k, 0, why) for k, why in out["skipped"].items()]
        emit(_fmt(args), out, ("kind", "count", "names"), rows)
        if _fmt(args) == "table":
            note(f"wrote {sum(len(v) for v in out['written'].values())} files under "
                 f"{out['directory']} (no secret values)")
    return _run(args, run)


# ---- run: a coding agent, through the gateway ----

def cmd_run_claude(args) -> int:
    """Claude Code with every model call through the AI gateway, as one
    agent's governed calls (runclaude says what is refused, and why)."""
    from . import runclaude

    def run(s: Session) -> int:
        gateway_url = s.url + runclaude.GATEWAY_PATH
        refusals, warnings = runclaude.check_settings(
            runclaude.settings_files(Path.cwd(), Path.home()), gateway_url)
        for w in warnings:
            note(paint(f"! {w}", "yellow"))
        if refusals:
            for r_ in refusals:
                note(paint(f"x {r_}", "red"))
            raise CliError("not started: Claude Code would call its model around the gateway",
                           code=EXIT_INVALID)
        claude = runclaude.find_claude(args.claude_bin)
        if not claude:
            raise CliError("Claude Code not found — install it (npm install -g "
                           "@anthropic-ai/claude-code), or pass --claude-bin PATH",
                           code=EXIT_NOT_FOUND)
        token, where = _gateway_token(s, args)
        env, cleared = runclaude.child_env(dict(os.environ), gateway_url, token)
        rest = list(args.claude_args)
        argv = [claude, *(rest[1:] if rest[:1] == ["--"] else rest)]
        if cleared:
            note(f"started without {', '.join(cleared)} from this shell: its calls go "
                 "through the gateway instead")
        note(f"Claude Code → {gateway_url} as agent token from {where}")
        if args.dry_run:
            shown = {"ANTHROPIC_BASE_URL": gateway_url, "ANTHROPIC_AUTH_TOKEN": "***"}
            emit(_fmt(args), {"command": argv, "env": shown, "cleared": cleared},
                 ("variable", "value"), [*shown.items(), ("command", " ".join(argv))])
            return EXIT_OK
        return runclaude.launch(argv, env)
    return _run(args, run)


def _gateway_token(s: Session, args) -> tuple[str, str]:
    """The agent's gateway token, and where it came from: LIYA_GATEWAY_TOKEN,
    stdin, or minted for --agent — which replaces the agent's current token,
    so it is confirmed first (or --yes)."""
    if os.environ.get("LIYA_GATEWAY_TOKEN"):
        return os.environ["LIYA_GATEWAY_TOKEN"], "LIYA_GATEWAY_TOKEN"
    if args.token_stdin:
        return _read_secret("Gateway token: ", True), "stdin"
    if not args.agent:
        raise CliError("no gateway token — set LIYA_GATEWAY_TOKEN, pass --token-stdin, or "
                       "--agent NAME to mint one", code=EXIT_INVALID)
    if not args.yes:
        if not sys.stdin.isatty():
            raise CliError(f"minting a token replaces {args.agent}'s current one — pass --yes "
                           "to confirm, or use LIYA_GATEWAY_TOKEN", code=EXIT_INVALID)
        _confirm(args, f"Mint a new gateway token for {args.agent} (its current token stops "
                       "working)")
    out = s.post(f"/api/gateway/agents/{q(args.agent)}/token", {"ttl_hours": args.ttl_hours},
                 not_found=f"no such agent {args.agent!r}")
    return out["token"], f"a new {out.get('ttl_hours', args.ttl_hours)}h token for {args.agent}"


# ---- misc ----

def cmd_version(args) -> int:
    from . import __version__
    info: dict[str, Any] = {"client": __version__, "server": None}
    s = _session(args)
    try:
        info["env"], info["url"] = s.env, s.url
        try:
            h = s.get("/api/health", auth=bool(s.token_source()[0]), check=False)
            info["server"] = (h.json() or {}).get("version") if h.content else None
        except Exception:
            pass
    finally:
        s.close()
    if _fmt(args) == "table":
        print(f"liya {__version__}" + (f" (server {info['server']} at {s.url})"
                                       if info["server"] else ""))
    else:
        emit(_fmt(args), info)
    return EXIT_OK


def cmd_completion(args) -> int:
    tree = _command_tree(build_parser())
    print(_bash_completion(tree) if args.shell == "bash" else _zsh_completion(tree))
    return EXIT_OK


def cmd_tiq(args) -> int:
    return _forward_tiq(args.rest, args)


def _forward_tiq(rest: list[str], args=None) -> int:
    """Hand a `tiq` verb to tiq.main, with liya's environment and stored
    credential filled in where the caller gave none."""
    argv = list(rest)
    if "--url" not in argv and not os.environ.get("TICKETIQ_URL"):
        try:
            s = Session(env=getattr(args, "env", None), url=getattr(args, "url", None))
            argv = ["--url", s.url] + argv
            if not any(a in argv for a in ("--token", "--user")) and not (
                    os.environ.get("TICKETIQ_TOKEN") or os.environ.get("TICKETIQ_CLI_USER")):
                token, _ = s.token_source()
                if token:
                    os.environ["TICKETIQ_TOKEN"] = token  # this process only, never argv
        except CliError:
            pass
    return tiq.main(argv)


# ---- the parser ----

def _out_parent() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("-o", "--output", choices=FORMATS, default=argparse.SUPPRESS,
                   help="output format: table (default), json or yaml")
    return p


def _conn_parent() -> argparse.ArgumentParser:
    """-o plus --env/--url, accepted after the subcommand as well as before it."""
    p = _out_parent()
    p.add_argument("--env", default=argparse.SUPPRESS, help="environment to use")
    p.add_argument("--url", default=argparse.SUPPRESS, help="instance URL override")
    return p


def build_parser() -> argparse.ArgumentParser:
    out_only = _out_parent()
    out = _conn_parent()
    p = argparse.ArgumentParser(
        prog=PROG, parents=[out_only],
        description="liya — the Liyagent / TicketIQ command line. Every command calls the "
                    "same REST API as the web console.",
        epilog="Environment: LIYA_TOKEN, LIYA_ENV, LIYA_URL, LIYA_HOME (default ~/.liya), "
               "LIYA_OUTPUT, NO_COLOR. Run `liya COMMAND --help` for details.")
    p.add_argument("--env", default=None, help="environment to use (default: the current one)")
    p.add_argument("--url", default=None, help="instance URL, overriding the environment's")
    p.add_argument("--token", default=None, help=argparse.SUPPRESS)  # prefer LIYA_TOKEN
    p.add_argument("--timeout", type=float, default=120.0, help="HTTP timeout in seconds")
    p.add_argument("--no-color", action="store_true", help="disable colour (same as NO_COLOR)")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="log each request's method, URL, status and latency to stderr "
                        "(never headers or secrets); LIYA_VERBOSE=1 too")
    p.add_argument("--version", action="store_true", help="print the client version and exit")
    sub = p.add_subparsers(dest="command", metavar="COMMAND")

    def group(name: str, help_: str) -> argparse._SubParsersAction:
        g = sub.add_parser(name, help=help_, description=help_)
        gs = g.add_subparsers(dest=f"{name}_command", metavar="SUBCOMMAND")
        g.set_defaults(fn=lambda a, g=g: (g.print_help(), EXIT_ERROR)[1])
        return gs

    def cmd(gs, name: str, fn, help_: str, **kw) -> argparse.ArgumentParser:
        c = gs.add_parser(name, help=help_, description=kw.pop("description", help_),
                          parents=[kw.pop("parent", out)], **kw)
        c.set_defaults(fn=fn)
        return c

    # auth
    g = group("auth", "log in, log out, and show who you are")
    c = cmd(g, "login", cmd_auth_login, "store a credential for the current environment",
            description="Log in to the current environment. Uses the server's device-code "
                        "flow when it offers one; otherwise reads LIYA_TOKEN, a token from "
                        "stdin (--token-stdin), or a hidden prompt. --username signs in with a "
                        "password (hidden prompt) and stores the resulting session, never the "
                        "password. Service-account tokens (svc/NAME:SECRET) are accepted.")
    c.add_argument("--username", default="", help="sign in as this user (password prompted)")
    c.add_argument("--token-stdin", action="store_true", help="read the token from stdin")
    c.add_argument("--password-stdin", action="store_true",
                   help="read the password from stdin (with --username)")
    cmd(g, "logout", cmd_auth_logout, "forget the current environment's credential")
    cmd(g, "status", cmd_auth_status, "show who you are signed in as (never the token)")

    # env
    g = group("env", "manage environments (instances)")
    cmd(g, "list", cmd_env_list, "list environments; * marks the current one")
    c = cmd(g, "use", cmd_env_use, "switch the current environment")
    c.add_argument("name")
    c = cmd(g, "add", cmd_env_add, "add or update an environment", parent=out_only)
    c.add_argument("name")
    c.add_argument("--url", required=True, dest="url", help="base URL, e.g. https://x.example")
    c.add_argument("--use", action="store_true", help="also switch to it")
    c = cmd(g, "remove", cmd_env_remove, "remove an environment and its credential")
    c.add_argument("name")

    # agents
    g = group("agents", "list, configure and talk to agents")
    c = cmd(g, "list", cmd_agents_list, "list agents and their model bindings")
    c.add_argument("--stage", default="", help="only agents in this stage")
    c = cmd(g, "get", cmd_agents_get, "show one agent")
    c.add_argument("id")
    c = cmd(g, "create", cmd_agents_create, "create an agent from a blueprint")
    c.add_argument("name", nargs="?", default="", help="new agent id (default: blueprint's)")
    c.add_argument("--from-blueprint", required=True, metavar="BLUEPRINT")
    c.add_argument("--provider", default="")
    c.add_argument("--model", default="")
    c.add_argument("--tag", action="append", help="key=value (repeatable)")
    c = cmd(g, "update", cmd_agents_update, "change an agent's model binding")
    c.add_argument("id")
    c.add_argument("--provider")
    c.add_argument("--model")
    c.add_argument("--max-tokens", type=int, dest="max_tokens")
    c.add_argument("--effort")
    c.add_argument("--agent-timeout", type=float, dest="agent_timeout", help="model call timeout, seconds")
    en = c.add_mutually_exclusive_group()
    en.add_argument("--enable", dest="enabled", action="store_const", const=True, default=None)
    en.add_argument("--disable", dest="enabled", action="store_const", const=False)
    c.add_argument("--reason", default="", help="why (required when weakening a control)")
    c = cmd(g, "delete", cmd_agents_delete, "delete an agent")
    c.add_argument("id")
    c.add_argument("--dry-run", action="store_true", help="show what would be touched")
    c.add_argument("--force", action="store_true", help="delete even if still referenced")
    c.add_argument("--reason", default="")
    c.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    c = cmd(g, "pause", cmd_agents_pause, "stop a managed agent")
    c.add_argument("id")
    c = cmd(g, "resume", cmd_agents_resume, "start a stopped managed agent")
    c.add_argument("id")
    c = cmd(g, "chat", cmd_agents_chat, "send one message through the playground",
            description="Run one message through the agent's governed playground path and "
                        "print the reply. Exit 5 when the agent declines (budget, kill switch, "
                        "no model).")
    c.add_argument("id")
    c.add_argument("message", help="the message; - reads stdin")
    c.add_argument("--session", default="", help="continue a playground session")
    c.add_argument("--system", default="", help="override the system prompt")
    c.add_argument("--ticket", default="", help="ground the turn on this ticket id")
    c = cmd(g, "eval", cmd_agents_eval, "run the agent's eval set and print pass/fail",
            description="Run an evaluation dataset against the agent, wait, and print each "
                        "metric against the baseline. Exit 0 pass, 1 fail or regression.")
    c.add_argument("id")
    c.add_argument("--dataset", default="", help="eval dataset (default: the agent's own)")
    c.add_argument("--baseline", default="", help="run id, pinned, latest or none")
    c.add_argument("--wait", type=float, default=1800.0, help="seconds to wait")

    # tickets
    g = group("tickets", "work with tickets")
    c = cmd(g, "list", cmd_tickets_list, "list tickets, with filters")
    c.add_argument("--status")
    c.add_argument("--team")
    c.add_argument("--category")
    c.add_argument("-q", "--query", help="free-text search")
    c.add_argument("--limit", type=int, default=50)
    c.add_argument("--offset", type=int, default=0)
    c = cmd(g, "get", cmd_tickets_get, "show one ticket")
    c.add_argument("id")
    c = cmd(g, "create", cmd_tickets_create, "open a ticket")
    c.add_argument("--title", required=True)
    c.add_argument("-d", "--description", default="", help="text, or - for stdin")
    c.add_argument("--requester", default="")
    c = cmd(g, "comment", cmd_tickets_comment, "add a reply or internal note")
    c.add_argument("id")
    c.add_argument("text", help="the comment; - reads stdin")
    c.add_argument("--internal", action="store_true", help="an internal note, not public")
    c.add_argument("--author", choices=("desk", "requester"), default="desk")
    c = cmd(g, "close", cmd_tickets_close, "resolve or close a ticket")
    c.add_argument("id")
    c.add_argument("--resolution", default="")
    c.add_argument("--status", default="closed", choices=("closed", "resolved"))

    # triggers
    g = group("triggers", "schedules, webhooks and event triggers")
    c = cmd(g, "list", cmd_triggers_list, "list triggers")
    c.add_argument("--agent", default="", help="only this agent's")
    c = cmd(g, "create", cmd_triggers_create, "create a trigger")
    c.add_argument("name")
    c.add_argument("--agent", required=True)
    c.add_argument("--kind", required=True,
                   help="cron, ticket, webhook, teams, slack, email or google_chat")
    c.add_argument("--schedule", help="cron expression, for kind=cron")
    c.add_argument("--timezone")
    c.add_argument("--input", help="the message a scheduled run sends")
    c.add_argument("--event", action="append", help="event name, for kind=event (repeatable)")
    c.add_argument("--about", default="")
    c.add_argument("--disabled", action="store_true", help="create it paused")
    c.add_argument("--replace", action="store_true", help="overwrite an existing trigger")
    c = cmd(g, "delete", cmd_triggers_delete, "delete a trigger")
    c.add_argument("name")
    c.add_argument("-y", "--yes", action="store_true")

    # providers & models
    g = group("providers", "LLM providers")
    cmd(g, "list", cmd_providers_list, "list providers with health")
    c = cmd(g, "test", cmd_providers_test, "send a test call through a saved provider")
    c.add_argument("name")
    c = cmd(g, "add", cmd_providers_add, "add a provider",
            description="Add an LLM provider. The API key is read from stdin "
                        "(--api-key-stdin) or a hidden prompt (--prompt-key), never argv.")
    c.add_argument("name")
    c.add_argument("--kind", required=True, help="openai, anthropic, azure, bedrock, ollama, …")
    c.add_argument("--base-url", default="", dest="base_url")
    c.add_argument("--model", default="", help="default model")
    c.add_argument("--display-name", default="", dest="display_name")
    c.add_argument("--about", default="")
    c.add_argument("--api-key-stdin", action="store_true", dest="api_key_stdin")
    c.add_argument("--prompt-key", action="store_true", help="prompt for the API key (hidden)")
    c.add_argument("--replace", action="store_true")
    g = group("models", "the model catalogue")
    c = cmd(g, "list", cmd_models_list, "list models (the catalogue, or one provider's)")
    c.add_argument("--provider", default="")
    c.add_argument("--limit", type=int, default=100)

    # guardrails
    g = group("guardrails", "input/output guardrails")
    cmd(g, "list", cmd_guardrails_list, "list guardrails")
    c = cmd(g, "test", cmd_guardrails_test, "dry-run every guardrail over sample text",
            description="Dry-run the configured guardrails over TEXT. Exit 5 if it would be "
                        "blocked.")
    c.add_argument("text", help="sample text; - reads stdin")
    c.add_argument("--agent", default="copilot")
    c.add_argument("--direction", default="input", choices=("input", "output"))

    # secrets
    g = group("secrets", "the secret vault (values are never shown)")
    cmd(g, "list", cmd_secrets_list, "list secret labels")
    c = cmd(g, "set", cmd_secrets_set, "store a secret",
            description="Store a secret. The value is read from stdin when piped (or with "
                        "--stdin), else from a hidden prompt. It is never echoed.")
    c.add_argument("label")
    c.add_argument("--about", default="")
    c.add_argument("--tag", action="append")
    c.add_argument("--stdin", action="store_true")
    c = cmd(g, "delete", cmd_secrets_delete, "delete a secret")
    c.add_argument("label")
    c.add_argument("-y", "--yes", action="store_true")

    # policies
    g = group("policies", "Cedar access policies")
    c = cmd(g, "list", cmd_policies_list, "list policies")
    c.add_argument("--filter", default="", help="AIP-160 filter")
    c = cmd(g, "get", cmd_policies_get, "show one policy")
    c.add_argument("name")
    c = cmd(g, "create", cmd_policies_create, "bind a built-in template to an agent",
            description="Bind a built-in template to an agent. A template is what PEOPLE may "
                        "do with the agent: readonly (read it), sandboxed (read and run it), "
                        "standard (run and reconfigure it), full (everything, the kill switch "
                        "too). --principal names who (default: anyone). The moment a policy "
                        "names the agent it is governed: people without a permit lose what "
                        "their roles gave them. The agent's OWN tool and model calls are a "
                        "separate decision; --agent-tools writes them as the template implies "
                        "— readonly and sandboxed: no tools of its attached MCP servers; "
                        "standard: their tools; full: those and its bound LLM provider. Each "
                        "policy is analysed first and a lockout, or one that takes a server "
                        "from another agent, is refused without --yes. --dry-run exits 5.")
    c.add_argument("name", help="policy name (lowercase letters, digits and -)")
    c.add_argument("--agent", required=True, help="the agent the template is bound to")
    c.add_argument("--template", required=True, choices=sorted(POLICY_TEMPLATES),
                   help="readonly, sandboxed, standard or full")
    c.add_argument("--principal", default="any",
                   help="any (default), user:NAME, group:NAME or role:NAME")
    c.add_argument("--agent-tools", action="store_true", dest="agent_tools",
                   help="also write the agent's own call_tool (and, for full, call_model) "
                        "policies the template implies")
    c.add_argument("--about", default="")
    c.add_argument("--dry-run", action="store_true", help="show the policies and their impact")
    c.add_argument("--reason", default="")
    c.add_argument("-y", "--yes", action="store_true",
                   help="create even where the analysis warns")
    c = cmd(g, "apply", cmd_policies_apply, "create or update policies from a YAML file")
    c.add_argument("-f", "--file", required=True, help="policy YAML; - for stdin")
    c.add_argument("--dry-run", action="store_true", help="show the diff, change nothing")
    c.add_argument("--reason", default="")

    # audit
    g = group("audit", "the audit log")
    c = cmd(g, "search", cmd_audit_search, "search audit events",
            description='Search the audit log. QUERY is field=value terms, e.g. '
                        '"outcome=denied actor=alice"; free text also matches.')
    c.add_argument("query", nargs="*", default=[])
    c.add_argument("--since", default="24h", help="30m, 24h, 7d, 2w or ISO time (default 24h)")
    c.add_argument("--until", default="")
    c.add_argument("--limit", type=int, default=50)
    c.add_argument("--offset", type=int, default=0)
    c.add_argument("--order", choices=("desc", "asc"), default="desc")
    c = cmd(g, "verify", cmd_audit_verify, "verify an evidence bundle offline (no server)")
    c.add_argument("bundle")
    c.add_argument("--fingerprint", action="append", default=[], metavar="HEX",
                   help="trust the signing key with this fingerprint (repeatable)")
    c.add_argument("--audit-keys", metavar="FILE", default="",
                   help="the instance's published audit signing keys, as JSON")

    # budgets
    g = group("budgets", "spend budgets")
    cmd(g, "list", cmd_budgets_list, "spend against each budget")
    c = cmd(g, "set", cmd_budgets_set, "set the default or an agent's budget")
    c.add_argument("--agent", default="", help="omit for the default budget")
    c.add_argument("--limit", type=float, required=True, help="USD per period")
    c.add_argument("--period", default="month", choices=("day", "week", "month"))
    c.add_argument("--warn-pct", type=float, default=0, dest="warn_pct")

    # tenant
    g = group("tenant", "a tenant's solutions, and adopting legacy history into one")
    t = g.add_parser("solutions", help="which solutions a tenant has",
                     description="Which solutions a tenant has. TENANT '' is the instance's "
                                 "row, the default for every tenant without one.")
    ts = t.add_subparsers(dest="solutions_command", metavar="SUBCOMMAND")
    t.set_defaults(fn=lambda a, t=t: (t.print_help(), EXIT_ERROR)[1])
    c = cmd(ts, "show", cmd_tenant_solutions_show, "show a tenant's solutions")
    c.add_argument("tenant", help="tenant id, or '' for the instance")
    c = cmd(ts, "set", cmd_tenant_solutions_set, "set exactly which solutions a tenant has",
            description="Set exactly which solutions a tenant has (instance owners only). "
                        "SOLUTIONS are keys: itsm, sap, hr, finance, and SAP's modules "
                        "sap.s4, sap.sf, sap.fsm (sap alone means all of them). --default "
                        "removes the row, so the tenant falls back to the instance's — or, "
                        "with none, every GA solution. Audited as tenant.solutions.update.")
    c.add_argument("tenant", help="tenant id, or '' for the instance")
    c.add_argument("solutions", nargs="*", metavar="SOLUTION")
    c.add_argument("--default", action="store_true", help="remove the row instead")
    c.add_argument("--plan", default="", help="a plan (starter, business, enterprise); the "
                                              "row grants its solutions plus SOLUTIONS")
    c.add_argument("--dry-run", action="store_true", dest="dry_run",
                   help="show what would turn on and off; write nothing")
    c.add_argument("--reason", default="", help="why (kept on the row and the audit log; "
                                                "required when anything turns off)")
    c = cmd(ts, "infer", cmd_tenant_solutions_infer,
            "propose each tenant's row from what it uses",
            description="Propose each tenant's solutions from what it uses: intake sources "
                        "(itsm), SAP connectors bound to it (sap and modules), HR switched "
                        "on or HR systems bound (hr), finance connectors (finance). A dry "
                        "run unless --apply. Never proposes turning off what is in use: a "
                        "solution kept only by a shared, unbound server stays on and is "
                        "listed as ambiguous.")
    c.add_argument("--apply", action="store_true",
                   help="write each proposal (audited, reason 'migration infer')")

    c = cmd(g, "adopt-legacy", cmd_tenant_adopt_legacy,
            "adopt the instance's pre-tenancy history into a home tenant",
            description="Adopt the records written before this instance had "
                                 "tenants (transcripts, sessions, answer records, trigger "
                                 "runs, memory, SAP/HR records; audit rows by cut-off) into "
                                 "TENANT, bind the unbound door triggers and the deflection "
                                 "door to it and grant it to every non-owner account that "
                                 "holds no tenant — so the people who used the instance keep "
                                 "reading their own history, and only it. Idempotent; "
                                 "audited as tenant.legacy.adopt. Run with --dry-run first.")
    c.add_argument("--tenant", required=True, help="the home tenant (it must exist)")
    c.add_argument("--dry-run", action="store_true", dest="dry_run",
                   help="count every step; write nothing")
    c.add_argument("--reason", default="", help="why (required to apply; on the audit row)")
    c.add_argument("--triggers", default="doors", choices=("doors", "all", "none"),
                   help="unbound triggers to bind: inbound doors (default), all, or none")
    c.add_argument("--no-grant-users", action="store_true", dest="no_grant_users",
                   help="do not grant the home tenant to accounts holding none")
    c.add_argument("--no-sources", action="store_true", dest="no_sources",
                   help="do not give it the unowned sources and the unsourced intake")

    # connectors
    g = group("connectors", "ServiceNow, Jira, Teams and other connectors")
    cmd(g, "list", cmd_connectors_list, "list integrations and MCP connectors")
    c = cmd(g, "test", cmd_connectors_test, "test one connector")
    c.add_argument("name")

    # kb
    g = group("kb", "the knowledge base")
    c = cmd(g, "search", cmd_kb_search, "search knowledge files")
    c.add_argument("query", nargs="+")
    c.add_argument("--limit", type=int, default=10)

    # top-level
    s_ = sub.add_parser("status", parents=[out], help="gateway, model chain and connector "
                                                      "health: the command-center summary")
    s_.set_defaults(fn=cmd_status)
    s_ = sub.add_parser("doctor", parents=[out], help="diagnose configuration and connectivity")
    s_.set_defaults(fn=cmd_doctor)
    a = sub.add_parser("apply", parents=[out], help="apply YAML resources from a file or dir",
                       description="Declarative apply of agents, providers, guardrails, "
                                   "policies and triggers. --dry-run prints a diff and exits 5 "
                                   "if changes are pending.")
    a.add_argument("-f", "--file", required=True, help="a YAML/JSON file or a directory")
    a.add_argument("--dry-run", action="store_true")
    a.add_argument("--reason", default="", help="why, for changes that weaken a control")
    a.set_defaults(fn=cmd_apply)
    e = sub.add_parser("export", help="export resources as YAML files (no secrets)",
                       description="Write agents, providers (without secrets), guardrails, "
                                   "policies and triggers as YAML under DIR.")
    e.add_argument("-o", "--output-dir", dest="dir", required=True, help="target directory")
    e.add_argument("--kind", action="append",
                   choices=("Agent", "Provider", "Guardrail", "Policy", "Trigger"),
                   help="only these kinds (repeatable)")
    e.add_argument("--format", dest="output", choices=FORMATS, default=argparse.SUPPRESS,
                   help="format of the summary printed")
    e.set_defaults(fn=cmd_export)
    g = group("run", "run a coding agent with its model calls through the AI gateway")
    c = cmd(g, "claude", cmd_run_claude, "start Claude Code routed through the AI gateway",
            description="Start Claude Code with ANTHROPIC_BASE_URL set to this instance's "
                        "Anthropic gateway (/api/gateway/anthropic) and ANTHROPIC_AUTH_TOKEN "
                        "to an agent's gateway token, so every model call is that agent's "
                        "governed call: kill switch, Cedar, guardrails, budget, audit. The "
                        "token comes from LIYA_GATEWAY_TOKEN, --token-stdin, or is minted for "
                        "--agent (replacing its current token; confirmed, or --yes). A Claude "
                        "Code settings file that would send calls around the gateway — "
                        "CLAUDE_CODE_USE_VERTEX, _BEDROCK, _FOUNDRY or its own "
                        "ANTHROPIC_BASE_URL — refuses the launch; the same set only in this "
                        "shell is cleared from Claude Code's environment instead. Arguments "
                        "after -- go to Claude Code; its exit status is liya's.")
    c.add_argument("--agent", default="", help="mint a gateway token for this agent")
    c.add_argument("--ttl-hours", type=float, default=8.0, dest="ttl_hours",
                   help="lifetime of a minted token (default 8)")
    c.add_argument("--token-stdin", action="store_true", dest="token_stdin",
                   help="read the agent's gateway token from stdin")
    c.add_argument("--claude-bin", default="", dest="claude_bin",
                   help="the Claude Code executable (default: claude on PATH)")
    c.add_argument("--dry-run", action="store_true",
                   help="show what would run, the token masked, and start nothing")
    c.add_argument("-y", "--yes", action="store_true", help="mint without asking")
    c.add_argument("claude_args", nargs=argparse.REMAINDER,
                   help="arguments for Claude Code, after --")
    v = sub.add_parser("version", parents=[out], help="client and server version")
    v.set_defaults(fn=cmd_version)
    comp = sub.add_parser("completion", help="print a shell completion script",
                          description="eval \"$(liya completion zsh)\" in ~/.zshrc, or "
                                      "source <(liya completion bash).")
    comp.add_argument("shell", choices=("bash", "zsh"))
    comp.set_defaults(fn=cmd_completion)
    t = sub.add_parser("tiq", help="run a legacy `tiq` command (ask, plan, replay, …)",
                       description="Forward to the legacy tiq CLI with liya's environment "
                                   "and credential. `liya tiq --help` lists its verbs.")
    t.add_argument("rest", nargs=argparse.REMAINDER)
    t.set_defaults(fn=cmd_tiq)
    return p


# ---- completion ----

def _command_tree(p: argparse.ArgumentParser) -> dict[str, Any]:
    tree: dict[str, Any] = {"_opts": sorted(o for a in p._actions for o in a.option_strings
                                            if o.startswith("--"))}
    for a in p._actions:
        if isinstance(a, argparse._SubParsersAction):
            for name, sp in a.choices.items():
                tree[name] = _command_tree(sp)
    return tree


def _bash_completion(tree: dict[str, Any]) -> str:
    lines = ["# bash completion for liya", "_liya() {",
             "  local cur=${COMP_WORDS[COMP_CWORD]} path=\"\"",
             "  local i; for ((i=1; i<COMP_CWORD; i++)); do",
             "    case ${COMP_WORDS[i]} in -*) ;; *) path=\"$path ${COMP_WORDS[i]}\";; esac",
             "  done", "  path=${path# }", "  local words=\"\"", "  case \"$path\" in"]

    def walk(t: dict[str, Any], prefix: str) -> None:
        subs = [k for k in t if k != "_opts"]
        lines.append(f"    \"{prefix}\") words=\"{' '.join(subs + t['_opts'])}\";;")
        for k in subs:
            walk(t[k], f"{prefix} {k}".strip())
    walk(tree, "")
    lines += ["  esac", "  COMPREPLY=($(compgen -W \"$words\" -- \"$cur\"))", "}",
              "complete -F _liya liya"]
    return "\n".join(lines)


def _zsh_completion(tree: dict[str, Any]) -> str:
    return "#compdef liya\n" + "autoload -U +X bashcompinit && bashcompinit\n" + \
        _bash_completion(tree)


# ---- entry point ----

def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--no-color" in argv:
        os.environ["NO_COLOR"] = "1"
    # Legacy verbs: first positional word that is a tiq-only command.
    first = next((a for a in argv if not a.startswith("-")), None)
    if first in TIQ_VERBS and not _is_option_value(argv, first):
        return tiq.main(argv)
    # tiq's own global flags mean a tiq command line (`--json agents`, `--user u …`).
    if any(a in ("--json", "--user", "--password") for a in argv):
        return tiq.main(argv)
    parser = build_parser()
    # Accepted after the subcommand too, as --env and -o are — but never
    # taken from past a `--`, where the words are another program's
    # (`liya run claude -- -v`).
    cut = argv.index("--") if "--" in argv else len(argv)
    if "--verbose" in argv[:cut] or "-v" in argv[:cut]:
        argv = ["--verbose", *[a for a in argv[:cut] if a not in ("--verbose", "-v")],
                *argv[cut:]]
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # A usage error is invalid input (help stays 0).
        return 0 if e.code in (0, None) else EXIT_INVALID
    if args.version and not getattr(args, "fn", None):
        from . import __version__
        print(f"liya {__version__}")
        return EXIT_OK
    if not getattr(args, "fn", None):
        parser.print_help()
        return EXIT_ERROR
    try:
        return int(args.fn(args) or 0)
    except CliError as e:
        print(f"{PROG}: error: {e}", file=sys.stderr)
        code = getattr(e, "code", EXIT_ERROR)
        return code if code in (EXIT_ERROR, EXIT_INVALID, EXIT_AUTH, EXIT_NOT_FOUND) \
            else EXIT_ERROR
    except KeyboardInterrupt:
        print(f"{PROG}: interrupted", file=sys.stderr)
        return 130
    except Exception as e:  # pragma: no cover - last resort, no traceback for users
        if os.environ.get("LIYA_DEBUG"):
            raise
        print(f"{PROG}: error: {e.__class__.__name__}: {e} (LIYA_DEBUG=1 for a traceback)",
              file=sys.stderr)
        return EXIT_ERROR


def _is_option_value(argv: list[str], word: str) -> bool:
    i = argv.index(word)
    return i > 0 and argv[i - 1] in ("--env", "--url", "--token", "--timeout", "-o", "--output",
                                     "--user", "--password")


if __name__ == "__main__":
    raise SystemExit(main())
