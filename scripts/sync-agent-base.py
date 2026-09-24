#!/usr/bin/env python3
"""Sync AGENT-BASE.md into the base section of every repo's AGENTS.md.

check-agent-setup.sh only creates a missing AGENTS.md; it never updates one, so copies drift
as AGENT-BASE.md changes. This script updates them. The base section is everything before
the "---" line that opens "## Project-Specific Guidelines"; the project section is never
touched.

A repo whose base section has lines the new base doesn't contain (local edits, as in
AI-first-PM-workflow) is skipped and those lines are printed: syncing would delete them.
Dry run by default; --apply writes. Never commits.

Usage:  python3 scripts/sync-agent-base.py [--apply] [--root DIR] [--base FILE]
        --root defaults to the parent of this repo (the Projects folder).
"""
import argparse
import difflib
import os
import sys

MARKER = "\n---\n\n## Project-Specific"
HERE = os.path.dirname(os.path.abspath(__file__))
STANDARDS_DIR = os.path.dirname(HERE)


def find_agents_files(root):
    """AGENTS.md in each direct subfolder of root, once per real path (some folders are symlinks)."""
    seen = set()
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name, "AGENTS.md")
        if not os.path.isfile(path):
            continue
        real = os.path.realpath(path)
        if real in seen:
            continue
        seen.add(real)
        yield name, path


def plan(text, base):
    """Return (status, new_text, added, removed) for one AGENTS.md."""
    i = text.find(MARKER)
    if i < 0:
        return "no-marker", text, [], []
    old_lines = text[:i].rstrip("\n").split("\n")
    new_lines = base.rstrip("\n").split("\n")
    if old_lines == new_lines:
        return "current", text, [], []
    diff = [d for d in difflib.ndiff(old_lines, new_lines) if d[:2] in ("+ ", "- ")]
    added = [d[2:] for d in diff if d.startswith("+ ")]
    removed = [d[2:] for d in diff if d.startswith("- ")]
    if removed:
        return "local-edits", text, added, removed
    return "update", base.rstrip("\n") + "\n" + text[i:], added, removed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    parser.add_argument("--root", default=os.path.dirname(STANDARDS_DIR))
    parser.add_argument("--base", default=os.path.join(STANDARDS_DIR, "AGENT-BASE.md"))
    args = parser.parse_args()

    with open(args.base) as f:
        base = f.read()

    changed = []
    for name, path in find_agents_files(args.root):
        with open(path) as f:
            text = f.read()
        status, new_text, added, removed = plan(text, base)
        if status == "current":
            print(f"{name}: up to date")
        elif status == "no-marker":
            print(f"{name}: skipped, no Project-Specific section")
        elif status == "local-edits":
            print(f"{name}: skipped, local edits would be lost ({len(removed)} lines):")
            for line in removed:
                print(f"    - {line}")
        else:
            if args.apply:
                with open(path, "w") as f:
                    f.write(new_text)
                changed.append(name)
                print(f"{name}: updated (+{len(added)} lines)")
            else:
                print(f"{name}: would update (+{len(added)} lines)")

    if changed:
        print("\nChanged, not committed: " + ", ".join(changed))
    elif not args.apply:
        print("\nDry run. Re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
