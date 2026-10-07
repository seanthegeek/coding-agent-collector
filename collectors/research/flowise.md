# Flowise: on-disk paths

This document came out of the agent framework sweep for issue #64; see
[frameworks.md](frameworks.md) for the frameworks that got no catalog line.
There is no analyzer document yet.

## 1. Source and evidence level

FlowiseAI/Flowise, commit
[`9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb`](https://github.com/FlowiseAI/Flowise/commit/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb).
A Node.js visual agent and chatflow builder (`npx flowise start`, Docker).
Licence: Apache 2.0, except `packages/server/src/enterprise`, which is
commercial
([LICENSE.md:1-7](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/LICENSE.md#L1-L7)).
All claims are from source; nothing was installed or run.

Flowise executes tools on the host. Custom JavaScript functions and tools
run in-process in a vm2 `NodeVM` unless `E2B_APIKEY` is set
([components utils.ts:1594-1606](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/components/src/utils.ts#L1594-L1606),
[1791](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/components/src/utils.ts#L1791)),
and MCP stdio servers are spawned on the host, with an allow-list for
custom scripts
([MCP/core.ts:117](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/components/nodes/tools/MCP/core.ts#L117),
[248-258](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/components/nodes/tools/MCP/core.ts#L248-L258)).

## 2. Per-user storage

The home is `HOME`, or `USERPROFILE` on Windows
([server utils/index.ts:114-125](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/server/src/utils/index.ts#L114-L125)),
so `~/.flowise` is used on every OS.

| Path | Holds | Default or opt-in |
| --- | --- | --- |
| `.flowise/database.sqlite` | all app data: tables `chat_message` (`content`, `usedTools`, `agentReasoning`), `execution` (`executionData`), `credential` (`encryptedData`), `chat_flow`, `tool` (custom tool code), `custom_mcp_server`, and `login_sessions` ([DataSource.ts:16-30](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/server/src/DataSource.ts#L16-L30), [90-99](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/server/src/DataSource.ts#L90-L99), [Init.ts:6-16](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/server/src/database/migrations/sqlite/1693835579790-Init.ts#L6-L16), [AddExecutionEntity.ts:6](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/server/src/database/migrations/sqlite/1738090872625-AddExecutionEntity.ts#L6), [ChatMessage.ts:25-38](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/server/src/database/entities/ChatMessage.ts#L25-L38), [SessionPersistance.ts:88-97](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/server/src/enterprise/middleware/passport/SessionPersistance.ts#L88-L97)) | default (`DATABASE_TYPE` unset or `sqlite`) |
| `.flowise/encryption.key` | AES key for `credential.encryptedData` ([utils/index.ts:1580-1588](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/server/src/utils/index.ts#L1580-L1588)) | default |
| `.flowise/token_hash_secret.key`, `express_session_secret.key`, `jwt_auth_token_secret.key`, `jwt_refresh_token_secret.key` | auth signing secrets ([authSecrets.ts:29-56](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/server/src/enterprise/utils/authSecrets.ts#L29-L56), [utils/index.ts:1669-1671](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/server/src/utils/index.ts#L1669-L1671), [1726-1735](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/server/src/utils/index.ts#L1726-L1735)) | default |
| `.flowise/storage`, `.flowise/uploads` | chat uploads and generated files ([storageUtils.ts:50-53](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/components/src/storageUtils.ts#L50-L53), [utils/index.ts:2018-2022](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/server/src/utils/index.ts#L2018-L2022)) | default |
| `.flowise/vectorstore` | Faiss and SimpleStore indexes ([validator.ts:213-224](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/components/src/validator.ts#L213-L224)) | default when the node is used |

Logs are not under the home. They go to `<install>/packages/server/logs`
(or `LOG_PATH`), which for `npx` is inside the npx cache
([utils/config.ts:10](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/server/src/utils/config.ts#L10),
[services/log/index.ts:73-75](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/packages/server/src/services/log/index.ts#L73-L75)).

Docker: the README compose bind-mounts the host's `~/.flowise` to
`/home/node/.flowise`
([docker/docker-compose.yml:162-165](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/docker/docker-compose.yml#L162-L165)),
so the home line already covers it. The only named volume is `redis_data`,
in the queue compose
([docker-compose-queue-prebuilt.yml:9-10](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/docker/docker-compose-queue-prebuilt.yml#L9-L10),
[340-342](https://github.com/FlowiseAI/Flowise/blob/9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb/docker/docker-compose-queue-prebuilt.yml#L340-L342));
it is generic and not matched. An inferred `*flowise*` volume line, like
the inferred block for Tabby and others, was considered and not added:
the documented deployment uses a bind mount.

## 3. Credentials

- `.flowise/encryption.key` and the four `*_secret.key` files: flagged.
- `database.sqlite` holds encrypted credentials and the chat history
  together, so it is collected unflagged; with `encryption.key` the
  `credential` rows can be decrypted.

## 4. Exclusions

`.flowise/vectorstore`.

## 5. Project-local files

None. Flows are rows in `database.sqlite`.

## 6. Where the project path is recorded

Nowhere; Flowise has no project concept.

## 7. Confidence

High for every path and table (source). Nothing material was left
undetermined.
