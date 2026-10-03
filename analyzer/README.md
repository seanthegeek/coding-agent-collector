# Analyzer

The analyst-side half of coding-agent-collector. It takes a collector archive,
an extracted collection, or any loose directory tree, detects which AI coding
agents left state in it, and parses the transcripts it knows how to read into
one normalised CSV timeline. It never runs on the host under investigation, so
unlike the collectors it may carry dependencies. Today it needs only Python
3.9 or later and the standard library.

## Quick start

```sh
cd analyzer

# What is in this collection?
python3 -m agent_analyzer detect /cases/host01/host01_20261003T165531Z_agent-artifacts.tar.gz

# Build the timeline
python3 -m agent_analyzer timeline /cases/host01/host01_*.tar.gz -o /cases/host01/analysis

# A home directory copied off a host by other means, or a mounted image
python3 -m agent_analyzer timeline /mnt/evidence -o /cases/host02/analysis --host host02

# A single agent directory copied on its own
python3 -m agent_analyzer detect /cases/host03/alice-dot-claude --user alice
```

`pip install .` in this directory installs the same thing as the
`analyze-agent-artifacts` command.

## Inputs

| Input | How it is read |
| --- | --- |
| `*_agent-artifacts.tar.gz` or `.zip` from either collector | Extracted to a temporary directory (or `--work-dir`), then read as an extracted collection. A `.sha256` sidecar next to the archive is verified and the result reported. Symlinks inside the archive are not materialised; their targets are in the manifest. |
| Extracted collection: a directory holding `manifest.jsonl`, `collection.json` and `fs/` | Host name from `collection.json`; user, home and agent for every file from the manifest. Only rows with status `collected` are parsed. |
| Anything else | Treated as a loose tree: a copied home directory, a mounted disk image, another collector's output, or one agent directory such as `.claude`. Homes and agents are discovered from the catalog, and the user is inferred from the path. |

In loose mode the analyzer walks the tree and treats a directory as a home
when at least one catalog entry for a real agent matches under it. A
directory that holds only shared files such as `AGENTS.md` or `.env` is a
project, not a home. A home is never nested inside another, so project-level
`.claude` directories inside a home are not mistaken for a second user. The
user is taken from `home/<user>`, `Users/<user>`, `usr/home/<user>`,
`export/home/<user>`, `root` or `var/root` in the path, falling back to the
directory name, and left empty when the input root itself is the home. Pass
`--user` and `--host` to fill in what the path cannot say. Loose-mode output
is marked `inferred` in `detect --json` because none of this comes from a
manifest.

## Detection

Detection uses the collectors' own catalog. `agent_analyzer/catalog.txt` is a
verbatim copy of `collect-agent-artifacts.sh --list`; the catalog drift test
in `collectors/tests/catalog-sync.sh` and the analyzer's own test suite both
fail when it is stale. Regenerate it with:

```sh
collectors/collect-agent-artifacts.sh --list > analyzer/agent_analyzer/catalog.txt
```

Every agent the collectors know is therefore detected, whether or not a
parser exists for it. When two entries match the same file, the more specific
one wins, so Antigravity CLI state under `.gemini/antigravity-cli` is
attributed to `antigravity`, not to the enclosing `gemini-cli` entry, in both
loose mode and the collectors' manifests. `python3 -m agent_analyzer catalog --agents` lists the
agents and which have parsers.

## Parsers

| Agent | Files | Validated against |
| --- | --- | --- |
| `claude-code` | `.claude/projects/<slug>/<session>.jsonl`, subagent transcripts under the session directory, `.claude/history.jsonl` | Real install, Claude Code 2.x, October 2026 |
| `codex-cli` | `.codex/sessions/**/rollout-*.jsonl`, `.codex/history.jsonl` | Real install, Codex CLI, October 2026 |

The field names each parser relies on are listed in its module docstring
under `agent_analyzer/parsers/`. Thinking and reasoning blocks are left out
unless `--include-thinking` is passed. History files are parsed even when the
matching session transcript exists, because they survive session deletion;
filter on `source_file` to drop them.

Agents detected but not yet parsed: everything else in the catalog. Gemini
CLI, Qwen Code, Cline, Roo Code, Continue, Copilot Chat, Goose, OpenCode, Zed
and Kiro are open source and next in line. Antigravity, Windsurf and Cursor
need format work first.

## Output

`timeline` writes three files into `-o`:

```
timeline.csv    one row per turn, tool call, tool result or system event
sessions.csv    one row per session with first and last timestamp and counts
detect.json     what detect would have printed, for the record
```

`timeline.csv` columns, in order:

| Column | Meaning |
| --- | --- |
| `timestamp_utc` | ISO 8601 UTC with milliseconds, `2026-10-03T16:55:31.123Z`. Empty when the record has none. |
| `host` | From `collection.json`, or `--host`. |
| `user` | From the manifest, inferred from the path, or `--user`. |
| `agent` | Catalog agent name. |
| `session_id` | The agent's own session or thread identifier. |
| `project_path` | Working directory recorded for the turn. |
| `git_branch` | Branch recorded for the turn, where the agent logs one. |
| `turn_type` | `user`, `assistant`, `tool_use`, `tool_result`, `system`, or `thinking` with `--include-thinking`. |
| `model` | Model that produced the turn, where recorded. |
| `tool_name` | For `tool_use` rows: the tool. Codex shell calls are `shell`. |
| `tool_use_id` | Links a `tool_use` row to its `tool_result`. |
| `summary` | The prompt, response, command, file path or output, whitespace collapsed and cut to `--summary-length` characters (default 400, `0` for unlimited). For tool calls it is the most identifying argument: the Bash command, the edited file, the search pattern, the fetched URL. Everything else is JSON. |
| `source_file` | Path of the record on the source host, as in the manifest. In loose mode it is relative to the input root. |
| `source_line` | Line number in that file, so the full record can be read. |

Rows are sorted by timestamp, then by source file and line. Rows without a
timestamp sort last. Injected context (`isMeta` user records in Claude Code,
`developer` messages in Codex) is typed `system`, not `user`, so the `user`
rows are what the person typed.

`sessions.csv` columns: `host`, `user`, `agent`, `session_id`,
`project_path`, `first_timestamp_utc`, `last_timestamp_utc`, `models`
(space separated), `user_turns`, `assistant_turns`, `tool_calls`,
`source_file` (the file that contributed most rows).

Both CSVs are interfaces. Columns are only added, at the end.

## Options

| Option | Meaning |
| --- | --- |
| `detect INPUT` | Print homes, users, agents, file counts and whether a parser exists. `--json` for machine-readable output, `--files` to list every attributed file. |
| `timeline INPUT -o DIR` | Write `timeline.csv`, `sessions.csv` and `detect.json`. |
| `catalog` | Print the bundled catalog; `--agents` prints agent names and parser availability. |
| `--host NAME` | Host to record when the input has no `collection.json`. |
| `--user NAME` | User to record for a home whose owner cannot be inferred. |
| `--work-dir DIR` | Where to extract an archive. Default is a temporary directory. |
| `--keep-extracted` | Keep the extracted archive and print its path. |
| `--summary-length N` | Cap on the `summary` column. Default 400, `0` disables. |
| `--include-thinking` | Emit thinking and reasoning blocks as `thinking` rows. |
| `--agent NAME` | Parse only this agent. Repeatable. |

Exit code is `0` when rows were written, `1` when nothing was found or
parsed, `2` for a bad input path.

## Testing

```sh
cd analyzer
tests/run.sh                 # python3 -m unittest discover -s tests
```

The suite builds a fake image with two Linux users and a Windows profile
tree, each holding synthetic Claude Code and Codex state in the exact shapes
the parsers were validated against, and checks detection in every input mode,
each parser's rows, the CSV output, and the bundled catalog against the
collector's `--list`. When `sh` and `tar` are available it also runs the sh
collector on the fake image and analyses the resulting archive end to end.

## Adding a parser

1. Confirm the record format against source or a real install and write the
   field names into the module docstring, as the two existing parsers do.
2. Subclass `Parser` in `agent_analyzer/parsers/<agent>.py`: set `agent` to
   the catalog name, implement `wants` on `artifact.rel` and `parse` yielding
   `Row` objects. Use `iter_jsonl` so a truncated line is reported, not fatal.
   Timestamps go through `to_utc`; text through `compact`.
3. Register it in `agent_analyzer/parsers/__init__.py`.
4. Add fixture records to `tests/fixtures.py` and a test class to
   `tests/test_parsers.py`. Then add the row to the table above.

## License

Copyright 2026 Sean Whalen. Licensed under the Apache License, Version 2.0.
See [LICENSE](../LICENSE).
