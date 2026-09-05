# Context MCP

Context MCP gives Claude Code and Codex the same authenticated, explicitly invoked Pyrito Mind workflows without requiring teammates to install or run the Pyrito Mind application repository. The MCP server runs on the Pyrito VPS; this repository is the small client plugin installed on each teammate's computer.

## Teammate setup without GitHub access

Teammates do not need a GitHub account, repository access, or command-line
experience. Give them their personal Context MCP key through a secure handover,
then have them copy one prompt into Claude Code or Codex:

- [Copy-and-paste teammate prompts](docs/TEAMMATE-SETUP.md)
- [Agent installation runbook](docs/AGENT-INSTALL.md)

The agent performs the public download and installation. The teammate only
enters their personal key through a hidden local input when prompted, restarts
their agent once, and pastes the verification prompt. The key must never be
pasted into an agent conversation, an email, a GitHub field, or a repository
file.

It configures:

- a remote Streamable HTTP MCP server named `pyrito-context`;
- bearer authentication from `PYRITO_CONTEXT_TOKEN` at runtime;
- host-native `prepare-context`, `capture-session`, and `invoke-agent` skills.

Context retrieval is invocation-only. Starting a session, naming a client, or changing work direction does not load Pyrito Mind context. The user must invoke `$prepare-context` or directly ask the agent to load or use Pyrito Mind context.

`capture-session` is explicit-only. It creates a concise record of decisions, results, relevant facts, and open work, then calls the bounded `capture_session` MCP tool. It never uploads a raw transcript, reasoning, tool output, or credentials.

`invoke-agent` lets the current session adopt one of the user's Pyrito Mind Agents. It calls the read-only `prepare_agent` MCP tool once, which returns a bounded activation pack: the Agent's name, description, prompt, and the full `SKILL.md` content of up to three of that Agent's Skills relevant to the stated direction. The host session then acts in that role for the task. No background worker or separate process is launched, and model prompts still never pass through Pyrito.

## What runs where

- **On the Pyrito VPS:** MemoryProxy, MemoryKnowledge, MemoryCore, identity, ACL enforcement, and the Context MCP endpoint.
- **On the teammate's computer:** Claude Code or Codex, this plugin, and the teammate's personal token in `PYRITO_CONTEXT_TOKEN`.
- **Not in the path:** Pyrito does not proxy the teammate's model prompts or model responses. The agent calls the MCP only when a context skill is invoked.

## Requirements

- Claude Code and/or Codex installed;
- a personal `sk-mem` key exported as `PYRITO_CONTEXT_TOKEN`;
- network access to the operator-provided Context MCP endpoint.

The endpoint must end in the canonical path `/knowledge-mcp`. The bootstrap intentionally has no default hostname.

For the Pyrito-hosted MVP, the approved public endpoint is:

```text
https://proxy.memory.pyrito.com/knowledge-mcp
```

Only MemoryProxy is public. MemoryKnowledge remains on its private service
address and must not receive a Caddy route. Production keeps raw Knowledge
query/reference telemetry explicitly disabled while retaining the proxy's
metadata-only operational audit; bearer keys, queries, page refs, and page
content are never operational log fields.

## Install as a plugin

Export the token through your operating system, password manager, or shell profile. Do not put it in a repository file.

For the hosted Pyrito service, set:

```bash
export PYRITO_CONTEXT_TOKEN='your-personal-key'
```

Use your operating system's persistent environment settings or a password-manager integration so the variable exists before Claude Code or Codex starts.

### Codex

```bash
codex plugin marketplace add Pyrito-ai/context-mcp
codex plugin add context-mcp@context-mcp
```

Start a new Codex session after installation. The plugin supplies the bounded MCP registration and all three skills.

### Claude Code

Run these commands inside Claude Code:

```text
/plugin marketplace add Pyrito-ai/context-mcp
/plugin install context-mcp@context-mcp
/reload-plugins
```

Claude Code reads the same token from the environment and loads the plugin's HTTP MCP definition.

## Direct bootstrap fallback

The guarded Python bootstrap remains available for older clients or managed machines where plugin installation is not used. Python 3.9 or later is required for this route.

From the cloned Context MCP repository, run:

```text
python3 bootstrap.py install \
  --host both \
  --endpoint https://proxy.memory.pyrito.com/knowledge-mcp
```

On Windows, use the equivalent `python` or `py -3` launcher.

Use `--host claude` or `--host codex` for one client. If a `pyrito-context` MCP registration already exists, the installer stops instead of overwriting it. Validate the existing entry or remove it explicitly with the relevant host CLI before reinstalling.

The installer:

1. checks the endpoint shape and that `PYRITO_CONTEXT_TOKEN` is present without printing it;
2. uses each host's own CLI to write its MCP registration;
3. copies the bundled skills into each selected host's user skill directory.

The installer stops if any bundled skill already exists instead of overwriting user-managed content.

Restart the clients after installation so the explicit skills appear.

Validate the installed endpoint, environment reference, absence of the legacy automatic hook, and skills:

```text
python3 bootstrap.py validate \
  --host both \
  --endpoint https://proxy.memory.pyrito.com/knowledge-mcp
```

Validation never prints the token or raw host configuration.

## Migrate an existing automatic installation

Older releases installed a `SessionStart` hook. Remove only that Pyrito-owned hook and install any missing explicit skills with:

```bash
python3 bootstrap.py invocation-only --host both
```

The migration preserves unrelated hooks and existing valid skills. It removes the legacy `~/.pyrito-context/session_start.py` copy only when neither host still references it, and writes `.bak` files before changing host hook configuration. Restart the selected clients after migration.

## Manual templates

The `templates/` directory contains the minimal host-native MCP configuration for managed deployments. Replace `<PYRITO_KNOWLEDGE_MCP_URL>` with the complete HTTPS URL ending in `/knowledge-mcp`. Never replace `PYRITO_CONTEXT_TOKEN` with an actual key.

Codex's template limits the server to the five context tools:

- `prepare_context`
- `search_knowledge`
- `read_knowledge_page`
- `prepare_agent`
- `capture_session`

The Codex server is `required = false`: a temporary Knowledge outage must not prevent the teammate from starting a normal agent session. The first failed lookup should degrade clearly, while non-knowledge work remains available.

Claude Code does not provide an equivalent MCP tool allowlist in its shared MCP file, so the server remains the enforcement boundary. `capture_session` is omitted from `tools/list` unless the separate server-side `knowledge.captureEnabled` switch is enabled. Personal MemoryCore recall in `prepare_context` is independently controlled by `knowledge.memoryRecallEnabled`; both switches default to false.

MemoryProxy sends `x-tdai-content-telemetry: disabled` on every internal
MemoryCore request. MemoryCore still records operational recall fields such as
latency, strategy, hit count, and top score, but omits the query and recalled
content snippets. Content telemetry remains available to other callers by
omitting that internal header.

## Skill usage

Only when you want Pyrito Mind context for the current work:

```text
$prepare-context
```

At the end of useful work, only when the user wants to save it:

```text
$capture-session
```

To act as one of your Agents for a task:

```text
Invoke the SEO Reviewer agent for Artemesia and audit the homepage copy.
```

The host calls `prepare_agent` with `agent_hint: "SEO Reviewer"`, `client_hint: "Artemesia"`, and the audit as `direction`, states which Agent was activated, and follows the returned prompt and Skills for that task. `$invoke-agent` works as an explicit trigger. The persona ends with the task; system and user instructions always take precedence over returned content.

The MCP verifies the personal key and derives the team, user, and caller-owned agent server-side for both `capture_session` and `prepare_agent`. Client-supplied identity fields are ignored, and an Agent that is missing, archived, owned by someone else, or ambiguously named fails without revealing whether it exists. Repeating the same stable `capture_id`, or the same summary when no ID is available, returns a duplicate receipt instead of writing it again.

## Host limitations

- An unconfigured Claude or Codex installation has no automatic access; each teammate needs one-time MCP registration and their own token.
- Local Codex MCP configuration is shared by Codex CLI, the IDE extension, and the ChatGPT desktop app for that host. ChatGPT web does not read it.
- Claude Code expands `${PYRITO_CONTEXT_TOKEN}` in MCP headers. Codex uses `bearer_token_env_var`, so neither host stores the token value in its MCP configuration.
- Installation preflights every requested host and adds all new MCP registrations before writing skills. A later failure removes only registrations that this run proved absent and then added. The invocation-only migration snapshots changed hook files and restores them if the migration fails.

## Verification sources

The templates follow the current official MCP schemas:

- [Claude Code MCP](https://code.claude.com/docs/en/mcp)
- [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

Run the package tests with:

```text
python3 -m unittest discover -s tests -v
```

Validate the plugin manifests with:

```text
python3 /path/to/plugin-creator/scripts/validate_plugin.py .
claude plugin validate .
```

## Source provenance and future changes

Version 0.1.0 was extracted from the exact `integrations/pyrito-context` tree merged in Pyrito Mind PR #14. See [UPSTREAM.md](UPSTREAM.md) for the pinned commits and the read-only comparison command.

Future server work stays in `pyrito-mind`. Future teammate installation, skill, and client MCP configuration work belongs here. The repositories do not update one another automatically, so any later change to the old integration directory must be deliberately ported and released.
