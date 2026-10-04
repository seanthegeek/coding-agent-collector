"""OpenHands conversations (Agent Canvas, Agent Server and the `openhands` CLI).

Validated against source, OpenHands/software-agent-sdk at b347047 and
OpenHands/OpenHands at 7fbb48c (0.62.0, legacy layout), with a synthetic
fixture; no real install was used. See `analyzer/research/openhands.md`.

Files, relative to the home directory (the same layout on every OS):

* `.openhands/agent-canvas/dev_conversations/<hex>/`,
  `.openhands/agent-canvas/conversations/<hex>/` and
  `.openhands/conversations/<hex>/`, one directory per conversation named by
  its UUID as 32 hex digits. Each artifact is one event file,
  `events/event-<idx, 5+ digits>-<event id>.json`, holding one JSON object.
  Fields read: `kind`, `id`, `timestamp`, `source`, and per kind:
  - `MessageEvent`: `llm_message.{role, content[] ({type:"text", text} or
    {type:"image"}), tool_calls[].{id, name or function.name, arguments},
    tool_call_id, reasoning_content, thinking_blocks[].thinking}`.
  - `ActionEvent`: `thought[]`, `reasoning_content`, `thinking_blocks[]`,
    `action.{kind, command, path}`, `tool_name`, `tool_call_id`,
    `tool_call.arguments`.
  - `ObservationEvent`: `tool_name`, `tool_call_id`, `observation.{content[],
    is_error}`; `UserRejectObservation`: `rejection_reason`,
    `rejection_source`; `AgentErrorEvent`: `error`.
  - `ACPToolCallEvent`: `tool_call_id`, `title`, `status`, `tool_kind`,
    `raw_input`, `raw_output`, `content`, `is_error`.
  - `SystemPromptEvent`: `system_prompt`, `tools`; `Condensation` and
    `CondensationSummaryEvent`: `summary`, `forgotten_event_ids`;
    `HookExecutionEvent`: `hook_event_type`, `hook_command`, `exit_code`,
    `blocked`, `stderr`; `ConversationStateUpdateEvent`: `key`, `value`.
  The sibling files of the conversation directory are read once per
  conversation: `meta.json` (`id`, `title`, `created_at`,
  `parent_conversation_id`, `forked_from_conversation_id`,
  `workspace.working_dir`) and `base_state.json` (`agent.llm.model`,
  `workspace.working_dir`). Their `secrets`, `api_key` and
  `secret_registry` fields are never read, and `settings.json`,
  `secrets.json` and `profiles/*.json` are never opened.
* Legacy 0.x `.openhands/sessions/<sid>/events/<n>.json` and
  `.openhands/users/<uid>/conversations/<sid>/events/<n>.json`: detected and
  reported as one `system` row per session (on the lowest-numbered event
  file), not parsed. The 1.x `v1_conversations/` tree and `bash_events/`
  are not read.

Timestamps. Event `timestamp` is `datetime.now().isoformat()`, naive host
local time. When `meta.json` has a UTC `created_at`, the host's offset is
taken as the difference between the first event's naive time (the lowest
index in `events/`) and `created_at`, floored to the quarter hour after
allowing one minute of clock skew, so a first event written up to 14
minutes after creation still gives the right offset; it is applied to every
event of that conversation. Without `meta.json` (the CLI does not write one)
the naive times are emitted as if they were UTC, as the Aider parser does.
The conversation's header row says which was done. An event timestamp that
does carry a zone is converted as is.

Rows. The first event file of a conversation also yields one `system`
header row (title, parent or fork, model, timestamp basis). `MessageEvent`
rows take their type from `llm_message.role` (`tool` is `tool_result`),
with any `tool_calls` as `tool_use` rows; `ActionEvent` and
`ACPToolCallEvent` are `tool_use` (an ACP call that has output also yields a
`tool_result`); `ObservationEvent`, `UserRejectObservation` and
`AgentErrorEvent` are `tool_result` joined on `tool_call_id`; everything else
is `system`. Thoughts, `reasoning_content` and thinking blocks become
`thinking` rows with `--include-thinking`. The session id is the directory
name, `project_path` is `workspace.working_dir` from `meta.json`, else from
`base_state.json` (a container path under Canvas in Docker), and the model
is `agent.llm.model`. No git branch is recorded. `source_line` is 1, since
every file holds one object.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, text_of

EVENT_RX = re.compile(
    r"^\.openhands/(?:agent-canvas/(?:dev_)?conversations|conversations)/"
    r"([0-9a-fA-F]{32})/events/event-(\d{5,})-[0-9a-fA-F-]{8,}\.json$"
)
EVENT_NAME_RX = re.compile(r"^event-(\d{5,})-[0-9a-fA-F-]{8,}\.json$")
LEGACY_RX = re.compile(
    r"^\.openhands/(?:sessions|users/[^/]+/conversations)/([^/]+)/events/(\d+)\.json$"
)

QUARTER = 900
SKEW = 60
MAX_OFFSET = 14 * 3600


def _d(value) -> dict:
    return value if isinstance(value, dict) else {}


def _join(*parts: str) -> str:
    return " | ".join(p for p in parts if p)


def _read_json(path: Path):
    try:
        if path.is_symlink() or not path.is_file():
            return None
        with open(path, "rb") as fh:
            return json.loads(fh.read().decode("utf-8", errors="replace"))
    except (OSError, ValueError):
        return None


def _aware(value) -> datetime | None:
    """A UTC datetime from a string `to_utc` accepts, else None."""
    s = to_utc(value) if isinstance(value, str) else ""
    if not s:
        return None
    return datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)


def _naive(value) -> datetime | None:
    """A naive datetime when the timestamp has no zone, else None."""
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(re.sub(r"(\.\d{6})\d+", r"\1", value.strip()))
    except ValueError:
        return None
    return dt if dt.tzinfo is None else None


def _fmt_offset(seconds: int) -> str:
    sign = "+" if seconds >= 0 else "-"
    seconds = abs(seconds)
    return "UTC%s%02d:%02d" % (sign, seconds // 3600, seconds % 3600 // 60)


@dataclass
class _Conv:
    session_id: str
    project_path: str = ""
    model: str = ""
    offset: int | None = None  # seconds east of UTC, when anchored
    first_event: str = ""  # file name of the lowest-index event
    header: str = ""
    created: str = ""


class OpenHandsParser(Parser):
    agent = "openhands"
    name = "openhands"

    def __init__(self) -> None:
        self._cache: dict[tuple, _Conv] = {}

    def wants(self, artifact: Artifact) -> bool:
        return bool(EVENT_RX.match(artifact.rel) or LEGACY_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if LEGACY_RX.match(artifact.rel):
            yield from self._parse_legacy(artifact, opts)
            return
        conv = self._conversation(artifact.disk_path.parent.parent)
        if artifact.disk_path.name == conv.first_event:
            row = self._row(artifact, conv, "system")
            row.timestamp_utc = conv.created
            row.text = compact(conv.header, opts.max_text_length)
            yield row
        ev = _read_json(artifact.disk_path)
        if not isinstance(ev, dict):
            row = self._row(artifact, conv, "system")
            row.text = "parser: event file could not be decoded"
            yield row
            return
        ts = self._timestamp(ev.get("timestamp"), conv)
        for row in self._event_rows(artifact, conv, ev, opts):
            row.timestamp_utc = ts
            yield row

    # -- conversation context ---------------------------------------------------------
    def _conversation(self, cdir: Path) -> _Conv:
        def mtime(p: Path) -> int:
            try:
                return p.stat().st_mtime_ns
            except OSError:
                return 0

        key = (
            str(cdir),
            mtime(cdir / "meta.json"),
            mtime(cdir / "base_state.json"),
            mtime(cdir / "events"),
        )
        conv = self._cache.get(key)
        if conv is None:
            conv = self._load_conversation(cdir)
            if len(self._cache) > 256:
                self._cache.clear()
            self._cache[key] = conv
        return conv

    def _load_conversation(self, cdir: Path) -> _Conv:
        meta = _d(_read_json(cdir / "meta.json"))
        state = _d(_read_json(cdir / "base_state.json"))
        conv = _Conv(session_id=cdir.name)
        conv.project_path = str(
            _d(meta.get("workspace")).get("working_dir")
            or _d(state.get("workspace")).get("working_dir")
            or ""
        )
        conv.model = str(_d(_d(state.get("agent")).get("llm")).get("model") or "")

        events: list[tuple[int, str]] = []
        try:
            for p in (cdir / "events").iterdir():
                m = EVENT_NAME_RX.match(p.name)
                if m and not p.is_symlink():
                    events.append((int(m.group(1)), p.name))
        except OSError:
            pass
        events.sort()
        conv.first_event = events[0][1] if events else ""
        first = _d(_read_json(cdir / "events" / conv.first_event)) if events else {}

        created = _aware(meta.get("created_at"))
        naive_first = _naive(first.get("timestamp"))
        if created is not None and naive_first is not None:
            diff = (naive_first.replace(tzinfo=timezone.utc) - created).total_seconds()
            offset = int((diff + SKEW) // QUARTER) * QUARTER
            if abs(offset) <= MAX_OFFSET:
                conv.offset = offset
        if created is not None:
            conv.created = to_utc(meta.get("created_at"))
        else:
            conv.created = self._timestamp(first.get("timestamp"), conv)

        if conv.offset is not None:
            basis = (
                "event times are host local, corrected by %s from meta.json created_at"
                % _fmt_offset(conv.offset)
            )
        elif naive_first is not None:
            basis = "event times are host local with no zone, emitted as if UTC"
        else:
            basis = ""
        conv.header = _join(
            "conversation start",
            str(meta.get("title") or ""),
            "id=%s" % meta["id"] if meta.get("id") else "",
            "parent=%s" % meta["parent_conversation_id"]
            if meta.get("parent_conversation_id")
            else "",
            "forked_from=%s" % meta["forked_from_conversation_id"]
            if meta.get("forked_from_conversation_id")
            else "",
            "model=%s" % conv.model if conv.model else "",
            "status=%s" % state["execution_status"] if state.get("execution_status") else "",
            "%d events" % len(events),
            basis,
        )
        return conv

    @staticmethod
    def _timestamp(value, conv: _Conv) -> str:
        naive = _naive(value)
        if naive is not None and conv.offset is not None:
            return to_utc((naive - timedelta(seconds=conv.offset)).isoformat() + "+00:00")
        return to_utc(value) if isinstance(value, str) else ""

    def _row(self, artifact: Artifact, conv: _Conv, turn_type: str) -> Row:
        row = self.base_row(artifact)
        row.session_id = conv.session_id
        row.project_path = conv.project_path
        row.model = conv.model
        row.turn_type = turn_type
        row.source_line = 1
        return row

    # -- events -----------------------------------------------------------------------
    def _event_rows(
        self, artifact: Artifact, conv: _Conv, ev: dict, opts: Options
    ) -> Iterator[Row]:
        kind = str(ev.get("kind") or "")

        def mk(turn_type: str, text: str, tool_name: str = "", tool_use_id: str = "") -> Row:
            row = self._row(artifact, conv, turn_type)
            row.tool_name, row.tool_use_id = tool_name, tool_use_id
            row.text = compact(text, opts.max_text_length)
            return row

        if kind == "MessageEvent":
            msg = _d(ev.get("llm_message"))
            role = str(msg.get("role") or ev.get("source") or "")
            if opts.include_thinking:
                thinking = _thinking(msg)
                if thinking:
                    yield mk("thinking", thinking)
            text = text_of(msg.get("content"))
            if role == "tool":
                yield mk(
                    "tool_result",
                    text,
                    str(msg.get("name") or ""),
                    str(msg.get("tool_call_id") or ""),
                )
            elif text or role in ("user", "system"):
                yield mk(role if role in ("user", "assistant", "system") else "system", text)
            for call in msg.get("tool_calls") or []:
                call = _d(call)
                fn = _d(call.get("function"))
                yield mk(
                    "tool_use",
                    str(call.get("arguments") or fn.get("arguments") or ""),
                    str(call.get("name") or fn.get("name") or ""),
                    str(call.get("id") or ""),
                )
        elif kind == "ActionEvent":
            if opts.include_thinking:
                thinking = _join(text_of(ev.get("thought")), _thinking(ev))
                if thinking:
                    yield mk("thinking", thinking)
            yield mk(
                "tool_use",
                _action_text(ev),
                str(ev.get("tool_name") or ""),
                str(ev.get("tool_call_id") or ""),
            )
        elif kind == "ObservationEvent":
            obs = _d(ev.get("observation"))
            text = text_of(obs.get("content"))
            if obs.get("is_error"):
                text = "[error] " + text
            yield mk(
                "tool_result",
                text,
                str(ev.get("tool_name") or ""),
                str(ev.get("tool_call_id") or ""),
            )
        elif kind == "UserRejectObservation":
            yield mk(
                "tool_result",
                "[rejected by %s] %s"
                % (ev.get("rejection_source") or "user", ev.get("rejection_reason") or ""),
                str(ev.get("tool_name") or ""),
                str(ev.get("tool_call_id") or ""),
            )
        elif kind == "AgentErrorEvent":
            yield mk(
                "tool_result",
                "[error] %s" % (ev.get("error") or ""),
                str(ev.get("tool_name") or ""),
                str(ev.get("tool_call_id") or ""),
            )
        elif kind == "ACPToolCallEvent":
            name, call_id = str(ev.get("tool_kind") or "acp"), str(ev.get("tool_call_id") or "")
            raw_in = ev.get("raw_input")
            yield mk(
                "tool_use",
                _join(
                    str(ev.get("title") or ""), compact_json(raw_in) if raw_in is not None else ""
                ),
                name,
                call_id,
            )
            out = ev.get("raw_output")
            out_text = _join(
                out if isinstance(out, str) else compact_json(out) if out is not None else "",
                text_of(ev.get("content")) if isinstance(ev.get("content"), list) else "",
            )
            if out_text or ev.get("status") in ("completed", "failed"):
                if ev.get("is_error") or ev.get("status") == "failed":
                    out_text = "[error] " + out_text
                yield mk("tool_result", out_text, name, call_id)
        elif kind == "SystemPromptEvent":
            tools = ev.get("tools")
            yield mk(
                "system",
                "system prompt, %d tools: %s"
                % (len(tools) if isinstance(tools, list) else 0, text_of(ev.get("system_prompt"))),
            )
        elif kind in ("Condensation", "CondensationSummaryEvent"):
            forgotten = ev.get("forgotten_event_ids")
            yield mk(
                "system",
                _join(
                    "%s:" % kind,
                    "%d events forgotten" % len(forgotten) if isinstance(forgotten, list) else "",
                    str(ev.get("summary") or ""),
                ),
            )
        elif kind == "HookExecutionEvent":
            yield mk(
                "system",
                _join(
                    "hook %s: %s" % (ev.get("hook_event_type") or "", ev.get("hook_command") or ""),
                    "exit=%s" % ev["exit_code"] if ev.get("exit_code") is not None else "",
                    "blocked" if ev.get("blocked") else "",
                    str(ev.get("stderr") or ""),
                ),
            )
        elif kind == "ConversationStateUpdateEvent":
            # The full_state value is a whole ConversationState, secrets
            # included; only its key is reported.
            value = ev.get("value")
            shown = (
                ""
                if isinstance(value, (dict, list)) or ev.get("key") == "full_state"
                else str(value)
            )
            yield mk(
                "system", "state update: %s%s" % (ev.get("key") or "", "=" + shown if shown else "")
            )
        else:
            rest = {
                k: v
                for k, v in ev.items()
                if k not in ("kind", "id", "timestamp", "source", "parent_id")
            }
            yield mk("system", _join("%s:" % (kind or "event"), compact_json(rest) if rest else ""))

    # -- legacy 0.x ---------------------------------------------------------------------
    def _parse_legacy(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        m = LEGACY_RX.match(artifact.rel)
        assert m is not None  # parse() routes only matching paths here
        mine = int(m.group(2))
        numbers = []
        try:
            for p in artifact.disk_path.parent.iterdir():
                if p.suffix == ".json" and p.stem.isdigit() and not p.is_symlink():
                    numbers.append(int(p.stem))
        except OSError:
            pass
        if numbers and mine != min(numbers):
            return
        ev = _d(_read_json(artifact.disk_path))
        row = self.base_row(artifact)
        row.session_id = m.group(1)
        row.turn_type = "system"
        row.source_line = 1
        row.timestamp_utc = (
            to_utc(ev.get("timestamp")) if isinstance(ev.get("timestamp"), str) else ""
        )
        row.text = compact(
            "legacy OpenHands 0.x session, %d event files, not parsed; "
            "times are host local, emitted as if UTC" % len(numbers),
            opts.max_text_length,
        )
        yield row


def _thinking(rec: dict) -> str:
    parts = []
    if isinstance(rec.get("reasoning_content"), str):
        parts.append(rec["reasoning_content"])
    for b in rec.get("thinking_blocks") or []:
        if isinstance(b, dict) and isinstance(b.get("thinking"), str):
            parts.append(b["thinking"])
    return _join(*parts)


def _action_text(ev: dict) -> str:
    """The command for a terminal action, `<command> <path>` for a file
    editor action, else the call's JSON arguments."""
    action = _d(ev.get("action"))
    cmd, path = action.get("command"), action.get("path")
    if isinstance(path, str) and path:
        return "%s %s" % (cmd, path) if isinstance(cmd, str) and cmd else path
    if isinstance(cmd, str) and cmd:
        return cmd
    args = _d(ev.get("tool_call")).get("arguments")
    if isinstance(args, str) and args:
        return args
    rest = {k: v for k, v in action.items() if k != "kind"}
    return compact_json(rest) if rest else str(action.get("kind") or "")
