# Augment (auggie CLI): on-disk paths

## 1. Source and evidence level

Closed source. Evidence, in order of weight:

1. Shipped bundle `@augmentcode/auggie` 0.36.0 (`npm pack`,
   `scratchpad/npm/augmentcode-auggie-0.36.0.tgz`, single minified
   `package/augment.mjs`, 13 MB, 8201 lines). Line numbers are meaningless;
   claims cite the literal string found with `grep -a`.
2. Official docs at docs.augmentcode.com (`/cli/setup-auggie/authentication`,
   `/cli/rules`, `/cli/integrations`, `/cli/custom-commands`,
   `/cli/setup-auggie/workspace-indexing`, `/troubleshooting/logs`), fetched
   2026-10-03.

The VS Code extension `augment.vscode-augment` was not unpacked; its state is
whatever sits in the editor's `globalStorage/augment.vscode-augment`, covered
by the vscode entries.

## 2. Per-user storage

`~/.augment` on every OS: the bundle joins `os.homedir()` with `".augment"`
(`homedir(),".augment"` appears 20+ times); a config key `augmentCacheDir`
can override it (`augmentCacheDir||...join(homedir(),".augment")`). No XDG,
Library or AppData branches exist in the bundle.

Files and directories (bundle literals `".augment","<name>"`):

- `session.json`: OAuth session (`AuthSessionStore`, `join(r,"session.json")`).
- `sessions/<conversationId>.json`: full conversations
  (`join(_u(),".augment","sessions")`; session store writes
  `this.sessionsDir,\`${e}.json\``; conversation ids are `[A-Za-z0-9_-]`).
- `prompt-history.jsonl`: `{message}` lines, capped at 500
  (`wBo="prompt-history.jsonl",yfr=500`); directory argument is the
  `~/.augment` state dir.
- `settings.json` (MCP servers, model, rules; docs `/cli/integrations`),
  `feature-config.json`, `disabled-skills.json`.
- `rules/`, `commands/`, `agents/`, `skills/`, `plans/`
  (help text: `"~/.augment/rules/"`, `"~/.augment/commands/"`,
  `"~/.augment/agents"`; docs `/cli/rules`, `/cli/custom-commands`).
- `plugins/marketplaces/` (plugin clones).
- `binaries/` (downloaded helper binaries), `vfs/<space>` (virtual
  filesystem mirror, `AUGMENT_VFS_DIR` overrides), `knowledgebase/`
  (synced knowledge base: `"Sync the knowledgebase to ~/.augment/knowledgebase/"`),
  `uploads/`, `worktrees/` (agent git worktrees, `worktreeDir??join(n,"worktrees")`),
  `daemon/<sha256(workspace)[:12]>/state.json`, `daemon/locks/<uuid>.json`.
- Also reads `~/.claude/commands`, `~/.agents/commands`, `AGENTS.md`,
  `CLAUDE.md` (docs `/cli/custom-commands`, `/cli/rules`).

Logs are not under home: `$TMPDIR/augment-log.txt`, `augment-daemon.txt`,
`%TEMP%\augment-log.txt` (bundle `tmpdir(),"augment-log.txt"`; docs
`/troubleshooting/logs`). Temp also holds `tmpdir()/.augment/...` scratch.

Environment: `AUGMENT_SESSION_AUTH` (session JSON inline),
`AUGMENT_API_TOKEN`, `AUGMENT_API_URL`, `AUGMENT_VFS_DIR`,
`AUGMENT_WORKSPACE_ROOT`, `AUGMENT_ANTHROPIC_API_KEY`,
`AUGMENT_OPENAI_API_KEY`, `AUGMENT_FIREWORKS_API_KEY`, `AUGMENT_BEDROCK_API_KEY`
(all literal in the bundle). Shell histories may carry these.

## 3. Credentials

- `~/.augment/session.json`: `{accessToken, tenantURL, scopes}`
  (bundle `accessToken:t.accessToken,tenantURL:t.tenantURL,scopes:...`),
  written mode 0600 and copied into daemon sandboxes as `session.json`.
  The docs call this "the session JSON" and advise treating it as a secret
  (`/cli/setup-auggie/authentication`); the TUI tells users to paste the file
  into a GitHub secret.
- `~/.augment/settings.json` and project `.augment/settings.json`,
  `.augment/settings.local.json`: MCP `mcpServers` with env/headers.
- No OS keychain use found in the bundle (no `keytar`/`security` strings).

## 4. Exclude

`.augment/binaries`, `.augment/vfs`, `.augment/knowledgebase`,
`.augment/uploads`, `.augment/worktrees`, `.augment/plugins/marketplaces`.
Keep `daemon/` (small state and locks with workspace hashes).

## 5. Project-local

`.augment/rules/*.md`, `.augment/commands/<name>.md`, `.augment/agents/`,
`.augment/skills/<name>/SKILL.md`, `.augment/settings.json`,
`.augment/settings.local.json`, `.augment-guidelines`, `.augmentignore`,
`.augment-plugin` (plugin manifest), `.augment-setup.sh`; also `.claude/commands`,
`.agents/commands`, `AGENTS.md`, `CLAUDE.md` (bundle literals; docs
`/cli/rules`, `/cli/custom-commands`, `/cli/setup-auggie/workspace-indexing`).
No per-project database; the code index is server-side ("Augment stores
your code securely", docs) with only `vfs/` mirrors locally.

## 6. Project path

`sessions/<id>.json` carries `workspaceRoot` next to `conversationId`
(bundle `conversationId:n,workspaceRoot:r`; telemetry objects use the same
pair). Exact JSON key path inside the session file is not verifiable
without a live file. `daemon/<hash>/state.json` keys the workspace by a
truncated sha256 and is not reversible.

## 7. Catalog review

Home: `.augment`: confirmed.

Project: `.augment`, `.augment-guidelines`, `.augmentignore`: confirmed.
Missing `.augment-plugin`.

Excluded: `.augment/binaries`, `vfs`, `knowledgebase`, `uploads`,
`worktrees`: confirmed. Missing `plugins/marketplaces`.

Credential: `.augment/session.json`: confirmed. Missing settings files that
embed MCP env.

Add:

```
project|.augment-plugin
.augment/plugins/marketplaces
.augment/settings.json
.augment/settings.local.json
```

Doubtful: `.augment/settings*.json` as credential globs also match project
`.augment/settings.json` because credential globs cross `/`; that is the
intent.

## 8. Confidence

High (bundle literal): `~/.augment` root, `session.json` and its fields,
`sessions/<id>.json`, `prompt-history.jsonl`, the five large dirs,
`settings.json`, project dotfiles, env variable names. Medium (bundle
context only): `sessions/` is the conversation store rather than a cache;
`workspaceRoot` is persisted in the session file. Low: anything about the
VS Code extension's globalStorage layout and the JetBrains plugin; the
`augmentCacheDir` config key's source (settings.json vs flag).
