"""Tests for sync-agent-base.py on a temporary projects root."""
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync-agent-base.py")

OLD_BASE = "# Agent Guidelines\n\n## 1. Rule one\n\nText one.\n"
NEW_BASE = "# Agent Guidelines\n\n## 1. Rule one\n\nText one.\n\nA new paragraph.\n"
PROJECT = "\n---\n\n## Project-Specific Guidelines\n\nProject rules stay.\n"


class SyncAgentBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.base = os.path.join(self.root, "AGENT-BASE.md")
        with open(self.base, "w") as f:
            f.write(NEW_BASE)

    def tearDown(self):
        self.tmp.cleanup()

    def repo(self, name, agents_md):
        path = os.path.join(self.root, name)
        os.makedirs(path)
        if agents_md is not None:
            with open(os.path.join(path, "AGENTS.md"), "w") as f:
                f.write(agents_md)
        return os.path.join(path, "AGENTS.md")

    def run_script(self, *args):
        return subprocess.run([sys.executable, SCRIPT, "--root", self.root, "--base", self.base, *args],
                              capture_output=True, text=True)

    def read(self, path):
        with open(path) as f:
            return f.read()

    def test_up_to_date_is_left_alone(self):
        path = self.repo("fresh", NEW_BASE + PROJECT)
        out = self.run_script("--apply")
        self.assertIn("fresh: up to date", out.stdout)
        self.assertEqual(self.read(path), NEW_BASE + PROJECT)

    def test_dry_run_reports_but_does_not_write(self):
        path = self.repo("stale", OLD_BASE + PROJECT)
        out = self.run_script()
        self.assertIn("stale: would update (+2 lines)", out.stdout)
        self.assertEqual(self.read(path), OLD_BASE + PROJECT)

    def test_apply_replaces_base_and_keeps_project_section(self):
        path = self.repo("stale", OLD_BASE + PROJECT)
        out = self.run_script("--apply")
        self.assertIn("stale: updated (+2 lines)", out.stdout)
        self.assertEqual(self.read(path), NEW_BASE.rstrip("\n") + "\n" + PROJECT)

    def test_local_edits_are_never_overwritten(self):
        local = OLD_BASE + "\nA local note only this repo has.\n"
        path = self.repo("custom", local + PROJECT)
        out = self.run_script("--apply")
        self.assertIn("custom: skipped, local edits would be lost", out.stdout)
        self.assertIn("A local note only this repo has.", out.stdout)
        self.assertEqual(self.read(path), local + PROJECT)

    def test_missing_project_section_is_skipped(self):
        path = self.repo("odd", "# Just a file\n")
        out = self.run_script("--apply")
        self.assertIn("odd: skipped, no Project-Specific section", out.stdout)
        self.assertEqual(self.read(path), "# Just a file\n")

    def test_dirs_without_agents_md_are_ignored(self):
        self.repo("notarepo", None)
        out = self.run_script()
        self.assertNotIn("notarepo", out.stdout)


if __name__ == "__main__":
    unittest.main()
