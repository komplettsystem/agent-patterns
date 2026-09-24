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
    check-agent-setup.sh   ← Claude Code SessionStart hook: sets up AGENTS.md, CLAUDE.md and an AGENT.md stub in each repo, reports the inbox and stale STATUS.md files
```

**Where to start:** [AGENT-BASE.md](AGENT-BASE.md). Its rules are starting points, not
laws: a project's own rules override them, and so does what the work teaches.

## How a project uses them

```
any-project/
  AGENTS.md    ← the base guidelines, with the project's own rules below them
  CLAUDE.md    ← Claude Code entry point: "@AGENTS.md"
  AGENT.md     ← short redirect stub, only for Amp
```

`AGENTS.md` is the single source of truth per project. It is the cross-tool standard, so
agents that read it natively need nothing else. `CLAUDE.md` and the `AGENT.md` stub are
small pointers for the two agents that look for other filenames;
[MULTI-AGENT-COMPAT.md](MULTI-AGENT-COMPAT.md) covers how.

## Automatic setup in Claude Code (optional)

`scripts/check-agent-setup.sh` runs when a Claude Code session starts. In any git repo
without them, it creates `AGENTS.md` from `AGENT-BASE.md` (local copy first, GitHub as
fallback), an `AGENT.md` redirect stub for Amp, and a `CLAUDE.md` that imports
`AGENTS.md`. It never commits or pushes anything.

It doesn't update an existing `AGENTS.md`. After changing `AGENT-BASE.md`, run
`python3 scripts/sync-agent-base.py` to see which repos next to this one have a stale copy,
then `--apply` to update them. It replaces only the part above "Project-Specific
Guidelines", skips any repo whose copy has local edits that syncing would delete (and lists
those lines), and never commits.

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

**Optional liveness check**: a harness fails by being abandoned, so each session can
report which projects have let their `STATUS.md` go stale. Add to the same
`inbox.local.conf`:

```bash
LIVENESS_PROJECTS="project-a project-b"   # directory names next to this repo
LIVENESS_DAYS=14                          # optional, default 14
```

A project with no `STATUS.md` counts as stale. Without `LIVENESS_PROJECTS` the script
prints nothing about liveness.

**Optional rule audit**: written rules only count if something checks them. Each day's
first session can report how many actions in recent Claude Code transcripts had no request
for them in the preceding user message (external sends, destructive commands, commits),
using `scripts/audit-rule-compliance.py --summary`. Add to `inbox.local.conf`:

```bash
AUDIT_DAYS=7   # look-back window in days
```

The line is cached per day under `~/.cache/agent-patterns/`. It's a keyword heuristic, and
permission approvals aren't recorded in transcripts, so the counts are a reason to look,
not findings. If the audit fails, the session is told so rather than shown zeros.

## Adding project-specific rules

Edit the project's `AGENTS.md` and add rules below the `## Project-Specific Guidelines`
heading. Where they conflict with the base guidelines, the project's rules win.

## License

MIT, see [LICENSE](LICENSE).
