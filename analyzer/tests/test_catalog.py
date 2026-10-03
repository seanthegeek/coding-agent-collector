import os
import subprocess
import unittest
from pathlib import Path

from agent_analyzer import catalog

REPO = Path(__file__).resolve().parents[2]
COLLECTOR = REPO / "collectors" / "collect-agent-artifacts.sh"


class GlobTests(unittest.TestCase):
    def rx(self, pat):
        return catalog.glob_segment_to_regex(pat)

    def test_star_does_not_cross_slash(self):
        self.assertIsNotNone(self.rx("*.jsonl").fullmatch("a.jsonl"))
        self.assertIsNone(self.rx("*").fullmatch("a/b"))

    def test_question_and_class(self):
        self.assertIsNotNone(self.rx("rollout-?.jsonl").fullmatch("rollout-1.jsonl"))
        self.assertIsNotNone(self.rx("[Zz]ed").fullmatch("Zed"))
        self.assertIsNotNone(self.rx("[Zz]ed").fullmatch("zed"))
        self.assertIsNone(self.rx("[Zz]ed").fullmatch("Xed"))
        self.assertIsNotNone(self.rx("[!a]bc").fullmatch("xbc"))
        self.assertIsNone(self.rx("[!a]bc").fullmatch("abc"))

    def test_literal_dots_and_spaces(self):
        self.assertIsNotNone(self.rx("Application Support").fullmatch("Application Support"))
        self.assertIsNone(self.rx(".claude.json*").fullmatch("xclaudejson"))
        self.assertIsNotNone(self.rx(".claude.json*").fullmatch(".claude.json.backup"))


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.cat = catalog.load()

    def test_sections_parsed(self):
        self.assertGreater(len(self.cat.entries), 100)
        self.assertGreater(len(self.cat.project_entries), 30)
        self.assertGreater(len(self.cat.excludes), 50)
        self.assertGreater(len(self.cat.secrets), 50)
        self.assertIn("claude-code", self.cat.agents)
        self.assertIn("codex-cli", self.cat.agents)
        self.assertTrue(all(e.agent == "project" for e in self.cat.project_entries))

    def test_every_entry_has_agent_and_glob(self):
        for e in self.cat.entries:
            self.assertTrue(e.agent and e.glob and e.segments, e)

    @unittest.skipUnless(COLLECTOR.exists(), "collector script not present")
    def test_bundled_copy_matches_collector_list(self):
        out = subprocess.run(["sh", str(COLLECTOR), "--list"], capture_output=True, text=True, check=True).stdout
        self.assertEqual(out, self.cat.text,
                         "catalog.txt drifted; run: collectors/collect-agent-artifacts.sh --list > analyzer/agent_analyzer/catalog.txt")


if __name__ == "__main__":
    unittest.main()
