# Changelog

## 0.1.2 - 2026-09-05

- Add a low-tech, agent-guided teammate setup flow.
- Require public, unauthenticated installation without access to Pyrito Mind.
- Keep personal keys out of agent conversations and repository files.
- Add a separate post-restart prompt for real read-only access verification.

## 0.1.1 - 2026-09-03

- Declare Claude's MCP configuration through an explicit companion path
  supported by the Claude plugin schema.

## 0.1.0 - 2026-09-03

- Extract the merged Pyrito Context client integration from `pyrito-mind`.
- Package the remote Context MCP and three explicit skills for Codex and Claude Code.
- Preserve the invocation-only behavior from Pyrito Mind PR #14.
- Retain the guarded bootstrap and legacy automatic-hook migration path.
