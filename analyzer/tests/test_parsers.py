import csv
import io
import shutil
import tempfile
import unittest
from pathlib import Path

from agent_analyzer import catalog, cli
from agent_analyzer.inputs import open_input
from agent_analyzer.model import summarise
from agent_analyzer.parsers import Options
from agent_analyzer.parsers.claude_code import ClaudeCodeParser, tool_summary
from agent_analyzer.parsers.codex import CodexParser
from agent_analyzer.timeutil import to_utc

from agent_analyzer.parsers.antigravity import AntigravityParser, tool_args_summary, uri_to_path
from agent_analyzer.parsers.crush import CrushParser, project_of
from agent_analyzer.parsers.goose import GooseParser, unescape_history
from agent_analyzer import protobuf, sqlite_util

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
        self.assertEqual({r["agent"] for r in rows}, {"claude-code", "codex-cli", "antigravity", "crush", "goose"})
        self.assertEqual({r["host"] for r in rows}, {"h1"})
        with open(out / "sessions.csv", encoding="utf-8", newline="") as fh:
            sessions = {r["session_id"]: r for r in csv.DictReader(fh)}
        self.assertEqual(set(sessions), {CLAUDE_SESSION, CODEX_SESSION, AGY_CONVERSATION, "99999999-0000-4000-8000-000000000000",
                                         CRUSH_SESSION, GOOSE_SESSION, "20260301_090000"})
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
