# Changelog

All notable changes to the collectors are recorded here. The sh and
PowerShell collectors share one version, printed by `--version` and
`-Version` and recorded in `collection.json`. Changes to the manifest
(`manifest.jsonl` fields and status values) and to `collection.json` are
called out, since analysts and the analyzer depend on them.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- PowerShell collector: the internal logging function is renamed from
  `Write-Log` to `Write-CollectorLog` so it no longer shadows a Windows
  built-in command name; output and behaviour are unchanged. Found by
  PSScriptAnalyzer 1.25.0 with `collectors/PSScriptAnalyzerSettings.psd1`.

### Fixed

- sh collector: failed to parse under posh and other pdksh-derived shells,
  which stop a `$(...)` at the `)` of a case pattern. The two such `case`
  statements use the `(pattern)` form, and the shared helper and worker
  programs are read from here-documents without `$(cat <<...)`; the
  programs are byte-identical. The smoke test now passes under posh.

## [1.6.0] - 2026-10-04

### Added

- Inventory mode, `--inventory` / `-Inventory`, for fleet audits through
  an EDR console: the collection walk (catalog, exclusions, nested claims,
  Docker volumes, `-u`, `-r`, `--full`, `--no-docker`) with `lstat` only.
  It writes nothing, not even a log; `-o` is ignored with a stderr note.
  Exit code `0` once the walk has run.
- Inventory output on stdout, JSON Lines: one `host` line (`type`, `host`,
  `collector`, `mode`, `at`, `users_scanned`, `users_unreadable`,
  `docker_volumes`).
- Then one `agent` line per user and agent with at least one file after
  exclusions and nested claims (`type`, `host`, `user`,
  `agent`, `files`, `bytes`, `first`, `last`, `projects`, `evidence`);
  `projects` is the user's discovered project count, repeated on each of
  the user's lines, and Docker volumes appear as user `docker`.
- Inventory never opens a credential file: project discovery skips sources
  that match `SECRET_GLOBS`.

### Changed

- PowerShell: the `profile not accessible (skipped)` log line is written
  only for profiles selected by `-Users`.

### Removed

- The live system snapshot. Both collectors no longer write the `live/`
  directory (`system.txt`, `users.txt`, `logins.txt`, `processes.txt`,
  `agent-processes.txt`, `network.txt`, `services.txt`,
  `scheduled-tasks.txt`, and the sh collector's `live/environ/<pid>.txt`
  process environments). The collectors supplement an EDR, which already
  records processes, logins, network connections and services.
- Manifest: the `live` agent name and the `live/<file>` archive paths are
  gone; no row has an empty `path` any more.
- The `--no-live` / `-NoLive` option. Passing it is now a usage error.
- `collection.json`: the `options.no_live` field. The host name stays in
  `hostname`.

## [1.5.0] - 2026-10-04

### Added

- Docker and Podman named volumes are collected (issue 28). Both
  collectors enumerate `var/lib/docker/volumes`,
  `var/lib/containers/storage/volumes` and `ProgramData/Docker/volumes`
  under the root, and the rootless `.local/share/docker/volumes` and
  `.local/share/containers/storage/volumes` under each home, from the
  filesystem only. A volume whose name matches the new `DOCKER_VOLUMES`
  table is collected whole with `user` `docker` and its `_data` directory
  as `home`; exclusion and secret globs apply relative to `_data`.
- New catalog table `DOCKER_VOLUMES` (Agent Zero, Local Deep Research,
  Ollama from source; Tabby, OpenHands, Letta, Hermes, OpenClaw and nanobot
  by inferred name), printed last by `--list` and `-List` under the new
  heading `# docker volumes (agent|volume name glob)`. Consumers of the
  `--list` output that do not know the heading should stop reading there.
- Volume-relative forms of the Agent Zero, Tabby, Ollama, Local Deep
  Research, OpenHands, Hermes, OpenClaw, nanobot and Letta exclusions and
  secret globs, at the end of `EXCLUDES` and `SECRET_GLOBS`.
- `--no-docker` / `-NoDocker` skips the enumeration.
- Manifest: new status value `skipped_unmatched_volume`, one `dir` row
  with its size for each volume that matches no `DOCKER_VOLUMES` line.
- `collection.json`: `options.no_docker`, `counts.skipped_unmatched_volume`,
  a `docker` object (`volumes_found`, `volumes_collected`, `unreadable`,
  `docker_desktop`) and a `notes` list. An unreadable volume directory or a
  volume that cannot be walked is noted there and in a `docker:` line of
  the stdout summary; collection continues and the exit code is unchanged.
  Docker Desktop data (whose Linux volumes are inside a VM disk) is only
  noted.

## [1.4.0] - 2026-10-04

### Added

- Fifteen catalog agents from the October 2026 backlog, each with an
  evidence document under `research/`: `pearai`, `cody`, `twinny`, `tabby`,
  `open-interpreter`, `openhands`, `pi`, `little-coder`, `letta`, `hermes`,
  `openclaw`, `nanobot`, `agent-zero`, `shellgpt` and `local-deep-research`.
  Several of them are general-purpose or chat-channel agents rather than
  coding agents. Sourcegraph Cody and Twinny have nested entries inside
  every VS Code family editor's globalStorage, like Cline and Continue, and
  little-coder's prompt history is a nested entry inside pi's `~/.pi`.
- 82 home catalog entries, 33 project catalog entries, 151 exclusions and
  150 secret globs, among them Codex CLI's `.codex/.env`, which was not
  flagged before.
- Twenty-one more project discovery sources in both collectors: Hermes
  checkpoint project records; Letta's session index and local-backend
  transcripts; pi session headers (also little-coder's), misplaced
  sessions, trusted folders, crash log and experimental session metadata;
  Open Interpreter live and archived rollouts; OpenHands workspaces, Agent
  Canvas conversation metadata and CLI conversation state; PearAI
  sessions; OpenClaw `workspace` and `agentDir` from its JSON5 config,
  legacy `clawdbot.json` included; nanobot workspace markers and instance
  config; Tabby `file://` repositories; and the common directory of the
  files in each Twinny embeddings manifest.
- `[!...]` negated classes in exclusion and secret globs now work in the
  PowerShell collector as they do in the sh collector.

### Fixed

- The PowerShell collector dropped `file:///` URIs of POSIX paths found in
  agent state; they now map to the path.

## [1.3.0] - 2026-10-03

### Added

- 60 home catalog entries, among them the remote server data directories of
  VS Code, Cursor, Windsurf, Devin and Kiro (with their agent extensions
  attributed to the extension), Antigravity IDE and `.gemini/config`, the
  Copilot CLI XDG directories and caches, Windsurf transcripts, the Ollama
  desktop app and Zed under Flatpak.
- 33 project catalog entries, 55 exclusions and 80 secret globs, including
  the Cursor and Windsurf credential files, now flagged `secret: true`.
- Ten more project discovery sources in both collectors.
- `collectors/research/` holds one evidence document per catalog agent.

### Fixed

- Exclusions that hid evidence: Factory Droid's cache exclusion now covers
  only its sounds, Kiro's `powers` directory is collected again, the Kilo
  Code worktree exclusions match the real paths, and Codex database backups
  and Goose apps are collected.

## [1.2.0] - 2026-10-03

### Changed

- A catalog entry nested inside another entry's directory now claims its
  subtree: each file is collected once, under the most specific agent.
  Manifest rows for Antigravity CLI files under `~/.gemini/antigravity-cli`
  now have `agent` `antigravity` instead of `gemini-cli`.

### Added

- Nested entries for the Cline, Roo Code, Kilo Code and Continue extensions
  inside the globalStorage of every VS Code family editor (VS Code, VSCodium,
  Cursor, Windsurf, Antigravity IDE, Kiro), on all three platforms, so their
  files are attributed to the extension rather than the editor.

## [1.1.0] - 2026-10-03

### Added

- `Collect-AgentArtifacts.ps1`, the Windows PowerShell 5.1 collector, with
  the same catalog, manifest and archive layout as the sh collector. It reads
  profiles from the registry and `C:\Users`, copies files held open by
  running editors, takes a CIM live snapshot, and writes a `tar.gz` through
  `tar.exe` or a `.zip` on older hosts.
- Manifest rows written by the Windows collector carry two extra fields,
  `owner` and `attributes`, and record `uid`, `gid`, `ctime` as `0` and
  `mode` as `""`.
- Catalog agents `roo-code`, `kilo-code`, `copilot` (the GitHub Copilot
  editor plugin's `github-copilot` directory) and `shared` (`~/.agents`,
  `~/.env` and `AGENTS.md` shared between agents).
- Nine more project discovery sources, and Crush's per-project `.crush`
  session database.
- Exclusions for embedding indexes, shadow git checkpoints, worktrees,
  daemon binaries and Electron caches.
- Secret flags for the Gemini CLI and Goose credential files that replace
  the OS keychain when it is unavailable.

### Changed

- Catalog entries for Cursor, Windsurf, Continue, Amp, Goose, Zed, Kiro,
  Qwen Code, Cline, Augment, Factory Droid, Crush, OpenCode, ChatGPT Desktop,
  Claude Desktop, Gemini CLI, Codex CLI and Aider were rebuilt from each
  tool's source, shipped bundle or official documentation.
- Zed, Goose, OpenCode, Crush, Kilo Code and Amp are looked for under
  `~/.config` and `~/.local/share` on macOS and Windows images too.

### Fixed

- Continue's `index/globalContext.json` is collected; only the embedding
  index beside it is excluded.

## [1.0.0] - 2026-10-03

### Added

- `collect-agent-artifacts.sh`, a single POSIX sh collector with no
  dependencies beyond the base system, for live macOS, Linux and BSD hosts
  and for mounted disk images (`-r`).
- Collection of Claude Code, Claude Desktop, Gemini CLI, Antigravity, Codex
  CLI, Copilot CLI, Cursor, VS Code, Windsurf, Aider, Ollama and other agent
  state, plus shell histories, for every user, and project files from
  repositories referenced in agent state.
- `manifest.jsonl` with one row per path: `user`, `home`, `agent`, `path`,
  `archive_path`, `type`, `size`, `mtime`, `atime`, `ctime`, `btime`, `uid`,
  `gid`, `mode`, `sha256`, `secret`, `status`, `target`, `error`. Status
  values: `collected`, `symlink`, `skipped_excluded`, `skipped_size`,
  `skipped_secret`, `error_copy`.
- `collection.json` run summary, a `fs/<original path>` archive layout, a
  live system snapshot, and a SHA-256 of the archive.
- Options `-o`, `-r`, `-u`, `-p`, `--full`, `--no-secrets`, `--no-live`,
  `--no-projects`, `--max-file-size`, `-k`, `--list`, `-q`, `-V`, `-h`.
- Default size exclusions for model weights, caches and extension binaries,
  overridden by `--full`; credential files collected and flagged
  `secret: true` by default.

[Unreleased]: https://github.com/seanthegeek/coding-agent-collector/compare/collector-v1.6.0...HEAD
[1.6.0]: https://github.com/seanthegeek/coding-agent-collector/compare/collector-v1.5.0...collector-v1.6.0
[1.5.0]: https://github.com/seanthegeek/coding-agent-collector/compare/collector-v1.4.0...collector-v1.5.0
[1.4.0]: https://github.com/seanthegeek/coding-agent-collector/compare/collector-v1.3.0...collector-v1.4.0
[1.3.0]: https://github.com/seanthegeek/coding-agent-collector/compare/collector-v1.2.0...collector-v1.3.0
[1.2.0]: https://github.com/seanthegeek/coding-agent-collector/compare/collector-v1.1.0...collector-v1.2.0
[1.1.0]: https://github.com/seanthegeek/coding-agent-collector/compare/collector-v1.0.0...collector-v1.1.0
[1.0.0]: https://github.com/seanthegeek/coding-agent-collector/releases/tag/collector-v1.0.0
