#!/usr/bin/env python3
"""Session-start check for drift in a judgment file and in Claude Code memories.

Reads a judgment file (corrections kept as durable examples, see AGENT-BASE.md) and the
memory folders under ~/.claude/projects/*/memory, and prints at most two lines for the
SessionStart hook:

- [judgment] whether a drift review is due: 30 days since the last review (or since the
  file was created), or 5 corrections marked "new" in the corrections log since then.
- [memory] memory files changed since the last consistency check, and memory files with
  the same name in several projects whose content differs.

Deterministic and read-only. It finds candidates; deciding whether two memories actually
contradict each other is left to a fresh-context agent and the user.

Usage: check-judgment-drift.py --judgment PATH [--memory-root DIR] [--today YYYY-MM-DD]
"""
import argparse
import datetime as dt
import glob
import os
import re

DUE_DAYS = 30
DUE_NEW = 5
DATE = r"(\d{4}-\d{2}-\d{2})"


def parse_date(s):
    return dt.date.fromisoformat(s)


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def judgment_line(text, today):
    m = re.search(r"\*\*Last drift review:\*\*\s*" + DATE, text)
    if m:
        since, after_since, label = parse_date(m.group(1)), True, "last review"
    else:
        m = re.search(r"\*\*Last drift review:\*\*.*?file created " + DATE, text)
        if not m:
            return "[judgment] Could not find the 'Last drift review' line in the judgment file. Say so in one line."
        since, after_since, label = parse_date(m.group(1)), False, "file created"
    new = 0
    for row in re.finditer(r"^\|\s*" + DATE + r"\s*\|(.*)\|\s*$", text, re.M):
        cells = [c.strip() for c in row.group(2).split("|")]
        if not cells[-1].lower().startswith("new"):
            continue
        d = parse_date(row.group(1))
        if d > since or (d == since and not after_since):
            new += 1
    days = (today - since).days
    state = f"{plural(days, 'day')} since {label}, {plural(new, 'new correction')} logged since"
    if days >= DUE_DAYS or new >= DUE_NEW:
        return (f"[judgment] Drift review due: {state}. Once, early in this session and without blocking "
                "the user's first request, offer to run it: a fresh-context subagent reads the judgment file "
                "and lists entries that contradict each other, entries whose facts changed, and duplicates. "
                "The user decides; then update the 'Last drift review' line.")
    return f"[judgment] Drift review not due: {state} (due at {DUE_DAYS} days or {DUE_NEW} new corrections)."


def short(project):
    """Turn a Claude Code project folder name (-Users-me-Documents-Projects-x) into x."""
    return re.sub(r"^-Users-[^-]+-(Documents-Projects-|Local-Tools-)?", "", project) or project


def body(path):
    with open(path, errors="ignore") as f:
        text = f.read()
    # Ignore bookkeeping lines that differ between copies without changing meaning.
    return "\n".join(l.strip() for l in text.splitlines()
                     if not re.match(r"\s*(modified|originSessionId|node_type):", l)).strip()


def memory_line(text, memory_root):
    m = re.search(r"\*\*Last memory consistency check:\*\*\s*" + DATE, text)
    checked = parse_date(m.group(1)) if m else None
    files = sorted(p for p in glob.glob(os.path.join(memory_root, "*", "memory", "*.md"))
                   if os.path.basename(p) != "MEMORY.md")
    changed = []
    by_name = {}
    for p in files:
        project = short(os.path.basename(os.path.dirname(os.path.dirname(p))))
        name = os.path.basename(p)
        mdate = dt.date.fromtimestamp(os.path.getmtime(p))
        if checked is None or mdate > checked:
            changed.append(f"{project}/{name}")
        by_name.setdefault(name, []).append((project, p))
    conflicts = []
    for name, copies in sorted(by_name.items()):
        if len(copies) > 1 and len({body(p) for _, p in copies}) > 1:
            conflicts.append(f"{name} ({', '.join(proj for proj, _ in copies)})")
    if not changed and not conflicts:
        return None
    parts = []
    if changed:
        shown = ", ".join(changed[:5]) + (", ..." if len(changed) > 5 else "")
        verb = "changed" if checked else "not yet checked"
        parts.append(f"{plural(len(changed), 'memory file')} {verb} since the last consistency check ({shown})")
    if conflicts:
        verb = "exists" if len(conflicts) == 1 else "exist"
        parts.append(f"{plural(len(conflicts), 'memory name')} {verb} in several projects with different content: "
                     + "; ".join(conflicts))
    return ("[memory] " + "; ".join(parts) + ". Once, without blocking the user's first request, offer a "
            "consistency check: a fresh-context subagent compares these memories with the judgment file and "
            "each other and lists contradictions. The user decides which wins; then update the "
            "'Last memory consistency check' line.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judgment", required=True)
    ap.add_argument("--memory-root", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--today", default=None)
    args = ap.parse_args()
    today = parse_date(args.today) if args.today else dt.date.today()
    try:
        with open(args.judgment) as f:
            text = f.read()
    except OSError:
        print(f"[judgment] Could not read the judgment file at {args.judgment}. Say so in one line; "
              "never treat it as empty.")
        return
    print(judgment_line(text, today))
    line = memory_line(text, args.memory_root)
    if line:
        print(line)


if __name__ == "__main__":
    main()
