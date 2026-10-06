"""Where `liya` keeps its state: ~/.liya (or $LIYA_HOME).

Two files, deliberately separate:

* ``config`` — environments and which one is current. Safe to show, safe to
  copy between machines.
* ``credentials`` — one token per environment. Created 0600 inside a 0700
  directory, rewritten atomically, and never printed by any command: `auth
  status` says *that* a credential exists and what kind it is, not what it is.

Both are JSON, which is also valid YAML, so a person can edit either by hand.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_ENVS: dict[str, dict[str, str]] = {
    "local": {"url": "http://127.0.0.1:8787"},   # the server's default port
    "demo": {"url": "https://liyagent.com"},
}
DEFAULT_CURRENT = "local"


def home() -> Path:
    return Path(os.environ.get("LIYA_HOME") or Path.home() / ".liya")


def config_path() -> Path:
    return home() / "config"


def credentials_path() -> Path:
    return home() / "credentials"


def _ensure_home() -> Path:
    h = home()
    h.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(h, 0o700)
    except OSError:
        pass
    return h


def _read(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except ValueError:
        import yaml  # a hand-edited file may be real YAML
        data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def _write(path: Path, data: dict[str, Any], mode: int) -> None:
    """Atomic, and created with `mode` from the first byte: a credential file
    that is briefly world-readable between write and chmod is not 0600."""
    _ensure_home()
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    os.chmod(path, mode)


# ---- environments ----

def load_config() -> dict[str, Any]:
    cfg = _read(config_path())
    envs = dict(DEFAULT_ENVS)
    envs.update(cfg.get("environments") or {})
    return {"current": cfg.get("current") or DEFAULT_CURRENT, "environments": envs}


def save_config(cfg: dict[str, Any]) -> None:
    _write(config_path(), cfg, 0o644)


def add_env(name: str, url: str) -> None:
    cfg = load_config()
    cfg["environments"][name] = {"url": url.rstrip("/")}
    save_config(cfg)


def remove_env(name: str) -> bool:
    cfg = load_config()
    if name not in cfg["environments"]:
        return False
    del cfg["environments"][name]
    if cfg["current"] == name:
        cfg["current"] = DEFAULT_CURRENT
    save_config(cfg)
    return True


def use_env(name: str) -> None:
    cfg = load_config()
    if name not in cfg["environments"]:
        raise KeyError(name)
    cfg["current"] = name
    save_config(cfg)


# ---- credentials ----

def load_credentials() -> dict[str, Any]:
    return _read(credentials_path())


def credentials_mode() -> int | None:
    try:
        return stat.S_IMODE(os.stat(credentials_path()).st_mode)
    except FileNotFoundError:
        return None


def save_credential(env: str, entry: dict[str, Any]) -> None:
    creds = load_credentials()
    creds[env] = entry
    _write(credentials_path(), creds, 0o600)


def delete_credential(env: str) -> bool:
    creds = load_credentials()
    if env not in creds:
        return False
    del creds[env]
    _write(credentials_path(), creds, 0o600)
    return True


def token_kind(token: str) -> str:
    """What a token is, for display — never the token."""
    if token.startswith("svc/") and ":" in token:
        return "service-account"
    return "session"
