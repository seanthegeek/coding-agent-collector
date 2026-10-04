"""Timestamp normalisation. Every timestamp the analyzer emits is UTC ISO 8601
with millisecond precision and a trailing Z, so rows from different agents
sort together."""
from __future__ import annotations

import re
from datetime import datetime, timezone

OUT_FMT = "%Y-%m-%dT%H:%M:%S.%f"
_FRACTION_RX = re.compile(r"(\.\d{7,})")


def to_utc(value: str | int | float | None) -> str:
    """Return a canonical UTC string for an ISO 8601 string or an epoch number.

    Epoch values above 1e11 are taken as milliseconds (Claude Code's
    history.jsonl), below as seconds (Codex's history.jsonl). Unparseable
    input returns an empty string rather than raising, so one bad record
    never aborts a timeline.
    """
    if value is None or value == "":
        return ""
    try:
        if isinstance(value, bool):
            return ""
        if isinstance(value, (int, float)):
            return _from_epoch(float(value))
        s = str(value).strip()
        if s.replace(".", "", 1).isdigit():
            return _from_epoch(float(s))
        if s.endswith("Z") or s.endswith("z"):
            s = s[:-1] + "+00:00"
        # SQLite CURRENT_TIMESTAMP text and nanosecond fractions (Go) are not
        # accepted by fromisoformat before Python 3.11.
        if len(s) > 10 and s[10] == " ":
            s = s[:10] + "T" + s[11:]
        s = _FRACTION_RX.sub(lambda m: m.group(1)[:7], s)
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return _fmt(dt.astimezone(timezone.utc))
    except (ValueError, OverflowError, OSError):
        return ""


def _from_epoch(n: float) -> str:
    if n > 1e11:
        n = n / 1000.0
    return _fmt(datetime.fromtimestamp(n, tz=timezone.utc))


def _fmt(dt: datetime) -> str:
    return dt.strftime(OUT_FMT)[:-3] + "Z"


def first_nonempty(*values: str | None) -> str:
    for v in values:
        if v:
            return v
    return ""
