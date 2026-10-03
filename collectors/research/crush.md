# Crush: on-disk paths

## 1. Source and evidence level

charmbracelet/crush, open source, commit `ca6ae26ce016b980407ce32f012a467ec10c1e2f`. All claims from source. Transcript schema is in `analyzer/research/crush.md`.

## 2. Per-user storage

Home comes from `os.UserHomeDir()` and the config root is `XDG_CONFIG_HOME` or `~/.config` on every OS, Windows included (`internal/home/home.go:12,26-31`).

Config: `~/.config/crush/crush.json`, or `$CRUSH_GLOBAL_CONFIG/crush.json` (`internal/config/load.go:1212-1216`), with an optional sibling shell config `crushrc` (`load.go:1219-1231`). Global context files default to `~/.config/crush/CRUSH.md` and `~/.config/AGENTS.md` (`load.go:578-582`). Commands are read from `~/.config/crush/commands`, `~/.crush/commands` and `<data dir>/commands` (`internal/commands/commands.go:125-133`). Skills from `$CRUSH_SKILLS_DIR`, `~/.config/crush/skills`, `~/.config/agents/skills` (`load.go:1366-1372`). System config `/etc/crush/crush.json` on Unix, none on Windows (`internal/config/config_unix.go:7`, `config_windows.go:8`).

Data: `GlobalConfigData()` is `$CRUSH_GLOBAL_DATA/crush.json`, `$XDG_DATA_HOME/crush/crush.json`, `%LOCALAPPDATA%\crush\crush.json` on Windows, else `~/.local/share/crush/crush.json` (`load.go:1259-1281`). The directory also holds `projects.json` (`internal/projects/projects.go:14,31-32`) and a `locks/` directory (`internal/config/store.go:1102`). It is "writable machine state and must never be executed as Bash" (`load.go:947-949`). There is no session database here; sessions live in each project.

Cache: `$CRUSH_CACHE_DIR`, `$XDG_CACHE_HOME/crush`, `%LOCALAPPDATA%\crush\cache` on Windows, else `~/.cache/crush` (`load.go:1235-1250`), containing only `server-<host>/crush.log` for client-server mode (`internal/cmd/server.go:50`, `internal/cmd/root.go:508,627`).

Environment variables: `CRUSH_GLOBAL_CONFIG`, `CRUSH_GLOBAL_DATA`, `CRUSH_CACHE_DIR`, `CRUSH_SKILLS_DIR`, `CRUSH_HYPER_API_KEY`, `XDG_*`.

## 3. Credentials

- `~/.local/share/crush/crush.json` (Windows `%LOCALAPPDATA%\crush\crush.json`): the TUI writes provider keys and OAuth tokens here. `SetProviderAPIKey` (`store.go:569`) resolves the global scope to `globalDataPath` (`store.go:330-341`); `ProviderConfig` has `api_key` (`config.go:102`) and `oauth` (`config.go:106`); MCP entries persist `oauth_token` (`config.go:273-275`, orphan cleanup `config.go:326-328`); the Hyper provider token is refreshed in this file (`load.go:109`).
- `~/.config/crush/crush.json` can hold the same `api_key` fields literally or as `$ENV` references.
- `~/.config/crush/crushrc` and project `crushrc`/`.crushrc` are shell scripts that typically export keys.
- Project `.crush/crush.json` is the workspace scope and `SetProviderAPIKey` can target it (`store.go:333-337`).
- Crush also reads `~/.config/github-copilot/apps.json` (`%LOCALAPPDATA%\github-copilot\apps.json`) for Copilot OAuth (`internal/oauth/copilot/disk.go:32-34`) and probes `~/.aws/credentials` and `~/.aws/login` (`load.go:1118-1121`). No keychain use.

## 4. Exclusions

Nothing large under home. In projects, `.crush/crush-fetch-*` are temporary fetch directories (`internal/agent/agentic_fetch_tool.go:102`); `.crush/shell-output` holds spilled tool output (`internal/shell/truncate.go:29`) and is evidence, so keep it. `~/.cache/crush` is only logs; collect or skip at will.

## 5. Project-local files

Data dir is the closest `.crush` between cwd and the git root, else `<cwd>/.crush` (`config.go:25`, `load.go:590-593`). Contents: `crush.db` with `-wal`/`-shm` (`internal/db/connect.go:20,93`), `crush.json` workspace overrides (`load.go:58`, `store.go:97`), `logs/crush.log` (`root.go:311`), `commands/`, `shell-output/`, `crush-fetch-*`, and a `.gitignore` containing `*` (`root.go:295-297`), so git never sees it. Config files searched from cwd up to the git root: `.crushrc`, `crushrc`, `.crush.json`, `crush.json` (`load.go:962-970`). Context files: `.github/copilot-instructions.md`, `.cursorrules`, `.cursor/rules/`, `CLAUDE.md`, `CLAUDE.local.md`, `GEMINI.md`, `gemini.md`, `crush.md`, `crush.local.md`, `Crush.md`, `Crush.local.md`, `CRUSH.md`, `CRUSH.local.md`, `AGENTS.md`, `agents.md`, `Agents.md` (`config.go:29-45`). Ignore file `.crushignore` (`internal/fsext/ls.go:141,168`).

## 6. Where the project path is recorded

`projects.json` next to the data `crush.json`: `projects[].path`, `projects[].data_dir`, `projects[].last_accessed` (`projects.go:18-25`), registered on every start (`root.go:302`). `crush stats` itself crawls for `.crush/crush.db` (`internal/cmd/stats.go:247-265`), confirming the layout.

## 7. Catalog review

Home: `.config/crush` confirmed; `.local/share/crush` confirmed; `AppData/Local/crush` confirmed (data and cache). No `AppData/Roaming/crush` exists, correctly absent.
Project: `.crush`, `crush.json`, `.crush.json`, `crushrc`, `.crushrc`, `.crushignore`, `CRUSH.md` all confirmed. `crush.md`, `Crush.md`, `*.local.md` variants are not listed.
Excluded: none; nothing needed.
Credential: `.local/share/crush/crush.json` confirmed; `.config/crush/crush.json` confirmed; `.config/crush/crushrc` confirmed; `.crush/crush.json` confirmed.

Add:
```
# home
crush|.crush
crush|.cache/crush
# project
project|CRUSH.local.md
project|crush.md
project|crush.local.md
project|Crush.md
project|Crush.local.md
# credential
AppData/Local/crush/crush.json
.config/crush/.crushrc
*/.crush/crush.json
```
`~/.crush` is only a commands directory (`commands.go:129`) but is cheap. Consider flagging project `crushrc`, `.crushrc`, `crush.json`, `.crush.json` as secrets since the same `api_key` field is valid there.

## 8. Confidence

High: all paths and file names (source). Medium: whether `.crushrc` is honoured globally; `shellConfigSibling` only derives `crushrc` (`load.go:1219-1225`), so the `.config/crush/.crushrc` addition is speculative. Not determined: whether exclusion globs apply inside project directories, which the `*/.crush/crush.json` form assumes.
