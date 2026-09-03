# Changelog

## 0.1.2 - 2026-09-03

- Make Context MCP the canonical source for the mirrored Pyrito Mind client
  integration.
- Add guarded, one-way pull-request synchronization using a target-scoped
  GitHub App credential.
- Add a manifest-bounded synchronizer, drift checker, revision pin, and tests.

## 0.1.1 - 2026-09-03

- Declare Claude's MCP configuration through an explicit companion path
  supported by the Claude plugin schema.

## 0.1.0 - 2026-09-03

- Extract the merged Pyrito Context client integration from `pyrito-mind`.
- Package the remote Context MCP and three explicit skills for Codex and Claude Code.
- Preserve the invocation-only behavior from Pyrito Mind PR #14.
- Retain the guarded bootstrap and legacy automatic-hook migration path.
