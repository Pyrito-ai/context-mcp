# Set up Pyrito Context with your agent

This setup does not require a GitHub account, access to any private repository,
or confidence with a command line. Your Claude Code or Codex agent will do the
technical work.

## What you need

1. Claude Code or Codex already installed and open.
2. The secure handover from your Pyrito administrator.
3. The Context MCP endpoint from that handover. It is not a password and ends
   in `/knowledge-mcp`.
4. Your personal Context MCP key from that handover. Treat this key like a
   password.

Do not paste the personal key into the agent conversation. The agent will pause
and give you a hidden local input when it needs the key.

## Installation prompt

Replace only `<CONTEXT ENDPOINT>` with the endpoint from your handover. Do not
put your personal key into this prompt.

```text
Set up Pyrito Context MCP for me from start to finish.

Use only this public repository:
https://github.com/Pyrito-ai/context-mcp

My Context MCP endpoint is:
<CONTEXT ENDPOINT>

I am not comfortable with GitHub or command-line setup, so perform the technical
steps yourself and explain only the actions I need to take.

Security and scope rules:
- The public Context MCP repository is the only repository you may download.
- Do not request access to Pyrito-ai/pyrito-mind or any other private repository.
- Do not ask me to sign into GitHub, create a GitHub account, configure an SSH
  key, fork a repository, or make a commit.
- Do not ask me to paste my personal Pyrito key into this conversation.
- When the key is required, pause and provide a hidden local input suitable for
  this operating system. The key must not be echoed, printed, logged, committed,
  or placed in a project file.
- Install only for the agent host I am using now unless I explicitly ask for
  another host too.
- Do not enable automatic context loading. Pyrito context must remain explicitly
  invoked.

First confirm that the repository is reachable without GitHub authentication.
Then read docs/AGENT-INSTALL.md from its main branch and follow that runbook.
Use the guarded bootstrap with my endpoint, preserve unrelated settings, and
run its non-secret validation. Tell me clearly when I need to restart the agent.
Stop after giving me the post-restart verification prompt. Do not claim that the
setup works until a new session completes the live read-only verification.
```

The agent may ask for permission to download the public repository or update
your local agent settings. That is normal. A request for GitHub credentials or
private-repository access is not normal and should be declined.

## After restarting: verification prompt

Open a new Claude Code or Codex session and paste this prompt:

```text
Verify my Pyrito Context MCP setup now.

Do not reinstall anything and do not write to Pyrito Mind. Confirm that the
pyrito-context MCP and its explicit context skills are available, then invoke
$prepare-context for this direction: "Confirm my authorized Pyrito Mind access
and return a short list of the wiki spaces I can use."

Report whether the live authenticated read succeeded, which team was resolved,
and which wiki spaces were returned. Do not display credentials, tokens, raw
configuration, or unrelated wiki content. If verification fails, diagnose the
specific local registration, restart, endpoint, or credential problem and guide
me through the smallest safe correction.
```

Setup is complete only when this live authenticated read succeeds. Seeing files
or a configured MCP entry is not enough.

## Everyday use

Pyrito does not load context automatically. Ask for it when it would help:

```text
$prepare-context
```

You can also be specific:

```text
Use Pyrito Mind context for BuildBargains while we plan this task.
```

Saving a useful outcome is also explicit:

```text
$capture-session
```

Your administrator controls your team and wiki access. Installing the client
cannot grant access that your personal key does not already have.
