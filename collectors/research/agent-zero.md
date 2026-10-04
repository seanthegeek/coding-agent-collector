# Agent Zero: on-disk paths

Catalog agent: `agent-zero`. Transcript schema is in
[`analyzer/research/agent-zero.md`](../../analyzer/research/agent-zero.md).

## 1. Source and evidence level

agent0ai/agent-zero at commit
[`e3051fb584b1a36be2b0a0c90606f1c2c2d356ec`](https://github.com/agent0ai/agent-zero/commit/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec).
The `LICENSE` file at that commit is plain MIT
([`LICENSE:1-4`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/LICENSE#L1-L4)), not a custom licence. Python, source public. Three companion
repositories decide where the data lands on the host and were also read:
agent0ai/a0-install at [`c89b4026e9f16f53389e75537783411fefdd53f1`](https://github.com/agent0ai/a0-install/commit/c89b4026e9f16f53389e75537783411fefdd53f1)
(installer scripts), agent0ai/a0-launcher at
[`b0333d80b5abf38d8481f55b667b0cf23d805bbb`](https://github.com/agent0ai/a0-launcher/commit/b0333d80b5abf38d8481f55b667b0cf23d805bbb) (Electron launcher, MIT,
[`LICENSE:1`](https://github.com/agent0ai/a0-launcher/blob/b0333d80b5abf38d8481f55b667b0cf23d805bbb/LICENSE#L1)), and agent0ai/a0-connector at
[`76e834f20e50f6e47954c89ee39dd4c5b50d81b7`](https://github.com/agent0ai/a0-connector/commit/76e834f20e50f6e47954c89ee39dd4c5b50d81b7) (the host-side "A0 CLI", MIT,
[`LICENSE:1`](https://github.com/agent0ai/a0-connector/blob/76e834f20e50f6e47954c89ee39dd4c5b50d81b7/LICENSE#L1)). All claims are from source or the in-repo docs. Nothing
was installed or run.

## 2. Per-user storage

**Agent Zero itself never resolves a home directory.** Every path is relative
to the install directory, the parent of `helpers/`
([`helpers/files.py:23`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/files.py#L23),[`575-584`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/files.py#L575-L584)), shown to the agent as `/a0/...`
([`files.py:618-623`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/files.py#L618-L623)). In the container that is `/a0`; all user state is
under `/a0/usr` and `/a0/tmp`, both gitignored
([`.gitignore:26-39`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/.gitignore#L26-L39)). Where that lands on the host depends on how
it was started:

| Deployment | Host location of `/a0/usr` |
| --- | --- |
| A0 Install (`install.sh`, `install.ps1`) | `~/agent-zero/<container-name>/usr`, override `--data-dir` ([`install.sh:1630`](https://github.com/agent0ai/a0-install/blob/c89b4026e9f16f53389e75537783411fefdd53f1/install.sh#L1630),[`1650-1652`](https://github.com/agent0ai/a0-install/blob/c89b4026e9f16f53389e75537783411fefdd53f1/install.sh#L1650-L1652),[`1830`](https://github.com/agent0ai/a0-install/blob/c89b4026e9f16f53389e75537783411fefdd53f1/install.sh#L1830); [`install.ps1:30`](https://github.com/agent0ai/a0-install/blob/c89b4026e9f16f53389e75537783411fefdd53f1/install.ps1#L30),[`1856`](https://github.com/agent0ai/a0-install/blob/c89b4026e9f16f53389e75537783411fefdd53f1/install.ps1#L1856),[`1874`](https://github.com/agent0ai/a0-install/blob/c89b4026e9f16f53389e75537783411fefdd53f1/install.ps1#L1874)) |
| A0 Launcher, default "host directory" mode | `~/agent-zero/<instance>[-N]/usr` ([`state_store.js:144-149`](https://github.com/agent0ai/a0-launcher/blob/b0333d80b5abf38d8481f55b667b0cf23d805bbb/shell/docker_manager/state_store.js#L144-L149), [`index.js:890-899`](https://github.com/agent0ai/a0-launcher/blob/b0333d80b5abf38d8481f55b667b0cf23d805bbb/shell/docker_manager/index.js#L890-L899)) |
| A0 Launcher, "named volume" mode | Docker volume `a0-launcher-<slug>-usr` ([`index.js:948-951`](https://github.com/agent0ai/a0-launcher/blob/b0333d80b5abf38d8481f55b667b0cf23d805bbb/shell/docker_manager/index.js#L948-L951)) |
| README `docker run` | Docker volume `a0_usr` ([`README.md:92`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/README.md#L92)) |
| `docker/run/docker-compose.yml` | `./agent-zero` beside the compose file, mounted as all of `/a0` ([`docker-compose.yml:5-6`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/docker/run/docker-compose.yml#L5-L6)) |
| Native ("development") run | the git clone, anywhere; the docs example is `~/Desktop/agent-zero` ([`docs/setup/dev-setup.md:34-37`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/docs/setup/dev-setup.md#L34-L37)); native means not `--dockerized` ([`helpers/runtime.py:59-64`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/runtime.py#L59-L64)) |

Named volumes live under the Docker data root (or inside the Docker Desktop
VM), outside any home, and are not reachable by a home-relative catalog;
since collector 1.5.0 the `DOCKER_VOLUMES` table collects `*a0_usr` and
`a0-launcher-*-usr` volumes with usr-relative exclusions and secret globs. Only
the native run has `usr/` and `tmp/` beside the source, a `.venv` or
`.conda`, and a legacy root `.env`.

**Contents of `usr/`:**

- `chats/<ctxid>/chat.json`, one per chat or scheduled-task context, and
  `chats/<ctxid>/messages/<n>.txt` for tool results of 500 characters or
  more ([`helpers/persist_chat.py:17-19`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/persist_chat.py#L17-L19),[`47-48`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/persist_chat.py#L47-L48),
  [`extensions/python/hist_add_tool_result/_90_save_tool_call_file.py:23-40`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/extensions/python/hist_add_tool_result/_90_save_tool_call_file.py#L23-L40)).
- `settings.json` ([`helpers/settings.py:182`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/settings.py#L182)), `.env`
  ([`helpers/dotenv.py:17-18`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/dotenv.py#L17-L18)), `secrets.env`
  ([`helpers/secrets.py:19`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/secrets.py#L19)).
- `memory/<subdir>/`: LangChain FAISS store, `index.faiss`, `index.pkl`
  (pickled docstore holding the memory text), `embedding.json`,
  `knowledge_import.json` ([`plugins/_memory/helpers/memory.py:180`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/plugins/_memory/helpers/memory.py#L180),[`197`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/plugins/_memory/helpers/memory.py#L197),[`269`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/plugins/_memory/helpers/memory.py#L269),[`550`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/plugins/_memory/helpers/memory.py#L550),[`666-673`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/plugins/_memory/helpers/memory.py#L666-L673)).
- `knowledge/` user knowledge files ([`memory.py:676-689`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/plugins/_memory/helpers/memory.py#L676-L689)).
- `projects/<name>/` with metadata in `.a0proj/`: `project.json`,
  `mcp_servers.json`, `instructions/`, `knowledge/`, `skills/`, `memory/`,
  `secrets.env`, `variables.env`
  ([`helpers/projects.py:11-17`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/projects.py#L11-L17),[`77-86`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/projects.py#L77-L86),[`672-684`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/projects.py#L672-L684); [`secrets.py:554`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/secrets.py#L554)).
- `workdir/`, the agent's default working directory
  ([`settings.py:597`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/settings.py#L597)).
- `scheduler/tasks.json` ([`helpers/task_scheduler.py:29`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/task_scheduler.py#L29),[`521`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/task_scheduler.py#L521)).
- `agents/`, `skills/`, `plugins/` user extensions
  ([`helpers/subagents.py:12`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/subagents.py#L12), [`helpers/skills.py:91`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/skills.py#L91)).
- `uploads/`, `upload/`, `downloads/`, `email/`
  ([`helpers/migration.py:24-31`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/migration.py#L24-L31)).
- `.time_travel/workspaces/`: shadow git history of `usr` workspaces
  ([`plugins/_time_travel/helpers/time_travel.py:23-24`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/plugins/_time_travel/helpers/time_travel.py#L23-L24)).

Older releases kept chats, scheduler, uploads, settings and secrets under
`tmp/`, memory under `memory/` and the `.env` at the install root; startup
moves them into `usr/` ([`migration.py:24-38`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/migration.py#L24-L38),[`95-107`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/migration.py#L95-L107)), so an
image of an un-upgraded install may hold them in the old places.

**Host-side companions** (these are home-relative):

- A0 CLI connector: `~/.agent-zero/.env` (instance URL, last chat id,
  remote-exec and computer-use flags) and `~/.agent-zero/session_cookies.json`
  ([`a0-connector config.py:8-10`](https://github.com/agent0ai/a0-connector/blob/76e834f20e50f6e47954c89ee39dd4c5b50d81b7/src/agent_zero_cli/config.py#L8-L10),[`15-25`](https://github.com/agent0ai/a0-connector/blob/76e834f20e50f6e47954c89ee39dd4c5b50d81b7/src/agent_zero_cli/config.py#L15-L25)), same path on every OS. Its
  managed browser profiles are under `~/.local/share/a0/browser-profiles`,
  `~/Library/Application Support/A0/Browser Profiles` or
  `%LOCALAPPDATA%\A0\Browser Profiles` ([`host_browser_common.py:476-487`](https://github.com/agent0ai/a0-connector/blob/76e834f20e50f6e47954c89ee39dd4c5b50d81b7/src/agent_zero_cli/host_browser_common.py#L476-L487)).
- A0 Launcher: Electron `productName` "Agent Zero Launcher"
  ([`package.json:51`](https://github.com/agent0ai/a0-launcher/blob/b0333d80b5abf38d8481f55b667b0cf23d805bbb/package.json#L51)), so `userData` is the Electron default directory of
  that name; it holds `docker_manager/state.json` and `docker_manager/cache`
  ([`state_store.js:13-23`](https://github.com/agent0ai/a0-launcher/blob/b0333d80b5abf38d8481f55b667b0cf23d805bbb/shell/docker_manager/state_store.js#L13-L23)).

## 3. Credentials

- `usr/.env`: provider keys as `API_KEY_<PROVIDER>`, `AUTH_LOGIN`,
  `AUTH_PASSWORD`, `RFC_PASSWORD`, `ROOT_PASSWORD`; settings strip these
  before writing `settings.json`
  ([`settings.py:540-570`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/settings.py#L540-L570)).
- `usr/secrets.env` and `usr/projects/*/.a0proj/secrets.env`: user secrets
  the agent references as `§§secret(KEY)`
  ([`secrets.py:17-19`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/secrets.py#L17-L19),[`535-556`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/secrets.py#L535-L556)).
- `usr/settings.json` keeps `mcp_servers`, a JSON string of MCP server
  definitions that can carry headers or env keys
  ([`settings.py:93`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/settings.py#L93)); `mcp_server_token` is blanked
  ([`settings.py:553`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/settings.py#L553)).
- Legacy: root `.env`, `tmp/secrets.env`, `tmp/settings.json`
  ([`migration.py:36-38`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/migration.py#L36-L38)); the VPS guide still mounts a root `.env`
  ([`docs/setup/vps-deployment.md:176`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/docs/setup/vps-deployment.md#L176)).
- The desktop plugin keeps a profile with `.ssh/` and `.gnupg/` under
  `usr/plugins/_desktop/profiles/agent-zero-desktop/` (paths from a grep of
  string literals; writer not traced).
- Host side: `~/.agent-zero/session_cookies.json` (login cookies per host,
  [`config.py:123-146`](https://github.com/agent0ai/a0-connector/blob/76e834f20e50f6e47954c89ee39dd4c5b50d81b7/src/agent_zero_cli/config.py#L123-L146)); the launcher's `state.json` stores instance
  passwords encrypted with Electron `safeStorage`, i.e. the OS keychain
  ([`state_store.js:683-688`](https://github.com/agent0ai/a0-launcher/blob/b0333d80b5abf38d8481f55b667b0cf23d805bbb/shell/docker_manager/state_store.js#L683-L688),[`753-761`](https://github.com/agent0ai/a0-launcher/blob/b0333d80b5abf38d8481f55b667b0cf23d805bbb/shell/docker_manager/state_store.js#L753-L761)).

## 4. Exclusions

`tmp/memory/embeddings` is an embedding cache ([`memory.py:145-147`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/plugins/_memory/helpers/memory.py#L145-L147)),
`tmp/playwright` holds browser binaries
([`plugins/_browser/helpers/playwright.py:16`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/plugins/_browser/helpers/playwright.py#L16)), `usr/.time_travel` is shadow git.
For native clones: `.venv`, `.conda`, `.git`. Python environments inside
`usr/workdir/*/.venv` occur (the code references one). The connector's and
launcher's Chromium directories are caches and cookie stores.

## 5. Project-local files

Agent Zero "projects" are directories it owns under `usr/projects/<name>`
(git clones are made there, [`projects.py:121-151`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/projects.py#L121-L151)) with metadata in
`.a0proj/`; they are collected with `usr/`. Through the A0 CLI connector
the containerised agent reads and writes files and runs commands in the
host's current directory ([`acp.py:314`](https://github.com/agent0ai/a0-connector/blob/76e834f20e50f6e47954c89ee39dd4c5b50d81b7/src/agent_zero_cli/acp.py#L314),
[`session.py:119`](https://github.com/agent0ai/a0-connector/blob/76e834f20e50f6e47954c89ee39dd4c5b50d81b7/src/agent_zero_cli/session.py#L119)) but writes no Agent Zero state file there.

## 6. Where the project path is recorded

`usr/chats/<ctxid>/chat.json` key `data.project` holds the project name
([`projects.py:27`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/projects.py#L27),[`457`](https://github.com/agent0ai/agent-zero/blob/e3051fb584b1a36be2b0a0c90606f1c2c2d356ec/helpers/projects.py#L457)); the path is `usr/projects/<name>`. No host
repository paths are recorded, so there is nothing for `discover_projects`.

## 7. Confidence

High: every path under the install directory and its `usr/` layout
(constants), the installer and launcher defaults, the connector files. Medium:
the Electron `userData` paths for the launcher (Electron default from
`productName`, no `setPath` found); `Desktop/agent-zero`, which is only the
docs example; whether `*agent-zero*` over-matches in real homes. Not
determined: where native installs are cloned in practice (the catalog cannot
find a clone outside the two listed paths, and a named Docker volume is never
under a home; both need a manual collection, or a separate issue for
collecting Docker volumes); the desktop plugin's credential files beyond the
literal paths found; whether plugin state such as
`usr/plugins/_telegram_integration/state.json` holds bot tokens.
