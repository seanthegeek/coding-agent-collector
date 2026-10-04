import contextlib
import csv
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from agent_analyzer import cli, inventory

from fixtures import build_image

REPO = Path(__file__).resolve().parents[2]
COLLECTOR = REPO / "collectors" / "collect-agent-artifacts.sh"

# Captured stdout of two hosts, in the shapes collect-agent-artifacts.sh and
# Collect-AgentArtifacts.ps1 print with --inventory / -Inventory (1.6.0).
HOST_A = """\
{"type":"host","host":"ws01","collector":"1.6.0","mode":"live","at":"2026-10-04T16:31:54Z","users_scanned":3,"users_unreadable":1,"docker_volumes":1}
{"type":"agent","host":"ws01","user":"alice","agent":"claude-code","files":6,"bytes":318,"first":"2026-09-15T01:02:03Z","last":"2026-10-04T16:31:11Z","projects":2,"evidence":".claude,.claude.json*"}
{"type":"agent","host":"ws01","user":"alice","agent":"codex-cli","files":1,"bytes":35,"first":"2026-10-01T00:00:00Z","last":"2026-10-01T00:00:00Z","projects":2,"evidence":".codex"}
{"type":"agent","host":"ws01","user":"bob","agent":"claude-code","files":0,"bytes":0,"first":"","last":"","projects":0,"evidence":".claude"}
{"type":"agent","host":"ws01","user":"docker","agent":"agent-zero","files":2,"bytes":63,"first":"2026-10-02T10:00:00Z","last":"2026-10-03T10:00:00Z","projects":0,"evidence":"*a0_usr"}
"""

# What an EDR console export looks like: a banner, a prompt, a blank line, a
# truncated record and a JSON value that is not an inventory record.
HOST_B = """\
Real Time Response session started on WS02
C:\\> runscript -CloudFile=Collect-AgentArtifacts -CommandLine=-Inventory

{"type":"host","host":"WS02","collector":"1.6.0","mode":"live","at":"2026-10-04T17:00:00Z","users_scanned":1,"users_unreadable":0,"docker_volumes":0}
{"type":"agent","host":"WS02","user":"carol","agent":"claude-code","files":3,"bytes":90,"first":"2026-10-04T08:00:00Z","last":"2026-10-04T12:00:00Z","projects":1,"evidence":".claude"}
{"type":"agent","host":"WS02","user":"carol","agent":"cur
{"note":"not a record"}
"""

# A host where nothing was found: the host line alone.
HOST_C = """\
{"type":"host","host":"srv03","collector":"1.6.0","mode":"image","at":"2026-10-04T18:00:00Z","users_scanned":2,"users_unreadable":0,"docker_volumes":0}
"""


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cac-inventory-test-"))
        self.inputs = self.tmp / "captures"
        self.inputs.mkdir()
        (self.inputs / "ws01.txt").write_text(HOST_A, encoding="utf-8")
        (self.inputs / "ws02.txt").write_text(HOST_B, encoding="utf-8")
        (self.inputs / "srv03.txt").write_text(HOST_C, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, argv, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        old = os.getcwd()
        if cwd:
            os.chdir(cwd)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = cli.main(argv)
        finally:
            os.chdir(old)
        return rc, out.getvalue(), err.getvalue()

    def read_csv(self, path):
        with open(path, newline="", encoding="utf-8") as fh:
            return list(csv.reader(fh))

    def test_default_file_name_and_columns(self):
        work = self.tmp / "work"
        work.mkdir()
        rc, out, _ = self.run_cli(["inventory", str(self.inputs)], cwd=work)
        self.assertEqual(rc, 0)
        path = work / "fleet-inventory.csv"
        self.assertTrue(path.is_file())
        rows = self.read_csv(path)
        self.assertEqual(rows[0], [
            "host", "collector", "mode", "at", "user", "agent", "files", "bytes",
            "first", "last", "projects", "evidence"])
        self.assertEqual(rows[0], inventory.INVENTORY_COLUMNS)
        # srv03 (empty) + 4 ws01 agents + 1 WS02 agent; files sorted by name.
        self.assertEqual(len(rows), 1 + 1 + 4 + 1)
        self.assertIn("fleet-inventory.csv", out)

    def test_output_option(self):
        target = self.tmp / "out" / "fleet.csv"
        rc, _, _ = self.run_cli(["inventory", "-o", str(target), str(self.inputs / "ws01.txt")])
        self.assertEqual(rc, 0)
        rows = self.read_csv(target)
        self.assertEqual(len(rows), 5)
        alice = [r for r in rows[1:] if r[4] == "alice" and r[5] == "claude-code"][0]
        self.assertEqual(alice, [
            "ws01", "1.6.0", "live", "2026-10-04T16:31:54.000Z", "alice", "claude-code", "6", "318",
            "2026-09-15T01:02:03.000Z", "2026-10-04T16:31:11.000Z", "2", ".claude,.claude.json*"])
        bob = [r for r in rows[1:] if r[4] == "bob"][0]
        self.assertEqual(bob[6:10], ["0", "0", "", ""])
        docker = [r for r in rows[1:] if r[4] == "docker"][0]
        self.assertEqual((docker[5], docker[11]), ("agent-zero", "*a0_usr"))

    def test_junk_lines_skipped_and_counted(self):
        rc, _, err = self.run_cli(["inventory", "-o", str(self.tmp / "b.csv"), str(self.inputs / "ws02.txt")])
        self.assertEqual(rc, 0)
        self.assertIn("skipped 4 non-inventory lines in", err)
        rows = self.read_csv(self.tmp / "b.csv")
        self.assertEqual([r[5] for r in rows[1:]], ["claude-code"])
        self.assertEqual(rows[1][0], "WS02")

    def test_empty_host_row(self):
        rc, _, _ = self.run_cli(["inventory", "-o", str(self.tmp / "c.csv"), str(self.inputs / "srv03.txt")])
        self.assertEqual(rc, 0)
        rows = self.read_csv(self.tmp / "c.csv")
        self.assertEqual(rows[1], ["srv03", "1.6.0", "image", "2026-10-04T18:00:00.000Z"] + [""] * 8)

    def test_rollup(self):
        rc, out, _ = self.run_cli(["inventory", "-o", str(self.tmp / "r.csv"), str(self.inputs)])
        self.assertEqual(rc, 0)
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("rows:   6 from 3 hosts in "))
        table = [l.split() for l in lines[lines.index("") + 1:]]
        self.assertEqual(table[0], ["agent", "hosts", "users", "latest"])
        self.assertEqual(table[1], ["claude-code", "2", "3", "2026-10-04T16:31:11.000Z"])
        self.assertEqual(table[2], ["agent-zero", "1", "1", "2026-10-03T10:00:00.000Z"])
        self.assertEqual(table[3], ["codex-cli", "1", "1", "2026-10-01T00:00:00.000Z"])
        self.assertEqual(len(table), 4)

    def test_agent_line_without_host_line(self):
        f = self.tmp / "orphan.txt"
        f.write_text(HOST_A.split("\n", 1)[1], encoding="utf-8")
        rc, _, _ = self.run_cli(["inventory", "-o", str(self.tmp / "o.csv"), str(f)])
        self.assertEqual(rc, 0)
        rows = self.read_csv(self.tmp / "o.csv")
        self.assertEqual(rows[1][:5], ["ws01", "", "", "", "alice"])

    def test_no_records_and_missing_input(self):
        f = self.tmp / "junk.txt"
        f.write_text("nothing here\n", encoding="utf-8")
        rc, _, _ = self.run_cli(["inventory", "-o", str(self.tmp / "j.csv"), str(f)])
        self.assertEqual(rc, 1)
        self.assertEqual(self.read_csv(self.tmp / "j.csv"), [inventory.INVENTORY_COLUMNS])
        rc, _, err = self.run_cli(["inventory", "-o", str(self.tmp / "m.csv"), str(self.tmp / "missing")])
        self.assertEqual(rc, 2)
        self.assertIn("does not exist", err)

    @unittest.skipUnless(shutil.which("sh"), "needs sh")
    def test_collector_inventory_end_to_end(self):
        root = build_image(self.tmp / "image")
        cap = self.tmp / "e2e"
        cap.mkdir()
        with open(cap / "image.txt", "w", encoding="utf-8") as fh:
            r = subprocess.run(["sh", str(COLLECTOR), "-r", str(root), "--inventory", "-q"],
                               stdout=fh, stderr=subprocess.PIPE)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr, b"")
        rc, _, err = self.run_cli(["inventory", "-o", str(self.tmp / "e2e.csv"), str(cap)])
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")
        rows = self.read_csv(self.tmp / "e2e.csv")
        pairs = {(r[4], r[5]) for r in rows[1:]}
        self.assertIn(("alice", "claude-code"), pairs)
        self.assertIn(("carol", "codex-cli"), pairs)
        self.assertTrue(all(r[2] == "image" for r in rows[1:]))


if __name__ == "__main__":
    unittest.main()
