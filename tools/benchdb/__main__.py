"""Command line entry: python -m tools.benchdb <validate|build> [args]."""

from __future__ import annotations

import sys

from . import build, validate

USAGE = (
    "usage: python -m tools.benchdb validate [data/database.json]\n"
    "       python -m tools.benchdb build [--check] [data/database.json] [public/benchmarks.v1.json]\n"
)


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help"}:
        print(USAGE, end="")
        return 2
    command, rest = args[0], args[1:]
    if command == "validate":
        return validate.main(rest)
    if command == "build":
        return build.main(rest)
    print(USAGE, end="")
    return 2


if __name__ == "__main__":
    sys.exit(main())
