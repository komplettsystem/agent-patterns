# Triage Loop

A pattern for capturing work from anywhere and filing it into project repos later,
without the capture channel becoming a graveyard.

Companion to [RESEARCH-LOOP](RESEARCH-LOOP.md) and [EXPERIMENT-LOOP](EXPERIMENT-LOOP.md).
Those two assume you are already sitting in the repo. This one is about the gap
between having a thought and being somewhere you can act on it.

---

## The Problem

Project repos only compound if things actually land in them. But most capture
happens away from the machine: on a phone, mid-conversation, between other tasks.
At that moment the repo path asks for four decisions (which repo, which file, what
structure, what wording) against a chat window's zero. Chat wins every time, and
the work quietly stops accumulating where it should.

The instinct is to make capture more disciplined. That fails, because discipline
is the scarce resource. Instead, **split capture from filing.**

- **Capture** must cost one line and no decisions, from any device.
- **Filing** is a session you sit down for, where an agent does the sorting.

Everything below exists to keep those two separate and to stop the queue between
them from rotting.

---

## Structure

Per project repo:

```
STATUS.md          # present tense, small, OVERWRITTEN — current state only
log/YYYY-MM.md     # past tense, dated, APPEND-ONLY — what happened and why
```

Plus one shared capture channel outside the repos: a chat channel, a notes file,
anything reachable from a phone that you do not have to operate yourself.

The split between `STATUS.md` and `log/` is what makes stale memory tractable:

- Log entries are dated past-tense facts. "2026-05-10, dropped X, ops cost too
  high." That is true forever and never needs curating.
- State is present tense and gets rewritten, not appended. It is the only thing
  that can go stale, it is small, and rewriting it is what triage does anyway.

The rule that keeps this working: **the log never asserts present-tense facts, and
STATUS.md never accumulates.** Violate either and you are back to managing rot
across the whole corpus.

---

## The Loop

### 1. Capture
One line into the channel, from wherever you are. No routing, no formatting, no
decision about which project it belongs to. If it takes more than a few seconds,
the pattern has already failed.

### 2. Prepare (automated, deterministic only)
If you already run a scheduled local job (cron, launchd, a file watcher) for
indexing or syncing, add one step to it. That step:

- pulls unfiled items from the capture channel into the indexed corpus, so by the
  time you sit down they are already searchable alongside everything else
- writes a small state file: item count, age of the oldest item, which items are
  past the bankruptcy horizon, and **`last_success` timestamp**

Nothing here exercises judgment, and nothing here writes to a project repo. If
this step dies, triage gets slower, never wrong.

**Carry `last_success` and surface it.** A fetcher that silently stops looks
exactly like an empty inbox. Any consumer of the state file must report staleness
("inbox state is 9 days old") rather than assume freshness. Silent staleness is
the same class of bug as a search tool that returns weak matches without saying
they are weak.

### 3. Check at session start (non-blocking)
Reference this loop from the repo's agent instructions file so it runs when a
session opens. The check reads the local state file (fast, offline-tolerant) and:

- reports the total: "inbox has 7 items, 2 belong to this repo"
- offers to file the items belonging to **this** repo
- leaves everything else visible and untouched

**It must not block.** Forcing a full triage before the task the human actually
opened the terminal for is how this instruction gets deleted. Surface the backlog,
never enforce it.

### 4. File (the actual triage)
For each item, in a session:

- append a dated entry to the right repo's `log/YYYY-MM.md`
- rewrite the affected `STATUS.md` (rewrite, not append)
- mark the item handled in the channel

One writer. Automated steps prepare and notify; only a session with a human in it
writes to repos. This keeps a failed automation from ever producing a wrong commit.

### 5. Declare bankruptcy on a schedule
Items older than a fixed horizon (six weeks is a reasonable default) are archived
unprocessed. Not migrated, not deferred — archived.

This step is not a concession, it is what keeps the loop alive. An item you
captured and then ignored for six weeks was noise. Without an expiry, backlog
becomes debt and debt becomes guilt, and people abandon systems that make them
feel guilty far faster than systems that lose a little information. Losing that
information is the cheaper error.

---

## The Backstop

A local scheduled job only runs when that machine is awake. If it sleeps for two
weeks, nothing notices the inbox filling.

So pair it with a check that runs somewhere you do not operate — a hosted
scheduled task, a CI cron, anything that survives your laptop being shut. Its job
is deliberately narrow: **notice and nudge, never file.** Filing needs the repos,
and the repos need your machine. Posting the nudge back into the same capture
channel works well, since that is somewhere you already look.

The two are complementary, not redundant: the local job makes triage fast when you
are there, the hosted one makes sure you come back when you are not.

---

## Failure Modes

| Symptom | Cause | Fix |
|---|---|---|
| Channel full, repos stale | Triage blocks the real task, so it gets skipped | Make step 3 non-blocking; only auto-handle current-repo items |
| Inbox looks empty, isn't | Prep step died silently | Surface `last_success` age at session start |
| Backlog feels like debt | No expiry horizon | Enforce step 5 on schedule |
| STATUS.md contradicts the log | State was appended to instead of rewritten | Rewrite state; the log is the only append-only surface |
| Automation filed something wrong | More than one writer | Only sessions write to repos |

---

## When Not To Use This

If the work already happens in the repo, skip all of it. This loop exists to cover
the distance between where thoughts occur and where work is stored. If there is no
distance, adding a channel and a queue just gives you one more thing to maintain.
