# OpenCode: on-disk paths

## 1. Source and evidence level

sst/opencode, open source, commit `907b3bc518fa48e90e8ec24dd327d13eee71c36c`. Every claim is from source. Platform mapping verified against the `xdg-basedir` 5.1.0 tarball (`scratchpad/crates/xdg/package/index.js`), the version pinned in `packages/core/package.json:127`. Transcript schema is in `analyzer/research/opencode.md`; not repeated here.

## 2. Per-user storage

`packages/core/src/global.ts:3,10-15` builds data, cache, config and state as `xdg*/opencode`. `xdg-basedir/index.js:7-16` has no platform branch: `XDG_DATA_HOME` or `~/.local/share`, `XDG_CONFIG_HOME` or `~/.config`, `XDG_STATE_HOME` or `~/.local/state`, `XDG_CACHE_HOME` or `~/.cache`. So the layout is identical on Linux, macOS and Windows (`%USERPROFILE%\.local\share\opencode` etc.). Home itself comes from `OPENCODE_TEST_HOME` or `os.homedir()` (`global.ts:19`).

`~/.local/share/opencode` (data):
- `opencode.db` with `-wal`/`-shm` (WAL at `packages/core/src/database/database.ts:27`). Name is `opencode.db` on the latest/beta/prod channels or when `OPENCODE_DISABLE_CHANNEL_DB` is set, otherwise `opencode-<channel>.db` (`database.ts:48-54`). `OPENCODE_DB` relocates it; a relative value is joined to the data dir (`database.ts:44-46`).
- `storage/` legacy JSON tree: `project/<id>.json`, `session/<projectID>/`, `message/<sessionID>/`, `part/<messageID>/`, `session_diff/`, plus a `migration` marker (`packages/opencode/src/storage/storage.ts:122,143,154,169,192,224-225`).
- `auth.json` (`packages/opencode/src/auth/index.ts:10`), `mcp-auth.json` (`packages/opencode/src/mcp/auth.ts:37`).
- `snapshot/<projectID>/<hash>` bare git dirs for file checkpoints (`packages/opencode/src/snapshot/index.ts:71`, `packages/core/src/snapshot.ts:98`).
- `worktree/<projectID>/` git worktrees (`packages/opencode/src/worktree/index.ts:208`).
- `repos/` (`global.ts:24`), `tool-output/` truncated tool output, pruned unless `OPENCODE_DISABLE_PRUNE` (`packages/opencode/src/tool/truncation-dir.ts:4`, `config.ts:596`).
- `log/opencode.log` and `log/direct/<stamp>-<pid>.jsonl` run traces (`packages/core/src/observability/logging.ts:49`, `packages/opencode/src/cli/cmd/run/trace.ts:32`).

`~/.config/opencode` (config, overridable with `OPENCODE_CONFIG_DIR`, `global.ts:64`): `opencode.jsonc`, `opencode.json`, `config.json`, legacy `config` migrated to `config.json` (`packages/opencode/src/config/config.ts:141-142,272-285`); `tui.json(c)` (`config/tui.ts:184`); `AGENTS.md` (`session/instruction.ts:61`); `agents/`, `themes/`, `plugins/`, `skills/`; a `.gitignore` plus `package.json` and `node_modules` created by the background `@opencode-ai/plugin` install in every config dir (`config.ts:309-317,450-460`).

`~/.opencode`: a second config directory discovered with `afs.up` from home to home (`packages/opencode/src/config/paths.ts:34-38`), read for `opencode.json(c)` because it ends in `.opencode` (`config.ts:439-441`); also gets the `node_modules` install. `~/.opencode/bin/opencode` is the curl installer target (`install:68`, recognised at `installation/index.ts:175`).

`~/.local/state/opencode`: `plugin-meta.json` (`plugin/meta.ts:49`), `model.json` last-used model (`cli/cmd/run/variant.shared.ts:19`), file locks (`global.ts:33`).

`~/.cache/opencode`: `bin/` LSP and tool binaries (`global.ts:22`, `lsp/server.ts:835,964,1049`), `packages/` npm installs (`packages/core/src/npm.ts:87`), `skills/` clones (`skill/discovery.ts:35`), `models.json` models.dev cache (`packages/core/src/models-dev.ts:160-164`).

System-wide managed config, outside home: `/Library/Application Support/opencode`, `%ProgramData%\opencode`, `/etc/opencode` (`config/managed.ts:23-27`).

## 3. Credentials

- `~/.local/share/opencode/auth.json`, mode 0600: per provider `{type:"oauth",refresh,access,expires}` or `{type:"api",key}` or `{type:"wellknown",key,token}` (`auth/index.ts:14-33,79`). `OPENCODE_AUTH_CONTENT` can replace it (`:59`).
- `~/.local/share/opencode/mcp-auth.json` MCP OAuth tokens (`mcp/auth.ts:37`).
- `opencode*.db*`: table `credential` with JSON `value` column (`packages/core/src/credential/sql.ts:5-14`), so the transcript database is also a secret store.
- `opencode.json(c)` / `config.json` in both config dirs can carry `provider.<id>.options.apiKey` (`packages/opencode/src/provider/provider.ts:229,352`).
- No keychain use found.

## 4. Exclusions (relative to home)

`.local/share/opencode/snapshot`, `.local/share/opencode/worktree`, `.local/share/opencode/repos`, `.local/share/opencode/tool-output`, `.config/opencode/node_modules`, `.opencode/node_modules`, `.opencode/bin`, `.cache/opencode` (entire dir is binaries, package installs and skill clones; `models.json` is public data).

## 5. Project-local files

`.opencode/` directories from cwd up to the worktree root (`config/paths.ts:26-31`) holding `opencode.json(c)`, `agents/`, `plugins/`, `themes/`, `skills/`, and the generated `.gitignore`, `package.json`, `node_modules`; `opencode.jsonc` / `opencode.json` found by walking up (`paths.ts:17-19`); `AGENTS.md`, `CLAUDE.md`, deprecated `CONTEXT.md` (`session/instruction.ts:65-67`). No per-project database; sessions live in the home DB.

## 6. Where the project path is recorded

- SQLite table `project`: `worktree` (absolute), `sandboxes` (array), and table `project_directory` `directory` with `type` main/root/git_worktree (`packages/core/src/project/sql.ts:7-34`).
- Legacy `storage/project/<id>.json` key `worktree` (`storage.ts:122-132`).

## 7. Catalog review

Home: `.config/opencode` confirmed; `.opencode` confirmed (config dir plus installer); `.local/share/opencode` confirmed; `.local/state/opencode` confirmed.
Project: `.opencode` confirmed; `opencode.json*` confirmed.
Excluded: `.local/share/opencode/bin` doubtful, bin now lives in `.cache/opencode/bin` (`global.ts:22`), harmless; `snapshot`, `worktree`, `repos`, `tool-output` confirmed; `.config/opencode/node_modules`, `.opencode/bin`, `.opencode/node_modules` confirmed.
Credential: `auth.json`, `mcp-auth.json`, `opencode*.db*`, `.config/opencode/opencode.json*`, `.config/opencode/config.json` all confirmed.

Add:
```
# home
opencode|.cache/opencode
# excluded
.cache/opencode/bin
.cache/opencode/packages
.cache/opencode/skills
*/.opencode/node_modules
# credential
.opencode/opencode.json*
```
The `.cache/opencode` entry only matters if `models.json` is wanted; otherwise skip it and the three exclusions.

## 8. Confidence

High: every path above (source). Medium: whether the collector's project-level exclusion syntax matches `<project>/.opencode/node_modules`; test it. Not determined: whether older releases wrote `bin/` under the data dir (the current catalog exclusion suggests they did).
