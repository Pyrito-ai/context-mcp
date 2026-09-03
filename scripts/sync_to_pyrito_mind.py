#!/usr/bin/env python3
"""Synchronize the canonical client payload into a Pyrito Mind checkout."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from context_sync import SyncError, sync


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pyrito_mind", type=Path, help="Path to a Pyrito Mind Git checkout")
    parser.add_argument("--source-revision", required=True, help="Full Context MCP Git SHA")
    args = parser.parse_args()
    try:
        changed = sync(ROOT, args.pyrito_mind.expanduser(), args.source_revision)
    except SyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not changed:
        print("Pyrito Mind is already synchronized.")
        return 0
    print("Synchronized Context MCP payload:")
    for change in changed:
        print(f"- {change}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
