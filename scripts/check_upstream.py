#!/usr/bin/env python3
"""Compare the canonical client payload with a local Pyrito Mind checkout."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from context_sync import SyncError, compare

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pyrito_mind", type=Path, help="Path to a Pyrito Mind checkout")
    args = parser.parse_args()
    try:
        differences = compare(ROOT, args.pyrito_mind.expanduser())
    except SyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if differences:
        print("Pyrito Mind differs from the canonical Context MCP payload:")
        for difference in differences:
            print(f"- {difference}")
        return 1

    print("Pyrito Mind matches the canonical Context MCP payload.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
