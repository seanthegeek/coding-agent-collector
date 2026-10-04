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
        self.assertLessEqual({"claude-code", "codex-cli", "antigravity"}, {r["agent"] for r in rows})
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


from agent_analyzer.parsers.opencode import OpenCodeParser, tool_summary as opencode_tool_summary
from agent_analyzer.parsers.kilo_code import KiloCodeParser, iter_json_array
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
        self.assertEqual(iter_json_array('[1, {"a": 2} ,3]'), ([1, {"a": 2}, 3], None))
        self.assertEqual(iter_json_array("[]"), ([], None))
        self.assertEqual(iter_json_array('[1, {"a"')[0], [1])
        self.assertEqual(iter_json_array("[1, 2")[1], "record 3: unexpected end of file")
        self.assertEqual(iter_json_array('{"a":1}'), ([], "not a JSON array"))
