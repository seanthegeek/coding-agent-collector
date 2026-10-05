# Output

What `detect` prints, the files `timeline` writes, and the
`timeline.jsonl` and `sessions.jsonl` schemas. Back to the
[analyzer README](../README.md).

## detect

`detect` prints the input, its kind (`archive`, `collected` for an extracted
collection, or `loose`), the host, any notes, and one line per user, home
and agent with the number of files, their bytes (from the manifest `size`,
or from disk in loose mode), and whether a parser exists. The notes cover the
archive hash check, unreadable `collection.json`, manifest rows that do not
parse, and how a loose root was interpreted. One `problem:` line follows the
notes for each directory or file inside the input that could not be read
(see [Unreadable inputs](inputs.md#unreadable-inputs)). `--files` adds one
`user<TAB>agent<TAB>path` line per attributed file. With `--json` the same
data is printed as one object with the keys `input`, `kind`, `host`,
`notes`, `homes` (`user`, `home`, `inferred`), `agents` (`user`, `home`,
`agent`, `files`, `bytes`, `parser`, `inferred`), `problems` (an array of
the problem line texts, without the `problem:` prefix), and with `--files`
also `files` (`user`, `agent`, `path`). Collections made by collectors before
1.6.0 also hold a `live/` system snapshot, which appears as agent `live`
with no user, and `detect only`.

## timeline

`timeline` writes three files into `-o`, creating the directory if needed,
and writes them even when no rows were produced:

```text
timeline.jsonl  one record per turn, tool call, tool result or system event
sessions.jsonl  one record per session with first and last timestamp and counts
detect.json     the detect --json object without its homes and files keys; its
                problems also hold the files a parser could not read
```

On stdout it prints the input, host and notes, one `problem:` line per
directory or file that could not be read (see
[Unreadable inputs](inputs.md#unreadable-inputs)), and, when the timeline
is filtered, a `window:` line with the resolved UTC bounds, a `match:`
line with the patterns, and a `filtered:` line counting the rows dropped
outside the window, without a timestamp, and not matching. Then come the agents parsed and the agents only
detected, the row count with a breakdown by agent and `turn_type`, and the
session count. The agents parsed are those that produced rows before
filtering; the breakdown counts the rows written.

## JSONL encoding

Both JSONL files are UTF-8 without a byte order mark, one JSON object per
line, each line ended by LF, with no header line. Every object has every
field, in the order listed below. Fields with no value hold the empty string
`""`, never `null`, and every field is a string except the integers
`source_line`, `user_turns`, `assistant_turns` and `tool_calls` and the
array `models`. A line holds no literal line break: newlines inside
`text` are written as `\n`, and U+2028 and U+2029 as `\u2028` and
`\u2029`, because some line readers split on them. Other non-ASCII text is
written as UTF-8, not escaped, so a search for it matches as typed; the
exception is a record whose text holds a lone UTF-16 surrogate, which UTF-8
cannot encode, and which is written entirely with `\uXXXX` escapes.
There is no space after `:` or `,`, the same layout `jq -c` prints, so a
`grep` pattern such as `"agent":"codex-cli"` matches the file and jq output
alike. [searching.md](searching.md) has recipes.

## timeline.jsonl

`timeline.jsonl` fields, in order:

| Field | Meaning |
| --- | --- |
| `timestamp_utc` | ISO 8601 UTC with milliseconds, `2026-10-03T16:55:31.123Z`. Times recorded without a zone are taken as UTC. Epoch numbers above 10^11 are read as milliseconds, smaller ones as seconds. Empty when the record has none. |
| `host` | From `collection.json`, or `--host`. Empty for loose input without `--host`. |
| `user` | From the manifest, inferred from the path, or `--user`. |
| `agent` | Catalog agent name of the parser that produced the row. |
| `session_id` | The agent's own session or thread identifier. |
| `project_path` | Working directory recorded for the turn. |
| `git_branch` | Branch recorded for the turn, where the agent logs one. |
| `turn_type` | `user`, `assistant`, `tool_use`, `tool_result`, `system`, or `thinking` with `--include-thinking`. |
| `model` | Model that produced the turn, where recorded. |
| `tool_name` | For `tool_use` rows: the tool. Codex shell calls are `shell`. |
| `tool_use_id` | Links a `tool_use` row to its `tool_result`. |
| `text` | The event's full text, with leading and trailing whitespace removed and inner line breaks and indentation kept: the prompt, the response, the tool output, or for a tool call its most identifying argument (the Bash command, the edited file, the search pattern, the fetched URL), else the arguments as JSON. |
| `source_file` | Path of the record on the source host, as in the manifest. In loose mode it is the path relative to the input root with a leading `/`, or relative to the home when the input root is the home or an agent directory. |
| `source_line` | Integer. Where the record is in that file, so the full record can be read. For line-oriented files (JSONL, Markdown, text) the 1-based line number. For SQLite stores it is the record's `rowid` (Tabby events: the event id), and for JSON documents an array index or `1`. Each parser's module docstring says which. `0` when no position applies. |

### Row order and system rows

Rows are sorted by timestamp, then by source file and line. Rows without a
timestamp sort last. Injected context is typed `system`, not `user`, so
the `user` rows are what the person typed. In Claude Code that is
`isMeta` records, task notifications, slash commands and their output, a
subagent's task, compaction summaries and messages from other agents. In
Codex it is `developer` messages and user-role blocks whose content kind
names harness context rather than `user.*` input, or, in older rollouts
without content kinds, a block that is wholly a harness wrapper such as
`<environment_context>`. These `system` rows start with a lowercase label
naming the source, such as `subagent task:`, `task notification:`,
`slash command:`, `command output:` or `context: <kind>:`, followed by the
full text. A line a parser cannot decode, such as a
transcript's last line cut off mid-write, is reported as a `system` row,
and the rest of the file is still read.

## sessions.jsonl

`sessions.jsonl` has one record per `host`, `user`, `agent` and
`session_id`, built from the timeline records that have a session id. Its
fields, in order: `host`, `user`, `agent`, `session_id`, `project_path`
(the first non-empty one), `first_timestamp_utc`, `last_timestamp_utc`,
`models` (an array of strings, in order of first use, empty when none was
recorded), `user_turns` and `assistant_turns` (integers, timeline records
of those types), `tool_calls` (integer, `tool_use` records), and
`source_file` (the file that contributed the most records). It is sorted by
first timestamp, so sessions with no timestamp come first.

## Compatibility

The two JSONL layouts are a compatibility contract with the analysts and
tooling that consume them. A future version may append new fields after the
existing ones, but existing fields keep their names, order, type and
meaning.
