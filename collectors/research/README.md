# Catalog evidence

One document per catalog agent, named after the agent as it appears in
`collect-agent-artifacts.sh --list`, recording where that agent stores state
on each OS, which files are credentials, which subtrees are large or
worthless, which files it writes inside projects, and where it records the
project path, ending with the confidence in each finding. These documents
are the evidence behind the `CATALOG`, `PROJECT_CATALOG`, `EXCLUDES` and
`SECRET_GLOBS` tables; the collectors README table summarises the evidence
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

| Agent | Document | Evidence | Notes |
| --- | --- | --- | --- |
| `agent-zero` | [agent-zero.md](agent-zero.md) | source (agent-zero, a0-install, a0-launcher, a0-connector) | state under the install dir `~/agent-zero/<instance>/usr`, not a dot dir; Docker volumes not covered |
| `aider` | [aider.md](aider.md) | source | history files live in the repository, home copies only as a fallback |
| `amp` | [amp.md](amp.md) | shipped binary strings, docs | threads are server-side; XDG dirs on every OS |
| `antigravity` | [antigravity.md](antigravity.md) | binary strings, real install, docs | CLI under `.gemini/antigravity-cli`; IDE now `.gemini/antigravity-ide` and `Antigravity IDE` app dirs |
| `augment` | [augment.md](augment.md) | shipped bundle, docs | `~/.augment` on every OS |
| `chatgpt-desktop` | [chatgpt-desktop.md](chatgpt-desktop.md) | write-ups and press only | conversations encrypted with a Keychain key |
| `claude-code` | [claude-code.md](claude-code.md) | shipped bundle, docs, real install | `CLAUDE_CONFIG_DIR`; several credential files beyond `.credentials.json` |
| `claude-desktop` | [claude-desktop.md](claude-desktop.md) | official docs, GitHub issues | encrypted token cache in `config.json`; local-agent sessions |
| `cline` | [cline.md](cline.md) | source | `~/.cline/data` shared by VS Code, CLI and JetBrains |
| `codex-cli` | [codex-cli.md](codex-cli.md) | source, real install | rollouts may be zstd-compressed |
| `cody` | [cody.md](cody.md) | source (frozen public snapshot, August 2025) | chat history and token are rows in `state.vscdb`; the nested entry claims only the symf index |
| `continue` | [continue.md](continue.md) | source | `~/.continue` only |
| `copilot` | [copilot.md](copilot.md) | source (vendored language server) | editor OAuth store `github-copilot/apps.json` |
| `copilot-cli` | [copilot-cli.md](copilot-cli.md) | shipped bundle, docs, real install | migrates XDG state and config dirs into `~/.copilot` |
| `crush` | [crush.md](crush.md) | source | sessions only in each project's `.crush/crush.db` |
| `cursor` | [cursor.md](cursor.md) | shipped Agent CLI bundle, docs, forum, write-ups | no secret globs today; `auth.json` and `mcp-auth.json` exist |
| `factory-droid` | [factory-droid.md](factory-droid.md) | shipped binary strings, docs | `.factory/cache` holds the session index |
| `gemini-cli` | [gemini-cli.md](gemini-cli.md) | source | slug project dirs; OAuth moved to keyring with encrypted file fallback |
| `goose` | [goose.md](goose.md) | source, crate sources | XDG on macOS; token caches under the config dir |
| `hermes` | [hermes.md](hermes.md) | source | `~/.hermes` or `AppData/Local/hermes`; profiles are full homes; installer checkout `.env` kept |
| `kilo-code` | [kilo-code.md](kilo-code.md) | source | OpenCode fork; `kilo.db` embeds tokens |
| `kiro` | [kiro.md](kiro.md) | Amazon Q source, Kiro CLI binary strings, docs, issues | `.kiro/powers` holds MCP configuration, not just binaries |
| `letta` | [letta.md](letta.md) | source (Letta Code; retired V1 server) | `.letta/settings.json` secret glob also flags project settings |
| `little-coder` | [little-coder.md](little-coder.md) | source (little-coder, pi v0.83.0) | launcher for pi; sessions in `~/.pi/agent`, prompt history a nested entry |
| `local-deep-research` | [local-deep-research.md](local-deep-research.md) | source, platformdirs source | history in a SQLCipher database keyed by the login password; no analyzer document |
| `nanobot` | [nanobot.md](nanobot.md) | source | `~/.nanobot-<name>` instances; workspace path in `.workspace` markers |
| `ollama` | [ollama.md](ollama.md) | source, real install | desktop app chat database on macOS and Windows |
| `open-interpreter` | [open-interpreter.md](open-interpreter.md) | source | now a Codex CLI fork with the Codex layout under `~/.openinterpreter` |
| `openclaw` | [openclaw.md](openclaw.md) | source | formerly Clawdbot and Moltbot; `~/.clawdbot` may be a symlink; JSON5 config |
| `opencode` | [opencode.md](opencode.md) | source, crate sources | XDG on every OS; binaries moved to `.cache/opencode/bin` |
| `openhands` | [openhands.md](openhands.md) | source (OpenHands, software-agent-sdk, OpenHands-CLI) | `agent-canvas/workspaces` excluded; Docker conversations record container paths |
| `pearai` | [pearai.md](pearai.md) | source (pearai-app, pearai-submodule, PearAI-Roo-Code) | VS Code fork; `~/.pearai` is also its Continue fork home |
| `pi` | [pi.md](pi.md) | source | same path on every OS; shared with little-coder |
| `qwen-code` | [qwen-code.md](qwen-code.md) | source | second root `QWEN_RUNTIME_DIR` |
| `roo-code` | [roo-code.md](roo-code.md) | source | platform-branched MCP clone dirs |
| `shared` | [shared.md](shared.md) | derived from the per-agent documents | cross-agent instruction and skill dirs, `.env` |
| `shell-history` | [shell-history.md](shell-history.md) | shell documentation | formats and which carry timestamps |
| `shellgpt` | [shellgpt.md](shellgpt.md) | source | chat history in the system temp dir, collected only on Windows |
| `tabby` | [tabby.md](tabby.md) | source, JetBrains docs | self-hosted server; Docker `TABBY_ROOT=/data` not covered |
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
