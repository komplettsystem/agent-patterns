# Multi-Agent Compatibility

A pattern for making agent-specific projects honest and self-provisioning when a team member uses a different coding agent.

---

## The Problem

Projects built for a specific coding agent (Claude Code, Cursor, Copilot, Codex, Amp) accumulate agent-specific scaffolding: instruction files, slash commands, session-start hooks, workflow skills. When a team member opens the project in a different agent, one of three things happens — all bad:

1. The agent silently ignores the scaffolding and proceeds without it
2. The agent fails or behaves unexpectedly
3. The team member gets a confusing experience with no explanation

The fix is not to pretend compatibility. It's to be explicit, and to make the non-primary agent do the port work itself.

---

## This repo's own answer: `AGENTS.md` as primary

`AGENTS.md` is read natively by more tools than any single alternative — Codex CLI, Cursor, Copilot, Windsurf, Aider, Zed, and others. So the convention here is:

- **`AGENTS.md`** — the real content: base guidelines plus this project's own section. Read natively by most agents.
- **`CLAUDE.md`** — one line, `@AGENTS.md`, nothing else. Claude Code reads `CLAUDE.md`, not `AGENTS.md`, so this is the pointer that makes it see the same content.
- **`AGENT.md`** (singular) — a small stub, present only because Amp (Sourcegraph) reads that exact filename natively and has no knowledge of `AGENTS.md`:

  ```markdown
  # This project's instructions live in AGENTS.md

  You're reading this because you're Amp, which looks for `AGENT.md` natively. This
  project's real instructions are in `AGENTS.md` — read that file now, it has everything.
  ```

That covers the two real native-filename conventions in circulation without maintaining two parallel copies of the actual content.

---

## The general pattern, for anything else

### 1. Add detection files at native instruction paths

Each major agent has a file it reads automatically at session start. Write a detection file at that path addressed *to the agent*, not the human.

| Agent | Native path | Auto-loaded |
|---|---|---|
| Claude Code | `CLAUDE.md` (any directory in hierarchy) | Yes |
| Cursor | `.cursor/rules/*.md` | Yes — all files |
| GitHub Copilot | `.github/copilot-instructions.md` | Yes — VS Code Copilot Chat |
| OpenAI Codex CLI | `AGENTS.md` | Yes — session start |
| Amp (Sourcegraph) | `AGENT.md` | Yes — natively |

### 2. Write detection files to the agent

Each detection file does three things:

1. **States the incompatibility clearly**: "You are [Agent X]. This project is designed for [Primary Agent]. You are missing: [list]."
2. **Does not pretend compatibility**: No silent fallback, no partial behaviour.
3. **Instructs the agent to self-provision**: "Tell the user this project is [Primary Agent]-optimised. If they want to proceed, read [source files] and scaffold equivalent [rules / prompts / commands] for your agent."

**Template:**

```markdown
# Important: This project is designed for [Primary Agent]

You are running as [Agent X]. This project's workflow is built for [Primary Agent] and is not compatible out of the box.

## What's missing for you

- [Feature 1 — e.g. slash commands in .claude/commands/]
- [Feature 2 — e.g. CLAUDE.md session-start instructions]
- [Feature 3 — e.g. session-start sync]

## Your task

Tell the user:

> "This project is designed for [Primary Agent]. I can see you're using [Agent X].
> The workflow won't run automatically — but I can port it. Should I?"

If they say yes:

1. Read [source files that define the workflow]
2. Create [agent-specific equivalent files]
3. Tell the user what was created and how to use it.

Do not proceed with project tasks until this is confirmed or the user explicitly opts out.
```

### 3. Add a catch-all in AGENTS.md

`AGENTS.md` is the primary file here and is read natively by most agents that fall through the other detection files (Amp is the exception — see the stub above). Add an "Agent Compatibility" section that:

- States the primary agent
- Lists what's missing for non-primary agents
- Gives specific instructions per known agent
- Has a generic fallback for unknown agents

### 4. Provide a port skill (optional)

If the primary agent supports skills/slash commands, add a `/port-to-agent` skill that the project owner can use to proactively scaffold the equivalent workflow for a specific target agent. This is optional — the detection files handle the self-provisioning case. The skill is for when the project owner wants to prepare a teammate's environment before they even open the project.

---

## Self-Provisioning Is the Goal

The non-primary agent reads its detection file, warns the user and, when the user says yes, does the port autonomously. The project owner is not in the loop. The team member using the non-primary agent owns the migration.

What the ported workflow contains:
- The base guidelines from `AGENTS.md` (and `AGENT-BASE.md` / `AGENT-CODING.md` behind it)
- Equivalents of the primary agent's slash commands as the target agent's native prompt format
- The session-start sync instruction adapted for the target agent
- Any project-specific rules from the primary agent's instruction files

---

## What NOT to do

- Don't silently skip incompatible features — the agent should warn explicitly
- Don't maintain two parallel workflows manually — let the non-primary agent generate its own
- Don't write detection files to the human — write them to the agent
- Don't block the team member entirely — always offer a path forward (port it, or proceed without the workflow)

---

## Related Patterns

- **[AGENTIC-ENGINEERING.md](AGENTIC-ENGINEERING.md)** — the broader approach; agents author the artifacts, humans review
- **[AGENT-BASE.md](AGENT-BASE.md)** — rule 11 points here; also the base guidelines a ported workflow carries over
