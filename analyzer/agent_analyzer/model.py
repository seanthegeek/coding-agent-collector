"""Output schema. `timeline.csv` and `sessions.csv` are interfaces that
analysts build on; add columns at the end, never rename or remove them
without a README note."""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Dict, List, Optional

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

    def as_list(self) -> List[object]:
        return [getattr(self, c) for c in TIMELINE_COLUMNS]


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
    models: Dict[str, None] = field(default_factory=dict)
    user_turns: int = 0
    assistant_turns: int = 0
    tool_calls: int = 0
    source_file: str = ""
    _sources: Dict[str, int] = field(default_factory=dict)

    def add(self, row: Row) -> None:
        # The session's source is the file that contributed most rows, so a
        # transcript wins over the one-line-per-prompt history file.
        if row.source_file:
            self._sources[row.source_file] = self._sources.get(row.source_file, 0) + 1
            self.source_file = max(self._sources, key=self._sources.get)
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

    def as_list(self) -> List[object]:
        return [
            self.host, self.user, self.agent, self.session_id, self.project_path,
            self.first_timestamp_utc, self.last_timestamp_utc, " ".join(self.models),
            self.user_turns, self.assistant_turns, self.tool_calls, self.source_file,
        ]


def summarise(rows: List[Row]) -> List[SessionSummary]:
    out: Dict[tuple, SessionSummary] = {}
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


def compact(text: Optional[object], limit: int) -> str:
    """One-line text, optionally length-capped. Whitespace runs collapse so the
    CSV stays one row per record; the full content is at source_file:line."""
    if text is None:
        return ""
    s = text if isinstance(text, str) else str(text)
    s = " ".join(s.split())
    if limit and len(s) > limit:
        s = s[: limit - 1] + "…"
    return s
