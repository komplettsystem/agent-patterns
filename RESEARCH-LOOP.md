# Research Loop

A pattern for building persistent, compounding knowledge bases through iterative LLM-driven research.

Inspired by [Andrej Karpathy's LLM Wiki pattern](https://x.com/karpathy/status/2039805659525644595) and his [reference implementation](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

---

## When to Trigger

When a user asks for research, first decide: **is this trivial or persistent?**

Ask yourself:
- Will this answer be useful again in future sessions?
- Does the topic have enough breadth to warrant multiple articles?
- Is this domain central to the project's ongoing work?

If **yes** to any → trigger the research loop and build a knowledge base.
If **no** → answer inline, do not persist.

When in doubt, ask the user: *"Should I build a persistent knowledge base for this topic, or is a one-off answer sufficient?"*

---

## Directory Structure

Place the knowledge base under the project root:

```
research/
  raw/          # shared collection zone — agent + human both contribute
  kb/           # compiled wiki — one .md file per concept
    index.md    # master index: all articles with one-line descriptions
  gaps.md       # open research questions, prioritized
```

`raw/` is a **shared collection zone**:
- **Agent writes**: Glean search results, web research, saved articles, paper summaries, scraped content
- **Human drops in**: internal documents, business numbers, private data, findings the agent can't reach

Both feed the same compilation step. There is no ownership distinction in `raw/` — the rule is append-only, not who appends. Neither party edits files already in `raw/`; they only add new ones.

The `kb/` directory is agent-maintained. The human rarely edits it directly — they redirect via PR review instead.

---

## The Loop

### 1. Ingest
Collect source material into `raw/`. Run Glean and web searches and save results as individual files. Each file should be self-contained: a saved article, a paper summary, a URL + key excerpts, or raw notes. If the human has dropped internal documents or proprietary data into `raw/`, include those in the same pass. Do not synthesize yet.

### 2. Compile
For each new item in `raw/`, update or create articles in `kb/`. Each article covers one concept:
- Summary of what is known
- Backlinks to raw sources
- Cross-references to related KB articles

Update `kb/index.md` — one line per article, with a short description.

### 3. Gap Analysis
Review the index and existing articles. Produce a prioritized `gaps.md`:
- List sub-topics of the domain that are missing or shallow
- Flag contradictions or unverified claims
- Identify which gaps matter most for the project's goals

### 4. Open a Pull Request
Commit all changes (`raw/`, `kb/`, `gaps.md`) and open a PR. The PR description should include:
- What was added or updated this iteration
- Current coverage estimate (see below)
- Top 3–5 open gaps driving the next iteration

**Wait for the PR to be merged before continuing.** Merge = human approval to proceed.

### 5. Loop
On the next iteration, pull the merged state and research the highest-priority gaps from `gaps.md`. Repeat from step 1.

---

## Coverage Assessment

After each gap analysis, self-assess coverage as a percentage:

1. List all known sub-topics of the domain (from the index + gaps.md)
2. For each sub-topic, mark: covered / shallow / missing
3. Coverage = covered / total sub-topics
4. Report this in the PR description

**Target: 80–90% coverage.** Stop the loop when coverage is in this range or when `gaps.md` contains only low-priority or out-of-scope items. Full 100% coverage is not the goal — useful working knowledge is.

---

## Division of Labor

| Human | Agent |
|---|---|
| Drop internal docs, proprietary data, and private findings into `raw/` | Search Glean + web, save results into `raw/` |
| Direct research focus and topic scope | Compile `raw/` into KB articles |
| Review and merge PRs | Perform gap analysis each iteration |
| Decide when coverage is sufficient | Write and maintain all KB articles and the index |

Both contribute to `raw/`. Neither edits files already there. The KB is the agent's artifact; the human steers it through PR review.

The human's signal to continue the loop is merging the PR. The human's signal to stop is closing the PR or leaving a comment saying coverage is sufficient.

---

## Rules

- **One article per concept.** Don't bundle unrelated ideas into one file.
- **Raw is append-only.** Never edit or delete files in `raw/` after they've been added — by either the agent or the human. Add new files; don't modify existing ones.
- **Index is always current.** Update `kb/index.md` in the same commit as any article change.
- **Gaps are prioritized.** `gaps.md` is not a dump — rank by relevance to project goals.
- **PRs are the checkpoint.** Never start a new iteration on an unmerged PR.
- **Coverage is honest.** If a sub-topic is shallow, mark it shallow — don't count it as covered.
