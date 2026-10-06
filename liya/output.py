"""Formatting command output: table (default), json or yaml.

One rule, inherited from `tiq`: a stream is either for people or for
machines, never both. JSON and YAML carry the server's payload whole; the
table is a readable projection of it. Notes and hints go to stderr so stdout
stays pipeable in every format.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Iterable, Sequence

FORMATS = ("table", "json", "yaml")

_CODES = {"green": "32", "red": "31", "yellow": "33", "dim": "2", "bold": "1", "cyan": "36"}


def color_enabled(stream=None) -> bool:
    """NO_COLOR (https://no-color.org) wins; then a non-terminal gets none."""
    if "NO_COLOR" in os.environ:
        return False
    if os.environ.get("LIYA_FORCE_COLOR"):
        return True
    stream = stream or sys.stdout
    return bool(getattr(stream, "isatty", lambda: False)())


def paint(text: str, color: str, stream=None) -> str:
    if not color_enabled(stream) or color not in _CODES:
        return text
    return f"\033[{_CODES[color]}m{text}\033[0m"


def state(word: str) -> str:
    """Colour a health word by what it means."""
    w = str(word).lower()
    if w in ("ok", "pass", "passed", "healthy", "up", "enabled", "active", "running",
             "yes", "allowed", "completed", "closed"):
        return paint(str(word), "green")
    if w in ("degraded", "warn", "warning", "paused", "stopped", "open-half", "pending",
             "half_open", "monitor", "skipped"):
        return paint(str(word), "yellow")
    if w in ("error", "fail", "failed", "down", "denied", "open", "blocked", "disabled",
             "no", "unreachable", "regressed"):
        return paint(str(word), "red")
    return str(word)


def _cell(v: Any) -> str:
    if v is None or v == "":
        return "-"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (list, tuple)):
        return ",".join(_cell(x) for x in v) or "-"
    if isinstance(v, dict):
        return json.dumps(v, sort_keys=True, default=str)
    s = str(v).replace("\n", " ")
    return s


def _visible_len(s: str) -> int:
    import re
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def render_table(header: Sequence[str], rows: Iterable[Sequence[Any]],
                 max_width: int = 60) -> str:
    cells = [[_cell(c) for c in r] for r in rows]
    cells = [[c if _visible_len(c) <= max_width else c[: max_width - 1] + "…" for c in r]
             for r in cells]
    if not cells:
        return "(nothing to show)"
    widths = [max([len(h)] + [_visible_len(r[i]) for r in cells]) for i, h in enumerate(header)]
    lines = ["  ".join(paint(h.upper(), "bold") + " " * (w - len(h))
                       for h, w in zip(header, widths)).rstrip()]
    for r in cells:
        lines.append("  ".join(c + " " * (w - _visible_len(c)) for c, w in zip(r, widths)).rstrip())
    return "\n".join(lines)


def to_yaml(data: Any) -> str:
    import yaml

    class _Dumper(yaml.SafeDumper):
        pass

    def _str(dumper, value):
        style = "|" if "\n" in value else None
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)

    _Dumper.add_representer(str, _str)
    return yaml.dump(json.loads(json.dumps(data, default=str)), Dumper=_Dumper,
                     sort_keys=False, allow_unicode=True, default_flow_style=False).rstrip()


def emit(fmt: str, payload: Any, header: Sequence[str] | None = None,
         rows: Iterable[Sequence[Any]] | None = None, out=None) -> None:
    """Print `payload` as json/yaml, or the (header, rows) table. A command
    with no table shape falls back to key/value rows for a dict."""
    out = out or sys.stdout
    if fmt == "json":
        print(json.dumps(payload, indent=2, sort_keys=True, default=str), file=out)
        return
    if fmt == "yaml":
        print(to_yaml(payload), file=out)
        return
    if header is None:
        if isinstance(payload, dict):
            header, rows = ("field", "value"), [(k, v) for k, v in payload.items()]
        elif isinstance(payload, list):
            print("\n".join(_cell(x) for x in payload) or "(nothing to show)", file=out)
            return
        else:
            print(_cell(payload), file=out)
            return
    print(render_table(header, rows or []), file=out)


def note(msg: str) -> None:
    sys.stdout.flush()  # keep order when both streams go to one terminal or file
    print(msg, file=sys.stderr, flush=True)
