"""Qwen Code transcripts.

Validated against source, QwenLM/qwen-code at 2c591ecc (0.24.7, October
2026), with a synthetic fixture; see `research/qwen-code.md`. Qwen Code
forked Gemini CLI but its session format is a Claude-Code-style record
stream, not Gemini's. Files:

* `~/.qwen/projects/<sanitized cwd>/chats/<sessionId>.jsonl`, and archived
  sessions under `chats/archive/`. One `ChatRecord` per line, each with
  `uuid`, `parentUuid`, `sessionId`, `timestamp` (ISO 8601 Z), `type`
  (user, assistant, tool_result, system), `subtype`, `cwd`, `gitBranch`
  and `version`. `message` is a Gemini `Content` `{role, parts}`:
  - user: `parts[].text`; `systemPayload.displayText` is used when the
    parts carry no text.
  - assistant: top-level `model`; `parts[]` hold `text`, `thought: true`
    text (a `thinking` row, opt-in) and `functionCall {id, name, args}`.
  - tool_result: `parts[].functionResponse {id, name, response}` and
    `toolCallResult {callId, status, resultDisplay, errorType}`.
  - system: `subtype` plus `systemPayload`; slash_command (`rawCommand`),
    session_model (`modelId`, `authType`), custom_title (`customTitle`),
    turn_result (`state`, `resultText`), rewind (`truncatedCount`),
    chat_compression (`info`) are summarised, other subtypes (including
    the managed-engine `managed_session_header_v1` records) are emitted
    with their subtype name and the payload as JSON.
  The sidecars `<sessionId>.runtime.json`, `.worktree.json` and
  `.ledger.jsonl` in the same directory are not transcripts and are skipped.
* `~/.qwen/tmp/<sha256(cwd)>/logs.json`: a JSON array of the Gemini-legacy
  `LogEntry {sessionId, messageId, timestamp, type, message}`, `type` user
  or model_switch (whose `message` is a JSON `ModelSwitchEvent {fromModel,
  toModel, reason}`). The directory is a hash, so these rows have no
  project path. A truncated array still yields the entries before the cut.

Not parsed: `checkpoint-<tag>.json` (a raw `Content[]` without timestamps)
and `shell_history`.
"""
from __future__ import annotations

import json
import re
from typing import Iterator

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, iter_jsonl

SESSION_RX = re.compile(r"^\.qwen/projects/[^/]+/chats/(?:archive/)?[^/]+\.jsonl$")
LOGS_RX = re.compile(r"^\.qwen/tmp/[^/]+/logs\.json$")
SIDECAR_SUFFIX = ".ledger.jsonl"

ARG_KEYS = ("command", "absolute_path", "file_path", "path", "pattern", "url", "query", "prompt", "description")


def args_summary(args) -> str:
    """The most identifying argument of a function call, else the arguments
    as JSON."""
    if isinstance(args, dict):
        for k in ARG_KEYS:
            v = args.get(k)
            if v not in (None, ""):
                return v if isinstance(v, str) else compact_json(v)
        return compact_json(args)
    if args in (None, ""):
        return ""
    return args if isinstance(args, str) else compact_json(args)


def _parts(rec: dict) -> list:
    msg = rec.get("message")
    if not isinstance(msg, dict):
        return []
    parts = msg.get("parts")
    return [p for p in parts if isinstance(p, dict)] if isinstance(parts, list) else []


def _response_text(response) -> str:
    if isinstance(response, dict):
        for k in ("output", "error", "llmContent"):
            v = response.get(k)
            if isinstance(v, str) and v:
                return v
        return compact_json(response)
    if response in (None, ""):
        return ""
    return response if isinstance(response, str) else compact_json(response)


def system_text(subtype: str, payload) -> str:
    p = payload if isinstance(payload, dict) else {}
    if subtype == "slash_command":
        detail = "%s %s" % (p.get("phase") or "", p.get("rawCommand") or "")
    elif subtype == "session_model":
        detail = "%s auth=%s" % (p.get("modelId") or "", p.get("authType") or "")
    elif subtype == "custom_title":
        detail = p.get("customTitle") or ""
    elif subtype == "turn_result":
        detail = "%s %s" % (p.get("state") or "", p.get("resultText") or "")
    elif subtype == "rewind":
        detail = "truncated %s record(s)" % p.get("truncatedCount")
    elif subtype == "chat_compression":
        detail = compact_json(p.get("info")) if p.get("info") is not None else ""
    else:
        detail = compact_json(payload) if payload else ""
    detail = str(detail).strip()
    return "%s: %s" % (subtype, detail) if detail else subtype


class QwenCodeParser(Parser):
    agent = "qwen-code"
    name = "qwen-code"

    def wants(self, artifact: Artifact) -> bool:
        rel = artifact.rel
        if LOGS_RX.match(rel):
            return True
        return bool(SESSION_RX.match(rel)) and not rel.endswith(SIDECAR_SUFFIX)

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if LOGS_RX.match(artifact.rel):
            yield from self._parse_logs(artifact, opts)
        else:
            yield from self._parse_session(artifact, opts)

    def _parse_session(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        session_id = ""
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            rtype = rec.get("type")
            if rec.get("sessionId"):
                session_id = str(rec["sessionId"])

            def base(turn_type: str, text: str) -> Row:
                row = self.base_row(artifact)
                row.source_line = n
                row.timestamp_utc = to_utc(rec.get("timestamp"))
                row.session_id = session_id
                row.project_path = str(rec.get("cwd") or "")
                row.git_branch = str(rec.get("gitBranch") or "")
                row.turn_type = turn_type
                row.text = compact(text, opts.max_text_length)
                return row

            parts = _parts(rec)
            if rtype == "user":
                text = "\n".join(p["text"] for p in parts if isinstance(p.get("text"), str) and not p.get("thought"))
                if not text:
                    payload = rec.get("systemPayload")
                    if isinstance(payload, dict):
                        text = str(payload.get("displayText") or "")
                yield base("user", text)
            elif rtype == "assistant":
                model = str(rec.get("model") or "")
                for p in parts:
                    fc = p.get("functionCall")
                    if isinstance(fc, dict):
                        row = base("tool_use", args_summary(fc.get("args")))
                        row.tool_name = str(fc.get("name") or "")
                        row.tool_use_id = str(fc.get("id") or "")
                    elif isinstance(p.get("text"), str) and p.get("thought"):
                        if not opts.include_thinking:
                            continue
                        row = base("thinking", p["text"])
                    elif isinstance(p.get("text"), str) and p["text"]:
                        row = base("assistant", p["text"])
                    else:
                        continue
                    row.model = model
                    yield row
            elif rtype == "tool_result":
                tcr = rec.get("toolCallResult")
                tcr = tcr if isinstance(tcr, dict) else {}
                responses = [p["functionResponse"] for p in parts if isinstance(p.get("functionResponse"), dict)]
                fr = responses[0] if responses else {}
                display = tcr.get("resultDisplay")
                if isinstance(display, str) and display:
                    text = display
                elif fr:
                    text = _response_text(fr.get("response"))
                else:
                    text = compact_json(display) if display else ""
                status = str(tcr.get("status") or "")
                if status and status != "success":
                    tag = status if not tcr.get("errorType") else "%s %s" % (status, tcr.get("errorType"))
                    text = "[%s] %s" % (tag, text)
                row = base("tool_result", text)
                row.tool_name = str(fr.get("name") or "")
                row.tool_use_id = str(tcr.get("callId") or fr.get("id") or "")
                yield row
            elif rtype == "system":
                subtype = str(rec.get("subtype") or "system")
                payload = rec.get("systemPayload")
                row = base("system", system_text(subtype, payload))
                if subtype == "session_model" and isinstance(payload, dict):
                    row.model = str(payload.get("modelId") or "")
                yield row
        if errors:
            yield self._error_row(artifact, session_id, errors)

    def _parse_logs(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        for idx, entry in self._iter_array(artifact.disk_path, errors):
            row = self.base_row(artifact)
            row.source_line = idx
            row.timestamp_utc = to_utc(entry.get("timestamp"))
            row.session_id = str(entry.get("sessionId") or "")
            etype = entry.get("type")
            message = entry.get("message")
            if etype == "user":
                row.turn_type = "user"
                text = message if isinstance(message, str) else compact_json(message)
            else:
                row.turn_type = "system"
                event = message
                if isinstance(message, str):
                    try:
                        event = json.loads(message)
                    except ValueError:
                        event = message
                if etype == "model_switch" and isinstance(event, dict):
                    text = "model_switch: %s -> %s (%s)" % (event.get("fromModel"), event.get("toModel"), event.get("reason"))
                    row.model = str(event.get("toModel") or "")
                else:
                    text = "%s: %s" % (etype, event if isinstance(event, str) else compact_json(event))
            row.text = compact(text, opts.max_text_length)
            yield row
        if errors:
            yield self._error_row(artifact, "", errors, "entry")

    @staticmethod
    def _iter_array(path, errors: list):
        """Yield (1-based index, entry) from a JSON array, decoding element by
        element so a file cut mid-write still yields the entries before the
        cut. A parse failure is recorded in `errors` as (index, message)."""
        with open(path, "rb") as fh:
            data = fh.read().decode("utf-8", errors="replace")
        dec = json.JSONDecoder()
        pos = 0
        n = len(data)

        def skip(p: int) -> int:
            while p < n and data[p] in " \t\r\n":
                p += 1
            return p

        pos = skip(pos)
        if pos >= n:
            return
        if data[pos] != "[":
            errors.append((0, "not a JSON array"))
            return
        pos = skip(pos + 1)
        idx = 0
        while pos < n and data[pos] != "]":
            idx += 1
            try:
                value, pos = dec.raw_decode(data, pos)
            except ValueError as e:
                errors.append((idx, str(e)))
                return
            if isinstance(value, dict):
                yield idx, value
            pos = skip(pos)
            if pos < n and data[pos] == ",":
                pos = skip(pos + 1)
        if pos >= n:
            errors.append((idx + 1, "unterminated JSON array"))

    def _error_row(self, artifact: Artifact, session_id: str, errors: list, unit: str = "line") -> Row:
        row = self.base_row(artifact)
        row.session_id = session_id
        row.turn_type = "system"
        row.source_line = errors[0][0]
        row.text = "parser: %d unparseable %s(s), first at %s %d" % (len(errors), unit, unit, errors[0][0])
        return row
