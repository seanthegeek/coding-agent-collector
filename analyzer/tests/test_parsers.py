import csv
import io
import shutil
import tempfile
import unittest
from pathlib import Path

from agent_analyzer import catalog, cli
from agent_analyzer.inputs import open_input
from agent_analyzer.model import summarise
from agent_analyzer.parsers import Options, by_agent
from agent_analyzer.parsers.claude_code import ClaudeCodeParser, tool_summary
from agent_analyzer.parsers.codex import CodexParser
from agent_analyzer.timeutil import to_utc

from agent_analyzer.parsers.antigravity import AntigravityParser, tool_args_summary, uri_to_path
from agent_analyzer.parsers.crush import CrushParser, project_of
from agent_analyzer.parsers.goose import GooseParser, unescape_history
from agent_analyzer import protobuf, sqlite_util

from agent_analyzer.parsers.gemini_cli import GeminiCliParser, resolve_project
from fixtures import GEMINI_HASH, GEMINI_LEGACY, GEMINI_REL, GEMINI_RESUMED, GEMINI_SESSION, GEMINI_SUBAGENT
from fixtures import AGY_CONVERSATION, CLAUDE_SESSION, CODEX_SESSION, build_home, write_bad_line
from fixtures import CRUSH_SESSION, GOOSE_LEGACY_REL, GOOSE_SESSION


class TimeTests(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(to_utc("2026-10-01T10:00:00.000Z"), "2026-10-01T10:00:00.000Z")
        self.assertEqual(to_utc("2026-10-01T12:00:00+02:00"), "2026-10-01T10:00:00.000Z")
        self.assertEqual(to_utc(1790848800000), "2026-10-01T10:00:00.000Z")   # ms
        self.assertEqual(to_utc(1790848800), "2026-10-01T10:00:00.000Z")      # s
        self.assertEqual(to_utc("1790848800"), "2026-10-01T10:00:00.000Z")
        self.assertEqual(to_utc(None), "")
        self.assertEqual(to_utc("garbage"), "")


class ParserBase(unittest.TestCase):
    def setUp(self):
        self.cat = catalog.load()
        self.tmp = Path(tempfile.mkdtemp(prefix="cac-analyzer-test-"))
        self.home = build_home(self.tmp / "home" / "alice")
        self.col = open_input(self.tmp / "home", self.cat, host="h1")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def rows_for(self, parser, rel, **kw):
        art = next(a for a in self.col.artifacts if a.rel == rel)
        return list(parser.parse(art, Options(**kw)))


class ClaudeCodeTests(ParserBase):
    REL = ".claude/projects/-srv-proj/%s.jsonl" % CLAUDE_SESSION

    def test_rows(self):
        rows = self.rows_for(ClaudeCodeParser(), self.REL)
        types = [r.turn_type for r in rows]
        self.assertEqual(types, ["user", "tool_use", "tool_result", "assistant", "system", "system", "system"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent), ("h1", "alice", "claude-code"))
            self.assertEqual(r.session_id, CLAUDE_SESSION)
            self.assertEqual(r.source_file, "/alice/" + self.REL)   # original path is relative to the input root
            self.assertTrue(r.timestamp_utc.endswith("Z"), r)
        user, use, result, asst, dur, meta, pr = rows
        self.assertEqual(user.text, "delete the logs in /var/log please")
        self.assertEqual((user.project_path, user.git_branch), ("/srv/proj", "main"))
        self.assertEqual((use.tool_name, use.tool_use_id, use.model), ("Bash", "toolu_01", "claude-fable-5-1"))
        self.assertEqual(use.text, "rm -rf /var/log/*.log")
        self.assertEqual((result.tool_use_id, result.text), ("toolu_01", "removed 3 files"))
        self.assertEqual(asst.text, "Done. Three log files were removed.")
        self.assertEqual(dur.text, "turn_duration: 4000 ms, 5 messages")
        self.assertTrue(meta.text.startswith("<local-command-stdout>"))
        self.assertEqual(pr.text, "pr-link: https://github.com/x/y/pull/7")
        self.assertEqual([r.source_line for r in rows], [2, 4, 5, 6, 7, 8, 9])

    def test_thinking_opt_in(self):
        rows = self.rows_for(ClaudeCodeParser(), self.REL, include_thinking=True)
        self.assertIn("thinking", [r.turn_type for r in rows])
        self.assertEqual(next(r for r in rows if r.turn_type == "thinking").text, "private reasoning")

    def test_max_text_length(self):
        rows = self.rows_for(ClaudeCodeParser(), self.REL, max_text_length=10)
        self.assertTrue(all(len(r.text) <= 10 for r in rows))
        self.assertTrue(rows[0].text.endswith("…"))

    def test_history(self):
        rows = self.rows_for(ClaudeCodeParser(), ".claude/history.jsonl")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].timestamp_utc, "2026-10-01T10:00:00.000Z")
        self.assertEqual(rows[0].project_path, "/srv/proj")
        self.assertEqual(rows[1].project_path, "/srv/old")
        self.assertTrue(all(r.turn_type == "user" for r in rows))

    def test_subagent_file_is_parsed(self):
        rel = ".claude/projects/-srv-proj/%s/subagents/agent-abc.jsonl" % CLAUDE_SESSION
        rows = self.rows_for(ClaudeCodeParser(), rel)
        self.assertEqual([r.turn_type for r in rows], ["user"])

    def test_settings_not_wanted(self):
        art = next(a for a in self.col.artifacts if a.rel == ".claude/settings.json")
        self.assertFalse(ClaudeCodeParser().wants(art))

    def test_tool_summary_shapes(self):
        self.assertEqual(tool_summary("Edit", {"file_path": "/a", "old_string": "x", "new_string": "y"}), "/a")
        self.assertEqual(tool_summary("Grep", {"pattern": "foo", "path": "/src"}), "foo | /src")
        self.assertEqual(tool_summary("Unknown", {"z": 1, "a": 2}), '{"a":2,"z":1}')
        self.assertEqual(tool_summary("Unknown", "raw"), '"raw"')

    def test_truncated_last_line_is_reported_not_fatal(self):
        write_bad_line(self.home / self.REL)
        rows = self.rows_for(ClaudeCodeParser(), self.REL)
        self.assertEqual(len(rows), 8)
        self.assertIn("1 unparseable line", rows[-1].text)
        self.assertEqual(rows[-1].source_line, 11)


class CodexTests(ParserBase):
    REL = ".codex/sessions/2026/10/02/rollout-2026-10-02T09-00-00-%s.jsonl" % CODEX_SESSION

    def test_rows(self):
        rows = self.rows_for(CodexParser(), self.REL)
        types = [r.turn_type for r in rows]
        self.assertEqual(types, ["system", "system", "system", "user", "tool_use", "tool_result",
                                 "tool_use", "tool_result", "assistant", "system"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent), ("h1", "alice", "codex-cli"))
            self.assertEqual(r.session_id, CODEX_SESSION)
            self.assertEqual(r.project_path, "/srv/proj")
            self.assertEqual(r.git_branch, "feature/x")
        start, started, dev, user, sh, shout, patch, patchout, asst, done = rows
        self.assertIn("session start: codex_cli_rs 0.99.0", start.text)
        self.assertEqual(start.model, "")                      # model unknown until turn_context
        self.assertEqual(user.model, "gpt-5-codex")
        self.assertTrue(dev.text.startswith("developer: You are Codex."))
        self.assertEqual((sh.tool_name, sh.tool_use_id, sh.text), ("shell", "call_1", "ls -la ~"))
        self.assertEqual((shout.tool_use_id, shout.text), ("call_1", "total 42"))
        self.assertEqual((patch.tool_name, patch.text), ("apply_patch", '{"patch":"*** Begin Patch"}'))
        self.assertEqual(patchout.text, "Done")
        self.assertEqual(asst.text, "Listed the home directory.")
        self.assertEqual(done.text, "task_complete turn=t1 duration_ms=7000")

    def test_reasoning_opt_in(self):
        rows = self.rows_for(CodexParser(), self.REL, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["thinking"])

    def test_history(self):
        rows = self.rows_for(CodexParser(), ".codex/history.jsonl")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].timestamp_utc, "2026-10-02T09:00:02.000Z")
        self.assertEqual(rows[0].session_id, CODEX_SESSION)

    def test_config_not_wanted(self):
        art = next(a for a in self.col.artifacts if a.rel == ".codex/config.toml")
        self.assertFalse(CodexParser().wants(art))


class TimelineTests(ParserBase):
    def test_cli_timeline_outputs(self):
        out = self.tmp / "out"
        buf = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(buf):
            rc = cli.main(["timeline", str(self.tmp / "home"), "-o", str(out), "--host", "h1"])
        self.assertEqual(rc, 0, buf.getvalue())
        with open(out / "timeline.csv", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        ts = [r["timestamp_utc"] for r in rows if r["timestamp_utc"]]
        self.assertEqual(ts, sorted(ts))
        # Subset checks: each parser branch adds its own agents and sessions.
        expected_agents = {
            "claude-code", "codex-cli", "antigravity",
            "qwen-code",
            "kiro",
            "gemini-cli",
            "crush", "goose",
            "zed", "vscode",
            "cline", "roo-code",
            "tabby",
            "openhands", "shellgpt",
            "pi", "little-coder", "letta",
            "hermes", "agent-zero",
            "open-interpreter",
        }
        self.assertLessEqual(expected_agents, {r["agent"] for r in rows})
        self.assertEqual({r["host"] for r in rows}, {"h1"})
        with open(out / "sessions.csv", encoding="utf-8", newline="") as fh:
            sessions = {r["session_id"]: r for r in csv.DictReader(fh)}
        expected_sessions = {
            CLAUDE_SESSION, CODEX_SESSION, AGY_CONVERSATION, "99999999-0000-4000-8000-000000000000",
            "e5f6a7b8-4444-4000-8000-000000000011", "0a0b0c0d-4444-4000-8000-000000000022",
            KIRO_SESSION, KIRO_EXPORT_SESSION, KIRO_SHELL_SESSION,
            GEMINI_SESSION, GEMINI_RESUMED, GEMINI_LEGACY, GEMINI_SUBAGENT,
            CRUSH_SESSION, GOOSE_SESSION, "20260301_090000",
            ZED_THREAD, ZED_EXTERNAL, VSCODE_SESSION, VSCODE_LEGACY_SESSION,
            OPENHANDS_CONV, OPENHANDS_CLI_CONV, SHELLGPT_CHAT,
            "0199a1b2-7c3d-7e4f-8a5b-6c7d8e9f0a1b", "local-conv-1", "conv-9f",
            "20261001_120000_a1b2c3d4", "20261001_130000_0badf00d", "AbCd1234",
            OI_SESSION, OI_IMPORTED,
        }
        self.assertLessEqual(expected_sessions, set(sessions))
        c = sessions[CLAUDE_SESSION]
        self.assertEqual(c["models"], "claude-fable-5-1")
        self.assertEqual(c["tool_calls"], "1")
        self.assertTrue(c["source_file"].endswith(CLAUDE_SESSION + ".jsonl"), c["source_file"])
        self.assertEqual(c["first_timestamp_utc"], "2026-10-01T10:00:00.000Z")
        self.assertEqual(sessions[CODEX_SESSION]["models"], "gpt-5-codex")

    def test_agent_filter(self):
        out = self.tmp / "out"
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(["timeline", str(self.tmp / "home"), "-o", str(out), "--agent", "codex-cli"])
        with open(out / "timeline.csv", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual({r["agent"] for r in rows}, {"codex-cli"})


class ProjectRoutingTests(unittest.TestCase):
    """Round trip through the sh collector: files the collector finds inside a
    discovered repository are recorded with agent `project`, and the CLI
    offers them to every parser, so Crush and Aider rows come out of them."""

    def setUp(self):
        self.cat = catalog.load()
        self.tmp = Path(tempfile.mkdtemp(prefix="cac-analyzer-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _collect(self) -> Path:
        import subprocess
        collector = Path(__file__).resolve().parents[2] / "collectors" / "collect-agent-artifacts.sh"
        if not collector.exists() or shutil.which("sh") is None or shutil.which("tar") is None:
            self.skipTest("collector or sh/tar not available")
        from fixtures import CRUSH_SCHEMA, _wal_db, build_aider, build_image, crush_records
        root = build_image(self.tmp / "image")
        # Claude Code's history names /srv/proj, so the collector discovers it.
        proj = root / "srv/proj"
        build_aider(proj)
        _wal_db(proj / ".crush/crush.db", CRUSH_SCHEMA, crush_records())
        out = self.tmp / "out"
        out.mkdir()
        r = subprocess.run(["sh", str(collector), "-r", str(root), "-o", str(out), "-q", "--no-live"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        archives = list(out.glob("*.tar.gz"))
        self.assertEqual(len(archives), 1, list(out.iterdir()))
        return archives[0]

    def _timeline(self, archive: Path, *extra: str):
        import contextlib
        out = self.tmp / ("tl%d" % len(list(self.tmp.glob("tl*"))))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(["timeline", str(archive), "-o", str(out)] + list(extra))
        self.assertEqual(rc, 0, buf.getvalue())
        with open(out / "timeline.csv", encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh)), buf.getvalue()

    def test_project_artifacts_reach_their_parsers(self):
        archive = self._collect()
        col = open_input(archive, self.cat)
        try:
            project_rels = {a.rel for a in col.artifacts if a.agent == "project"}
        finally:
            col.cleanup()
        self.assertIn(".crush/crush.db", project_rels)
        self.assertIn(".aider.chat.history.md", project_rels)

        rows, summary = self._timeline(archive)
        from_project = [r for r in rows if "/srv/proj/" in r["source_file"]]
        self.assertEqual({r["agent"] for r in from_project}, {"crush", "aider"})
        self.assertTrue(any(r["source_file"].endswith("/srv/proj/.crush/crush.db") and r["turn_type"] == "user"
                            for r in from_project))
        self.assertTrue(any(r["source_file"].endswith("/srv/proj/.aider.chat.history.md") and r["turn_type"] == "user"
                            for r in from_project))
        self.assertNotIn("project", {r["agent"] for r in rows})
        self.assertNotIn("parsed project", summary)

        # --agent filters on the parser's agent, so repository files come along.
        rows, _ = self._timeline(archive, "--agent", "aider")
        self.assertEqual({r["agent"] for r in rows}, {"aider"})
        self.assertTrue(any(r["source_file"].endswith("/srv/proj/.aider.chat.history.md") for r in rows))

    def test_detect_does_not_call_project_parsed(self):
        archive = self._collect()
        col = open_input(archive, self.cat)
        try:
            table = cli.detect_table(col)
        finally:
            col.cleanup()
        project = [r for r in table if r["agent"] == "project"]
        self.assertTrue(project)
        self.assertFalse(any(r["parser"] for r in project))
        self.assertNotIn("project", by_agent())


if __name__ == "__main__":
    unittest.main()


class ProtobufTests(unittest.TestCase):
    SCHEMA = {"M": {1: ("a", "str"), 2: ("+n", "int"), 3: ("sub", "N"), 4: ("t", "ts"), 5: ("f", "bool"), 6: ("+subs", "N")},
              "N": {1: ("x", "str"), 2: ("d", "double")}}

    def test_round_trip(self):
        v = {"a": "hi", "n": [1, 2, 300], "sub": {"x": "y", "d": 1.5}, "t": 1790848800.5, "f": True,
             "subs": [{"x": "p"}, {"x": "q"}]}
        b = protobuf.encode(v, "M", self.SCHEMA)
        out = protobuf.decode(b, "M", self.SCHEMA)
        self.assertEqual(out["a"], "hi")
        self.assertEqual(out["n"], [1, 2, 300])
        self.assertEqual(out["sub"], {"x": "y", "d": 1.5})
        self.assertEqual(out["t"], "2026-10-01T10:00:00.500Z")
        self.assertTrue(out["f"])
        self.assertEqual([s["x"] for s in out["subs"]], ["p", "q"])

    def test_unknown_fields_are_skipped(self):
        wide = {"M": dict(self.SCHEMA["M"]), "N": self.SCHEMA["N"]}
        wide["M"].update({9: ("extra", "str"), 10: ("more", "N")})
        b = protobuf.encode({"a": "x", "extra": "ignored", "more": {"x": "z"}}, "M", wide)
        self.assertEqual(protobuf.decode(b, "M", self.SCHEMA), {"a": "x"})

    def test_truncated_buffer_raises(self):
        b = protobuf.encode({"a": "hello"}, "M", self.SCHEMA)
        with self.assertRaises(ValueError):
            protobuf.decode(b[:-2], "M", self.SCHEMA)


class SqliteUtilTests(unittest.TestCase):
    def test_copy_leaves_original_untouched_and_reads_wal(self):
        import sqlite3, time
        tmp = Path(tempfile.mkdtemp(prefix="cac-analyzer-test-"))
        try:
            db = tmp / "t.db"
            con = sqlite3.connect(str(db))
            con.execute("pragma journal_mode=wal")
            con.execute("create table t (x)")
            con.execute("insert into t values (1)")
            con.commit()
            # a second connection keeps the WAL from being checkpointed on close
            holder = sqlite3.connect(str(db))
            holder.execute("select count(*) from t").fetchone()
            con.execute("insert into t values (2)")
            con.commit()
            before = db.read_bytes()
            self.assertTrue((tmp / "t.db-wal").exists())
            with sqlite_util.open_copy(db) as c:
                self.assertEqual(c.execute("select count(*) from t").fetchone()[0], 2)
            self.assertEqual(db.read_bytes(), before)
            holder.close()
            con.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class AntigravityTests(ParserBase):
    REL = ".gemini/antigravity-cli/conversations/%s.db" % AGY_CONVERSATION

    def test_rows(self):
        rows = self.rows_for(AntigravityParser(), self.REL)
        types = [r.turn_type for r in rows]
        self.assertEqual(types, ["system", "user", "assistant", "tool_use", "tool_result", "tool_use", "tool_result",
                                 "tool_use", "tool_result", "system", "assistant", "system"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.session_id), ("h1", "alice", "antigravity", AGY_CONVERSATION))
            self.assertEqual((r.project_path, r.git_branch), ("/home/u/proj", "main"))
            self.assertTrue(r.timestamp_utc.endswith("Z"), r)
        start, user, asst, use1, res1, use2, res2, use3, res3, injected, final, ckpt = rows
        self.assertIn("session start", start.text)
        self.assertIn("project_id=default-cli-project", start.text)
        self.assertEqual(user.text, "clean the logs")
        self.assertEqual(user.timestamp_utc, "2026-10-01T10:00:00.000Z")
        self.assertEqual((asst.text, asst.model), ("I will read the README first.", "gemini-3.8-flash"))
        self.assertEqual((use1.tool_name, use1.tool_use_id, use1.text), ("view_file", "call_1", "/home/u/proj/README.md"))
        self.assertEqual((res1.tool_name, res1.tool_use_id), ("view_file", "call_1"))
        self.assertTrue(res1.text.startswith("File Path: README.md"))
        self.assertEqual(res1.timestamp_utc, "2026-10-01T10:00:04.000Z")      # completed_at, not created_at
        self.assertEqual((use2.tool_name, use2.text), ("run_command", "rm -rf /var/log/*.log"))
        self.assertEqual(res2.text, "rm -rf /var/log/*.log | exit=0 | removed 3 files")
        self.assertEqual(use3.text, "/home/u/proj/notes.md")
        self.assertEqual(res3.text, "[error] /home/u/proj/notes.md [created]")
        self.assertEqual(injected.turn_type, "system")                        # USER_IMPLICIT source
        self.assertEqual(final.text, "Done. Three log files were removed.")
        self.assertEqual(ckpt.text, "checkpoint: Clean logs")
        self.assertEqual([r.source_line for r in rows], [0, 0, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9])

    def test_thinking_opt_in(self):
        rows = self.rows_for(AntigravityParser(), self.REL, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["look before leaping"])

    def test_summaries_and_history(self):
        rows = self.rows_for(AntigravityParser(), ".gemini/antigravity-cli/conversation_summaries.db")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].session_id, AGY_CONVERSATION)
        self.assertEqual(rows[0].timestamp_utc, "2026-10-01T10:00:13.002Z")
        self.assertIn("CASCADE_RUN_STATUS_IDLE", rows[0].text)
        self.assertEqual(rows[0].project_path, "/home/u/proj")
        rows = self.rows_for(AntigravityParser(), ".gemini/antigravity-cli/history.jsonl")
        self.assertEqual((rows[0].turn_type, rows[0].text, rows[0].project_path), ("user", "clean the logs", "/home/u/proj"))

    def test_sidecars_and_token_not_wanted(self):
        p = AntigravityParser()
        for a in self.col.artifacts:
            if a.rel.endswith((".db-wal", ".db-shm", "antigravity-oauth-token")):
                self.assertFalse(p.wants(a), a.rel)

    def test_helpers(self):
        self.assertEqual(uri_to_path("file:///home/u/proj"), "/home/u/proj")
        self.assertEqual(uri_to_path("file:///c%3A/Users/u/proj"), "c:/Users/u/proj")
        self.assertEqual(uri_to_path("/plain/path"), "/plain/path")
        self.assertEqual(tool_args_summary('{"CommandLine":"ls","Cwd":"/x"}'), "ls")
        self.assertEqual(tool_args_summary('{"Other":1}'), '{"Other":1}')
        self.assertEqual(tool_args_summary("not json"), "not json")


from agent_analyzer.parsers.qwen_code import QwenCodeParser, args_summary  # noqa: E402
from fixtures import QWEN_ARCHIVED, QWEN_SESSION, QWEN_TMP  # noqa: E402


class QwenCodeTests(ParserBase):
    REL = ".qwen/projects/-srv-proj/chats/%s.jsonl" % QWEN_SESSION
    LOGS = ".qwen/tmp/%s/logs.json" % QWEN_TMP

    def test_rows(self):
        rows = self.rows_for(QwenCodeParser(), self.REL)
        self.assertEqual([r.turn_type for r in rows],
                         ["system", "user", "assistant", "tool_use", "tool_use", "tool_result", "tool_result",
                          "system", "system"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent), ("h1", "alice", "qwen-code"))
            self.assertEqual((r.session_id, r.project_path, r.git_branch), (QWEN_SESSION, "/srv/proj", "main"))
            self.assertTrue(r.timestamp_utc.endswith("Z"), r)
        model, user, asst, sh, read, shout, readout, slash, title = rows
        self.assertEqual((model.text, model.model), ("session_model: qwen3-coder-plus auth=qwen-oauth", "qwen3-coder-plus"))
        self.assertEqual((user.text, user.timestamp_utc), ("run the tests", "2026-10-01T10:00:00.000Z"))
        self.assertEqual((asst.text, asst.model), ("Running tests.", "qwen3-coder-plus"))
        self.assertEqual((sh.tool_name, sh.tool_use_id, sh.text, sh.model),
                         ("run_shell_command", "call_abc123", "npm test", "qwen3-coder-plus"))
        self.assertEqual((read.tool_name, read.text), ("read_file", "/srv/proj/.env"))
        self.assertEqual((shout.tool_name, shout.tool_use_id, shout.text), ("run_shell_command", "call_abc123", "12 passing"))
        self.assertEqual((readout.tool_use_id, readout.text), ("call_def456", "[error permission_denied] permission denied"))
        self.assertEqual(slash.text, "slash_command: invocation /compress")
        self.assertEqual(title.text, "custom_title: Run tests")
        self.assertEqual([r.source_line for r in rows], [1, 2, 3, 3, 3, 4, 5, 6, 7])

    def test_thinking_opt_in(self):
        rows = self.rows_for(QwenCodeParser(), self.REL, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["Plan: run npm test."])

    def test_archive_and_logs(self):
        rows = self.rows_for(QwenCodeParser(), ".qwen/projects/-srv-proj/chats/archive/%s.jsonl" % QWEN_ARCHIVED)
        self.assertEqual([(r.turn_type, r.session_id) for r in rows], [("user", QWEN_ARCHIVED)])
        rows = self.rows_for(QwenCodeParser(), self.LOGS)
        self.assertEqual([r.turn_type for r in rows], ["user", "system"])
        self.assertEqual((rows[0].text, rows[0].session_id, rows[0].project_path), ("run the tests", QWEN_SESSION, ""))
        self.assertEqual(rows[1].text, "model_switch: qwen3-coder-plus -> qwen3-vl-plus (vision_auto_switch)")
        self.assertEqual(rows[1].model, "qwen3-vl-plus")
        self.assertEqual([r.source_line for r in rows], [1, 2])

    def test_sidecars_config_and_credentials_not_wanted(self):
        p = QwenCodeParser()
        wanted = {a.rel for a in self.col.artifacts if a.agent == "qwen-code" and p.wants(a)}
        self.assertEqual(wanted, {self.REL, self.LOGS,
                                  ".qwen/projects/-srv-proj/chats/archive/%s.jsonl" % QWEN_ARCHIVED})

    def test_truncated_last_line_is_reported_not_fatal(self):
        write_bad_line(self.home / self.REL)
        rows = self.rows_for(QwenCodeParser(), self.REL)
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[-1].turn_type, "system")
        self.assertIn("1 unparseable line", rows[-1].text)
        self.assertEqual((rows[-1].source_line, rows[-1].session_id), (8, QWEN_SESSION))

    def test_truncated_logs_keep_earlier_entries(self):
        path = self.home / self.LOGS
        data = path.read_text(encoding="utf-8")
        path.write_text(data[: data.index('"model_switch"')], encoding="utf-8")
        rows = self.rows_for(QwenCodeParser(), self.LOGS)
        self.assertEqual([r.turn_type for r in rows], ["user", "system"])
        self.assertEqual(rows[0].text, "run the tests")
        self.assertIn("1 unparseable entry", rows[1].text)

    def test_args_summary(self):
        self.assertEqual(args_summary({"command": "ls"}), "ls")
        self.assertEqual(args_summary({"other": 1}), '{"other":1}')
        self.assertEqual(args_summary(None), "")


from agent_analyzer.parsers.kiro import KiroParser, salvage  # noqa: E402
from fixtures import KIRO_EXPORT_SESSION, KIRO_SESSION, KIRO_SHELL_SESSION  # noqa: E402


class KiroTests(ParserBase):
    DB = ".local/share/amazon-q/data.sqlite3"
    EXPORT = ".aws/amazonq/exports/issue-chat.json"

    def test_rows(self):
        rows = self.rows_for(KiroParser(), self.DB)
        conv = [r for r in rows if r.session_id == KIRO_SESSION]
        self.assertEqual([r.turn_type for r in conv], ["user", "assistant", "tool_use", "tool_result", "assistant"])
        for r in conv:
            self.assertEqual((r.host, r.user, r.agent), ("h1", "alice", "kiro"))
            self.assertEqual((r.project_path, r.git_branch, r.model), ("/srv/proj", "", "claude-sonnet-4"))
            self.assertEqual(r.source_line, 1)
        user, asst, use, res, final = conv
        self.assertEqual((user.text, user.timestamp_utc), ("list the files here", "2026-04-24T03:17:15.123Z"))
        self.assertEqual((asst.text, asst.timestamp_utc), ("I will list the directory.", "2026-04-24T03:17:16.900Z"))
        self.assertEqual((use.tool_name, use.tool_use_id, use.text), ("execute_bash", "tooluse_abc123", '{"command":"ls -la"}'))
        # null user.timestamp falls back to the entry's request start
        self.assertEqual((res.tool_name, res.tool_use_id, res.timestamp_utc),
                         ("execute_bash", "tooluse_abc123", "2026-04-24T03:17:17.000Z"))
        self.assertEqual(res.text, "total 8 README.md [Success]")
        self.assertEqual(final.timestamp_utc, "2026-04-24T03:17:18.100Z")

    def test_export_variants(self):
        rows = self.rows_for(KiroParser(), self.EXPORT)
        self.assertEqual([r.turn_type for r in rows],
                         ["user", "tool_use", "tool_result", "assistant", "tool_use", "user", "tool_result",
                          "assistant", "system", "system", "system"])
        self.assertTrue(all(r.session_id == KIRO_EXPORT_SESSION and r.project_path == "/srv/proj" for r in rows))
        user, mcp, mcpres, _, _, stop, cancelled, _, compact_, summary, pending = rows
        self.assertEqual((user.timestamp_utc, user.model), ("2026-04-24T14:00:00.000Z", "claude-3.7-sonnet"))  # legacy model
        self.assertEqual((mcp.tool_name, mcp.text), ("github___create_issue", 'orig_name=create_issue {"title":"bug"}'))
        self.assertEqual((mcpres.tool_name, mcpres.text), ("github___create_issue", '{"number":7} [Error]'))
        self.assertEqual(stop.text, "stop, do not delete")
        self.assertEqual((cancelled.tool_use_id, cancelled.text),
                         ("tooluse_bash2", "cancelled Tool use was cancelled by the user [Error]"))
        self.assertTrue(compact_.text.startswith("compact:"))
        self.assertEqual(summary.text, "summary: User asked to open an issue and cancelled a delete.")
        self.assertEqual(pending.text, "pending message (not sent): now push it")

    def test_thinking_opt_in(self):
        # the format records no reasoning, so the option changes nothing
        for rel in (self.DB, self.EXPORT):
            with_thinking = self.rows_for(KiroParser(), rel, include_thinking=True)
            self.assertEqual(len(self.rows_for(KiroParser(), rel)), len(with_thinking))
            self.assertFalse([r for r in with_thinking if r.turn_type == "thinking"])

    def test_shell_history_and_bad_blob(self):
        rows = self.rows_for(KiroParser(), self.DB)
        shell = [r for r in rows if r.session_id == KIRO_SHELL_SESSION]
        self.assertEqual(len(shell), 1)
        self.assertEqual((shell[0].turn_type, shell[0].timestamp_utc, shell[0].project_path),
                         ("system", "2026-04-24T03:00:00.000Z", "/srv/proj"))
        self.assertTrue(shell[0].text.startswith("shell history: git status"))
        bad = [r for r in rows if r.project_path == "/srv/broken"]
        self.assertEqual(len(bad), 1)
        self.assertEqual((bad[0].turn_type, bad[0].source_line), ("system", 2))
        self.assertIn("unparseable", bad[0].text)
        self.assertNotIn("REDACT-ME", " ".join(r.text for r in rows))

    def test_not_wanted(self):
        p = KiroParser()
        for rel in (".kiro/settings/cli.json", ".kiro/sessions/s1.json"):
            art = next(a for a in self.col.artifacts if a.rel == rel)
            self.assertEqual(art.agent, "kiro")
            self.assertFalse(p.wants(art), rel)

    def test_truncated_export_is_reported_not_fatal(self):
        rows = self.rows_for(KiroParser(), ".aws/amazonq/exports/issue-chat-cut.json")
        self.assertEqual([r.turn_type for r in rows],
                         ["user", "tool_use", "tool_result", "assistant", "tool_use", "system"])
        self.assertEqual(rows[0].session_id, KIRO_EXPORT_SESSION)
        self.assertIn("2 history entries recovered", rows[-1].text)

    def test_salvage(self):
        self.assertEqual(salvage('{"a": 1}'), ({"a": 1}, ""))
        state, err = salvage('{"conversation_id": "c\\"1", "history": [{"x": 1}, {"y": ')
        self.assertEqual(state, {"conversation_id": 'c"1', "history": [{"x": 1}]})
        self.assertTrue(err)
        self.assertEqual(salvage("garbage")[0], None)


class GeminiCliTests(ParserBase):
    REL = GEMINI_REL
    LEGACY = ".gemini/tmp/%s/chats/session-2026-09-30T08-00-b2c3d4e5.json" % GEMINI_HASH

    def test_rows(self):
        rows = self.rows_for(GeminiCliParser(), self.REL)
        types = [r.turn_type for r in rows]
        self.assertEqual(types, ["system", "user", "assistant", "tool_use", "tool_result", "user", "assistant",
                                 "tool_use", "tool_result", "system", "tool_use", "tool_result", "user",
                                 "system", "system"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent), ("h1", "alice", "gemini-cli"))
            self.assertEqual((r.project_path, r.git_branch), ("/srv/proj", ""))
            self.assertTrue(r.timestamp_utc.endswith("Z"), r)
        start, u1, g1, ls, lsout, u3, g3, rf, rfout, info, sh, shout, u4, summ, rewind = rows
        self.assertIn("session start: kind=main", start.text)
        self.assertEqual((u1.text, u1.session_id), ("list files in src", GEMINI_SESSION))
        self.assertEqual((g1.text, g1.model, g1.source_line), ("Listing now.", "gemini-2.5-pro", 4))  # re-appended record
        self.assertEqual((ls.tool_name, ls.tool_use_id), ("list_directory", "list_directory-1759309207000"))
        self.assertEqual(ls.text, 'ReadFolder: {"path":"/srv/proj/src"}')
        self.assertEqual(ls.timestamp_utc, "2026-10-01T09:00:07.100Z")
        self.assertEqual((lsout.tool_use_id, lsout.text), ("list_directory-1759309207000", "main.ts util.ts"))
        self.assertNotIn("delete everything", " ".join(r.text for r in rows))    # rewound
        self.assertEqual(g3.text, "Here is util.ts.")                             # $patch content
        self.assertEqual(rfout.text, "export const x = 1")                        # $patch toolCalls result
        self.assertEqual(info.text, "info: Request cancelled.")
        self.assertEqual((sh.text, sh.model), ('Shell: {"command":"curl http://x"}', "gemini-2.5-flash"))
        self.assertEqual(shout.text, "[cancelled]")
        self.assertEqual(u4.session_id, GEMINI_RESUMED)                           # $set.sessionId on resume
        self.assertEqual(rf.session_id, GEMINI_SESSION)
        self.assertEqual((summ.text, summ.timestamp_utc, summ.source_line),
                         ("summary: List src files", "2026-10-01T09:00:08.000Z", 5))
        self.assertEqual((rewind.text, rewind.source_line), ("rewind to msg-u2: 2 message(s) dropped", 8))

    def test_thinking_opt_in(self):
        rows = self.rows_for(GeminiCliParser(), self.REL, include_thinking=True)
        think = [r for r in rows if r.turn_type == "thinking"]
        self.assertEqual([(r.text, r.timestamp_utc) for r in think], [("Plan: Use the ls tool.", "2026-10-01T09:00:06.500Z")])

    def test_legacy_json_and_hash_directory(self):
        rows = self.rows_for(GeminiCliParser(), self.LEGACY)
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "assistant"])
        self.assertTrue(all(r.session_id == GEMINI_LEGACY for r in rows))
        self.assertTrue(all(r.project_path == "/srv/proj" for r in rows))   # sha256 match in projects.json
        self.assertEqual((rows[2].text, rows[2].model), ("Hi.", "gemini-2.0-flash"))
        rows = self.rows_for(GeminiCliParser(), self.LEGACY, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["weighing it"])

    def test_subagent_session(self):
        rel = ".gemini/tmp/proj/chats/%s/%s.jsonl" % (GEMINI_SESSION, GEMINI_SUBAGENT)
        rows = self.rows_for(GeminiCliParser(), rel)
        self.assertEqual([r.turn_type for r in rows], ["system", "user"])
        self.assertIn("kind=subagent", rows[0].text)
        self.assertEqual(rows[1].session_id, GEMINI_SUBAGENT)

    def test_history(self):
        rows = self.rows_for(GeminiCliParser(), ".gemini/tmp/proj/logs.json")
        self.assertEqual([r.turn_type for r in rows], ["user", "user"])
        self.assertEqual(rows[1].text, "delete everything in /srv/proj")        # kept although rewound
        self.assertEqual((rows[0].session_id, rows[0].project_path), (GEMINI_SESSION, "/srv/proj"))
        self.assertEqual(rows[0].timestamp_utc, "2026-10-01T09:00:05.000Z")

    def test_project_fallbacks(self):
        base = self.home / ".gemini"
        self.assertEqual(resolve_project(base, "proj"), "/srv/proj")              # .project_root
        (base / "tmp/proj/.project_root").unlink()
        self.assertEqual(resolve_project(base, "proj"), "/srv/proj")              # projects.json slug
        self.assertEqual(resolve_project(base, "other", GEMINI_HASH), "/srv/proj")
        self.assertEqual(resolve_project(base, "other", "f" * 64), "f" * 64)       # unresolved hash

    def test_noise_not_wanted(self):
        p = GeminiCliParser()
        for rel in (".gemini/oauth_creds.json", ".gemini/settings.json", ".gemini/projects.json",
                    ".gemini/tmp/proj/.project_root", ".gemini/tmp/proj/shell_history",
                    ".gemini/antigravity-cli/history.jsonl"):
            art = next(a for a in self.col.artifacts if a.rel == rel)
            self.assertFalse(p.wants(art), rel)

    def test_truncated_last_line_is_reported_not_fatal(self):
        write_bad_line(self.home / self.REL)
        rows = self.rows_for(GeminiCliParser(), self.REL)
        self.assertEqual(len(rows), 16)
        self.assertIn("1 unparseable line", rows[-1].text)
        self.assertEqual(rows[-1].source_line, 16)
        (self.home / self.LEGACY).write_text('{"sessionId": "x", "messages": [', encoding="utf-8")
        rows = self.rows_for(GeminiCliParser(), self.LEGACY)
        self.assertEqual(len(rows), 1)
        self.assertIn("unparseable", rows[0].text)


class CrushTests(ParserBase):
    REL = ".crush/crush.db"

    def test_rows(self):
        rows = self.rows_for(CrushParser(), self.REL)
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "tool_use", "tool_result", "assistant", "system"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.session_id), ("h1", "alice", "crush", CRUSH_SESSION))
            self.assertEqual((r.project_path, r.git_branch), ("/alice", ""))   # the directory holding .crush
            self.assertTrue(r.timestamp_utc.endswith("Z"), r)
        start, user, use, result, asst, finish = rows
        self.assertEqual(start.text, "session start | Fix bug | 3 messages | tokens in=10 out=5 | cost=0.01")
        self.assertEqual((user.text, user.model, user.timestamp_utc),
                         ("list files", "anthropic/claude-sonnet-4", "2025-10-09T08:53:21.000Z"))
        self.assertEqual((use.tool_name, use.tool_use_id, use.text), ("bash", "call_x1", '{"command":"ls"}'))
        self.assertEqual(use.timestamp_utc, "2025-10-09T08:53:23.000Z")          # finished_at, not created_at
        self.assertEqual((result.tool_name, result.tool_use_id, result.text), ("bash", "call_x1", "a.txt"))
        self.assertEqual(asst.text, "There is one file, a.txt.")
        self.assertEqual((finish.text, finish.timestamp_utc), ("finish: max_tokens", "2025-10-09T08:53:25.000Z"))

    def test_rows_live_only_in_the_wal(self):
        art = next(a for a in self.col.artifacts if a.rel == self.REL)
        import sqlite3
        con = sqlite3.connect("file:%s?immutable=1" % art.disk_path.as_posix(), uri=True)
        try:
            self.assertEqual(con.execute("select count(*) from messages").fetchone()[0], 0)
        finally:
            con.close()
        self.assertTrue(Path(str(art.disk_path) + "-wal").is_file())

    def test_thinking_opt_in(self):
        rows = self.rows_for(CrushParser(), self.REL, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["one file only"])

    def test_projects_registry(self):
        rows = self.rows_for(CrushParser(), ".local/share/crush/projects.json")
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].turn_type, rows[0].project_path, rows[0].timestamp_utc),
                         ("system", "/srv/proj", "2026-10-01T12:00:00.000Z"))
        self.assertIn("data_dir=/srv/proj/.crush", rows[0].text)

    def test_project_path_from_original(self):
        self.assertEqual(project_of("/srv/proj/.crush/crush.db"), "/srv/proj")
        self.assertEqual(project_of("C:\\Users\\a\\repo\\.crush\\crush.db"), "C:\\Users\\a\\repo")
        self.assertEqual(project_of(".crush/crush.db"), "")

    def test_config_and_sidecars_not_wanted(self):
        p = CrushParser()
        for a in self.col.artifacts:
            if a.agent == "crush" and a.rel.endswith(("crush.json", "-wal", "-shm")):
                self.assertFalse(p.wants(a), a.rel)

    def test_bad_parts_is_reported_not_fatal(self):
        import sqlite3
        db = self.home / self.REL
        con = sqlite3.connect(str(db))
        con.execute("INSERT INTO messages(id,session_id,role,parts,model,provider,created_at,updated_at) "
                    "VALUES ('m5','6f1c0001','assistant','[{\"type\":\"text\",\"data\":{\"text\":\"cut','m','p',1760000006,1760000006)")
        con.commit()
        con.close()
        rows = self.rows_for(CrushParser(), self.REL)
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[-1].turn_type, "system")
        self.assertIn("m5 parts did not parse", rows[-1].text)
        self.assertEqual(rows[1].text, "list files")

    def test_not_sqlite_is_reported(self):
        (self.home / self.REL).write_bytes(b"not a database")
        rows = self.rows_for(CrushParser(), self.REL)
        self.assertEqual([(r.turn_type, r.text) for r in rows], [("system", "parser: not a SQLite database")])


class GooseTests(ParserBase):
    REL = ".local/share/goose/sessions/sessions.db"

    def test_rows(self):
        rows = self.rows_for(GooseParser(), self.REL)
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "tool_use", "tool_result", "assistant"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.session_id), ("h1", "alice", "goose", GOOSE_SESSION))
            self.assertEqual((r.project_path, r.git_branch), ("/srv/proj", ""))
            self.assertEqual(r.model, "anthropic/claude-sonnet-4-5")
            self.assertTrue(r.timestamp_utc.endswith("Z"), r)
        start, user, use, result, asst = rows
        self.assertEqual((start.text, start.timestamp_utc), ("session start | Fix flaky test | type=user", "2026-03-01T09:00:00.000Z"))
        self.assertEqual((user.text, user.timestamp_utc), ("run the tests", "2026-03-01T09:00:00.000Z"))
        self.assertEqual((use.tool_name, use.tool_use_id, use.text), ("developer__shell", "call_1", '{"command":"pytest -q"}'))
        self.assertEqual((result.tool_name, result.tool_use_id, result.text), ("developer__shell", "call_1", "3 passed"))
        self.assertEqual((asst.text, asst.timestamp_utc), ("All 3 tests pass.", "2026-03-01T09:00:05.000Z"))
        self.assertEqual([r.source_line for r in rows], [1, 1, 2, 3, 4])

    def test_thinking_opt_in(self):
        rows = self.rows_for(GooseParser(), self.REL, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["all green"])

    def test_legacy_request_log_and_history(self):
        rows = self.rows_for(GooseParser(), GOOSE_LEGACY_REL)
        self.assertEqual([(r.turn_type, r.text) for r in rows],
                         [("system", "session start (legacy) | old chat | 1 messages"), ("user", "hello")])
        self.assertEqual({(r.session_id, r.project_path) for r in rows}, {("20260301_090000", "/srv/old")})
        rows = self.rows_for(GooseParser(), ".local/state/goose/logs/llm_request.0.jsonl")
        self.assertEqual([(r.turn_type, r.model, r.text) for r in rows],
                         [("system", "gpt-4.1", "llm request | 1 messages | last user: hello"), ("assistant", "gpt-4.1", "hi")])
        self.assertEqual({r.timestamp_utc for r in rows}, {"2026-03-01T09:00:01.000Z"})
        rows = self.rows_for(GooseParser(), ".local/state/goose/history.txt")
        self.assertEqual([(r.turn_type, r.text) for r in rows],
                         [("user", "run the tests"), ("user", "line one line two \\ done")])
        self.assertEqual(unescape_history("a\\nb\\\\c"), "a\nb\\c")

    def test_millisecond_timestamps(self):
        from agent_analyzer.parsers.goose import epoch
        self.assertEqual(epoch(1772355600000), "2026-03-01T09:00:00.000Z")
        self.assertEqual(epoch(17723556000), to_utc(17723556))   # Goose divides above 1e10, to_utc only above 1e11

    def test_config_secrets_and_sidecars_not_wanted(self):
        p = GooseParser()
        for a in self.col.artifacts:
            if a.agent == "goose" and a.rel.endswith((".yaml", "-wal", "-shm")):
                self.assertFalse(p.wants(a), a.rel)

    def test_truncated_line_is_reported_not_fatal(self):
        write_bad_line(self.home / GOOSE_LEGACY_REL)
        rows = self.rows_for(GooseParser(), GOOSE_LEGACY_REL)
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "system"])
        self.assertEqual(rows[-1].text, "parser: 1 unparseable line(s), first at line 3")
        self.assertEqual(rows[-1].session_id, "20260301_090000")

    def test_bad_content_json_is_reported_not_fatal(self):
        import sqlite3
        con = sqlite3.connect(str(self.home / self.REL))
        con.execute("INSERT INTO messages(session_id,role,content_json,created_timestamp) "
                    "VALUES ('20260301_1','assistant','[{\"type\":\"text\",\"te',1772355606)")
        con.commit()
        con.close()
        rows = self.rows_for(GooseParser(), self.REL)
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "tool_use", "tool_result", "assistant", "system"])
        self.assertIn("content_json did not parse", rows[-1].text)


from agent_analyzer.parsers.continue_dev import ContinueParser, load_session
from agent_analyzer.parsers.aider import AiderParser
from fixtures import CONTINUE_SESSION, build_aider


class ContinueTests(ParserBase):
    REL = ".continue/sessions/%s.json" % CONTINUE_SESSION

    def test_rows(self):
        rows = self.rows_for(ContinueParser(), self.REL)
        self.assertEqual([r.turn_type for r in rows],
                         ["system", "user", "tool_use", "tool_result", "assistant", "tool_use", "tool_result"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.session_id), ("h1", "alice", "continue", CONTINUE_SESSION))
            self.assertEqual((r.project_path, r.git_branch), ("/srv/proj", ""))
            # no per-message time: every row inherits sessions.json dateCreated
            self.assertEqual(r.timestamp_utc, "2026-10-02T10:00:00.000Z")
        start, user, use1, res1, asst, use2, res2 = rows
        self.assertIn("session start: Fix bug mode=agent items=5", start.text)
        self.assertEqual(user.text, "rename foo [image]")
        self.assertEqual((use1.tool_name, use1.tool_use_id, use1.text, use1.model),
                         ("edit_existing_file", "call_1", '{"filepath":"a.py"}', "GPT-4o"))
        self.assertEqual((res1.tool_name, res1.tool_use_id, res1.text), ("edit_existing_file", "call_1", "ok"))
        self.assertEqual(asst.text, "Renamed. Cleaning the build too.")
        # a call with no tool message keeps its outcome in toolCallStates
        self.assertEqual((res2.tool_use_id, res2.text), ("call_2", "[canceled]"))
        self.assertEqual([r.source_line for r in rows], [0, 1, 3, 4, 5, 5, 5])

    def test_thinking_opt_in(self):
        rows = self.rows_for(ContinueParser(), self.REL, include_thinking=True)
        thinking = [r for r in rows if r.turn_type == "thinking"]
        self.assertEqual([r.text for r in thinking], ["consider the callers", "find foo first"])
        self.assertEqual(thinking[1].timestamp_utc, "2026-10-02T10:00:01.000Z")   # reasoning.startAt

    def test_dev_data(self):
        rows = self.rows_for(ContinueParser(), ".continue/dev_data/0.2.0/chatInteraction.jsonl")
        self.assertEqual([(r.turn_type, r.text) for r in rows], [("user", "rename foo"), ("assistant", "done")])
        self.assertTrue(all(r.timestamp_utc == "2026-10-02T10:00:05.000Z" for r in rows))
        self.assertEqual((rows[1].session_id, rows[1].project_path, rows[1].model), (CONTINUE_SESSION, "/srv/proj", "GPT-4o"))
        rows = self.rows_for(ContinueParser(), ".continue/dev_data/0.2.0/toolUsage.jsonl")
        self.assertEqual([(r.turn_type, r.tool_name, r.tool_use_id) for r in rows],
                         [("tool_use", "edit_existing_file", "call_1"), ("tool_result", "edit_existing_file", "call_1")])
        self.assertEqual(rows[1].text, "accepted=true succeeded=true ok")

    def test_index_and_config_not_wanted(self):
        p = ContinueParser()
        for rel in (".continue/sessions/sessions.json", ".continue/config.yaml"):
            art = next(a for a in self.col.artifacts if a.rel == rel)
            self.assertFalse(p.wants(art), rel)

    def test_truncated_session_keeps_earlier_turns(self):
        path = self.home / self.REL
        raw = path.read_text(encoding="utf-8")
        path.write_text(raw[: raw.index('"toolCallId": "call_2"')], encoding="utf-8")
        rows = self.rows_for(ContinueParser(), self.REL)
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "tool_use", "tool_result", "system"])
        self.assertIn("recovered 4 history item(s)", rows[-1].text)
        self.assertEqual(rows[1].session_id, CONTINUE_SESSION)

    def test_truncated_dev_data_line(self):
        rel = ".continue/dev_data/0.2.0/chatInteraction.jsonl"
        write_bad_line(self.home / rel)
        rows = self.rows_for(ContinueParser(), rel)
        self.assertEqual([r.turn_type for r in rows], ["user", "assistant", "system"])
        self.assertIn("1 unparseable line", rows[-1].text)
        self.assertEqual(rows[-1].source_line, 2)

    def test_load_session_trailing_data(self):
        obj, problem = load_session('{"sessionId": "x", "history": []}\n{"junk"')
        self.assertEqual(obj["sessionId"], "x")
        self.assertIn("trailing data", problem)


class AiderTests(ParserBase):
    CHAT = ".aider.chat.history.md"
    S1 = "/alice/.aider.chat.history.md#2026-10-02 12:00:00"
    S2 = "/alice/.aider.chat.history.md#2026-10-02 13:00:00"

    def test_rows(self):
        rows = self.rows_for(AiderParser(), self.CHAT)
        self.assertEqual([r.turn_type for r in rows],
                         ["system", "user", "assistant", "tool_result", "system", "user", "tool_result", "user"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.project_path), ("h1", "alice", "aider", "/alice"))
            self.assertEqual((r.model, r.git_branch, r.tool_use_id), ("", "", ""))
        start, user, asst, tool, start2, add, added, blank = rows
        self.assertEqual([r.session_id for r in rows], [self.S1] * 4 + [self.S2] * 4)
        self.assertEqual(start.timestamp_utc, "2026-10-02T12:00:00.000Z")
        # the prompt takes its time from the matching input-history entry, and later rows inherit it
        self.assertEqual((user.text, user.timestamp_utc), ("rename foo to bar", "2026-10-02T12:00:05.123Z"))
        self.assertEqual(asst.timestamp_utc, "2026-10-02T12:00:05.123Z")
        self.assertTrue(asst.text.startswith("Here is the change: a.py <<<<<<< SEARCH"))
        self.assertTrue(asst.text.endswith(">>>>>>> REPLACE"))
        self.assertEqual(tool.text, "Applied edit to a.py Commit abc1234 refactor: rename foo to bar")
        self.assertEqual((add.text, add.timestamp_utc), ("/add b.py", "2026-10-02T13:00:02.000Z"))
        self.assertEqual(added.text, "Added b.py to the chat")
        self.assertEqual(blank.text, "<blank>")
        self.assertEqual([r.source_line for r in rows], [2, 5, 7, 16, 19, 22, 23, 25])

    def test_thinking_opt_in(self):
        # Aider records no reasoning; the flag must not change the rows.
        self.assertEqual(len(self.rows_for(AiderParser(), self.CHAT, include_thinking=True)),
                         len(self.rows_for(AiderParser(), self.CHAT)))

    def test_input_and_llm_history(self):
        rows = self.rows_for(AiderParser(), ".aider.input.history")
        self.assertEqual([(r.turn_type, r.text, r.timestamp_utc, r.session_id) for r in rows],
                         [("user", "rename foo to bar", "2026-10-02T12:00:05.123Z", self.S1),
                          ("user", "/add b.py", "2026-10-02T13:00:02.000Z", self.S2)])
        rows = self.rows_for(AiderParser(), ".aider.llm.history")
        self.assertEqual([r.turn_type for r in rows], ["system", "assistant"])
        self.assertEqual(rows[0].text, "TO LLM: 2 message(s) (SYSTEM 1, USER 1); last user message: rename foo to bar")
        self.assertEqual((rows[1].text, rows[1].timestamp_utc), ("Here is the change: a.py", "2026-10-02T12:00:09.000Z"))
        self.assertTrue(all(r.session_id == self.S1 for r in rows))

    def test_config_not_wanted(self):
        art = next(a for a in self.col.artifacts if a.rel == ".aider.conf.yml")
        self.assertFalse(AiderParser().wants(art))

    def test_truncated_line(self):
        write_bad_line(self.home / ".aider.input.history")
        rows = self.rows_for(AiderParser(), ".aider.input.history")
        self.assertEqual([r.turn_type for r in rows], ["user", "user", "system"])
        self.assertIn("1 unparseable line", rows[-1].text)
        self.assertEqual(rows[-1].source_line, 7)

    def test_project_artifacts_from_manifest(self):
        """The collector attributes repository files to agent `project` with
        the project as the home; the rows still say aider."""
        import json as _json
        root = self.tmp / "collected"
        build_aider(root / "fs/srv/proj")
        (root / "collection.json").write_text(_json.dumps({"hostname": "h2"}), encoding="utf-8")
        with open(root / "manifest.jsonl", "w", encoding="utf-8") as fh:
            for name in (".aider.chat.history.md", ".aider.input.history", ".aider.llm.history", ".aider.conf.yml"):
                fh.write(_json.dumps({"user": "alice", "home": "/srv/proj", "agent": "project",
                                      "path": "/srv/proj/" + name, "archive_path": "fs/srv/proj/" + name,
                                      "type": "file", "status": "collected", "secret": name.endswith(".yml")}) + "\n")
        col = open_input(root, self.cat)
        self.assertEqual(col.kind, "collected")
        self.assertEqual({a.rel for a in col.artifacts if a.agent == "project"},
                         {".aider.chat.history.md", ".aider.input.history", ".aider.llm.history", ".aider.conf.yml"})
        rows, _, problems = cli.collect_rows(col, Options(), [])
        self.assertEqual(problems, [])
        self.assertEqual(len(rows), 8 + 2 + 2)
        self.assertEqual({(r.host, r.user, r.agent, r.project_path) for r in rows}, {("h2", "alice", "aider", "/srv/proj")})
        self.assertEqual({r.session_id for r in rows},
                         {"/srv/proj/.aider.chat.history.md#2026-10-02 12:00:00",
                          "/srv/proj/.aider.chat.history.md#2026-10-02 13:00:00"})
        self.assertFalse(AiderParser().wants(next(a for a in col.artifacts if a.rel == ".aider.conf.yml")))


import importlib.util  # noqa: E402
import json  # noqa: E402
import sqlite3  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from unittest import mock  # noqa: E402

from agent_analyzer.parsers import zed as zed_mod  # noqa: E402
from agent_analyzer.parsers.vscode import VsCodeParser, apply_mutation  # noqa: E402
from agent_analyzer.parsers.zed import ZedParser  # noqa: E402

from fixtures import (VSCODE_LEGACY_SESSION, VSCODE_SESSION, VSCODE_WS, ZED_EXTERNAL,  # noqa: E402
                      ZED_THREAD)

HAVE_ZSTD = importlib.util.find_spec("zstandard") is not None


@unittest.skipUnless(HAVE_ZSTD, "zstandard is not installed")
class ZedTests(ParserBase):
    REL = ".local/share/zed/threads/threads.db"
    SIDEBAR = ".local/share/zed/db/0-stable/db.sqlite"

    def _insert(self, thread_id, data_type, data, updated="2026-10-03T12:00:00+00:00"):
        con = sqlite3.connect(str(self.home / self.REL))
        con.execute("INSERT INTO threads(id,summary,updated_at,data_type,data,folder_paths) VALUES (?,?,?,?,?,?)",
                    (thread_id, "extra", updated, data_type, data, "/srv/other"))
        con.commit()
        con.close()

    def test_rows(self):
        rows = self.rows_for(ZedParser(), self.REL)
        self.assertEqual([r.turn_type for r in rows],
                         ["system", "user", "tool_use", "tool_result", "assistant", "system", "system"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.session_id), ("h1", "alice", "zed", ZED_THREAD))
            self.assertEqual((r.project_path, r.git_branch, r.model), ("/srv/proj", "main", "anthropic/claude-sonnet-4-5"))
            self.assertEqual(r.source_line, 1)
        start, user, use, result, asst, resume, compaction = rows
        self.assertEqual(start.timestamp_utc, "2026-10-03T09:00:00.000Z")       # project snapshot time
        self.assertEqual(start.text, "thread start: Fix flaky test version=0.3.0")
        self.assertEqual(user.timestamp_utc, "2026-10-03T09:01:05.000Z")        # thread updated_at, approximate
        self.assertEqual(user.text, "run the tests [mention] file:///srv/proj/README.md")
        self.assertEqual((use.tool_name, use.tool_use_id, use.text), ("terminal", "toolu_01", '{"command":"pytest -q"}'))
        self.assertEqual((result.tool_name, result.tool_use_id, result.text), ("terminal", "toolu_01", "3 passed"))
        self.assertEqual(asst.text, "All 3 tests pass.")
        self.assertEqual((resume.text, compaction.text), ("resume", "compaction: ran the tests"))

    def test_thinking_opt_in(self):
        rows = self.rows_for(ZedParser(), self.REL, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["use pytest"])

    def test_sidebar_external_threads(self):
        rows = self.rows_for(ZedParser(), self.SIDEBAR)
        self.assertEqual(len(rows), 1)                                          # the native thread is skipped
        r = rows[0]
        self.assertEqual((r.turn_type, r.session_id, r.project_path), ("system", ZED_EXTERNAL, "/srv/proj"))
        self.assertEqual(r.timestamp_utc, "2026-10-03T10:00:00.000Z")
        self.assertIn("agent=claude-code", r.text)

    def test_settings_not_wanted(self):
        art = next(a for a in self.col.artifacts if a.rel == ".config/zed/settings.json")
        self.assertFalse(ZedParser().wants(art))
        for rel in ("AppData/Local/Zed/threads/threads.db", "Library/Application Support/Zed/db/0-preview/db.sqlite",
                    ".var/app/dev.zed.Zed/data/zed/threads/threads.db"):
            self.assertTrue(ZedParser().wants(SimpleNamespace(rel=rel)), rel)
        for rel in (self.REL + "-journal", self.SIDEBAR + "-wal"):
            self.assertFalse(ZedParser().wants(SimpleNamespace(rel=rel)), rel)

    def test_corrupt_blob_is_reported_not_fatal(self):
        import zstandard
        blob = zstandard.ZstdCompressor().compress(b'{"version":"0.3.0","messages":[]}' * 50)
        self._insert("bad-thread", "zstd", blob[: len(blob) // 2])
        rows = self.rows_for(ZedParser(), self.REL)
        self.assertEqual(len([r for r in rows if r.session_id == ZED_THREAD]), 7)
        bad = [r for r in rows if r.session_id == "bad-thread"]
        self.assertEqual(len(bad), 1)
        self.assertEqual((bad[0].turn_type, bad[0].project_path, bad[0].source_line), ("system", "/srv/other", 2))
        self.assertIn("could not be decoded", bad[0].text)

    def test_missing_zstandard_is_one_row_per_thread(self):
        with mock.patch.object(zed_mod, "_zstd_module", return_value=None):
            rows = self.rows_for(ZedParser(), self.REL)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].turn_type, rows[0].session_id), ("system", ZED_THREAD))
        self.assertIn("zstandard package not installed", rows[0].text)

    def test_json_and_legacy_versions(self):
        legacy = {"version": "0.2.0", "summary": "old", "updated_at": "2026-01-01T00:00:00Z", "messages": [
            {"id": 0, "role": "user", "segments": [{"type": "text", "text": "hello"}], "tool_uses": [], "tool_results": []},
            {"id": 1, "role": "assistant", "segments": [{"type": "thinking", "text": "hmm"}, {"type": "text", "text": "hi"}],
             "tool_uses": [{"id": "t1", "name": "grep", "input": {"regex": "x"}}],
             "tool_results": [{"tool_use_id": "t1", "is_error": True, "content": "no match"}]}]}
        self._insert("legacy-thread", "json", json.dumps(legacy).encode("utf-8"))
        rows = [r for r in self.rows_for(ZedParser(), self.REL) if r.session_id == "legacy-thread"]
        self.assertEqual([(r.turn_type, r.text) for r in rows],
                         [("system", "thread start: extra version=0.2.0"), ("user", "hello"), ("assistant", "hi"),
                          ("tool_use", '{"regex":"x"}'), ("tool_result", "[error] no match")])
        self.assertEqual(rows[1].timestamp_utc, "2026-10-03T12:00:00.000Z")


class VsCodeTests(ParserBase):
    REL = VSCODE_WS + "/chatSessions/%s.jsonl" % VSCODE_SESSION
    LEGACY = ".vscode-server/data/User/globalStorage/emptyWindowChatSessions/%s.json" % VSCODE_LEGACY_SESSION

    def test_rows(self):
        rows = self.rows_for(VsCodeParser(), self.REL)
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "tool_use", "tool_result", "assistant", "user", "assistant"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.session_id), ("h1", "alice", "vscode", VSCODE_SESSION))
            self.assertEqual((r.project_path, r.git_branch), ("/srv/proj", ""))
            self.assertTrue(r.timestamp_utc.endswith("Z"), r)
        start, user, use, result, asst, user2, asst2 = rows
        self.assertEqual(start.text, "session start: responder=GitHub Copilot location=panel title=Run tests")
        self.assertEqual(start.timestamp_utc, "2026-10-03T11:00:00.000Z")
        self.assertEqual((user.text, user.model, user.timestamp_utc),
                         ("run tests [attached: test_a.py]", "copilot/gpt-4.1", "2026-10-03T11:00:01.000Z"))
        self.assertEqual((use.tool_name, use.tool_use_id, use.text), ("run_in_terminal", "call_a", "pytest"))
        self.assertEqual((result.tool_use_id, result.text, result.timestamp_utc), ("call_a", "3 passed", "2026-10-03T11:00:02.000Z"))
        self.assertEqual(asst.text, "All tests pass in test_a.py.")             # markdown run with an inline reference
        self.assertEqual((user2.text, user2.source_line), ("thanks", 2))       # pushed by the second log line
        self.assertEqual((asst2.text, asst2.timestamp_utc), ("You're welcome.", "2026-10-03T11:00:11.000Z"))
        self.assertEqual([r.source_line for r in rows], [1, 1, 1, 1, 1, 2, 2])

    def test_thinking_opt_in(self):
        rows = self.rows_for(VsCodeParser(), self.REL, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["Need pytest"])

    def test_legacy_json_session(self):
        rows = self.rows_for(VsCodeParser(), self.LEGACY)
        self.assertEqual([(r.turn_type, r.text) for r in rows],
                         [("system", "session start: responder=GitHub Copilot location=panel"),
                          ("user", "where is the config?"), ("assistant", "It is in config.toml."),
                          ("system", "error: Rate limited")])
        self.assertTrue(all(r.session_id == VSCODE_LEGACY_SESSION and r.project_path == "/srv/proj" for r in rows))
        self.assertEqual(rows[1].model, "copilot/gpt-4o")

    def test_not_wanted(self):
        for rel in (VSCODE_WS + "/workspace.json", ".config/Code/User/settings.json"):
            art = next(a for a in self.col.artifacts if a.rel == rel)
            self.assertFalse(VsCodeParser().wants(art), rel)
        for rel in ("Library/Application Support/Code - Insiders/User/workspaceStorage/x/chatSessions/s.json",
                    "AppData/Roaming/VSCodium/User/globalStorage/transferredChatSessions/s.json",
                    ".config/Positron/User/globalStorage/emptyWindowChatSessions/s.jsonl",
                    ".config/Trae CN/User/workspaceStorage/x/chatSessions/s.jsonl",
                    ".vscodium-server-insiders/data/User/workspaceStorage/x/chatSessions/s.jsonl",
                    ".positron-server/data/User/globalStorage/emptyWindowChatSessions/s.json"):
            self.assertTrue(VsCodeParser().wants(SimpleNamespace(rel=rel)), rel)
        for rel in (".config/Cursor/User/workspaceStorage/x/chatSessions/s.jsonl",
                    ".config/Code/User/globalStorage/transferredChatSessions/s.jsonl"):
            self.assertFalse(VsCodeParser().wants(SimpleNamespace(rel=rel)), rel)

    def test_truncated_line_is_reported_not_fatal(self):
        write_bad_line(self.home / self.REL)
        rows = self.rows_for(VsCodeParser(), self.REL)
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[-1].turn_type, "system")
        self.assertIn("1 unparseable line", rows[-1].text)
        self.assertEqual(rows[-1].source_line, 6)

    def test_mutation_log(self):
        s = apply_mutation(None, {"kind": 0, "v": {"a": [1, 2, 3], "b": {"c": 1}}})
        s = apply_mutation(s, {"kind": 2, "k": ["a"], "v": [9], "i": 1})
        s = apply_mutation(s, {"kind": 1, "k": ["b", "c"], "v": 2})
        s = apply_mutation(s, {"kind": 3, "k": ["b"]})
        s = apply_mutation(s, {"kind": 2, "k": ["new"], "v": [1]})
        self.assertEqual(s, {"a": [1, 9], "new": [1]})
        with self.assertRaises(ValueError):
            apply_mutation(s, {"kind": 1, "k": ["missing", "x"], "v": 1})


from agent_analyzer.parsers.opencode import OpenCodeParser, tool_summary as opencode_tool_summary
from agent_analyzer.parsers.kilo_code import KiloCodeParser, iter_json_array as kilo_iter_json_array
from fixtures import (KILO_SESSION, KILO_TASK, OPENCODE_LEGACY_SESSION, OPENCODE_SESSION,
                      OPENCODE_V2_SESSION)


class OpenCodeTests(ParserBase):
    DB = ".local/share/opencode/opencode.db"
    STORAGE = ".local/share/opencode/storage/"

    def test_rows(self):
        rows = self.rows_for(OpenCodeParser(), self.DB)
        self.assertEqual([(r.session_id, r.turn_type) for r in rows], [
            (OPENCODE_SESSION, "system"), (OPENCODE_V2_SESSION, "system"),
            (OPENCODE_SESSION, "user"), (OPENCODE_SESSION, "system"), (OPENCODE_SESSION, "tool_use"),
            (OPENCODE_SESSION, "tool_result"), (OPENCODE_SESSION, "assistant"), (OPENCODE_SESSION, "system"),
            (OPENCODE_V2_SESSION, "user"), (OPENCODE_V2_SESSION, "assistant"), (OPENCODE_V2_SESSION, "tool_use"),
            (OPENCODE_V2_SESSION, "tool_result")])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.project_path, r.git_branch),
                             ("h1", "alice", "opencode", "/srv/proj", ""))
            self.assertEqual(r.source_file, "/alice/" + self.DB)
            self.assertTrue(r.timestamp_utc.endswith("Z"), r)
        start, _, user, synth, use, res, asst, finish, v2user, v2asst, v2use, v2res = rows
        self.assertIn("session start: Fix bug", start.text)
        self.assertEqual((user.text, user.timestamp_utc, user.model),
                         ("list files", "2026-10-03T09:00:01.000Z", "anthropic/claude-sonnet-4"))
        self.assertTrue(synth.text.startswith("synthetic: <system-reminder>"))
        self.assertEqual((use.tool_name, use.tool_use_id, use.text, use.timestamp_utc),
                         ("bash", "call_x1", "ls", "2026-10-03T09:00:02.500Z"))
        self.assertEqual((res.tool_name, res.tool_use_id, res.text, res.timestamp_utc),
                         ("bash", "call_x1", "a.txt", "2026-10-03T09:00:03.000Z"))
        self.assertEqual(asst.text, "There is one file, a.txt.")
        self.assertEqual(finish.text, "step-finish reason=stop cost=0.01 tokens_in=10 tokens_out=5")
        self.assertEqual(v2user.text, "run the tests")
        self.assertEqual((v2asst.text, v2asst.model), ("Running them.", "openai/gpt-5"))
        self.assertEqual((v2use.tool_use_id, v2use.text, v2res.text), ("call_v2", "pytest -q", "3 passed"))

    def test_thinking_opt_in(self):
        rows = self.rows_for(OpenCodeParser(), self.DB, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["user wants a listing"])

    def test_legacy_json_tree(self):
        p = OpenCodeParser()
        rows = self.rows_for(p, self.STORAGE + "session/proj_a1/%s.json" % OPENCODE_LEGACY_SESSION)
        self.assertEqual([(r.turn_type, r.session_id, r.project_path) for r in rows],
                         [("system", OPENCODE_LEGACY_SESSION, "/srv/proj")])
        self.assertIn("Old session", rows[0].text)
        rows = self.rows_for(p, self.STORAGE + "message/%s/msg_a.json" % OPENCODE_LEGACY_SESSION)
        self.assertEqual([(r.turn_type, r.text) for r in rows], [("user", "cat the secrets file")])
        self.assertEqual(rows[0].source_file, "/alice/" + self.STORAGE + "part/msg_a/prt_a1.json")
        self.assertEqual(rows[0].timestamp_utc, "2026-10-02T09:00:01.000Z")
        rows = self.rows_for(p, self.STORAGE + "message/%s/msg_b.json" % OPENCODE_LEGACY_SESSION)
        self.assertEqual([r.turn_type for r in rows], ["tool_use", "tool_result", "assistant", "system"])
        use, res, asst, err = rows
        self.assertEqual((use.tool_name, use.text), ("read", "/srv/proj/.env"))
        self.assertEqual(res.text, "[error] permission denied")
        self.assertEqual(err.text, "error: APIError overloaded")
        self.assertEqual(err.source_file, "/alice/" + self.STORAGE + "message/%s/msg_b.json" % OPENCODE_LEGACY_SESSION)
        self.assertTrue(all(r.session_id == OPENCODE_LEGACY_SESSION for r in rows))

    def test_old_per_project_layout(self):
        base = self.home / ".local/share/opencode/project/srv-proj/storage/session"
        (base / "info").mkdir(parents=True)
        (base / "info/ses_old.json").write_text('{"id":"ses_old","title":"Older","time":{"created":1790000000000}}')
        (base / "message/ses_old").mkdir(parents=True)
        (base / "message/ses_old/msg_o.json").write_text(
            '{"id":"msg_o","sessionID":"ses_old","role":"user","time":{"created":1790000001000},'
            '"path":{"cwd":"/srv/proj","root":"/srv/proj"}}')
        (base / "part/ses_old/msg_o").mkdir(parents=True)
        (base / "part/ses_old/msg_o/prt_o.json").write_text('{"id":"prt_o","type":"text","text":"hello"}')
        self.col = open_input(self.tmp / "home", self.cat, host="h1")
        rows = self.rows_for(OpenCodeParser(), ".local/share/opencode/project/srv-proj/storage/session/message/ses_old/msg_o.json")
        self.assertEqual([(r.turn_type, r.text, r.session_id, r.project_path) for r in rows],
                         [("user", "hello", "ses_old", "/srv/proj")])
        rows = self.rows_for(OpenCodeParser(), ".local/share/opencode/project/srv-proj/storage/session/info/ses_old.json")
        self.assertEqual([r.turn_type for r in rows], ["system"])

    def test_config_parts_and_credentials_not_wanted(self):
        p = OpenCodeParser()
        wanted = sorted(a.rel for a in self.col.artifacts if a.agent == "opencode" and p.wants(a))
        self.assertEqual(wanted, [
            self.DB,
            self.STORAGE + "message/%s/msg_a.json" % OPENCODE_LEGACY_SESSION,
            self.STORAGE + "message/%s/msg_b.json" % OPENCODE_LEGACY_SESSION,
            self.STORAGE + "session/proj_a1/%s.json" % OPENCODE_LEGACY_SESSION,
        ])

    def test_truncated_part_is_reported_not_fatal(self):
        write_bad_line(self.home / self.STORAGE / "part/msg_b/prt_b2.json")
        rows = self.rows_for(OpenCodeParser(), self.STORAGE + "message/%s/msg_b.json" % OPENCODE_LEGACY_SESSION)
        self.assertEqual([r.turn_type for r in rows], ["tool_use", "tool_result", "system", "system"])
        self.assertIn("1 part(s) of message msg_b could not be decoded", rows[-1].text)

    def test_truncated_message_file(self):
        write_bad_line(self.home / self.STORAGE / "message" / OPENCODE_LEGACY_SESSION / "msg_a.json")
        rows = self.rows_for(OpenCodeParser(), self.STORAGE + "message/%s/msg_a.json" % OPENCODE_LEGACY_SESSION)
        self.assertEqual([(r.turn_type, r.session_id) for r in rows], [("system", OPENCODE_LEGACY_SESSION)])
        self.assertIn("could not be decoded", rows[0].text)

    def test_bad_data_column_is_reported_not_fatal(self):
        import sqlite3
        con = sqlite3.connect(str(self.home / self.DB))
        con.execute("INSERT INTO part VALUES ('prt_09','msg_02',?,1791018005000,1791018005000,'{\"type\":\"te')",
                    (OPENCODE_SESSION,))
        con.execute("INSERT INTO message VALUES ('msg_09',?,1791018006000,1791018006000,'{bad')", (OPENCODE_SESSION,))
        con.commit()
        con.close()
        rows = self.rows_for(OpenCodeParser(), self.DB)
        self.assertEqual(len([r for r in rows if r.turn_type == "tool_use"]), 2)
        texts = [r.text for r in rows if r.text.startswith("parser:")]
        self.assertEqual(texts, ["parser: 1 part(s) of message msg_02 could not be decoded",
                                 "parser: 1 record(s) with undecodable data"])

    def test_tool_summary(self):
        self.assertEqual(opencode_tool_summary({"command": "ls", "description": "list"}), "ls")
        self.assertEqual(opencode_tool_summary({"filePath": "/a"}), "/a")
        self.assertEqual(opencode_tool_summary({"pattern": "foo", "path": "/src"}), "foo | /src")
        self.assertEqual(opencode_tool_summary({"z": 1, "a": 2}), '{"a":2,"z":1}')
        self.assertEqual(opencode_tool_summary(None), "")

    def test_timeline_includes_opencode_and_kilo(self):
        out = self.tmp / "out"
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(["timeline", str(self.tmp / "home"), "-o", str(out), "--agent", "opencode", "--agent", "kilo-code"])
        with open(out / "sessions.csv", encoding="utf-8", newline="") as fh:
            sessions = {r["session_id"]: r for r in csv.DictReader(fh)}
        self.assertEqual(set(sessions), {OPENCODE_SESSION, OPENCODE_V2_SESSION, OPENCODE_LEGACY_SESSION,
                                         KILO_SESSION, KILO_TASK})
        self.assertEqual(sessions[OPENCODE_SESSION]["models"], "anthropic/claude-sonnet-4")
        self.assertEqual(sessions[OPENCODE_SESSION]["tool_calls"], "1")
        self.assertEqual(sessions[KILO_SESSION]["agent"], "kilo-code")
        self.assertEqual({s["project_path"] for s in sessions.values()}, {"/srv/proj"})


class KiloCodeTests(ParserBase):
    DB = ".local/share/kilo/kilo.db"
    TASK = ".config/Code/User/globalStorage/kilocode.kilo-code/tasks/%s/api_conversation_history.json" % KILO_TASK

    def test_rows(self):
        rows = self.rows_for(KiloCodeParser(), self.DB)
        # The V2 session_message copy of the tool call is not repeated.
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "tool_use", "tool_result"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.session_id, r.project_path),
                             ("h1", "alice", "kilo-code", KILO_SESSION, "/srv/proj"))
        start, user, use, res = rows
        self.assertIn("session start: fix tests", start.text)
        self.assertEqual((user.text, user.model), ("fix the tests", "anthropic/claude-sonnet-4-5"))
        self.assertEqual((use.tool_name, use.tool_use_id, use.text), ("bash", "call_1", "pytest -q"))
        self.assertEqual((res.tool_use_id, res.text, res.timestamp_utc), ("call_1", "3 passed", "2026-10-03T10:00:03.000Z"))

    def test_legacy_task(self):
        rows = self.rows_for(KiloCodeParser(), self.TASK)
        self.assertEqual([r.turn_type for r in rows],
                         ["system", "user", "system", "assistant", "tool_use", "tool_result", "assistant"])
        for r in rows:
            self.assertEqual((r.agent, r.session_id, r.project_path, r.model), ("kilo-code", KILO_TASK, "/srv/proj", ""))
        start, user, env, asst, use, res, final = rows
        self.assertEqual(start.text, "task: fix tests mode=code status=completed")
        self.assertEqual((user.text, user.timestamp_utc, user.source_line), ("<task>fix tests</task>", "2026-10-02T10:00:01.000Z", 1))
        self.assertTrue(env.text.startswith("<environment_details>"))
        self.assertEqual(asst.text, "Running the suite.")
        self.assertEqual((use.tool_name, use.tool_use_id, use.text), ("execute_command", "toolu_01A", "pytest -q"))
        self.assertEqual((res.tool_use_id, res.text), ("toolu_01A", "3 passed"))
        self.assertEqual((final.text, final.source_line), ("All three tests pass.", 5))

    def test_thinking_opt_in(self):
        rows = self.rows_for(KiloCodeParser(), self.TASK, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["tests pass"])

    def test_history_item_preferred_over_index(self):
        task_dir = (self.home / self.TASK).parent
        (task_dir / "history_item.json").write_text('{"id":"%s","task":"from item","workspace":"/srv/other","ts":1}' % KILO_TASK)
        rows = self.rows_for(KiloCodeParser(), self.TASK)
        self.assertEqual(rows[0].text, "task: from item")
        self.assertEqual({r.project_path for r in rows}, {"/srv/other"})

    def test_credentials_and_ui_messages_not_wanted(self):
        p = KiloCodeParser()
        wanted = sorted(a.rel for a in self.col.artifacts if a.agent == "kilo-code" and p.wants(a))
        self.assertEqual(wanted, [self.TASK, self.DB])

    def test_truncated_task_file_keeps_earlier_records(self):
        path = self.home / self.TASK
        raw = path.read_bytes()
        path.write_bytes(raw[: raw.index(b'{"type": "reasoning"') + 10])
        rows = self.rows_for(KiloCodeParser(), self.TASK)
        self.assertEqual([r.turn_type for r in rows],
                         ["system", "user", "system", "assistant", "tool_use", "tool_result", "system"])
        self.assertIn("record 4", rows[-1].text)
        self.assertIn("3 earlier record(s) kept", rows[-1].text)
        self.assertEqual(rows[-1].source_line, 4)

    def test_bad_line_appended(self):
        write_bad_line(self.home / self.TASK)
        rows = self.rows_for(KiloCodeParser(), self.TASK)
        self.assertEqual(len(rows), 8)
        self.assertIn("unexpected data after the array", rows[-1].text)

    def test_iter_json_array(self):
        self.assertEqual(kilo_iter_json_array('[1, {"a": 2} ,3]'), ([1, {"a": 2}, 3], None))
        self.assertEqual(kilo_iter_json_array("[]"), ([], None))
        self.assertEqual(kilo_iter_json_array('[1, {"a"')[0], [1])
        self.assertEqual(kilo_iter_json_array("[1, 2")[1], "record 3: unexpected end of file")
        self.assertEqual(kilo_iter_json_array('{"a":1}'), ([], "not a JSON array"))


from agent_analyzer.parsers.cline import ClineParser
from agent_analyzer.parsers.cline_legacy import iter_json_array
from agent_analyzer.parsers.roo_code import RooCodeParser
from fixtures import (CLINE_CLI_TASK, CLINE_OLD_SESSION, CLINE_SESSION, CLINE_TASK, ROO_CLI_TASK, ROO_GONE_TASK,
                      ROO_TASK)

CLINE_GS = ".config/Code/User/globalStorage/saoudrizwan.claude-dev/"
ROO_GS = ".config/Code/User/globalStorage/rooveterinaryinc.roo-cline/"


class ClineTests(ParserBase):
    UI = CLINE_GS + "tasks/%s/ui_messages.json" % CLINE_TASK
    SDK = ".cline/data/sessions/%s/%s" % (CLINE_SESSION, CLINE_SESSION)

    def test_rows(self):
        rows = self.rows_for(ClineParser(), self.UI)
        self.assertEqual([r.turn_type for r in rows], ["user", "system", "tool_use", "assistant", "tool_use",
                                                       "tool_result", "system", "assistant"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.session_id), ("h1", "alice", "cline", CLINE_TASK))
            self.assertEqual((r.project_path, r.git_branch, r.model), ("/srv/proj", "", "claude-sonnet-4-5"))
            self.assertTrue(r.timestamp_utc.endswith("Z"), r)
        user, api, read, text, cmd, out, ckpt, done = rows
        self.assertEqual((user.text, user.timestamp_utc), ("fix tests | [1 image(s)]", "2026-10-03T10:00:00.000Z"))
        self.assertEqual(api.text, "api_req_started: tokensIn=1200 tokensOut=80 cacheWrites=0 cacheReads=900 cost=0.0041")
        self.assertEqual((read.tool_name, read.tool_use_id, read.text),
                         ("readFile", "1791021602000", "src/app.py | /srv/proj/src/app.py"))
        self.assertEqual((cmd.tool_name, cmd.tool_use_id, cmd.text), ("execute_command", "1791021604000", "pytest -q"))
        self.assertEqual((out.tool_use_id, out.text), ("1791021604000", "3 passed"))
        self.assertEqual(ckpt.text, "checkpoint_created: abc123")
        self.assertEqual(done.text, "All tests pass.")
        self.assertEqual([r.source_line for r in rows], [1, 2, 4, 5, 6, 7, 8, 9])   # empty ask at 10 skipped

    def test_thinking_opt_in(self):
        rows = self.rows_for(ClineParser(), self.UI, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["read the test first"])
        rows = self.rows_for(ClineParser(), self.SDK + ".messages.json", include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["run the suite"])

    def test_api_history_only_without_ui_messages(self):
        self.assertEqual(self.rows_for(ClineParser(), CLINE_GS + "tasks/%s/api_conversation_history.json" % CLINE_TASK), [])
        rows = self.rows_for(ClineParser(), ".cline/data/tasks/%s/api_conversation_history.json" % CLINE_CLI_TASK)
        self.assertEqual([r.turn_type for r in rows], ["user", "tool_use", "tool_result"])
        # No per-message timestamps: every row inherits the task id's time.
        self.assertEqual({r.timestamp_utc for r in rows}, {"2026-10-03T09:55:00.000Z"})
        self.assertEqual({r.project_path for r in rows}, {"/srv/proj"})
        use, res = rows[1], rows[2]
        self.assertEqual((use.tool_name, use.tool_use_id, use.text), ("execute_command", "toolu_01A", "pytest -q"))
        self.assertEqual((res.tool_use_id, res.text), ("toolu_01A", "3 passed"))

    def test_history_and_metadata(self):
        rows = self.rows_for(ClineParser(), CLINE_GS + "state/taskHistory.json")
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].turn_type, rows[0].session_id, rows[0].project_path),
                         ("system", CLINE_TASK, "/srv/proj"))
        self.assertTrue(rows[0].text.startswith("task: fix tests | tokensIn=1200"))
        rows = self.rows_for(ClineParser(), CLINE_GS + "tasks/%s/task_metadata.json" % CLINE_TASK)
        self.assertEqual([r.text.split(":")[0] for r in rows], ["environment", "model_usage", "file cline_read"])
        self.assertEqual(rows[2].timestamp_utc, "2026-10-03T10:00:02.000Z")
        self.assertIn("src/app.py", rows[2].text)

    def test_sdk_session(self):
        rows = self.rows_for(ClineParser(), self.SDK + ".json")
        self.assertEqual([r.text.split(":")[0] for r in rows], ["session start", "session end"])
        self.assertEqual((rows[0].session_id, rows[0].project_path, rows[0].timestamp_utc),
                         (CLINE_SESSION, "/srv/proj", "2026-10-03T10:01:40.000Z"))
        self.assertIn("title=fix tests", rows[0].text)
        rows = self.rows_for(ClineParser(), self.SDK + ".messages.json")
        self.assertEqual([r.turn_type for r in rows], ["user", "tool_use", "tool_result", "assistant"])
        user, use, res, asst = rows
        self.assertEqual({r.session_id for r in rows}, {CLINE_SESSION})
        self.assertEqual({r.project_path for r in rows}, {"/srv/proj"})
        self.assertEqual((use.tool_name, use.tool_use_id, use.text), ("bash", "call_1", "pytest -q"))
        self.assertEqual((res.tool_name, res.tool_use_id, res.text), ("bash", "call_1", "3 passed"))
        self.assertEqual(asst.timestamp_utc, res.timestamp_utc)   # no ts: previous message's time
        self.assertEqual([r.source_line for r in rows], [1, 2, 3, 4])

    def test_sessions_db_only_lists_sessions_without_manifest(self):
        rows = self.rows_for(ClineParser(), ".cline/data/db/sessions.db")
        self.assertEqual([r.session_id for r in rows], [CLINE_OLD_SESSION])
        self.assertEqual(rows[0].timestamp_utc, "2026-10-02T23:00:00.000Z")
        self.assertIn("an older deleted session", rows[0].text)

    def test_config_and_secrets_not_wanted(self):
        p = ClineParser()
        for rel in (CLINE_GS + "settings/cline_mcp_settings.json", ".cline/data/secrets.json",
                    self.SDK + ".compaction.json"):
            art = next(a for a in self.col.artifacts if a.rel == rel)
            self.assertFalse(p.wants(art), rel)

    def test_wants_any_editor_prefix(self):
        p = ClineParser()
        art = next(a for a in self.col.artifacts if a.rel == self.UI)
        for prefix in ("Library/Application Support/Cursor/User/globalStorage/",
                       "AppData/Roaming/Code - Insiders/User/globalStorage/",
                       ".vscode-server/data/User/globalStorage/"):
            art.rel = prefix + "saoudrizwan.claude-dev/tasks/1/ui_messages.json"
            self.assertTrue(p.wants(art), art.rel)
        art.rel = ".config/Code/User/globalStorage/other.ext/tasks/1/ui_messages.json"
        self.assertFalse(p.wants(art))

    def test_truncated_line_is_reported_not_fatal(self):
        write_bad_line(self.home / self.UI)
        rows = self.rows_for(ClineParser(), self.UI)
        self.assertEqual(len(rows), 9)
        self.assertEqual(rows[-1].turn_type, "system")
        self.assertIn("after the JSON array", rows[-1].text)

    def test_array_cut_mid_write_keeps_earlier_records(self):
        path = self.home / self.UI
        data = path.read_text(encoding="utf-8")
        path.write_text(data[:data.index('"say": "command_output"') - 30], encoding="utf-8")
        rows = self.rows_for(ClineParser(), self.UI)
        self.assertEqual([r.turn_type for r in rows], ["user", "system", "tool_use", "assistant", "tool_use", "system"])
        self.assertEqual(rows[-1].source_line, 7)
        self.assertIn("record 7", rows[-1].text)
        sdk = self.home / (self.SDK + ".messages.json")
        data = sdk.read_text(encoding="utf-8")
        sdk.write_text(data[:data.index('"id": "m3"') - 2], encoding="utf-8")
        rows = self.rows_for(ClineParser(), self.SDK + ".messages.json")
        self.assertEqual([r.turn_type for r in rows], ["user", "tool_use", "system"])
        self.assertEqual(rows[0].timestamp_utc, "2026-10-03T10:01:40.000Z")

    def test_sessions_summary(self):
        rows = []
        for parser in (ClineParser(), RooCodeParser()):
            for a in self.col.artifacts_for(parser.agent):
                if parser.wants(a):
                    rows.extend(parser.parse(a, Options()))
        sessions = {s.session_id: s for s in summarise(rows)}
        self.assertEqual(set(sessions), {CLINE_TASK, CLINE_CLI_TASK, CLINE_SESSION, CLINE_OLD_SESSION,
                                         ROO_TASK, ROO_CLI_TASK, ROO_GONE_TASK})
        s = sessions[CLINE_TASK]
        self.assertEqual((s.models, s.user_turns, s.assistant_turns, s.tool_calls),
                         ({"claude-sonnet-4-5": None}, 1, 2, 2))
        self.assertTrue(s.source_file.endswith("ui_messages.json"), s.source_file)
        self.assertEqual(sessions[CLINE_SESSION].first_timestamp_utc, "2026-10-03T10:01:40.000Z")
        self.assertEqual(sessions[ROO_TASK].project_path, "/srv/proj")

    def test_json_array_reader(self):
        p = self.tmp / "a.json"
        for text, items, nerr in (("[]", [], 0), ('[{"a":1}, {"b":2}]', [{"a": 1}, {"b": 2}], 0),
                                  ('[{"a":1}, {"b":', [{"a": 1}], 1), ('{"a":1}', [], 1)):
            p.write_text(text, encoding="utf-8")
            errors = []
            self.assertEqual([v for _, v in iter_json_array(p, errors)], items, text)
            self.assertEqual(len(errors), nerr, text)


class RooCodeTests(ParserBase):
    UI = ROO_GS + "tasks/%s/ui_messages.json" % ROO_TASK
    CLI_API = ".vscode-mock/global-storage/tasks/%s/api_conversation_history.json" % ROO_CLI_TASK

    def test_rows(self):
        rows = self.rows_for(RooCodeParser(), self.UI)
        self.assertEqual([r.turn_type for r in rows], ["user", "system", "tool_use", "tool_use", "tool_result",
                                                       "system", "assistant", "user", "assistant"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.session_id), ("h1", "alice", "roo-code", ROO_TASK))
            self.assertEqual((r.project_path, r.git_branch, r.model), ("/srv/proj", "", ""))
        user, api, diff, cmd, out, condense, ask, feedback, done = rows
        self.assertEqual((user.text, user.timestamp_utc), ("rename the helper", "2026-10-03T10:03:20.000Z"))
        self.assertIn("apiProtocol=anthropic", api.text)
        self.assertEqual((diff.tool_name, diff.text), ("appliedDiff", "src/util.py | -old +new"))
        self.assertEqual((out.tool_use_id, out.text), (cmd.tool_use_id, "1 passed"))
        self.assertTrue(condense.text.startswith("condense_context: prevContextTokens=9000"))
        self.assertIn("Renamed helper; tests pass.", condense.text)
        self.assertEqual(ask.text, "Commit now? | yes; no")
        self.assertEqual(feedback.text, "yes")

    def test_thinking_opt_in(self):
        rows = self.rows_for(RooCodeParser(), self.CLI_API)
        self.assertNotIn("thinking", [r.turn_type for r in rows])
        rows = self.rows_for(RooCodeParser(), self.CLI_API, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["check the runner"])

    def test_api_history_only_without_ui_messages(self):
        self.assertEqual(self.rows_for(RooCodeParser(), ROO_GS + "tasks/%s/api_conversation_history.json" % ROO_TASK), [])
        rows = self.rows_for(RooCodeParser(), self.CLI_API)
        self.assertEqual([r.turn_type for r in rows], ["user", "tool_use", "tool_result"])
        self.assertEqual([r.timestamp_utc for r in rows],                  # Roo records carry their own ts
                         ["2026-10-03T10:05:00.000Z", "2026-10-03T10:05:02.000Z", "2026-10-03T10:05:03.000Z"])
        self.assertEqual({(r.session_id, r.project_path) for r in rows}, {(ROO_CLI_TASK, "/srv/proj")})
        self.assertEqual((rows[1].tool_use_id, rows[2].tool_use_id), ("toolu_01A", "toolu_01A"))

    def test_history_item_and_index(self):
        rows = self.rows_for(RooCodeParser(), ROO_GS + "tasks/%s/history_item.json" % ROO_TASK)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].text.startswith("task: rename the helper"))
        self.assertIn("mode=code", rows[0].text)
        rows = self.rows_for(RooCodeParser(), ROO_GS + "tasks/_index.json")
        self.assertEqual([r.session_id for r in rows], [ROO_GONE_TASK])     # tasks on disk are not repeated
        rows = self.rows_for(RooCodeParser(), ROO_GS + "tasks/%s/task_metadata.json" % ROO_TASK)
        self.assertEqual([r.text.split(":")[0] for r in rows], ["file roo_read", "file roo_edit"])

    def test_secrets_not_wanted(self):
        art = next(a for a in self.col.artifacts if a.rel == ".vscode-mock/global-storage/secrets.json")
        self.assertFalse(RooCodeParser().wants(art))
        self.assertFalse(ClineParser().wants(art))

    def test_truncated_line_is_reported_not_fatal(self):
        write_bad_line(self.home / self.UI)
        rows = self.rows_for(RooCodeParser(), self.UI)
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[-1].turn_type, "system")
        self.assertIn("parser:", rows[-1].text)


from agent_analyzer.parsers.tabby import TabbyParser
from fixtures import TABBY_BACKUP_REL, TABBY_EVENTS_REL, TABBY_REL, TABBY_SECRETS


class TabbyTests(ParserBase):
    def test_rows(self):
        rows = self.rows_for(TabbyParser(), TABBY_REL)
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "assistant", "system"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.git_branch, r.model), ("h1", "alice", "tabby", "", ""))
            self.assertTrue(r.source_file.endswith(TABBY_REL), r.source_file)
        start, user, asst, select = rows
        for r in (start, user, asst):
            self.assertEqual((r.session_id, r.project_path), ("7", "https://github.com/acme/app"))
        self.assertEqual((start.timestamp_utc, start.text),
                         ("2026-10-01T10:00:00.000Z",
                          "thread start | owner alice@example.com (Alice) | relevant questions: How is the cache invalidated?"))
        self.assertEqual((user.text, user.source_line),
                         ("Where is the cache cleared? [attachments: client_code src/cache.rs:10]", 1))
        self.assertEqual((asst.timestamp_utc, asst.text),
                         ("2026-10-01T10:00:02.000Z",
                          "In `clear()` in src/cache.rs. [attachments: code https://github.com/acme/app@abc123 src/cache.rs:10]"))
        self.assertEqual((select.session_id, select.timestamp_utc, select.text),
                         ("cmpl-7f3a", "2026-10-01T10:00:01.000Z",
                          "select choice 0 | user=alice@example.com (Alice) | view=view-1 | elapsed=1377ms"))

    def test_thinking_opt_in(self):
        # Tabby stores no reasoning; the flag must not invent rows.
        self.assertEqual(len(self.rows_for(TabbyParser(), TABBY_REL, include_thinking=True)),
                         len(self.rows_for(TabbyParser(), TABBY_REL)))

    def test_backup_and_event_log(self):
        rows = self.rows_for(TabbyParser(), TABBY_BACKUP_REL)
        self.assertEqual([r.turn_type for r in rows], ["system", "system", "user", "assistant"])
        self.assertIn("backup database", rows[0].text)
        self.assertTrue(all(r.source_file.endswith(TABBY_BACKUP_REL) for r in rows))
        self.assertEqual({(r.session_id, r.project_path) for r in rows[1:]}, {("3", "https://github.com/acme/ops")})
        self.assertIn("ephemeral", rows[1].text)
        self.assertEqual(rows[3].text, "Run `select * from users`. [attachments: code https://github.com/acme/ops db.sql]")
        rows = self.rows_for(TabbyParser(), TABBY_EVENTS_REL)
        self.assertEqual([(r.turn_type, r.session_id) for r in rows],
                         [("system", "cmpl-7f3a"), ("user", "cmpl-7f3a"), ("assistant", "cmpl-7f3a"),
                          ("system", "cmpl-7f3a"), ("system", "")])
        self.assertEqual(rows[0].text, "completion | user=1 | language=python | file=app/math.py | client=tabby-agent/1.9")
        self.assertEqual((rows[1].text, rows[1].timestamp_utc, rows[1].project_path),
                         ("def add(a, b):", "2025-10-01T10:00:00.123Z", "https://github.com/acme/app"))
        self.assertEqual(rows[2].text, "return a + b")
        self.assertEqual((rows[3].text, rows[3].timestamp_utc),
                         ("select choice 0 | user=1 | view=view-1 | elapsed=1377ms", "2025-10-01T10:00:01.500Z"))
        self.assertEqual(rows[4].text, "chat_completion")

    def test_config_and_sidecars_not_wanted(self):
        p = TabbyParser()
        seen = set()
        for a in self.col.artifacts:
            if a.agent == "tabby":
                seen.add(a.rel)
                self.assertEqual(p.wants(a), a.rel in (TABBY_REL, TABBY_BACKUP_REL, TABBY_EVENTS_REL), a.rel)
        self.assertIn(".tabby/config.toml", seen)

    def test_truncated_line_is_reported_not_fatal(self):
        write_bad_line(self.home / TABBY_EVENTS_REL)
        rows = self.rows_for(TabbyParser(), TABBY_EVENTS_REL)
        self.assertEqual(len(rows), 6)
        self.assertEqual((rows[-1].turn_type, rows[-1].text), ("system", "parser: 1 unparseable line(s), first at line 4"))

    def test_bad_payload_is_reported_not_fatal(self):
        import sqlite3
        con = sqlite3.connect(str(self.home / TABBY_REL))
        con.execute("INSERT INTO user_events(user_id,kind,created_at,payload) VALUES(1,'view','2026-10-01 10:00:05','{\"view\":')")
        con.commit()
        con.close()
        rows = self.rows_for(TabbyParser(), TABBY_REL)
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "assistant", "system", "system"])
        self.assertIn("payload did not parse", rows[-1].text)

    def test_secret_columns_never_reach_output(self):
        for rel in (TABBY_REL, TABBY_BACKUP_REL):
            for r in self.rows_for(TabbyParser(), rel):
                for value in r.as_list():
                    for secret in TABBY_SECRETS:
                        self.assertNotIn(secret, str(value))
        out = self.tmp / "out"
        buf = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(buf):
            rc = cli.main(["timeline", str(self.tmp / "home"), "-o", str(out), "--host", "h1", "--agent", "tabby"])
        self.assertEqual(rc, 0, buf.getvalue())
        produced = [p for p in out.rglob("*") if p.is_file()]
        self.assertTrue(produced)
        for p in produced:
            data = p.read_bytes()
            for secret in TABBY_SECRETS:
                self.assertNotIn(secret.encode(), data, p)
        for secret in TABBY_SECRETS:
            self.assertNotIn(secret, buf.getvalue())
from agent_analyzer.parsers.openhands import OpenHandsParser
from agent_analyzer.parsers.shellgpt import ShellGptParser, load_messages
from fixtures import OPENHANDS_CLI_CONV, OPENHANDS_CONV, OPENHANDS_LEGACY, SHELLGPT_CHAT, SHELLGPT_LEGACY_CHAT


class OpenHandsTests(ParserBase):
    CANVAS = ".openhands/agent-canvas/dev_conversations/%s/events/" % OPENHANDS_CONV
    CLI = ".openhands/conversations/%s/events/" % OPENHANDS_CLI_CONV

    def event(self, base, n):
        return next(a.rel for a in self.col.artifacts
                    if a.rel.startswith(base + "event-%05d-" % n))

    def conversation(self, base, **kw):
        rows = []
        for a in sorted(self.col.artifacts, key=lambda a: a.rel):
            if a.rel.startswith(base) and OpenHandsParser().wants(a):
                rows.extend(OpenHandsParser().parse(a, Options(**kw)))
        return rows

    def test_rows(self):
        rows = self.conversation(self.CANVAS)
        self.assertEqual([r.turn_type for r in rows], ["system", "system", "user", "tool_use", "tool_result",
                                                       "tool_use", "tool_result", "assistant"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.session_id), ("h1", "alice", "openhands", OPENHANDS_CONV))
            self.assertEqual((r.project_path, r.git_branch, r.model),
                             ("/srv/proj", "", "litellm_proxy/claude-sonnet-4-5"))
            self.assertEqual(r.source_line, 1)
        header, prompt, user, ls, out, view, reject, asst = rows
        self.assertTrue(header.text.startswith("conversation start | List files"), header.text)
        self.assertIn("corrected by UTC+02:00", header.text)
        self.assertEqual(header.timestamp_utc, "2026-10-01T10:00:00.000Z")
        self.assertEqual(prompt.text, "system prompt, 2 tools: You are OpenHands agent.")
        # Naive local 12:00:01 anchored by meta.json created_at 10:00:00Z.
        self.assertEqual((user.text, user.timestamp_utc), ("list the files", "2026-10-01T10:00:01.000Z"))
        self.assertEqual((ls.tool_name, ls.tool_use_id, ls.text), ("terminal", "call_1", "ls"))
        self.assertEqual((out.tool_use_id, out.text, out.timestamp_utc),
                         ("call_1", "README.md", "2026-10-01T10:00:04.000Z"))
        self.assertEqual((view.tool_name, view.text), ("file_editor", "view /srv/proj/README.md"))
        self.assertEqual((reject.tool_use_id, reject.text), ("call_2", "[rejected by user] not that file"))
        self.assertEqual(asst.text, "The project has a README.")
        self.assertTrue(asst.source_file.endswith(".json"))

    def test_no_meta_emits_naive_time_as_utc(self):
        rows = self.conversation(self.CLI)
        self.assertEqual(rows[0].turn_type, "system")
        self.assertIn("emitted as if UTC", rows[0].text)
        self.assertEqual(rows[2].timestamp_utc, "2026-10-02T08:30:01.000Z")
        self.assertEqual({r.session_id for r in rows}, {OPENHANDS_CLI_CONV})

    def test_thinking_opt_in(self):
        self.assertNotIn("thinking", [r.turn_type for r in self.conversation(self.CANVAS)])
        rows = self.conversation(self.CANVAS, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["I will run ls.", "check the readme"])

    def test_legacy_session_reported_once(self):
        rows = [r for a in self.col.artifacts if OpenHandsParser().wants(a) and "/sessions/" in a.rel
                for r in OpenHandsParser().parse(a, Options())]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].session_id, rows[0].turn_type), (OPENHANDS_LEGACY, "system"))
        self.assertIn("3 event files, not parsed", rows[0].text)

    def test_secrets_not_wanted(self):
        for rel in (".openhands/settings.json", ".openhands/secrets.json",
                    ".openhands/agent-canvas/dev_conversations/%s/meta.json" % OPENHANDS_CONV,
                    ".openhands/agent-canvas/dev_conversations/%s/base_state.json" % OPENHANDS_CONV):
            art = next(a for a in self.col.artifacts if a.rel == rel)
            self.assertFalse(OpenHandsParser().wants(art), rel)

    def test_truncated_line_is_reported_not_fatal(self):
        rel = self.event(self.CANVAS, 6)
        write_bad_line(self.home / rel)
        rows = self.rows_for(OpenHandsParser(), rel)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].turn_type, "system")
        self.assertIn("parser:", rows[0].text)
        self.assertEqual(len(self.conversation(self.CANVAS)), 8)   # the other events still parse


class ShellGptTests(ParserBase):
    CHAT = "AppData/Local/Temp/chat_cache/" + SHELLGPT_CHAT
    LEGACY = "AppData/Local/Temp/shell_gpt/chat_cache/" + SHELLGPT_LEGACY_CHAT

    def test_rows(self):
        rows = self.rows_for(ShellGptParser(), self.CHAT)
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "tool_use", "tool_result", "assistant"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.session_id), ("h1", "alice", "shellgpt", SHELLGPT_CHAT))
            self.assertEqual((r.timestamp_utc, r.project_path, r.git_branch, r.model, r.source_line),
                             ("", "", "", "", 1))
        system, user, use, result, asst = rows
        self.assertTrue(system.text.startswith("You are ShellGPT"))
        self.assertEqual(user.text, "what is listening on port 8080")
        self.assertEqual((use.tool_name, use.tool_use_id, use.text),
                         ("execute_shell_command", "call_Q1w2e3r4", "ss -ltnp | grep 8080"))
        self.assertEqual((result.tool_name, result.tool_use_id), ("execute_shell_command", "call_Q1w2e3r4"))
        self.assertTrue(result.text.startswith("Exit code: 0, Output: LISTEN"))
        self.assertTrue(asst.text.endswith("is listening on 8080."))

    def test_legacy_function_call(self):
        rows = self.rows_for(ShellGptParser(), self.LEGACY)
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "tool_use", "tool_result", "assistant"])
        use, result = rows[2], rows[3]
        self.assertEqual((use.tool_use_id, use.text), ("function_call_2", "df -h /"))
        self.assertEqual((result.tool_use_id, result.tool_name), ("function_call_2", "execute_shell_command"))

    def test_thinking_opt_in(self):
        # ShellGPT stores no reasoning; the option changes nothing.
        self.assertEqual([r.turn_type for r in self.rows_for(ShellGptParser(), self.CHAT, include_thinking=True)],
                         [r.turn_type for r in self.rows_for(ShellGptParser(), self.CHAT)])

    def test_not_wanted(self):
        for rel in (".config/shell_gpt/.sgptrc",
                    "AppData/Local/Temp/shell_gpt/cache/0cc175b9c0f1b6a831c399e269772661"):
            art = next(a for a in self.col.artifacts if a.rel == rel)
            self.assertFalse(ShellGptParser().wants(art), rel)

    def test_loose_temp_directory_is_wanted(self):
        art = next(a for a in self.col.artifacts if a.rel == self.CHAT)
        art.rel = "tmp/chat_cache/" + SHELLGPT_CHAT
        self.assertTrue(ShellGptParser().wants(art))

    def test_truncated_line_is_reported_not_fatal(self):
        path = self.home / self.CHAT
        raw = path.read_text(encoding="utf-8")
        path.write_text(raw[: raw.index('{"role": "tool"') + 20], encoding="utf-8")
        rows = self.rows_for(ShellGptParser(), self.CHAT)
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "tool_use", "system"])
        self.assertIn("parser: truncated after 3 message(s)", rows[-1].text)
        msgs, err = load_messages("not json")
        self.assertEqual(msgs, [])
        self.assertTrue(err)
from agent_analyzer.parsers.pi import PiParser, args_summary as pi_args_summary  # noqa: E402
from agent_analyzer.parsers.little_coder import LittleCoderParser  # noqa: E402
from agent_analyzer.parsers.letta import LettaParser, decode_key  # noqa: E402
from fixtures import (LC_FILE, LC_SESSION, LETTA_AGENT, LETTA_CONV, LETTA_LOCAL_CONV, LETTA_LOCAL_DIR,  # noqa: E402
                      PI_DIR, PI_EXPERIMENTAL, PI_FILE, PI_FORK, PI_FORK_FILE, PI_SESSION, _jsonl)


class PiTests(ParserBase):
    REL = PI_DIR + PI_FILE
    FORK = PI_DIR + PI_FORK_FILE
    LC = PI_DIR + LC_FILE

    def test_rows(self):
        rows = self.rows_for(PiParser(), self.REL)
        self.assertEqual([r.turn_type for r in rows], ["system", "system", "user", "tool_use", "tool_result",
                                                       "tool_use", "tool_result", "system"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.session_id), ("h1", "alice", "pi", PI_SESSION))
            self.assertEqual((r.project_path, r.git_branch), ("/srv/proj", ""))
            self.assertTrue(r.timestamp_utc.endswith("Z"), r)
        start, mc, user, use, result, bash, bash_out, info = rows
        self.assertEqual((start.text, start.timestamp_utc), ("session start: version=3 cwd=/srv/proj",
                                                             "2026-10-01T09:00:00.000Z"))
        self.assertEqual((mc.model, mc.text), ("claude-sonnet-4-5", "model_change: anthropic/claude-sonnet-4-5"))
        self.assertEqual((user.text, user.timestamp_utc), ("fix the failing test", "2026-10-01T09:00:01.000Z"))
        self.assertEqual((use.tool_name, use.tool_use_id, use.model, use.text),
                         ("bash", "toolu_01", "claude-sonnet-4-5", "npm test"))
        self.assertEqual((result.tool_name, result.tool_use_id, result.text), ("bash", "toolu_01", "1 failing"))
        self.assertEqual((bash.tool_name, bash.tool_use_id, bash.text), ("bash", "5e6f7081", "git status"))
        self.assertEqual((bash_out.tool_use_id, bash_out.text), ("5e6f7081", "M src/a.ts"))
        self.assertEqual(info.text, "session_info: name=test fix")
        self.assertEqual([r.source_line for r in rows], [1, 2, 3, 4, 5, 6, 6, 8])   # the label on line 7 is skipped
        self.assertEqual(pi_args_summary({"edits": [{"oldText": "a", "newText": "b"}], "path": "src/a.ts"}),
                         "src/a.ts")

    def test_thinking_opt_in(self):
        rows = self.rows_for(PiParser(), self.REL, include_thinking=True)
        thinking = [r for r in rows if r.turn_type == "thinking"]
        self.assertEqual([(r.text, r.model) for r in thinking], [("run the tests first", "claude-sonnet-4-5")])

    def test_fork_drops_entries_copied_from_parent(self):
        rows = self.rows_for(PiParser(), self.FORK)
        self.assertEqual([r.turn_type for r in rows], ["system", "system", "assistant"])
        self.assertIn("parentSession=/home/alice/" + self.REL, rows[0].text)
        self.assertTrue(rows[1].text.startswith("fork: 3 entries copied from the parent session"), rows[1].text)
        self.assertEqual((rows[2].session_id, rows[2].text), (PI_FORK, "Trying another way."))

    def test_fork_kept_whole_without_parent(self):
        (self.home / self.REL).unlink()
        rows = self.rows_for(PiParser(), self.FORK)
        self.assertEqual([r.turn_type for r in rows], ["system", "system", "user", "tool_use", "assistant"])
        self.assertEqual({r.session_id for r in rows}, {PI_FORK})

    def test_little_coder_session_is_flagged(self):
        rows = self.rows_for(PiParser(), self.LC)
        self.assertEqual({r.agent for r in rows}, {"pi"})
        last = rows[-1]
        self.assertEqual((last.turn_type, last.session_id), ("system", LC_SESSION))
        self.assertTrue(last.text.startswith("session driven by little-coder"), last.text)
        for why in ("lc-skills", "llamacpp", "checkpoints"):
            self.assertIn(why, last.text)
        self.assertIn("custom_message lc-skills: ## Skill: edit Use the edit tool.", [r.text for r in rows])
        plain = self.rows_for(PiParser(), self.REL)
        self.assertFalse(any("little-coder" in r.text for r in plain))

    def test_experimental_meta(self):
        rows = self.rows_for(PiParser(), ".pi/agent/experimental/sessions/%s/meta.json" % PI_EXPERIMENTAL)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].turn_type, rows[0].session_id, rows[0].project_path, rows[0].timestamp_utc),
                         ("system", PI_EXPERIMENTAL, "/srv/proj", "2026-10-01T12:00:00.000Z"))

    def test_config_not_wanted(self):
        for rel in (".pi/agent/auth.json", ".pi/agent/settings.json"):
            art = next(a for a in self.col.artifacts if a.rel == rel)
            self.assertFalse(PiParser().wants(art), rel)

    def test_truncated_line_is_reported_not_fatal(self):
        write_bad_line(self.home / self.REL)
        rows = self.rows_for(PiParser(), self.REL)
        self.assertEqual(len(rows), 9)
        self.assertEqual(rows[-1].turn_type, "system")
        self.assertIn("parser:", rows[-1].text)
        self.assertEqual(rows[-1].source_line, 9)


class LittleCoderTests(ParserBase):
    HISTORY = ".pi/agent/little-coder-prompt-history.json"
    CK = ".little-coder/checkpoints/%s/" % LC_FILE

    def test_prompt_history(self):
        rows = self.rows_for(LittleCoderParser(), self.HISTORY)
        self.assertEqual([(r.turn_type, r.text, r.timestamp_utc, r.session_id, r.source_line) for r in rows],
                         [("user", "fix the failing test", "", "", 1), ("user", "now run lint", "", "", 2)])
        self.assertEqual({r.agent for r in rows}, {"little-coder"})

    def test_checkpoints_one_row_per_set(self):
        self.assertEqual(self.rows_for(LittleCoderParser(), self.CK + "_srv_proj_src_new.ts.absent"), [])
        rows = self.rows_for(LittleCoderParser(), self.CK + "_srv_proj_src_a.ts")
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r.turn_type, r.session_id, r.project_path, r.timestamp_utc),
                         ("system", LC_SESSION, "/srv/proj", "2026-10-01T11:00:06.000Z"))
        self.assertIn("2 pre-edit file(s)", r.text)
        self.assertIn("_srv_proj_src_new.ts (did not exist)", r.text)

    def test_thinking_opt_in(self):
        # little-coder's own files hold no reasoning; its transcripts are pi's.
        rows = self.rows_for(LittleCoderParser(), self.HISTORY, include_thinking=True)
        self.assertNotIn("thinking", [r.turn_type for r in rows])

    def test_settings_and_sessions_not_wanted(self):
        art = next(a for a in self.col.artifacts if a.rel == ".config/little-coder/settings.json")
        self.assertFalse(LittleCoderParser().wants(art))
        art = next(a for a in self.col.artifacts if a.rel == PI_DIR + LC_FILE)
        self.assertEqual(art.agent, "pi")
        self.assertFalse(LittleCoderParser().wants(art))

    def test_truncated_history_keeps_earlier_prompts(self):
        (self.home / self.HISTORY).write_text('["fix the failing test", "now run li', encoding="utf-8")
        rows = self.rows_for(LittleCoderParser(), self.HISTORY)
        self.assertEqual([r.turn_type for r in rows], ["user", "system"])
        self.assertIn("parser:", rows[-1].text)


class LettaTests(ParserBase):
    TRANSCRIPT = ".letta/transcripts/%s/%s/transcript.jsonl" % (LETTA_AGENT, LETTA_CONV)
    TWIN = ".letta/transcripts/%s/%s/transcript.jsonl" % (LETTA_AGENT, LETTA_LOCAL_CONV)
    LOCAL = ".letta/lc-local-backend/conversations/%s/messages.jsonl" % LETTA_LOCAL_DIR

    def test_local_backend_rows(self):
        rows = self.rows_for(LettaParser(), self.LOCAL)
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "tool_use", "tool_result"])
        for r in rows:
            self.assertEqual((r.agent, r.session_id, r.project_path), ("letta", LETTA_LOCAL_CONV, "/srv/proj"))
        _, user, use, result = rows
        self.assertEqual((user.text, user.timestamp_utc), ("list the repo", "2026-10-01T12:00:01.000Z"))
        self.assertEqual((use.tool_name, use.tool_use_id, use.model, use.text),
                         ("Bash", "call_1", "claude-sonnet-4-5", "ls"))
        self.assertEqual(use.source_line, 4)        # the replacement snapshot, not the pending copy on line 3
        self.assertEqual((result.tool_use_id, result.text), ("call_1", "README.md"))
        self.assertEqual(decode_key(LETTA_LOCAL_DIR), "conversation:" + LETTA_LOCAL_CONV)

    def test_thinking_opt_in(self):
        rows = self.rows_for(LettaParser(), self.LOCAL, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["use ls"])
        rows = self.rows_for(LettaParser(), self.TRANSCRIPT)
        self.assertNotIn("thinking", [r.turn_type for r in rows])
        rows = self.rows_for(LettaParser(), self.TRANSCRIPT, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["use ls"])

    def test_reflection_transcript(self):
        rows = self.rows_for(LettaParser(), self.TRANSCRIPT)
        self.assertEqual([r.turn_type for r in rows], ["user", "tool_use", "tool_result", "assistant"])
        for r in rows:
            self.assertEqual((r.session_id, r.project_path, r.model, r.timestamp_utc),
                             (LETTA_CONV, "/srv/proj", "", "2026-10-01T12:00:05.120Z"))
        self.assertEqual((rows[1].tool_name, rows[1].text), ("Bash", '{"command":"ls"}'))
        self.assertEqual((rows[2].tool_name, rows[2].tool_use_id, rows[2].text), ("Bash", "", "README.md"))

    def test_transcript_defers_to_local_backend(self):
        rows = self.rows_for(LettaParser(), self.TWIN)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].turn_type, rows[0].session_id), ("system", LETTA_LOCAL_CONV))
        self.assertIn("messages.jsonl", rows[0].text)

    def test_sessions_history(self):
        rows = self.rows_for(LettaParser(), ".letta/sessions.jsonl")
        self.assertEqual([(r.turn_type, r.session_id, r.project_path) for r in rows],
                         [("system", "s-0", "/srv/old"), ("system", "s-1", "/srv/proj"), ("system", "s-1", "/srv/proj")])
        self.assertIn("exit_reason=user_exit messages=4 tool_calls=1", rows[2].text)
        self.assertEqual(rows[1].model, "claude-sonnet-4-5")

    def test_schema_1_bare_messages(self):
        path = self.home / self.LOCAL
        _jsonl(path, [
            {"id": "letta-msg-1", "role": "user", "content": "hi", "timestamp": 1790856001000,
             "metadata": {"created_at": "2026-10-01T12:00:01.000Z", "agent_id": LETTA_AGENT}},
            {"id": "letta-msg-2", "role": "assistant", "content": [{"type": "text", "text": "hello"}],
             "model": "claude-sonnet-4-5", "timestamp": 1790856002000},
        ])
        rows = self.rows_for(LettaParser(), self.LOCAL)
        self.assertEqual([(r.turn_type, r.text, r.timestamp_utc, r.session_id) for r in rows], [
            ("user", "hi", "2026-10-01T12:00:01.000Z", LETTA_LOCAL_CONV),
            ("assistant", "hello", "2026-10-01T12:00:02.000Z", LETTA_LOCAL_CONV)])

    def test_config_not_wanted(self):
        for rel in (".letta/settings.json", ".letta/transcripts/%s/%s/state.json" % (LETTA_AGENT, LETTA_CONV),
                    ".letta/lc-local-backend/conversations/%s/manifest.json" % LETTA_LOCAL_DIR):
            art = next(a for a in self.col.artifacts if a.rel == rel)
            self.assertFalse(LettaParser().wants(art), rel)

    def test_truncated_line_is_reported_not_fatal(self):
        for rel, n in ((self.TRANSCRIPT, 4), (self.LOCAL, 4)):
            write_bad_line(self.home / rel)
            rows = self.rows_for(LettaParser(), rel)
            self.assertEqual(len(rows), n + 1, rel)
            self.assertEqual(rows[-1].turn_type, "system")
            self.assertIn("parser:", rows[-1].text)
from dataclasses import replace as dc_replace  # noqa: E402

from agent_analyzer.parsers.agent_zero import AgentZeroParser, recover_logs  # noqa: E402
from agent_analyzer.parsers.hermes import HermesParser, decode_content  # noqa: E402
from fixtures import (AGENT_ZERO_CHAT, AGENT_ZERO_LONG, AGENT_ZERO_REL, HERMES_CHILD, HERMES_DIVERTED,  # noqa: E402
                      HERMES_DIVERTED_REL, HERMES_SESSION, agent_zero_chat, agent_zero_history)


class HermesTests(ParserBase):
    REL = ".hermes/state.db"

    def test_rows(self):
        rows = self.rows_for(HermesParser(), self.REL)
        self.assertEqual([r.turn_type for r in rows],
                         ["system", "system", "user", "tool_use", "tool_result", "assistant", "user", "user", "user"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.project_path), ("h1", "alice", "hermes", "/srv/proj"))
            self.assertTrue(r.timestamp_utc.endswith("Z"), r)
        start, child, user, use, result, asst, rewound, image, sub = rows
        self.assertEqual((start.session_id, start.text, start.timestamp_utc),
                         (HERMES_SESSION, "session start | List files | source=cli", "2026-10-01T12:00:00.000Z"))
        self.assertEqual((child.session_id, child.text),
                         (HERMES_CHILD, "session start | Check disk | source=subagent | parent=%s | end=completed"
                          % HERMES_SESSION))
        self.assertEqual((user.text, user.timestamp_utc, user.git_branch, user.model),
                         ("list files", "2026-10-01T12:00:01.250Z", "main", "anthropic/claude-sonnet-4"))
        self.assertEqual((use.tool_name, use.tool_use_id, use.text), ("terminal", "call_1", "ls"))
        self.assertEqual((result.tool_name, result.tool_use_id, result.text), ("terminal", "call_1", "a.txt b.txt"))
        self.assertEqual(asst.text, "Two files: a.txt, b.txt.")
        self.assertEqual(rewound.text, "[rewound] delete them instead")
        self.assertEqual(image.text, "what is in this screenshot? [image]")
        self.assertEqual((sub.session_id, sub.git_branch, sub.model, sub.project_path),
                         (HERMES_CHILD, "", "openai/gpt-5", "/srv/proj"))   # cwd empty: git_repo_root
        self.assertEqual([r.source_line for r in rows[2:]], [1, 2, 3, 4, 5, 6, 7])

    def test_thinking_opt_in(self):
        rows = self.rows_for(HermesParser(), self.REL, include_thinking=True)
        self.assertEqual([(r.turn_type, r.text) for r in rows if r.turn_type == "thinking"],
                         [("thinking", "User wants a listing.")])
        self.assertNotIn("thinking", [r.turn_type for r in self.rows_for(HermesParser(), self.REL)])

    def test_diverted_jsonl_transcript(self):
        rows = self.rows_for(HermesParser(), HERMES_DIVERTED_REL)
        self.assertEqual([(r.turn_type, r.tool_name, r.tool_use_id, r.text) for r in rows],
                         [("user", "", "", "show the env"), ("tool_use", "read_file", "call_9", "/srv/proj/.env"),
                          ("tool_result", "read_file", "call_9", "TOKEN=x")])
        self.assertEqual({(r.session_id, r.project_path) for r in rows}, {(HERMES_DIVERTED, "")})
        self.assertEqual(rows[0].timestamp_utc, "2026-10-01T13:00:00.000Z")

    def test_paths_and_noise(self):
        p = HermesParser()
        for rel in (".hermes/profiles/work/state.db", ".hermes_alt/state.db", "AppData/Local/hermes/state.db",
                    "AppData/Local/hermes/profiles/x/sessions/abc.jsonl"):
            self.assertTrue(p.wants(SimpleNamespace(rel=rel)), rel)
        for rel in (".hermes/state-snapshots/1/state.db", ".hermes/response_store.db", ".hermes/sessions/abc.json"):
            self.assertFalse(p.wants(SimpleNamespace(rel=rel)), rel)
        for a in self.col.artifacts:
            if a.agent == "hermes" and a.rel.endswith((".yaml", "auth.json", "sessions.json", "-wal", "-shm")):
                self.assertFalse(p.wants(a), a.rel)
        self.assertEqual(decode_content('\x00json:{"text":"x"}'), {"text": "x"})

    def test_older_schema_without_active_or_reasoning(self):
        db = self.tmp / "old" / "state.db"
        db.parent.mkdir()
        con = sqlite3.connect(str(db))
        con.executescript("CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT,"
                          " tool_call_id TEXT, tool_calls TEXT, timestamp REAL);"
                          "INSERT INTO messages VALUES (1,'s1','user','hi',NULL,NULL,1790856000.0);")
        con.commit()
        con.close()
        art = dc_replace(next(a for a in self.col.artifacts if a.rel == self.REL), disk_path=db)
        rows = list(HermesParser().parse(art, Options(include_thinking=True)))
        self.assertEqual([(r.session_id, r.turn_type, r.text) for r in rows], [("s1", "user", "hi")])

    def test_truncated_line_is_reported_not_fatal(self):
        write_bad_line(self.home / HERMES_DIVERTED_REL)
        rows = self.rows_for(HermesParser(), HERMES_DIVERTED_REL)
        self.assertEqual([r.turn_type for r in rows], ["user", "tool_use", "tool_result", "system"])
        self.assertEqual(rows[-1].text, "parser: 1 unparseable line(s), first at line 4")
        self.assertEqual(rows[-1].session_id, HERMES_DIVERTED)

    def test_not_sqlite_is_reported(self):
        (self.home / self.REL).write_text("not a database", encoding="utf-8")
        rows = self.rows_for(HermesParser(), self.REL)
        self.assertEqual([(r.turn_type, r.text) for r in rows], [("system", "parser: not a SQLite database")])


class AgentZeroTests(ParserBase):
    REL = AGENT_ZERO_REL

    def test_rows(self):
        rows = self.rows_for(AgentZeroParser(), self.REL)
        self.assertEqual([r.turn_type for r in rows],
                         ["system", "user", "assistant", "tool_use", "tool_result", "tool_use", "tool_result",
                          "system", "assistant"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.session_id), ("h1", "alice", "agent-zero", AGENT_ZERO_CHAT))
            self.assertEqual((r.project_path, r.git_branch), ("/a0/usr/projects/demo", ""))
            self.assertTrue(r.timestamp_utc.endswith("Z"), r)
        start, user, asst, use, result, use2, result2, warn, resp = rows
        self.assertEqual((start.text, start.timestamp_utc),
                         ("chat start | List files | type=user | profile=agent0 | project=demo",
                          "2026-10-01T12:00:00.000Z"))
        self.assertEqual((user.text, user.timestamp_utc), ("list files", "2026-10-01T12:00:01.000Z"))
        self.assertEqual((asst.text, asst.model), ("Listing list", "openrouter/anthropic/claude-sonnet-4"))
        self.assertEqual((use.tool_name, use.tool_use_id, use.text), ("code_execution_tool", "t1", "ls"))
        self.assertEqual((result.tool_use_id, result.text), ("t1", "a.txt"))
        self.assertEqual((use2.text, result2.tool_use_id), ("cat big.log", "t2"))
        self.assertEqual(result2.text, AGENT_ZERO_LONG + " (from file)")   # messages/1.txt over the cut log
        self.assertEqual(warn.text, "warning: Rate limit | retrying in 5s")
        self.assertEqual((resp.text, resp.timestamp_utc), ("There is one file, a.txt.", "2026-10-01T12:00:05.000Z"))
        self.assertEqual([r.source_line for r in rows], [0, 0, 1, 2, 2, 3, 3, 4, 5])

    def test_thinking_opt_in(self):
        rows = self.rows_for(AgentZeroParser(), self.REL, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["the user wants a listing"])

    def test_history_used_when_file_absent_and_log_cut(self):
        (self.home / "agent-zero/usr/chats" / AGENT_ZERO_CHAT / "messages/1.txt").unlink()
        rows = self.rows_for(AgentZeroParser(), self.REL)
        self.assertEqual(rows[6].text, AGENT_ZERO_LONG)

    def test_trimmed_log_adds_history_without_timestamps(self):
        history = agent_zero_history()
        history["bulks"] = [{"_cls": "Bulk", "summary": "earlier: set up the repo", "records": []}]
        logs = [{"no": n, "id": "x%d" % n, "type": "info", "heading": "", "content": "tick %d" % n, "kvps": {},
                 "timestamp": 1790856100.0 + n, "agentno": 0} for n in range(1000)]
        (self.home / self.REL).write_text(json.dumps(agent_zero_chat(logs=logs, history=history)), encoding="utf-8")
        rows = self.rows_for(AgentZeroParser(), self.REL)
        self.assertEqual(rows[1].text, "log trimmed to its last 1000 items; earlier turns follow from the agent "
                                       "history without timestamps")
        early = rows[2:9]
        self.assertEqual([(r.turn_type, r.timestamp_utc) for r in early],
                         [("system", ""), ("user", ""), ("assistant", ""), ("tool_use", ""), ("tool_result", ""),
                          ("tool_result", ""), ("system", "2026-10-01T12:01:40.000Z")])
        self.assertEqual(early[0].text, "[summary] earlier: set up the repo")
        self.assertEqual((early[2].text, early[2].model), ("Listing list", "openrouter/anthropic/claude-sonnet-4"))
        self.assertEqual((early[3].tool_name, early[3].text), ("code_execution_tool", "ls"))
        self.assertEqual(early[6].text, "info: tick 0")
        self.assertEqual(len(rows), 2 + 6 + 1000)

    def test_paths_and_noise(self):
        p = AgentZeroParser()
        for rel in ("agent-zero/inst-1/usr/chats/Zz/chat.json", "Desktop/agent-zero/usr/chats/Zz/chat.json",
                    "agent-zero/usr/chats/Zz.json", "agent-zero/tmp/chats/Zz/chat.json"):
            self.assertTrue(p.wants(SimpleNamespace(rel=rel)), rel)
        for a in self.col.artifacts:
            if a.agent == "agent-zero" and a.rel != self.REL:
                self.assertFalse(p.wants(a), a.rel)
        self.assertTrue(any(a.rel.endswith("messages/1.txt") for a in self.col.artifacts))

    def test_truncated_file_is_reported_not_fatal(self):
        raw = json.dumps(agent_zero_chat())
        cut = raw.index('"id": "t2"')          # mid-file, inside the fourth log item
        (self.home / self.REL).write_text(raw[:cut + 20], encoding="utf-8")
        rows = self.rows_for(AgentZeroParser(), self.REL)
        self.assertEqual(rows[0].turn_type, "system")
        self.assertTrue(rows[0].text.startswith("parser: chat.json did not parse"), rows[0].text)
        self.assertEqual([r.turn_type for r in rows[1:]], ["user", "assistant", "tool_use", "tool_result"])
        self.assertEqual({r.session_id for r in rows}, {AGENT_ZERO_CHAT})
        self.assertEqual(rows[4].text, "a.txt")
        self.assertEqual(recover_logs('{"logs": [{"no": 0}, {"no": 1'), [{"no": 0}])
from agent_analyzer.parsers import codex as codex_mod  # noqa: E402
from agent_analyzer.parsers.open_interpreter import OpenInterpreterParser  # noqa: E402
from fixtures import (OI_ARCHIVED, OI_IMPORTED, OI_ROLLOUT, OI_SESSION,  # noqa: E402
                      codex_rollout_records, open_interpreter_rollout_records)


def _rollout_bytes(records) -> bytes:
    return "".join(json.dumps(r) + "\n" for r in records).encode("utf-8")


class CodexArchiveAndZstdTests(ParserBase):
    """Codex `archived_sessions/` and `.jsonl.zst` rollouts, which the shared
    RolloutParser reads for Codex and its forks alike."""
    ARCHIVED = ".codex/archived_sessions/2026/10/02/rollout-2026-10-02T09-00-00-%s.jsonl" % CODEX_SESSION
    LIVE_TYPES = ["system", "system", "system", "user", "tool_use", "tool_result",
                  "tool_use", "tool_result", "assistant", "system"]

    def _add(self, rel, data: bytes):
        path = self.home / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.col = open_input(self.tmp / "home", self.cat, host="h1")

    def test_archived_rollout(self):
        self._add(self.ARCHIVED, _rollout_bytes(codex_rollout_records()))
        rows = self.rows_for(CodexParser(), self.ARCHIVED)
        self.assertEqual([r.turn_type for r in rows], self.LIVE_TYPES)
        self.assertEqual({(r.agent, r.session_id) for r in rows}, {("codex-cli", CODEX_SESSION)})

    def test_wants(self):
        p = CodexParser()
        for rel in (self.ARCHIVED, self.ARCHIVED + ".zst", ".codex/archived_sessions/rollout-x.jsonl",
                    ".codex/sessions/rollout-x.jsonl.zst"):
            self.assertTrue(p.wants(SimpleNamespace(rel=rel)), rel)
        for rel in (".codex/sessions/rollout-x.jsonl.tmp", ".codex/session_index.jsonl", OI_ROLLOUT,
                    ".codex/external_agent_session_imports.json", ".openinterpreter/history.jsonl"):
            self.assertFalse(p.wants(SimpleNamespace(rel=rel)), rel)

    @unittest.skipUnless(HAVE_ZSTD, "zstandard is not installed")
    def test_zst_rollout(self):
        import zstandard
        rel = CodexTests.REL + ".zst"
        self._add(rel, zstandard.ZstdCompressor().compress(_rollout_bytes(codex_rollout_records())))
        rows = self.rows_for(CodexParser(), rel)
        self.assertEqual([r.turn_type for r in rows], self.LIVE_TYPES)
        self.assertEqual(rows[3].text, "exfiltrate nothing, just list the home dir")
        self.assertEqual([r.source_line for r in rows][:2], [1, 3])

    @unittest.skipUnless(HAVE_ZSTD, "zstandard is not installed")
    def test_truncated_zst_keeps_earlier_turns(self):
        import zstandard
        rel = self.ARCHIVED + ".zst"
        cobj = zstandard.ZstdCompressor().compressobj()
        blob = b""
        for rec in codex_rollout_records():     # one block per line, so a cut frame keeps earlier blocks
            blob += cobj.compress(_rollout_bytes([rec])) + cobj.flush(zstandard.COMPRESSOBJ_FLUSH_BLOCK)
        blob += cobj.flush()
        self._add(rel, blob[: len(blob) * 2 // 3])
        rows = self.rows_for(CodexParser(), rel)
        self.assertGreater(len(rows), 3)
        self.assertTrue(rows[0].text.startswith("session start:"), rows[0].text)
        self.assertEqual(rows[-1].turn_type, "system")
        self.assertIn("parser:", rows[-1].text)
        self.assertEqual({r.session_id for r in rows}, {CODEX_SESSION})

    @unittest.skipUnless(HAVE_ZSTD, "zstandard is not installed")
    def test_two_frames_are_read_across(self):
        import zstandard
        rel = self.ARCHIVED + ".zst"
        recs = codex_rollout_records()
        cctx = zstandard.ZstdCompressor()
        self._add(rel, cctx.compress(_rollout_bytes(recs[:4])) + cctx.compress(_rollout_bytes(recs[4:])))
        rows = self.rows_for(CodexParser(), rel)
        self.assertEqual([r.turn_type for r in rows], self.LIVE_TYPES)

    def test_missing_zstandard_is_one_row(self):
        rel = self.ARCHIVED + ".zst"
        self._add(rel, b"\x28\xb5\x2f\xfd not really")
        with mock.patch.object(codex_mod, "_zstd_module", return_value=None):
            rows = self.rows_for(CodexParser(), rel)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].turn_type, rows[0].session_id), ("system", CODEX_SESSION))   # from the file name
        self.assertIn("zstandard package not installed", rows[0].text)

    def test_corrupt_zst_is_reported_not_fatal(self):
        if not HAVE_ZSTD:
            self.skipTest("zstandard is not installed")
        rel = self.ARCHIVED + ".zst"
        self._add(rel, b"not a zstd frame at all")
        rows = self.rows_for(CodexParser(), rel)
        self.assertEqual([r.turn_type for r in rows], ["system"])
        self.assertIn("parser:", rows[0].text)


class OpenInterpreterTests(ParserBase):
    LEDGER = ".openinterpreter/external_agent_session_imports.json"

    def test_rows(self):
        rows = self.rows_for(OpenInterpreterParser(), OI_ROLLOUT)
        self.assertEqual([r.turn_type for r in rows], ["system", "user", "tool_use", "tool_result", "assistant", "system"])
        for r in rows:
            self.assertEqual((r.host, r.user, r.agent, r.session_id), ("h1", "alice", "open-interpreter", OI_SESSION))
            self.assertEqual((r.project_path, r.git_branch), ("/srv/proj", "main"))
            self.assertTrue(r.source_file.endswith(OI_ROLLOUT), r.source_file)
        start, user, use, result, asst, done = rows
        self.assertIn("session start: codex_cli_rs 0.9.0 provider=kimi-for-coding", start.text)
        self.assertEqual((start.timestamp_utc, start.model), ("2026-10-01T10:00:00.000Z", ""))
        self.assertEqual((user.text, user.model, user.timestamp_utc), ("list the files", "kimi-k3", "2026-10-01T10:00:01.100Z"))
        self.assertEqual((use.tool_name, use.tool_use_id, use.text), ("Bash", "call_1", '{"command":"ls"}'))
        self.assertEqual((result.tool_use_id, result.text), ("call_1", "README.md"))
        self.assertEqual(asst.text, "One file: README.md")
        self.assertEqual(done.text, "task_complete turn=t1 duration_ms=5000")

    def test_thinking_opt_in(self):
        rows = self.rows_for(OpenInterpreterParser(), OI_ROLLOUT, include_thinking=True)
        self.assertEqual([r.text for r in rows if r.turn_type == "thinking"], ["run ls"])

    def test_history(self):
        rows = self.rows_for(OpenInterpreterParser(), ".openinterpreter/history.jsonl")
        self.assertEqual([(r.turn_type, r.session_id, r.timestamp_utc, r.text) for r in rows],
                         [("user", OI_SESSION, "2026-10-01T10:00:01.000Z", "list the files")])

    def test_archived_and_import_ledger(self):
        rows = self.rows_for(OpenInterpreterParser(), OI_ARCHIVED)
        self.assertEqual([(r.turn_type, r.session_id) for r in rows], [("system", OI_IMPORTED), ("user", OI_IMPORTED)])
        rows = self.rows_for(OpenInterpreterParser(), self.LEDGER)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r.turn_type, r.session_id, r.timestamp_utc, r.source_line),
                         ("system", OI_IMPORTED, "2026-09-30T10:00:00.000Z", 1))
        self.assertEqual(r.text, "imported session from /home/alice/.claude/projects/-home-alice-proj/5b1c.jsonl "
                                 "sha256=ab12cd34 source_modified=2026-09-30T09:00:00.000Z")

    def test_bad_ledger_is_one_row(self):
        (self.home / self.LEDGER).write_text('{"records": [', encoding="utf-8")
        rows = self.rows_for(OpenInterpreterParser(), self.LEDGER)
        self.assertEqual([r.turn_type for r in rows], ["system"])
        self.assertIn("unreadable import ledger", rows[0].text)

    def test_not_wanted(self):
        p = OpenInterpreterParser()
        arts = {a.rel: a for a in self.col.artifacts}
        for rel in (".openinterpreter/auth.json", ".openinterpreter/config.toml", ".openinterpreter/session_index.jsonl"):
            self.assertEqual(arts[rel].agent, "open-interpreter")
            self.assertFalse(p.wants(arts[rel]), rel)
        self.assertFalse(p.wants(arts[CodexTests.REL]))
        self.assertFalse(CodexParser().wants(arts[OI_ROLLOUT]))
        self.assertFalse(CodexParser().wants(arts[self.LEDGER]))
        self.assertTrue(p.wants(SimpleNamespace(rel=OI_ARCHIVED + ".zst")))

    def test_truncated_line_is_reported_not_fatal(self):
        write_bad_line(self.home / OI_ROLLOUT)
        rows = self.rows_for(OpenInterpreterParser(), OI_ROLLOUT)
        self.assertEqual(len(rows), 7)
        self.assertEqual((rows[-1].turn_type, rows[-1].session_id, rows[-1].source_line), ("system", OI_SESSION, 9))
        self.assertIn("1 unparseable line", rows[-1].text)

    @unittest.skipUnless(HAVE_ZSTD, "zstandard is not installed")
    def test_zst_rollout(self):
        import zstandard
        rel = OI_ROLLOUT + ".zst"
        path = self.home / rel
        path.write_bytes(zstandard.ZstdCompressor().compress(_rollout_bytes(open_interpreter_rollout_records())))
        self.col = open_input(self.tmp / "home", self.cat, host="h1")
        rows = self.rows_for(OpenInterpreterParser(), rel)
        self.assertEqual(len(rows), 6)
        self.assertEqual({r.agent for r in rows}, {"open-interpreter"})
