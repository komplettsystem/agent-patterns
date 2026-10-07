#!/usr/bin/env python3
"""Stop hook: send a reply back once if it refers to things by internal label.

A reader can't remember what "row 4", "thesis 6" or "C10" point to. Say what the thing
is; a label may follow in brackets. This hook reads the reply that just finished (all
assistant text since the user's last message), ignores code, paths, URLs, quotes and
anything in brackets, and if labels remain, blocks the stop once with the list so the
reply gets rewritten. It never blocks twice in a row (stop_hook_active).

Every checked reply is logged as a line (date, session, hit count, hits), so the rate
can be compared over time.

Hook setup (~/.claude/settings.json):
  "Stop": [{"hooks": [{"type": "command",
            "command": "python3 /path/to/agent-patterns/scripts/check-reply-labels.py"}]}]
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

# "step", "option", "item" and "round" are left out: they usually point back to a numbered
# list in the same reply, which the reader can see.
WORDS = r"rule|row|thesis|finding|phase|layer|section|question|pattern|entry|gate"
WORD_LABEL = re.compile(r"\b(?:" + WORDS + r")s?\s+\d+[a-z]?\b", re.I)
CODE_LABEL = re.compile(r"\b[A-Z]{1,2}\d{1,3}[a-z]?\b")
NOT_LABELS = {"S3", "V3", "V4", "H100", "A100", "B200", "P50", "P95", "P99", "K8", "BM25", "MP3", "MP4"}


def strip(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)        # code blocks
    text = re.sub(r"`[^`]*`", " ", text)                       # inline code
    text = re.sub(r"https?://\S+", " ", text)                  # URLs
    text = re.sub(r"\S*/\S*", " ", text)                       # paths
    text = re.sub(r"\S+\.(md|py|sh|json|jsonl|txt)\b", " ", text)
    text = re.sub(r'"[^"\n]*"|“[^”\n]*”', " ", text)           # quotes
    text = re.sub(r"^>.*$", " ", text, flags=re.M)             # blockquotes
    prev = None
    while prev != text:                                        # brackets, nested too
        prev = text
        text = re.sub(r"\([^()]*\)|\[[^\[\]]*\]", " ", text)
    return text


def find_labels(text):
    clean = strip(text)
    hits = [m.group(0) for m in WORD_LABEL.finditer(clean)]
    hits += [m.group(0) for m in CODE_LABEL.finditer(clean) if m.group(0) not in NOT_LABELS]
    seen = []
    for h in hits:
        if h not in seen:
            seen.append(h)
    return seen


def is_user_text(entry):
    if entry.get("type") != "user":
        return False
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return True
    return any(isinstance(b, dict) and b.get("type") == "text" for b in content or [])


def last_reply(path):
    entries = []
    with open(path, errors="ignore") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
    start = max((i for i, e in enumerate(entries) if is_user_text(e)), default=-1)
    texts = []
    for e in entries[start + 1:]:
        if e.get("type") != "assistant":
            continue
        for b in e.get("message", {}).get("content") or []:
            if isinstance(b, dict) and b.get("type") == "text":
                texts.append(b.get("text", ""))
    return "\n".join(texts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=os.path.expanduser("~/.cache/agent-patterns/reply-labels.tsv"))
    args = ap.parse_args()
    try:
        payload = json.load(sys.stdin)
        reply = last_reply(payload["transcript_path"])
    except (ValueError, KeyError, OSError):
        return  # never break the session over a check
    if payload.get("stop_hook_active"):
        return
    hits = find_labels(reply)
    try:
        os.makedirs(os.path.dirname(args.log), exist_ok=True)
        with open(args.log, "a") as f:
            f.write(f"{dt.datetime.now().isoformat(timespec='seconds')}\t{payload.get('session_id', '')}\t"
                    f"{len(hits)}\t{', '.join(hits)}\n")
    except OSError:
        pass
    if hits:
        print(json.dumps({
            "decision": "block",
            "reason": ("Your reply refers to things by internal label: " + ", ".join(hits) + ". Karsten has "
                       "asked repeatedly not to do this, because he can't remember what the labels point to. "
                       "Rewrite those sentences to say what each thing is in plain words; a label may follow "
                       "in brackets. If a hit is a product or model name rather than a label, say so in one "
                       "line instead of rewriting."),
        }))


if __name__ == "__main__":
    main()
