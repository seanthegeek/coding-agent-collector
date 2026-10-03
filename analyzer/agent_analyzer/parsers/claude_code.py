"""Claude Code transcripts.

Validated against a real install (Claude Code 2.x, October 2026). Files:

* `~/.claude/projects/<slug>/<session>.jsonl`: one JSON object per line.
  Records with `type` user, assistant or system carry `uuid`, `parentUuid`,
  `timestamp` (ISO 8601 Z), `sessionId`, `cwd`, `gitBranch`, `version` and
  `isSidechain`. `message.content` is a string or a list of blocks typed
  text, thinking, tool_use (`id`, `name`, `input`) or tool_result
  (`tool_use_id`, `content`, `is_error`). Assistant records carry
  `message.model`. System records have a `subtype` (turn_duration,
  local_command, away_summary, bridge_status, ...) and `content`.
  Other record types (attachment, mode, ai-title, last-prompt, cost-state,
  file-history-snapshot, file-history-delta, queue-operation, pr-link,
  agent-name, bridge-session, atis-latch, permission-mode) are session
  metadata; pr-link and queue-operation are emitted as system rows, the rest
  are skipped.
* `~/.claude/projects/<slug>/<session>/subagents/*.jsonl`: subagent
  transcripts in the same format.
* `~/.claude/history.jsonl`: `{display, project, sessionId, timestamp}` per
  prompt, `timestamp` in epoch milliseconds. Kept even when the session file
  exists because it survives session deletion.
"""
from __future__ import annotations

import re
from typing import Iterator

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, iter_jsonl, text_of

SESSION_RX = re.compile(r"^\.claude/projects/[^/]+/.*\.jsonl$")
HISTORY_REL = ".claude/history.jsonl"

# Which tool_use input field best identifies the action, per tool name.
TOOL_KEYS = {
    "Bash": ("command",),
    "Read": ("file_path",),
    "Write": ("file_path",),
    "Edit": ("file_path",),
    "MultiEdit": ("file_path",),
    "NotebookEdit": ("notebook_path",),
    "Glob": ("pattern", "path"),
    "Grep": ("pattern", "path"),
    "WebFetch": ("url",),
    "WebSearch": ("query",),
    "Agent": ("description", "prompt"),
    "Task": ("description", "prompt"),
    "Skill": ("skill", "args"),
    "LS": ("path",),
}


def tool_summary(name: str, inp) -> str:
    if not isinstance(inp, dict):
        return compact_json(inp)
    keys = TOOL_KEYS.get(name)
    if keys:
        vals = [str(inp[k]) for k in keys if inp.get(k) not in (None, "")]
        if vals:
            return " | ".join(vals)
    for k in ("command", "file_path", "path", "pattern", "url", "query", "description"):
        if inp.get(k) not in (None, ""):
            return str(inp[k])
    return compact_json(inp)


class ClaudeCodeParser(Parser):
    agent = "claude-code"
    name = "claude-code"

    def wants(self, artifact: Artifact) -> bool:
        return artifact.rel == HISTORY_REL or bool(SESSION_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if artifact.rel == HISTORY_REL:
            yield from self._parse_history(artifact, opts)
        else:
            yield from self._parse_session(artifact, opts)

    def _parse_history(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            row = self.base_row(artifact)
            row.source_line = n
            row.timestamp_utc = to_utc(rec.get("timestamp"))
            row.session_id = str(rec.get("sessionId") or "")
            row.project_path = str(rec.get("project") or "")
            row.turn_type = "user"
            row.text = compact(rec.get("display"), opts.max_text_length)
            yield row

    def _parse_session(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        session_id = ""
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            rtype = rec.get("type")
            sid = rec.get("sessionId") or rec.get("session_id")
            if sid:
                session_id = str(sid)

            def base() -> Row:
                row = self.base_row(artifact)
                row.source_line = n
                row.timestamp_utc = to_utc(rec.get("timestamp"))
                row.session_id = session_id
                row.project_path = str(rec.get("cwd") or "")
                row.git_branch = str(rec.get("gitBranch") or "")
                return row

            if rtype == "user":
                msg = rec.get("message") or {}
                content = msg.get("content")
                is_meta = bool(rec.get("isMeta"))
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        btype = block.get("type")
                        if btype == "tool_result":
                            row = base()
                            row.turn_type = "tool_result"
                            row.tool_use_id = str(block.get("tool_use_id") or "")
                            text = text_of(block.get("content"))
                            if block.get("is_error"):
                                text = "[error] " + text
                            row.text = compact(text, opts.max_text_length)
                            yield row
                        elif btype in ("text", "image"):
                            row = base()
                            row.turn_type = "system" if is_meta else "user"
                            row.text = compact(text_of([block]), opts.max_text_length)
                            yield row
                else:
                    row = base()
                    row.turn_type = "system" if is_meta else "user"
                    row.text = compact(text_of(content), opts.max_text_length)
                    yield row
            elif rtype == "assistant":
                msg = rec.get("message") or {}
                model = str(msg.get("model") or "")
                content = msg.get("content")
                blocks = content if isinstance(content, list) else [{"type": "text", "text": text_of(content)}]
                for block in blocks:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "tool_use":
                        row = base()
                        row.turn_type = "tool_use"
                        row.model = model
                        row.tool_name = str(block.get("name") or "")
                        row.tool_use_id = str(block.get("id") or "")
                        row.text = compact(tool_summary(row.tool_name, block.get("input")), opts.max_text_length)
                        yield row
                    elif btype == "text":
                        text = block.get("text")
                        if not text:
                            continue
                        row = base()
                        row.turn_type = "assistant"
                        row.model = model
                        row.text = compact(text, opts.max_text_length)
                        yield row
                    elif btype in ("thinking", "redacted_thinking") and opts.include_thinking:
                        row = base()
                        row.turn_type = "thinking"
                        row.model = model
                        row.text = compact(block.get("thinking") or "[redacted]", opts.max_text_length)
                        yield row
            elif rtype == "system":
                row = base()
                row.turn_type = "system"
                subtype = str(rec.get("subtype") or "system")
                detail = rec.get("content")
                if subtype == "turn_duration":
                    detail = "%s ms, %s messages" % (rec.get("durationMs"), rec.get("messageCount"))
                row.text = compact("%s: %s" % (subtype, text_of(detail)) if detail else subtype, opts.max_text_length)
                yield row
            elif rtype == "pr-link":
                row = base()
                row.turn_type = "system"
                row.text = compact("pr-link: %s" % (rec.get("prUrl") or rec.get("prNumber")), opts.max_text_length)
                yield row
            elif rtype == "queue-operation":
                row = base()
                row.turn_type = "system"
                row.text = compact("queue %s: %s" % (rec.get("operation"), rec.get("content") or ""), opts.max_text_length)
                yield row
        if errors:
            row = self.base_row(artifact)
            row.session_id = session_id
            row.turn_type = "system"
            row.source_line = errors[0][0]
            row.text = "parser: %d unparseable line(s), first at line %d" % (len(errors), errors[0][0])
            yield row
