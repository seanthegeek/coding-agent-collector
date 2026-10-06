"""Inputs that cannot be read: the reason is printed, the exit code is 2 for
the input itself, and anything unreadable inside an input is a problem line,
never a traceback and never silence (issue 37)."""

import contextlib
import io
import json
import os
import shutil
import stat
import tarfile
import tempfile
import unittest
from pathlib import Path

from doubleagent import cli
from fixtures import CLAUDE_SESSION, build_home

CAN_DENY = os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() != 0
DENY_REASON = "chmod does not deny access as root or on Windows"

SESSION_REL = ".claude/projects/-srv-proj/" + CLAUDE_SESSION + ".jsonl"


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli.main(argv)
    return rc, out.getvalue(), err.getvalue()


def build_collected(root: Path, extra_rows=()) -> Path:
    """A minimal extracted collection: one Claude Code transcript under
    fs/home/alice with its manifest row, plus any extra rows given."""
    home = build_home(root / "src", with_noise=False)
    dest = root / "col" / "fs/home/alice" / SESSION_REL
    dest.parent.mkdir(parents=True)
    shutil.copyfile(home / SESSION_REL, dest)
    rows = [manifest_row(SESSION_REL), *extra_rows]
    col = root / "col"
    with open(col / "manifest.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    (col / "collection.json").write_text('{"hostname": "h1"}', encoding="utf-8")
    return col


def manifest_row(rel: str) -> dict:
    return {
        "path": "/home/alice/" + rel,
        "home": "/home/alice",
        "user": "alice",
        "agent": "claude-code",
        "type": "file",
        "status": "collected",
        "size": 1,
        "archive_path": "fs/home/alice/" + rel,
    }


def make_archive(src: Path, dest: Path) -> Path:
    with tarfile.open(dest, "w:gz") as tf:
        for p in sorted(src.iterdir()):
            tf.add(p, arcname=p.name)
    return dest


class ErrorTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cac-errors-test-"))
        self._locked: list[Path] = []

    def tearDown(self):
        for p in self._locked:
            os.chmod(p, stat.S_IRWXU)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def lock(self, p: Path) -> None:
        os.chmod(p, 0)
        self._locked.append(p)

    def assertInputError(self, argv, path, reason):
        rc, out, err = run_cli(argv)
        self.assertEqual(rc, 2, out + err)
        self.assertEqual(err, "error: %s: %s\n" % (path, reason))
        self.assertNotIn("Traceback", out + err)


class MissingInputTests(ErrorTestBase):
    def test_detect(self):
        p = self.tmp / "nope.tar.gz"
        self.assertInputError(["detect", str(p)], p, "no such file or directory")

    def test_timeline(self):
        p = self.tmp / "nope.tar.gz"
        self.assertInputError(
            ["timeline", str(p), "-o", str(self.tmp / "out")], p, "no such file or directory"
        )
        self.assertFalse((self.tmp / "out").exists())

    def test_inventory(self):
        p = self.tmp / "nope.txt"
        self.assertInputError(
            ["inventory", str(p), "-o", str(self.tmp / "f.csv")], p, "no such file or directory"
        )
        self.assertFalse((self.tmp / "f.csv").exists())


class MissingFromCollectionTests(ErrorTestBase):
    """A manifest row whose file is absent from fs/ is one problem line."""

    def setUp(self):
        super().setUp()
        gone = manifest_row(".claude/projects/-srv-proj/gone.jsonl")
        self.col = build_collected(self.tmp, [gone])
        self.line = "/home/alice/.claude/projects/-srv-proj/gone.jsonl: missing from the collection"

    def check(self, path):
        rc, out, err = run_cli(["timeline", str(path), "-o", str(self.tmp / "tl")])
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(out.count("problem:   " + self.line + "\n"), 1, out)
        rows = (self.tmp / "tl" / "timeline.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertGreater(len(rows), 0)
        detect = json.loads((self.tmp / "tl" / "detect.json").read_text(encoding="utf-8"))
        self.assertEqual(detect["problems"], [self.line])
        rc, out, err = run_cli(["detect", str(path)])
        self.assertEqual(rc, 0, out + err)
        self.assertIn("problem: " + self.line + "\n", out)

    def test_extracted_collection(self):
        self.check(self.col)

    def test_archive(self):
        self.check(make_archive(self.col, self.tmp / "x_agent-artifacts.tar.gz"))


@unittest.skipUnless(CAN_DENY, DENY_REASON)
class PermissionTests(ErrorTestBase):
    def test_unreadable_archive(self):
        archive = make_archive(build_collected(self.tmp), self.tmp / "y.tar.gz")
        self.lock(archive)
        self.assertInputError(["detect", str(archive)], archive, "permission denied")
        self.assertInputError(
            ["timeline", str(archive), "-o", str(self.tmp / "out")], archive, "permission denied"
        )

    def test_archive_in_untraversable_directory(self):
        locked = self.tmp / "locked"
        locked.mkdir()
        archive = make_archive(build_collected(self.tmp), locked / "x.tar.gz")
        self.lock(locked)
        self.assertInputError(["detect", str(archive)], archive, "permission denied")
        self.assertInputError(
            ["timeline", str(archive), "-o", str(self.tmp / "out")], archive, "permission denied"
        )

    def test_unreadable_input_directory(self):
        home = build_home(self.tmp / "alice")
        self.lock(home)
        self.assertInputError(["detect", str(home)], home, "permission denied")

    def test_unreadable_manifest(self):
        col = build_collected(self.tmp)
        self.lock(col / "manifest.jsonl")
        self.assertInputError(["detect", str(col)], col / "manifest.jsonl", "permission denied")

    def test_unreadable_inventory_input(self):
        f = self.tmp / "ws01.txt"
        f.write_text("", encoding="utf-8")
        self.lock(f)
        self.assertInputError(
            ["inventory", str(f), "-o", str(self.tmp / "f.csv")], f, "permission denied"
        )

    def test_unreadable_directory_in_loose_tree(self):
        root = self.tmp / "image"
        build_home(root / "home/alice")
        build_home(root / "home/bob")
        locked_home = root / "home/bob"
        locked_agent = root / "home/alice/.codex"
        self.lock(locked_home)
        self.lock(locked_agent)
        rc, out, err = run_cli(["detect", str(root)])
        self.assertEqual(rc, 0, out + err)
        self.assertIn("problem: %s: permission denied\n" % locked_home, out)
        self.assertIn("problem: %s: permission denied\n" % locked_agent, out)
        self.assertEqual(out.count("problem:"), 2, out)
        rc, out, err = run_cli(["detect", str(root), "--json"])
        self.assertEqual(
            sorted(json.loads(out)["problems"]),
            sorted("%s: permission denied" % p for p in (locked_home, locked_agent)),
        )
        rc, out, err = run_cli(["timeline", str(root), "-o", str(self.tmp / "tl")])
        self.assertEqual(rc, 0, out + err)
        self.assertIn("problem:   %s: permission denied\n" % locked_agent, out)

    def test_unreadable_file_problem_names_path_once(self):
        col = build_collected(self.tmp)
        self.lock(col / "fs/home/alice" / SESSION_REL)
        rc, out, err = run_cli(["timeline", str(col), "-o", str(self.tmp / "tl")])
        self.assertEqual(rc, 1, out + err)  # the only transcript could not be read
        self.assertNotIn("Traceback", out + err)
        self.assertIn("problem:   /home/alice/%s: permission denied\n" % SESSION_REL, out)
        self.assertNotIn("Errno", out)


if __name__ == "__main__":
    unittest.main()
