---
name: capture-session
description: Save the useful outcomes of the current client session to the caller's authorized personal MemoryCore context when the user explicitly asks to capture it.
---

# Capture Session

Do not capture anything unless the user explicitly asks during the current session.

Create one concise Markdown session record containing only durable value:

- decisions and their rationale;
- completed work and meaningful results;
- client or project facts that will matter later;
- unresolved questions, owners, and next steps.

Exclude hidden reasoning, system or developer instructions, tool calls and outputs, credentials, routine conversation, and unsupported conclusions. Do not copy a raw transcript.

Call the `pyrito-context` MCP tool `capture_session` once with:

- `summary`: the session record;
- `client_hint`: the exact client or team;
- `recorded_at`: the current ISO-8601 time when available;
- `capture_id`: only when the host exposes a stable current-session identifier;
- `agent_hint`: only when the tool reports that more than one caller-owned agent exists.

If the client or team is unclear, ask one concise question before the call. Report the returned receipt accurately. A duplicate receipt means the existing capture was retained; an error means nothing was confirmed as saved. Do not retry an uncertain write without the same stable `capture_id` or the user's direction.
