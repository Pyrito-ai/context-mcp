# Automatic synchronization

## Purpose

`context-mcp` is canonical for the teammate-facing client payload. When that
payload changes on `main`, GitHub Actions copies only the declared files into a
fresh Pyrito Mind checkout and opens or updates a pull request. The workflow
cannot merge the pull request and cannot push directly to `pyrito-mind/main`.

Pyrito Mind remains canonical for the Context MCP server, identity, ACL,
MemoryKnowledge, and MemoryCore implementation.

## Synchronized boundary

The allowlist lives in `sync/pyrito-mind.json`.

Synchronized:

- `bootstrap.py`
- `skills/**`
- `templates/**`
- `tests/test_bootstrap.py`
- the generated `CONTEXT_MCP_REVISION` commit pin

Not synchronized:

- either plugin manifest
- marketplace metadata
- standalone documentation
- packaging and synchronization tests
- Pyrito Mind's integration README
- any server code

Stale files are removed only inside the declared `skills` and `templates`
directories. Files elsewhere in Pyrito Mind are never deletion candidates.

## One-time GitHub App setup

Create an organization-owned GitHub App named `Pyrito Context Sync` with:

- Repository permissions: **Contents — Read and write**
- Repository permissions: **Pull requests — Read and write**
- Metadata: **Read-only**
- No organization, issues, actions, administration, or secrets permissions
- Installation limited to `Pyrito-ai/pyrito-mind`

Generate one private key for the App. In the `Pyrito-ai/context-mcp` repository,
create:

- Actions variable `PYRITO_SYNC_APP_ID` containing the numeric App ID
- Actions secret `PYRITO_SYNC_PRIVATE_KEY` containing the complete PEM private key

Do not use a personal access token. The App installation can be revoked without
affecting a teammate's GitHub account and cannot access repositories beyond its
installation.

Configure both values before merging the synchronization workflow. If either is
missing, the workflow fails before checking out or modifying Pyrito Mind.

## Normal operation

1. Merge a reviewed client-payload change into `context-mcp/main`.
2. `Sync Context MCP to Pyrito Mind` runs the complete Context MCP test suite.
3. It mints a short-lived token for the target-only GitHub App installation.
4. It synchronizes the manifest-bounded payload into a fresh `pyrito-mind/main`
   checkout and runs the mirrored bootstrap tests.
5. If there is a difference, it replaces the automation-owned branch
   `automation/context-mcp-sync` using `--force-with-lease` and creates or
   updates one pull request.
6. Pyrito Mind's `Context MCP Compatibility` workflow verifies that the server's
   discovered tools still exactly match the mirrored Codex allowlist.
7. A person reviews and merges the Pyrito Mind pull request.

No difference means no branch update and no pull request.

## Manual verification

From a Context MCP checkout beside Pyrito Mind:

```bash
python3 scripts/check_upstream.py ../pyrito-mind
```

To preview the exact changes without touching a real checkout, use a temporary
clone. The synchronizer intentionally writes its target, so do not point it at a
working directory with uncommitted integration changes.

## Recovery

- Disable the workflow in GitHub Actions to stop new runs.
- Close the open synchronization pull request if its contents are unwanted.
- Delete `automation/context-mcp-sync`; `main` remains untouched.
- Revoke the GitHub App installation or delete its private key to remove access.
- Rotate a compromised key by generating a new App key, replacing
  `PYRITO_SYNC_PRIVATE_KEY`, and deleting the old key.

The workflow leaves a durable source commit in
`integrations/pyrito-context/CONTEXT_MCP_REVISION`, so any mirrored state can be
traced back to an exact Context MCP commit.
