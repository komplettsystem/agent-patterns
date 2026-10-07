#!/usr/bin/env python3
"""Copy the user's own messages out of Claude Code transcripts, mechanically.

Corrections can only become durable examples if they are still around when someone
looks for them, and transcripts are deleted after cleanupPeriodDays. This script keeps
every message the user typed (including ones sent mid-turn), with the start and end of
the reply it answered, in monthly JSONL files. It makes no judgment about which messages
are corrections; that is done later, by an agent or the user, from these files.

Output stays local: the messages can contain things the user asked not to share.

Incremental and idempotent: a state file records how far each transcript was read, so
running it at session end (SessionEnd hook, --transcript) and again at session start
(--catch-up, for sessions that ended without the hook) never duplicates a message.
Subagent transcripts are skipped; their "user" turns are prompts written by an agent.

Usage: extract-user-messages.py --out-dir DIR [--projects-root DIR] (--catch-up | --transcript PATH|-)
"""
import argparse
import glob
import json
import os
import re
import sys

STATE = ".state.json"
REPLY_HEAD, REPLY_TAIL = 400, 200


def short(project):
    return re.sub(r"^-Users-[^-]+-(Documents-Projects-|Local-Tools-)?", "", project) or project


def system_text(text):
    """System text that some versions record as if the user typed it."""
    return re.match(r"\s*(<task-notification>|This session is being continued from a previous conversation)",
                    text) is not None


def human_text(entry):
    """The text of a message the user typed, or None."""
    if entry.get("type") == "attachment":
        a = entry.get("attachment") or {}
        if a.get("type") == "queued_command" and isinstance(a.get("prompt"), str):
            kind = (a.get("origin") or {}).get("kind")
            return a["prompt"] if kind in (None, "human") and not system_text(a["prompt"]) else None
        return None
    if entry.get("type") != "user" or entry.get("isMeta"):
        return None
    kind = (entry.get("origin") or {}).get("kind")
    if kind is not None and kind != "human":
        return None
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        text = content
    else:
        parts = [b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text"]
        if not parts:
            return None  # tool results
        text = "\n".join(parts)
    if kind is None and re.match(r"\s*(<|Another Claude session|Base directory for this skill|\[SYSTEM)", text):
        return None  # older transcripts without origin: skip injected text
    return None if system_text(text) else text


def reply_text(entry):
    if entry.get("type") != "assistant":
        return ""
    return "\n".join(b.get("text", "") for b in entry.get("message", {}).get("content") or []
                     if isinstance(b, dict) and b.get("type") == "text")


def excerpt(text):
    text = text.strip()
    if len(text) <= REPLY_HEAD + REPLY_TAIL:
        return text
    return text[:REPLY_HEAD] + " [...] " + text[-REPLY_TAIL:]


def process(path, state, out_dir):
    key = os.path.abspath(path)
    st = state.get(key, {"offset": 0, "reply": "", "new_turn": True})
    try:
        size = os.path.getsize(path)
    except OSError:
        return 0
    if size <= st["offset"]:
        return 0
    project = short(os.path.basename(os.path.dirname(path)))
    session = os.path.splitext(os.path.basename(path))[0]
    written = 0
    with open(path, "rb") as f:
        f.seek(st["offset"])
        data = f.read()
    end = data.rfind(b"\n") + 1  # only complete lines
    reply, new_turn = st["reply"], st.get("new_turn", True)
    for raw in data[:end].splitlines():
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        text = human_text(entry)
        if text is not None:
            ts = entry.get("timestamp") or ""
            month = ts[:7] if re.match(r"\d{4}-\d{2}", ts) else "unknown"
            rec = {"ts": ts, "project": project, "session": session, "text": text, "reacting_to": excerpt(reply)}
            with open(os.path.join(out_dir, f"{month}.jsonl"), "a") as out:
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1
            new_turn = True  # the next reply replaces this one; until then it still stands
        else:
            r = reply_text(entry)
            if r:
                reply = r if new_turn else reply + "\n" + r
                new_turn = False
    state[key] = {"offset": st["offset"] + end, "reply": excerpt(reply), "new_turn": new_turn}
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--projects-root", default=os.path.expanduser("~/.claude/projects"))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--catch-up", action="store_true")
    g.add_argument("--transcript")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    state_path = os.path.join(args.out_dir, STATE)
    try:
        with open(state_path) as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    if args.catch_up:
        paths = sorted(glob.glob(os.path.join(args.projects_root, "*", "*.jsonl")))
    elif args.transcript == "-":  # SessionEnd hook: {"transcript_path": ...} on stdin
        try:
            paths = [json.load(sys.stdin)["transcript_path"]]
        except (ValueError, KeyError):
            print("[extract] No transcript_path on stdin.", file=sys.stderr)
            return
    else:
        paths = [args.transcript]
    total = sum(process(p, state, args.out_dir) for p in paths)
    tmp = state_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, state_path)
    print(f"[extract] {total} new message(s) from {len(paths)} transcript(s).", file=sys.stderr)


if __name__ == "__main__":
    main()
