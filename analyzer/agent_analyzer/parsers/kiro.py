"""Amazon Q Developer CLI conversations, the open-source predecessor of the
Kiro CLI (catalog agent `kiro`).

Validated against the source of aws/amazon-q-developer-cli at 15cc8f3
(1.19.7, `crates/chat-cli`), with a synthetic fixture; see
`analyzer/research/kiro.md`. No real install was used. Files, relative to
the home directory:

* `data.sqlite3` under `.local/share/amazon-q/`, `Library/Application
  Support/amazon-q/` or `AppData/Local/amazon-q/`, and the same three under
  `kiro-cli/` (the rebrand; those directories are from the catalog and not
  verified from source). Rollback journal, not WAL. Tables read:
  - `conversations(key, value)`: one row per working directory. `key` is the
    cwd, `value` is the serialised `ConversationState` below. Only the
    latest conversation per directory survives.
  - `history(command, shell, pid, session_id, cwd, start_time | time,
    end_time, duration, hostname, exit_code)`: legacy Fig shell history with
    no writer in the current source; old installs may hold rows. Each row
    becomes a `system` row prefixed `shell history:` since it records a
    shell command, not an agent turn. `session_id` is the shell session.
  - `auth_kv` and `state` hold tokens and are never read.
* Saved `/save` exports anywhere under the agent's directories: a `.json`
  file whose top-level object has `conversation_id` and `history`, the same
  `ConversationState` schema pretty-printed.

`ConversationState` fields used: `conversation_id`, `history[]`,
`next_message`, `latest_summary` (`[text, RequestMetadata]`),
`model_info.model_id`, legacy `model`. Each history entry is `{user,
assistant, request_metadata}`:

  - `user.content` is `{"Prompt": {prompt}}`, `{"ToolUseResults":
    {tool_use_results}}` or `{"CancelledToolUses": {prompt,
    tool_use_results}}`; each result is `{tool_use_id, content: [{"Text"} |
    {"Json"}], status}`. `user.timestamp` is RFC 3339 with the local offset
    or null; `user.env_context.env_state.current_working_directory`.
  - `assistant` is `{"Response": {message_id, content}}` or `{"ToolUse":
    {message_id, content, tool_uses: [{id, name, orig_name, args}]}}`.
  - `request_metadata`: `request_start_timestamp_ms`,
    `stream_end_timestamp_ms`, `model_id`, `message_meta_tags`.

Rows: `user` per prompt; `tool_result` per tool use result (text suffixed
with the status, and `cancelled` for CancelledToolUses), named by looking up
the id among earlier tool uses; `assistant` per response text; `tool_use`
per `tool_uses[]` entry with `name` as the tool name and the JSON `args` as
the text (prefixed `orig_name=` when the MCP original name differs);
`system` rows for a `Compact` meta tag, the `latest_summary` and a pending
`next_message`. There are no thinking blocks in this format.

Timestamps: user and tool_result rows use `user.timestamp`, which is null
on tool-result messages; they fall back to the same entry's
`request_start_timestamp_ms`. Assistant and tool_use rows use
`stream_end_timestamp_ms`, then `request_start_timestamp_ms`. Entries with
neither (old releases without `request_metadata`) inherit the previous
row's timestamp. `project_path` is the database row key, else the first
`current_working_directory`. No git branch is recorded.

A blob or export that fails to parse as a whole (an export truncated
mid-write) is salvaged entry by entry: the history entries before the cut
are still yielded, followed by one `system` row.

Not parsed: Kiro CLI's `.kiro/sessions/` files. That closed-source format is
unverified (the research suggests the camelCase `crates/agent` schema, but
that is inference), so `wants()` ignores it until the format is confirmed
from a shipped binary or a real install. The Kiro IDE stores are not parsed
either.
"""
from __future__ import annotations

import json
import re
from typing import Dict, Iterator, List, Optional, Tuple

from ..inputs import Artifact
from ..model import Row, compact
from ..sqlite_util import is_sqlite, open_copy, table_names
from ..timeutil import to_utc
from .base import Options, Parser, compact_json

DB_RX = re.compile(
    r"^(?:\.local/share|Library/Application Support|AppData/Local)/(?:amazon-q|kiro-cli)/data\.sqlite3$")
SESSIONS_RX = re.compile(r"^\.kiro/sessions/")
SNIFF_BYTES = 4096

_CONV_ID_RX = re.compile(r'"conversation_id"\s*:\s*"((?:[^"\\]|\\.)*)"')
_HISTORY_RX = re.compile(r'"history"\s*:\s*\[')


def _sniff_export(path) -> bool:
    try:
        with open(path, "rb") as fh:
            head = fh.read(SNIFF_BYTES)
    except OSError:
        return False
    return head.lstrip()[:1] == b"{" and b'"conversation_id"' in head


def salvage(text: str) -> Tuple[Optional[dict], str]:
    """Parse a ConversationState. On failure, recover `conversation_id` and
    every complete `history` entry before the damage; the second value is the
    error message, empty when the whole document parsed."""
    try:
        state = json.loads(text)
        if isinstance(state, dict):
            return state, ""
        return None, "not a JSON object"
    except ValueError as e:
        err = str(e)
    m = _HISTORY_RX.search(text)
    if not m:
        return None, err
    state = {"history": []}
    cid = _CONV_ID_RX.search(text, 0, m.start())
    if cid:
        try:
            state["conversation_id"] = json.loads('"%s"' % cid.group(1))
        except ValueError:
            pass
    dec = json.JSONDecoder()
    i = m.end()
    n = len(text)
    while i < n:
        while i < n and text[i] in " \t\r\n,":
            i += 1
        if i >= n or text[i] == "]":
            break
        try:
            entry, i = dec.raw_decode(text, i)
        except ValueError:
            break
        if isinstance(entry, dict):
            state["history"].append(entry)
    return state, err


def _variant(value) -> Tuple[str, dict]:
    """Unpack a serde externally tagged enum: {"Tag": {...}}."""
    if isinstance(value, dict) and len(value) == 1:
        tag, body = next(iter(value.items()))
        return str(tag), body if isinstance(body, dict) else {}
    return "", {}


def result_text(result: dict) -> str:
    parts: List[str] = []
    for block in result.get("content") or []:
        if not isinstance(block, dict):
            parts.append(str(block))
        elif isinstance(block.get("Text"), str):
            parts.append(block["Text"])
        elif "Json" in block:
            parts.append(compact_json(block["Json"]))
        else:
            parts.append(compact_json(block))
    text = "\n".join(parts)
    status = result.get("status")
    if status:
        text = "%s [%s]" % (text, status) if text else "[%s]" % status
    return text


class KiroParser(Parser):
    agent = "kiro"
    name = "kiro"

    def wants(self, artifact: Artifact) -> bool:
        rel = artifact.rel
        if DB_RX.match(rel):
            return True
        if SESSIONS_RX.match(rel) or not rel.endswith(".json"):
            return False
        return _sniff_export(artifact.disk_path)

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if DB_RX.match(artifact.rel):
            yield from self._parse_db(artifact, opts)
        else:
            yield from self._parse_export(artifact, opts)

    # -- data.sqlite3 -------------------------------------------------------------
    def _parse_db(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if not is_sqlite(artifact.disk_path):
            return
        with open_copy(artifact.disk_path) as con:
            tables = table_names(con)
            if "conversations" in tables:
                for n, r in enumerate(con.execute("select key, value from conversations order by rowid"), 1):
                    value = r["value"]
                    if isinstance(value, bytes):
                        value = value.decode("utf-8", errors="replace")
                    yield from self._conversation(artifact, opts, str(value or ""), str(r["key"] or ""), n)
            if "history" in tables:
                yield from self._shell_history(artifact, opts, con)

    def _shell_history(self, artifact: Artifact, opts: Options, con) -> Iterator[Row]:
        for n, r in enumerate(con.execute("select * from history order by rowid"), 1):
            r = dict(r)
            row = self.base_row(artifact)
            row.source_line = n
            start = r.get("start_time") if "start_time" in r else r.get("time")
            row.timestamp_utc = to_utc(start)
            row.session_id = str(r.get("session_id") or "")
            row.project_path = str(r.get("cwd") or "")
            row.turn_type = "system"
            extras = ["%s=%s" % (k, r[k]) for k in ("exit_code", "shell", "hostname", "duration")
                      if r.get(k) not in (None, "")]
            text = "shell history: %s" % (r.get("command") or "")
            if extras:
                text += " (%s)" % " ".join(extras)
            row.text = compact(text, opts.max_text_length)
            yield row

    # -- /save exports ------------------------------------------------------------
    def _parse_export(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        with open(artifact.disk_path, "rb") as fh:
            text = fh.read().decode("utf-8", errors="replace")
        yield from self._conversation(artifact, opts, text, "", 0)

    # -- ConversationState --------------------------------------------------------
    def _conversation(self, artifact: Artifact, opts: Options, text: str, key: str, line: int) -> Iterator[Row]:
        state, err = salvage(text)
        if state is None or not isinstance(state.get("history"), list):
            if err:
                row = self.base_row(artifact)
                row.source_line = line
                row.project_path = key
                row.turn_type = "system"
                row.text = "parser: unparseable conversation: %s" % err
                yield row
            return
        session_id = str(state.get("conversation_id") or "")
        info = state.get("model_info")
        conv_model = ""
        if isinstance(info, dict) and info.get("model_id"):
            conv_model = str(info["model_id"])
        elif isinstance(state.get("model"), str):
            conv_model = state["model"]
        project = key or self._first_cwd(state)
        names: Dict[str, str] = {}
        last_ts = [""]

        def base(ts: str, model: str = "") -> Row:
            row = self.base_row(artifact)
            row.source_line = line
            if ts:
                last_ts[0] = ts
            row.timestamp_utc = ts or last_ts[0]
            row.session_id = session_id
            row.project_path = project
            row.model = model
            return row

        def fill(row: Row, s: str) -> Row:
            row.text = compact(s, opts.max_text_length)
            return row

        for entry in state["history"]:
            if not isinstance(entry, dict):
                continue
            meta = entry.get("request_metadata")
            meta = meta if isinstance(meta, dict) else {}
            model = str(meta.get("model_id") or conv_model)
            start_ts = to_utc(meta.get("request_start_timestamp_ms"))
            end_ts = to_utc(meta.get("stream_end_timestamp_ms")) or start_ts
            user = entry.get("user")
            if isinstance(user, dict):
                user_ts = to_utc(user.get("timestamp")) or start_ts
                yield from self._user(user.get("content"), user_ts, model, names, base, fill)
            assistant = entry.get("assistant")
            tag, body = _variant(assistant)
            if tag in ("Response", "ToolUse"):
                content = body.get("content")
                if content:
                    yield self._assistant(base(end_ts, model), content, fill)
                for use in body.get("tool_uses") or []:
                    if not isinstance(use, dict):
                        continue
                    tid = str(use.get("id") or "")
                    tname = str(use.get("name") or use.get("orig_name") or "")
                    names[tid] = tname
                    row = base(end_ts, model)
                    row.turn_type = "tool_use"
                    row.tool_name = tname
                    row.tool_use_id = tid
                    args = use.get("args")
                    s = args if isinstance(args, str) else compact_json(args)
                    orig = use.get("orig_name")
                    if orig and orig != tname:
                        s = "orig_name=%s %s" % (orig, s)
                    yield fill(row, s)
            tags = meta.get("message_meta_tags") or []
            if isinstance(tags, list) and "Compact" in tags:
                row = base(end_ts, model)
                row.turn_type = "system"
                yield fill(row, "compact: conversation history summarised")

        summary = state.get("latest_summary")
        if isinstance(summary, list) and summary:
            smeta = summary[1] if len(summary) > 1 and isinstance(summary[1], dict) else {}
            ts = to_utc(smeta.get("stream_end_timestamp_ms")) or to_utc(smeta.get("request_start_timestamp_ms"))
            row = base(ts, str(smeta.get("model_id") or ""))
            row.turn_type = "system"
            yield fill(row, "summary: %s" % (summary[0] if isinstance(summary[0], str) else compact_json(summary[0])))

        pending = state.get("next_message")
        if isinstance(pending, dict):
            tag, body = _variant(pending.get("content"))
            prompt = body.get("prompt") if tag in ("Prompt", "CancelledToolUses") else None
            row = base(to_utc(pending.get("timestamp")))
            row.turn_type = "system"
            yield fill(row, "pending message (not sent): %s" % (prompt or compact_json(pending.get("content"))))

        if err:
            row = self.base_row(artifact)
            row.source_line = line
            row.session_id = session_id
            row.project_path = project
            row.turn_type = "system"
            row.text = "parser: truncated conversation, %d history entries recovered: %s" % (
                len(state["history"]), err)
            yield row

    @staticmethod
    def _assistant(row: Row, content, fill) -> Row:
        row.turn_type = "assistant"
        return fill(row, content if isinstance(content, str) else compact_json(content))

    @staticmethod
    def _user(content, ts: str, model: str, names: Dict[str, str], base, fill) -> Iterator[Row]:
        tag, body = _variant(content)
        prompt = body.get("prompt")
        if tag in ("Prompt", "CancelledToolUses") and prompt:
            row = base(ts, model)
            row.turn_type = "user"
            yield fill(row, prompt)
        if tag in ("ToolUseResults", "CancelledToolUses"):
            for result in body.get("tool_use_results") or []:
                if not isinstance(result, dict):
                    continue
                row = base(ts, model)
                row.turn_type = "tool_result"
                row.tool_use_id = str(result.get("tool_use_id") or "")
                row.tool_name = names.get(row.tool_use_id, "")
                s = result_text(result)
                if tag == "CancelledToolUses":
                    s = "cancelled %s" % s if s else "cancelled"
                yield fill(row, s)

    @staticmethod
    def _first_cwd(state: dict) -> str:
        for entry in state.get("history") or []:
            try:
                cwd = entry["user"]["env_context"]["env_state"]["current_working_directory"]
            except (KeyError, TypeError):
                continue
            if cwd:
                return str(cwd)
        return ""
