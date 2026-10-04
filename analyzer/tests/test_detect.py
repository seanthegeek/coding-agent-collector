import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from agent_analyzer import catalog, cli
from agent_analyzer.inputs import open_input

from fixtures import build_home, build_image

REPO = Path(__file__).resolve().parents[2]
COLLECTOR = REPO / "collectors" / "collect-agent-artifacts.sh"


class LooseDetectTests(unittest.TestCase):
    def setUp(self):
        self.cat = catalog.load()
        self.tmp = Path(tempfile.mkdtemp(prefix="cac-analyzer-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def agents_by_user(self, col):
        out = {}
        for a in col.artifacts:
            out.setdefault(a.home.user, set()).add(a.agent)
        return out

    def test_image_layout_finds_every_home(self):
        root = build_image(self.tmp / "image")
        col = open_input(root, self.cat)
        self.assertEqual(col.kind, "loose")
        by_user = self.agents_by_user(col)
        self.assertEqual(set(by_user), {"alice", "bob", "carol"})
        self.assertLessEqual({"claude-code", "codex-cli", "gemini-cli", "antigravity", "vscode", "cline"}, by_user["alice"])
        self.assertEqual(by_user["carol"], {"codex-cli"})
        homes = {h.user: h for h in col.homes}
        self.assertEqual(homes["alice"].original, "/home/alice")
        self.assertEqual(homes["carol"].original, "/Users/carol")
        self.assertTrue(all(h.inferred for h in col.homes))

    def test_nested_entry_wins_over_enclosing_entry(self):
        home = build_home(self.tmp / "home" / "alice")
        for root in (self.tmp / "home", home / ".gemini"):
            col = open_input(root, self.cat)
            by_rel = {a.rel: a.agent for a in col.artifacts}
            self.assertEqual(by_rel[".gemini/antigravity-cli/history.jsonl"], "antigravity", root)
            self.assertEqual(by_rel[".gemini/settings.json"], "gemini-cli", root)
            self.assertEqual(sum(1 for a in col.artifacts if a.rel == ".gemini/antigravity-cli/history.jsonl"), 1)
        col = open_input(self.tmp / "home", self.cat)
        by_rel = {a.rel: a.agent for a in col.artifacts}
        self.assertEqual(by_rel[".config/Code/User/globalStorage/saoudrizwan.claude-dev/state/taskHistory.json"], "cline")
        self.assertEqual(by_rel[".config/Code/User/globalStorage/state.vscdb"], "vscode")

    def test_project_dirs_inside_home_are_not_homes(self):
        root = build_image(self.tmp / "image")
        col = open_input(root, self.cat)
        self.assertFalse(any("dev/proj" in (h.original or "") for h in col.homes))
        # The .claude inside the project belongs to nobody at home level.
        self.assertFalse(any("dev/proj/.claude" in a.original for a in col.artifacts))

    def test_shared_only_directory_is_not_a_home(self):
        d = self.tmp / "repo"
        d.mkdir()
        (d / "AGENTS.md").write_text("x", encoding="utf-8")
        (d / ".env").write_text("A=1", encoding="utf-8")
        col = open_input(d, self.cat)
        self.assertEqual(col.homes, [])
        self.assertEqual(col.artifacts, [])

    def test_bare_home_directory(self):
        home = build_home(self.tmp / "alice")
        col = open_input(home, self.cat)
        self.assertEqual(len(col.homes), 1)
        # The root itself gives no clue who owns it; --user fills this in.
        self.assertEqual(col.homes[0].user, "")
        self.assertEqual(col.homes[0].original, "")
        rels = {a.rel for a in col.artifacts if a.agent == "claude-code"}
        self.assertIn(".claude/history.jsonl", rels)
        self.assertIn(".claude/settings.json", rels)

    def test_agent_directory_as_root(self):
        home = build_home(self.tmp / "home" / "alice")
        col = open_input(home / ".claude", self.cat)
        self.assertEqual(len(col.homes), 1)
        self.assertEqual(col.homes[0].user, "alice")
        self.assertEqual({a.agent for a in col.artifacts}, {"claude-code"})
        self.assertTrue(any("claude-code directory" in n for n in col.notes))
        # .claude/backups-style nested matches must not create extra homes
        self.assertTrue(all(a.rel.startswith(".claude/") for a in col.artifacts))

    def test_symlinked_directories_are_not_followed(self):
        home = build_home(self.tmp / "home" / "alice")
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "secret.jsonl").write_text("{}", encoding="utf-8")
        try:
            os.symlink(outside, home / ".claude" / "linked")
        except OSError:
            self.skipTest("symlinks not permitted")
        col = open_input(self.tmp / "home", self.cat)
        self.assertFalse(any("linked" in a.rel for a in col.artifacts))

    def test_fs_without_manifest(self):
        root = self.tmp / "extracted"
        build_image(root / "fs")
        col = open_input(root, self.cat)
        self.assertTrue(any("fs/ found without manifest" in n for n in col.notes))
        self.assertEqual({h.user for h in col.homes}, {"alice", "bob", "carol"})

    def test_cli_detect_json_and_user_override(self):
        home = build_home(self.tmp / "x")
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(["detect", str(home / ".codex"), "--json", "--user", "mallory", "--host", "h1"])
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["kind"], "loose")
        self.assertEqual(out["host"], "h1")
        self.assertEqual(out["agents"][0]["agent"], "codex-cli")
        self.assertEqual(out["agents"][0]["user"], "mallory")
        self.assertTrue(out["agents"][0]["parser"])

    def test_missing_input(self):
        self.assertEqual(cli.main(["detect", str(self.tmp / "nope")]), 2)


class ArchiveTests(unittest.TestCase):
    """Round trip through the sh collector when a POSIX shell is available:
    collector archive in, attributed artifacts and timeline out."""

    def setUp(self):
        self.cat = catalog.load()
        self.tmp = Path(tempfile.mkdtemp(prefix="cac-analyzer-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _collect(self):
        if not COLLECTOR.exists() or shutil.which("sh") is None or shutil.which("tar") is None:
            self.skipTest("collector or sh/tar not available")
        root = build_image(self.tmp / "image")
        out = self.tmp / "out"
        out.mkdir()
        r = subprocess.run(["sh", str(COLLECTOR), "-r", str(root), "-o", str(out), "-q", "--no-live"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        archives = list(out.glob("*.tar.gz"))
        self.assertEqual(len(archives), 1, list(out.iterdir()))
        return archives[0], out

    def test_archive_attribution_comes_from_manifest(self):
        archive, out = self._collect()
        col = open_input(archive, self.cat)
        try:
            self.assertEqual(col.kind, "archive")
            self.assertTrue(col.host)
            self.assertTrue(any("sha256 verified" in n for n in col.notes), col.notes)
            users = {a.home.user for a in col.artifacts if a.agent in ("claude-code", "codex-cli")}
            self.assertEqual(users, {"alice", "bob", "carol"})
            self.assertFalse(any(h.inferred for h in col.homes))
            # every attributed file exists on disk after extraction
            for a in col.artifacts:
                self.assertTrue(a.disk_path.is_file(), a.disk_path)
        finally:
            col.cleanup()
        self.assertFalse(Path(col.root).exists())

    def test_extracted_directory_and_timeline_cli(self):
        archive, out = self._collect()
        extracted = self.tmp / "extracted"
        extracted.mkdir()
        with tarfile.open(archive) as tf:
            if hasattr(tarfile, "data_filter"):
                tf.extractall(extracted, filter="data")
            else:
                tf.extractall(extracted)
        col = open_input(extracted, self.cat)
        self.assertEqual(col.kind, "collected")
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(["timeline", str(extracted), "-o", str(self.tmp / "tl")])
        self.assertEqual(rc, 0, buf.getvalue())
        rows = (self.tmp / "tl" / "timeline.csv").read_text(encoding="utf-8").splitlines()
        self.assertGreater(len(rows), 20)
        self.assertTrue(rows[0].startswith("timestamp_utc,host,user,agent"))
        self.assertTrue((self.tmp / "tl" / "sessions.csv").exists())
        self.assertTrue((self.tmp / "tl" / "detect.json").exists())
        # host comes from collection.json, users from the manifest
        self.assertTrue(all(",alice," in r or ",bob," in r or ",carol," in r for r in rows[1:]), rows[1:3])


if __name__ == "__main__":
    unittest.main()
