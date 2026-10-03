# Goose: on-disk paths

## 1. Source and evidence level

block/goose, open source, commit `591edd47cf2cfea4957d720c607cf2a4def8673d`. Platform mapping verified against `etcetera` 0.11.0 (`scratchpad/crates/etcetera-0.11.0`, the version in `Cargo.lock`). Electron userData locations are Electron documentation level, not goose source. Transcript schema is in `analyzer/research/goose.md`.

## 2. Per-user storage

`crates/goose/src/config/paths.rs:22-36` uses `etcetera::choose_app_strategy` with author `Block`, app `goose`. `etcetera/src/app_strategy.rs:157-164` picks `Windows` on Windows and `Xdg` everywhere else, including macOS. So:

- Linux and macOS: `~/.config/goose`, `~/.local/share/goose`, `~/.local/state/goose` (`XDG_*_HOME` honoured; `etcetera/src/app_strategy/xdg.rs:37-50`).
- Windows: `%APPDATA%\Block\goose\config`, `%APPDATA%\Block\goose\data`; no state dir, so state falls back to data (`paths.rs:32`; `etcetera/src/app_strategy/windows.rs:141-165`; `base_strategy/windows.rs:190-200`). Cache would be `%LOCALAPPDATA%\Block\goose\cache` but no caller uses it.
- `GOOSE_PATH_ROOT` (absolute only) replaces all of it with `<root>/config`, `<root>/data`, `<root>/state`, `<root>/.agents` (`paths.rs:9-17,40-46`).
- The comment at `paths.rs:19-21` names `~/Library/Application Support/Block/goose/` as a legacy macOS location; no migration code reads it, so it is historical only.

Config dir (`~/.config/goose`): `config.yaml` (`config/base.rs:34,200`), `secrets.yaml` (`base.rs:393-395`), `custom_providers/` (`config/declarative_providers.rs:23`), `permissions/` (`permission/permission_store.rs:41`), `recipes/` (`recipe/local_recipes.rs:16`), `skills/` (`skills/mod.rs:223`), `agents/` (`sources.rs:470`), `prompts/` (`prompt_template.rs:67`), `mcp-apps-cache/` (`goose_apps/cache.rs:35`), `adversary.md` (`security/adversary_inspector.rs:112`), `gateway/<platform>/<user_id>/` (`gateway/handler.rs:841-845`), `roaming_trust.json`, `roaming_peers.json` (`goose-cli/src/commands/roam.rs:40-46`), `roaming_node_key` (`goose-roaming/src/identity.rs:17,114-116`), `tls/` (`acp/transport/tls.rs:87-89`), legacy `history.txt` (`goose-cli/src/session/mod.rs:197`), and the provider token caches listed in section 3. System config: `/etc/goose/config.yaml`, `C:\ProgramData\goose\config.yaml` (`base.rs:163-169`).

Data dir (`~/.local/share/goose`): `sessions/sessions.db` (`session/session_manager.rs:29-30,960-962`) plus legacy `sessions/*.jsonl` (`session/legacy.rs:13-19`, imported at `session_manager.rs:1149`); `schedule.json`, `scheduled_recipes/` (`scheduler/common.rs:95-103`); `apps/<name>.html` agent-written apps (`agents/platform_extensions/apps.rs:57,137,250`); `models/` whisper weights (`dictation/whisper.rs:94`); `model_catalog/` (`model_catalog.rs:8`); `roam/serve.json`, `roam/serve.lock` (`goose-cli/src/cli.rs:1713`, `roam.rs:616`).

State dir (`~/.local/state/goose`): `logs/<component>/<date>/` and `logs/llm_request.<id>.jsonl` full request bodies (`logging.rs:117-136`, `providers/utils.rs:60-125`); `history.txt` CLI input history (`goose-cli/src/session/mod.rs:196`); `instance_id` (`instance_id.rs:9`); `telemetry_installation.json` (`posthog.rs:114`); `roaming_directory.json` (`roam.rs:37`); `codex/images/` temp (`providers/codex.rs:121`); claude-code system prompt temp files (`providers/claude_code.rs:397`).

Shared cross-agent dirs read by goose: `~/.agents/plugins`, `~/.agents/agents` (`paths.rs:33-35`), `~/.goose/agents`, `~/.claude/agents` (`sources.rs:467-468,541-542`).

Electron desktop: `productName` `Goose` (`ui/desktop/package.json:3`); writes `settings.json`, `logs/startup/`, `logs/main.log`, `recent-dirs.json` under `app.getPath('userData')` (`ui/desktop/src/main.ts:182-183`, `utils/logger.ts:6`, `utils/recentDirs.ts:5`). Electron userData is `~/.config/Goose`, `~/Library/Application Support/Goose`, `%APPDATA%\Goose`. The desktop talks to the same Rust config and data dirs.

## 3. Credentials

Secrets go to the OS keyring (service `goose`, `base.rs:31`) unless `GOOSE_DISABLE_KEYRING` is set or the keyring fails, then `~/.config/goose/secrets.yaml` (`base.rs:85-91,216-220,1163-1185`). `config.yaml` holds non-secret config but `GOOSE_PROVIDER__*` style values can be placed there. Provider token caches are always files under the config dir (`providers/provider_secrets.rs:113-150`): `githubcopilot/info.json` and `githubcopilot/<host>/info.json` (`githubcopilot.rs:181-184`), `chatgpt_codex/tokens.json`, `gemini_oauth/tokens.json`, `kimicode/token.json` and `kimicode/device_id`, `muse_code/token.json`, `huggingface/oauth/tokens.json` (`huggingface_auth.rs:19`), `databricks/oauth/` (`providers/oauth.rs:94-96`), `xai_oauth/tokens.json` (`xai_oauth.rs:106`). Also `roaming_node_key` (private identity key), `tls/` (private key, `tls.rs:91`), and `logs/llm_request.*.jsonl` which contain full prompts.

## 4. Exclusions

`.local/share/goose/models`, `.local/share/goose/model_catalog`, `.local/state/goose/codex`, `.config/goose/mcp-apps-cache`, `AppData/Roaming/Block/goose/data/models`, `AppData/Roaming/Block/goose/data/model_catalog`, `AppData/Roaming/Block/goose/data/codex`, Electron `*/Goose/Cache`, `Code Cache`, `GPUCache`, `DawnGraphiteCache`, `DawnWebGPUCache`, `blob_storage`. `apps/` is agent output (HTML written by the model), not a binary cache; excluding it is a judgement call.

## 5. Project-local files

`.goosehints` and `AGENTS.md` walked from cwd upward, overridable with `CONTEXT_FILE_NAMES` (`hints/load_hints.rs:10-17`); `.goose/memory/` (`goose-mcp/src/memory/mod.rs:212,541`), `.goose/recipes` (`summon.rs:376`, `ui/desktop/src/recipe/recipe_management.ts:80`), `.goose/agents`, `.agents/agents`, `.agents/recipes`, `.claude/agents` (`sources.rs:534-536`, `summon.rs:377`), `.goose/skills` (`ui/desktop/src/components/skills/SkillsView.tsx:31`). No per-project database. `.gooseignore` has no hits in current Rust source.

## 6. Where the project path is recorded

`sessions.db` table `sessions` column `working_dir TEXT NOT NULL` (`session_manager.rs:1028-1034`); legacy jsonl first line key `working_dir` (`legacy.rs:74`); desktop `recent-dirs.json` (`recentDirs.ts:5`), a plain-text source usable by `discover_projects`.

## 7. Catalog review

Home: `.config/goose`, `.local/share/goose`, `.local/state/goose` confirmed; `.config/Goose`, `Library/Application Support/Goose`, `AppData/Roaming/Goose` confirmed as Electron userData (documentation level); `AppData/Roaming/Block/goose` confirmed; `.goose` confirmed but only `~/.goose/agents` is read (`sources.rs:467`).
Project: `.goosehints`, `.goose` confirmed.
Excluded: `models`, `model_catalog`, `.local/state/goose/codex`, `AppData/.../data/models`, Electron caches confirmed; `.local/share/goose/apps` doubtful (agent-written content).
Credential: `secrets.yaml`, `config.yaml`, the seven token dirs, `roaming_node_key`, `tls/*`, `AppData/Roaming/Block/goose/config/secrets.yaml`, `llm_request.*` confirmed.

Add:
```
# home
goose|.agents
goose|Library/Application Support/Block/goose
# excluded
.config/goose/mcp-apps-cache
AppData/Roaming/Block/goose/data/model_catalog
AppData/Roaming/Block/goose/data/codex
# credential
.config/goose/xai_oauth/*
AppData/Roaming/Block/goose/config/config.yaml
AppData/Roaming/Block/goose/config/githubcopilot/*
AppData/Roaming/Block/goose/config/chatgpt_codex/*
AppData/Roaming/Block/goose/config/gemini_oauth/*
AppData/Roaming/Block/goose/config/kimicode/*
AppData/Roaming/Block/goose/config/muse_code/*
AppData/Roaming/Block/goose/config/huggingface/*
AppData/Roaming/Block/goose/config/databricks/*
AppData/Roaming/Block/goose/config/xai_oauth/*
AppData/Roaming/Block/goose/config/roaming_node_key
AppData/Roaming/Block/goose/config/tls/*
AppData/Roaming/Block/goose/data/logs/llm_request.*
```
Discovery: add `recent-dirs.json` under the three Electron dirs.

## 8. Confidence

High: Rust paths, Windows mapping, credential files. Medium: Electron userData names (convention, no explicit `setPath`); the `Block/goose` legacy macOS dir (comment only). Not determined: `.gooseignore`, whether `.goose` at home is ever written rather than read.
