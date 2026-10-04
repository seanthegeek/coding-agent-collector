"""pi coding agent sessions.

Validated against source, earendil-works/pi at 20038712 (coding-agent
1.0.2, October 2026; v0.83.0 at 845d6ff1 where the schema differs), with a
synthetic fixture; see `research/pi.md`. Files:

* `~/.pi/agent/sessions/--<encoded cwd>--/<ISO time>_<session id>.jsonl`,
  and legacy `~/.pi/agent/*.jsonl`. One JSON object per line, append-only:
  - line 1, the header: `type: "session"`, `version` (3; absent in v1),
    `id` (session id), `timestamp` (ISO 8601 Z), `cwd`, optional
    `parentSession` (absolute path of the file this one was forked or
    branched from). Files whose first record is not a header are skipped.
  - entries: `type`, `id`, `parentId`, `timestamp` (ISO). Types:
    `message` (`message.role` below), `model_change` (`provider`,
    `modelId`), `thinking_level_change` (`thinkingLevel`), `compaction`
    (`summary`, `tokensBefore`), `branch_summary` (`summary`, `fromId`),
    `custom_message` (`customType`, `content`), `context_edit`
    (`targetId`, `replacement.content`), `session_info` (`name`) become
    system rows; `custom`, `label` and `usage` are extension or UI state
    and are skipped, as are unknown types.
  - `message.role`, each with `timestamp` in Unix ms (the fallback when
    the entry has none): `user` (`content` string or text/image parts);
    `assistant` (`content[]` of `text`, `thinking` (`thinking`,
    `redacted`), `toolCall` (`id`, `name`, `arguments`); `provider`,
    `model`, `stopReason`, `errorMessage`); `toolResult` (`toolCallId`,
    `toolName`, `content[]`, `isError`); `bashExecution` (a user
    `!command`: `command`, `output`, `exitCode`, `cancelled`), emitted as a
    tool_use and a tool_result joined on the entry `id`; `system`
    (`content`, the system prompt), `custom` (`customType`, `content`),
    `branchSummary` and `compactionSummary` (`summary`) as system rows.
  The file holds every branch of the `id`/`parentId` tree; rows follow
  file order, not the active branch.
* Forks: pi copies every parent entry into the child file verbatim, ids
  and timestamps included. When the header's `parentSession` resolves to a
  file present in the same collected home, child entries whose `id` and
  `timestamp` match a parent entry are dropped and one system row says how
  many, so a fork does not double the timeline.
* little-coder (a pi launcher) writes into pi's own directory and the
  header names no producer. A session with a `custom_message` whose
  `customType` starts `lc-`, an assistant `provider` of `llamacpp`, or a
  `~/.little-coder/checkpoints/<this file name>/` directory gets one
  system row saying so; its rows stay agent `pi`, as the manifest says.
* `~/.pi/agent/experimental/sessions/<id>/meta.json` (`PI_EXPERIMENTAL=1`,
  not at v0.83.0): `{createdAt (ms), cwd}`, one system row per session.
  The transcript beside it, `session.sqlite`, is not parsed: its `record`
  JSON shape was not determined by the research.

The session reader (`read_session`, `entry_rows`) is shared with
`letta.py`, whose local backend writes the same format.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, iter_jsonl, text_of

SESSION_RX = re.compile(r"^\.pi/agent/(?:sessions/[^/]+/)?[^/]+\.jsonl$")
META_RX = re.compile(r"^\.pi/agent/experimental/sessions/([^/]+)/meta\.json$")

ARG_KEYS = ("command", "path", "file_path", "pattern", "code", "url", "query")
SKIPPED_ENTRIES = ("custom", "label", "usage")


class SessionFile:
    """One pi-format session file: the header (empty when line 1 is not
    one), the entries after it as (line, record), and unparseable lines."""

    def __init__(self) -> None:
        self.header: dict = {}
        self.header_line = 0
        self.entries: List[Tuple[int, dict]] = []
        self.errors: list = []


def read_session(path) -> SessionFile:
    s = SessionFile()
    first = True
    for n, rec in iter_jsonl(path, s.errors):
        if first:
            first = False
            if rec.get("type") == "session":
                s.header, s.header_line = rec, n
                continue
        s.entries.append((n, rec))
    return s


def entry_keys(path) -> Set[Tuple[str, str]]:
    """(id, timestamp) of every entry, for fork deduplication."""
    out: Set[Tuple[str, str]] = set()
    for _, rec in read_session(path).entries:
        if rec.get("id"):
            out.add((str(rec.get("id")), str(rec.get("timestamp") or "")))
    return out


def args_summary(args) -> str:
    """The most identifying tool argument, else the arguments as JSON."""
    if isinstance(args, dict):
        for k in ARG_KEYS:
            v = args.get(k)
            if v not in (None, ""):
                return v if isinstance(v, str) else compact_json(v)
        return compact_json(args)
    if args in (None, ""):
        return ""
    return args if isinstance(args, str) else compact_json(args)


def _label(prefix: str, text: str) -> str:
    return "%s: %s" % (prefix, text) if text else prefix


def entry_rows(parser: Parser, artifact: Artifact, session: SessionFile, opts: Options,
               session_id: str = "", project_path: str = "",
               skip: Optional[Set[Tuple[str, str]]] = None) -> Iterator[Row]:
    """Timeline rows for the entries of a pi-format session. `skip` holds
    (id, timestamp) keys to drop (entries a fork copied from its parent)."""
    skip = skip or set()
    for n, rec in session.entries:
        if skip and (str(rec.get("id") or ""), str(rec.get("timestamp") or "")) in skip:
            continue
        etype = rec.get("type")
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}

        def base(model: str = "") -> Row:
            row = parser.base_row(artifact)
            row.source_line = n
            row.timestamp_utc = to_utc(rec.get("timestamp")) or to_utc(msg.get("timestamp"))
            row.session_id = session_id
            row.project_path = project_path
            row.model = model
            return row

        def emit(row: Row, turn: str, text: str, tool_name: str = "", tool_use_id: str = "") -> Row:
            row.turn_type = turn
            row.tool_name = tool_name
            row.tool_use_id = tool_use_id
            row.text = compact(text, opts.max_text_length)
            return row

        if etype == "message":
            yield from _message_rows(msg, rec, base, emit, opts)
        elif etype == "model_change":
            model = str(rec.get("modelId") or "")
            yield emit(base(model), "system", "model_change: %s/%s" % (rec.get("provider") or "", model))
        elif etype == "thinking_level_change":
            yield emit(base(), "system", "thinking_level_change: %s" % (rec.get("thinkingLevel") or ""))
        elif etype == "compaction":
            yield emit(base(), "system", _label("compaction: tokensBefore=%s" % (rec.get("tokensBefore") or ""),
                                               str(rec.get("summary") or "")))
        elif etype == "branch_summary":
            yield emit(base(), "system", _label("branch_summary from %s" % (rec.get("fromId") or ""),
                                               str(rec.get("summary") or "")))
        elif etype == "custom_message":
            yield emit(base(), "system", _label("custom_message %s" % (rec.get("customType") or ""),
                                               text_of(rec.get("content"))))
        elif etype == "context_edit":
            rep = rec.get("replacement")
            what = text_of(rep.get("content")) if isinstance(rep, dict) else "omitted from context"
            yield emit(base(), "system", _label("context_edit target=%s" % (rec.get("targetId") or ""), what))
        elif etype == "session_info":
            yield emit(base(), "system", "session_info: name=%s" % (rec.get("name") or ""))
        # custom, label, usage and unknown types carry no conversation content.


def _message_rows(msg: dict, rec: dict, base, emit, opts: Options) -> Iterator[Row]:
    role = msg.get("role")
    if role == "user":
        text = text_of(msg.get("content"))
        if text:
            yield emit(base(), "user", text)
    elif role == "assistant":
        model = str(msg.get("model") or "")
        content = msg.get("content")
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        for part in content if isinstance(content, list) else []:
            if not isinstance(part, dict):
                continue
            ptype = part.get("type")
            if ptype == "text" and part.get("text"):
                yield emit(base(model), "assistant", str(part.get("text")))
            elif ptype == "thinking" and opts.include_thinking:
                text = str(part.get("thinking") or "")
                if part.get("redacted") and not text:
                    text = "[redacted]"
                if text:
                    yield emit(base(model), "thinking", text)
            elif ptype == "toolCall":
                name = str(part.get("name") or "")
                yield emit(base(model), "tool_use", args_summary(part.get("arguments")),
                           tool_name=name, tool_use_id=str(part.get("id") or ""))
        if msg.get("stopReason") in ("error", "aborted"):
            yield emit(base(model), "system", _label("assistant stopReason=%s" % msg.get("stopReason"),
                                                     str(msg.get("errorMessage") or "")))
    elif role == "toolResult":
        text = text_of(msg.get("content"))
        if msg.get("isError"):
            text = "[error] " + text
        yield emit(base(), "tool_result", text, tool_name=str(msg.get("toolName") or ""),
                   tool_use_id=str(msg.get("toolCallId") or ""))
    elif role == "bashExecution":
        eid = str(rec.get("id") or "")
        yield emit(base(), "tool_use", str(msg.get("command") or ""), tool_name="bash", tool_use_id=eid)
        out = str(msg.get("output") or "")
        notes = []
        if msg.get("exitCode") not in (None, 0):
            notes.append("exit %s" % msg.get("exitCode"))
        if msg.get("cancelled"):
            notes.append("cancelled")
        if msg.get("truncated"):
            notes.append("truncated")
        if notes:
            out = (out + "\n" if out else "") + "[%s]" % ", ".join(notes)
        yield emit(base(), "tool_result", out, tool_name="bash", tool_use_id=eid)
    elif role == "system":
        yield emit(base(), "system", _label("system prompt", text_of(msg.get("content"))))
    elif role == "custom":
        yield emit(base(), "system", _label("custom %s" % (msg.get("customType") or ""), text_of(msg.get("content"))))
    elif role in ("branchSummary", "compactionSummary"):
        yield emit(base(), "system", _label(role, str(msg.get("summary") or "")))


def error_row(parser: Parser, artifact: Artifact, errors: list, session_id: str = "",
              project_path: str = "") -> Row:
    row = parser.base_row(artifact)
    row.session_id = session_id
    row.project_path = project_path
    row.turn_type = "system"
    row.source_line = errors[0][0]
    row.text = "parser: %d unparseable line(s), first at line %d" % (len(errors), errors[0][0])
    return row


def home_file(artifact: Artifact, original: str, marker: str) -> Optional[Path]:
    """The collected copy of `original` (a path on the source host) inside
    the artifact's home, or None. Tried relative to the home's original path,
    then from the last `marker` segment (loose input whose home path is not
    the host's). Symlinks are never followed."""
    p = original.replace("\\", "/")
    rels = []
    h = artifact.home.original.replace("\\", "/").rstrip("/")
    if h and p.startswith(h + "/"):
        rels.append(p[len(h) + 1:])
    i = p.rfind("/" + marker)
    if i >= 0:
        rels.append(p[i + 1:])
    root = artifact.home.disk_path
    for rel in rels:
        parts = [x for x in rel.split("/") if x]
        if not parts or ".." in parts:
            continue
        cur = root
        ok = True
        for x in parts:
            cur = cur / x
            if cur.is_symlink():
                ok = False
                break
        if ok and cur.is_file():
            return cur
    return None


class PiParser(Parser):
    agent = "pi"
    name = "pi"

    def __init__(self) -> None:
        self._parent_cache: Dict[Path, Set[Tuple[str, str]]] = {}

    def wants(self, artifact: Artifact) -> bool:
        return bool(SESSION_RX.match(artifact.rel) or META_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        m = META_RX.match(artifact.rel)
        if m:
            yield from self._parse_meta(artifact, m.group(1), opts)
            return
        session = read_session(artifact.disk_path)
        h = session.header
        if not h:
            if session.errors and not session.entries:
                yield error_row(self, artifact, session.errors)
            return
        sid = str(h.get("id") or "")
        cwd = str(h.get("cwd") or "")
        parent = str(h.get("parentSession") or "")

        row = self.base_row(artifact)
        row.source_line = session.header_line
        row.timestamp_utc = to_utc(h.get("timestamp"))
        row.session_id, row.project_path, row.turn_type = sid, cwd, "system"
        text = "session start: version=%s cwd=%s" % (h.get("version") or 1, cwd)
        if parent:
            text += " parentSession=%s" % parent
        row.text = compact(text, opts.max_text_length)
        yield row

        skip: Set[Tuple[str, str]] = set()
        if parent:
            pf = home_file(artifact, parent, ".pi/")
            if pf is not None and pf != artifact.disk_path:
                if pf not in self._parent_cache:
                    self._parent_cache[pf] = entry_keys(pf)
                skip = self._parent_cache[pf]
        dropped = 0
        if skip:
            dropped = sum(1 for _, r in session.entries
                          if (str(r.get("id") or ""), str(r.get("timestamp") or "")) in skip)
            if dropped:
                row = self.base_row(artifact)
                row.source_line = session.header_line
                row.timestamp_utc = to_utc(h.get("timestamp"))
                row.session_id, row.project_path, row.turn_type = sid, cwd, "system"
                row.text = compact("fork: %d entries copied from the parent session %s omitted; "
                                   "they are in the parent's rows" % (dropped, parent), opts.max_text_length)
                yield row

        yield from entry_rows(self, artifact, session, opts, sid, cwd, skip if dropped else None)

        why = little_coder_markers(artifact, session)
        if why:
            row = self.base_row(artifact)
            row.source_line = session.header_line
            row.timestamp_utc = to_utc(h.get("timestamp"))
            row.session_id, row.project_path, row.turn_type = sid, cwd, "system"
            row.text = compact("session driven by little-coder (pi launcher): %s" % "; ".join(why),
                               opts.max_text_length)
            yield row
        if session.errors:
            yield error_row(self, artifact, session.errors, sid, cwd)

    def _parse_meta(self, artifact: Artifact, sid: str, opts: Options) -> Iterator[Row]:
        row = self.base_row(artifact)
        row.session_id, row.turn_type, row.source_line = sid, "system", 1
        try:
            with open(artifact.disk_path, "rb") as fh:
                meta = json.loads(fh.read().decode("utf-8", errors="replace"))
        except ValueError as e:
            row.text = "parser: %s" % e
            yield row
            return
        if not isinstance(meta, dict):
            meta = {}
        row.timestamp_utc = to_utc(meta.get("createdAt"))
        row.project_path = str(meta.get("cwd") or "")
        row.text = compact("experimental durable session created: cwd=%s (transcript in session.sqlite, "
                           "not parsed)" % row.project_path, opts.max_text_length)
        yield row


def little_coder_markers(artifact: Artifact, session: SessionFile) -> List[str]:
    """Why a pi session looks driven by little-coder, empty when it does not."""
    types: Dict[str, None] = {}
    llamacpp = False
    for _, rec in session.entries:
        if rec.get("type") == "custom_message":
            ct = str(rec.get("customType") or "")
            if ct.startswith("lc-"):
                types.setdefault(ct)
        elif rec.get("type") == "message":
            msg = rec.get("message")
            if isinstance(msg, dict) and msg.get("role") == "assistant" and msg.get("provider") == "llamacpp":
                llamacpp = True
    why = []
    if types:
        why.append("custom_message types " + ", ".join(types))
    if llamacpp:
        why.append("assistant provider llamacpp")
    ck = artifact.home.disk_path / ".little-coder" / "checkpoints" / os.path.basename(artifact.rel)
    if not ck.is_symlink() and ck.is_dir():
        why.append("checkpoints in ~/.little-coder/checkpoints/%s" % ck.name)
    return why
