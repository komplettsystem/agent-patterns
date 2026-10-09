#!/usr/bin/env python3
"""token-ledger.py

Sums the token usage Claude Code records in its session transcripts
(~/.claude/projects/**/*.jsonl, subagent transcripts included) per session, model
and agent kind (main loop or subagent), and keeps the totals in a ledger file that
outlives the transcripts (they are deleted after about 30 days).

Each run rescans every transcript still on disk, replaces those sessions' rows with
fresh totals (a session can grow between runs), and keeps every other row as it is.
An assistant message is split across several transcript lines, one per content
block, and the usage on those lines grows as the message streams (output 8, 8, 213);
each message counts once, with the largest value seen for each usage field.

This is the token half of "cost per finished task". The other half, whether the
task succeeded, is not in the transcripts. --outcomes reads the "Handed for review"
table of a judgment file (Date | Project | Deliverable | Outcome | Session) and joins
each row to the ledger. With a Session cell (a prefix of $CLAUDE_CODE_SESSION_ID),
the join is exact: all tokens of that session, shared by the deliverables handed from
it. Without one it falls back to date and project: the tokens that project's sessions
used that day (a session counts on the day it started), which misses work done from
another project's folder.

Usage:
  token-ledger.py [--root DIR] [--ledger PATH] [--since YYYY-MM-DD | --days N]
                  [--outcomes JUDGMENT.md]

Prints totals per project and model for the window (default: last 7 days).
"""

import argparse
import csv
import glob
import json
import os
import re
from collections import defaultdict
from datetime import date, timedelta

FIELDS = ["date", "project", "session", "model", "agent", "calls", "input_tokens",
          "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"]
COUNTS = FIELDS[5:]
USAGE_KEYS = FIELDS[6:]


def scan(root):
    """Return {(session, model, agent): row} for every transcript under root."""
    messages = {}  # (path, message id) -> (meta, {usage field: max seen})
    for path in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
        agent = "subagent" if os.sep + "subagents" + os.sep in path else "main"
        try:
            lines = open(path, encoding="utf-8", errors="replace").readlines()
        except OSError:
            continue
        for line in lines:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("type") != "assistant":
                continue
            msg = rec.get("message") or {}
            usage, model = msg.get("usage"), msg.get("model")
            if not usage or not model or model.startswith("<"):
                continue
            msg_key = (path, msg.get("id") or rec.get("uuid"))
            if msg_key not in messages:
                messages[msg_key] = ({
                    "date": (rec.get("timestamp") or "")[:10],
                    "project": os.path.basename(rec.get("cwd") or "") or "unknown",
                    "session": rec.get("sessionId") or "unknown",
                    "model": model, "agent": agent}, {k: 0 for k in USAGE_KEYS})
            peak = messages[msg_key][1]
            for k in USAGE_KEYS:
                peak[k] = max(peak[k], int(usage.get(k) or 0))

    rows = {}
    for meta, peak in messages.values():
        key = (meta["session"], meta["model"], meta["agent"])
        row = rows.get(key)
        if row is None:
            row = rows[key] = {**meta, **{k: 0 for k in COUNTS}}
        row["date"] = min(row["date"], meta["date"])
        row["calls"] += 1
        for k in USAGE_KEYS:
            row[k] += peak[k]
    return rows


def load(ledger):
    if not os.path.exists(ledger):
        return {}
    with open(ledger, newline="") as f:
        return {(r["session"], r["model"], r["agent"]): r
                for r in csv.DictReader(f, delimiter="\t")}


def save(ledger, rows):
    os.makedirs(os.path.dirname(os.path.abspath(ledger)), exist_ok=True)
    tmp = ledger + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t")
        w.writeheader()
        for key in sorted(rows, key=lambda k: (rows[k]["date"], k)):
            w.writerow(rows[key])
    os.replace(tmp, ledger)


def handed(path):
    """Rows of the "Handed for review" table: [(date, project, kind, session prefix)]."""
    rows, inside = [], False
    for line in open(path, encoding="utf-8"):
        if line.startswith("## "):
            inside = line.strip() == "## Handed for review"
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if inside and len(cells) in (4, 5) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]):
            outcome = cells[3].lower()
            kind = next((k for k in ("accepted", "corrected") if outcome.startswith(k)), "open")
            session = cells[4] if len(cells) == 5 else ""
            rows.append((cells[0], cells[1], kind, session))
    return rows


def print_outcomes(rows, path, since):
    def tokens(match):
        out = inp = 0
        for r in rows.values():
            if match(r):
                out += int(r["output_tokens"])
                inp += sum(int(r[k]) for k in USAGE_KEYS if k != "output_tokens")
        return out, inp

    groups = defaultdict(lambda: defaultdict(int))
    for day, project, kind, session in handed(path):
        if day < since:
            continue
        key = ("session", session) if session else ("day", day, project)
        groups[key]["handed"] += 1
        groups[key][kind] += 1
    print(f"\nTokens per handed deliverable since {since}")
    print(f"{'joined on':<36} {'handed':>6} {'acc':>4} {'corr':>4} {'open':>4} "
          f"{'output':>10} {'all input':>13} {'out/handed':>10}")
    for key, d in sorted(groups.items()):
        if key[0] == "session":
            label = f"session {key[1]}"
            out, inp = tokens(lambda r: r["session"].startswith(key[1]))
        else:
            label = f"{key[1]} {key[2]}"
            out, inp = tokens(lambda r: (r["date"], r["project"]) == key[1:])
        print(f"{label:<36} {d['handed']:>6} {d['accepted']:>4} {d['corrected']:>4} "
              f"{d['open']:>4} {out:>10} {inp:>13} {out // d['handed']:>10}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--ledger",
                    default=os.path.expanduser("~/.cache/agent-patterns/token-ledger.tsv"))
    ap.add_argument("--since")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--outcomes", help="judgment file with a 'Handed for review' table")
    args = ap.parse_args()

    rows = load(args.ledger)
    fresh = scan(args.root)
    rescanned = {k[0] for k in fresh}
    rows = {k: v for k, v in rows.items() if k[0] not in rescanned}
    rows.update(fresh)
    save(args.ledger, rows)

    since = args.since or (date.today() - timedelta(days=args.days)).isoformat()
    totals = defaultdict(lambda: defaultdict(int))
    sessions = defaultdict(set)
    for r in rows.values():
        if r["date"] < since:
            continue
        key = (r["project"], r["model"])
        sessions[key].add(r["session"])
        for k in COUNTS:
            totals[key][k] += int(r[k])
    print(f"Token totals since {since} ({len(rows)} ledger rows, {args.ledger})")
    print(f"{'project':<24} {'model':<28} {'sessions':>8} {'calls':>7} "
          f"{'output':>11} {'cache read':>13} {'uncached in':>12}")
    for (project, model), t in sorted(totals.items(), key=lambda x: -x[1]["output_tokens"]):
        print(f"{project:<24} {model:<28} {len(sessions[(project, model)]):>8} "
              f"{t['calls']:>7} {t['output_tokens']:>11,} {t['cache_read_input_tokens']:>13,} "
              f"{t['input_tokens'] + t['cache_creation_input_tokens']:>12,}")

    if args.outcomes:
        print_outcomes(rows, args.outcomes, since)


if __name__ == "__main__":
    main()
