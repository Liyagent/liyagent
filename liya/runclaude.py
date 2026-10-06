"""`liya run claude`: Claude Code, with every model call through the AI gateway.

Claude Code reads ANTHROPIC_BASE_URL for where to send its Messages calls and
ANTHROPIC_AUTH_TOKEN for the bearer to send. Pointed at the instance's
Anthropic endpoint (/api/gateway/anthropic, anthropic_gw) with an agent's
gateway token, every call it makes is that agent's governed call: its kill
switch, Cedar's call_model, guardrails both ways, its budget and rate limits,
the gateway.call audit row.

What would take a call AROUND the gateway is refused before Claude Code
starts, never left to find out later:

* a cloud-provider mode (CLAUDE_CODE_USE_VERTEX, _BEDROCK, _FOUNDRY) or a
  base URL of its own set in a Claude Code settings file — settings apply
  over the environment this launches it with, so Claude Code would call
  Vertex (or Bedrock, or that URL) directly. Refused unless that file's own
  base URL routes it through this instance's gateway;
* the same set only in this shell's environment is not a refusal: the child
  is started without it, so it is routed.

An API key or apiKeyHelper in a settings file would be sent in place of the
agent's token — the gateway then answers 401, which is safe but useless, so
it is said up front as a warning.

The token: LIYA_GATEWAY_TOKEN or --token-stdin (the agent's own token,
nothing rotated), else --agent minted afresh — which REPLACES the agent's
current token (issue_gateway_token), so it is asked for, not assumed.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

# The gateway path Claude Code's ANTHROPIC_BASE_URL points at; it appends
# /v1/messages itself.
GATEWAY_PATH = "/api/gateway/anthropic"
# Each switches Claude Code to a cloud provider's own endpoint.
CLOUD_MODES = {"CLAUDE_CODE_USE_VERTEX": "ANTHROPIC_VERTEX_BASE_URL",
               "CLAUDE_CODE_USE_BEDROCK": "ANTHROPIC_BEDROCK_BASE_URL",
               "CLAUDE_CODE_USE_FOUNDRY": "ANTHROPIC_FOUNDRY_BASE_URL"}
# What the child is started without: each would send its calls elsewhere, or
# with another credential than the agent's.
_CLEARED = (*CLOUD_MODES, *CLOUD_MODES.values(), "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
            "ANTHROPIC_AUTH_TOKEN")


def _truthy(v: Any) -> bool:
    return str(v).strip().lower() not in ("", "0", "false", "no", "off", "none")


def settings_files(cwd: Path, home: Path) -> list[Path]:
    """Every Claude Code settings file that could apply to a run in `cwd`:
    the managed one (macOS and Linux paths), the user's, and the project's
    shared and local ones."""
    managed = (Path("/Library/Application Support/ClaudeCode/managed-settings.json")
               if platform.system() == "Darwin" else Path("/etc/claude-code/managed-settings.json"))
    return [managed, home / ".claude" / "settings.json",
            cwd / ".claude" / "settings.json", cwd / ".claude" / "settings.local.json"]


def check_settings(files: list[Path], gateway_url: str) -> tuple[list[str], list[str]]:
    """(refusals, warnings) from the settings files that exist. A refusal is
    a setting that would take Claude Code's calls around the gateway."""
    refusals: list[str] = []
    warnings: list[str] = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
        except (OSError, ValueError) as e:
            refusals.append(f"{f}: cannot be read ({e.__class__.__name__}) — Claude Code would "
                            "read it, so whether it routes around the gateway is unknown")
            continue
        env = data.get("env") if isinstance(data, dict) else None
        env = env if isinstance(env, dict) else {}
        for mode, base_var in CLOUD_MODES.items():
            if _truthy(env.get(mode, "")):
                base = str(env.get(base_var) or "")
                if not base.startswith(gateway_url):
                    refusals.append(f"{f}: env.{mode} sends Claude Code's calls to the cloud "
                                    f"provider directly, around the gateway — remove it, or "
                                    f"route it ({base_var}) through {gateway_url}")
        base = str(env.get("ANTHROPIC_BASE_URL") or "")
        if base and not base.startswith(gateway_url):
            refusals.append(f"{f}: env.ANTHROPIC_BASE_URL sends Claude Code's calls to {base}, "
                            "around the gateway — remove it")
        for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
            if env.get(key):
                warnings.append(f"{f}: env.{key} replaces the agent's gateway token — the "
                                "gateway will refuse it (401)")
        if isinstance(data, dict) and data.get("apiKeyHelper"):
            warnings.append(f"{f}: apiKeyHelper's key replaces the agent's gateway token — "
                            "the gateway will refuse it (401)")
    return refusals, warnings


def child_env(base: dict[str, str], gateway_url: str, token: str) -> tuple[dict[str, str],
                                                                          list[str]]:
    """(the environment Claude Code is started with, what was cleared from
    this shell's): the gateway as its base URL and the agent's token as its
    bearer, every variable that would send a call elsewhere taken out."""
    env = {k: v for k, v in base.items() if k not in _CLEARED}
    cleared = [k for k in _CLEARED if base.get(k) and k not in ("ANTHROPIC_BASE_URL",
                                                                  "ANTHROPIC_AUTH_TOKEN")]
    env["ANTHROPIC_BASE_URL"] = gateway_url
    env["ANTHROPIC_AUTH_TOKEN"] = token
    return env, cleared


def find_claude(explicit: str = "") -> str:
    """The Claude Code executable: --claude-bin, else `claude` on PATH, else
    the native installer's own location."""
    if explicit:
        return explicit if Path(explicit).exists() or shutil.which(explicit) else ""
    found = shutil.which("claude")
    if found:
        return found
    local = Path.home() / ".claude" / "local" / "claude"
    return str(local) if local.exists() else ""


def launch(argv: list[str], env: dict[str, str]) -> int:
    """Run Claude Code in the foreground, its exit status ours. The seam
    tests replace."""
    return subprocess.call(argv, env=env)
