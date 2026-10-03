# ollama

## 1. Source and evidence level

- Open source, `https://github.com/ollama/ollama`, shallow clone at `scratchpad/repos/ollama`, commit `42e911bc3d05798cad729cb474bf62f378cb2e26` (2026-10-02). All claims below are evidence level **A** (source, file:line) unless marked **D** (repo docs `docs/*.mdx`) or **L** (local layout check, `ls ~/.ollama`, names only).
- Local check (L): `~/.ollama/` on this workstation holds `backup/config.json.<epoch>`, `cache/model-recommendations.json`, `config.json`, `history`, `id_ed25519`, `id_ed25519.pub`, `models/blobs/` (6 blobs, 1.9 GB), `models/manifests/registry.ollama.ai/library/llama3.2/`.

## 2. Per-user storage

CLI and server (all OSes, `os.UserHomeDir()`):
- `~/.ollama/models/` — `envconfig/config.go:111-123` (`OLLAMA_MODELS` override, default `$HOME/.ollama/models`); `models/manifests/<host>/<ns>/<model>/<tag>` and `models/blobs/sha256-<digest>` (`manifest/paths.go:11,30,42`); `models/metadata` (`server/gguf_metadata.go:109`); transient `models/blobs/.ollama-split-*` (`llm/model_split.go:21-23`). There is no `OLLAMA_HOME` variable; only `OLLAMA_MODELS` relocates data (grep of `envconfig/config.go` lines 315-336).
- `~/.ollama/history` — REPL readline history, mode 0600 (`readline/history.go:41-52`); disabled by `OLLAMA_NOHISTORY` (`envconfig/config.go:224,333`).
- `~/.ollama/id_ed25519`, `id_ed25519.pub` — generated on first serve (`cmd/cmd.go:2120-2126`), used to sign registry/cloud requests (`auth/auth.go:13,45`).
- `~/.ollama/server.json` — `disable_ollama_cloud` (`envconfig/config.go:382-404`, `app/store/cloud_config.go:15-30`).
- `~/.ollama/config.json` — `ollama launch` integration config: `models`, `aliases`, `integrations{}`, `last_model`, `last_selection` (`cmd/config/config.go:20-33,88`); legacy `~/.ollama/config/config.json` (`:96`).
- `~/.ollama/backup/<file>.<epoch>` — copies of other agents' config files taken before `ollama launch` edits them (`cmd/internal/fileutil/files.go:47-56`).
- `~/.ollama/cache/model-recommendations.json` (`server/model_recommendations.go:310-314`); no `cache/show` is written (`server/model_show_cache.go:49-50`).
- `~/.ollama/launch/{muse-config, dsh, codex-app-restore.json, chatgpt-session-start}` (`cmd/launch/muse.go:218`, `deepseek_harness.go:503`, `codex_app.go:2653`, `codex_app_profile.go:86`).
- `~/.ollama/logs/codex-proxy.log` — activity log of the Codex desktop proxy (`server/codex_proxy.go:31`).
- Linux systemd install: service user `ollama`, home `/usr/share/ollama`, so data is `/usr/share/ollama/.ollama/` (`scripts/install.sh:200,222`; D `docs/faq.mdx:236,398`). Docker: `/root/.ollama` (D `docs/docker.mdx:4`). `OLLAMA_DEBUG_LOG_REQUESTS` writes request bodies to a temp dir `ollama-request-logs-*`, outside home (`server/inference_request_log.go:25-34`).

Desktop app, macOS (`app/`):
- `~/.ollama/logs/server.log`, `app.log`, `upgrade.log` (`app/server/server_unix.go:20`, `app/cmd/app/app_darwin.go:81`, `app/updater/updater_darwin.go:86`; D `docs/macos.mdx:25-28`).
- `~/Library/Application Support/Ollama/db.sqlite` — chat database: tables `settings` (incl. `device_id`, `working_dir`), `chats`, `messages` (role, content, thinking, model_name, tool_result), `tool_calls`, `attachments` (filename + BLOB), `users` (name, email, plan) (`internal/onboarding/app_state.go:26-34`, `app/store/database.go:65-155`). WAL mode (`database.go:31`), so `db.sqlite-wal`/`-shm` sidecars.
- `~/Library/Application Support/Ollama/config.json` (legacy app config, `app/store/store.go:209`), `ollama.pid` (`server_unix.go:19`), `~/Library/LaunchAgents/com.ollama.ollama.plist` (`app_darwin.go:82`). Low value: `~/Library/Caches/ollama`, `~/Library/Caches/com.electron.ollama`, `~/Library/WebKit/com.electron.ollama`, `~/Library/Saved Application State/com.electron.ollama.savedState` (D `docs/macos.mdx:38-42`).

Desktop app, Windows:
- `%LOCALAPPDATA%\Ollama\{db.sqlite, server.log, server-#.log, app.log, config.json, ollama.pid, updates\}` (`app_state.go:33`, `app/server/server_windows.go:18-19`, `app/cmd/app/app_windows.go:39`, `store.go:207`, `app/ollama.iss:120`; D `docs/windows.mdx:66-71`). Binaries in `%LOCALAPPDATA%\Programs\Ollama`. Models, history, keys stay in `%USERPROFILE%\.ollama` (`ollama.iss:139,260-261`).
- Linux has no desktop database (`AppDatabasePath` returns "" by default, `app_state.go:35`).

## 3. Credentials

- `~/.ollama/id_ed25519` is the only credential: Ollama cloud "sign-in" binds this public key to the account (`app/auth/connect.go:14-25`, `cmd/cmd.go:1012-1026`); no token file is written. `id_ed25519.pub` identifies the device.
- No keychain use anywhere in the tree (grep `keychain|Keychain` in cmd, auth, server, app: none).
- `~/.ollama/config.json`, `server.json`, `~/.ollama/backup/*` can contain copies of other tools' settings files (which may embed API keys) but hold no Ollama secret themselves.
- `db.sqlite` `users` table holds account name/email/plan; `attachments.data` holds user-uploaded files.

## 4. Exclusions

`.ollama/models` (blobs are multi-GB; manifests are small but live under the same root), `AppData/Local/Ollama/updates`, `Library/Caches/ollama`, `Library/Caches/com.electron.ollama`, `Library/WebKit/com.electron.ollama`. Consider collecting `.ollama/models/manifests` separately as an inventory of pulled models (small JSON).

## 5. Project-local files

None. Ollama writes nothing into repositories. `ollama launch` edits other agents' configs under their own homes (`cmd/launch/droid.go:60`, `claude.go:33`, `qwen.go:381`, …).

## 6. Project path records

None for the CLI. The desktop app stores a single `settings.working_dir` in `db.sqlite` (`database.go:76`). `~/.ollama/history` lines are raw prompts without cwd.

## 7. Catalog review

Current:
- `ollama|.ollama` — confirmed (A, L); covers Linux, macOS, Windows `%USERPROFILE%` and `/usr/share/ollama` if the collector enumerates passwd homes.
- `.ollama/models` excluded — confirmed necessary (1.9 GB locally with one model).
- `.ollama/id_ed25519` secret — confirmed; the only credential.

Add:
```
ollama|Library/Application Support/Ollama
ollama|AppData/Local/Ollama
AppData/Local/Ollama/updates
Library/Caches/ollama
Library/Caches/com.electron.ollama
```
No new secret globs. Optional: `ollama|.ollama/models/manifests` as an explicit include if the collector supports include-over-exclude; otherwise document that the manifest inventory is lost to the exclusion.

## 8. Confidence

High: everything in sections 2-3 (source with line numbers, local layout confirmed). Medium: WAL sidecar presence depends on app state at collection. Not determined: whether the macOS app also writes `db.sqlite` into `~/.ollama` on non-standard installs (code says no); size of `~/.ollama/launch/*` and `repl` artifacts of other `ollama launch` integrations; whether `/usr/share/ollama` homes are enumerated by the collector's user discovery (passwd-based) — if not, add `/usr/share/ollama/.ollama` as an explicit extra root.
