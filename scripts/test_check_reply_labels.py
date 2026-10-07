"""Tests for check-reply-labels.py (Stop hook) on temporary transcripts."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check-reply-labels.py")


def user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def tool_result():
    return {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}}


def assistant(text):
    return {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}


class CheckReplyLabels(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.transcript = os.path.join(self.tmp.name, "t.jsonl")
        self.log = os.path.join(self.tmp.name, "log.tsv")

    def tearDown(self):
        self.tmp.cleanup()

    def run_hook(self, entries, active=False):
        with open(self.transcript, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        payload = json.dumps({"transcript_path": self.transcript, "stop_hook_active": active, "session_id": "s1"})
        r = subprocess.run([sys.executable, SCRIPT, "--log", self.log], input=payload, capture_output=True, text=True)
        return json.loads(r.stdout) if r.stdout.strip() else None

    def test_blocks_reply_with_internal_labels(self):
        out = self.run_hook([user("hi"), assistant("Row 4 is open and see thesis 6 and C10.")])
        self.assertEqual(out["decision"], "block")
        for label in ("Row 4", "thesis 6", "C10"):
            self.assertIn(label, out["reason"])

    def test_allows_label_in_brackets_after_plain_words(self):
        out = self.run_hook([user("hi"), assistant("The memory row (row 4) and the verification layer (Layer 5).")])
        self.assertIsNone(out)

    def test_ignores_code_paths_urls_and_quotes(self):
        text = ("Run `check row 4` in scripts/rule-7.py, see https://x.io/C10 and "
                "```\nstep 3\n```\nHe said \"rule 7 again\".")
        self.assertIsNone(self.run_hook([user("hi"), assistant(text)]))

    def test_only_checks_text_after_last_user_message(self):
        out = self.run_hook([user("a"), assistant("old reply about row 4"), user("b"), assistant("A plain reply.")])
        self.assertIsNone(out)

    def test_tool_results_do_not_end_the_reply(self):
        out = self.run_hook([user("a"), assistant("First part, row 4."), tool_result(), assistant("Second part.")])
        self.assertEqual(out["decision"], "block")

    def test_does_not_block_twice(self):
        self.assertIsNone(self.run_hook([user("hi"), assistant("Row 4.")], active=True))

    def test_product_names_are_not_labels(self):
        self.assertIsNone(self.run_hook([user("hi"), assistant("Stored on S3 and run with DeepSeek V4 on an H100.")]))

    def test_logs_every_checked_reply(self):
        self.run_hook([user("hi"), assistant("Row 4.")])
        self.run_hook([user("hi"), assistant("Plain.")])
        with open(self.log) as f:
            lines = f.read().rstrip("\n").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("\t1\t", lines[0])
        self.assertIn("\t0\t", lines[1])


if __name__ == "__main__":
    unittest.main()
