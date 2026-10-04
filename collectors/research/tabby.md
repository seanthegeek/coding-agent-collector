# Tabby: on-disk paths

## 1. Source and evidence level

TabbyML/tabby at [`21b29048d7bcf6b94f9f482f2d0fd05efadfd19f`](https://github.com/TabbyML/tabby/commit/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f).
Source public: Apache-2.0 outside `ee/`, the Tabby Enterprise licence inside
it ([LICENSE:3-7](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/LICENSE#L3-L7); [ee/LICENSE:1-12](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/LICENSE#L1-L12)). Rust server, TypeScript
`tabby-agent` and VS Code client, Kotlin IntelliJ plugin. All claims from
source except the JetBrains settings directory, which is from JetBrains
documentation. Record schema: `analyzer/research/tabby.md`.

Tabby is a self-hosted server. On a developer workstation it runs as that
user (state under their home); in Docker the images set `TABBY_ROOT=/data`
([docker/Dockerfile.cuda:88](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/docker/Dockerfile.cuda#L88)), which is outside any home and
not covered by a home catalog. The editor plugins talk to the server; chat
history is server-side.

## 2. Per-user storage

**Server root `~/.tabby`.** `TABBY_ROOT` if set, else `home::home_dir()/.tabby`
([crates/tabby-common/src/path.rs:5-14](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/path.rs#L5-L14)). No platform branching: the
same name under the profile on Windows. The root is created with mode 0700
on Unix ([crates/tabby/src/main.rs:61-68](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby/src/main.rs#L61-L68)). Contents
([path.rs:28-54](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/path.rs#L28-L54)):

- `config.toml`: server configuration, `[[repositories]]` and
  `[model.*.http]` blocks ([crates/tabby-common/src/config.rs:18-38](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/config.rs#L18-L38), [164-168](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/config.rs#L164-L168), [300-316](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/config.rs#L300-L316)).
- `usage_anonymous_id`: a UUID for telemetry ([crates/tabby-common/src/usage.rs:20-26](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/usage.rs#L20-L26)).
- `events/YYYY-MM-DD.json`: JSON Lines (despite the extension) of every
  completion, view, select, dismiss and chat event, written in all modes
  ([crates/tabby/src/services/event.rs:16-41](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby/src/services/event.rs#L16-L41), [68-93](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby/src/services/event.rs#L68-L93)). Completion events
  carry the full prompt, code segments and generated text
  ([crates/tabby/src/services/completion.rs:410-421](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby/src/services/completion.rs#L410-L421)).
- `ee/db.sqlite` with `-wal`/`-shm` (release builds use the `prod` feature,
  [.github/workflows/release.yml:138](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/.github/workflows/release.yml#L138); source builds without it write
  `ee/dev-db.sqlite`) ([ee/tabby-webserver/src/path.rs:5-15](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-webserver/src/path.rs#L5-L15);
  [ee/tabby-db/src/lib.rs:165-176](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/src/lib.rs#L165-L176)). Users, chat threads, AI pages,
  completion statistics, integrations, OAuth and SMTP settings.
- `ee/db.backup-YYYYMMDD.sqlite`: a full copy taken before each schema
  migration ([lib.rs:189-221](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/src/lib.rs#L189-L221)). Older chats can survive here.
- `ee/jobs/<job id>/stdout.log` (`dev-jobs` in dev builds): background job
  output, repository indexing and sync ([path.rs:17-23](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-webserver/src/path.rs#L17-L23);
  [ee/tabby-webserver/src/service/background_job/helper/logger.rs:40-44](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-webserver/src/service/background_job/helper/logger.rs#L40-L44)).
- `models/<registry>/<model>/` (weights, `models.json`), relocatable with
  `TABBY_MODEL_CACHE_ROOT` ([path.rs:12-13](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/path.rs#L12-L13), [44-50](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/path.rs#L44-L50);
  [crates/tabby-common/src/registry.rs:39](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/registry.rs#L39), [113-116](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/registry.rs#L113-L116)).
- `index/`: the Tantivy code and document index ([path.rs:40-42](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/path.rs#L40-L42)).
- `repositories/<sanitised git url>/`: clones of indexed remote repositories;
  `file://` URLs are indexed in place ([config.rs:198-218](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/config.rs#L198-L218)).

The webserver (and so the database) runs unless the hidden
`--no-webserver` flag is given ([crates/tabby/src/serve.rs:112-114](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby/src/serve.rs#L112-L114), [125-145](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby/src/serve.rs#L125-L145)).

**Client `~/.tabby-client/agent`**, used by `tabby-agent`, the language
server behind the VS Code, IntelliJ, Vim and Eclipse plugins, from
`os.homedir()` on every OS:

- `config.toml`: `[server] endpoint`, `token`, request headers, proxy
  ([clients/tabby-agent/src/config/configFile.ts:19-28](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/clients/tabby-agent/src/config/configFile.ts#L19-L28), [161-164](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/clients/tabby-agent/src/config/configFile.ts#L161-L164)).
- `data.json`: `anonymousId`, cached server-provided config per endpoint,
  ignored issues ([clients/tabby-agent/src/dataStore/dataFile.ts:47-50](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/clients/tabby-agent/src/dataStore/dataFile.ts#L47-L50);
  [dataStore/index.ts:17-21](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/clients/tabby-agent/src/dataStore/index.ts#L17-L21)).
- `logs/YYYYMMDD/HHMMSS-<pid>*.log` plus `logs/audit.json`, rotated at
  10 MB, kept 30 days ([clients/tabby-agent/src/logger/fileLogger.ts:13-26](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/clients/tabby-agent/src/logger/fileLogger.ts#L13-L26)).

**VS Code extension `TabbyML.vscode-tabby`**
([clients/vscode/package.json:2-3](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/clients/vscode/package.json#L2-L3)) keeps its state in `globalState`
(`server.serverRecords` with per-endpoint `token`, `edit.recentlyCommand`,
[clients/vscode/src/Config.ts:41-43](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/clients/vscode/src/Config.ts#L41-L43), [55-66](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/clients/vscode/src/Config.ts#L55-L66), [139-145](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/clients/vscode/src/Config.ts#L139-L145)), that is in
`state.vscdb` under the `vscode` entry; it writes no `globalStorage` files.

**IntelliJ plugin** persists `intellij-tabby.xml` and
`intellij-tabby-command-history.xml`
([clients/intellij/.../settings/SettingsService.kt:11-13](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/clients/intellij/src/main/kotlin/com/tabbyml/intellijtabby/settings/SettingsService.kt#L11-L13);
[.../inlineChat/CommandHistory.kt:9-12](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/clients/intellij/src/main/kotlin/com/tabbyml/intellijtabby/inlineChat/CommandHistory.kt#L9-L12)); the settings hold
`serverEndpoint` but no token ([.../settings/SettingsState.kt:12](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/clients/intellij/src/main/kotlin/com/tabbyml/intellijtabby/settings/SettingsState.kt#L12)). The IDE stores them in
`options/` of its configuration directory: `~/.config/JetBrains/<product>`,
`~/Library/Application Support/JetBrains/<product>`,
`%APPDATA%\JetBrains\<product>`
([JetBrains docs](https://www.jetbrains.com/help/idea/directories-used-by-the-ide-to-store-settings-caches-plugins-and-logs.html)).

## 3. Credentials

- `~/.tabby/config.toml`: `api_key` for each HTTP model backend
  ([config.rs:300-316](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/config.rs#L300-L316)).
- `~/.tabby-client/agent/config.toml`: `server.token`, the user's Tabby API
  token ([configFile.ts:20-23](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/clients/tabby-agent/src/config/configFile.ts#L20-L23)).
- `~/.tabby/ee/db.sqlite` (and backups), plaintext unless noted
  ([ee/tabby-db/schema/schema.sql](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/schema/schema.sql)): `users.auth_token` (each
  user's API token) and `password_encrypted` (hash) ([:17-30](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/schema/schema.sql#L17-L30)),
  `registration_token` ([:9-15](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/schema/schema.sql#L9-L15)), `email_setting.smtp_password`
  ([:72-82](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/schema/schema.sql#L72-L82)), `oauth_credential.client_secret` ([:83-93](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/schema/schema.sql#L83-L93)),
  `refresh_tokens.token` ([:126-134](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/schema/schema.sql#L126-L134)), `integrations.access_token`
  (GitHub/GitLab tokens, [:142-152](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/schema/schema.sql#L142-L152)), `ldap_credential.bind_password`
  ([:249-266](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/schema/schema.sql#L249-L266)). The same file holds the chats, so collect it
  unflagged and redact by column.
- VS Code: endpoint tokens in `globalState` (`state.vscdb`), above.
- Keychain: not used by any component.

## 4. Exclusions

- `.tabby/models`: GGUF weights, gigabytes.
- `.tabby/index`: Tantivy index, rebuilt from sources.
- `.tabby/repositories`: git clones.

Keep `events/`, `ee/` (database, backups, job logs) and `config.toml`.
`.tabby-client/agent/logs` is bounded by rotation and records server
connection and completion request activity; keep it.

## 5. Project-local files

None. Neither the server nor `tabby-agent` writes into repositories.
Repositories to index are named in `config.toml` or in the database.

## 6. Where the project path is recorded

- `~/.tabby/config.toml`: `[[repositories]] git_url`; `file://` URLs are
  local project directories ([config.rs:164-168](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/config.rs#L164-L168), [216-218](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/config.rs#L216-L218)).
- `ee/db.sqlite`: `repositories.git_url` ([schema.sql:53-60](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/ee/tabby-db/schema/schema.sql#L53-L60)) and
  `provided_repositories.git_url` (SQLite, analyzer work).
- `events/*.json`: `segments.git_url` and `segments.filepath` per completion
  ([crates/tabby-common/src/api/event.rs:81-98](https://github.com/TabbyML/tabby/blob/21b29048d7bcf6b94f9f482f2d0fd05efadfd19f/crates/tabby-common/src/api/event.rs#L81-L98)); these are repository
  identities, not local roots.

## 7. Confidence

High: `~/.tabby` layout, env overrides, database file names, WAL,
pre-migration backups, table columns, event file naming and fields,
`~/.tabby-client/agent` files, VS Code `globalState` keys (source). Medium:
Windows `home_dir()` resolving to the profile directory (the `home` crate's
documented behaviour, not re-read here); the JetBrains `options/` location
(vendor docs). Not determined: Eclipse plugin storage; the size of `events/` on a busy server (no retention in the
writer, so it grows without bound).
