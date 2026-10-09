"""Tests for token-ledger.py on a temporary transcript root and ledger file."""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token-ledger.py")


def assistant(msg_id, model, out, ts="2026-10-08T10:00:00Z", cwd="/x/Projects/tech-radar",
              session="s1", cache_read=0):
    return {
        "type": "assistant", "sessionId": session, "cwd": cwd, "timestamp": ts,
        "message": {"id": msg_id, "model": model, "usage": {
            "input_tokens": 2, "cache_creation_input_tokens": 10,
            "cache_read_input_tokens": cache_read, "output_tokens": out}},
    }


class TokenLedger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "projects")
        self.ledger = os.path.join(self.tmp.name, "ledger.tsv")
        self.proj = os.path.join(self.root, "-x-Projects-tech-radar")
        os.makedirs(os.path.join(self.proj, "s1", "subagents"))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, records):
        with open(path, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            f.write("not json\n")

    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, SCRIPT, "--root", self.root, "--ledger", self.ledger, *args],
            capture_output=True, text=True, check=True).stdout

    def rows(self):
        with open(self.ledger) as f:
            return list(csv.DictReader(f, delimiter="\t"))

    def test_sums_per_session_model_and_agent_kind_without_double_counting(self):
        main = os.path.join(self.proj, "s1.jsonl")
        # the same message id appears once per content block; count it once
        self.write(main, [assistant("m1", "claude-opus-5-5", 100),
                          assistant("m1", "claude-opus-5-5", 100),
                          assistant("m2", "claude-opus-5-5", 50, cache_read=1000),
                          assistant("m3", "<synthetic>", 0)])
        sub = os.path.join(self.proj, "s1", "subagents", "agent-a1.jsonl")
        self.write(sub, [assistant("m9", "claude-sonnet-5-5", 400)])
        self.run_script()
        got = {(r["session"], r["model"], r["agent"]): r for r in self.rows()}
        self.assertEqual(set(got), {("s1", "claude-opus-5-5", "main"),
                                    ("s1", "claude-sonnet-5-5", "subagent")})
        opus = got[("s1", "claude-opus-5-5", "main")]
        self.assertEqual(opus["output_tokens"], "150")
        self.assertEqual(opus["cache_read_input_tokens"], "1000")
        self.assertEqual(opus["calls"], "2")
        self.assertEqual(opus["project"], "tech-radar")
        self.assertEqual(opus["date"], "2026-10-08")

    def test_streamed_message_counts_its_final_usage(self):
        # usage grows across the lines of one streamed message: 8, 8, 213
        self.write(os.path.join(self.proj, "s1.jsonl"),
                   [assistant("m1", "claude-opus-5-5", 8),
                    assistant("m1", "claude-opus-5-5", 8),
                    assistant("m1", "claude-opus-5-5", 213)])
        self.run_script()
        rows = self.rows()
        self.assertEqual(rows[0]["output_tokens"], "213")
        self.assertEqual(rows[0]["calls"], "1")

    def test_keeps_sessions_whose_transcripts_were_deleted(self):
        main = os.path.join(self.proj, "s1.jsonl")
        self.write(main, [assistant("m1", "claude-opus-5-5", 100)])
        self.run_script()
        os.remove(main)
        self.write(os.path.join(self.proj, "s2.jsonl"),
                   [assistant("m5", "claude-opus-5-5", 7, session="s2")])
        self.run_script()
        self.assertEqual(sorted(r["session"] for r in self.rows()), ["s1", "s2"])

    def test_rerun_updates_a_growing_session_instead_of_adding_rows(self):
        main = os.path.join(self.proj, "s1.jsonl")
        self.write(main, [assistant("m1", "claude-opus-5-5", 100)])
        self.run_script()
        self.write(main, [assistant("m1", "claude-opus-5-5", 100),
                          assistant("m2", "claude-opus-5-5", 20)])
        self.run_script()
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["output_tokens"], "120")

    def test_summary_groups_by_project_and_model(self):
        self.write(os.path.join(self.proj, "s1.jsonl"),
                   [assistant("m1", "claude-opus-5-5", 100)])
        out = self.run_script("--since", "2026-10-01")
        self.assertIn("tech-radar", out)
        self.assertIn("claude-opus-5-5", out)


    def test_outcomes_join_handed_deliverables_on_date_and_project(self):
        self.write(os.path.join(self.proj, "s1.jsonl"),
                   [assistant("m1", "claude-opus-5-5", 300, cache_read=900)])
        self.write(os.path.join(self.proj, "s2.jsonl"),
                   [assistant("m2", "claude-opus-5-5", 100, session="s2",
                              ts="2026-10-09T09:00:00Z")])
        judgment = os.path.join(self.tmp.name, "JUDGMENT.md")
        with open(judgment, "w") as f:
            f.write("# J\n\n## Handed for review\n\ntext\n\n"
                    "| Date | Project | Deliverable | Outcome |\n|---|---|---|---|\n"
                    "| 2026-10-08 | tech-radar | Entry A | accepted |\n"
                    "| 2026-10-08 | tech-radar | Entry B | corrected (1) |\n"
                    "| 2026-10-08 | other | Draft C | open |\n"
                    "\n## Retired\n\n| 2026-10-08 | tech-radar | not a row | accepted |\n")
        out = self.run_script("--since", "2026-10-01", "--outcomes", judgment)
        line = next(l for l in out.splitlines()
                    if l.startswith("2026-10-08") and "tech-radar" in l)
        cols = line.split()
        # date project handed accepted corrected open output all_input out_per_handed
        self.assertEqual(cols[2:6], ["2", "1", "1", "0"])
        self.assertEqual(cols[6], "300")
        self.assertEqual(cols[8], "150")
        other = next(l for l in out.splitlines() if l.startswith("2026-10-08") and "other" in l)
        self.assertEqual(other.split()[6], "0")  # no tokens recorded for that project
        self.assertFalse(any(l.startswith("2026-10-09") for l in out.splitlines()),
                         "days with no handed deliverable are not listed")

    def test_outcomes_join_exactly_on_session_when_given(self):
        # session s2 started in tech-radar, but the deliverable belongs to another project
        self.write(os.path.join(self.proj, "s2.jsonl"),
                   [assistant("m2", "claude-opus-5-5", 100, session="s2-abcdef",
                              ts="2026-10-08T09:00:00Z"),
                    assistant("m3", "claude-opus-5-5", 40, session="s2-abcdef",
                              ts="2026-10-09T09:00:00Z")])
        judgment = os.path.join(self.tmp.name, "JUDGMENT.md")
        with open(judgment, "w") as f:
            f.write("## Handed for review\n\n"
                    "| Date | Project | Deliverable | Outcome | Session |\n|---|---|---|---|---|\n"
                    "| 2026-10-09 | elsewhere | Options | accepted | s2-abc |\n")
        out = self.run_script("--since", "2026-10-01", "--outcomes", judgment)
        cols = next(l for l in out.splitlines() if l.startswith("session s2-abc")).split()
        self.assertEqual(cols[2:6], ["1", "1", "0", "0"])
        self.assertEqual(cols[6], "140")


if __name__ == "__main__":
    unittest.main()
