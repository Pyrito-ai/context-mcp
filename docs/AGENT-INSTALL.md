# Agent runbook for teammate installation

This runbook is for a Claude Code or Codex agent performing setup on behalf of a
non-technical teammate. The human should not need to understand Git or type the
installation commands.

## Required outcome

- Install from `https://github.com/Pyrito-ai/context-mcp`, which is public and
  does not require a GitHub account.
- Register only the current host against the administrator-provided HTTPS
  endpoint ending exactly in `/knowledge-mcp`.
- Keep the personal key out of the conversation transcript, command text,
  command output, repository files, and project files.
- Preserve unrelated MCP registrations, skills, hooks, and agent settings.
- Keep all Pyrito context and session capture explicitly invoked.
- Validate local configuration without displaying the key.
- Require a restart, then use the separate prompt for a real authenticated,
  read-only retrieval.

## Boundaries

Do not request or use:

- membership of the Pyrito-ai GitHub organization;
- access to `Pyrito-ai/pyrito-mind` or another private repository;
- a GitHub login, personal access token, SSH key, fork, or commit;
- the teammate's Pyrito key in chat;
- a shared administrator key or another person's key.

Do not place the repository inside one of the teammate's work projects. Use a
temporary directory or a clearly named user-level tools directory. Do not leave
the clone behind unless it is needed for the selected installation route.

## Procedure

### 1. Detect the current host and prerequisites

Determine whether the current session is Claude Code or Codex. Install only that
host by default. Confirm its executable and Python 3.9 or later are available.
If a prerequisite is missing, explain the single user action required and stop.

Do not install both hosts merely because both executables happen to exist.

### 2. Prove public access

Check the repository over unauthenticated HTTPS with interactive credential
prompts disabled. A suitable read-only check is:

```bash
GIT_TERMINAL_PROMPT=0 git -c credential.helper= ls-remote \
  https://github.com/Pyrito-ai/context-mcp.git HEAD
```

If Git requests credentials, stop. Do not authenticate or fall back to a private
repository. Report that the public distribution is unavailable.

### 3. Obtain the installer

Clone only the public repository into a temporary directory and check out its
default branch. Do not use `gh`, SSH, submodules, or another Pyrito repository.

Inspect `README.md`, `bootstrap.py`, and this runbook before execution. Confirm
that the supplied endpoint is absolute HTTPS, contains no embedded credentials,
and ends exactly in `/knowledge-mcp`.

### 4. Prepare the personal key without chat disclosure

First check only whether `PYRITO_CONTEXT_TOKEN` is already available. Never
print its value and do not run broad environment-dump commands.

If it is unavailable, pause. Tell the teammate to retrieve their personal key
from the secure handover and enter it through a hidden local input. Choose a
method appropriate to the operating system and client that:

- does not include the key in a command the agent writes;
- does not echo the key or expose it in command output or shell history;
- makes `PYRITO_CONTEXT_TOKEN` available when the selected client starts;
- uses the operating system credential store or an existing password-manager
  integration when available;
- requires restrictive user-only permissions for any fallback local secret
  file; and
- explains that the client must be fully restarted after the credential is set.

On macOS, prefer Login Keychain for storage. The `security
add-generic-password` command supports an interactive hidden password prompt
when `-w` is supplied as its final option without a value. For a terminal-launched
client, load the key from Keychain into `PYRITO_CONTEXT_TOKEN` without printing
it. For a GUI-launched client, ensure the environment is available to the newly
started GUI process rather than assuming a shell profile is inherited.

Do not improvise by inserting the key directly into an MCP JSON or TOML file.
Both supported hosts can reference `PYRITO_CONTEXT_TOKEN` instead.

### 5. Run the guarded installer

From the temporary public clone, run one of:

```bash
python3 bootstrap.py install --host codex --endpoint '<CONTEXT ENDPOINT>'
```

```bash
python3 bootstrap.py install --host claude --endpoint '<CONTEXT ENDPOINT>'
```

The endpoint is not secret, but it must be the exact value provided by the
administrator. Do not use the generic hosted endpoint from the plugin manifest
for a white-labelled or isolated tenant.

If `pyrito-context` or one of the bundled skills already exists, the bootstrap
will stop rather than overwrite it. Inspect and explain the conflict. Never
delete or replace an existing registration without the teammate's explicit
approval.

### 6. Validate locally

Run the matching validation command:

```bash
python3 bootstrap.py validate --host codex --endpoint '<CONTEXT ENDPOINT>'
```

or:

```bash
python3 bootstrap.py validate --host claude --endpoint '<CONTEXT ENDPOINT>'
```

Validation must confirm the endpoint, environment-variable reference, explicit
skills, and absence of the legacy automatic hook. Do not display raw host
configuration or the personal key.

Remove the temporary clone after successful validation. Keep the installed
user-level configuration and skills.

### 7. Restart and verify live access

Tell the teammate to quit the client completely and open it again. Provide the
verification prompt from `docs/TEAMMATE-SETUP.md`.

Do not claim completion in the installation session. The new session must invoke
`$prepare-context` and complete a live, authenticated, read-only call. A plugin
listing, copied skill, or successful local validation proves installation only,
not access to Pyrito Mind.

## Failure handling

- **Public repository unavailable:** stop without requesting GitHub credentials.
- **Key missing:** return to the hidden local input; never request it in chat.
- **HTTP 401:** check that the correct personal key is available to the restarted
  client. Do not print it and do not substitute an administrator key.
- **HTTP 403:** the key is authenticated but lacks the requested server-side
  access. Escalate to the Pyrito administrator rather than changing local files.
- **Wrong endpoint:** reinstall only after the teammate approves removal of the
  incorrect `pyrito-context` registration.
- **Existing skill or registration:** preserve it and report the exact path or
  registration name without dumping secret-bearing content.
- **Temporary service outage:** leave the MCP optional so unrelated agent work
  can continue.
