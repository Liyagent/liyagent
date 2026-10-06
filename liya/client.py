"""The one HTTP path every `liya` command takes.

Credential resolution, highest first:

1. ``--token`` / ``LIYA_TOKEN`` (``TICKETIQ_TOKEN`` is honoured too, so a CI
   secret that drove `tiq` drives `liya` unchanged);
2. the current environment's entry in ~/.liya/credentials.

A service account's client credentials (``svc/<name>:<secret>``) are
exchanged for a one-hour session on every run, by the same code `tiq` uses
(tiq._bearer); anything else is sent as a bearer as it is.

Error handling is `tiq`'s too (tiq._checked / _refused / _detail): 401 and 403
are told apart, and the server's reason is printed rather than a bare status.
Each failure carries its kind (CliError.code) for the exit status.

``--verbose`` (or LIYA_VERBOSE=1) logs every request to stderr — its method,
its URL (a query value under a secret-looking name masked), the status and
how long it took — and never a header: the Authorization header is the one
thing on the request a log must not hold.
"""

from __future__ import annotations

import os
import re
import sys
import time
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from . import config
from .tiq import CliError, _bearer, _checked, _detail  # reuse, not re-implement

__all__ = ["CliError", "Session", "make_client", "q", "_detail"]


def make_client(base_url: str, timeout: float) -> Any:
    """The seam tests replace with a FastAPI TestClient or a MockTransport."""
    import httpx
    return httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout,
                        headers={"User-Agent": f"liya/{_version()}"})


# A query parameter whose value may be a credential: masked in --verbose.
_SECRET_PARAM = re.compile(r"(secret|password|passwd|api[_-]?key|access[_-]?token|"
                           r"refresh[_-]?token|id[_-]?token|^token$|^code$|signature|sig$)",
                           re.I)


def loggable_url(url: Any) -> str:
    """The URL as --verbose prints it: whole, but with the value of a query
    parameter named like a credential masked. A path never holds one here."""
    parts = urlsplit(str(url))
    if "@" in parts.netloc:
        # Credentials in the URL itself (https://user:pass@host): dropped.
        parts = parts._replace(netloc=parts.netloc.rpartition("@")[2])
    if not parts.query:
        return urlunsplit(parts)
    query = [(k, "***" if _SECRET_PARAM.search(k) else v)
             for k, v in parse_qsl(parts.query, keep_blank_values=True)]
    return urlunsplit(parts._replace(query=urlencode(query, safe="*,:/")))


def _log_requests(client: Any, stream: Any = None) -> Any:
    """Hook --verbose onto `client`: one stderr line per response — method,
    URL, status, latency. Never headers. Hooks rather than a wrapper around
    Session.request, so the sign-in, the service-account exchange and the
    health probes that talk to the client directly are logged too."""
    def started(request: Any) -> None:
        request.extensions["liya_started"] = time.monotonic()

    def finished(response: Any) -> None:
        req = response.request
        t0 = req.extensions.get("liya_started")
        ms = f"{(time.monotonic() - t0) * 1000:.0f} ms" if t0 is not None else "?"
        print(f"liya: {req.method} {loggable_url(req.url)} -> {response.status_code} ({ms})",
              file=stream or sys.stderr)

    hooks = dict(client.event_hooks)
    hooks["request"] = [*hooks.get("request", []), started]
    hooks["response"] = [*hooks.get("response", []), finished]
    client.event_hooks = hooks
    return client


def _version() -> str:
    from . import __version__
    return __version__


def q(segment: str) -> str:
    """One path segment, quoted whole."""
    return quote(str(segment), safe="")


class Session:
    def __init__(self, env: str | None = None, url: str | None = None,
                 token: str | None = None, timeout: float = 60.0, verbose: bool = False):
        cfg = config.load_config()
        self.env = env or os.environ.get("LIYA_ENV") or cfg["current"]
        envs = cfg["environments"]
        if not url and self.env not in envs:
            raise CliError(f"unknown environment {self.env!r} — `liya env list` shows them, "
                           "`liya env add NAME --url URL` adds one", code=2)
        self.verbose = verbose or os.environ.get("LIYA_VERBOSE", "") not in ("", "0")
        self.url = (url or os.environ.get("LIYA_URL") or envs[self.env]["url"]).rstrip("/")
        self.timeout = timeout
        self._explicit_token = token
        self._client: Any = None
        self._openapi: dict[str, Any] | None = None

    # ---- credentials ----

    def token_source(self) -> tuple[str, str]:
        """(token, where it came from). The token never leaves this object
        except as an Authorization header."""
        if self._explicit_token:
            return self._explicit_token, "--token"
        for var in ("LIYA_TOKEN", "TICKETIQ_TOKEN"):
            if os.environ.get(var):
                return os.environ[var], var
        entry = config.load_credentials().get(self.env) or {}
        if entry.get("token"):
            return entry["token"], str(config.credentials_path())
        return "", ""

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = make_client(self.url, self.timeout)
            if self.verbose:
                _log_requests(self._client)
        return self._client

    def anonymous(self) -> Any:
        return self.client

    def authed(self) -> Any:
        c = self.client
        if "Authorization" not in c.headers:
            token, _ = self.token_source()
            if not token:
                raise CliError(f"not logged in to {self.env!r} ({self.url}) — run "
                               "`liya auth login`, or set LIYA_TOKEN", code=3)
            try:
                c.headers["Authorization"] = f"Bearer {_bearer(c, token)}"
            except CliError:
                raise
            except Exception as e:
                raise CliError(f"cannot reach {self.url}: {e.__class__.__name__}: {e}") from None
        return c

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    # ---- requests ----

    def request(self, method: str, path: str, *, params: dict | None = None,
                json: Any = None, auth: bool = True, check: bool = True,
                not_found: str | None = None) -> Any:
        c = self.authed() if auth else self.anonymous()
        qp = {k: v for k, v in (params or {}).items() if v not in (None, "", [])}
        try:
            r = c.request(method, path, params=qp or None, json=json)
        except CliError:
            raise
        except Exception as e:
            raise CliError(f"cannot reach {self.url}: {e.__class__.__name__}: {e}") from None
        if not check:
            return r
        if r.status_code == 404 and not_found:
            raise CliError(not_found, code=4)
        if r.status_code in (404, 405) and self.route_missing(method, path):
            raise CliError(f"{method} {path}: not supported by this server version")
        if r.status_code == 204 or not r.content:
            if r.status_code >= 400:
                _checked(r, path)
            return {}
        return _checked(r, path)

    def get(self, path: str, **kw: Any) -> Any:
        return self.request("GET", path, **kw)

    def post(self, path: str, body: Any = None, **kw: Any) -> Any:
        return self.request("POST", path, json=body if body is not None else {}, **kw)

    def put(self, path: str, body: Any, **kw: Any) -> Any:
        return self.request("PUT", path, json=body, **kw)

    def patch(self, path: str, body: Any, **kw: Any) -> Any:
        return self.request("PATCH", path, json=body, **kw)

    def delete(self, path: str, body: Any = None, **kw: Any) -> Any:
        return self.request("DELETE", path, json=body, **kw)

    # ---- what the server supports ----

    def openapi(self) -> dict[str, Any]:
        if self._openapi is None:
            try:
                r = self.client.get("/openapi.json")
                self._openapi = r.json() if r.status_code == 200 else {}
            except Exception:
                self._openapi = {}
        return self._openapi

    def _route(self, method: str, path: str) -> dict[str, Any] | None:
        """The OpenAPI operation serving `method path`, matching templated
        segments; None when the spec does not list it (or has no spec)."""
        spec = self.openapi()
        paths = spec.get("paths") or {}
        want = path.split("?", 1)[0].rstrip("/").split("/")
        for tmpl, ops in paths.items():
            parts = tmpl.rstrip("/").split("/")
            if parts[-1].endswith(":path}"):
                if len(want) < len(parts):
                    continue
                want_cmp = want[: len(parts) - 1] + ["/".join(want[len(parts) - 1:])]
            else:
                if len(parts) != len(want):
                    continue
                want_cmp = want
            if all(p == w or (p.startswith("{") and p.endswith("}"))
                   for p, w in zip(parts, want_cmp)):
                op = ops.get(method.lower())
                if op is not None:
                    return op
        return None

    def supports(self, method: str, path: str) -> bool:
        if not self.openapi().get("paths"):
            return True  # no spec to consult: assume yes, let the call answer
        return self._route(method, path) is not None

    def route_missing(self, method: str, path: str) -> bool:
        return bool(self.openapi().get("paths")) and self._route(method, path) is None

    def body_fields(self, method: str, path: str) -> list[str] | None:
        """The request body's property names, from the server's own schema:
        what an exported resource may carry back into a PUT."""
        props = self.body_properties(method, path)
        return list(props) if props is not None else None

    def body_properties(self, method: str, path: str) -> dict[str, Any] | None:
        """The request body's properties, each its JSON Schema (its
        `default` among them) — None when the spec does not describe it."""
        op = self._route(method, path)
        if not op:
            return None
        schema = (((op.get("requestBody") or {}).get("content") or {})
                  .get("application/json") or {}).get("schema") or {}
        ref = schema.get("$ref", "")
        if ref:
            name = ref.rsplit("/", 1)[-1]
            schema = ((self.openapi().get("components") or {}).get("schemas") or {}).get(name, {})
        props = schema.get("properties")
        return props if isinstance(props, dict) else None


_DURATION = re.compile(r"^(\d+)([smhdw])$")


def since_timestamp(text: str, now: Any = None) -> str:
    """--since as the ISO-8601 UTC instant the server compares against.

    '30m', '24h', '7d', '2w' are resolved here, against this machine's clock
    (the server's rolling windows are a fixed menu — 1h, 24h, 7d…); an ISO
    timestamp is passed through. A typo is a usage error, not a server 400."""
    from datetime import datetime, timedelta, timezone
    text = text.strip()
    m = _DURATION.match(text)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        delta = timedelta(**{{"s": "seconds", "m": "minutes", "h": "hours",
                               "d": "days", "w": "weeks"}[unit]: n})
        now = now or datetime.now(timezone.utc)
        return (now - delta).isoformat(timespec="seconds")
    try:
        ts = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise CliError(f"--since {text!r}: use a duration like 30m, 24h, 7d or 2w, "
                       "or an ISO-8601 timestamp", code=2) from None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat(timespec="seconds")
