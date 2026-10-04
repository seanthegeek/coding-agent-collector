# Changelog

All notable changes to the collectors are recorded here. The sh and
PowerShell collectors share one version, printed by `--version` and
`-Version` and recorded in `collection.json`. Changes to the manifest
(`manifest.jsonl` fields and status values) and to `collection.json` are
called out, since analysts and the analyzer depend on them.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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

[Unreleased]: https://github.com/seanthegeek/coding-agent-collector/compare/collector-v1.3.0...HEAD
[1.3.0]: https://github.com/seanthegeek/coding-agent-collector/compare/collector-v1.2.0...collector-v1.3.0
[1.2.0]: https://github.com/seanthegeek/coding-agent-collector/compare/collector-v1.1.0...collector-v1.2.0
[1.1.0]: https://github.com/seanthegeek/coding-agent-collector/compare/collector-v1.0.0...collector-v1.1.0
[1.0.0]: https://github.com/seanthegeek/coding-agent-collector/releases/tag/collector-v1.0.0
