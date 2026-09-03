#!/usr/bin/env python3
"""Compare extracted client files with a local Pyrito Mind checkout."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
EXTRACTED_PATHS = (
    "bootstrap.py",
    "skills/capture-session/SKILL.md",
    "skills/capture-session/agents/openai.yaml",
    "skills/invoke-agent/SKILL.md",
    "skills/invoke-agent/agents/openai.yaml",
    "skills/prepare-context/SKILL.md",
    "skills/prepare-context/agents/openai.yaml",
    "templates/claude.mcp.json",
    "templates/codex.config.toml",
    "tests/test_bootstrap.py",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pyrito_mind", type=Path, help="Path to a Pyrito Mind checkout")
    args = parser.parse_args()
    upstream = args.pyrito_mind.expanduser().resolve() / "integrations" / "pyrito-context"

    if not upstream.is_dir():
        print(f"error: Pyrito Context integration not found at {upstream}", file=sys.stderr)
        return 2

    differences: list[str] = []
    for relative in EXTRACTED_PATHS:
        local_path = ROOT / relative
        upstream_path = upstream / relative
        if not local_path.is_file():
            differences.append(f"missing locally: {relative}")
        elif not upstream_path.is_file():
            differences.append(f"missing upstream: {relative}")
        elif local_path.read_bytes() != upstream_path.read_bytes():
            differences.append(f"content differs: {relative}")

    if differences:
        print("Context MCP differs from the local Pyrito Mind integration:")
        for difference in differences:
            print(f"- {difference}")
        return 1

    print("Extracted Context MCP files match the local Pyrito Mind integration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
