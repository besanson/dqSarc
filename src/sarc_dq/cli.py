"""``sarc-dq`` command-line entrypoint.

Phase 0 exposes one subcommand, ``smoke``, delegating to the benchmark runner so
``sarc-dq smoke`` and ``python -m benchmarks.phase0_smoke`` do the same thing.
"""

from __future__ import annotations

import sys
from typing import Any


def main(argv: Any = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "smoke":
        from benchmarks.phase0_smoke import main as smoke_main

        return smoke_main(args[1:])
    print("usage: sarc-dq smoke [--arm mock|live] [--episodes N] [--out PATH]")
    print("       (Phase 0 smoke test — the first hard-stop gate)")
    return 0 if (args and args[0] in {"-h", "--help"}) else 2


if __name__ == "__main__":
    raise SystemExit(main())
