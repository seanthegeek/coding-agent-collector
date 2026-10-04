# little-coder: on-disk paths

## 1. Source and evidence level

itayinbarr/little-coder at [`89d4fa0af864230527ab75d12604ed0eb320e6df`](https://github.com/itayinbarr/little-coder/commit/89d4fa0af864230527ab75d12604ed0eb320e6df),
version 1.20.0, Apache-2.0 ([package.json:3](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/package.json#L3), [10](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/package.json#L10)). Open source,
TypeScript and Node. All claims from source. little-coder is a launcher plus
a fixed set of extensions for the **pi** coding agent
(`@earendil-works/pi-coding-agent` `^0.83.0`, [package.json:41](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/package.json#L41)); it spawns
pi's own CLI from its `node_modules` ([bin/little-coder.mjs:98-136](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/bin/little-coder.mjs#L98-L136),
[505-509](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/bin/little-coder.mjs#L505-L509)). pi's storage was therefore read at earendil-works/pi tag
`v0.83.0`, [`845d6ff1f6643aba440341cce877ce1c43ebbc39`](https://github.com/earendil-works/pi/commit/845d6ff1f6643aba440341cce877ce1c43ebbc39).
Record schema: `analyzer/research/little-coder.md`.

## 2. Per-user storage

**Shared with pi: `~/.pi/agent`.** The launcher and pi both use
`PI_CODING_AGENT_DIR` (with `~` expansion) or `homedir()/.pi/agent` on every
OS ([little-coder.mjs:24-35](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/bin/little-coder.mjs#L24-L35); pi
[packages/coding-agent/src/config.ts:491-496](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/config.ts#L491-L496), [515-521](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/config.ts#L515-L521)). In it pi
keeps `settings.json`, `auth.json`, `models.json`,
`themes/`, `tools/`, `bin/` (fd, rg), `prompts/`, `pi-debug.log` and
`sessions/` ([config.ts:523-566](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/config.ts#L523-L566)). Sessions are
`sessions/--<cwd with / \ : replaced by ->--/<ISO timestamp>_<uuid>.jsonl`
([packages/coding-agent/src/core/session-manager.ts:476-481](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/session-manager.ts#L476-L481), [950-953](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/session-manager.ts#L950-L953)),
overridable by `PI_CODING_AGENT_SESSION_DIR` ([config.ts:495-496](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/config.ts#L495-L496)).
little-coder sessions and plain pi sessions share this directory and
cannot be told apart by path. little-coder itself writes:

- `settings.json`: merges `quietStartup: true` and `lastChangelogVersion`
  on each interactive launch ([little-coder.mjs:400-466](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/bin/little-coder.mjs#L400-L466)); a v1.9.0
  keybinding is removed from `keybindings.json` ([:468-490](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/bin/little-coder.mjs#L468-L490)).
- `little-coder-prompt-history.json`: a JSON array of the last 100 prompts
  typed, no timestamps ([.pi/extensions/prompt-history/index.ts:23-26](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/prompt-history/index.ts#L23-L26), [38-40](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/prompt-history/index.ts#L38-L40), [52-57](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/prompt-history/index.ts#L52-L57)).

**`~/.little-coder/checkpoints/<session file name>/`.** Before a `write` or
`edit` tool call, the first time per session, a copy of the target file's
previous contents is saved under a name derived from its path (non
`[A-Za-z0-9._-]` characters become `_`, last 200 characters), or an empty
`<name>.absent` if it did not exist
([.pi/extensions/checkpoint/index.ts:6-9](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/checkpoint/index.ts#L6-L9), [25-58](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/checkpoint/index.ts#L25-L58)). The directory is the session
file's basename, so it matches a `sessions/` JSONL file
([:63-65](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/checkpoint/index.ts#L63-L65)). `homedir()` on every OS.

**`~/.config/little-coder/`**, or `$XDG_CONFIG_HOME/little-coder`, using
`HOME` or `USERPROFILE`, so `~/.config` on macOS and Windows too:
- `models.json`, the user's provider override (`LITTLE_CODER_MODELS_FILE`
  wins) ([little-coder.mjs:46-56](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/bin/little-coder.mjs#L46-L56); [.pi/extensions/llama-cpp-provider/config.ts:75-82](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/llama-cpp-provider/config.ts#L75-L82)).
- `extensions/`, user extensions loaded on every launch
  (`LITTLE_CODER_EXTENSIONS_DIR` wins) ([bin/user-extensions.mjs:17-22](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/bin/user-extensions.mjs#L17-L22), [37-51](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/bin/user-extensions.mjs#L37-L51)).

**`~/.cache/little-coder/version-check.json`** (or `$XDG_CACHE_HOME`):
update check timestamp and latest version ([bin/update-check.mjs:33-37](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/bin/update-check.mjs#L33-L37)).

The package itself (`.pi/extensions/`, `AGENTS.md` used as the system
prompt, `skills/`, bundled `models.json`) lives in the global npm or bun
install, not the home ([little-coder.mjs:163](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/bin/little-coder.mjs#L163), [314](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/bin/little-coder.mjs#L314)).

## 3. Credentials

- `~/.pi/agent/auth.json`, pi's credential store, mode 0600
  ([packages/coding-agent/src/core/auth-storage.ts:21](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/auth-storage.ts#L21), [31](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/auth-storage.ts#L31)). Belongs to pi.
- `~/.config/little-coder/models.json`: `providers.<name>.apiKey` is meant
  to name an environment variable, but a value that names none is used as a
  literal key ([config.ts:4-14](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/llama-cpp-provider/config.ts#L4-L14), [294-300](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/llama-cpp-provider/config.ts#L294-L300)). Flag it.
- No keychain use.

## 4. Exclusions

None. Checkpoints are copies of project files and can be large on a busy
host, but they are pre-edit evidence; keep them.

## 5. Project-local files

- `.pi/approved-plan.md`, written by the plan mode in the session's cwd
  ([.pi/extensions/plan-mode/index.ts:20](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/plan-mode/index.ts#L20), [740-742](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/plan-mode/index.ts#L740-L742)).
- Reads `AGENTS.md`, then `CLAUDE.md`, from the project
  ([.pi/extensions/project-context/discover.ts:21-27](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/project-context/discover.ts#L21-L27)); pi's own project
  context loading is turned off with `--no-context-files`, and project
  `.pi/extensions` load only with `--with-pi-extensions`
  ([little-coder.mjs:222-228](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/bin/little-coder.mjs#L222-L228), [365-372](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/bin/little-coder.mjs#L365-L372)).
- `/deep-research` writes its report into the cwd
  ([.pi/extensions/deep-research/index.ts:366-367](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/deep-research/index.ts#L366-L367)).

## 6. Where the project path is recorded

The pi session header line: `{"type":"session",...,"cwd":...}`
([session-manager.ts:32-39](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/session-manager.ts#L32-L39), [936-944](https://github.com/earendil-works/pi/blob/845d6ff1f6643aba440341cce877ce1c43ebbc39/packages/coding-agent/src/core/session-manager.ts#L936-L944)), and the encoded
session directory name. Checkpoint file names encode absolute paths, but
lossily (`/` becomes `_`).

## 7. Catalog proposal

pi's `~/.pi/agent` (sessions, `auth.json`) should be its own catalog entry;
the lines below are what is specific to little-coder. The prompt history
file is nested inside pi's directory and claims itself.

```
little-coder|.little-coder
little-coder|.config/little-coder
little-coder|.cache/little-coder
little-coder|.pi/agent/little-coder-prompt-history.json
```

```
project|.pi/approved-plan.md
```

```
# none
```

```
.config/little-coder/models.json
```

Discovery sources:

```
.pi/agent/sessions/*/*.jsonl  first line "cwd"   (pi's; covers little-coder sessions)
```

## 8. Confidence

High: every path above, the env overrides, the checkpoint naming, the
prompt history format, that sessions are pi's (source). High for pi paths
at v0.83.0 (source at the tag); a later little-coder that moves to pi 1.x
may differ. Medium: on Windows the checkpoint directory name, since the
extension splits the session path on `/` only
([checkpoint/index.ts:64](https://github.com/itayinbarr/little-coder/blob/89d4fa0af864230527ab75d12604ed0eb320e6df/.pi/extensions/checkpoint/index.ts#L64)) and a backslash path would not be
split. Not determined: real sizes of `checkpoints/`; whether pi project
files beyond `.pi/approved-plan.md` are written when `--with-pi-extensions`
is used (that is pi's behaviour, covered by pi's own research).
