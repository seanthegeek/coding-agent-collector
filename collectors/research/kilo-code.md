# Kilo Code: on-disk paths

## 1. Source and evidence level

Open source. Kilo-Org/kilocode at [`76bcfd40be616a72f4697b3041565f322245b462`](https://github.com/Kilo-Org/kilocode/commit/76bcfd40be616a72f4697b3041565f322245b462)
(clone `scratchpad/repos/kilo`). The CLI/TUI/server is an OpenCode fork
(`packages/core`, `packages/opencode`); the VS Code extension
`kilocode.kilo-code` ([`packages/kilo-vscode/package.json:2`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/kilo-vscode/package.json#L2),[`11`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/kilo-vscode/package.json#L11)) is a thin
client of that server. All claims from source. Record schemas:
[`analyzer/research/kilo-code.md`](../../analyzer/research/kilo-code.md) and `opencode.md`.

## 2. Per-user storage

`xdg-basedir` with no platform branching ([`packages/core/src/global.ts:3`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/global.ts#L3),[`12`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/global.ts#L12),[`22-26`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/global.ts#L22-L26)),
so the same paths on Linux, macOS and Windows; `XDG_DATA_HOME`,
`XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME` relocate them.
`KILO_TEST_HOME` overrides home ([`global.ts:32`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/global.ts#L32)). Newlines are stripped
from `$HOME` ([`global.ts:21`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/global.ts#L21)). All three roots are tagged no-index for
Spotlight ([`global.ts:58`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/global.ts#L58)).

`~/.local/share/kilo` (data):

- `kilo.db` (SQLite, WAL) on release builds; `kilo-<channel>.db` or a
  pre-existing `opencode-<channel>.db` otherwise; `KILO_DB` overrides
  ([`packages/core/src/database/database.ts:32`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/database/database.ts#L32),[`52-66`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/database/database.ts#L52-L66);
  [`packages/core/src/flag/flag.ts:111`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/flag/flag.ts#L111)). Holds sessions, messages, parts,
  projects.
- `auth.json` ([`packages/opencode/src/auth/index.ts:11`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/auth/index.ts#L11)), `mcp-auth.json`
  ([`mcp/auth.ts:37`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/mcp/auth.ts#L37)).
- `storage/` legacy JSON store ([`storage/storage.ts:234`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/storage/storage.ts#L234);
  [`kilocode/storage/json-migration.ts:78`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/storage/json-migration.ts#L78)).
- `snapshot/<projectID>/<hash>` bare git dirs for checkpoints
  ([`snapshot/index.ts:108`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/snapshot/index.ts#L108)), `worktree/<projectID>/` agent worktrees
  ([`worktree/index.ts:210`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/worktree/index.ts#L210)), `tool-output/` truncated tool results
  ([`tool/truncation-dir.ts:4`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/tool/truncation-dir.ts#L4)), `repos/` ([`global.ts:37`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/global.ts#L37)), `log/`
  ([`global.ts:36`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/global.ts#L36)), `plans/*.md` ([`session/session.ts:416`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/session/session.ts#L416)),
  `retention/state.json` ([`kilocode/session/retention.ts:326`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/session/retention.ts#L326)),
  `session-export.db`, `session-export-workspace.json`
  ([`kilocode/bootstrap.ts:83-88`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/bootstrap.ts#L83-L88)).
- `state/` fallback for the state dir when `XDG_STATE_HOME` is unset and
  `~/.local/state/kilo` is unusable ([`global.ts:26`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/global.ts#L26); [`kilocode/global.ts:38-72`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/kilocode/global.ts#L38-L72)).

`~/.local/state/kilo` (state): `indexing/` codebase index
([`kilocode/indexing.ts:298`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/indexing.ts#L298)), `model.json`, `plugin-meta.json`,
`background-process/`.

`~/.config/kilo` (config, `KILO_CONFIG_DIR` overrides, [`flag.ts:140-141`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/flag/flag.ts#L140-L141)):
`kilo.jsonc`, `kilo.json`, `opencode.jsonc`, `opencode.json`,
`config.json`, legacy `config/` dir ([`packages/opencode/src/config/config.ts:206-208`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/config/config.ts#L206-L208),[`458-488`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/config/config.ts#L458-L488)),
`agents/` ([`kilocode/marketplace/paths.ts:76`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/marketplace/paths.ts#L76)), `tui.jsonc`, `themes/`,
`marketplace/`. `KILO_CONFIG` points at an extra config file,
`KILO_CONFIG_CONTENT` inlines one ([`config.ts:762-777`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/config/config.ts#L762-L777),[`897-903`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/config/config.ts#L897-L903)).

`~/.cache/kilo`: `bin/` ([`global.ts:35`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/global.ts#L35), LSP servers such as clangd, zls),
`skills/`, `packages/git/`, `commands/` ([`kilocode/skill-remove.ts:25`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/skill-remove.ts#L25);
[`kilocode/plugin/git-source.ts:158`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/plugin/git-source.ts#L158); [`kilocode/command-files.ts:118`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/command-files.ts#L118)).

`~/.kilo`: `bin/kilo` installer target ([`install:70`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/install#L70)), `skills/`
([`marketplace/paths.ts:81`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/marketplace/paths.ts#L81)), `rules/` ([`kilocode/rules-migrator.ts:12`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/rules-migrator.ts#L12)); it
and `~/.kilocode` are extra config roots ([`kilocode/config/overlay.ts:244`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/config/overlay.ts#L244)).
`~/.kilocode`: legacy `rules/`, `cli/config.json`,
`cli/global/settings/custom_modes.yaml` ([`kilocode/modes-migrator.ts:170`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/modes-migrator.ts#L170));
`~/.kilocodemodes` ([`modes-migrator.ts:174`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/modes-migrator.ts#L174)). `~/.agents` is read for
skills ([`kilocode/config/claude-migration.ts:641`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/config/claude-migration.ts#L641)).

VS Code `globalStorage/kilocode.kilo-code/`: the current extension keeps only
`globalState` keys ([`packages/kilo-vscode/src/KiloProvider.ts:1652-1663`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/kilo-vscode/src/KiloProvider.ts#L1652-L1663))
and reads legacy Roo-style `tasks/_index.json` for import
([`packages/kilo-vscode/src/legacy-migration/task-store.ts:136`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/kilo-vscode/src/legacy-migration/task-store.ts#L136)). Pre-fork
installs leave `tasks/`, `checkpoints/`, `cache/` there.

## 3. Credentials

- `~/.local/share/kilo/auth.json`, mode 0600: per provider `{type:"api",
  key}` or `{type:"oauth", refresh, access, accountId?, enterpriseUrl?,
  baseURL?}` ([`auth/index.ts:15-27`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/auth/index.ts#L15-L27),[`81-90`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/auth/index.ts#L81-L90)).
- `~/.local/share/kilo/mcp-auth.json`: MCP OAuth tokens ([`mcp/auth.ts:37`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/mcp/auth.ts#L37)).
- `~/.kilocode/cli/config.json`: legacy Kilo token, migrated into
  `auth.json` ([`packages/kilo-gateway/src/auth/legacy-migration.ts:5-11`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/kilo-gateway/src/auth/legacy-migration.ts#L5-L11)).
- `kilo.db` has no credential table in this fork's schema search; `kilo.json*`
  and `config.json` can embed `{env:...}` provider keys and MCP headers.
- No keychain use. `KILO_SERVER_PASSWORD` is env only ([`flag.ts:68`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/flag/flag.ts#L68)).

## 4. Exclude

`.local/share/kilo/snapshot`, `/worktree`, `/repos`, `/tool-output`, `/log`,
`.local/state/kilo/indexing`, `.local/share/kilo/state/indexing`,
`.cache/kilo` (binaries, package clones), `.kilo/bin`, project
`.kilo/worktrees`. Keep `plans/`, `retention/`, `session-export*`.

## 5. Project-local

`.kilo/` and legacy `.kilocode/` at any depth ([`kilocode/permission/config-paths.ts:9-11`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/permission/config-paths.ts#L9-L11);
[`config.ts:808`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/config/config.ts#L808)) with `rules/`, `workflows/`, `agent/`, `agents/`, `skills/`,
`worktrees/` ([`rules-migrator.ts:11`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/rules-migrator.ts#L11); [`workflows-migrator.ts:14`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/workflows-migrator.ts#L14);
[`kilocode/agent/builder.ts:77`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/agent/builder.ts#L77); [`marketplace/paths.ts:77`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/marketplace/paths.ts#L77),[`82`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/marketplace/paths.ts#L82);
[`kilocode/cli/cmd/tui-worktree.ts:17`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/cli/cmd/tui-worktree.ts#L17), added to `.git/info/exclude`);
`kilo.json`, `kilo.jsonc`, `opencode.json(c)` ([`cli/cmd/mcp.ts:399-402`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/cli/cmd/mcp.ts#L399-L402));
`.kilocodeignore` ([`kilocode/ignore-migrator.ts:10`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/ignore-migrator.ts#L10)), `.kilocodemodes`
([`modes-migrator.ts:187`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/modes-migrator.ts#L187)), `.kilocoderules` ([`rules-migrator.ts:7`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/opencode/src/kilocode/rules-migrator.ts#L7)),
`AGENTS.md`. No per-project database.

## 6. Project path

`kilo.db` table `project`: `worktree` (absolute), `vcs`, `name`,
`sandboxes[]`; table `project_directory`: `directory`, `type`
(`main|root|git_worktree`) ([`packages/core/src/project/sql.ts:6-34`](https://github.com/Kilo-Org/kilocode/blob/76bcfd40be616a72f4697b3041565f322245b462/packages/core/src/project/sql.ts#L6-L34)).
Legacy `storage/project/<id>.json` `worktree`. SQLite only; left to the analyzer.

## 7. Confidence

High: XDG roots, db names, auth files, project table columns, project
dotfiles. Medium: whether `kilo.db` carries a `credential` table like
upstream OpenCode (not found by grep in this clone). Low: contents of
`globalStorage/kilocode.kilo-code` on current installs beyond
`globalState`; nothing in `kilo-vscode` writes files there.
