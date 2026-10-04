# nanobot: on-disk paths

## 1. Source and evidence level

HKUDS/nanobot, commit [`acdae3d0ae2714b6dde672428e921dbf705c096f`](https://github.com/HKUDS/nanobot/commit/acdae3d0ae2714b6dde672428e921dbf705c096f)
(2026-10-04, PyPI package `nanobot-ai` version `0.3.5`, [`pyproject.toml:2-3`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/pyproject.toml#L2-L3)), MIT
([`LICENSE`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/LICENSE)), open source, Python. Every claim is source-level unless it
cites `docs/` in the same checkout. nanobot is a small personal-assistant
agent with a CLI, a WebUI and a gateway that connects chat channels
(Telegram, Discord, Feishu, WhatsApp, Matrix, QQ, WeChat and others under
`nanobot/channels/`). Transcript schema is in `analyzer/research/nanobot.md`.

## 2. Per-user storage

All paths derive from `Path.home()`, so the layout is `~/.nanobot` on Linux and
macOS and `%USERPROFILE%\.nanobot` on Windows; there is no XDG, Library or
AppData branch. The config file is `~/.nanobot/config.json` unless
`--config` selects another ([`nanobot/config/loader.py:20-39`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/loader.py#L20-L39)), and the
instance data directory is the config file's parent
([`nanobot/config/paths.py:20-27`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/paths.py#L20-L27)). The documented multi-instance pattern
is `~/.nanobot-<name>/config.json` with its own workspace
([`docs/multiple-instances.md:13-20`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/docs/multiple-instances.md#L13-L20)). Settings can also come from
`NANOBOT_*` environment variables ([`config/schema.py:665-668`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/schema.py#L665-L668)).

Under the data directory:

- `config.json`: providers, channels, MCP servers, agent defaults (section 3).
- `sessions/<workspace-id>/`: one directory per workspace, named by a 32-hex
  id, holding a `.workspace` marker file with the workspace path,
  `<base64url(session key)>.jsonl` transcripts, `<...>.checkpoint.json`
  runtime overlays, `.session-files.lock` and `.migration-conflicts/`
  ([`nanobot/session/manager.py:58-76`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L58-L76),[`448-477`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L448-L477),[`606-607`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L606-L607),[`777-779`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L777-L779),[`903-927`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L903-L927)).
- `webui/`: WebUI display transcripts `<key>.jsonl`, `<key>.segments/` with
  `manifest.json`, legacy `<key>.json`, plus `workspace-state.json`,
  `sidebar-state.json` ([`nanobot/webui/transcript.py:172-188`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/webui/transcript.py#L172-L188); [`webui/workspaces.py:45`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/webui/workspaces.py#L45); [`webui/sidebar_state.py:37`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/webui/sidebar_state.py#L37)).
- `cron/jobs.json` (legacy location, [`nanobot/cli/runtime_config.py:195-196`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/cli/runtime_config.py#L195-L196)), `logs/`,
  `media/<channel>/` received attachments ([`config/paths.py:30-48`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/paths.py#L30-L48)).
- `llm_usage.sqlite3`: table `llm_calls` with provider, model and UTC
  epoch-ms timestamps for every model call, WAL mode
  ([`nanobot/llm_usage/__init__.py:42`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/llm_usage/__init__.py#L42); [`llm_usage/store.py:190-222`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/llm_usage/store.py#L190-L222)).
- `pairing.json`: approved chat senders ([`nanobot/pairing/store.py:3`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/pairing/store.py#L3),[`33`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/pairing/store.py#L33)).
- `auth/xai.json`, `auth/mcp.json` (section 3), `whatsapp-auth/neonize.db`,
  `matrix-store/`, `weixin/`, `mochat/`, `linear/state.sqlite3` channel state
  ([`channels/whatsapp/runtime.py:75`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/channels/whatsapp/runtime.py#L75); [`channels/matrix/runtime.py:354`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/channels/matrix/runtime.py#L354); [`channels/weixin/runtime.py:378`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/channels/weixin/runtime.py#L378); [`channels/mochat/runtime.py:283`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/channels/mochat/runtime.py#L283); [`channels/linear/state.py:44`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/channels/linear/state.py#L44)).
- `mcp/<name>/` working directories for MCP presets ([`webui/mcp_presets_api.py:563`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/webui/mcp_presets_api.py#L563)),
  `cli-apps/` ([`apps/cli/service.py:428`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/apps/cli/service.py#L428)).
- `cache/tiktoken/`, `bin/tui/<version>/`, `run/executables/` (section 4).

Always under `~/.nanobot` regardless of `--config`: `history/cli_history`
(prompt_toolkit input history), legacy `sessions/<safe key>.jsonl`, the
default `workspace/`, and launchd logs `logs/<name>.launchd.log`
([`config/paths.py:51-71`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/paths.py#L51-L71); [`gateway/service.py:135-139`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/gateway/service.py#L135-L139)).

The **workspace** (default `~/.nanobot/workspace`, [`config/schema.py:117-120`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/schema.py#L117-L120))
holds the agent's instructions and memory: `AGENTS.md`, `SOUL.md`, `USER.md`
([`agent/context.py:92`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/agent/context.py#L92),[`194-202`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/agent/context.py#L194-L202)), `HEARTBEAT.md` (periodic tasks, [`cli/gateway_runtime.py:629`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/cli/gateway_runtime.py#L629)),
`memory/MEMORY.md`, `memory/history.jsonl`, legacy `memory/HISTORY.md`, cursors
`memory/.cursor` and `.dream_cursor` ([`agent/memory.py:76-91`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/agent/memory.py#L76-L91)), a dulwich git
repository versioning those files ([`agent/memory.py:89-91`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/agent/memory.py#L89-L91); [`utils/gitstore.py:56`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/utils/gitstore.py#L56)),
`skills/` ([`agent/skills.py:61`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/agent/skills.py#L61)), `cron/jobs.json` ([`cli/gateway_runtime.py:469`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/cli/gateway_runtime.py#L469)),
`.nanobot/workspace-id` ([`session/manager.py:529-534`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L529-L534)) and
`.nanobot/tool-results/` spilled tool output ([`utils/helpers.py:366-368`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/utils/helpers.py#L366-L368),[`639`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/utils/helpers.py#L639)). Older
releases kept `sessions/*.jsonl` inside the workspace; they are copied to the
data directory and removed ([`session/manager.py:806-855`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L806-L855)).

Persistence: systemd user unit `~/.config/systemd/user/nanobot-gateway.service`
or `~/Library/LaunchAgents/ai.nanobot.gateway.plist` ([`gateway/service.py:25`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/gateway/service.py#L25),[`86-87`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/gateway/service.py#L86-L87),[`135-136`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/gateway/service.py#L135-L136),[`227-236`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/gateway/service.py#L227-L236)). No Windows service.

## 3. Credentials

- `config.json`: `providers.<name>.apiKey` ([`config/schema.py:194-202`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/schema.py#L194-L202)), the API
  server `apiKey` ([`:340`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/schema.py#L340)), MCP server `env` ([`:370`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/schema.py#L370)), and channel
  secrets such as Feishu `appSecret` and `verificationToken`
  ([`channels/feishu/config.py:18-20`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/channels/feishu/config.py#L18-L20)) or Linear `clientSecret`
  ([`channels/linear/config.py:22-23`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/channels/linear/config.py#L22-L23)). Keys are camelCase via `to_camel`
  ([`config_base.py:9-15`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config_base.py#L9-L15)). `${VAR}` references are resolved from the
  environment ([`config/loader.py:196`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/loader.py#L196)).
- `auth/xai.json` (xAI OAuth, [`providers/xai_oauth.py:262`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/providers/xai_oauth.py#L262)) and `auth/mcp.json`
  (MCP OAuth, [`agent/tools/mcp_oauth.py:102`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/agent/tools/mcp_oauth.py#L102)).
- `whatsapp-auth/neonize.db` is a linked-device WhatsApp session; `matrix-store/`
  holds Matrix session and encryption state.
- No keychain use found.

## 4. Exclude

`bin/tui` (downloaded TUI binaries, [`cli/tui_launcher.py:261`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/cli/tui_launcher.py#L261)), `run/executables`
([`:248`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/cli/tui_launcher.py#L248)), `cache/tiktoken` ([`utils/token_encoding.py:20`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/utils/token_encoding.py#L20)). Nothing else is
large by design; `media/` can grow but is evidence.

## 5. Project-local files

A user can point `--workspace` at a repository, which then receives the
workspace files of section 2, notably `.nanobot/` and `memory/`. `AGENTS.md`
is read from the active workspace, `SOUL.md` and `USER.md` from the configured
one ([`agent/context.py:194-202`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/agent/context.py#L194-L202)). No per-project database.

## 6. Where the project path is recorded

- `sessions/<workspace-id>/.workspace`: absolute workspace path, one line
  ([`session/manager.py:606-607`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/session/manager.py#L606-L607)).
- `config.json` `agents.defaults.workspace` ([`config/schema.py:117-120`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/schema.py#L117-L120),[`188-191`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/schema.py#L188-L191),[`428`](https://github.com/HKUDS/nanobot/blob/acdae3d0ae2714b6dde672428e921dbf705c096f/nanobot/config/schema.py#L428)).
- `webui/workspace-state.json` (WebUI workspace list; keys not traced).

## 7. Catalog proposal

```
nanobot|.nanobot
nanobot|.nanobot-*
nanobot|Library/LaunchAgents/ai.nanobot.*
nanobot|.config/systemd/user/nanobot-*
```

```
project|.nanobot
project|SOUL.md
project|USER.md
project|HEARTBEAT.md
project|memory/MEMORY.md
project|memory/history.jsonl
project|memory/HISTORY.md
```

```
.nanobot*/bin
.nanobot*/run
.nanobot*/cache
```

```
.nanobot*/config.json
.nanobot*/auth/*
.nanobot*/whatsapp-auth/*
.nanobot*/matrix-store/*
```

Discovery sources:

```
.nanobot*/sessions/*/.workspace     (whole file is the path)
.nanobot*/config.json               workspace
```

## 8. Confidence

High: every path in sections 2 to 6, read from constants in the cited files.
Medium: that `matrix-store/` holds credentials (inferred from its role; not
read); `.nanobot-*` as an instance naming convention comes from docs, and any
other `--config` location is missed. `project|memory/...` lines assume the
collector's project globs accept a sub-path, as `.github/...` entries do. Not
determined: the contents of `webui/workspace-state.json`, `weixin/` and
`mochat/` state; whether the Docker image's `/root/.nanobot` differs.
