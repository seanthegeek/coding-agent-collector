# Catalog evidence

One document per catalog agent, named after the agent as it appears in
`collect-agent-artifacts.sh --list`, recording where that agent stores state
on each OS, which files are credentials, which subtrees are large or
worthless, which files it writes inside projects, and where it records the
project path, ending with the confidence in each finding. These documents
are the evidence behind the `CATALOG`, `PROJECT_CATALOG`, `EXCLUDES`,
`SECRET_GLOBS` and `DOCKER_VOLUMES` tables; the index table below summarises the evidence
level. How transcripts are encoded is the analyzer's concern and lives in
`analyzer/research/`.

Evidence levels, best first: source code at a named commit with file and
line, where each citation links to that line at that commit so the link
stays correct after the file changes upstream; the shipped package or binary (`npm pack`, extracted bundles, binary
strings); official documentation; vendor forums and issue trackers; published
write-ups. Each document says which level each claim rests on. Where a
document mentions `scratchpad/...`, that is the research session's working
directory, kept only for the duration of the research; the cited sources are
the repositories, package versions and URLs named beside it.

`tools/check_research_links.py` (at the repository root) checks every
GitHub citation in these documents and in `analyzer/research/`. For each
link it checks that the file exists at the cited commit and that the cited
line range lies inside it. It fetches each file from
`raw.githubusercontent.com`, or uses local checkouts with `--repos DIR`
(each named after its repository, with `HEAD` at the cited commit). Pass
file names to check only those. It exits `1` when any link fails.

| Agent | Document | Evidence | Notes |
| --- | --- | --- | --- |
| `agent-zero` | [agent-zero.md](agent-zero.md) | source (agent-zero, a0-install, a0-launcher, a0-connector) | state under the install dir `~/agent-zero/<instance>/usr`, not a dot dir; named Docker volumes `*a0_usr` and `a0-launcher-*-usr` collected since 1.5.0 |
| `aider` | [aider.md](aider.md) | source | history files live in the repository, home copies only as a fallback |
| `amp` | [amp.md](amp.md) | shipped binary strings, docs | threads are server-side; XDG dirs on every OS |
| `antigravity` | [antigravity.md](antigravity.md) | binary strings, real install, docs | CLI under `.gemini/antigravity-cli`; IDE now `.gemini/antigravity-ide` and `Antigravity IDE` app dirs |
| `augment` | [augment.md](augment.md) | shipped bundle, docs | `~/.augment` on every OS |
| `autogen-studio` | [autogen-studio.md](autogen-studio.md) | source | `~/.autogenstudio` on every OS; run history and model client API keys in one SQLite database |
| `camel-ai` | [camel-ai.md](camel-ai.md) | source | `~/.camel` is shared with Apache Camel JBang, so only CAMEL's Gmail token and skills dirs are collected |
| `chatgpt-desktop` | [chatgpt-desktop.md](chatgpt-desktop.md) | write-ups and press only | conversations encrypted with a Keychain key |
| `claude-code` | [claude-code.md](claude-code.md) | shipped bundle, docs, real install | `CLAUDE_CONFIG_DIR`; several credential files beyond `.credentials.json` |
| `claude-desktop` | [claude-desktop.md](claude-desktop.md) | official docs, GitHub issues | encrypted token cache in `config.json`; local-agent sessions |
| `cline` | [cline.md](cline.md) | source | `~/.cline/data` shared by VS Code, CLI and JetBrains |
| `codex-cli` | [codex-cli.md](codex-cli.md) | source, real install | rollouts may be zstd-compressed |
| `cody` | [cody.md](cody.md) | source (frozen public snapshot, August 2025) | chat history and token are rows in `state.vscdb`; the nested entry claims only the symf index |
| `continue` | [continue.md](continue.md) | source | `~/.continue` only |
| `copilot` | [copilot.md](copilot.md) | source (vendored language server) | editor OAuth store `github-copilot/apps.json` |
| `copilot-cli` | [copilot-cli.md](copilot-cli.md) | shipped bundle, docs, real install | migrates XDG state and config dirs into `~/.copilot` |
| `crewai` | [crewai.md](crewai.md) | source, appdirs source | run database in a data dir named after the project folder, collected by file name; opt-in memory stores beside it are not |
| `crush` | [crush.md](crush.md) | source | sessions only in each project's `.crush/crush.db` |
| `cursor` | [cursor.md](cursor.md) | shipped Agent CLI bundle, docs, forum, write-ups | no secret globs today; `auth.json` and `mcp-auth.json` exist |
| `dify` | [dify.md](dify.md) | source | server state in bind mounts beside its compose file (manual step); agent sandbox named volumes and `difyctl` config collected |
| `factory-droid` | [factory-droid.md](factory-droid.md) | shipped binary strings, docs | `.factory/cache` holds the session index |
| `flowise` | [flowise.md](flowise.md) | source | `~/.flowise` on every OS; `encryption.key` decrypts the credentials in `database.sqlite` |
| `gemini-cli` | [gemini-cli.md](gemini-cli.md) | source | slug project dirs; OAuth moved to keyring with encrypted file fallback |
| `goose` | [goose.md](goose.md) | source, crate sources | XDG on macOS; token caches under the config dir |
| `hermes` | [hermes.md](hermes.md) | source | `~/.hermes` or `AppData/Local/hermes`; profiles are full homes; installer checkout `.env` kept |
| `kilo-code` | [kilo-code.md](kilo-code.md) | source | OpenCode fork; `kilo.db` embeds tokens |
| `kiro` | [kiro.md](kiro.md) | Amazon Q source, Kiro CLI binary strings, docs, issues | `.kiro/powers` holds MCP configuration, not just binaries |
| `langflow` | [langflow.md](langflow.md) | source, platformdirs source; Desktop from docs only | config dir is the platformdirs cache dir; the OSS `langflow.db` is in site-packages (manual step); `langflow-data` volume |
| `letta` | [letta.md](letta.md) | source (Letta Code; retired V1 server) | `.letta/settings.json` secret glob also flags project settings |
| `little-coder` | [little-coder.md](little-coder.md) | source (little-coder, pi v0.83.0) | launcher for pi; sessions in `~/.pi/agent`, prompt history a nested entry |
| `local-deep-research` | [local-deep-research.md](local-deep-research.md) | source, platformdirs source | history in a SQLCipher database keyed by the login password; no analyzer document |
| `metagpt` | [metagpt.md](metagpt.md) | source | only `~/.metagpt/config2.yaml` (API key) under the home; workspace is relative to the clone or working directory |
| `muse-code` | [muse-code.md](muse-code.md) | shipped binary strings (Linux and Windows builds), launcher and installer scripts, real install (Linux) | closed source; XDG dirs under the home on every OS; launcher state in `~/.local/bin` or `AppData/Local/Programs/muse` |
| `n8n` | [n8n.md](n8n.md) | source | `~/.n8n` on every OS; computer-use gateway log records every tool call; `n8n_data` and `n8n-data` volumes |
| `nanobot` | [nanobot.md](nanobot.md) | source | `~/.nanobot-<name>` instances; workspace path in `.workspace` markers |
| `ollama` | [ollama.md](ollama.md) | source, real install | desktop app chat database on macOS and Windows; model manifests collected, blobs excluded; `ollama launch chatgpt` writes into `~/.codex` |
| `open-interpreter` | [open-interpreter.md](open-interpreter.md) | source, 0.4.3 sdist | now a Codex CLI fork with the Codex layout under `~/.openinterpreter`; the legacy Python tool's platformdirs `open-interpreter` and older `Open Interpreter*` dirs collected since 1.10.0 |
| `openclaw` | [openclaw.md](openclaw.md) | source | formerly Clawdbot and Moltbot; `~/.clawdbot` may be a symlink; JSON5 config |
| `opencode` | [opencode.md](opencode.md) | source, crate sources | XDG on every OS; binaries moved to `.cache/opencode/bin` |
| `openhands` | [openhands.md](openhands.md) | source (OpenHands, software-agent-sdk, OpenHands-CLI) | `agent-canvas/workspaces` excluded; Docker conversations record container paths |
| `pearai` | [pearai.md](pearai.md) | source (pearai-app, pearai-submodule, PearAI-Roo-Code) | VS Code fork; `~/.pearai` is also its Continue fork home |
| `pi` | [pi.md](pi.md) | source | same path on every OS; shared with little-coder |
| `pydantic-clai` | [pydantic-clai.md](pydantic-clai.md) | source, PyPI wheel | `clai` history and the CLAI 2.0 coding agent's `sessions.db`; `/resume` copies Claude Code and Codex sessions in |
| `qwen-code` | [qwen-code.md](qwen-code.md) | source | second root `QWEN_RUNTIME_DIR` |
| `roo-code` | [roo-code.md](roo-code.md) | source | platform-branched MCP clone dirs |
| `shared` | [shared.md](shared.md) | derived from the per-agent documents | cross-agent instruction and skill dirs |
| `shellgpt` | [shellgpt.md](shellgpt.md) | source | chat history in the system temp dir, collected only on Windows |
| `tabby` | [tabby.md](tabby.md) | source, JetBrains docs | self-hosted server; Docker `TABBY_ROOT=/data` reached only through a named volume matching `*tabby*` |
| `twinny` | [twinny.md](twinny.md) | source | chats in `state.vscdb`; project root inferred from the embeddings manifest |
| `vscode` | [vscode.md](vscode.md) | source (vscode, vscode-copilot-chat) | remote server data dirs hold Copilot Chat state on WSL and SSH hosts |
| `windsurf` | [windsurf.md](windsurf.md) | official docs, community write-ups | rebrand to Devin in progress; new `.windsurf/transcripts` |
| `zed` | [zed.md](zed.md) | source, crate sources | Flatpak install paths not covered |

Collector version 1.3.0 (issue 24, commit 88678a0) applied the catalog
lines these documents proposed. Each document originally ended with a review
of the catalog lines current at the time and the lines to add; those
sections described a catalog that has since moved on and were removed, so
the tables in the scripts are the record of what was adopted and that
commit's history is the record of what was considered.

Collector version 1.4.0 added fifteen agents from the October 2026 backlog
(`agent-zero` to `twinny` above, among them agents that are not coding
agents, such as `hermes`, `openclaw`, `nanobot` and `local-deep-research`)
in the same way: each document ended with a catalog proposal, which was
applied and then removed.

Collector version 1.10.0 (issue #64) swept sixteen agent frameworks,
framework studios and self-hosted agent platforms for default per-user
paths. The sweep itself, with the evidence for every framework that got no
catalog line (the AutoGen libraries, Microsoft Agent Framework, Semantic
Kernel, TaskWeaver, LangGraph, the Pydantic AI library, Logfire, Atomic
Agents and IntentKit), is one document,
[frameworks.md](frameworks.md), which is not an agent document and so has
no row in the table. Each framework that got a catalog agent
(`autogen-studio`, `camel-ai`, `crewai`, `dify`, `flowise`, `langflow`,
`metagpt`, `n8n`, `pydantic-clai`) has its own document like any other
agent, and the legacy Open Interpreter paths were added to
[open-interpreter.md](open-interpreter.md).

Findings that cut across agents, from the October 2026 round:

- Remote development hosts matter. `.vscode-server*/data/User`,
  `.cursor-server/data/User` and the Windsurf and Kiro equivalents hold the
  same chat and extension state as the desktop `User` directory, on the WSL
  or SSH host rather than the workstation. All are in the catalog since
  1.3.0.
- Several exclusions swallowed evidence: `.factory/cache` (session index),
  `.kiro/powers` (skills and MCP configuration) and `.kilocode/worktrees`
  (wrong path) were narrowed or corrected in 1.3.0;
  `.local/share/goose/apps` (agent-written output) is not excluded.
- Credentials are moving into OS keyrings with encrypted file fallbacks
  (Gemini CLI, Claude Code, Amp, Factory Droid), so the plaintext files in the
  catalog are increasingly legacy. The fallbacks still appear on headless
  hosts and in WSL, which is where collections usually run.
- Nearly every tool now has a per-project ignore file and a plugin or skill
  marketplace clone directory; the ignore files are project entries and the
  clone directories are exclusions since 1.3.0.
