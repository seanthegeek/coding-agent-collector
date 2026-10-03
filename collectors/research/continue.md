# Continue: on-disk paths

## 1. Source and evidence level

Open source. continuedev/continue at `5522c6f44ca0ac3528b37244818fbfa39b5af470`
(clone `scratchpad/repos/continue`). All claims from source. Covers the VS Code
extension `continue.continue`, the JetBrains plugin (same core via
`binary/`) and the `cn` CLI (`extensions/cli`). Record schemas:
`analyzer/research/continue.md`.

## 2. Per-user storage

One global dir on every OS, `~/.continue`, from `os.homedir()`; env
`CONTINUE_GLOBAL_DIR` relocates it (relative values resolve against cwd)
(`core/util/paths.ts:27-35`; `extensions/cli/src/env.ts:10-11`). No XDG,
Library or AppData paths.

Under `~/.continue`:

- `sessions/<sessionId>.json`, `sessions/sessions.json` (`paths.ts:78-112`;
  `core/util/history.ts:112-120`); the CLI writes the same dir
  (`extensions/cli/src/session.ts:50-67`).
- `config.yaml`, `config.json`, `config.ts`, `tsconfig.json`,
  `package.json`, `types/core/index.d.ts`, `out/config.js`
  (`paths.ts:114-177`), `.continuerc.json` (`paths.ts:210-225`),
  `.continueignore` (`paths.ts:58-67`), `sharedConfig.json` (`paths.ts:98-100`),
  `.env` (`paths.ts:377-378`), `.local`/`.staging` environment markers
  (`paths.ts:462-468`).
- `.configs/<hostname>/config.json`, `config.js` for remote configs
  (`paths.ts:342-375`).
- `index/index.sqlite`, `index/lancedb/`, `index/autocompleteCache.sqlite`,
  `index/docs.sqlite`, `index/globalContext.json` (`paths.ts:86-95,326-340`).
- `dev_data/devdata.sqlite`, `dev_data/<schema>/<event>.jsonl` with events
  `chatInteraction`, `chatFeedback`, `toolUsage`, `tokensGenerated`,
  `autocomplete`, `editInteraction`, `quickEdit`, `editOutcome`,
  `nextEditOutcome` (`paths.ts:228-249`;
  `packages/config-yaml/src/schemas/data/index.ts`); legacy `dev_data/*.jsonl`
  (`paths.ts:440-461`).
- `logs/core.log`, `logs/prompt.log` (`paths.ts:385-399`); CLI logs in
  `logs/` too (`extensions/cli/src/util/logger.ts:17`).
- `.utils/.chromium-browser-snapshots`, `.utils/esbuild`, `.utils/repo_map.txt`
  (`paths.ts:46-56,433-438`), `.diffs/` (`paths.ts:470-477`),
  `.migrations/<id>` markers (`paths.ts:293-310`), `node_modules/`.
- Blocks folders shared by IDE and CLI: `rules/`, `prompts/`, `agents/`,
  `mcpServers/`, `skills/`, plus any `<name>/` read by
  `getGlobalFolderWithName` (`paths.ts:401-406`;
  `core/config/loadLocalAssistants.ts:108-121`;
  `core/context/mcp/json/loadJsonMcpConfigs.ts:43`;
  `extensions/cli/src/util/loadMarkdownSkills.ts:98`;
  `extensions/cli/src/systemMessage.ts:93`).
- CLI only: `auth.json`, `input_history.json`, `permissions.yaml`,
  `.onboarding_complete` (`extensions/cli/src/auth/authEnv.ts:5`;
  `util/inputHistory.ts:6`; `permissions/permissionsYamlLoader.ts:12`;
  `onboarding.ts:108`).

VS Code `globalStorage/continue.continue/`: `<key>.bin` AES-GCM blobs
written by the extension's own secret store, key material in VS Code
`context.secrets` (`extensions/vscode/src/stubs/SecretStorage.ts:7-23,41-58,100`).

## 3. Credentials

- `~/.continue/auth.json` (CLI): `userId`, `userEmail`, `accessToken`,
  `refreshToken`, `expiresAt`, `organizationId`
  (`extensions/cli/src/auth/workos.ts:28-40`).
- `config.yaml` / `config.json` / `config.ts` / `.configs/*/config.js*` embed
  provider `apiKey` values; `.env` holds the `${{ secrets.X }}` inputs
  (`paths.ts:377-383`).
- `index/globalContext.json` key `mcpOauthStorage[server].tokens` and
  `clientInformation` (`core/util/GlobalContext.ts:50-53`); it shares the
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
(`loadLocalAssistants.ts:22-23,112-115`; `extensions/vscode/src/activation/activate.ts:42`;
`createNewAssistantFile.ts:55`; `promptFiles/index.ts:4`;
`tools/definitions/createRuleBlock.ts:65`); `.continuerc.json`
(`core/config/json/loadRcConfigs.ts:18`; `loadLocalAssistants.ts:18`);
`.continueignore` (`core/core.ts:1287`). No per-project database.

## 6. Project path

`sessions/sessions.json[].workspaceDirectory` and
`sessions/<id>.json.workspaceDirectory` (`history.ts:105-120,160-172`).
Empty string for sessions created without a workspace.

## 7. Catalog review

Home: three `*/User/globalStorage/continue.continue`: confirmed (`.bin`
secret blobs). `.continue`: confirmed.

Project: `.continue`, `.continuerc.json`: confirmed. Missing `.continueignore`.

Excluded: all nine entries confirmed (`paths.ts:46-56,146-173,236,293,326-340,470`).

Credential: `.continue/auth*.json`, `.env`, `config.yaml`, `config.json`,
`config.ts`, `.configs/*/config.js*`, `mcpServers/*`,
`index/globalContext.json`: confirmed.

Add:

```
project|.continueignore
```

Doubtful: `.continue/mcpServers/*` crosses `/`, so it also flags project
`.continue/mcpServers/*` files, which is the intent. Consider adding
`*/globalStorage/continue.continue/*.bin` as a credential glob: encrypted,
but it is the hub token.

## 8. Confidence

High: every `~/.continue` path, `auth.json` fields, `workspaceDirectory`,
`.bin` secret blobs. Medium: list of project `.continue/<subdir>` names (the
loader accepts any subdir passed by callers). Not determined: whether the
JetBrains plugin writes anything outside `~/.continue` (its `binary/` uses
the same `core/util/paths.ts`).
