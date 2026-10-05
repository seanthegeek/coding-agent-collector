"""Output schema. `timeline.jsonl` and `sessions.jsonl` are interfaces that
analysts build on; add fields at the end, never rename or remove them
without a README note."""

from __future__ import annotations

from dataclasses import dataclass, field, fields

TIMELINE_COLUMNS = [
    "timestamp_utc",
    "host",
    "user",
    "agent",
    "session_id",
    "project_path",
    "git_branch",
    "turn_type",
    "model",
    "tool_name",
    "tool_use_id",
    "text",
    "source_file",
    "source_line",
]

TURN_TYPES = ("user", "assistant", "tool_use", "tool_result", "system", "thinking")

SESSION_COLUMNS = [
    "host",
    "user",
    "agent",
    "session_id",
    "project_path",
    "first_timestamp_utc",
    "last_timestamp_utc",
    "models",
    "user_turns",
    "assistant_turns",
    "tool_calls",
    "source_file",
]


@dataclass
class Row:
    timestamp_utc: str = ""
    host: str = ""
    user: str = ""
    agent: str = ""
    session_id: str = ""
    project_path: str = ""
    git_branch: str = ""
    turn_type: str = ""
    model: str = ""
    tool_name: str = ""
    tool_use_id: str = ""
    text: str = ""
    source_file: str = ""
    source_line: int = 0

    def as_dict(self) -> dict[str, object]:
        return {c: getattr(self, c) for c in TIMELINE_COLUMNS}


assert [f.name for f in fields(Row)] == TIMELINE_COLUMNS


@dataclass
class SessionSummary:
    host: str
    user: str
    agent: str
    session_id: str
    project_path: str = ""
    first_timestamp_utc: str = ""
    last_timestamp_utc: str = ""
    models: dict[str, None] = field(default_factory=dict)
    user_turns: int = 0
    assistant_turns: int = 0
    tool_calls: int = 0
    source_file: str = ""
    _sources: dict[str, int] = field(default_factory=dict)

    def add(self, row: Row) -> None:
        # The session's source is the file that contributed most rows, so a
        # transcript wins over the one-line-per-prompt history file.
        if row.source_file:
            self._sources[row.source_file] = self._sources.get(row.source_file, 0) + 1
            self.source_file = max(self._sources, key=self._sources.__getitem__)
        if row.timestamp_utc:
            if not self.first_timestamp_utc or row.timestamp_utc < self.first_timestamp_utc:
                self.first_timestamp_utc = row.timestamp_utc
            if row.timestamp_utc > self.last_timestamp_utc:
                self.last_timestamp_utc = row.timestamp_utc
        if row.model:
            self.models.setdefault(row.model)
        if not self.project_path and row.project_path:
            self.project_path = row.project_path
        if row.turn_type == "user":
            self.user_turns += 1
        elif row.turn_type == "assistant":
            self.assistant_turns += 1
        elif row.turn_type == "tool_use":
            self.tool_calls += 1

    def as_dict(self) -> dict[str, object]:
        return {
            "host": self.host,
            "user": self.user,
            "agent": self.agent,
            "session_id": self.session_id,
            "project_path": self.project_path,
            "first_timestamp_utc": self.first_timestamp_utc,
            "last_timestamp_utc": self.last_timestamp_utc,
            "models": list(self.models),
            "user_turns": self.user_turns,
            "assistant_turns": self.assistant_turns,
            "tool_calls": self.tool_calls,
            "source_file": self.source_file,
        }


def summarise(rows: list[Row]) -> list[SessionSummary]:
    out: dict[tuple, SessionSummary] = {}
    for r in rows:
        if not r.session_id:
            continue
        key = (r.host, r.user, r.agent, r.session_id)
        s = out.get(key)
        if s is None:
            s = SessionSummary(r.host, r.user, r.agent, r.session_id)
            out[key] = s
        s.add(r)
    return sorted(out.values(), key=lambda s: (s.first_timestamp_utc, s.agent, s.session_id))


def compact(text: object | None) -> str:
    """Event text with leading and trailing whitespace stripped. Inner
    newlines and indentation are kept: JSON escapes them, so each record
    still stays on one line of the JSONL output."""
    if text is None:
        return ""
    s = text if isinstance(text, str) else str(text)
    return s.strip()
