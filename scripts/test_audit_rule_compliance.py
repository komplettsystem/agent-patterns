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


def run(root, *args):
    return subprocess.run([sys.executable, SCRIPT, "--root", root, *args], capture_output=True, text=True)


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


if __name__ == "__main__":
    unittest.main()
