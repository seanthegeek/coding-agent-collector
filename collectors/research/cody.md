# Sourcegraph Cody: on-disk paths

Catalog agent: `cody`. Cody is Sourcegraph's coding assistant, shipped as
a VS Code extension (`sourcegraph.cody-ai`), a JetBrains plugin and a
`cody` CLI; the last two run the same TypeScript "agent" in a Node
process. **In VS Code, chat history and the access token are not files:
they are rows in the editor's `User/globalStorage/state.vscdb`**, which
the `vscode` entries already collect. The extension's own
`globalStorage` folder holds only a local search index. The JetBrains
plugin and CLI keep the same chat history as files under an `env-paths`
directory named `Cody-nodejs`. Transcript schema is in
[`analyzer/research/cody.md`](../../analyzer/research/cody.md).

## 1. Source and evidence level

sourcegraph/cody-public-snapshot, commit
[`8e20ac6c1460c08b0db581c0204658112a246eda`](https://github.com/sourcegraph/cody-public-snapshot/commit/8e20ac6c1460c08b0db581c0204658112a246eda)
(2025-08-01), VS Code extension version 1.116.0
([`vscode/package.json:3-7`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/package.json#L3-L7)). **The source
is frozen.** Sourcegraph moved Cody to a private repository and this is the
copy taken just before
([`README.md:1-5`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/README.md#L1-L5)); the README names
[`d7fc674`](https://github.com/sourcegraph/cody-public-snapshot/commit/d7fc6741e7893e3f6e29efe58043f1afe08d505f)
as the last Apache-2.0 commit, while the `LICENSE` file at HEAD is still
Apache-2.0 text. The shipped extension may have moved on; every claim
below is about the extension as of August 2025. Home-directory resolution
of `env-paths` is cited from its source at the locked version 2.2.1
(`pnpm-lock.yaml`). VS Code storage mechanics are cited from the PearAI
fork of VS Code 1.96.4, the only VS Code checkout read in this round; see
[vscode.md](vscode.md) for upstream.

## 2. Per-user storage

**VS Code extension.**

- Global state: `localStorage.setStorage(context.globalState)`
  ([`vscode/src/main.ts:133-136`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/main.ts#L133-L136)). VS
  Code stores an extension's global state as one JSON value under the
  extension id in `ItemTable` of `User/globalStorage/state.vscdb`
  ([PearAI `extensionStorage.ts:159-161`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/src/vs/platform/extensionManagement/common/extensionStorage.ts#L159-L161),
  [`170-175`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/src/vs/platform/extensionManagement/common/extensionStorage.ts#L170-L175)).
  So the row key is `sourcegraph.cody-ai` and its value is a JSON object
  whose keys include `cody-local-chatHistory-v2` (all chat history),
  `SOURCEGRAPH_CODY_ENDPOINT` (last server), `SOURCEGRAPH_CODY_ENDPOINT_HISTORY`,
  `sourcegraphAnonymousUid`, `cody-model-preferences`,
  `cody-github-repo-metadata`
  ([`vscode/src/services/LocalStorageProvider.ts:29-39`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/services/LocalStorageProvider.ts#L29-L39)).
  History is keyed by `<endpoint>-<username>`
  ([`LocalStorageProvider.ts:393-397`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/services/LocalStorageProvider.ts#L393-L397)),
  so one row can hold several accounts' chats.
- `User/globalStorage/sourcegraph.cody-ai/symf/`: the downloaded `symf`
  search binary `symf-<version>-<arch>-<platform>`
  ([`vscode/src/local-context/download-symf.ts:53-56`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/local-context/download-symf.ts#L53-L56),
  [`118`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/local-context/download-symf.ts#L118)) and
  `symf/indexroot/<absolute workspace path>/`, one index per indexed
  folder; on Windows the drive colon is dropped
  ([`vscode/src/local-context/symf.ts:74`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/local-context/symf.ts#L74),
  [`396-411`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/local-context/symf.ts#L396-L411)), plus
  `.tmp/`, `.trash/` and `.failed/<path with / as __>` sentinels
  ([`symf.ts:339`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/local-context/symf.ts#L339),
  [`514-517`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/local-context/symf.ts#L514-L517)). Enabled by
  default (`cody.experimental.symf.enabled`;
  [`vscode/src/extension.node.ts:33-35`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/extension.node.ts#L33-L35)).
- `~/.vscode/cody.json`: user custom commands, in the home, not the
  user data directory
  ([`vscode/src/commands/services/custom-commands.ts:20`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/commands/services/custom-commands.ts#L20),
  [`46-48`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/commands/services/custom-commands.ts#L46-L48);
  [`vscode/src/commands/types.ts:9-15`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/commands/types.ts#L9-L15)).
  The `vscode` entries do not collect it today.
- Output channel logs go to the editor's `logs/` tree, already collected.

**JetBrains plugin and CLI (agent).** Paths come from
`envPaths('Cody')` ([`lib/shared/src/codyPaths.ts:3`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/lib/shared/src/codyPaths.ts#L3)),
which appends `-nodejs` by default
([env-paths `index.js:54-59`](https://github.com/sindresorhus/env-paths/blob/62d4ec8cd42f1a419e00856fab949ca8286773f6/index.js#L54-L59)):

| | data | config | log |
| --- | --- | --- | --- |
| Linux | `~/.local/share/Cody-nodejs` | `~/.config/Cody-nodejs` | `~/.local/state/Cody-nodejs` |
| macOS | `~/Library/Application Support/Cody-nodejs` | `~/Library/Preferences/Cody-nodejs` | `~/Library/Logs/Cody-nodejs` |
| Windows | `%LOCALAPPDATA%\Cody-nodejs\Data` | `%APPDATA%\Cody-nodejs\Config` | `%LOCALAPPDATA%\Cody-nodejs\Log` |

([env-paths `index.js:9-47`](https://github.com/sindresorhus/env-paths/blob/62d4ec8cd42f1a419e00856fab949ca8286773f6/index.js#L9-L47); XDG variables honoured
on Linux only.) The agent sets `globalStorageUri` and `storageUri` to
data, `logUri` to log, and copies extension resources into
`<config>/dist` ([`agent/src/agent.ts:120-137`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/agent/src/agent.ts#L120-L137),
[`159-161`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/agent/src/agent.ts#L159-L161),
[`180-189`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/agent/src/agent.ts#L180-L189)).

- `<data>/JetBrains-globalState/`: the JetBrains plugin asks for
  server-managed global state
  ([`jetbrains/.../CodyAgentService.kt:203`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/jetbrains/src/main/kotlin/com/sourcegraph/cody/agent/CodyAgentService.kt#L203)),
  with client name `JetBrains`
  ([`CodyAgent.kt:136-137`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/jetbrains/src/main/kotlin/com/sourcegraph/cody/agent/CodyAgent.kt#L136-L137)),
  so the agent opens `<data>/<name>-globalState` with `node-localstorage`
  ([`agent/src/agent.ts:1470-1476`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/agent/src/agent.ts#L1470-L1476);
  [`agent/src/global-state/AgentGlobalState.ts:115-121`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/agent/src/global-state/AgentGlobalState.ts#L115-L121)).
  Each key is one file named by its URL-encoded key, holding the JSON value
  ([`AgentGlobalState.ts:134-140`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/agent/src/global-state/AgentGlobalState.ts#L134-L140);
  [node-localstorage 3.0.5 `LocalStorage.js`](https://unpkg.com/node-localstorage@3.0.5/LocalStorage.js)
  `setItem`). The chat history is the file
  `JetBrains-globalState/cody-local-chatHistory-v2`, quota 256 MB.
- `<data>/symf/`: same binary and index as above.
- `<config>/user-settings.json`: CLI accounts
  ([`agent/src/cli/command-auth/settings.ts:6-36`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/agent/src/cli/command-auth/settings.ts#L6-L36)).
- `~/.cody/commands.json`: custom commands for agent clients
  ([`types.ts:13-14`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/commands/types.ts#L13-L14);
  [`custom-commands.ts:46-47`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/commands/services/custom-commands.ts#L46-L47)).

## 3. Credentials

- VS Code: the access token is stored in SecretStorage three times, under
  the endpoint URL, under `cody.access-token`, and the token source under
  `<endpoint>cody.access-token.source`
  ([`vscode/src/services/SecretStorageProvider.ts:5-6`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/services/SecretStorageProvider.ts#L5-L6),
  [`97-112`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/services/SecretStorageProvider.ts#L97-L112)).
  These are encrypted `secret://{"extensionId":"sourcegraph.cody-ai","key":...}`
  rows in `state.vscdb`
  ([PearAI `mainThreadSecretState.ts:76-78`](https://github.com/trypear/pearai-app/blob/d930f0233c14668df9f85c6a78a81828f4251194/src/vs/workbench/api/browser/mainThreadSecretState.ts#L76-L78)).
- `cody.experimental.localTokenPath`: a setting that points at a JSON file
  with a `token` key, read instead of SecretStorage
  ([`SecretStorageProvider.ts:48-57`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/services/SecretStorageProvider.ts#L48-L57),
  [`225-235`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/services/SecretStorageProvider.ts#L225-L235)).
  Its location is arbitrary; read `settings.json` for it.
- JetBrains: secrets are client-managed
  ([`CodyAgentService.kt:204`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/jetbrains/src/main/kotlin/com/sourcegraph/cody/agent/CodyAgentService.kt#L204)),
  that is, in the IDE's own password store, not in `Cody-nodejs`.
- CLI: the OS keychain via `security`, Windows Credential Manager or
  `secret-tool`, no file fallback
  ([`agent/src/cli/command-auth/secrets.ts:8-14`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/agent/src/cli/command-auth/secrets.ts#L8-L14),
  [`204-213`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/agent/src/cli/command-auth/secrets.ts#L204-L213)).
  `user-settings.json` holds `serverEndpoint`, `username` and
  `customHeaders`, which may carry proxy auth.

## 4. Exclusions

- The `symf-*` binary in each `symf/` directory.
- `<config>/dist`: copied extension resources.
- `symf/indexroot` index content was not sized; its directory names are
  the indexed workspace paths, which is evidence, so it is not proposed for
  exclusion until a live collection shows it is large.

## 5. Project-local files

`.vscode/cody.json` (VS Code) and `.cody/commands.json` (agent clients)
at the first workspace folder ([`custom-commands.ts:36-39`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/commands/services/custom-commands.ts#L36-L39));
`.sourcegraph/*.rule.md` rules
([`vscode/src/rules/fs-rule-provider.ts:20-26`](https://github.com/sourcegraph/cody-public-snapshot/blob/8e20ac6c1460c08b0db581c0204658112a246eda/vscode/src/rules/fs-rule-provider.ts#L20-L26)).
No per-project database.

## 6. Where the project path is recorded

- Chat transcripts carry no workspace field; context items carry file URIs
  (`contextFiles[].uri`), from which the project can be inferred.
- `symf/indexroot/<path>` directory names are indexed workspace roots.
- VS Code `workspaceStorage/*/workspace.json` as usual.

## 7. Confidence

High (frozen source): storage keys and row layout, symf paths, custom
command files, agent `Cody-nodejs` layout, JetBrains global-state
directory, CLI keychain use. Medium: that current shipped builds still
use these keys and paths; the source stops in August 2025. Medium: the
`*/Cody-nodejs/...` exclusion and secret forms assume exclusion globs match
under `AppData/Local` and `Library/Preferences` the same way. Not
determined: the size of a symf index; whether the JetBrains plugin passes a
`globalStateDir` from the Kotlin side in builds after the snapshot (it does
not at this commit); where the Eclipse and Visual Studio clients, which are
not in this repository, keep state.
