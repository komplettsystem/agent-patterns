# Agentic Engineering

A paradigm for working with AI agents where humans act as orchestrators and oversight, not authors.

Coined by [Andrej Karpathy (2026)](https://thenewstack.io/vibe-coding-is-passe/): *"Agentic because the new default is that you are not writing the code directly 99% of the time, you are orchestrating agents who do and acting as oversight. Engineering because there is an art and science and expertise to it."*

---

## The Core Shift

| Old model | Agentic model |
|---|---|
| Human authors the artifact | Human writes the brief; agent authors the artifact |
| Agent assists on demand | Agent runs autonomously; human reviews output |
| Sequential, human-paced | Parallel agents, agent-paced |
| Human fills in gaps | Human curates inputs; agent surfaces gaps |

The human's job is: define what success looks like, curate the inputs the agent can't access, and review output like a senior engineer reviews a PR. Not rewrite — review, redirect, approve.

---

## The Three Inputs a Human Provides

Before handing off to an agent, the human writes three things:

1. **Goal** — what the artifact should accomplish; what problem it solves
2. **Constraints** — what is out of scope, what must not change, what rules apply
3. **Done criteria** — what "good enough to proceed" looks like (a score, a checklist, an explicit condition)

These three inputs are the human's real work. Everything else is the agent's.

This maps directly to Karpathy's `program.md` in the [autoresearch pattern](https://github.com/karpathy/autoresearch): a short doc that simultaneously carries instructions, constraints, and stopping criteria.

---

## Parallel Agents

Don't run research or analysis sequentially. When a task has multiple independent dimensions, assign each to a separate agent thread running in parallel:

**Example — PM discovery:**
- Agent A: market sizing + competitive analysis
- Agent B: internal precedent search (past initiatives, PRDs, post-mortems)
- Agent C: user problem validation (interviews, support tickets, analytics)
- Agent D: OKR alignment check against strategy files

Their outputs merge into a single compiled artifact. The human reviews the merge, not each thread.

**When to parallelize:** any time two research or analysis tasks don't depend on each other's output. The bottleneck should be the human review, not the agent work.

---

## Human as Code Reviewer

The human's review role mirrors an engineer reviewing a PR:

- **Approve** — output meets the done criteria; proceed
- **Request changes** — specific, directed feedback; agent runs another pass
- **Reject** — wrong direction; human resets goal or constraints and re-runs

Don't rewrite the agent's output directly. Either approve it or give the agent a corrected direction. Rewriting trains the wrong loop and loses the audit trail.

---

## Inputs the Human Must Provide Directly

Agents can't access everything. Some inputs only the human can provide:

- Internal business numbers not indexed by search tools
- Private documents, meeting notes, or decisions made verbally
- Institutional knowledge that exists in someone's head, not a file
- Judgment calls about strategy, priority, or trade-offs

These go into a **human-curated input zone** (a `raw/` directory, a shared doc, a context file) that the agent reads but never modifies. The human drops inputs there; the agent compiles them into the working artifact.

**The rule:** agents own the compiled output; humans own the raw input. Never invert this.

---

## Ascending Abstraction

The leverage in agentic engineering comes from ascending layers of abstraction. Each layer you hand off to agents frees you to operate at a higher level:

1. Writing code → orchestrating agents that write code
2. Running experiments → orchestrating agents that run experiments
3. Doing research → orchestrating agents that research and synthesize
4. Filling in documents → orchestrating agents that draft documents for review

The highest-leverage work is: setting up long-running orchestrators with the right tools, memory, and instructions — so the agent can operate without constant check-ins.

---

## Related Patterns

- **[RESEARCH-LOOP.md](RESEARCH-LOOP.md)** — how to build a persistent knowledge base through iterative agent-driven research; the KB loop is an application of agentic engineering to domain knowledge
- **[EXPERIMENT-LOOP.md](EXPERIMENT-LOOP.md)** — hypothesis-driven variant with explicit commit/discard logic; complements agentic engineering with a quality filter for evidence
