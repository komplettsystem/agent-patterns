"""Tests for check-judgment-drift.py on a temporary judgment file and memory root."""
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check-judgment-drift.py")


def judgment(review_line, memory_line, rows):
    table = "\n".join(f"| {d} | p | x | y | z | {kind} |" for d, kind in rows)
    return (
        "# How Karsten judges\n\n"
        f"{review_line}\n\n{memory_line}\n\n"
        "## Corrections log\n\n"
        "| Date | Project | Deliverable | Correction | Entry | New / repeat |\n"
        "|---|---|---|---|---|---|\n"
        f"{table}\n"
    )


NO_REVIEW = "**Last drift review:** none yet (file created 2026-10-07)."
NO_MEMCHECK = "**Last memory consistency check:** none yet."


class CheckJudgmentDrift(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.jfile = os.path.join(self.root, "JUDGMENT.md")
        self.mem = os.path.join(self.root, "projects")
        os.makedirs(self.mem)

    def tearDown(self):
        self.tmp.cleanup()

    def write_judgment(self, text):
        with open(self.jfile, "w") as f:
            f.write(text)

    def memory(self, project, name, body, mtime=None):
        d = os.path.join(self.mem, project, "memory")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, name)
        with open(path, "w") as f:
            f.write(f"---\nname: {name}\nmetadata:\n  modified: 2026-10-01\n---\n\n{body}\n")
        if mtime:
            os.utime(path, (mtime, mtime))
        return path

    def run_script(self, today):
        return subprocess.run(
            [sys.executable, SCRIPT, "--judgment", self.jfile, "--memory-root", self.mem, "--today", today],
            capture_output=True, text=True)

    def test_not_due_when_recent_and_few_new_corrections(self):
        self.write_judgment(judgment(NO_REVIEW, NO_MEMCHECK, [("2026-10-07", "new"), ("2026-10-07", "repeat")]))
        out = self.run_script("2026-10-08").stdout
        self.assertIn("[judgment] Drift review not due", out)
        self.assertIn("1 day", out)
        self.assertIn("1 new correction", out)

    def test_due_after_30_days(self):
        self.write_judgment(judgment(NO_REVIEW, NO_MEMCHECK, []))
        out = self.run_script("2026-11-06").stdout
        self.assertIn("[judgment] Drift review due", out)

    def test_due_after_five_new_corrections_since_last_review(self):
        rows = [("2026-10-10", "new")] * 5 + [("2026-10-01", "new")]
        self.write_judgment(judgment("**Last drift review:** 2026-10-05.", NO_MEMCHECK, rows))
        out = self.run_script("2026-10-12").stdout
        self.assertIn("[judgment] Drift review due", out)
        self.assertIn("5 new corrections", out)

    def test_repeats_do_not_count_toward_due(self):
        rows = [("2026-10-10", "repeat (said 09-24)")] * 6
        self.write_judgment(judgment("**Last drift review:** 2026-10-05.", NO_MEMCHECK, rows))
        out = self.run_script("2026-10-12").stdout
        self.assertIn("not due", out)

    def test_missing_judgment_file_is_reported_not_silent(self):
        out = self.run_script("2026-10-08").stdout
        self.assertIn("[judgment] Could not read", out)

    def test_same_memory_name_with_different_content_is_flagged(self):
        self.write_judgment(judgment(NO_REVIEW, "**Last memory consistency check:** 2026-10-07.", []))
        old = 1759000000  # 2025-09-27, before the check date
        self.memory("proj-a", "be-critical.md", "Challenge him.", mtime=old)
        self.memory("proj-b", "be-critical.md", "Challenge him, once.", mtime=old)
        self.memory("proj-c", "same.md", "Identical.", mtime=old)
        self.memory("proj-d", "same.md", "Identical.", mtime=old)
        out = self.run_script("2026-10-08").stdout
        self.assertIn("be-critical.md (proj-a, proj-b)", out)
        self.assertNotIn("same.md", out)

    def test_memory_changed_since_last_check_is_counted(self):
        self.write_judgment(judgment(NO_REVIEW, "**Last memory consistency check:** 2026-01-01.", []))
        self.memory("proj-a", "old.md", "Old.", mtime=1759000000)
        self.memory("proj-a", "new.md", "New.")  # mtime now, after the check date
        out = self.run_script("2099-01-01").stdout
        self.assertIn("1 memory file changed since the last consistency check", out)
        self.assertIn("proj-a/new.md", out)

    def test_memory_quiet_when_nothing_changed_and_no_conflicts(self):
        self.write_judgment(judgment(NO_REVIEW, "**Last memory consistency check:** 2026-10-07.", []))
        self.memory("proj-a", "old.md", "Old.", mtime=1759000000)
        out = self.run_script("2026-10-08").stdout
        self.assertNotIn("[memory]", out)


if __name__ == "__main__":
    unittest.main()
