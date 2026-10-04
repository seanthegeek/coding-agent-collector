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


from agent_analyzer.parsers.continue_dev import ContinueParser, load_session
from agent_analyzer.parsers.aider import AiderParser, AiderProjectParser
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
        self.assertFalse(AiderProjectParser().wants(next(a for a in col.artifacts if a.rel == ".aider.conf.yml")))
