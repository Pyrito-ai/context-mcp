# Context MCP verification - 2026-09-03

## Source carried forward

- Pyrito Mind pull request: `Pyrito-ai/pyrito-mind#14`
- Pyrito Mind merge commit: `348ac0e72c09bfd9cdd09f1ee3f291489ccabdce`
- Context implementation commit: `d89d9afefb46a469514f6d4a8a1cdd78ba6ae3d1`
- Result: the extracted implementation files match the merged
  `integrations/pyrito-context` tree byte for byte.
- Invocation behavior: explicit only. No session-start hook is shipped.

## Package checks

- Python unit and contract tests: 17 passed.
- Codex plugin validator: passed.
- Claude plugin manifest validation in strict mode: passed.
- Claude marketplace validation in strict mode: passed.
- Secret scan: no embedded bearer token found.
- Fresh clone of the pushed GitHub repository: all tests and validators passed.

## Distribution checks

- GitHub repository: `Pyrito-ai/context-mcp`
- Visibility: private.
- Default branch: `main`.
- Verified release version: `0.1.1`.
- Codex marketplace registration and plugin installation: passed.
- Claude Code marketplace registration and plugin installation: passed.
- Both installed packages expose three skills: `prepare-context`,
  `capture-session`, and `invoke-agent`.

## Live checks

### Claude Code

A fresh read-only Claude process invoked `prepare-context` for Artemesia.
It resolved the Artemesia wiki and returned five results across two pages,
including a valid wiki citation. It returned no MemoryCore memories and made no
writes. Result: passed.

Claude's `plugin details` command reports zero MCP servers even though its
installed plugin metadata contains the validated `pyrito-context` server. The
successful fresh-process retrieval confirms the server is loaded at runtime;
the inventory count is a CLI reporting discrepancy.

### Codex

A fresh ephemeral Codex process loaded `$context-mcp:prepare-context`, resolved
the `pyrito-context/prepare_context` tool, and attempted the call. The
non-interactive runner then denied the tool because its approval policy was
`never`. This confirms plugin and MCP discovery. A normal interactive Codex
session still needs one read-only approval to complete the final live retrieval
acceptance check.

## Known boundary

This repository distributes the client plugin. The MCP service and all
identity, team, asset, ACL, MemoryKnowledge, and MemoryCore enforcement remain
in the deployed Pyrito Mind/MemoryProxy system. The two repositories do not
sync automatically; coordinated changes must be deliberately ported and
released.
