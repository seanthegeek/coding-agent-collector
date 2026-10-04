# Continue: on-disk paths

## 1. Source and evidence level

Open source. continuedev/continue at [`5522c6f44ca0ac3528b37244818fbfa39b5af470`](https://github.com/continuedev/continue/commit/5522c6f44ca0ac3528b37244818fbfa39b5af470)
(clone `scratchpad/repos/continue`). All claims from source. Covers the VS Code
extension `continue.continue`, the JetBrains plugin (same core via
`binary/`) and the `cn` CLI (`extensions/cli`). Record schemas:
[`analyzer/research/continue.md`](../../analyzer/research/continue.md).

## 2. Per-user storage

One global dir on every OS, `~/.continue`, from `os.homedir()`; env
`CONTINUE_GLOBAL_DIR` relocates it (relative values resolve against cwd)
([`core/util/paths.ts:27-35`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L27-L35); [`extensions/cli/src/env.ts:10-11`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/env.ts#L10-L11)). No XDG,
Library or AppData paths.

Under `~/.continue`:

- `sessions/<sessionId>.json`, `sessions/sessions.json` ([`paths.ts:78-112`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L78-L112);
  [`core/util/history.ts:112-120`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/history.ts#L112-L120)); the CLI writes the same dir
  ([`extensions/cli/src/session.ts:50-67`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/session.ts#L50-L67)).
- `config.yaml`, `config.json`, `config.ts`, `tsconfig.json`,
  `package.json`, `types/core/index.d.ts`, `out/config.js`
  ([`paths.ts:114-177`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L114-L177)), `.continuerc.json` ([`paths.ts:210-225`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L210-L225)),
  `.continueignore` ([`paths.ts:58-67`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L58-L67)), `sharedConfig.json` ([`paths.ts:98-100`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L98-L100)),
  `.env` ([`paths.ts:377-378`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L377-L378)), `.local`/`.staging` environment markers
  ([`paths.ts:462-468`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L462-L468)).
- `.configs/<hostname>/config.json`, `config.js` for remote configs
  ([`paths.ts:342-375`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L342-L375)).
- `index/index.sqlite`, `index/lancedb/`, `index/autocompleteCache.sqlite`,
  `index/docs.sqlite`, `index/globalContext.json` ([`paths.ts:86-95`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L86-L95),[`326-340`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L326-L340)).
- `dev_data/devdata.sqlite`, `dev_data/<schema>/<event>.jsonl` with events
  `chatInteraction`, `chatFeedback`, `toolUsage`, `tokensGenerated`,
  `autocomplete`, `editInteraction`, `quickEdit`, `editOutcome`,
  `nextEditOutcome` ([`paths.ts:228-249`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L228-L249);
  [`packages/config-yaml/src/schemas/data/index.ts`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/packages/config-yaml/src/schemas/data/index.ts)); legacy `dev_data/*.jsonl`
  ([`paths.ts:440-461`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L440-L461)).
- `logs/core.log`, `logs/prompt.log` ([`paths.ts:385-399`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L385-L399)); CLI logs in
  `logs/` too ([`extensions/cli/src/util/logger.ts:17`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/util/logger.ts#L17)).
- `.utils/.chromium-browser-snapshots`, `.utils/esbuild`, `.utils/repo_map.txt`
  ([`paths.ts:46-56`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L46-L56),[`433-438`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L433-L438)), `.diffs/` ([`paths.ts:470-477`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L470-L477)),
  `.migrations/<id>` markers ([`paths.ts:293-310`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L293-L310)), `node_modules/`.
- Blocks folders shared by IDE and CLI: `rules/`, `prompts/`, `agents/`,
  `mcpServers/`, `skills/`, plus any `<name>/` read by
  `getGlobalFolderWithName` ([`paths.ts:401-406`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L401-L406);
  [`core/config/loadLocalAssistants.ts:108-121`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/config/loadLocalAssistants.ts#L108-L121);
  [`core/context/mcp/json/loadJsonMcpConfigs.ts:43`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/context/mcp/json/loadJsonMcpConfigs.ts#L43);
  [`extensions/cli/src/util/loadMarkdownSkills.ts:98`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/util/loadMarkdownSkills.ts#L98);
  [`extensions/cli/src/systemMessage.ts:93`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/systemMessage.ts#L93)).
- CLI only: `auth.json`, `input_history.json`, `permissions.yaml`,
  `.onboarding_complete` ([`extensions/cli/src/auth/authEnv.ts:5`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/auth/authEnv.ts#L5);
  [`util/inputHistory.ts:6`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/util/inputHistory.ts#L6); [`permissions/permissionsYamlLoader.ts:12`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/permissions/permissionsYamlLoader.ts#L12);
  [`onboarding.ts:108`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/onboarding.ts#L108)).

VS Code `globalStorage/continue.continue/`: `<key>.bin` AES-GCM blobs
written by the extension's own secret store, key material in VS Code
`context.secrets` ([`extensions/vscode/src/stubs/SecretStorage.ts:7-23`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/vscode/src/stubs/SecretStorage.ts#L7-L23),[`41-58`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/vscode/src/stubs/SecretStorage.ts#L41-L58),[`100`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/vscode/src/stubs/SecretStorage.ts#L100)).

## 3. Credentials

- `~/.continue/auth.json` (CLI): `userId`, `userEmail`, `accessToken`,
  `refreshToken`, `expiresAt`, `organizationId`
  ([`extensions/cli/src/auth/workos.ts:28-40`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/cli/src/auth/workos.ts#L28-L40)).
- `config.yaml` / `config.json` / `config.ts` / `.configs/*/config.js*` embed
  provider `apiKey` values; `.env` holds the `${{ secrets.X }}` inputs
  ([`paths.ts:377-383`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts#L377-L383)).
- `index/globalContext.json` key `mcpOauthStorage[server].tokens` and
  `clientInformation` ([`core/util/GlobalContext.ts:50-53`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/GlobalContext.ts#L50-L53)); it shares the
  `index/` dir with the embedding store.
- `mcpServers/*.yaml|json` can embed headers and env.
- VS Code: hub session token in `globalStorage/continue.continue/*.bin`,
  decryptable only with the key in the editor's `state.vscdb`.
- No OS keychain use by the core.

## 4. Exclude

`.continue/index/lancedb`, `.continue/index/*.sqlite`, `.continue/.utils`,
`.continue/node_modules`, `.continue/out`, `.continue/types`,
`.continue/.diffs`, `.continue/.migrations`, `.continue/dev_data/devdata.sqlite`.
Keep `dev_data/**/*.jsonl` (prompts, tool usage), `logs/prompt.log`,
`index/globalContext.json`.

## 5. Project-local

`.continue/<subdir>/*.yaml|md` for `rules`, `prompts`, `agents`,
`mcpServers`, `skills`, `models`, `context`, `docs`, `data`
([`loadLocalAssistants.ts:22-23`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/config/loadLocalAssistants.ts#L22-L23),[`112-115`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/config/loadLocalAssistants.ts#L112-L115); [`extensions/vscode/src/activation/activate.ts:42`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/extensions/vscode/src/activation/activate.ts#L42);
[`createNewAssistantFile.ts:55`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/config/createNewAssistantFile.ts#L55); [`promptFiles/index.ts:4`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/promptFiles/index.ts#L4);
[`tools/definitions/createRuleBlock.ts:65`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/tools/definitions/createRuleBlock.ts#L65)); `.continuerc.json`
([`core/config/json/loadRcConfigs.ts:18`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/config/json/loadRcConfigs.ts#L18); [`loadLocalAssistants.ts:18`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/config/loadLocalAssistants.ts#L18));
`.continueignore` ([`core/core.ts:1287`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/core.ts#L1287)). No per-project database.

## 6. Project path

`sessions/sessions.json[].workspaceDirectory` and
`sessions/<id>.json.workspaceDirectory` ([`history.ts:105-120`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/history.ts#L105-L120),[`160-172`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/history.ts#L160-L172)).
Empty string for sessions created without a workspace.

## 7. Confidence

High: every `~/.continue` path, `auth.json` fields, `workspaceDirectory`,
`.bin` secret blobs. Medium: list of project `.continue/<subdir>` names (the
loader accepts any subdir passed by callers). Not determined: whether the
JetBrains plugin writes anything outside `~/.continue` (its `binary/` uses
the same [`core/util/paths.ts`](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/core/util/paths.ts)).
