# Changelog

All notable changes to the analyzer are recorded here. The version is
printed by `--version`. Changes to the `timeline.csv` and `sessions.csv`
columns are called out, since they are interfaces.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

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

[Unreleased]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.5.0...HEAD
[0.5.0]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.4.0...analyzer-v0.5.0
[0.4.0]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.3.1...analyzer-v0.4.0
[0.3.1]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.3.0...analyzer-v0.3.1
[0.3.0]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.2.0...analyzer-v0.3.0
[0.2.0]: https://github.com/seanthegeek/coding-agent-collector/compare/analyzer-v0.1.0...analyzer-v0.2.0
[0.1.0]: https://github.com/seanthegeek/coding-agent-collector/releases/tag/analyzer-v0.1.0
