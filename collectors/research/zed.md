# Zed: on-disk paths

## 1. Source and evidence level

zed-industries/zed, open source, commit `a84689073d296dfd39987bc7dd478e43ef76d83a` (blobless partial clone). Platform mapping verified against the `dirs` 6.0.0 crate (`scratchpad/crates/dirs/dirs-6.0.0`, version from `Cargo.lock`). Flatpak sandbox paths are Flatpak documentation level. Transcript schema is in `analyzer/research/zed.md`.

## 2. Per-user storage

`APP_NAME` is `Zed`, lowercased for XDG paths (`crates/paths/src/paths.rs:18-21`).

- Config (`paths.rs:122-139`): Windows `dirs::config_dir()/Zed` = `%APPDATA%\Zed` (`dirs/src/win.rs:8`); Linux/FreeBSD `$FLATPAK_XDG_CONFIG_HOME` or `$XDG_CONFIG_HOME`/`~/.config`, then `/zed` (`dirs/src/lin.rs:9`); macOS `~/.config/zed`.
- Data (`paths.rs:144-165`): macOS `~/Library/Application Support/Zed`; Linux `$FLATPAK_XDG_DATA_HOME` or `dirs::data_local_dir()` = `$XDG_DATA_HOME` or `~/.local/share`, then `/zed` (`lin.rs:11-12`); Windows `dirs::data_local_dir()/Zed` = `%LOCALAPPDATA%\Zed` (`win.rs:11`).
- State (`paths.rs:169-190`): macOS `~/.local/state/Zed` (capital Z), Linux `~/.local/state/zed`, Windows `%LOCALAPPDATA%\Zed`. No caller outside the paths crate uses it today.
- Temp/cache (`paths.rs:193-218`): macOS `~/Library/Caches/Zed`, Windows `%LOCALAPPDATA%\Zed`, Linux `~/.cache/zed`.
- Logs (`paths.rs:228-255`): macOS `~/Library/Logs/Zed`, elsewhere `<data>/logs`; files `Zed.log`, `Zed.log.old`. macOS crash reports in `~/Library/Logs/DiagnosticReports` (`:264-268`).
- `--user-data-dir <dir>` (`crates/cli/src/main.rs:524,969`) makes `<dir>` the data dir and `<dir>/config` the config dir (`paths.rs:103-125`).
- Flatpak builds use `FLATPAK_XDG_*` (`paths.rs:131,153,177,209`); app ids `dev.zed.Zed`, `dev.zed.ZedPreview`, `dev.zed.ZedNightly`, `dev.zed.ZedDev` (`script/flatpak/bundle-flatpak:15-33`), so sandboxed state is `~/.var/app/dev.zed.Zed*/{config,data,cache}/zed`.

Config dir files: `settings.json`, `global_settings.json`, `settings_backup.json`, `keymap.json`, `keymap_backup.json`, `tasks.json`, `debug.json`, `AGENTS.md` (`paths.rs:278-326`), `themes/`, `snippets/` (`:372-380`), `development_credentials` (`crates/zed_credentials_provider/src/zed_credentials_provider.rs:116`), `git/config`. On macOS only, `prompts/` (holding the LMDB `prompts-library-db.0.mdb`, `crates/prompt_store/src/prompt_store.rs:28`), `prompt_overrides/` and `embeddings/` sit under config; elsewhere under data (`paths.rs:386-433`).

Data dir: `threads/threads.db` agent threads (`crates/agent/src/db.rs:444-446`); `db/0-<channel>/db.sqlite` where channel is `dev`, `nightly`, `preview`, `stable` or `global` (`crates/db/src/db.rs:138,148-166`; `crates/release_channel/src/lib.rs:218-221`); `extensions/`, `remote_extensions/` (with `uploads/`), `languages/`, `debug_adapters/`, `external_agents/`, `copilot/`, `prettier/`, `remote_servers/`, `devcontainer/`, `hang_traces/`, `server_state/` (`paths.rs:222-242,348-483`); `node/` runtime (`crates/node_runtime/src/node_runtime.rs:637,1031`); `build_timings/` (`crates/zed/src/reliability.rs:465`); `zed-<channel>.sock` (`crates/zed/src/zed/open_listener.rs:413`); `logs/` on Linux and Windows. No `conversations/` directory exists in current source.

## 3. Credentials

Production builds store credentials only in the OS keychain (`zed_credentials_provider.rs:56-64,69`). On the Dev channel, unless `ZED_DEVELOPMENT_USE_KEYCHAIN` is set, they go to `<config>/development_credentials` as JSON (`:50-62,116-120`). `settings.json` (and its `settings_backup.json` copy and `global_settings.json`) can embed `api_key` and `custom_headers` for LM Studio style providers (`crates/settings_content/src/language_model.rs:310-312`) and `agent_servers` environment. `db.sqlite` and `threads.db` hold no tokens.

## 4. Exclusions

Under either data root: `extensions`, `remote_extensions`, `node`, `languages`, `copilot`, `debug_adapters`, `external_agents`, `prettier`, `remote_servers`, `devcontainer`, `embeddings`, `server_state`, `hang_traces`, plus `build_timings`. `~/.cache/zed` and `~/Library/Caches/Zed` are temp. `prompts/*.mdb` is the user prompt library, small, keep.

## 5. Project-local files

`.zed/settings.json`, `.zed/tasks.json`, `.zed/debug.json` (`paths.rs:487-531`); rules files read by the agent: `.rules`, `.cursorrules`, `.windsurfrules`, `.clinerules`, `.github/copilot-instructions.md`, `AGENT.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` (`crates/prompt_store/src/prompts.rs:22-32`). No per-project database.

## 6. Where the project path is recorded

- `threads.db` table `threads` columns `folder_paths`, `folder_paths_order` (`crates/agent/src/db.rs:469-470,545`).
- `db.sqlite` table `sidebar_threads` columns `folder_paths`, `folder_paths_order` (`crates/agent_ui/src/thread_metadata_store.rs:1375-1383`) and table `workspaces` columns `local_paths_array`, `local_paths_order_array` (`crates/workspace/src/persistence.rs:731-733`).
All SQLite, so v2 work.

## 7. Catalog review

Home: `.config/zed`, `.local/share/zed`, `Library/Application Support/Zed`, `Library/Logs/Zed`, `AppData/Roaming/Zed`, `AppData/Local/Zed` all confirmed.
Project: `.zed` confirmed; `.rules` is present in the catalog (line 227) and confirmed.
Excluded: all thirteen `*/[Zz]ed/...` entries confirmed; the `[Zz]` class also catches the macOS `.config/zed/embeddings` placement.
Credential: `.config/zed/development_credentials`, `.config/zed/settings.json`, `AppData/Roaming/Zed/development_credentials`, `AppData/Roaming/Zed/settings.json` confirmed.

Add:
```
# home
zed|.var/app/dev.zed.Zed/config/zed
zed|.var/app/dev.zed.Zed/data/zed
zed|.var/app/dev.zed.ZedPreview/config/zed
zed|.var/app/dev.zed.ZedPreview/data/zed
zed|.var/app/dev.zed.ZedNightly/config/zed
zed|.var/app/dev.zed.ZedNightly/data/zed
# excluded
*/[Zz]ed/build_timings
*/[Zz]ed/remote_extensions/uploads
# credential
.config/zed/settings_backup.json
.config/zed/global_settings.json
AppData/Roaming/Zed/settings_backup.json
AppData/Roaming/Zed/global_settings.json
*/dev.zed.Zed*/config/zed/settings.json
*/dev.zed.Zed*/config/zed/development_credentials
```

## 8. Confidence

High: all paths from `paths.rs` and the `dirs` crate; credential provider behaviour. Medium: Flatpak `~/.var/app/<id>/{config,data}` layout (Flatpak convention; Zed only reads the `FLATPAK_XDG_*` variables the runtime sets). Not determined: the serialisation format of `folder_paths` (a `PathList`), and whether any legacy `conversations/` data survives on old installs.
