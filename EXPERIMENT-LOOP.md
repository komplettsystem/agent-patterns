# Experiment Loop

A pattern for hypothesis-driven, autonomous agent iteration with explicit commit/discard logic.

Derived from [Karpathy's autoresearch project](https://github.com/karpathy/autoresearch) and his [overnight experiment loop](https://thenewstack.io/karpathy-autonomous-experiment-loop/): an agent modifies code, runs a fixed-time experiment, keeps the result if it improved, discards if not, and repeats — unsupervised, until manually stopped or stopping criteria are met.

---

## When to Use

Use the experiment loop when:
- You have a **measurable quality signal** — a score, a metric, a rubric that objectively improves or doesn't
- You want an agent to **run overnight or unsupervised** without human check-ins mid-loop
- You need a **quality filter**: only findings that improve the signal get committed; dead ends are discarded

Use the [research loop](RESEARCH-LOOP.md) instead when:
- The goal is encyclopedic coverage of a topic (accumulation, not validation)
- There is no objective quality signal — just "what do we know?"
- Human review after each iteration is feasible and desired

They compose well: use the research loop to build domain knowledge, use the experiment loop to validate specific hypotheses before they graduate into the knowledge base.

---

## The Three-Part Brief (program.md)

Before the agent starts, the human writes a brief — a short document that carries three kinds of content at once:

1. **Instructions** — what hypothesis to test, what direction to explore
2. **Constraints** — what must not change, what's out of scope, what rules are fixed
3. **Stopping criteria** — what condition ends the loop (a target score, N iterations, a specific outcome)

This brief is the human's entire contribution to each loop run. Keep it short — the agent reads it before every iteration.

**Example structure:**
```markdown
## Hypothesis
[What you believe to be true. Be specific and falsifiable.]

## Research direction
[What to investigate to test this hypothesis. What evidence would confirm or refute it.]

## Constraints
- Do not change X
- Assume Y is fixed
- Only consider sources from Z

## Done when
[Explicit condition: "when hypothesis is supported by 3+ independent sources" or
"when quality score reaches 80" or "after 5 iterations"]
```

---

## The Loop

```
WHILE stopping_criteria not met:
  1. Form or refine a specific hypothesis
  2. Run a research/experiment pass (fixed scope or time budget)
  3. Measure against quality signal
  4. IF quality improved → commit (update artifact, log finding)
     IF quality unchanged or worse → discard (revert, log why, try different angle)
  5. Update the brief with what was learned
```

**Fixed scope per iteration** — each pass has a bounded budget (time, token count, or number of sources). Don't let a single iteration run indefinitely. If the hypothesis isn't resolved within the budget, log the partial finding and move to the next iteration.

**Commit/discard is binary** — a finding either improves the quality signal or it doesn't. Don't keep "somewhat useful" findings that don't move the score. Partial evidence goes into the log, not the artifact.

**The agent does NOT pause to ask the human** mid-loop. The brief encodes all the human's intent upfront. If the agent hits a decision point the brief doesn't cover, it logs it and continues with the next hypothesis rather than waiting.

---

## Quality Signal

The experiment loop requires a measurable quality signal. Examples:

| Context | Quality signal |
|---|---|
| ML training | Validation loss / bits-per-byte on held-out set |
| Discovery brief | Quality scorecard score (0–100 across dimensions) |
| Knowledge base article | Evidence strength: Supported → Anecdotal → Unverified |
| Code | Test pass rate + coverage |
| PRD | Review agent scores across cross-functional dimensions |

If you can't define a quality signal, use the research loop instead.

---

## Logging

Every iteration, commit or discard, gets logged. The log is how the human reviews what happened overnight.

Minimum log entry per iteration:
```
Iteration N | [timestamp]
Hypothesis: [what was tested]
Approach: [what the agent did]
Result: [what was found]
Quality delta: [score before → after, or "no change"]
Decision: COMMIT | DISCARD
Reason: [why]
```

The log lives alongside the artifact. It's the audit trail that lets the human pick up where the agent left off.

---

## What It Adds Over the Research Loop

| Dimension | Research Loop | Experiment Loop |
|---|---|---|
| Orientation | Encyclopedic — what do we know? | Scientific — does this hypothesis hold? |
| What gets committed | Everything above coverage threshold | Only findings that improve quality signal |
| Handling weak evidence | Included if relevant | Discarded if it doesn't move the score |
| Rollback | No — KB only grows | Yes — discard and log dead ends |
| Time per iteration | Implicit (PR cadence) | Explicit fixed budget |
| Stopping criteria | 80–90% coverage (self-assessed) | Defined in the brief before loop starts |
| Human involvement | PR review after each iteration | Brief written before; review log after |

**Combined use:** run the experiment loop inside each research loop iteration. Before a finding graduates into a KB article, it passes through the experiment loop's quality filter — evidence is confirmed, not just collected.

---

## Related Patterns

- **[RESEARCH-LOOP.md](RESEARCH-LOOP.md)** — accumulation-oriented; use when building encyclopedic coverage; experiment loop is the quality filter that complements it
- **[AGENTIC-ENGINEERING.md](AGENTIC-ENGINEERING.md)** — the broader approach; experiment loop is one concrete application of autonomous agent orchestration
