"""Tests for extract-user-messages.py on temporary transcripts."""
import glob
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extract-user-messages.py")


def human(text, ts="2026-10-07T10:00:00Z"):
    return {"type": "user", "timestamp": ts, "sessionId": "s1", "origin": {"kind": "human"},
            "message": {"role": "user", "content": text}}


def injected(text):
    return {"type": "user", "timestamp": "2026-10-07T10:00:00Z", "isMeta": True,
            "origin": {"kind": "peer"}, "message": {"role": "user", "content": text}}


def queued(text):
    return {"type": "attachment", "timestamp": "2026-10-07T10:05:00Z", "sessionId": "s1",
            "attachment": {"type": "queued_command", "prompt": text}}


def reply(text):
    return {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}


class ExtractUserMessages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.projects = os.path.join(self.tmp.name, "projects")
        self.out = os.path.join(self.tmp.name, "out")
        self.dir = os.path.join(self.projects, "-Users-me-Documents-Projects-radar")
        os.makedirs(self.dir)
        self.t = os.path.join(self.dir, "s1.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, entries, mode="w"):
        with open(self.t, mode) as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def run_script(self, *args):
        return subprocess.run([sys.executable, SCRIPT, "--projects-root", self.projects, "--out-dir", self.out, *args],
                              capture_output=True, text=True)

    def records(self):
        recs = []
        for p in sorted(glob.glob(os.path.join(self.out, "*.jsonl"))):
            with open(p) as f:
                recs += [json.loads(l) for l in f if l.strip()]
        return recs

    def test_extracts_typed_and_queued_messages_with_the_reply_they_answer(self):
        self.write([human("first"), reply("Row four is open."), queued("also this"), human("second")])
        self.run_script("--catch-up")
        recs = self.records()
        self.assertEqual([r["text"] for r in recs], ["first", "also this", "second"])
        self.assertEqual(recs[0]["reacting_to"], "")
        self.assertIn("Row four is open.", recs[2]["reacting_to"])
        self.assertEqual(recs[0]["project"], "radar")
        self.assertTrue(os.path.exists(os.path.join(self.out, "2026-10.jsonl")))

    def test_skips_injected_messages(self):
        self.write([human("mine"), injected("Another Claude session sent a message: report")])
        self.run_script("--catch-up")
        self.assertEqual([r["text"] for r in self.records()], ["mine"])

    def test_skips_system_text_marked_as_human(self):
        self.write([human("<task-notification>\n<task-id>x</task-id>"),
                    human("This session is being continued from a previous conversation that ran out of context."),
                    queued("<task-notification>\n<task-id>y</task-id>"),
                    human("real")])
        self.run_script("--catch-up")
        self.assertEqual([r["text"] for r in self.records()], ["real"])

    def test_is_incremental_and_never_duplicates(self):
        self.write([human("one"), reply("answer")])
        self.run_script("--catch-up")
        self.write([human("two")], mode="a")
        self.run_script("--catch-up")
        self.run_script("--transcript", self.t)
        self.assertEqual([r["text"] for r in self.records()], ["one", "two"])
        self.assertIn("answer", self.records()[1]["reacting_to"])

    def test_ignores_a_half_written_last_line(self):
        self.write([human("done")])
        with open(self.t, "a") as f:
            f.write('{"type": "user", "origin": {"kind": "hu')
        self.run_script("--catch-up")
        self.assertEqual([r["text"] for r in self.records()], ["done"])

    def test_skips_subagent_transcripts(self):
        sub = os.path.join(self.dir, "s1", "subagents")
        os.makedirs(sub)
        with open(os.path.join(sub, "a.jsonl"), "w") as f:
            f.write(json.dumps(human("from a subagent prompt")) + "\n")
        self.run_script("--catch-up")
        self.assertEqual(self.records(), [])


if __name__ == "__main__":
    unittest.main()
