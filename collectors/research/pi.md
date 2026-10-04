# pi: on-disk paths

## 1. Source and evidence level

earendil-works/pi (the monorepo for the `pi` coding agent CLI,
`@earendil-works/pi-coding-agent` 1.0.2), MIT licence
([LICENSE:1](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/LICENSE#L1)), open source, TypeScript. Reviewed commit
[`200387122ca450d6387f033949423114a270b96c`](https://github.com/earendil-works/pi/commit/200387122ca450d6387f033949423114a270b96c) (2026-10-04). Where the
layout differs, tag `v0.83.0`
([`845d6ff1f6643aba440341cce877ce1c43ebbc39`](https://github.com/earendil-works/pi/commit/845d6ff1f6643aba440341cce877ce1c43ebbc39)), the version little-coder
pins, is cited. All claims from source; nothing was installed or run.
Wrappers that reuse pi's storage: `little-coder` (same `~/.pi/agent`, see
[little-coder.md](little-coder.md)) and Letta Code's local backend (pi
session format in its own directory, see [letta.md](letta.md)). Record
schema: `analyzer/research/pi.md`.

## 2. Per-user storage

One layout on every OS. The agent directory is `$PI_CODING_AGENT_DIR` (with
`~` expanded) or `os.homedir()/.pi/agent`
([`packages/coding-agent/src/config.ts:566-572`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/config.ts#L566-L572); tilde expansion
[`utils/paths.ts:88-93`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/utils/paths.ts#L88-L93)). No XDG, no `AppData`, no `Library`: Windows is
`C:\Users\<u>\.pi\agent`. The `.pi` name and the env-var prefix come from
`piConfig` in the package's `package.json`
([`config.ts:538-547`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/config.ts#L538-L547), [`package.json:6-8`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/package.json#L6-L8)), so a rebranded build
(the source comment's example is `TAU_CODING_AGENT_DIR`) uses another
directory and is not covered by the lines below.

Under `~/.pi/agent`:

- `sessions/--<cwd>--/<ISO timestamp>_<session id>.jsonl`: one JSONL
  transcript per session ([`config.ts:610-612`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/config.ts#L610-L612);
  [`core/session-manager.ts:589-594`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L589-L594), [`1079-1080`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L1079-L1080)). The directory
  name is the cwd with a leading `/` or `\` dropped and every `/`, `\`, `:`
  replaced by `-`: `/home/alice/proj` → `--home-alice-proj--`,
  `C:\Users\alice\proj` → `--C--Users-alice-proj--`. The file name is the
  ISO time with `:` and `.` replaced by `-`. A file is only created once a
  user or assistant message exists ([`1161-1170`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L1161-L1170)). The
  directory can be moved with `--session-dir`,
  `$PI_CODING_AGENT_SESSION_DIR` or the `sessionDir` setting, in that order
  ([`main.ts:688-692`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/main.ts#L688-L692)); a custom directory is flat, with no per-cwd
  subdirectory ([`session-manager.ts:1755-1757`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L1755-L1757)). Sessions written by
  v0.30.0 sat directly in `~/.pi/agent/*.jsonl` until a migration moved
  them ([`migrations.ts:76-84`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/migrations.ts#L76-L84)).
- `settings.json` (global settings; `packages`, `extensions`, `skills`,
  `sessionDir`, `httpProxy`, default provider and model)
  ([`config.ts:590-592`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/config.ts#L590-L592); [`core/settings-manager.ts:133-138`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/settings-manager.ts#L133-L138), [`159-180`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/settings-manager.ts#L159-L180)),
  `keybindings.json` ([`core/keybindings.ts:379-380`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/keybindings.ts#L379-L380)).
- `auth.json`, `models.json`, `models-store.json` (dynamically refreshed
  provider model catalogs) ([`config.ts:580-587`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/config.ts#L580-L587); [`core/models-store.ts:52`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/models-store.ts#L52)).
- `trust.json`: project trust decisions keyed by absolute path
  ([`core/trust-manager.ts:28`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/trust-manager.ts#L28), [`214`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/trust-manager.ts#L214), [`232-241`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/trust-manager.ts#L232-L241)).
- `mcp.json` (MCP servers), `mcp-auth.json` (MCP OAuth state), `mcp.log`
  ([`extensions/mcp/config.ts:146-148`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/extensions/mcp/config.ts#L146-L148); [`extensions/mcp/oauth.ts:137-145`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/extensions/mcp/oauth.ts#L137-L145);
  [`extensions/mcp/index.ts:351`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/extensions/mcp/index.ts#L351)). Not present at v0.83.0.
- `crashes.json`: last five crashes with `timestamp`, `message`, `stack`,
  `sessionFile`, `cwd` ([`core/crash-log.ts:6-23`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/crash-log.ts#L6-L23)). Not present at v0.83.0.
- `pi-debug.log`, written by `/debug` ([`config.ts:615-617`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/config.ts#L615-L617)).
- User resources: `extensions/`, `skills/`, `prompts/` (formerly
  `commands/`), `themes/`, `AGENTS.md`/`CLAUDE.md` global context,
  `SYSTEM.md`, `APPEND_SYSTEM.md`
  ([`core/resource-loader.ts:978-982`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/resource-loader.ts#L978-L982), [`1207`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/resource-loader.ts#L1207), [`1221`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/resource-loader.ts#L1221), [`242-246`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/resource-loader.ts#L242-L246);
  [`migrations.ts:137-143`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/migrations.ts#L137-L143)). Skills are also read from `~/.agents/skills`
  ([`core/trust-manager.ts:187-188`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/trust-manager.ts#L187-L188)), already in the catalog as `shared|.agents`.
- Installed packages (`pi install`): `npm/` (an npm root with
  `package.json` and `node_modules/<name>`) and `git/<host>/<path>`
  checkouts ([`core/package-manager.ts:2134`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/package-manager.ts#L2134), [`2154-2174`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/package-manager.ts#L2154-L2174)); temporary
  checkouts in `tmp/extensions/` ([`231-236`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/package-manager.ts#L231-L236)).
- `bin/` (downloaded `fd` and `rg`), legacy `tools/`
  ([`config.ts:595-602`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/config.ts#L595-L602); [`migrations.ts:176-185`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/migrations.ts#L176-L185)).
- Experimental (`PI_EXPERIMENTAL=1`, [`core/experimental.ts:1-3`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/experimental.ts#L1-L3);
  [`experimental/commands.ts:86`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/experimental/commands.ts#L86)), not at v0.83.0:
  `experimental/sessions/<id>/{meta.json,session.sqlite}`
  ([`experimental/server.ts:69-71`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/experimental/server.ts#L69-L71); [`experimental/session-catalog.ts:5-16`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/experimental/session-catalog.ts#L5-L16)),
  `experimental/vacation-sessions/<sha256(cwd)[:24]>/<ms>-<uuid>/session.sqlite`
  ([`experimental/vacation/sessions.ts:18-55`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/experimental/vacation/sessions.ts#L18-L55)), and a server directory
  `$PI_SERVER_DIR` or `~/.pi/server` holding `default-server-id`, lock
  directories and Unix sockets ([`experimental/server.ts:51-56`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/experimental/server.ts#L51-L56), [`85-91`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/experimental/server.ts#L85-L91)).

Outside the home: truncated bash output is spilled to
`<tmpdir>/pi-bash-<16 hex>.log` ([`core/bash-executor.ts:68-69`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/bash-executor.ts#L68-L69)), MCP and
codemode output to `pi-mcp-*` and `pi-codemode-*.txt`
([`extensions/mcp/tools.ts:72`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/extensions/mcp/tools.ts#L72); [`extensions/codemode/execute.ts:263`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/extensions/codemode/execute.ts#L263)); the session
records the path in `fullOutputPath`.

**pi rewrites its own evidence.** Opening an older-format session rewrites
the whole file in the current format ([`session-manager.ts:1088-1094`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L1088-L1094)),
and loading a file whose last line has no newline appends one
([`668`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L668)). Collect before anyone resumes a session on the host.

## 3. Credentials

- `~/.pi/agent/auth.json`, created mode 0600 in a 0700 directory: one
  object per provider, `{type:"api_key", key, env}` or `{type:"oauth",
  refresh, access, expires, ...}`
  ([`core/auth-storage.ts:24-25`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/auth-storage.ts#L24-L25), [`52-60`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/auth-storage.ts#L52-L60); [`packages/ai/src/auth/types.ts:17-37`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/ai/src/auth/types.ts#L17-L37)).
  No keychain.
- `~/.pi/agent/mcp-auth.json`: MCP client registrations, tokens and pending
  PKCE verifiers ([`extensions/mcp/oauth.ts:137-145`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/extensions/mcp/oauth.ts#L137-L145)).
- `~/.pi/agent/models.json`: custom providers may carry `apiKey` and
  `headers` ([`core/model-config.ts:242-251`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/model-config.ts#L242-L251)); a value is a literal, an
  env reference, or `!command` whose stdout is used
  ([`core/resolve-config-value.ts:140-145`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/resolve-config-value.ts#L140-L145)). Flag it.
- `~/.pi/agent/mcp.json` and project `.pi/mcp.json`: `headers` such as
  `Authorization: Bearer ...` ([`extensions/mcp/config.ts:14-21`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/extensions/mcp/config.ts#L14-L21)). Flag it.
- Legacy: `oauth.json` and `settings.json` `apiKeys` were folded into
  `auth.json`; the old file is renamed `oauth.json.migrated`, not deleted
  ([`migrations.ts:20-60`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/migrations.ts#L20-L60)).
- pi also reads, but does not write, `~/.config/gcloud/application_default_credentials.json`
  ([`packages/ai/src/env-api-keys.ts:60-67`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/ai/src/env-api-keys.ts#L60-L67)) and the Hugging Face token
  ([`extensions/llama/huggingface.ts:51-55`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/extensions/llama/huggingface.ts#L51-L55)); they belong to those tools.

## 4. Exclusions

`bin/` holds third-party binaries. `npm/node_modules`, the `git/` checkouts
and `tmp/` are installed extension packages; the package sources stay
recorded in `settings.json` `packages` and `npm/package.json`
([`package-manager.ts:2068`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/package-manager.ts#L2068)), so exclude only their dependency trees and
`.git`. Project `.pi/npm` and `.pi/git` are the same at project scope
([`2130-2132`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/package-manager.ts#L2130-L2132), [`2169-2172`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/package-manager.ts#L2169-L2172)). Sockets in `~/.pi/server` cannot be copied.
Sessions themselves stay: images are inline base64 and can be large, but
they are the transcript.

## 5. Project-local files

`<cwd>/.pi/` holds `settings.json`
([`settings-manager.ts:301`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/settings-manager.ts#L301)), `mcp.json`, `extensions/`, `skills/`,
`prompts/`, `themes/`, `SYSTEM.md`, `APPEND_SYSTEM.md`, `npm/`, `git/`
([`trust-manager.ts:30-39`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/trust-manager.ts#L30-L39); [`resource-loader.ts:984-988`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/resource-loader.ts#L984-L988)). Project
extensions run with the user's rights once the folder is trusted, so they
are evidence. little-coder adds `.pi/approved-plan.md`. Context files read
from the cwd up: `AGENTS.override.md`, `AGENTS.md`, `AGENTS.MD`,
`CLAUDE.md`, `CLAUDE.MD` ([`resource-loader.ts:183-185`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/resource-loader.ts#L183-L185)), and
`.agents/skills` up to the git root ([`package-manager.ts:467-480`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/package-manager.ts#L467-L480)).
Exports land in the cwd by default: `/export` HTML as
`pi-session-<session file basename>.html`
([`core/export-html/index.ts:274-277`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/export-html/index.ts#L274-L277)) and JSONL as `session-<ISO time>.jsonl`
([`core/session-export.ts:37-43`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-export.ts#L37-L43)). No per-project database.

## 6. Where the project path is recorded

- Session header (line 1 of each file), key `cwd`
  ([`session-manager.ts:43-50`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/session-manager.ts#L43-L50)); the directory name is a lossy copy.
- `trust.json`: every key is an absolute project path, value `true` or
  `false` ([`trust-manager.ts:232-241`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/trust-manager.ts#L232-L241)).
- `crashes.json`: `cwd` and `sessionFile` per record ([`crash-log.ts:6-15`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/core/crash-log.ts#L6-L15)).
- `experimental/sessions/*/meta.json`: `cwd` ([`session-catalog.ts:6-13`](https://github.com/earendil-works/pi/blob/200387122ca450d6387f033949423114a270b96c/packages/coding-agent/src/experimental/session-catalog.ts#L6-L13)).

## 7. Confidence

High: the agent directory, its override, every file name above, the session
directory encoding and file naming, credential file shapes, project `.pi`
contents (source). High that the layout is the same on Windows (plain
`homedir()` join). Medium: `.pi/agent/auth.json.*` (no backup file is
written by the code read; the glob only guards against editors'
copies); whether `.pi/mcp.json` holds literal tokens in practice (the
documented form is `${ENV}` interpolation); exclusion globs inside a
project `.pi`. Not determined: whether `vacation-sessions` is gated by
`PI_EXPERIMENTAL`; the contents of `pi-debug.log` beyond the rendered TUI
lines; whether a rebranded pi build (`piConfig.configDir`) is in use
anywhere, which would need its own catalog line.
