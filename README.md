# Agent Patterns

> **Status:** published for reference. Issues and pull requests are closed; these are
> working patterns shared as-is, not a maintained project.

Patterns for working with AI agents on real projects: how an agent should behave, and
the loops that turn single sessions into work that compounds. Written in plain markdown,
so they are not tied to one agent or vendor. The setup script is Claude Code specific.

## What's here

```
agent-patterns/
  AGENT-BASE.md            ← base guidelines for any project: code, documents, research
  AGENT-CODING.md          ← additions for projects with code
  AGENTIC-ENGINEERING.md   ← framing: the human sets goal, constraints and done criteria; agents author; the human reviews
  RESEARCH-LOOP.md         ← building a persistent knowledge base, with human checkpoints
  EXPERIMENT-LOOP.md       ← hypothesis-driven iteration, keeping only what improves a measured signal
  TRIAGE-LOOP.md           ← capture anywhere, file into projects later, with an expiry horizon
  MULTI-AGENT-COMPAT.md    ← when teammates open a project in a different coding agent
  scripts/
    check-agent-setup.sh   ← Claude Code SessionStart hook: sets up AGENT.md and CLAUDE.md in each repo
```

**Where to start:** [AGENT-BASE.md](AGENT-BASE.md). Its rules are starting points, not
laws: a project's own rules override them, and so does what the work teaches.

## How a project uses them

```
any-project/
  AGENT.md     ← the base guidelines, with the project's own rules below them
  CLAUDE.md    ← Claude Code entry point: "@AGENT.md"
```

`AGENT.md` is the single source of truth per project. Other coding agents get a one-line
pointer file in their own format; [MULTI-AGENT-COMPAT.md](MULTI-AGENT-COMPAT.md) covers
how.

## Automatic setup in Claude Code (optional)

`scripts/check-agent-setup.sh` runs when a Claude Code session starts. In any git repo
without them, it creates `AGENT.md` from `AGENT-BASE.md` (local copy first, GitHub as
fallback) and a `CLAUDE.md` that imports it. It never commits or pushes anything.

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          { "type": "command", "command": "/absolute/path/to/agent-patterns/scripts/check-agent-setup.sh" }
        ]
      }
    ]
  }
}
```

**Optional inbox check** ([TRIAGE-LOOP.md](TRIAGE-LOOP.md)): to have each session report
unfiled items from a Slack capture channel, create `inbox.local.conf` at the repo root
(gitignored):

```bash
INBOX_CHANNEL_NAME=your-inbox-channel
INBOX_CHANNEL_ID=C0123456789
```

Without that file the script prints nothing about an inbox.

## Adding project-specific rules

Edit the project's `AGENT.md` and add rules below the `## Project-Specific Guidelines`
heading. Where they conflict with the base guidelines, the project's rules win.

## License

MIT, see [LICENSE](LICENSE).
