# Filtering the timeline

The `--since`, `--until`, `--keep-undated` and `--match` options of
`timeline`, and the `WHEN` forms they accept.
Back to the [analyzer README](../README.md).

`timeline` can write only part of the timeline, which keeps the output of a
busy host to the incident window:

- `--since WHEN` and `--until WHEN` keep rows with `since <= timestamp_utc
  <= until`. Either may be given alone. Rows without a timestamp are
  dropped once either is given, unless `--keep-undated` is passed. Formats
  without per-message times (Continue, Zed, Cline's legacy history) give
  their rows the session's timestamp, so those rows are kept or dropped by
  the time the session started.
- `--match REGEX` keeps rows whose `text` matches the Python regular
  expression ([`re` syntax](https://docs.python.org/3/library/re.html),
  searched anywhere in the text, so anchor with `^` and `$` for a whole
  match). Repeat it to keep rows that match any of the patterns; `-i`
  makes every pattern case-insensitive. A matched `tool_use` row keeps its
  `tool_result` row, and a matched result its call, when the partner has
  the same `session_id` and `tool_use_id` (the same `source_file` for rows
  without a session id) and is inside the time window. Only `text` is
  searched; filter other fields with jq afterwards.
- `--match` applies after the time window. `sessions.jsonl` is summarised
  from the rows that are kept, so its counts and first and last timestamps
  describe the filtered timeline, not the whole session.

The resolved window is printed as a `window:` line, so a relative value
such as `3d` can be checked and recorded in case notes. A value that is not
one of the forms below, a `--since` later than the `--until`, or a
`--match` that is not a valid regular expression stops the command with
exit code `2` before the input is opened or extracted.

## WHEN forms

`WHEN` is one of the following, after surrounding whitespace is trimmed;
day words, units, `ago`, `Z` and `UTC` may be in any case. Nothing else is
accepted, and nothing is guessed. A value without an offset is UTC, like
the timeline.

| Form | Examples | Meaning |
| --- | --- | --- |
| ISO 8601 date | `2026-10-01`, basic `20261001`, week date `2026-W40-1`, ordinal `2026-274` | That day. |
| Year or month | `2026`, `2026-10` | That year or month. |
| Date and time, `T` or one space between them | `2026-10-01T09`, `2026-10-01T09:30`, `2026-10-01 09:30`, `2026-10-01 09:30:15`, `2026-10-01T09:30:15.250`, basic `20261001T093015` | Seconds are optional and may carry a fraction. |
| Date and time with a UTC offset, directly after the time or after one space | `2026-10-01T09:30Z`, `2026-10-01T09:30+02:00`, `2026-10-01T09:30-0500`, `2026-10-01T09:30+02`, `2026-10-01 09:30 +02:00`, `2026-10-01 09:30 UTC` | Offsets are `Z`, `UTC` (after a space only), `+HH:MM`, `+HHMM` or `+HH`; `-` is west of UTC. The time is converted to UTC. |
| Epoch number | `1759312800`, `1759312800000` | Seconds since 1970; a number above 10^11 is milliseconds. |
| Day word | `today`, `yesterday` | That UTC calendar day. |
| `now` | `now` | The current time. |
| Relative time | `45m`, `45min`, `45 minutes`, `36h`, `36 hours`, `3d`, `3 days ago`, `2w`, `6mo`, `6 months ago`, `1y`, `2 years` | That long before now. The space and a trailing `ago` are optional; units are `m`, `min`, `minute(s)` (minutes), `h`, `hour(s)`, `d`, `day(s)`, `w`, `week(s)`, `mo`, `month(s)`, `y`, `year(s)`. `m` is always minutes and `mo` always months. Months and years move the calendar date and keep the time of day; a day the target month lacks becomes its last day, so 31 March less `1mo` is 28 February (29 in a leap year). |

## Periods and instants

An absolute value or a day word names a period as long as its last written
unit: a year, a month, a day, an hour (`T09`), a minute (`09:30`) or a
second (`09:30:15`). `--since` takes the period's first millisecond and
`--until` its last, so `--since 2026-10-01 --until 2026-10-01` selects
that whole day, `--until 2026-10` runs to the end of October, and
`--until "2026-10-01 09:30"` keeps an event at 09:30:40. A time with a
fraction of a second, `now`, a relative time and an epoch number are
instants, used as they are. Dates and times are parsed by
`dateutil.parser.isoparse` and months and years counted by
`dateutil.relativedelta`, both from `python-dateutil`; the forms
themselves are defined in `agent_analyzer/filters.py`.
