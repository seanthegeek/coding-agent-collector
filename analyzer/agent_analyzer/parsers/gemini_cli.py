"""Gemini CLI transcripts.

Validated against source, google-gemini/gemini-cli at fb972b2 (0.64.0-nightly,
2026-10-02), with a synthetic fixture; see `research/gemini-cli.md`. Files,
under `~/.gemini` or the macOS sandbox base `~/.cache/.gemini`:

* `tmp/<slug>/chats/session-<YYYY-MM-DDTHH-MM>-<id8>.jsonl`, and subagent
  sessions at `tmp/<slug>/chats/<parentSessionId>/<sessionId>.jsonl`. One
  JSON object per line, discriminated as the reader in
  `chatRecordingService.ts` does:
  - metadata (line 1): `sessionId`, `projectHash`, `startTime`,
    `lastUpdated`, `summary`, `directories`, `kind`.
  - message: `id`, `timestamp`, `type` (user, gemini, info, error, warning),
    `content` (string, Part or Part[]; parts carry `text`, `thought`,
    `functionCall` {`id`, `name`, `args`}, `functionResponse` {`id`, `name`,
    `response`}, `inlineData`, `fileData`). Gemini messages also carry
    `model`, `thoughts` [{`subject`, `description`, `timestamp`}] and
    `toolCalls` [{`id`, `name`, `args`, `result`, `status`, `timestamp`,
    `displayName`}]. A message is re-appended whole whenever its tool calls
    change; the last record per `id` wins and keeps its first position.
  - `{"$set": {...}}`: metadata update; `sessionId` (rewritten on resume),
    `summary`, and the deprecated `messages` full-history checkpoint, which
    replaces every message.
  - `{"$patch": {id, content, toolCalls: [{id, result}], updates, removeIds,
    orderIds}}`: edits, removes or reorders earlier messages.
  - `{"$rewindTo": "<message id>"}`: drops that message and every later one;
    an unknown id drops all of them.
  The operations are replayed as the reader does and the surviving messages
  are emitted, each with the source line of its last full record. Each
  message keeps the `sessionId` in force when it was first written, so a
  resumed session's earlier turns stay under the earlier id. A `$rewindTo`
  or `removeIds` is reported as a `system` row with the count dropped; the
  dropped content is still in the source file at the cited lines. Rewind,
  summary and removal rows carry no timestamp of their own and inherit the
  latest one seen before them.
* The legacy single-object form, the same name with `.json`: a
  `ConversationRecord` with the metadata fields and `messages`. It is left
  in place when a resume migrates it to a sibling `.jsonl`, so both may be
  parsed and the turns appear twice; filter on `source_file`.
* `tmp/<slug>/logs.json`: a JSON array of `{sessionId, messageId,
  timestamp, type, message}`, user prompts only. Parsed even when the
  session file exists, like the other history files, because it keeps
  prompts that a rewind removed from the session.

No cwd and no git branch are stored per message. `project_path` is the
content of `tmp/<slug>/.project_root`, else the key of `projects.json`
(`{"projects": {"<path>": "<slug>"}}`) mapping to the slug, else the key
whose sha256 equals the legacy hash directory name or the `projectHash`,
else the `projectHash` itself. Tool checkpoints (`checkpoints/*.json`,
`checkpoint-<tag>.json`) and the activity log under `logs/` are not parsed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import OrderedDict
from collections.abc import Iterator
from pathlib import Path

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, iter_jsonl

SESSION_RX = re.compile(
    r"^(?P<base>(?:\.cache/)?\.gemini)/tmp/(?P<slug>[^/]+)/chats/(?:.*/)?[^/]+\.jsonl?$"
)
LOGS_RX = re.compile(r"^(?P<base>(?:\.cache/)?\.gemini)/tmp/(?P<slug>[^/]+)/logs\.json$")
HEX64_RX = re.compile(r"^[0-9a-f]{64}$")

MESSAGE_TYPES = ("user", "gemini", "info", "error", "warning")
FAILED_STATUSES = ("error", "cancelled")


# ---- content helpers ----------------------------------------------------------


def _parts(content) -> list:
    if content is None:
        return []
    if isinstance(content, list):
        return content
    return [content]


def part_text(content, thoughts: bool = False) -> str:
    """Text of a PartListUnion. Thought parts are included only when
    `thoughts` is set, and then only they are."""
    out = []
    for p in _parts(content):
        if isinstance(p, str):
            if not thoughts:
                out.append(p)
            continue
        if not isinstance(p, dict):
            continue
        if bool(p.get("thought")) != thoughts:
            continue
        if isinstance(p.get("text"), str):
            out.append(p["text"])
        elif thoughts:
            continue
        elif isinstance(p.get("functionResponse"), dict):
            out.append(response_text(p["functionResponse"]))
        elif isinstance(p.get("inlineData"), dict):
            out.append("[inlineData %s]" % (p["inlineData"].get("mimeType") or ""))
        elif isinstance(p.get("fileData"), dict):
            out.append("[fileData %s]" % (p["fileData"].get("fileUri") or ""))
    return "\n".join(s for s in out if s)


def response_text(fr: dict) -> str:
    resp = fr.get("response")
    if isinstance(resp, dict):
        for key in ("output", "error", "content"):
            v = resp.get(key)
            if isinstance(v, str) and v:
                return v
    if isinstance(resp, str):
        return resp
    return compact_json(resp)


def result_text(result) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    texts = []
    for p in _parts(result):
        if isinstance(p, dict) and isinstance(p.get("functionResponse"), dict):
            texts.append(response_text(p["functionResponse"]))
        elif isinstance(p, dict) and isinstance(p.get("text"), str):
            texts.append(p["text"])
        elif isinstance(p, str):
            texts.append(p)
        else:
            texts.append(compact_json(p))
    return "\n".join(t for t in texts if t)


def tool_text(call: dict) -> str:
    args = call.get("args")
    s = compact_json(args) if args not in (None, "") else ""
    label = call.get("displayName")
    if label and label != call.get("name"):
        return "%s: %s" % (label, s) if s else str(label)
    return s


# ---- project path -------------------------------------------------------------


def _read_small(path: Path) -> str | None:
    try:
        if os.path.islink(str(path)) or not path.is_file():
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def resolve_project(base: Path, slug: str, project_hash: str = "") -> str:
    """Project path for `tmp/<slug>` under the `.gemini` directory `base`."""
    root = _read_small(base / "tmp" / slug / ".project_root")
    if root and root.strip():
        return root.strip()
    projects = {}
    raw = _read_small(base / "projects.json")
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and isinstance(data.get("projects"), dict):
                projects = data["projects"]
        except ValueError:
            pass
    for path, s in projects.items():
        if s == slug:
            return str(path)
    wanted = {h for h in (slug if HEX64_RX.match(slug) else "", project_hash) if h}
    if wanted:
        for path in projects:
            if hashlib.sha256(str(path).encode("utf-8")).hexdigest() in wanted:
                return str(path)
    return project_hash


# ---- parser -------------------------------------------------------------------


class GeminiCliParser(Parser):
    agent = "gemini-cli"
    name = "gemini-cli"

    def wants(self, artifact: Artifact) -> bool:
        return bool(SESSION_RX.match(artifact.rel) or LOGS_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        m = LOGS_RX.match(artifact.rel)
        if m:
            yield from self._parse_logs(artifact, opts, m)
            return
        m = SESSION_RX.match(artifact.rel)
        if m:
            yield from self._parse_session(artifact, opts, m)

    def _base_dir(self, artifact: Artifact, m) -> Path:
        return Path(artifact.home.disk_path) / m.group("base")

    def _system(
        self,
        artifact: Artifact,
        line: int,
        ts: str,
        sid: str,
        project: str,
        text: str,
        opts: Options,
    ) -> Row:
        row = self.base_row(artifact)
        row.source_line = line
        row.timestamp_utc = ts
        row.session_id = sid
        row.project_path = project
        row.turn_type = "system"
        row.text = compact(text)
        return row

    # -- logs.json --

    def _parse_logs(self, artifact: Artifact, opts: Options, m) -> Iterator[Row]:
        project = resolve_project(self._base_dir(artifact, m), m.group("slug"))
        try:
            with open(artifact.disk_path, "rb") as fh:
                data = json.loads(fh.read().decode("utf-8", errors="replace"))
        except ValueError as e:
            yield self._system(
                artifact, 0, "", "", project, "parser: unparseable logs.json: %s" % e, opts
            )
            return
        if not isinstance(data, list):
            yield self._system(
                artifact, 0, "", "", project, "parser: logs.json is not a JSON array", opts
            )
            return
        for i, rec in enumerate(data):
            if not isinstance(rec, dict):
                continue
            row = self.base_row(artifact)
            row.source_line = i + 1  # array index, 1-based
            row.timestamp_utc = to_utc(rec.get("timestamp"))
            row.session_id = str(rec.get("sessionId") or "")
            row.project_path = project
            row.turn_type = "user"
            row.text = compact(rec.get("message"))
            yield row

    # -- sessions --

    def _parse_session(self, artifact: Artifact, opts: Options, m) -> Iterator[Row]:
        base = self._base_dir(artifact, m)
        slug = m.group("slug")
        if artifact.rel.endswith(".json"):
            records, errors = self._legacy_records(artifact)
        else:
            records, errors = self._jsonl_records(artifact)

        meta: dict = {}
        # id -> [record, line, session_id]
        messages: OrderedDict[str, list] = OrderedDict()
        starts: list[tuple[int, str, str, str]] = []  # (line, ts, session_id, text)
        events: list[tuple[int, str, str, str]] = []
        session_id = ""
        latest_ts = ""

        def put(msg: dict, line: int) -> None:
            mid = msg["id"]
            if mid in messages:
                messages[mid][0] = msg
                messages[mid][1] = line
            else:
                messages[mid] = [msg, line, session_id]

        def drop(ids: list) -> int:
            n = 0
            for i in ids:
                if messages.pop(i, None) is not None:
                    n += 1
            return n

        for n, rec in records:
            if isinstance(rec.get("$rewindTo"), str):
                target = rec["$rewindTo"]
                keys = list(messages)
                cut = keys.index(target) if target in messages else 0
                dropped = drop(keys[cut:])
                events.append(
                    (
                        n,
                        latest_ts,
                        session_id,
                        "rewind to %s: %d message(s) dropped" % (target, dropped),
                    )
                )
            elif isinstance(rec.get("$patch"), dict):
                p = rec["$patch"]
                if isinstance(p.get("id"), str):
                    self._apply_patch(messages, p)
                for u in p.get("updates") or []:
                    if isinstance(u, dict) and isinstance(u.get("id"), str):
                        self._apply_patch(messages, u)
                rem = [i for i in (p.get("removeIds") or []) if isinstance(i, str)]
                if rem:
                    dropped = drop(rem)
                    events.append(
                        (n, latest_ts, session_id, "patch removed %d message(s)" % dropped)
                    )
                order = [
                    i for i in (p.get("orderIds") or []) if isinstance(i, str) and i in messages
                ]
                if order:
                    for i in order:
                        messages.move_to_end(i)
            elif isinstance(rec.get("id"), str):
                ts = to_utc(rec.get("timestamp"))
                latest_ts = max(latest_ts, ts)
                put(rec, n)
            elif isinstance(rec.get("$set"), dict):
                s = rec["$set"]
                if isinstance(s.get("sessionId"), str) and s["sessionId"]:
                    session_id = s["sessionId"]
                if isinstance(s.get("messages"), list):
                    messages.clear()
                    for msg in s["messages"]:
                        if isinstance(msg, dict) and isinstance(msg.get("id"), str):
                            latest_ts = max(latest_ts, to_utc(msg.get("timestamp")))
                            put(msg, n)
                meta.update({k: v for k, v in s.items() if k != "messages"})
                if s.get("summary"):
                    ts = to_utc(s.get("lastUpdated")) or latest_ts
                    events.append((n, ts, session_id, "summary: %s" % s["summary"]))
            elif isinstance(rec.get("sessionId"), str):
                meta.update({k: v for k, v in rec.items() if k != "messages"})
                session_id = rec["sessionId"] or session_id
                ts = to_utc(rec.get("startTime"))
                latest_ts = max(latest_ts, ts)
                text = "session start: kind=%s projectHash=%s" % (
                    rec.get("kind") or "main",
                    rec.get("projectHash") or "",
                )
                if rec.get("directories"):
                    text += " directories=%s" % compact_json(rec["directories"])
                starts.append((n, ts, session_id, text))
                for msg in rec.get("messages") or []:  # legacy ConversationRecord
                    if isinstance(msg, dict) and isinstance(msg.get("id"), str):
                        latest_ts = max(latest_ts, to_utc(msg.get("timestamp")))
                        put(msg, n)

        project = resolve_project(base, slug, str(meta.get("projectHash") or ""))
        # Session start, then the surviving messages in replay order, then
        # summaries, rewinds and removals.
        for line, ts, sid, text in starts:
            yield self._system(artifact, line, ts, sid, project, text, opts)
        for msg, line, sid in messages.values():
            yield from self._message_rows(artifact, opts, msg, line, sid or session_id, project)
        for line, ts, sid, text in events:
            yield self._system(artifact, line, ts, sid, project, text, opts)
        if errors:
            yield self._system(
                artifact,
                errors[0][0],
                "",
                session_id,
                project,
                "parser: %d unparseable line(s), first at line %d" % (len(errors), errors[0][0]),
                opts,
            )

    @staticmethod
    def _apply_patch(messages: OrderedDict[str, list], patch: dict) -> None:
        entry = messages.get(patch["id"])
        if entry is None:
            return
        msg = dict(entry[0])
        if "content" in patch and patch["content"] is not None:
            msg["content"] = patch["content"]
        if (
            isinstance(patch.get("toolCalls"), list)
            and msg.get("type") == "gemini"
            and isinstance(msg.get("toolCalls"), list)
        ):
            calls = [dict(c) if isinstance(c, dict) else c for c in msg["toolCalls"]]
            for tp in patch["toolCalls"]:
                if not isinstance(tp, dict) or "result" not in tp:
                    continue
                for c in calls:
                    if isinstance(c, dict) and c.get("id") == tp.get("id"):
                        c["result"] = tp["result"]
                        break
            msg["toolCalls"] = calls
        entry[0] = msg

    @staticmethod
    def _jsonl_records(artifact: Artifact):
        errors: list = []
        return list(iter_jsonl(artifact.disk_path, errors)), errors

    def _legacy_records(self, artifact: Artifact):
        try:
            with open(artifact.disk_path, "rb") as fh:
                rec = json.loads(fh.read().decode("utf-8", errors="replace"))
        except ValueError as e:
            return [], [(1, str(e))]
        if not isinstance(rec, dict) or not isinstance(rec.get("sessionId"), str):
            return [], [(1, "not a ConversationRecord")]
        return [(1, rec)], []

    def _message_rows(
        self, artifact: Artifact, opts: Options, msg: dict, line: int, sid: str, project: str
    ) -> list[Row]:
        mtype = msg.get("type")
        ts = to_utc(msg.get("timestamp"))
        model = str(msg.get("model") or "") if mtype == "gemini" else ""

        def row(turn: str, text: str, when: str = "") -> Row:
            r = self.base_row(artifact)
            r.source_line = line
            r.timestamp_utc = when or ts
            r.session_id = sid
            r.project_path = project
            r.turn_type = turn
            r.model = model
            r.text = compact(text)
            return r

        out: list[Row] = []
        content = msg.get("content")
        if mtype == "user":
            out.append(row("user", part_text(content)))
            return out
        if mtype != "gemini":
            out.append(row("system", "%s: %s" % (mtype or "message", part_text(content))))
            return out

        if opts.include_thinking:
            for t in msg.get("thoughts") or []:
                if not isinstance(t, dict):
                    continue
                subj, desc = t.get("subject") or "", t.get("description") or ""
                out.append(
                    row(
                        "thinking",
                        "%s: %s" % (subj, desc) if subj else desc,
                        to_utc(t.get("timestamp")),
                    )
                )
            thought = part_text(content, thoughts=True)
            if thought:
                out.append(row("thinking", thought))
        text = part_text(content)
        if text:
            out.append(row("assistant", text))

        calls = [c for c in (msg.get("toolCalls") or []) if isinstance(c, dict)]
        seen = {str(c.get("id") or "") for c in calls}
        # "Modern" sessions may carry functionCall parts in content instead.
        for p in _parts(content):
            fc = p.get("functionCall") if isinstance(p, dict) else None
            if isinstance(fc, dict) and str(fc.get("id") or "") not in seen:
                calls.append({"id": fc.get("id"), "name": fc.get("name"), "args": fc.get("args")})
        for c in calls:
            cid = str(c.get("id") or "")
            name = str(c.get("name") or "")
            when = to_utc(c.get("timestamp"))
            use = row("tool_use", tool_text(c), when)
            use.tool_name, use.tool_use_id = name, cid
            out.append(use)
            status = c.get("status") or ""
            if c.get("result") is not None or status in FAILED_STATUSES:
                text = result_text(c.get("result"))
                if status in FAILED_STATUSES:
                    text = "[%s] %s" % (status, text) if text else "[%s]" % status
                res = row("tool_result", text, when)
                res.tool_name, res.tool_use_id = name, cid
                out.append(res)
        if not out:
            # An empty gemini turn (no text, no tools) still marks a model call.
            out.append(row("assistant", ""))
        return out
