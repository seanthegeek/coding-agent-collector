# n8n: on-disk paths

This document came out of the agent framework sweep for issue #64; see
[frameworks.md](frameworks.md) for the frameworks that got no catalog line.
There is no analyzer document yet.

## 1. Source and evidence level

n8n-io/n8n, commit
[`0e1c7549997f43053fda83534b597875b0310df6`](https://github.com/n8n-io/n8n/commit/0e1c7549997f43053fda83534b597875b0310df6).
The workflow automation server with AI Agent nodes, plus
`@n8n/computer-use`, a local tool gateway for the n8n Assistant. Licence:
Sustainable Use License, with `.ee.` files under the enterprise licence
([LICENSE.md:1-14](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/LICENSE.md#L1-L14)).
All claims are from source unless marked inferred; nothing was installed
or run.

n8n executes tools and shell commands on the host:

- The Execute Command node runs `spawn(command, {shell: true})`
  ([ExecuteCommand.node.ts:48](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/nodes-base/nodes/ExecuteCommand/ExecuteCommand.node.ts#L48)).
  It is excluded by default through `NODES_EXCLUDE`
  ([nodes.config.ts:32-39](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/config/src/configs/nodes.config.ts#L32-L39)).
- The Code node runs through task runners in `internal` mode by default,
  which means child processes on the host
  ([runners.config.ts:16-17](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/config/src/configs/runners.config.ts#L16-L17)).
- computer-use exposes `shell_execute`, file and input tools to the agent;
  shell is denied by default
  ([computer-use README.md:21](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/computer-use/README.md#L21)).

## 2. Per-user storage

The n8n folder is `N8N_USER_FOLDER`, otherwise `HOME` (or `USERPROFILE`
on Windows), with `.n8n` appended: `~/.n8n` on every OS
([config/src/utils/utils.ts:7-11](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/config/src/utils/utils.ts#L7-L11)).

| Path | Holds | Default or opt-in |
| --- | --- | --- |
| `.n8n/database.sqlite` | tables `execution_entity`, `execution_data` (run data), `credentials_entity` (encrypted), `workflow_entity`, `chat_hub_sessions`, `chat_hub_messages` ([database.config.ts:123-125](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/config/src/configs/database.config.ts#L123-L125), [db-connection-options.ts:82](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/db/src/connection/db-connection-options.ts#L82), [SeparateExecutionData.ts:8](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/db/src/migrations/sqlite/1690000000010-SeparateExecutionData.ts#L8), [chat-hub-message.entity.ts:15](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/cli/src/modules/chat-hub/chat-hub-message.entity.ts#L15), [chat-hub-session.entity.ts:35](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/cli/src/modules/chat-hub/chat-hub-session.entity.ts#L35)) | default |
| `.n8n/config` | JSON holding `encryptionKey` ([instance-settings.ts:60](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/core/src/instance-settings/instance-settings.ts#L60), [355-357](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/core/src/instance-settings/instance-settings.ts#L355-L357)) | default |
| `.n8n/storage` (legacy `.n8n/binaryData`) | binary data from executions ([storage.config.ts:37](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/core/src/storage.config.ts#L37), [74-85](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/core/src/storage.config.ts#L74-L85)) | default |
| `.n8n/n8nEventLog*.log`, `.n8n/crash.journal` | audit event log, crash journal ([event-bus.config.ts:17](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/config/src/configs/event-bus.config.ts#L17), [log-writer.ts:87-92](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/cli/src/eventbus/message-event-bus-writer/message-event-bus-log-writer.ts#L87-L92), [crash-journal.ts:21](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/cli/src/crash-journal.ts#L21)) | default |
| `.n8n/nodes`, `.n8n/custom`, `.n8n/node-definitions`, `.n8n/n8n-sdk-templates` | community and custom nodes, generated definitions, template cache ([instance-settings.ts:52-58](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/core/src/instance-settings/instance-settings.ts#L52-L58), [instance-ai.adapter.service.ts:937](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/cli/src/modules/instance-ai/instance-ai.adapter.service.ts#L937)) | default |
| `.n8n/git`, `.n8n/ssh/key` | source-control checkout and SSH private key ([constants.ts:2](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/cli/src/modules/source-control.ee/constants.ts#L2), [29-30](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/cli/src/modules/source-control.ee/constants.ts#L29-L30)) | opt-in (enterprise source control) |
| `.cache/n8n/public` | static UI assets ([instance-settings.ts:49](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/core/src/instance-settings/instance-settings.ts#L49)) | default; noise, not collected |
| `.n8n-local-gateway/log` | computer-use log: every tool call with full arguments (`{tool, args}`), including `shell_execute` ([computer-use logger.ts:75-76](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/computer-use/src/logger.ts#L75-L76), [91-97](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/computer-use/src/logger.ts#L91-L97), [323-327](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/computer-use/src/logger.ts#L323-L327)) | default for computer-use users |
| `.n8n-gateway/settings.json` | computer-use permissions and resource grants ([config.ts:257-259](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/computer-use/src/config.ts#L257-L259), [settings-store.ts:104-117](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/computer-use/src/settings-store.ts#L104-L117)) | default for computer-use users |
| `Library/Application Support/n8n Gateway`, `AppData/Roaming/n8n Gateway` | tray app `settings.json`; inferred from Electron `userData` and `productName: 'n8n Gateway'`, macOS and Windows builds only ([local-gateway settings-store.ts:83](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/local-gateway/src/main/settings-store.ts#L83), [electron-builder.config.js:4](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/packages/@n8n/local-gateway/electron-builder.config.js#L4)) | inferred; no catalog line |

Docker: the named volume `n8n_data` is mounted at `/home/node/.n8n`
([README.md:29-30](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/README.md#L29-L30),
[docker/images/n8n/README.md:73](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/docker/images/n8n/README.md#L73)).
The `get-n8n.sh` installer uses `n8n-data`
([get-n8n-compose.yml:11-13](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/docker/get-n8n-compose.yml#L11-L13),
[88-89](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/docker/get-n8n-compose.yml#L88-L89))
with the project directory `./n8n`
([get-n8n.sh:23](https://github.com/n8n-io/n8n/blob/0e1c7549997f43053fda83534b597875b0310df6/docker/get-n8n.sh#L23)),
which gives the volume `n8n_n8n-data`. Both volumes hold the `.n8n`
layout at their root, so the `DOCKER_VOLUMES` lines are `*n8n_data` and
`*n8n-data`, with volume-relative exclusions and secret globs.

## 3. Credentials

- `.n8n/config` (`encryptionKey`) and `.n8n/ssh/*`: flagged, and in a
  volume the volume-relative `config` and `ssh/*`. The bare `config` glob
  matches only a file named `config` at the root of a collection base; the
  one other layout that has one is the retired Letta V1 server's
  `~/.letta/config` at the root of a `*letta*` volume
  ([letta.md](letta.md)), which is then also flagged. That is an accepted
  overmatch: flagging only adds `secret: true` and the `--no-secrets`
  skip.
- `database.sqlite` holds encrypted credentials and the history together,
  so it is collected unflagged; with `config` the `credentials_entity`
  rows can be decrypted.

## 4. Exclusions

`.n8n/nodes/node_modules`, `.n8n/custom/node_modules`,
`.n8n/node-definitions`, `.n8n/n8n-sdk-templates`, and the volume-relative
`nodes/node_modules`, `node-definitions` and `n8n-sdk-templates`.

## 5. Project-local files

None. Workflows are rows in the database.

## 6. Where the project path is recorded

Nowhere; n8n has no project concept on disk.

## 7. Confidence

High, apart from the Electron tray paths, which are inferred and have no
catalog line. Not determined: the tray app's Linux build (none is
configured).
