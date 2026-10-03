"""Codex CLI transcripts.

Validated against a real install (Codex CLI, October 2026). Files:

* `~/.codex/sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl`, older
  releases wrote `~/.codex/sessions/rollout-*.jsonl`. Each line is
  `{timestamp, ordinal, type, payload}` with `timestamp` ISO 8601 Z. Types:
  - `session_meta`: payload `id` (session id), `timestamp`, `cwd`,
    `originator`, `cli_version`, `model_provider`, optional `git`
    (`branch`, `commit_hash`, `repository_url`).
  - `turn_context`: payload `turn_id`, `cwd`, `model`, `approval_policy`,
    `sandbox_policy`; updates the current project path and model.
  - `response_item`: payload `type` is `message` (`role` user, assistant or
    developer; `content` blocks with `text`), `function_call` or
    `custom_tool_call` (`name`, `call_id`, `arguments` or `input`),
    `function_call_output` or `custom_tool_call_output` (`call_id`,
    `output`), `local_shell_call` (`action.command`), `web_search_call`,
    `reasoning` (`summary`).
  - `event_msg`: payload `type` task_started, task_complete, token_count,
    item_completed and others; task_started and task_complete become system
    rows, the rest are skipped because the response_item records already
    carry the content.
  - `world_state`, `token_usage_record`: skipped.
* `~/.codex/history.jsonl`: `{session_id, text, ts}` per prompt, `ts` epoch
  seconds.
"""
from __future__ import annotations

import re
from typing import Iterator

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, iter_jsonl, text_of

ROLLOUT_RX = re.compile(r"^\.codex/sessions/(?:.*/)?rollout-[^/]*\.jsonl$")
HISTORY_REL = ".codex/history.jsonl"

CALL_TYPES = ("function_call", "custom_tool_call", "local_shell_call", "web_search_call")
OUTPUT_TYPES = ("function_call_output", "custom_tool_call_output", "local_shell_call_output")


def call_summary(payload: dict) -> str:
    ptype = payload.get("type")
    if ptype == "local_shell_call":
        action = payload.get("action") or {}
        cmd = action.get("command")
        if isinstance(cmd, list):
            return " ".join(str(c) for c in cmd)
        return str(cmd or compact_json(action))
    if ptype == "web_search_call":
        action = payload.get("action") or {}
        return str(action.get("query") or compact_json(action))
    for key in ("arguments", "input"):
        v = payload.get(key)
        if v not in (None, ""):
            return v if isinstance(v, str) else compact_json(v)
    return compact_json({k: v for k, v in payload.items() if k not in ("type", "id", "call_id", "name", "status")})


def call_name(payload: dict) -> str:
    ptype = payload.get("type")
    if ptype == "local_shell_call":
        return "shell"
    if ptype == "web_search_call":
        return "web_search"
    return str(payload.get("name") or ptype or "")


class CodexParser(Parser):
    agent = "codex-cli"
    name = "codex-cli"

    def wants(self, artifact: Artifact) -> bool:
        return artifact.rel == HISTORY_REL or bool(ROLLOUT_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if artifact.rel == HISTORY_REL:
            yield from self._parse_history(artifact, opts)
        else:
            yield from self._parse_rollout(artifact, opts)

    def _parse_history(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            row = self.base_row(artifact)
            row.source_line = n
            row.timestamp_utc = to_utc(rec.get("ts"))
            row.session_id = str(rec.get("session_id") or "")
            row.turn_type = "user"
            row.summary = compact(rec.get("text"), opts.summary_length)
            yield row

    def _parse_rollout(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        session_id = ""
        cwd = ""
        model = ""
        branch = ""
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            rtype = rec.get("type")
            payload = rec.get("payload")
            if not isinstance(payload, dict):
                payload = {}

            def base() -> Row:
                row = self.base_row(artifact)
                row.source_line = n
                row.timestamp_utc = to_utc(rec.get("timestamp"))
                row.session_id = session_id
                row.project_path = cwd
                row.git_branch = branch
                row.model = model
                return row

            if rtype == "session_meta":
                session_id = str(payload.get("id") or payload.get("session_id") or session_id)
                cwd = str(payload.get("cwd") or cwd)
                git = payload.get("git") or {}
                if isinstance(git, dict):
                    branch = str(git.get("branch") or branch)
                row = base()
                row.timestamp_utc = to_utc(payload.get("timestamp") or rec.get("timestamp"))
                row.turn_type = "system"
                row.summary = compact("session start: %s %s provider=%s cwd=%s" % (
                    payload.get("originator") or "codex", payload.get("cli_version") or "",
                    payload.get("model_provider") or "", cwd), opts.summary_length)
                yield row
            elif rtype == "turn_context":
                cwd = str(payload.get("cwd") or cwd)
                model = str(payload.get("model") or model)
            elif rtype == "response_item":
                ptype = payload.get("type")
                if ptype == "message":
                    role = payload.get("role")
                    text = text_of(payload.get("content"))
                    if not text:
                        continue
                    row = base()
                    row.turn_type = "user" if role == "user" else "assistant" if role == "assistant" else "system"
                    if role not in ("user", "assistant"):
                        text = "%s: %s" % (role, text)
                    yield self._fill(row, text, opts)
                elif ptype in CALL_TYPES:
                    row = base()
                    row.turn_type = "tool_use"
                    row.tool_name = call_name(payload)
                    row.tool_use_id = str(payload.get("call_id") or payload.get("id") or "")
                    yield self._fill(row, call_summary(payload), opts)
                elif ptype in OUTPUT_TYPES:
                    row = base()
                    row.turn_type = "tool_result"
                    row.tool_use_id = str(payload.get("call_id") or "")
                    yield self._fill(row, text_of(payload.get("output")), opts)
                elif ptype == "reasoning" and opts.include_thinking:
                    row = base()
                    row.turn_type = "thinking"
                    yield self._fill(row, text_of(payload.get("summary")) or text_of(payload.get("content")), opts)
            elif rtype == "event_msg":
                ptype = payload.get("type")
                if ptype == "task_started":
                    row = base()
                    row.turn_type = "system"
                    yield self._fill(row, "task_started turn=%s" % (payload.get("turn_id") or ""), opts)
                elif ptype == "task_complete":
                    row = base()
                    row.turn_type = "system"
                    yield self._fill(row, "task_complete turn=%s duration_ms=%s" % (
                        payload.get("turn_id") or "", payload.get("duration_ms") or ""), opts)
        if errors:
            row = self.base_row(artifact)
            row.session_id = session_id
            row.turn_type = "system"
            row.source_line = errors[0][0]
            row.summary = "parser: %d unparseable line(s), first at line %d" % (len(errors), errors[0][0])
            yield row

    @staticmethod
    def _fill(row: Row, text: str, opts: Options) -> Row:
        row.summary = compact(text, opts.summary_length)
        return row
