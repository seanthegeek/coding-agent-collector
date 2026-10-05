"""Row filters for `timeline`: a time window (`--since`, `--until`) and text
patterns (`--match`).

A --since or --until value is one of the forms below, after surrounding
whitespace is trimmed; day words, units, "ago", Z and UTC may be in any
case. Anything else is an error that lists the forms; nothing is guessed. A value without an
explicit offset is UTC, like the timeline.

Absolute times, parsed by python-dateutil's strict ISO 8601 parser
(`dateutil.parser.isoparse`):
  2026-10-01                      a date
  2026-10-01T09:30                date and time; seconds are optional and
  2026-10-01 09:30:15             may carry a fraction; a space may replace
  2026-10-01T09:30:15.250         the T
  2026-10-01T09:30Z               a UTC offset directly after the time:
  2026-10-01T09:30+02:00          Z, +HH:MM, +HHMM or +HH (- for west of
  2026-10-01T09:30-0500           UTC)
  2026-10-01 09:30 +02:00         the same offset after one space, and the
  2026-10-01 09:30 UTC            word UTC for Z
  2026-10, 2026                   a month or a year
  20261001T0930, 2026-W40-1,      the other ISO 8601 forms isoparse reads:
  2026-274                        basic format, week dates, ordinal dates
  1759312800                      epoch seconds; a number above 10^11 is
                                  milliseconds

Day words, in the UTC calendar:
  today, yesterday                that day
  now                             the current time, exactly

Relative times, counted back from now with `dateutil.relativedelta`, with
or without a space between number and unit and with or without a trailing
"ago":
  45m, 45min, 45 minutes          minutes (m is always minutes)
  36h, 36 hours                   hours
  3d, 3 days                      days
  2w, 2 weeks                     weeks
  6mo, 6 months                   calendar months (mo is months)
  1y, 1 year                      calendar years
Months and years move the calendar date and keep the time of day; a day
that does not exist in the target month becomes that month's last day
(31 March less 1mo is 28 February).

An absolute value names a period as long as its last written unit: 2026 a
year, 2026-10 a month, a date (and today, yesterday) a day, 09 an hour,
09:30 a minute, 09:30:15 a second; a value with a fraction of a second is
an instant. --since takes the period's first millisecond and --until its
last, so `--since 2026-10-01 --until 2026-10-01` selects that day and
`--until "2026-10-01 09:30"` keeps an event at 09:30:40. now, relative
times and epoch numbers are instants.

Bounds are canonical UTC strings in the timeline's own format, so a row is
kept by a plain string comparison: since <= timestamp_utc <= until.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from dateutil.parser import isoparse
from dateutil.relativedelta import relativedelta

from .model import Row
from .timeutil import format_utc, to_utc

FORMS_HELP = (
    "accepted: ISO 8601 such as 2026-10-01, 2026-10-01T09:30[:SS][Z|+HH:MM] or "
    "2026-10-01 09:30[:SS] [+HH:MM|UTC]; 2026-10 or 2026; epoch seconds; today, yesterday, now; "
    "or a relative time such as 45m, 36h, 3d, 2w, 6mo, 1y, optionally followed by 'ago'"
)

_YEAR_RX = re.compile(r"^\d{4}$")
_MONTH_RX = re.compile(r"^\d{4}-\d{2}$")
# The time of day after the T or space, extended (09:30:15) or basic
# (093015) format, to find the precision the value was written to.
_TIME_RX = re.compile(r"\d[T ](\d{2})(?::?(\d{2})(?::?(\d{2})(\.\d+)?)?)?", re.IGNORECASE)
# dateutil messages worth passing on; the rest describe its internals.
_RANGE_MSG_RX = re.compile(r"must be in|invalid hours|invalid minutes|out of range", re.IGNORECASE)
# An offset after a space, which isoparse does not accept; it is moved onto
# the time before parsing.
_SPACED_OFFSET_RX = re.compile(r"^(.*\d) (z|utc|[+-]\d{2}(?::?\d{2})?)$", re.IGNORECASE)
_EPOCH_RX = re.compile(r"^\d{9,}(\.\d+)?$")
_RELATIVE_RX = re.compile(
    r"^(\d+) ?(m|min|mins|minutes?|h|hours?|d|days?|w|weeks?|mo|months?|y|years?)(?: ago)?$",
    re.IGNORECASE,
)
_UNIT = {
    "m": "minutes", "min": "minutes", "mins": "minutes", "minute": "minutes", "minutes": "minutes",
    "h": "hours", "hour": "hours", "hours": "hours",
    "d": "days", "day": "days", "days": "days",
    "w": "weeks", "week": "weeks", "weeks": "weeks",
    "mo": "months", "month": "months", "months": "months",
    "y": "years", "year": "years", "years": "years",
}  # fmt: skip


class BoundError(ValueError):
    """A --since or --until value that is not one of the accepted forms."""


def parse_bound(text: str, end: bool = False, now: datetime | None = None) -> str:
    """Return the canonical UTC string for a --since (`end` False) or
    --until (`end` True) value in one of the forms in the module docstring.
    A value naming a whole period gives its first millisecond for --since
    and its last for --until."""
    s = " ".join(text.split())
    low = s.lower()
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if low == "now":
        return format_utc(now)
    if low in ("today", "yesterday"):
        day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if low == "yesterday":
            day -= timedelta(days=1)
        return _bound(day, timedelta(days=1), end)
    m = _RELATIVE_RX.match(s)
    if m:
        n = {u: 0 for u in _UNIT.values()}
        n[_UNIT[m.group(2).lower()]] = int(m.group(1))
        try:
            ago = relativedelta(
                years=n["years"],
                months=n["months"],
                weeks=n["weeks"],
                days=n["days"],
                hours=n["hours"],
                minutes=n["minutes"],
            )
            return format_utc(now - ago)
        except (ValueError, OverflowError):
            raise BoundError("%r is out of range" % text) from None
    if _EPOCH_RX.match(s):
        out = to_utc(s)
        if not out:
            raise BoundError("%r is out of range as epoch seconds or milliseconds" % text)
        return out
    m = _SPACED_OFFSET_RX.match(s)
    if m:
        offset = m.group(2)
        s = m.group(1) + ("Z" if offset.lower() == "utc" else offset)
    try:
        dt = isoparse(s)
    except (ValueError, OverflowError) as e:
        reason = " (%s)" % e if _RANGE_MSG_RX.search(str(e)) else ""
        raise BoundError("cannot read %r as a time%s; %s" % (text, reason, FORMS_HELP)) from None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    t = _TIME_RX.search(s)
    if t:
        _hour, minute, second, fraction = t.groups()
        if fraction:
            return format_utc(dt)
        if second:
            return _bound(dt, timedelta(seconds=1), end)
        if minute:
            return _bound(dt, timedelta(minutes=1), end)
        return _bound(dt, timedelta(hours=1), end)
    if _YEAR_RX.match(s):
        return _bound(dt, relativedelta(years=1), end)
    if _MONTH_RX.match(s):
        return _bound(dt, relativedelta(months=1), end)
    return _bound(dt, timedelta(days=1), end)


def _bound(start: datetime, length, end: bool) -> str:
    """The first millisecond of the period, or with `end` its last."""
    if end:
        return format_utc(start + length - timedelta(milliseconds=1))
    return format_utc(start)


@dataclass
class RowFilter:
    since: str = ""
    until: str = ""
    keep_undated: bool = False
    patterns: list[re.Pattern] = field(default_factory=list)
    dropped_window: int = 0
    dropped_undated: int = 0
    dropped_match: int = 0

    @property
    def active(self) -> bool:
        return bool(self.since or self.until or self.patterns)

    def in_window(self, row: Row) -> bool:
        if not (self.since or self.until):
            return True
        ts = row.timestamp_utc
        if not ts:
            if not self.keep_undated:
                self.dropped_undated += 1
            return self.keep_undated
        if (self.since and ts < self.since) or (self.until and ts > self.until):
            self.dropped_window += 1
            return False
        return True

    def apply(self, rows: list[Row]) -> list[Row]:
        """Rows inside the window that match a pattern. A matched tool_use
        keeps its tool_result, and a matched result its call, by session and
        tool_use_id, when the partner is inside the window too."""
        kept = [r for r in rows if self.in_window(r)]
        if not self.patterns:
            return kept
        hit = [any(p.search(r.text) for p in self.patterns) for r in kept]
        pairs = {
            (r.session_id, r.source_file if not r.session_id else "", r.tool_use_id)
            for r, h in zip(kept, hit, strict=True)
            if h and r.tool_use_id
        }
        out = []
        for r, h in zip(kept, hit, strict=True):
            key = (r.session_id, r.source_file if not r.session_id else "", r.tool_use_id)
            if h or (r.tool_use_id and key in pairs):
                out.append(r)
            else:
                self.dropped_match += 1
        return out
