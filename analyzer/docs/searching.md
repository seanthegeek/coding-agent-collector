# Reading and searching the output

Recipes for reading and searching a large `timeline.jsonl` or
`sessions.jsonl` with jq, grep, DuckDB, Python and PowerShell.
Back to the [analyzer README](../README.md).

A timeline from a busy host can run to gigabytes, because `text` holds full
tool output. Each line is one complete record, so the tools below stream
the file line by line and use little memory however large it is. The
examples run in the `-o` directory. A spreadsheet is the wrong viewer for
these files: Excel stops at 1,048,576 rows and 32,767 characters per cell.
Export a filtered, shortened subset to CSV instead, as shown at the end of
the jq examples.

**jq** (<https://jqlang.org>) reads one record at a time. Never pass `-s`
(slurp) on a large file, which loads the whole file into memory.

```sh
# Look at one record, pretty-printed
head -n 1 timeline.jsonl | jq .

# Record counts by agent and turn type
jq -r '[.agent, .turn_type] | @tsv' timeline.jsonl | sort | uniq -c | sort -rn

# Tool calls of one tool, with a few fields
jq -c 'select(.turn_type == "tool_use" and .tool_name == "Bash") | {timestamp_utc, user, text}' timeline.jsonl

# Case-insensitive regular expression over the text
jq -c 'select(.text | test("curl|wget|base64 -d"; "i")) | [.timestamp_utc, .agent, .turn_type, .text[0:120]]' timeline.jsonl

# One session as a readable transcript; line breaks in text are printed as line breaks
jq -r --arg s SESSION_ID 'select(.session_id == $s) | "\(.timestamp_utc)  \(.turn_type)  \(.tool_name)\n\(.text)\n"' timeline.jsonl | less

# A tool call and its result. IDs such as call_1 repeat across agents and
# sessions, so match the session too
jq -c --arg s SESSION_ID --arg id TOOL_USE_ID 'select(.session_id == $s and .tool_use_id == $id)' timeline.jsonl

# Sessions with more than 20 tool calls, and their models
jq -r 'select(.tool_calls > 20) | [.first_timestamp_utc, .user, .agent, .session_id, .tool_calls, (.models | join(" "))] | @tsv' sessions.jsonl

# A CSV for a spreadsheet: filter first, and cut text to 200 characters
jq -r 'select(.agent == "codex-cli") | [.timestamp_utc, .host, .user, .agent, .session_id, .turn_type, .tool_name, .text[0:200]] | @csv' timeline.jsonl > codex.csv
```

**grep first, then jq.** `grep -F` and `rg -F` scan text many times faster
than jq parses JSON, so use them to cut a large file down and jq to check
the field. A grep match can come from any field, so always confirm with a
`select` on the field you meant. Write patterns as the record stores them:
`"turn_type":"tool_use"` without spaces, a quote inside text as `\"`, a
backslash as `\\`, and a line break as the two characters `\n`.

```sh
grep -F '"turn_type":"tool_use"' timeline.jsonl | jq -r .tool_name | sort | uniq -c | sort -rn
rg -F 'aws_secret_access_key' timeline.jsonl | jq -c '{timestamp_utc, user, agent, source_file, source_line}'
```

**Split or compress.** One file per agent keeps each one small enough for an
editor, and gzip shrinks transcripts severalfold; `zcat` feeds jq and
`rg -z` searches the compressed file directly.

```sh
mkdir -p by-agent
jq -r .agent timeline.jsonl | sort -u | while read -r a; do
  jq -c --arg a "$a" 'select(.agent == $a)' timeline.jsonl > "by-agent/$a.jsonl"
done
gzip -k timeline.jsonl && zcat timeline.jsonl.gz | jq -c 'select(.agent == "codex-cli")'
```

**DuckDB** (<https://duckdb.org>) runs SQL over the file without an import
step, and keeps `session_id` a string even when it looks like a number.
`COPY` writes a filtered subset as CSV or Parquet.

```sql
SELECT agent, turn_type, count(*) AS n
FROM read_json_auto('timeline.jsonl') GROUP BY ALL ORDER BY n DESC;

SELECT timestamp_utc, user, agent, left(text, 120)
FROM read_json_auto('timeline.jsonl')
WHERE turn_type = 'tool_use' AND text ILIKE '%rm -rf%'
ORDER BY timestamp_utc;

COPY (SELECT * FROM read_json_auto('timeline.jsonl') WHERE agent = 'codex-cli')
TO 'codex.csv' (HEADER);
```

**Python.** Read line by line for a file of any size, or load it into
pandas when it fits in memory. pandas parses `timestamp_utc` as a datetime
by default; `chunksize` reads a large file in pieces.

```python
import json

with open("timeline.jsonl", encoding="utf-8") as fh:
    for line in fh:
        rec = json.loads(line)
        if rec["turn_type"] == "tool_use" and "curl" in rec["text"]:
            print(rec["timestamp_utc"], rec["agent"], rec["text"])

import pandas as pd

df = pd.read_json("timeline.jsonl", lines=True)
for chunk in pd.read_json("timeline.jsonl", lines=True, chunksize=100_000):
    print(chunk[chunk.turn_type == "tool_use"].tool_name.value_counts())
```

**Filtering by time afterwards.** `timestamp_utc` always has one fixed
form, `2026-10-03T16:55:31.123Z`, so plain string comparison puts times in
the right order and needs no date parsing in any tool. The `--since` and
`--until` options ([filtering.md](filtering.md)) do this while writing the
timeline; these recipes do it on a timeline already written.

```sh
# Everything on 1 October 2026 (UTC)
jq -c 'select(.timestamp_utc >= "2026-10-01" and .timestamp_utc < "2026-10-02")' timeline.jsonl

# A window to the second
jq -c 'select(.timestamp_utc >= "2026-10-01T10:00:00.000Z" and .timestamp_utc < "2026-10-01T10:05:00.000Z")' timeline.jsonl

# Sessions that overlap a day
jq -c 'select(.last_timestamp_utc >= "2026-10-01" and .first_timestamp_utc < "2026-10-02")' sessions.jsonl
```

```sql
SELECT * FROM read_json_auto('timeline.jsonl')
WHERE timestamp_utc >= '2026-10-01' AND timestamp_utc < '2026-10-02';
```

- Write a bound either as a date alone (`"2026-10-01"`) or in the full
  form with milliseconds and `Z`. `"2026-10-01T10:00:00Z"` without `.000`
  drops the records at exactly 10:00:00, because `.` sorts before `Z`.
- End a range with "before the next day", `< "2026-10-02"`. `<=
  "2026-10-01"` keeps almost nothing from that day, since every time on it
  sorts after the bare date.
- Records without a timestamp hold `""`, which never passes a lower bound,
  so they drop out. Add `or .timestamp_utc == ""` to keep them.
- Convert a local incident window to UTC before writing the bounds.
- In Python compare the strings directly (`"2026-10-01" <=
  rec["timestamp_utc"] < "2026-10-02"`). In Windows PowerShell 5.1 `-ge`
  and `-lt` compare the strings; PowerShell 7 first needs
  `ConvertFrom-Json -DateKind String`, as below.

**PowerShell**, for an analyst on Windows. `Select-String` as the first
filter keeps the slow `ConvertFrom-Json` step to the matching lines.
PowerShell 7 turns `timestamp_utc` into a local `DateTime`; add
`-DateKind String` (PowerShell 7.5 and later) to `ConvertFrom-Json` to keep
the UTC string. Windows PowerShell 5.1 keeps it a string.

```powershell
Select-String -Path timeline.jsonl -SimpleMatch '"agent":"codex-cli"' |
  ForEach-Object { $_.Line | ConvertFrom-Json } |
  Where-Object { $_.turn_type -eq 'tool_use' -and $_.text -match 'rm -rf' } |
  Select-Object timestamp_utc, user, tool_name, text
```
