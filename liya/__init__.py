"""liya: the command line for Liyagent.

* ``liya`` (``liya.commands``) — the official CLI; ``python -m liya``.
* ``tiq`` (``liya.tiq``) — the earlier CLI, kept working: ``liya``
  forwards its verbs, and ``./tiq`` / ``python -m liya.tiq`` still run it.
"""

from __future__ import annotations

__version__ = "2.5.0"


def main(argv: list[str] | None = None) -> int:
    from .commands import main as _main
    return _main(argv)


def tiq_main(argv: list[str] | None = None) -> int:
    from .tiq import main as _main
    return _main(argv)
