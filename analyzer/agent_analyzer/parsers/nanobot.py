"""nanobot sessions and memory history.

Validated against source, HKUDS/nanobot at acdae3d (see
`analyzer/research/nanobot.md`), with a synthetic fixture; no real install
was checked. The state directory is `.nanobot`, or `.nanobot-<instance>`.
Files:

* `sessions/<workspace-id>/<stem>.jsonl`: one file per session key,
  `<workspace-id>` 32 hex characters, `<stem>` the URL-safe base64 of the
  key without padding. The sibling `sessions/<workspace-id>/.workspace`
  holds the workspace path, used as `project_path`. Legacy global
  `sessions/<key with ":" as "_">.jsonl` files (no `.workspace`) and
  `sessions/<workspace-id>/.migration-conflicts/*.jsonl` copies have the
  same format. Line 1 is `{"_type":"metadata", "key", "created_at",
  "updated_at", "metadata"}` (`metadata._nanobot_model_preset`,
  `metadata.last_channel`); an optional `{"_type":"provider_state"}` line
  is opaque and skipped; every other line is an OpenAI chat message:
  `role` (`user`, `assistant`, `tool`, `system`), `content` (string or
  `{type:"text", text}` blocks), `timestamp`, assistant `tool_calls[]`
  {`id`, `function`: {`name`, `arguments` (JSON string)}} and
  `reasoning_content`, tool `tool_call_id` and `name`, and the flags
  `_hidden_history` (a synthetic user message standing in for summarised
  history, emitted as `system`) and `_runtime_context` (context attached to
  a real user message, which stays `user`). `*.checkpoint.json` sidecars
  are volatile and not read.
* `memory/history.jsonl` under a nanobot directory (the default workspace
  is `.nanobot/workspace`): the compressed long-term journal, lines
  `{cursor, timestamp: "YYYY-MM-DD HH:MM", content, session_key?}`, each
  one `system` row with `session_id` the `session_key` and `project_path`
  the workspace holding `memory/`.

`session_id` is the metadata `key` (`<channel>:<chat_id>` names the
external sender, or `cli:direct`, `heartbeat`, `unified:default`), falling
back to the decoded file name. Every timestamp nanobot writes is naive host
local time (`datetime.now().isoformat()`), and the collection does not
record the host's zone, so they are emitted as if they were UTC, the same
convention as the Aider parser; correct them by the host's offset, which
`llm_usage.sqlite3` `llm_calls.started_at_ms` (true UTC) can give. Messages
without a timestamp inherit the previous one, else the metadata
`updated_at`. No model is recorded per message: the session's
`_nanobot_model_preset`, when set, is the `model` of every row. No git
branch is recorded. `/new` empties a session file, so earlier turns may
survive only in `memory/history.jsonl`.
"""

from __future__ import annotations

import base64
import re
from collections.abc import Iterator

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, iter_jsonl, text_of
from .openclaw import tool_args_text

STATE = r"\.nanobot(?:-[^/]+)?"
SESSION_RX = re.compile(
    r"^" + STATE + r"/sessions/(?:(?P<ws>[0-9a-f]{32})/(?:\.migration-conflicts/)?)?"
    r"(?P<stem>[^/]+)\.jsonl$"
)
HISTORY_RX = re.compile(r"^" + STATE + r"/(?:.+/)?memory/history\.jsonl$")
ORIGINAL_MEMORY_RX = re.compile(r"^(.*)[\\/]memory[\\/]history\.jsonl$")


def decode_stem(stem: str) -> str:
    """Session key from a file stem: URL-safe base64 without padding, or the
    legacy lossy `<channel>_<chat>` form returned unchanged."""
    try:
        key = base64.urlsafe_b64decode(stem + "=" * (-len(stem) % 4)).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return stem
    if base64.urlsafe_b64encode(key.encode("utf-8")).decode("ascii").rstrip("=") != stem:
        return stem
    return key


class NanobotParser(Parser):
    agent = "nanobot"
    name = "nanobot"

    def wants(self, artifact: Artifact) -> bool:
        return bool(SESSION_RX.match(artifact.rel) or HISTORY_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if SESSION_RX.match(artifact.rel):
            yield from self._parse_session(artifact, opts)
        else:
            yield from self._parse_history(artifact, opts)

    @staticmethod
    def _workspace(artifact: Artifact) -> str:
        marker = artifact.disk_path.parent / ".workspace"
        if not SESSION_RX.match(artifact.rel).group("ws"):
            return ""
        if artifact.disk_path.parent.name == ".migration-conflicts":
            marker = artifact.disk_path.parent.parent / ".workspace"
        try:
            if marker.is_symlink() or not marker.is_file():
                return ""
            return marker.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return ""

    def _parse_session(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        m = SESSION_RX.match(artifact.rel)
        session_id = decode_stem(m.group("stem"))
        project = self._workspace(artifact)
        model = ""
        last_ts = ""
        errors: list = []

        def row(
            n: int, turn_type: str, text: str, tool_name: str = "", tool_use_id: str = ""
        ) -> Row:
            r = self.base_row(artifact)
            r.source_line = n
            r.session_id = session_id
            r.project_path = project
            r.timestamp_utc = last_ts
            r.model = model
            r.turn_type = turn_type
            r.tool_name = tool_name
            r.tool_use_id = tool_use_id
            r.text = compact(text, opts.max_text_length)
            return r

        for n, rec in iter_jsonl(artifact.disk_path, errors):
            rtype = rec.get("_type")
            if rtype == "metadata":
                if rec.get("key"):
                    session_id = str(rec["key"])
                meta = rec.get("metadata") if isinstance(rec.get("metadata"), dict) else {}
                model = str(meta.get("_nanobot_model_preset") or "")
                last_ts = to_utc(rec.get("created_at")) or to_utc(rec.get("updated_at"))
                yield row(
                    n,
                    "system",
                    " ".join(
                        x
                        for x in (
                            "session start: key=%s" % session_id,
                            "last_channel=%s" % meta["last_channel"]
                            if meta.get("last_channel")
                            else "",
                            "updated_at=%s" % rec["updated_at"] if rec.get("updated_at") else "",
                            "workspace=%s" % project if project else "",
                        )
                        if x
                    ),
                )
                continue
            if rtype is not None and "role" not in rec:
                continue  # provider_state and future record types
            last_ts = to_utc(rec.get("timestamp")) or last_ts
            role = rec.get("role")
            text = text_of(rec.get("content"))
            if role == "user":
                if rec.get("_hidden_history"):
                    yield row(n, "system", "summarised history: " + text)
                else:
                    yield row(n, "user", text)
            elif role == "assistant":
                reasoning = rec.get("reasoning_content")
                if opts.include_thinking and isinstance(reasoning, str) and reasoning:
                    yield row(n, "thinking", reasoning)
                if text:
                    yield row(n, "assistant", text)
                for tc in rec.get("tool_calls") or []:
                    if not isinstance(tc, dict):
                        continue
                    fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
                    yield row(
                        n,
                        "tool_use",
                        tool_args_text(fn.get("arguments")),
                        str(fn.get("name") or ""),
                        str(tc.get("id") or ""),
                    )
            elif role == "tool":
                yield row(
                    n,
                    "tool_result",
                    text,
                    str(rec.get("name") or ""),
                    str(rec.get("tool_call_id") or ""),
                )
            else:
                yield row(n, "system", "%s: %s" % (role or "message", text))
        if errors:
            yield row(
                errors[0][0],
                "system",
                "parser: %d unparseable line(s), first at line %d" % (len(errors), errors[0][0]),
            )

    def _parse_history(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        m = ORIGINAL_MEMORY_RX.match(artifact.original or "")
        project = m.group(1) if m else ""
        errors: list = []
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            r = self.base_row(artifact)
            r.source_line = n
            r.session_id = str(rec.get("session_key") or "")
            r.project_path = project
            r.timestamp_utc = to_utc(rec.get("timestamp"))
            r.turn_type = "system"
            r.text = compact(
                "memory history #%s: %s" % (rec.get("cursor", ""), rec.get("content") or ""),
                opts.max_text_length,
            )
            yield r
        if errors:
            r = self.base_row(artifact)
            r.source_line = errors[0][0]
            r.project_path = project
            r.turn_type = "system"
            r.text = "parser: %d unparseable line(s), first at line %d" % (
                len(errors),
                errors[0][0],
            )
            yield r


__all__ = ["NanobotParser", "decode_stem"]
