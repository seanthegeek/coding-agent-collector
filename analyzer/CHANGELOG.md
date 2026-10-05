# Changelog

All notable changes to the analyzer are recorded here. The version is
printed by `--version`. Changes to the `timeline.jsonl` and
`sessions.jsonl` fields (`timeline.csv` and `sessions.csv` columns up to
0.7.0) are called out, since they are interfaces.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.8.1] - 2026-10-04

### Added

- `detect` prints `problem:` lines too, and `detect --json` and
  `detect.json` have a new last key `problems`, an array of the problem
  texts; in `detect.json` it also holds the files a parser could not read.

### Fixed

- An input that cannot be opened, including a missing path, an archive
  that is not readable, an archive inside a directory that cannot be
  traversed, an input directory that cannot be listed and an unreadable
  `manifest.jsonl`, now prints `error: <path>: <reason>` with the OS
  reason in lower case (`no such file or directory`, `permission denied`)
  and exits 2 under `detect`, `timeline` and `inventory`. Before, it
  printed only the path, or a Python traceback for permission errors. A
  corrupt or truncated archive prints `error: <path>: cannot extract:
  <reason>` instead of a traceback, and the extracted work directory is
  removed on every such error.
- A directory inside a loose tree that cannot be listed is now a
  `problem:` line instead of being skipped silently.
- A manifest row whose file is absent from the extracted collection is now
  one `problem:` line, `<original path>: missing from the collection`.
- Problem lines and the `collection.json unreadable` note name the path
  once: `<path>: permission denied` instead of
  `<path>: [Errno 13] Permission denied: '<path>'`. The Continue and Codex
  `parser: unreadable ...` system rows carry only the reason, since
  `source_file` names the file.

## [0.8.0] - 2026-10-04

### Added

- `timeline --since WHEN` and `--until WHEN` keep only the rows inside a
  UTC time window, `--keep-undated` also keeps rows without a timestamp,
  and `--match REGEX` (repeatable, `-i` for case-insensitive) keeps rows
  whose `text` matches, with the paired tool call or result. `WHEN` is an
  ISO 8601 date or time (a space may replace the `T`, and an offset may
  follow after a space), a year or month, an epoch number, `today`,
  `yesterday`, `now`, or a relative time such as `45m`, `36h`, `3d`, `2w`,
  `6mo`, `1y`. A value names a period to its last written unit, so
  `--since 2026-10-01 --until 2026-10-01` is that whole day. The resolved
  window and the dropped-row counts are printed. `sessions.jsonl` is
  summarised from the kept rows.
- `python-dateutil` is a new required dependency, used for `--since` and
  `--until`; reinstall with `pip install -r requirements.txt`.
- The analyzer README has recipes for filtering a written timeline by time
  with jq, DuckDB, Python and PowerShell.

### Changed

- `timeline` writes `timeline.jsonl` and `sessions.jsonl` instead of
  `timeline.csv` and `sessions.csv`: one JSON object per line, UTF-8, LF
  line ends, every field present in the old column order, `""` for no
  value. Interface change: `source_line`, `user_turns`, `assistant_turns`
  and `tool_calls` are JSON integers, and `models` is an array of strings
  instead of a space-separated string. Field names are unchanged.
- The `text` field keeps the event's line breaks and indentation, so tool
  output, diffs and multi-line prompts read as they were written; only
  leading and trailing whitespace is removed. Before, whitespace runs were
  collapsed to one space.
- The analyzer README has a section on reading and searching large JSONL
  timelines with jq, grep, DuckDB, Python and PowerShell.

### Removed

- `--max-text-length`. `text` is always written in full; cut it while
  reading, for example with `.text[0:200]` in jq.
- The `shell-history` catalog agent, following collector 1.7.0, which no
  longer collects shell history. Loose input no longer attributes
  `.bash_history`, `.zsh_history` and the other shell history files to an
  agent.
- The `shared|.env` and `project|.env` catalog entries, following collector
  1.7.0. Loose input no longer attributes a home or project `.env` file to
  `shared` or `project`.

## [0.7.0] - 2026-10-04

### Added

- Claude Code: sessions and `history.jsonl` in a config home moved with
  `CLAUDE_CONFIG_DIR` to a `.claude-<name>` directory (such as
  `~/.claude-work`) are parsed, and the bundled catalog copy detects
  them; `~/.claude-code-router` and other `.claude-` tools are not.
- Claude Code: a tool result stored as a `<persisted-output>` stub now
  carries the full output from the session's `tool-results/*.txt` file;
  when the file is missing, the stub is kept with a
  `[persisted output not found: ...]` note.
- Claude Code: each subagent transcript opens with a `system` row
  `subagent <agent id> of <session id>`.
- Claude Code: `session title:` rows for `ai-title`, `custom-title` and
  `agent-name` records, `cwd changed:` rows for `relocated` records (later
  rows take the new `project_path`), `hook:` rows for hook system messages
  and `edited file:` rows for `edited_text_file` attachments (the path
  only, not the snippet).

### Changed

- Claude Code: the Bash `tool_use` text is the command the model sent,
  with its `cd <dir> &&` prefix, instead of the normalised one.
- Claude Code: other injected context (`isMeta` records) starts with
  `context:`, and `system` records without `content` (`api_error`,
  `memory_saved`, ...) show their fields as JSON after the subtype.
- Open Interpreter rollouts are read by the same code as Codex CLI's, so
  every Codex CLI change below applies to them too.
- Codex CLI: a rollout that holds an ancestor's `session_meta` (a copied
  fork) keeps the file's own session id, project and branch; the ancestor's
  record is a `system` row `copied from ancestor: ...`, and a fork gets a
  `forked from <id>` row.
- Codex CLI: a non-zero exit code from a command's `item_completed` record
  prefixes that call's `tool_result` text as `[exit N]`.
- Codex CLI: a subagent rollout starts with a `system` row
  `subagent <id> of <parent id>` (with its agent path and role), and its
  first prompt, the task from the parent, is a `system` row
  `subagent task: ...` instead of `user`. Messages copied from the parent
  (`inherited_user_message`) are no longer repeated in the subagent's rows.

### Fixed

- Claude Code: prompts typed while a turn was running and delivered as
  `queued_command` attachments are now `user` rows; they were missing.
  The `enqueue` that repeated a delivered prompt's text is now
  `prompt queued: delivered at line N`, keeping the time it was typed;
  an `enqueue` with no delivery in the file is still
  `queue enqueue: <prompt>`.
- Claude Code: a subagent's task, task notifications, slash commands and
  their output, peer and coordinator messages, interruption markers and
  compaction summaries were `user` rows; they are now `system` rows with
  a label (`subagent task:`, `task notification:`, `slash command:`,
  `command output:`, `peer message:`, `coordinator message:`,
  `interrupted:`, `compaction summary:`).
- Claude Code: local API errors (model `<synthetic>`) were `assistant`
  rows; they are now `system` rows `api error: <status> <error>: <text>`.
- Claude Code: empty thinking blocks (signature only) no longer produce
  `[redacted]` thinking rows; only `redacted_thinking` blocks do.
- Claude Code: `pr-link` rows, re-written on every metadata flush, appear
  once per session and URL, and with the session's project and branch,
  like the queue rows.
- Claude Code: tool results that list tools (`tool_reference` blocks) show
  the tool names instead of empty text.
- Codex CLI: user-role messages the harness injects (environment context,
  AGENTS.md and skill instructions, subagent notifications, user shell
  commands) were `user` rows; they are now `system` rows
  `context: <kind>: ...`, by content kind where the rollout records one
  (current releases) and otherwise by the harness's own wrapper around the
  block (`<environment_context>`, `# AGENTS.md instructions`, `<skill>`
  and others), so `user` rows and `user_turns` count only what the person
  typed. A tag typed inside a prompt does not change its type.
- Codex CLI: compaction summaries, messages between agents
  (`inter_agent_communication`, `agent_message`), image generation
  prompts, tool searches, realtime voice transcripts, aborted and
  rolled-back turns, and `item_completed` turn items that no other record
  carries (web searches inside code-mode calls, MCP and dynamic tool calls,
  plans) were dropped; they now produce rows.
- Codex CLI: a reverted thread's rollout
  (`rollout-<time>-<thread id>_<rollout id>.jsonl`) cut before its
  `session_meta` took the rollout id as session id; it now takes the
  thread id.
- Codex CLI: a reasoning item with no summary text was a `thinking` row
  with empty text under `--include-thinking`; it is now skipped.

## [0.6.0] - 2026-10-04

### Added

- Muse Code parser (`muse-code`): session logs under
  `.local/share/muse/sessions/` and their subagent logs (user prompts,
  assistant replies, tool calls and results, approval requests and
  decisions, failed runs; reasoning summaries with `--include-thinking`),
  and the `tui-history.jsonl` prompt history.
- The catalog copy detects `muse-code` (Meta's Muse Code CLI).

### Changed

- Minimum Python raised from 3.9 to 3.10.

### Fixed

- OpenClaw: a `transcript_events` row whose `event_json` is valid JSON
  but not an object (such as `null`) no longer stops the parser with
  `UnboundLocalError`; it becomes a `system` row, "event seq N
  unreadable: not a JSON object", and the session's later events are
  still read.

## [0.5.0] - 2026-10-04

### Added

- `inventory` command: merges the saved stdout of collector 1.6.0
  `--inventory` / `-Inventory` runs (files, or directories of files) into
  one CSV, `fleet-inventory.csv` unless `-o FILE` is given.
- New CSV interface, `fleet-inventory.csv`, columns `host`, `collector`,
  `mode`, `at`, `user`, `agent`, `files`, `bytes`, `first`, `last`,
  `projects`, `evidence`; times normalised to UTC with milliseconds. A host
  with no agents gives one row with the agent columns empty.
- Console junk lines in a capture are skipped and counted on stderr.
- A per-agent rollup on stdout after the CSV: hosts, users and latest
  `last`.
- The catalog copy carries collector 1.5.0's `DOCKER_VOLUMES` table; the
  reader keeps those lines in their own list instead of the secret list.

### Changed

- The README says the `live` pseudo-agent appears only in collections made
  by collectors before 1.6.0, which removed the live snapshot.

## [0.4.0] - 2026-10-04

### Added

- Transcript parsers for fourteen more agents: `tabby`, `openhands`,
  `shellgpt`, `pi`, `little-coder`, `letta`, `hermes`, `agent-zero`,
  `open-interpreter`, `openclaw`, `nanobot`, `cody`, `twinny` and `pearai`,
  for thirty parsed agents in all. little-coder and Letta Code sessions are
  read with the pi parser's reader, and Open Interpreter rollouts with the
  Codex one.
- `reads_agents` routing: a parser can name other catalog agents whose files
  it is also offered. Cody and Twinny use it to read their rows of the
  `state.vscdb` that the catalog attributes to `vscode` or to a fork
  (`cursor`, `windsurf`, `pearai`, `kiro`, `antigravity`); the rows come out
  under `cody` or `twinny`, and `--agent cody` selects them.
- `agent_analyzer/vscode_state.py`, a helper that reads one extension's
  global state out of a VS Code family `state.vscdb` through
  `sqlite_util`, never reading `secret://` rows.
- Detection of the fifteen agents added in collector 1.4.0: `pearai`,
  `cody`, `twinny`, `tabby`, `open-interpreter`, `openhands`, `pi`,
  `little-coder`, `letta`, `hermes`, `openclaw`, `nanobot`, `agent-zero`,
  `shellgpt` and `local-deep-research`, from the regenerated catalog copy.

### Changed

- The Codex parser now also reads archived rollouts under
  `archived_sessions/` and zstd-compressed `.jsonl.zst` rollouts (needs
  `zstandard`; without it each compressed rollout is one `system` row). Its
  rollout reader is now the reusable `RolloutParser` base class.

## [0.3.1] - 2026-10-04

### Fixed

- The `timeline` summary no longer lists `project` among the agents that
  were detected but not parsed.

## [0.3.0] - 2026-10-03

### Added

- Transcript parsers for Gemini CLI, Qwen Code, Kiro (Amazon Q Developer CLI
  conversations), Crush, Goose, Zed, VS Code chat sessions, Continue, Aider,
  OpenCode, Kilo Code, Cline and Roo Code, for sixteen parsed agents in all.
- Dependency on the `zstandard` package for Zed threads; without it each Zed
  thread becomes one undecodable `system` row and everything else runs.

### Changed

- Files the collector found inside a discovered repository (agent `project`
  in the manifest) are offered to every parser, so a repository's
  `.crush/crush.db` and `.aider.*` files are parsed and their rows carry the
  real agent. `--agent` filters on that agent, so `--agent aider` includes
  repository-level Aider files.
- `detect` no longer reports `project` as a parsed agent.

## [0.2.0] - 2026-10-03

### Added

- Antigravity CLI parser for its SQLite conversation databases, decoded from
  the protobuf schemas embedded in the shipped binary. SQLite stores are read
  from a copy taken with their WAL and SHM sidecars, so the evidence copy is
  never opened and uncheckpointed rows are kept.
- Detection of the catalog entries added in collectors 1.2.0 and 1.3.0.

### Changed

- `timeline.csv`: the `summary` column is renamed `text`, in the same
  position, and holds the event's full text by default.
- `--max-text-length N` replaces `--summary-length N` and defaults to `0`,
  no cut; the old default cut at 400 characters.
- In loose mode a nested catalog entry claims its subtree, as in the
  collectors, so Antigravity CLI files under `~/.gemini` are attributed to
  `antigravity`.

## [0.1.0] - 2026-10-03

### Added

- `detect`, `timeline` and `catalog` commands, reading a collector archive,
  an extracted collection, or a loose directory such as a mounted image, a
  copied home or a single agent directory.
- Detection of every agent in the collectors' catalog. Host, user and agent
  come from the manifest when present; for loose input they are inferred
  from paths and marked as inferred.
- Parsers for Claude Code (session transcripts, subagent transcripts,
  `history.jsonl`) and Codex CLI (rollouts, `history.jsonl`).
- `timeline.csv` columns: `timestamp_utc`, `host`, `user`, `agent`,
  `session_id`, `project_path`, `git_branch`, `turn_type`, `model`,
  `tool_name`, `tool_use_id`, `summary`, `source_file`, `source_line`.
- `sessions.csv` columns: `host`, `user`, `agent`, `session_id`,
  `project_path`, `first_timestamp_utc`, `last_timestamp_utc`, `models`,
  `user_turns`, `assistant_turns`, `tool_calls`, `source_file`.
- Options `--host`, `--user`, `--work-dir`, `--keep-extracted`,
  `--summary-length` (default 400), `--include-thinking` and `--agent`;
  `detect --json` and `--files`; `catalog --agents`.

[Unreleased]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.8.1...HEAD
[0.8.1]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.8.0...analyzer-v0.8.1
[0.8.0]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.7.0...analyzer-v0.8.0
[0.7.0]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.6.0...analyzer-v0.7.0
[0.6.0]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.5.0...analyzer-v0.6.0
[0.5.0]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.4.0...analyzer-v0.5.0
[0.4.0]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.3.1...analyzer-v0.4.0
[0.3.1]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.3.0...analyzer-v0.3.1
[0.3.0]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.2.0...analyzer-v0.3.0
[0.2.0]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.1.0...analyzer-v0.2.0
[0.1.0]: https://github.com/seanthegeek/coding-agent-collector/releases/tag/analyzer-v0.1.0
