# factory-droid (Factory Droid CLI)

## 1. Source and evidence level

- Closed source. Installer `https://app.factory.ai/cli` (`scratchpad/factory-install.sh`, read only) pins `VER="0.233.0"` and downloads `https://downloads.factory.ai/factory-cli/releases/0.233.0/<os>/<arch>/droid` into `~/.local/bin/droid` (lines 64-66, 106). Windows installer `https://app.factory.ai/cli/windows` (`scratchpad/factory-install.ps1`) fetches `droid.exe` into `%USERPROFILE%\bin` (lines 60-62, 105). No npm package.
- Binary: `linux/x64/droid` 0.233.0, 275,543,520 bytes, sha256 `744a5c50…f7ab8` matching the published `.sha256`; bun-compiled ELF. Evidence level **B** = `strings -n 8` (`scratchpad/npm/droid.strings`, 8-bit table holds the minified code) and UTF-16 (`droid.strings16`).
- Evidence level **D** = docs fetched as Markdown from `https://docs.factory.com/<page>.md` (`scratchpad/factory-docs/`, index `https://docs.factory.ai/llms.txt`).
- The Factory-AI/factory GitHub repo is docs only (prior finding; not re-cloned).

## 2. Per-user storage

Home resolution (B): `getFactoryHome(){return FACTORY_HOME_OVERRIDE ?? HOME ?? USERPROFILE}`, `getFactoryDirName(){return ".factory"}` (`.factory-dev` in dev builds); helper `Je(r,...)=join(home,".factory",r,...)`. Same layout on Linux, macOS and Windows (`droid-cli_settings.md:21-22`: `~/.factory/settings.json`, `%USERPROFILE%\.factory\settings.json`). The known top-level directory list in the binary: `Sq=["missions","missionsV2","repl-runs","specs","sessions","logs","cache","artifacts","temp","snapshots","crons","skills","droids","commands","plugins","updates","mermaid","automations","software-factory","worktree-setups","state","telemetry","generated-images"]`.

`~/.factory/` files and directories:

- `settings.json`, `settings.local.json` (D `droid-cli_settings.md:28-33`), legacy `config.json` with `custom_models` (`model-independence_byok.md:46`), `mcp.json` (`harness_mcp.md:164`), `hooks.json` (`harness_hooks.md:20`), `org-managed-settings.json`, `host.json`, `computer.json` (B list `bf`).
- `sessions/`: transcripts `sessions/<projectKey>/<sessionId>.jsonl` with sidecar `<sessionId>.settings.json`; legacy flat `sessions/<id>.jsonl` and `sessions/btw/<id>.jsonl` (B, `CREATE TABLE sessions` comment; `sessionFileExists`). `projectKey` = `"-" + realpath(cwd)` with leading `/` removed and every `/` → `-` (B, function `Ji`), e.g. `sessions/-Users-enoreyes-code-work-myapp/*.jsonl` (help text). `sessions/.favorites`.
- `cache/session-index/index.db` SQLite (`En(e)=join(e,"cache","session-index","index.db")`; tables `sessions(session_id, project_key, cwd, title, org_id, owner, mission, …)`, `session_ingest`, `meta`), `cache/session-discovery-index.json`, `cache/feature-flags.json`, `cache/changelog.json`, `cache/sounds/*.wav`.
- `state/history.json` prompt history (migrated from `~/.factory/history.json`), `state/mission-readiness-warnings-shown.json`.
- `logs/`: `droid-log-single.log`, `console.log`, `factoryd.log`, `daemon-critical-error.json`, `daemon-stderr.log`; rotation by `FACTORY_LOG_MAX_BYTES`/`FACTORY_LOG_MAX_DAYS`, override `FACTORY_LOG_FILE` (B). Hooks example appends `~/.factory/bash-command-log.txt` (D).
- `droids/`, `skills/<name>/SKILL.md`, `commands/`, `output-styles/`, `plugins/`, `automations/<id>/`, `specs/` (`specSaveDir`), `docs/`, `artifacts/`, `missions/<sessionId>/` (`mission.md`, `features.json`, `progress_log.jsonl`), `repl-runs/<sha256>/`, `software-factory/workstreams/…/{repos,worktrees,review-sessions}`, `worktrees/` (default `worktreeDirectory`, D `cli-reference.md:379`), `ide/` (IDE lock/pid files), `certs/`, `bin/` (`keytar.node`, `rg`, `agent-browser`, `script-runtime-<hash>/`), `tools/agent-browser/`, `snapshots/content/` (file snapshot store), `temp/env/droid-env-<session>-*.sh` (environment dumps for hooks), `generated-images/`, `updates/` (staged binaries), `telemetry/`.
- No `%APPDATA%` or `Library/Application Support` paths exist in the binary.

## 3. Credentials

All under `~/.factory/` (B, class `Ne`, `IH()` maps list `Uf` onto `join(home,".factory")`):

- `auth.v2.file` encrypted credentials; key in OS keyring (`keytar`, service "Factory CLI", account `auth-encryption-key`) with marker `auth.v2.keyring`; macOS alternative `security` CLI (`login-keychain-v2`); when the keyring is unavailable or `disableKeyring` is set the key is written to `auth.v2.key` ("auth.v2.file exists but auth.v2.key is missing"). Legacy `auth.encrypted`, and legacy plaintext `auth.json` (still in the cleanup list `["auth.json","config.json","mcp.json","settings.json"]`).
- `prem-auth/<sha256(origin)>/credentials.json` for Prem deployments.
- `mcp-oauth.v2.file` + `mcp-oauth.v2.key` MCP OAuth tokens (D `harness_mcp.md:177`: keyring "or a fallback file").
- `settings.json`/`settings.local.json`/`config.json`: `customModels[].apiKey` may be literal or `${VAR}` (D `byok.md:20-46`); `mcp.json` headers/`oauth.clientSecret` (D `harness_mcp.md:180`). `FACTORY_API_KEY` env var.
- `temp/env/*.sh` dumps process environment (may include keys).

## 4. Exclusions

`.factory/updates`, `.factory/bin`, `.factory/tools`, `.factory/snapshots`, `.factory/worktrees`, `.factory/generated-images`, `.factory/cache/sounds`, `.factory/software-factory/*/*/repos`, `.factory/software-factory/*/*/worktrees`, `.factory/temp` (see section 3 on `temp/env`).

## 5. Project-local files

`.factory/` at git root and in nested folders (D `hierarchical-settings.md:15-39`): `settings.json`, `settings.local.json`, `mcp.json`, `hooks.json` (legacy `hooks/hooks.json`, `hooks/hooks.migrated.json`), `hooks/*.sh|py`, `droids/*.md`, `skills/*/SKILL.md`, `commands/*`, `output-styles/*.md`, `worktree-setups/*.yaml`, `prompts/`, `docs/`, `system.md`, `pr-risk-thresholds.json`, `threat-model.md`, `video/wiki/`, `automations/`. `AGENTS.md` (also reads `CLAUDE.md`, `.agents/`, `.agent/`, `.claude/` dirs: B arrays `WM`, `h`). `.factory-plugin/plugin.json`, `marketplace.json` (D). `.droid.yaml` is documented only as "an older project configuration surface" (`settings.md:37`) and does not occur in the binary. `DROID.md` occurs nowhere.

## 6. Project path records

- Transcript first line: JSON with `type:"session_start"`, `cwd`, optional `lastCwd` (B, `a.type!=="session_start"`, `a.lastCwd`).
- Directory name `sessions/<projectKey>` encodes cwd (ambiguous when the path contains `-`).
- `cache/session-index/index.db` table `sessions`, columns `project_key`, `cwd`; `cache/session-discovery-index.json` entries `cwd`.

## 7. Confidence

High: `~/.factory` on all OSes, `FACTORY_HOME_OVERRIDE`, session layout and projectKey encoding, `index.db` path and columns, `auth.v2.*` and `mcp-oauth.v2.*` names, keyring-with-file-fallback, `state/history.json`, log file names, exclusion dirs. Medium: `software-factory` subtree sizes; `ide/` contents; `prem-auth` layout (from strings, matches prior finding). Low: whether `auth.json` is still written by 0.233.0 (only in cleanup list). Not determined: full transcript JSONL schema beyond the first line; Windows keyring backend (keytar → Credential Manager assumed); whether `%USERPROFILE%\bin\droid.exe` is the only Windows binary location.
