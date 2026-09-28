"""Tests for audit-rule-compliance.py's --summary mode, on a small synthetic transcript."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit-rule-compliance.py")
TODAY = date.today().isoformat()


def user(uid, parent, t, text):
    return {"type": "user", "uuid": uid, "parentUuid": parent, "timestamp": f"{TODAY}T10:00:{t:02d}Z",
            "message": {"role": "user", "content": text}}


def tool(uid, parent, t, tid, name, inp):
    return {"type": "assistant", "uuid": uid, "parentUuid": parent, "timestamp": f"{TODAY}T10:00:{t:02d}Z",
            "message": {"content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}]}}


SESSION = [
    user("u1", None, 1, "look at the notes"),
    tool("a1", "u1", 2, "t1", "Bash", {"command": "git commit -m 'unasked'"}),
    tool("a2", "a1", 3, "t2", "mcp__plugin_operations_slack__slack_send_message", {"channel_id": "C1", "message": "hi"}),
    user("u2", "a2", 4, "please commit this"),
    tool("a3", "u2", 5, "t3", "Bash",
         {"command": "git commit -m \"asked\n\nCo-Authored-By: Claude Opus <noreply@anthropic.com>\""}),
]


def run(root, *args, env=None):
    return subprocess.run([sys.executable, SCRIPT, "--root", root, *args], capture_output=True, text=True, env=env)


def tool_at(uid, parent, iso_ts, tid, name, inp, cwd=None):
    e = {"type": "assistant", "uuid": uid, "parentUuid": parent, "timestamp": iso_ts,
         "message": {"content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}]}}
    if cwd:
        e["cwd"] = cwd
    return e


def user_at(uid, parent, iso_ts, text):
    return {"type": "user", "uuid": uid, "parentUuid": parent, "timestamp": iso_ts,
            "message": {"role": "user", "content": text}}


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def make_repo(root, agents_md_text):
    """A git repo whose AGENTS.md carries AGENT-BASE rule 13's signature text."""
    repo = os.path.join(root, "repo")
    os.makedirs(repo)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@t.com")
    git(repo, "config", "user.name", "t")
    with open(os.path.join(repo, "AGENTS.md"), "w") as f:
        f.write(agents_md_text)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "add rule 13")
    return repo


def make_fake_gh(dir_, visibility):
    path = os.path.join(dir_, "gh")
    with open(path, "w") as f:
        f.write(f"#!/bin/sh\necho {visibility}\n")
    os.chmod(path, 0o755)


class Summary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.tmp.name, "-proj"))
        with open(os.path.join(self.tmp.name, "-proj", "s1.jsonl"), "w") as f:
            f.write("\n".join(json.dumps(e) for e in SESSION))

    def tearDown(self):
        self.tmp.cleanup()

    def test_one_line_counts_only_unrequested_events(self):
        r = run(self.tmp.name, "--days", "7", "--summary")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1, r.stdout)
        line = lines[0]
        self.assertTrue(line.startswith("[audit] last 7 days"), line)
        self.assertIn("1 send", line)
        self.assertIn("0 destructive", line)
        self.assertIn("1 commit", line)
        self.assertIn("1 without attribution", line)

    def test_days_window_excludes_older_sessions(self):
        old = (date.today() - timedelta(days=30)).isoformat()
        path = os.path.join(self.tmp.name, "-proj", "s1.jsonl")
        with open(path, "w") as f:
            f.write("\n".join(json.dumps(e).replace(TODAY, old) for e in SESSION))
        r = run(self.tmp.name, "--days", "7", "--summary")
        self.assertIn("0 send", r.stdout)
        self.assertIn("0 commit", r.stdout)

    def test_summary_writes_no_event_file(self):
        out = os.path.join(self.tmp.name, "events.jsonl")
        run(self.tmp.name, "--days", "7", "--summary", "--out", out)
        self.assertFalse(os.path.exists(out))

    def test_ack_suppresses_flagged_events_from_later_runs(self):
        ack_file = os.path.join(self.tmp.name, "ack.json")
        r = run(self.tmp.name, "--days", "7", "--ack", "--ack-file", ack_file)
        self.assertEqual(r.returncode, 0, r.stderr)
        # unasked send (R1) + unasked commit (R2) + its missing-attribution (R5)
        self.assertIn("Acknowledged 3 new event", r.stdout)
        self.assertTrue(os.path.exists(ack_file))

        r2 = run(self.tmp.name, "--days", "7", "--summary", "--ack-file", ack_file)
        line = r2.stdout.strip().splitlines()[0]
        self.assertIn("0 sends", line)
        self.assertIn("0 commits (0 without attribution)", line)

    def test_ack_is_idempotent(self):
        ack_file = os.path.join(self.tmp.name, "ack.json")
        run(self.tmp.name, "--days", "7", "--ack", "--ack-file", ack_file)
        r = run(self.tmp.name, "--days", "7", "--ack", "--ack-file", ack_file)
        self.assertIn("Acknowledged 0 new event(s) as reviewed (3 were already acked)", r.stdout)

    def test_ack_key_is_stable_across_window_size(self):
        # An event acked under --days 7 must still be suppressed under a wider window,
        # since the whole point is to survive the window rolling forward.
        ack_file = os.path.join(self.tmp.name, "ack.json")
        run(self.tmp.name, "--days", "7", "--ack", "--ack-file", ack_file)
        r = run(self.tmp.name, "--days", "365", "--summary", "--ack-file", ack_file)
        line = r.stdout.strip().splitlines()[0]
        self.assertIn("0 commit", line)


RULE13_TEXT = (
    "## 13. For git and outward messages, the risk boundary is visibility, not the action\n\n"
    "A commit is never gated on being asked... A push follows the repo it lands in..."
)
BEFORE_CUTOFF = f"{TODAY}T00:00:01Z"   # same day as RULE13_CUTOFF, but before its time-of-day
AFTER_CUTOFF = f"{TODAY}T23:59:59Z"    # same day, after its time-of-day


class Rule13(unittest.TestCase):
    """AGENT-BASE rule 13 authorizes a commit outright, and a push to a private repo,
    once the repo's own AGENTS.md/CLAUDE.md carries it — folded into the classifier
    at commit d3ced56 (2026-09-28)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = make_repo(self.tmp.name, RULE13_TEXT)
        self.transcripts = os.path.join(self.tmp.name, "transcripts")
        os.makedirs(os.path.join(self.transcripts, "-proj"))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, session):
        with open(os.path.join(self.transcripts, "-proj", "s1.jsonl"), "w") as f:
            f.write("\n".join(json.dumps(e) for e in session))

    def test_unasked_commit_authorized_when_repo_carries_rule13(self):
        # R5 attribution is a separate check rule 13 doesn't touch — keep the message
        # compliant so this test isolates R2's not-requested/standing-instruction call.
        cmd = "git commit -m \"unasked\n\nCo-Authored-By: Claude Opus <noreply@anthropic.com>\""
        self.write([
            user_at("u1", None, BEFORE_CUTOFF, "look at the notes"),
            tool_at("a1", "u1", AFTER_CUTOFF, "t1", "Bash", {"command": cmd}, cwd=self.repo),
        ])
        r = run(self.transcripts, "--days", "7", "--summary")
        self.assertIn("0 commits (0 without attribution)", r.stdout, r.stdout)

    def test_unasked_commit_before_cutoff_still_flagged(self):
        self.write([
            user_at("u1", None, BEFORE_CUTOFF, "look at the notes"),
            tool_at("a1", "u1", BEFORE_CUTOFF, "t1", "Bash", {"command": "git commit -m 'unasked'"}, cwd=self.repo),
        ])
        r = run(self.transcripts, "--days", "7", "--summary")
        self.assertIn("1 commit", r.stdout, r.stdout)

    def test_unasked_push_authorized_when_repo_is_private(self):
        fake_bin = os.path.join(self.tmp.name, "bin")
        os.makedirs(fake_bin)
        make_fake_gh(fake_bin, "PRIVATE")
        env = {**os.environ, "PATH": fake_bin + os.pathsep + os.environ["PATH"]}
        self.write([
            user_at("u1", None, BEFORE_CUTOFF, "look at the notes"),
            tool_at("a1", "u1", AFTER_CUTOFF, "t1", "Bash", {"command": "git push -q"}, cwd=self.repo),
        ])
        r = run(self.transcripts, "--days", "7", "--summary", env=env)
        self.assertIn("0 sends", r.stdout, r.stdout)

    def test_unasked_push_still_flagged_when_repo_is_public(self):
        fake_bin = os.path.join(self.tmp.name, "bin")
        os.makedirs(fake_bin)
        make_fake_gh(fake_bin, "PUBLIC")
        env = {**os.environ, "PATH": fake_bin + os.pathsep + os.environ["PATH"]}
        self.write([
            user_at("u1", None, BEFORE_CUTOFF, "look at the notes"),
            tool_at("a1", "u1", AFTER_CUTOFF, "t1", "Bash", {"command": "git push -q"}, cwd=self.repo),
        ])
        r = run(self.transcripts, "--days", "7", "--summary", env=env)
        self.assertIn("1 send", r.stdout, r.stdout)


if __name__ == "__main__":
    unittest.main()
