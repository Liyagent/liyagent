"""`liya export -o dir/` and `liya apply -f dir/`: the instance as files.

Layout written by export, read (recursively, any layout) by apply::

    dir/agents/<name>.yaml       kind: AgentBundle   (the server's own bundle)
    dir/providers/<name>.yaml    kind: Provider      (no secrets, ever)
    dir/guardrails/<name>.yaml   kind: Guardrail
    dir/policies/<name>.yaml     kind: Policy
    dir/triggers/<name>.yaml     kind: Trigger

Agents go through POST /api/agents/apply, the endpoint `tiq plan/apply`
already used — one transaction, the server's own plan for --dry-run. The
other kinds are PUT to their resource, with a spec cut down to exactly the
fields the server's request schema accepts (read from its /openapi.json), so
an export never carries a server-managed stamp back in and a newer server's
new field is exported the day it ships.

A kind the connected server has no endpoint for is reported as "not supported
by this server version" and skipped; it never fails the run.
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path
from typing import Any

from .client import CliError, Session, q
from .output import note, paint, to_yaml
from .tiq import _pending

API_VERSION = "ticketiq.io/v1"

# kind -> (directory, list path, item path template, how the list answers)
KINDS: dict[str, dict[str, str]] = {
    "Provider": {"dir": "providers", "list": "/api/llm/providers",
                 "item": "/api/llm/providers/{name}", "key": "providers"},
    "Guardrail": {"dir": "guardrails", "list": "/api/guardrails",
                  "item": "/api/guardrails/{name}", "key": "guardrails"},
    "Policy": {"dir": "policies", "list": "/api/policies",
               "item": "/api/policies/{name}", "key": "policies"},
    "Trigger": {"dir": "triggers", "list": "/api/triggers",
                "item": "/api/triggers/{name}", "key": "triggers"},
}
# Dependencies first: a guardrail or policy may name a provider or agent; a
# trigger names an agent.
ORDER = ("Provider", "Guardrail", "Policy", "AgentBundle", "Trigger")

# Never exported, whatever a schema says: a value, not a reference to one.
_SECRETISH = re.compile(r"(api_key|secret|password|token|credentials_json|"
                        r"access_key_id|private_key)$", re.I)
# Request-only fields: why a change was made, which fields a PATCH touches.
_REQUEST_ONLY = {"reason", "update_mask", "name"}


def is_secret_field(key: str) -> bool:
    return bool(_SECRETISH.search(key)) and not key.endswith("_ref")


def _names(listing: Any, key: str) -> list[str]:
    rows = listing.get(key) if isinstance(listing, dict) else None
    if isinstance(rows, dict):
        return sorted(rows)
    if isinstance(rows, list):
        return sorted(str(r.get("name")) for r in rows if isinstance(r, dict) and r.get("name"))
    return []


def project(obj: dict[str, Any], fields: list[str] | None) -> dict[str, Any]:
    """The declarative part of a server object: request-schema fields only,
    secrets stripped."""
    out: dict[str, Any] = {}
    for k, v in obj.items():
        if k in _REQUEST_ONLY or is_secret_field(k):
            continue
        if fields is not None and k not in fields:
            continue
        out[k] = v
    return out


def doc(kind: str, name: str, spec: dict[str, Any]) -> dict[str, Any]:
    return {"apiVersion": API_VERSION, "kind": kind, "metadata": {"name": name}, "spec": spec}


# ---- export ----

def export(s: Session, out_dir: Path, kinds: list[str] | None = None) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, list[str]] = {}
    skipped: dict[str, str] = {}
    for kind in ORDER:
        if kinds and kind not in kinds and not (kind == "AgentBundle" and "Agent" in kinds):
            continue
        if kind == "AgentBundle":
            if not s.supports("GET", "/api/export"):
                skipped[kind] = "not supported by this server version"
                continue
            data = s.get("/api/export")
            items = data.get("items") if data.get("kind") == "AgentBundleList" else [data]
            for item in items or []:
                name = (item.get("metadata") or {}).get("name")
                if name:
                    _write(out_dir / "agents" / f"{name}.yaml", item)
                    written.setdefault("AgentBundle", []).append(name)
            continue
        k = KINDS[kind]
        if not (s.supports("GET", k["list"]) and s.supports("PUT", k["item"])):
            skipped[kind] = "not supported by this server version"
            continue
        fields = s.body_fields("PUT", k["item"])
        for name in _names(s.get(k["list"]), k["key"]):
            obj = s.get(k["item"].format(name=q(name)))
            spec = project(obj if isinstance(obj, dict) else {}, fields)
            _write(out_dir / k["dir"] / f"{_safe(name)}.yaml", doc(kind, name, spec))
            written.setdefault(kind, []).append(name)
    return {"directory": str(out_dir), "written": written, "skipped": skipped}


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_yaml(data) + "\n", encoding="utf-8")


# ---- load ----

def load(path: Path) -> list[dict[str, Any]]:
    """Every resource document under `path` (a file or a directory), in
    dependency order. JSON and multi-document YAML both read; a `tiq export`
    bundle list is expanded into its agents."""
    import yaml
    if not path.exists():
        raise CliError(f"{path}: no such file or directory")
    files = ([path] if path.is_file() else
             sorted(p for p in path.rglob("*") if p.suffix in (".yaml", ".yml", ".json")))
    docs: list[dict[str, Any]] = []
    for f in files:
        try:
            for d in yaml.safe_load_all(f.read_text(encoding="utf-8")):
                if d is None:
                    continue
                if not isinstance(d, dict) or "kind" not in d:
                    raise CliError(f"{f}: a document without `kind`")
                if d["kind"] == "AgentBundleList":
                    docs.extend(dict(i, _file=str(f)) for i in d.get("items") or [])
                else:
                    docs.append(dict(d, _file=str(f)))
        except yaml.YAMLError as e:
            raise CliError(f"{f}: not valid YAML: {e}") from None
    for d in docs:
        if d["kind"] == "Agent":
            d["kind"] = "AgentBundle"
        if d["kind"] not in ORDER:
            raise CliError(f"{d['_file']}: unknown kind {d['kind']!r} "
                           f"(expected one of {', '.join(ORDER)})")
        if not (d.get("metadata") or {}).get("name"):
            raise CliError(f"{d['_file']}: metadata.name is required")
    return sorted(docs, key=lambda d: ORDER.index(d["kind"]))


# ---- apply ----

def _diff(before: Any, after: Any, label: str) -> str:
    a = to_yaml(before).splitlines() if before is not None else []
    b = to_yaml(after).splitlines()
    lines = []
    for line in difflib.unified_diff(a, b, f"{label} (server)", f"{label} (file)", lineterm=""):
        if line.startswith("+") and not line.startswith("+++"):
            line = paint(line, "green")
        elif line.startswith("-") and not line.startswith("---"):
            line = paint(line, "red")
        lines.append(line)
    return "\n".join(lines)


def apply(s: Session, docs: list[dict[str, Any]], dry_run: bool, reason: str = "",
          show_diff: bool = True) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for d in docs:
        kind, name = d["kind"], d["metadata"]["name"]
        label = f"{kind}/{name}"
        if kind == "AgentBundle":
            if not s.supports("POST", "/api/agents/apply"):
                results.append({"resource": label, "action": "skipped",
                                "detail": "not supported by this server version"})
                continue
            bundle = {k: v for k, v in d.items() if k != "_file"}
            out = s.post("/api/agents/apply", {"bundle": bundle, "dry_run": dry_run,
                                               "reason": reason})
            for a in out.get("agents") or []:
                if not a.get("valid", True):
                    ref = a.get("refusal") or {}
                    results.append({"resource": f"AgentBundle/{a.get('agent')}",
                                    "action": "refused", "detail": str(ref.get("detail"))})
                    continue
                what = _pending(a) if dry_run else (
                    ["create"] if a.get("created") else a.get("changed") or [])
                action = ("create" if what == ["create"] else
                          "update" if what else "unchanged")
                results.append({"resource": f"AgentBundle/{a.get('agent')}", "action": action,
                                "detail": ", ".join(w for w in what if w != "create")})
                if dry_run and show_diff and what and what != ["create"]:
                    note(f"~ {label}: server plan changes " + ", ".join(what))
            continue
        k = KINDS[kind]
        item = k["item"].format(name=q(name))
        if not s.supports("PUT", k["item"]):
            results.append({"resource": label, "action": "skipped",
                            "detail": "not supported by this server version"})
            continue
        spec = dict(d.get("spec") or {})
        leaked = [f for f in spec if is_secret_field(f)]
        if leaked:
            raise CliError(f"{d['_file']}: {label} carries secret value field(s) "
                           f"{', '.join(leaked)} — reference a stored secret (…_ref, or "
                           "`liya secrets set`) instead of putting a value in Git")
        r = s.request("GET", item, check=False)
        current = r.json() if r.status_code == 200 else None
        if r.status_code not in (200, 404):
            s.get(item)  # raises the readable error
        before, after = _compared(s, k["item"], spec, current)
        changed = [f for f in after if current is None or not _same(before.get(f), after[f])]
        if current is not None and not changed:
            results.append({"resource": label, "action": "unchanged", "detail": ""})
            continue
        action = "create" if current is None else "update"
        if dry_run:
            if show_diff:
                note(_diff(None if current is None else before, after, label))
        else:
            body = dict(spec)
            if reason and "reason" in (s.body_fields("PUT", k["item"]) or []):
                body["reason"] = reason
            s.put(item, body)
        results.append({"resource": label, "action": action,
                        "detail": ", ".join(changed) if action == "update" else ""})
    summary: dict[str, int] = {}
    for r_ in results:
        summary[r_["action"]] = summary.get(r_["action"], 0) + 1
    return {"dry_run": dry_run, "results": results, "summary": summary}


def _canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, default=str)


def _compared(s: Session, item: str, spec: dict[str, Any],
              current: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """(server, file): the resource as stored and as the PUT would leave it,
    over EVERY field the PUT writes — not only those the file names. A PUT
    replaces the whole record, so a writable field the file leaves out is
    set to its default: a diff over the file's own fields called that
    "unchanged" while the apply quietly reset it. A field the server never
    returns (write-only) is compared only when the file names it; a secret
    or request-only field never is. Without a schema to read, the file's
    fields are all there is to compare."""
    props = s.body_properties("PUT", item) or {}
    writable = [f for f in props if f not in _REQUEST_ONLY and not is_secret_field(f)]
    fields = list(dict.fromkeys([*spec, *(f for f in writable
                                         if current is not None and f in current)]))
    after = {f: spec[f] if f in spec else (props.get(f) or {}).get("default") for f in fields}
    before = {f: (current or {}).get(f) for f in fields}
    return before, after


def _same(a: Any, b: Any) -> bool:
    """Equal as the server stores them: an absent value, null, "", [] and {}
    are the one "empty" — a schema default of null and a stored "" are not
    a change."""
    def norm(v: Any) -> Any:
        return None if v in (None, "", [], {}) else v
    return _canon(norm(a)) == _canon(norm(b))
