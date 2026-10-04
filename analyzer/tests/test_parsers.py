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
from agent_analyzer import protobuf, sqlite_util

from fixtures import AGY_CONVERSATION, CLAUDE_SESSION, CODEX_SESSION, build_home, write_bad_line


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
        self.assertEqual({r["agent"] for r in rows}, {"claude-code", "codex-cli", "antigravity", "cline", "roo-code"})
        self.assertEqual({r["host"] for r in rows}, {"h1"})
        with open(out / "sessions.csv", encoding="utf-8", newline="") as fh:
            sessions = {r["session_id"]: r for r in csv.DictReader(fh)}
        self.assertLessEqual({CLAUDE_SESSION, CODEX_SESSION, AGY_CONVERSATION, "99999999-0000-4000-8000-000000000000"}, set(sessions))
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
