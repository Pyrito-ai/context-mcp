# Upstream provenance

Context MCP 0.1.0 was extracted from the `integrations/pyrito-context` tree in
[`Pyrito-ai/pyrito-mind`](https://github.com/Pyrito-ai/pyrito-mind).

- Merged pull request: `Pyrito-ai/pyrito-mind#14`
- Merge commit: `348ac0e72c09bfd9cdd09f1ee3f291489ccabdce`
- Context implementation commit: `d89d9afefb46a469514f6d4a8a1cdd78ba6ae3d1`
- Extracted: 2026-09-03

The extracted implementation includes the invocation-only change: context is
not loaded on session start, and the old automatic startup hook is not shipped.

## Ownership after extraction

This repository is the distribution source for the teammate-facing Context MCP
plugin. `pyrito-mind` remains the source for the server-side MemoryProxy,
MemoryKnowledge, MemoryCore, identity, and ACL implementation.

The repositories do not sync automatically. A later client-integration change
made under `pyrito-mind/integrations/pyrito-context` must be deliberately
ported here, tested, and released. Server contract changes must remain backward
compatible with the plugin or be paired with a Context MCP release.

## Verify a local Pyrito Mind checkout

Run the read-only comparison from this repository:

```bash
python3 scripts/check_upstream.py ../pyrito-mind
```

The check compares only the files that were extracted. Plugin manifests,
packaging tests, and standalone documentation are intentionally local to this
repository.
