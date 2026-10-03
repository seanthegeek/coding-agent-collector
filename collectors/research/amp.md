# amp (Sourcegraph Amp CLI)

## 1. Source and evidence level

- Closed source. npm `@sourcegraph/amp` is now an alias whose only dependency is `@ampcode/cli` (`scratchpad/npm/amp/package/package.json`, "Renamed to @ampcode/cli"). `@ampcode/cli` 0.0.1791060199-g5bacb8 is a wrapper (`install.cjs`, `cli-wrapper.cjs`) over per-platform packages; the Linux binary is `@ampcode/cli-linux-x64/amp`, a bun-compiled ELF (128 MB). Evidence level **B** = `strings -n 8` (`scratchpad/npm/amp.strings`) and `strings -el` UTF-16 (`scratchpad/npm/amp.strings16`) of that binary; the UTF-16 table holds the minified application code and is where the path joins live.
- Evidence level **D** = official docs, fetched as Markdown from `https://ampcode.com/docs/markdown/<page>` (saved in `scratchpad/amp-docs/`; index `https://ampcode.com/llms.txt`).
- Evidence level **S** = install script `https://ampcode.com/install.sh` (`scratchpad/amp-install.sh`).
- Thread transcripts are server-side: the bug-report bundler writes "The full thread is stored server-side and can be fetched by a site admin" (`amp.strings` near `thread/full.json`); docs say remote MCP definitions and threads are "stored by ampcode.com" (`customize_mcp.md:15,301`). No local thread transcript store was found in either strings table; only per-thread *logs* (section 2).

## 2. Per-user storage

Path resolution in the CLI code has no platform branching, so the layout is identical on Linux, macOS and Windows (B, `amp.strings16`):

```
fzt=process.env.XDG_DATA_HOME||join(home,".local/share")
dzt=process.env.XDG_CONFIG_HOME||join(home,".config")
tg =join(fzt,"amp")                    # data dir
DL =join(dzt,"amp","settings.json")    # settings default
F6t=join(process.env.XDG_CACHE_HOME??join(home,".cache"),"amp"), us=F6t   # cache/log dir
```

One auxiliary module (ripgrep download) differs: data = `~/.local/share/amp` even when `XDG_DATA_HOME` is set on win32/darwin, and cache = `%LOCALAPPDATA%\amp` on win32 (`La=...` in `amp.strings`). Only `<that cache>/bin/<rg>` is written there (`It.join(Pt,"bin")`).

Config `~/.config/amp/` (B+D `cli_settings.md:10-14`):
- `settings.json` or `settings.jsonc` (`.jsonc` fallback string "Settings file not found, falling back to .jsonc"); overridable by `--settings-file` / `AMP_SETTINGS_FILE`.
- `AGENTS.md` and also `~/.config/AGENTS.md`, `~/.config/AGENT.md` (`customize_agents-md.md:38`, `"~/.config/AGENT.md"` in code).
- `skills/` (`join(home,".config","amp","skills")`), `plugins/*.ts` (`customize_plugins`), `obelisk-app.env` (orb sandbox only).
- Shared agent dirs also read: `~/.config/agents/skills/`, `~/.agents/skills/` (`customize_skills.md:36-38`).

Data `~/.local/share/amp/` (B):
- `secrets.json` (`Fnt(H)=join(H.dataDir,VCr)`, `VCr="secrets.json"`), `accounts.json` (`join(H,"accounts.json")` in class `DGe`), `accounts/<identityKey>-<server>/secrets.json` for non-legacy multi-account (`join(dirname(H),"accounts",ED.directoryName,basename(H))`; `dataDir:join(tg,"accounts")`).
- `history.jsonl` prompt history, entries `{text, cwd}` (`rgr=join(Dit,"history.jsonl")`, `EiH(H){return H.text.length+(H.cwd?.length??0)}`; migrates from `history.json`).
- `device-id.json`, `guest-id`, `net/` (Amp Net sockets), `oauth/locks`, `orb-services/ad-hoc-services.json`, `runner/`, `daemon/`, `ide/` (IDE auth tokens: schema has `authToken`).

Cache `~/.cache/amp/` (B+D):
- `logs/cli.log` (10 MB rotate, 2 files), `logs/threads/<T-id>.log` per-thread logs, 7-day prune (`KGe=join(us,"logs"),LV=join(KGe,"threads"),JQ=join(KGe,"cli.log")`, `Y_$=604800000`), `logs/headless.log`, `logs/orb-services/`, `logs/orb-provider/`.
- `terminal/<threadId>/history` terminal-tool shell history (`iO(us,"terminal",threadId)`).
- `bin/rg` downloaded ripgrep, `pids/`, `portal-speed-test/latest.json`, `runner-desktop/<runner-id>/` compositor state (`cli_runners.md:84`), `desktop/` (orb desktop logs), `obelisk-runs/`.

Installer home `~/.amp/` (`AMP_HOME`, S `amp-install.sh:5-6`; B `join(home,".amp")`):
- `bin/amp`, `bin/amp-desktop-helper/<ver>/`, `bin/waymote/<ver>/` (`cli_runners.md:58,78`), `signing-key.pub`, `amp-install-signature.minisign`.
- `oauth/<server>-client.json` MCP OAuth client registrations (`join(HOME||USERPROFILE,".amp","oauth")`, `getClientInfoPath`).
- `claude-diagnostics/<T-id>/sessions/` copies of Claude Code session files when Amp drives Claude Code as an external agent (`join(home,".amp","claude-diagnostics",thread,"sessions")`).

System-wide (not per-user): `/etc/ampcode/`, `/Library/Application Support/ampcode/`, `%ProgramData%\ampcode\` holding `managed-settings.json` and `AGENTS.md` (`cli_settings.md:261-263`, `customize_agents-md.md:28`).

Env relocation: `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME`, `AMP_HOME`, `AMP_SETTINGS_FILE`, `AMP_LOG_FILE`.

## 3. Credentials

- Primary store is the OS keyring via `@napi-rs/keyring` (keyring-rs 3.6.3; service `amp.cli.<kind>`, account `amp.cli.account`). File fallback `~/.local/share/amp/secrets.json` (logger child `secrets.file`) and per-account `accounts/*/secrets.json`. Secret keys: `apiKey`, `mcp-oauth-client-secret`, `mcp-oauth-token`, `oauth-refresh-token` (`lzt=[...]`). (B)
- `accounts.json` lists saved accounts (email, server) — identity evidence, not a token.
- `~/.amp/oauth/*-client.json`: OAuth client info; `clientSecret` is stripped to secret storage before writing (`let{clientSecret:t,...r}=e`). (B)
- `~/.local/share/amp/ide/*` IDE connection records include `authToken`. (B)
- `settings.json` can embed MCP server `env`/headers (`amp.mcpServers`, `customize_mcp.md:244-245`). `AMP_API_KEY` env var.
- `.config/amp/secrets.json` (current catalog) was not found anywhere in the binary.

## 4. Exclusions

`.cache/amp/runner-desktop`, `.cache/amp/desktop`, `.cache/amp/bin`, `.cache/amp/obelisk-runs`, `.cache/amp/pids`, `.amp/bin`, `AppData/Local/amp/bin`.

## 5. Project-local files

`.amp/settings.json` or `.amp/settings.jsonc` searched upward (`join(o,".amp","settings.json")`), `.amp/plugins/*.ts`, `.amp/portals/*.json`, `.amp/portal-proxy.mjs`, `.amp/live-sync.pid`, `.amp/terminal/history` (legacy), `.amp/cache/ios-simulator-derived-data`, `.amp/services.yaml`, `.amp/obelisk.yaml`; `AGENTS.md` (fallback `AGENT.md`, `CLAUDE.md`) at every level up to `$HOME` (`customize_agents-md.md:36-44`); `.agents/skills/`. Commits carry an `Amp-Thread-ID` trailer (`threads.md:136`).

## 6. Project path records

`~/.local/share/amp/history.jsonl`: JSONL, key `cwd` per entry (B, medium). `~/.cache/amp/logs/threads/<T-id>.log` lines carry a thread id; cwd content unverified. No local thread index.

## 7. Catalog review

Current:
- `amp|.config/amp` — confirmed (B, D).
- `amp|.local/share/amp` — confirmed, all OSes (B).
- `amp|.cache/amp/logs` — confirmed (B); also on Windows since `us` has no platform branch.
- `amp|AppData/Local/amp/logs` — doubtful: `%LOCALAPPDATA%\amp` receives only `bin/` (ripgrep); harmless but empty.
- `project|.amp` — confirmed.
- `.cache/amp/runner-desktop`, `.cache/amp/desktop` — confirmed (D, B).
- `.local/share/amp/secrets.json`, `.local/share/amp/accounts.json` — confirmed (B).
- `.config/amp/secrets.json` — wrong: no such path in the binary; harmless.

Add:
```
amp|.amp
amp|.config/AGENTS.md
amp|.config/AGENT.md
amp|.config/agents
amp|.agents
amp|.cache/amp/terminal
project|.agents
project|AGENTS.md
.amp/bin
.cache/amp/bin
.cache/amp/obelisk-runs
.local/share/amp/accounts/*/secrets.json
.local/share/amp/ide/*
.amp/oauth/*
```
Discovery: `~/.local/share/amp/history.jsonl` key `cwd`.

## 8. Confidence

High: config/data/cache resolution, `settings.json(c)`, `secrets.json`, `accounts.json`, `history.jsonl`, `logs/cli.log`, `logs/threads`, `~/.amp/bin`, `~/.amp/oauth`, keyring use, server-side threads. Medium: `history.jsonl` `cwd` key (inferred from size accounting and type); `accounts/<dir>/secrets.json` naming; `ide/` contents. Low: whether `AppData/Local/amp` ever holds anything but `bin`. Not determined: exact JSON schema of `secrets.json`/`accounts.json`; whether `claude-diagnostics` is created outside orb sandboxes; Windows keyring behaviour (Credential Manager via keyring-rs assumed).
