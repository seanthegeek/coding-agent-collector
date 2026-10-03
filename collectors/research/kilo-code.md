# Kilo Code: on-disk paths

## 1. Source and evidence level

Open source. Kilo-Org/kilocode at `76bcfd40be616a72f4697b3041565f322245b462`
(clone `scratchpad/repos/kilo`). The CLI/TUI/server is an OpenCode fork
(`packages/core`, `packages/opencode`); the VS Code extension
`kilocode.kilo-code` (`packages/kilo-vscode/package.json:2,11`) is a thin
client of that server. All claims from source. Record schemas:
`analyzer/research/kilo-code.md` and `opencode.md`.

## 2. Per-user storage

`xdg-basedir` with no platform branching (`packages/core/src/global.ts:3,12,22-26`),
so the same paths on Linux, macOS and Windows; `XDG_DATA_HOME`,
`XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME` relocate them.
`KILO_TEST_HOME` overrides home (`global.ts:32`). Newlines are stripped
from `$HOME` (`global.ts:21`). All three roots are tagged no-index for
Spotlight (`global.ts:58`).

`~/.local/share/kilo` (data):

- `kilo.db` (SQLite, WAL) on release builds; `kilo-<channel>.db` or a
  pre-existing `opencode-<channel>.db` otherwise; `KILO_DB` overrides
  (`packages/core/src/database/database.ts:32,52-66`;
  `packages/core/src/flag/flag.ts:111`). Holds sessions, messages, parts,
  projects.
- `auth.json` (`packages/opencode/src/auth/index.ts:11`), `mcp-auth.json`
  (`mcp/auth.ts:37`).
- `storage/` legacy JSON store (`storage/storage.ts:234`;
  `kilocode/storage/json-migration.ts:78`).
- `snapshot/<projectID>/<hash>` bare git dirs for checkpoints
  (`snapshot/index.ts:108`), `worktree/<projectID>/` agent worktrees
  (`worktree/index.ts:210`), `tool-output/` truncated tool results
  (`tool/truncation-dir.ts:4`), `repos/` (`global.ts:37`), `log/`
  (`global.ts:36`), `plans/*.md` (`session/session.ts:416`),
  `retention/state.json` (`kilocode/session/retention.ts:326`),
  `session-export.db`, `session-export-workspace.json`
  (`kilocode/bootstrap.ts:83-88`).
- `state/` fallback for the state dir when `XDG_STATE_HOME` is unset and
  `~/.local/state/kilo` is unusable (`global.ts:26`; `kilocode/global.ts:38-72`).

`~/.local/state/kilo` (state): `indexing/` codebase index
(`kilocode/indexing.ts:298`), `model.json`, `plugin-meta.json`,
`background-process/`.

`~/.config/kilo` (config, `KILO_CONFIG_DIR` overrides, `flag.ts:140-141`):
`kilo.jsonc`, `kilo.json`, `opencode.jsonc`, `opencode.json`,
`config.json`, legacy `config/` dir (`packages/opencode/src/config/config.ts:206-208,458-488`),
`agents/` (`kilocode/marketplace/paths.ts:76`), `tui.jsonc`, `themes/`,
`marketplace/`. `KILO_CONFIG` points at an extra config file,
`KILO_CONFIG_CONTENT` inlines one (`config.ts:762-777,897-903`).

`~/.cache/kilo`: `bin/` (`global.ts:35`, LSP servers such as clangd, zls),
`skills/`, `packages/git/`, `commands/` (`kilocode/skill-remove.ts:25`;
`kilocode/plugin/git-source.ts:158`; `kilocode/command-files.ts:118`).

`~/.kilo`: `bin/kilo` installer target (`install:70`), `skills/`
(`marketplace/paths.ts:81`), `rules/` (`kilocode/rules-migrator.ts:12`); it
and `~/.kilocode` are extra config roots (`kilocode/config/overlay.ts:244`).
`~/.kilocode`: legacy `rules/`, `cli/config.json`,
`cli/global/settings/custom_modes.yaml` (`kilocode/modes-migrator.ts:170`);
`~/.kilocodemodes` (`modes-migrator.ts:174`). `~/.agents` is read for
skills (`kilocode/config/claude-migration.ts:641`).

VS Code `globalStorage/kilocode.kilo-code/`: the current extension keeps only
`globalState` keys (`packages/kilo-vscode/src/KiloProvider.ts:1652-1663`)
and reads legacy Roo-style `tasks/_index.json` for import
(`packages/kilo-vscode/src/legacy-migration/task-store.ts:136`). Pre-fork
installs leave `tasks/`, `checkpoints/`, `cache/` there.

## 3. Credentials

- `~/.local/share/kilo/auth.json`, mode 0600: per provider `{type:"api",
  key}` or `{type:"oauth", refresh, access, accountId?, enterpriseUrl?,
  baseURL?}` (`auth/index.ts:15-27,81-90`).
- `~/.local/share/kilo/mcp-auth.json`: MCP OAuth tokens (`mcp/auth.ts:37`).
- `~/.kilocode/cli/config.json`: legacy Kilo token, migrated into
  `auth.json` (`packages/kilo-gateway/src/auth/legacy-migration.ts:5-11`).
- `kilo.db` has no credential table in this fork's schema search; `kilo.json*`
  and `config.json` can embed `{env:...}` provider keys and MCP headers.
- No keychain use. `KILO_SERVER_PASSWORD` is env only (`flag.ts:68`).

## 4. Exclude

`.local/share/kilo/snapshot`, `/worktree`, `/repos`, `/tool-output`, `/log`,
`.local/state/kilo/indexing`, `.local/share/kilo/state/indexing`,
`.cache/kilo` (binaries, package clones), `.kilo/bin`, project
`.kilo/worktrees`. Keep `plans/`, `retention/`, `session-export*`.

## 5. Project-local

`.kilo/` and legacy `.kilocode/` at any depth (`kilocode/permission/config-paths.ts:9-11`;
`config.ts:808`) with `rules/`, `workflows/`, `agent/`, `agents/`, `skills/`,
`worktrees/` (`rules-migrator.ts:11`; `workflows-migrator.ts:14`;
`kilocode/agent/builder.ts:77`; `marketplace/paths.ts:77,82`;
`kilocode/cli/cmd/tui-worktree.ts:8`, added to `.git/info/exclude`);
`kilo.json`, `kilo.jsonc`, `opencode.json(c)` (`cli/cmd/mcp.ts:399-402`);
`.kilocodeignore` (`kilocode/ignore-migrator.ts:10`), `.kilocodemodes`
(`modes-migrator.ts:187`), `.kilocoderules` (`rules-migrator.ts:7`),
`AGENTS.md`. No per-project database.

## 6. Project path

`kilo.db` table `project`: `worktree` (absolute), `vcs`, `name`,
`sandboxes[]`; table `project_directory`: `directory`, `type`
(`main|root|git_worktree`) (`packages/core/src/project/sql.ts:6-34`).
Legacy `storage/project/<id>.json` `worktree`. SQLite only; v2 work.

## 7. Catalog review

Home: three `*/User/globalStorage/kilocode.kilo-code`: confirmed (legacy
content). `.kilo`, `.kilocode`, `.kilocodemodes`, `.config/kilo`,
`.local/share/kilo`, `.local/state/kilo`: confirmed. Not listed: `.cache/kilo`
(binaries and package clones; leave it out).

Project: `.kilo`, `.kilocode`, `.kilocodemodes`, `.kilocodeignore`,
`kilo.json*`: confirmed. Missing `.kilocoderules`, `opencode.json*` (already
present under opencode).

Excluded: `.local/share/kilo/{snapshot,repos,tool-output,log}`,
`.local/state/kilo/indexing`, `.local/share/kilo/state/indexing`: confirmed.
`*/kilocode.kilo-code/checkpoints`, `/cache`: confirmed for legacy content.
`.kilocode/worktrees`: wrong name; the managed worktree dir is `.kilo/worktrees`
(project-relative, `tui-worktree.ts:8`), and the home one is
`.local/share/kilo/worktree` (singular, `worktree/index.ts:210`).

Credential: `.local/share/kilo/auth.json`, `mcp-auth.json`,
`.kilocode/cli/config.json`: confirmed.

Add:

```
project|.kilocoderules
.local/share/kilo/worktree
.kilo/worktrees
.kilo/bin
.local/share/kilo/kilo*.db*
.local/share/kilo/opencode*.db*
.config/kilo/kilo.json*
.config/kilo/opencode.json*
.config/kilo/config.json
```

The last five are secret globs mirroring the opencode entries: the db can
hold MCP tokens in message parts and the configs embed keys.

## 8. Confidence

High: XDG roots, db names, auth files, project table columns, project
dotfiles. Medium: whether `kilo.db` carries a `credential` table like
upstream OpenCode (not found by grep in this clone). Low: contents of
`globalStorage/kilocode.kilo-code` on current installs beyond
`globalState`; nothing in `kilo-vscode` writes files there.
