# Agent Patterns — Status
_Last updated: 2026-09-23 · Project state: **active**_

Current state only; history is in the git log.

## State

| What | Now |
|---|---|
| Published | Base rules (`AGENT-BASE.md`, `AGENT-CODING.md`), three loops (research, experiment, triage), `MULTI-AGENT-COMPAT.md`, `scripts/check-agent-setup.sh`. Issues and PRs are closed |
| What the session hook does | Creates `AGENTS.md` / `AGENT.md` / `CLAUDE.md` in git repos that lack them, reports the Slack inbox, reports which tracked projects have a stale `STATUS.md`, and (opt-in, 2026-09-23) a daily count of transcript actions with no request found, from `scripts/audit-rule-compliance.py --summary` |
| Open | Projects still carry a copied base in their own `AGENTS.md` instead of referencing the shared rules |

## Next

| Action | Why |
|---|---|
| Write a pipeline loop (many objects, one table, an explicit next action per row) once a second project uses that shape | One project is not yet a pattern |
