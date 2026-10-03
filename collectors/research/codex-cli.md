# codex-cli

## 1. Source and evidence level

Open source. github.com/openai/codex, shallow clone at `scratchpad/repos/codex`, HEAD 3e238776e857eccd3bde6bff3026e2e9798f6524 (2026-10-03). All claims are **source** (file:line under `codex-rs/`) unless marked **local** (names-only listing of `~/.codex` on this host) or **web** (community write-ups used only for the desktop app).

## 2. Per-user storage

Home resolution: `CODEX_HOME` if set (must exist, canonicalised) else `dirs::home_dir()/.codex` (utils/home-dir/src/lib.rs:13-56). No OS branching: Linux, macOS and Windows all use `~/.codex` / `%USERPROFILE%\.codex`. The macOS desktop app uses the same `~/.codex` for sessions (web: github issue 49797, jazzyalex write-up) and keeps only Sparkle update state in `~/Library/Application Support/com.openai.codex` (cli/src/doctor/updates.rs:586).

Inside `$CODEX_HOME`:
- `sessions/YYYY/MM/DD/rollout-<YYYY-MM-DDThh-mm-ss>-<thread-uuid>.jsonl` transcripts (rollout/src/lib.rs:86, rollout_file_name.rs:51-67, recorder.rs:1733-1734, list.rs:905-916); may be zstd-compressed `.jsonl.zst` (rollout/src/compression.rs:29,68,98). `archived_sessions/` same layout (rollout/src/lib.rs:87). `session_index.jsonl` (rollout/src/session_index.rs:20). Local confirms `sessions/2026/10/03/rollout-*.jsonl`.
- `history.jsonl` prompt history (message-history/src/lib.rs:52,86).
- SQLite: `state_5.sqlite` (threads, metadata), `logs_2.sqlite`, `goals_1.sqlite`, `memories_1.sqlite`, `queue_1.sqlite`, `thread_history_1.sqlite` (state/src/sqlite.rs:34-39), `agent_message_board_1.sqlite` (ext/agent-message-board/src/local.rs:55), with `-wal`/`-shm` sidecars (local). Recovery copies in `db-backups/sqlite-<n>/` (state/src/runtime/recovery.rs:16).
- `memories/` (`MEMORY.md`, `rollout_summaries/*.md`), `memories_v2/`, `memories_extensions/` (memories/read/src/lib.rs:14, memories/write/src/control.rs:5-7,56-63).
- `log/` (`codex-tui.log`, `codex-login.log`) (core/src/config/mod.rs:4093, tui/src/lib.rs:281, cli/src/login.rs:85). Daemon logs in `app-server-daemon/` (feedback/src/daemon_logs.rs:18); `app-server-control/` socket dir (app-server-transport/src/transport/mod.rs:53).
- `shell_snapshots/` (core/src/shell_snapshot.rs:107), `skills/` with bundled `skills/.system/` (skills/src/lib.rs:57), `plugins/` and `plugins/cache/` (core-plugin-common/src/installed.rs:11), `packages/` managed binaries (app-server-daemon/src/managed_install.rs:52), `worktrees/` (worktree/src/settings.rs:44), `visualizations/` (tui/src/inline_visualization.rs:93), `.tmp/` (rollout/src/maintenance.rs:27, core-plugins/src/startup_sync.rs:171; `.tmp/bundled-marketplaces/`), `tmp/arg0/` (arg0/src/lib.rs:363), `cache/` (tui/src/pets/ambient.rs:158), `installation_id` (core/src/installation_id.rs:17), `version.json` (cli/src/doctor/updates.rs:35), `.sandbox_migration` (execpolicy/src/sandbox_migration.rs:10), `config.toml` (config/src/lib.rs:52), `rules/` exec policy (core/src/exec_policy.rs:54), `hooks.json`, `agents/`.
- Windows sandbox: `.sandbox/` (logs `.sandbox/logs/sandbox.<date>.log`, `setup_error.json`), `.sandbox-bin/`, `.sandbox-secrets/` (windows-sandbox-rs/src/spawn_prep.rs:108, logging.rs:240-251, setup.rs:196, uninstall_windows.rs:132-137).
- Local only (not grepped in source): `models_cache.json`, `thread-writer-locks/`, `tui-thread-reference-capabilities/`, `.sqlite-maintenance.lock`.

## 3. Credentials

- `auth.json` with `OPENAI_API_KEY` and OAuth tokens (login/src/auth/storage.rs:47-53,163). Store mode `AuthCredentialsStoreMode`: `file` (default), `keyring`, `auto`, `ephemeral` (config/src/types.rs:116-124). Keyring via `codex-keyring-store`.
- `.credentials.json`: MCP OAuth token fallback when keyring unavailable (rmcp-client/src/oauth.rs:17,857; config/src/types.rs:138).
- `secrets/` gateway OAuth and local secrets, age-encrypted (`gateway_oauth.age`, `local.age`, `gateway_oauth.lock`) (login/src/gateway_auth_storage.rs:20-24, secrets/src/local.rs:166,587-591).
- `.sandbox-secrets/` Windows sandbox tokens (setup.rs:196).
- `config.toml` can embed `experimental_bearer_token` per provider (model-provider-info/src/lib.rs:149-157); `env_key` names an env var instead.

## 4. Exclusions

`.codex/packages`, `.codex/cache`, `.codex/.tmp`, `.codex/tmp`, `.codex/plugins/cache`, `.codex/skills/.system`, `.codex/worktrees`, `.codex/.sandbox`, `.codex/.sandbox-bin`, `.codex/visualizations`, `.codex/app-server-daemon/packages` (if present). `.codex/db-backups` is a copy of the state DBs, small, and may hold rows deleted from the live DB: collect rather than exclude. `Library/Application Support/com.openai.codex` is updater state only.

## 5. Project-local files

`AGENTS.md`, `AGENTS.override.md` (core/src/agents_md.rs:43-45), `.codex/config.toml`, `.codex/agents/`, `.codex/hooks.json`, `.codex/hooks/`, `.codex/rules/`, `.codex/skills/` (external-agent-migration/src/scope.rs:59-62, detect/mod.rs:86,167,270; exec-server/src/discoverV2/capability_locations.rs:72), `.agents/skills` (external-agent-migration/src/service.rs:467), `generated_images/` in cwd (ext/image-generation/src/tool.rs:332). No per-project database.

## 6. Where the project path is recorded

- First line of every rollout: `SessionMeta` with `cwd: PathBuf`, `timestamp`, `id`, `originator`, `cli_version`, `source`, `runtime_workspace_roots` (protocol/src/protocol.rs:3123-3141). Compressed rollouts need zstd before grep.
- `session_index.jsonl` (rollout/src/session_index.rs) and `state_5.sqlite` threads table (v2 parser).

## 7. Catalog review

Current lines:
- `codex-cli|.codex` — confirmed (home-dir lib.rs:56).
- `project|.codex`, `project|AGENTS.md`, `project|AGENTS.override.md`, `project|.agents` — confirmed.
- exclude `.codex/packages`, `.codex/cache`, `.codex/.tmp`, `.codex/plugins/cache`, `.codex/skills/.system`, `.codex/worktrees`, `.codex/.sandbox`, `.codex/.sandbox-bin`, `.codex/tmp`, `.codex/visualizations` — confirmed.
- exclude `.codex/db-backups` — doubtful: holds pre-rebuild copies of `state_5.sqlite`; evidence value. Suggest removing the exclusion.
- secret `.codex/auth.json`, `.codex/.credentials.json`, `.codex/secrets/*` — confirmed.

Add:
```
secret: .codex/.sandbox-secrets/*
secret: .codex/config.toml            (experimental_bearer_token)
exclude: .codex/.tmp/bundled-marketplaces   (already under .tmp)
codex-cli|Library/Application Support/com.openai.codex   (optional, updater state)
project|generated_images              (optional; images Codex produced in the repo)
```
v2 note: rollouts may be `.jsonl.zst`; discovery must decompress, and `history.jsonl`, `session_index.jsonl`, `state_5.sqlite`, `thread_history_1.sqlite` are the indexes.

## 8. Confidence

High: everything in sections 2-6 cited to source, and the local listing matches. Medium: desktop app sharing `~/.codex` (issue tracker and write-ups, not source). Not determined: contents of `models_cache.json`, `thread-writer-locks/`, `tui-thread-reference-capabilities/` (local names only); whether `.sandbox*` dirs exist on non-Windows hosts.
