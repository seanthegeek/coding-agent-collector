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
        self.assertEqual({r["agent"] for r in rows}, {"claude-code", "codex-cli", "antigravity", "zed", "vscode"})
        self.assertEqual({r["host"] for r in rows}, {"h1"})
        with open(out / "sessions.csv", encoding="utf-8", newline="") as fh:
            sessions = {r["session_id"]: r for r in csv.DictReader(fh)}
        self.assertEqual(set(sessions), {CLAUDE_SESSION, CODEX_SESSION, AGY_CONVERSATION, "99999999-0000-4000-8000-000000000000",
                                         ZED_THREAD, ZED_EXTERNAL, VSCODE_SESSION, VSCODE_LEGACY_SESSION})
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
