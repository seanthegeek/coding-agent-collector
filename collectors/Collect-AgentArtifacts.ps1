<#
.SYNOPSIS
  Forensic collector for AI coding agent artifacts on Windows.

.DESCRIPTION
  Windows counterpart of collect-agent-artifacts.sh. Collects the on-disk state
  of AI coding agents (Claude Code, Gemini CLI, Antigravity, Codex CLI, Copilot
  CLI, Cursor, Windsurf, Continue, Aider, Ollama, ...) for every user profile on
  a host, from Docker and Podman named volumes it can reach on disk, into a
  single tar.gz (via the built-in tar.exe on Windows 10 1803+) or zip, with a JSONL
  manifest. Same catalog, manifest schema and archive layout as the sh script.
  Host state (processes, users, network, shell histories) is left to the EDR
  it supplements.

  Windows PowerShell 5.1 compatible. No modules, no prompts, nothing from stdin.
  Run as:  powershell.exe -ExecutionPolicy Bypass -File Collect-AgentArtifacts.ps1 -OutputDir C:\ir

.PARAMETER OutputDir
  Directory for the archive (default: current directory).
.PARAMETER Root
  Alternate root such as a mounted disk image (image mode).
.PARAMETER Users
  Comma-separated profile names to collect (default: all).
.PARAMETER Project
  Extra project directory to collect (repeatable).
.PARAMETER Full
  Disable default size exclusions.
.PARAMETER NoSecrets
  Skip credential files instead of collecting them.
.PARAMETER NoProjects
  Skip project-level artifact discovery.
.PARAMETER NoDocker
  Skip Docker and Podman volume enumeration. Docker Desktop keeps Linux volumes
  inside a WSL virtual disk that this script cannot reach; it only notes that.
.PARAMETER MaxFileSizeMB
  Skip files larger than this (default 256, 0 = none).
.PARAMETER KeepStaging
  Keep the staging directory after archiving.
.PARAMETER Inventory
  Write nothing: walk the catalog with file metadata only and print one JSON
  line per user and agent found (file count, bytes, first and last
  modification time) to stdout. -OutputDir is ignored.
.PARAMETER List
  Print the artifact catalog and exit.
.PARAMETER Quiet
  Only print the final summary.
.PARAMETER Version
  Print version and exit.

.NOTES
  Copyright 2026 Sean Whalen
  SPDX-License-Identifier: Apache-2.0
  Exit codes: 0 archive written (per-file errors are in the manifest), or,
                with -Inventory, the walk ran,
              1 usage error, 2 fatal.
#>
[CmdletBinding()]
param(
  [Alias('o')][string]$OutputDir = '.',
  [Alias('r')][string]$Root = '',
  [Alias('u')][string]$Users = '',
  [Alias('p')][string[]]$Project = @(),
  [switch]$Full,
  [switch]$NoSecrets,
  [switch]$NoProjects,
  [switch]$NoDocker,
  [int]$MaxFileSizeMB = 256,
  [Alias('k')][switch]$KeepStaging,
  [switch]$Inventory,
  [switch]$List,
  [Alias('q')][switch]$Quiet,
  [switch]$Version
)

Set-StrictMode -Version 2
$ErrorActionPreference = 'Continue'
$ToolVersion = '1.7.0'
$TOOL = 'collect-agent-artifacts'

# ---------------------------------------------------------------------------
# Artifact catalog. Identical to the tables in collect-agent-artifacts.sh;
# tests/catalog-sync.sh fails if they drift. agent|glob relative to each home.
# ---------------------------------------------------------------------------
$CATALOG = @'
# Anthropic
claude-code|.claude
claude-code|.claude.json*
# Claude Code config homes moved with CLAUDE_CONFIG_DIR (~/.claude-work):
# anchored on Claude-only names, never a bare .claude-*
claude-code|.claude-*/projects
claude-code|.claude-*/file-history
claude-code|.claude-*/history.jsonl
claude-code|.claude-*/.claude.json*
claude-code|.claude-*/.credentials.json
claude-code|.claude-*/hfi-auth.json
claude-code|.claude-*/.session_ingress_token
claude-code|.claude-*/remote/.oauth_token
claude-code|.claude-*/remote/.api_key
claude-code|.local/share/claude
claude-desktop|Library/Application Support/Claude
claude-desktop|Library/Application Support/Claude-3p
claude-desktop|Library/Logs/Claude
claude-desktop|Library/Logs/Claude-3p
claude-desktop|.config/Claude
claude-desktop|.config/Claude-3p
claude-desktop|AppData/Roaming/Claude
claude-desktop|AppData/Roaming/Claude-3p
claude-desktop|AppData/Local/Claude-3p
claude-desktop|Claude
claude-desktop|Documents/Claude
# Google (antigravity-cli lives inside ~/.gemini; the nested entry claims it)
gemini-cli|.gemini
gemini-cli|.cache/.gemini
antigravity|.gemini/antigravity-cli
antigravity|.gemini/antigravity-ide
antigravity|.gemini/antigravity
antigravity|.gemini/antigravity-backup
antigravity|.gemini/config
antigravity|.antigravity
antigravity|.cache/antigravity
antigravity|.config/Antigravity/User
antigravity|.config/Antigravity/logs
antigravity|Library/Application Support/Antigravity/User
antigravity|Library/Application Support/Antigravity/logs
antigravity|AppData/Roaming/Antigravity/User
antigravity|AppData/Roaming/Antigravity/logs
antigravity|.config/Antigravity IDE/User
antigravity|.config/Antigravity IDE/logs
antigravity|Library/Application Support/Antigravity IDE/User
antigravity|Library/Application Support/Antigravity IDE/logs
antigravity|AppData/Roaming/Antigravity IDE/User
antigravity|AppData/Roaming/Antigravity IDE/logs
# OpenAI
codex-cli|.codex
codex-cli|Library/Application Support/com.openai.codex
chatgpt-desktop|Library/Application Support/com.openai.chat
chatgpt-desktop|AppData/Local/Packages/OpenAI.ChatGPT-Desktop_*/LocalCache/Roaming/ChatGPT
chatgpt-desktop|AppData/Local/Packages/OpenAI.ChatGPT-Desktop_*/LocalState
# GitHub Copilot (CLI, and the OAuth token store used by Copilot plugins)
copilot-cli|.copilot
copilot-cli|.config/.copilot
copilot-cli|.local/state/.copilot
copilot-cli|.cache/copilot
copilot-cli|Library/Caches/copilot
copilot-cli|AppData/Local/copilot
copilot|.config/github-copilot
copilot|AppData/Local/github-copilot
# Cursor
cursor|.cursor
cursor|.config/cursor
cursor|AppData/Roaming/Cursor/auth.json
cursor|.cursor-server/data/User
cursor|Library/Application Support/Cursor/User
cursor|Library/Application Support/Cursor/logs
cursor|.config/Cursor/User
cursor|.config/Cursor/logs
cursor|AppData/Roaming/Cursor/User
cursor|AppData/Roaming/Cursor/logs
# VS Code and VSCodium: globalStorage holds Copilot Chat, Cline, Roo, Kilo, Continue, Augment state
vscode|.vscode*/extensions/extensions.json
vscode|Library/Application Support/Code*/User
vscode|Library/Application Support/Code*/logs
vscode|.config/Code*/User
vscode|.config/Code*/logs
vscode|AppData/Roaming/Code*/User
vscode|AppData/Roaming/Code*/logs
vscode|Library/Application Support/VSCodium*/User
vscode|Library/Application Support/VSCodium*/logs
vscode|.config/VSCodium*/User
vscode|.config/VSCodium*/logs
vscode|AppData/Roaming/VSCodium*/User
vscode|AppData/Roaming/VSCodium*/logs
vscode|Library/Application Support/Positron/User
vscode|.config/Positron/User
vscode|AppData/Roaming/Positron/User
vscode|Library/Application Support/Trae*/User
vscode|.config/Trae*/User
vscode|AppData/Roaming/Trae*/User
vscode|.vscode*/argv.json
vscode|.vscode*/cli/token*.json
# Remote development servers (WSL, SSH, tunnels) keep the same User layout on the remote host
vscode|.vscode-server*/data/User
vscode|.vscode-server*/data/logs
vscode|.vscodium-server*/data/User
vscode|.positron-server/data/User
# VS Code family extension state. Each editor User directory is collected
# above; these nested entries claim the agent extension globalStorage from
# that walk so Cline, Roo, Kilo, Continue, Cody and Twinny files are
# attributed to them.
cline|.config/*/User/globalStorage/saoudrizwan.claude-dev
cline|Library/Application Support/*/User/globalStorage/saoudrizwan.claude-dev
cline|AppData/Roaming/*/User/globalStorage/saoudrizwan.claude-dev
roo-code|.config/*/User/globalStorage/rooveterinaryinc.roo-cline
roo-code|Library/Application Support/*/User/globalStorage/rooveterinaryinc.roo-cline
roo-code|AppData/Roaming/*/User/globalStorage/rooveterinaryinc.roo-cline
kilo-code|.config/*/User/globalStorage/kilocode.kilo-code
kilo-code|Library/Application Support/*/User/globalStorage/kilocode.kilo-code
kilo-code|AppData/Roaming/*/User/globalStorage/kilocode.kilo-code
continue|.config/*/User/globalStorage/continue.continue
continue|Library/Application Support/*/User/globalStorage/continue.continue
continue|AppData/Roaming/*/User/globalStorage/continue.continue
cody|.config/*/User/globalStorage/sourcegraph.cody-ai
cody|Library/Application Support/*/User/globalStorage/sourcegraph.cody-ai
cody|AppData/Roaming/*/User/globalStorage/sourcegraph.cody-ai
twinny|.config/*/User/globalStorage/rjmacarthy.twinny
twinny|Library/Application Support/*/User/globalStorage/rjmacarthy.twinny
twinny|AppData/Roaming/*/User/globalStorage/rjmacarthy.twinny
cline|.*-server*/data/User/globalStorage/saoudrizwan.claude-dev
roo-code|.*-server*/data/User/globalStorage/rooveterinaryinc.roo-cline
kilo-code|.*-server*/data/User/globalStorage/kilocode.kilo-code
continue|.*-server*/data/User/globalStorage/continue.continue
cody|.*-server*/data/User/globalStorage/sourcegraph.cody-ai
twinny|.*-server*/data/User/globalStorage/rjmacarthy.twinny
# Windsurf (rebranding to Devin)
windsurf|.codeium
windsurf|.windsurf
windsurf|.devin
windsurf|.config/devin
windsurf|.local/share/devin
windsurf|AppData/Roaming/devin
windsurf|Library/Application Support/Windsurf/User
windsurf|Library/Application Support/Windsurf/logs
windsurf|.config/Windsurf/User
windsurf|.config/Windsurf/logs
windsurf|AppData/Roaming/Windsurf/User
windsurf|AppData/Roaming/Windsurf/logs
windsurf|Library/Application Support/Devin/User
windsurf|Library/Application Support/Devin/logs
windsurf|.config/Devin/User
windsurf|.config/Devin/logs
windsurf|AppData/Roaming/Devin/User
windsurf|AppData/Roaming/Devin/logs
windsurf|.windsurf-server/data/User
windsurf|.devin-server/data/User
# Cline, Roo Code, Kilo Code
cline|.cline
cline|Documents/Cline
cline|Cline/Rules
roo-code|.roo
roo-code|.roo-code
roo-code|.vscode-mock
roo-code|.local/share/Roo-Code
roo-code|AppData/Roaming/Roo-Code
kilo-code|.kilo
kilo-code|.kilocode
kilo-code|.kilocodemodes
kilo-code|.config/kilo
kilo-code|.local/share/kilo
kilo-code|.local/state/kilo
# Continue
continue|.continue
# Aider (history files live in the repo; these are the home-level ones)
aider|.aider
aider|.aider.conf.yml
aider|.aider.model.settings.yml
aider|.aider.model.metadata.json
aider|.aider.chat.history.md
aider|.aider.input.history
aider|.aider.llm.history
# OpenCode (xdg-basedir: same paths on macOS and Windows)
opencode|.config/opencode
opencode|.opencode
opencode|.local/share/opencode
opencode|.local/state/opencode
# Crush (~/.config on every OS; sessions live in each project .crush/crush.db)
crush|.config/crush
crush|.local/share/crush
crush|AppData/Local/crush
crush|.crush
crush|.cache/crush
# Goose (XDG on macOS too; Electron app dir is separate)
goose|.config/goose
goose|.local/share/goose
goose|.local/state/goose
goose|.config/Goose
goose|Library/Application Support/Goose
goose|AppData/Roaming/Block/goose
goose|Library/Application Support/Block/goose
goose|AppData/Roaming/Goose
goose|.goose
# Zed (config in ~/.config/zed on macOS too; data under Library)
zed|.config/zed
zed|.local/share/zed
zed|Library/Application Support/Zed
zed|Library/Logs/Zed
zed|AppData/Roaming/Zed
zed|AppData/Local/Zed
zed|.var/app/dev.zed.Zed/config/zed
zed|.var/app/dev.zed.Zed/data/zed
zed|.var/app/dev.zed.ZedPreview/config/zed
zed|.var/app/dev.zed.ZedPreview/data/zed
zed|.var/app/dev.zed.ZedNightly/config/zed
zed|.var/app/dev.zed.ZedNightly/data/zed
# Qwen Code
qwen-code|.qwen
# Amp (data dir is ~/.local/share/amp on every OS; threads are server-side)
amp|.config/amp
amp|.local/share/amp
amp|.cache/amp/logs
amp|.cache/amp/terminal
amp|.amp
amp|AppData/Local/amp/logs
# Factory Droid
factory-droid|.factory
# Meta Muse Code (XDG ~/.config/muse and ~/.local/share/muse on every OS; launcher state in its install dir)
muse-code|.config/muse
muse-code|.local/share/muse
muse-code|.muse
muse-code|.local/bin/.muse-*
muse-code|AppData/Local/Programs/muse
muse-code|AppData/LocalLow/muse-shell-sandbox-*
# Augment (auggie CLI; the VS Code extension state is under the vscode entries)
augment|.augment
# Kiro (CLI, legacy Amazon Q CLI, and the Kiro IDE which is a VS Code fork)
kiro|.kiro
kiro|.kiro-server/data/User
kiro|.aws/amazonq
kiro|.aws/sso/cache
kiro|.local/share/kiro-cli
kiro|.local/share/amazon-q
kiro|Library/Application Support/kiro-cli
kiro|Library/Application Support/amazon-q
kiro|AppData/Local/kiro-cli
kiro|AppData/Local/amazon-q
kiro|.config/Kiro/User
kiro|.config/Kiro/logs
kiro|Library/Application Support/Kiro/User
kiro|Library/Application Support/Kiro/logs
kiro|AppData/Roaming/Kiro/User
kiro|AppData/Roaming/Kiro/logs
# PearAI (VS Code fork; ~/.pearai is both the editor extension dir and the Continue fork home)
pearai|.pearai
pearai|.config/PearAI/User
pearai|.config/PearAI/logs
pearai|.config/pearai/User
pearai|Library/Application Support/PearAI/User
pearai|Library/Application Support/PearAI/logs
pearai|AppData/Roaming/PearAI/User
pearai|AppData/Roaming/PearAI/logs
pearai|.pearai-server/data/User
# Sourcegraph Cody (VS Code chat history and token are rows in state.vscdb; JetBrains and agent state under Cody-nodejs)
cody|.vscode/cody.json
cody|.cody
cody|.local/share/Cody-nodejs
cody|.config/Cody-nodejs
cody|.local/state/Cody-nodejs
cody|Library/Application Support/Cody-nodejs
cody|Library/Preferences/Cody-nodejs
cody|Library/Logs/Cody-nodejs
cody|AppData/Local/Cody-nodejs
cody|AppData/Roaming/Cody-nodejs
# Twinny (chats are rows in state.vscdb; embeddings, node and server state under ~/.twinny)
twinny|.twinny
# Tabby (self-hosted server state, editor agent config, JetBrains plugin settings)
tabby|.tabby
tabby|.tabby-client
tabby|.config/JetBrains/*/options/intellij-tabby*.xml
tabby|Library/Application Support/JetBrains/*/options/intellij-tabby*.xml
tabby|AppData/Roaming/JetBrains/*/options/intellij-tabby*.xml
# Open Interpreter (a Codex CLI fork with the Codex layout under ~/.openinterpreter)
open-interpreter|.openinterpreter
# OpenHands (CLI and Agent Server under ~/.openhands; Agent Canvas desktop app)
openhands|.openhands
openhands|Library/Application Support/OpenHands Agent Canvas
openhands|.config/OpenHands Agent Canvas
openhands|AppData/Roaming/OpenHands Agent Canvas
# pi (same path on every OS); little-coder runs pi and its prompt history is a nested entry
pi|.pi
little-coder|.little-coder
little-coder|.config/little-coder
little-coder|.cache/little-coder
little-coder|.pi/agent/little-coder-prompt-history.json
# Letta Code, and the retired Letta (MemGPT) server
letta|.letta
letta|.config/letta
letta|.memgpt
# Hermes Agent (Nous Research; AppData/Local/hermes on Windows, Electron app dir Hermes)
hermes|.hermes
hermes|.hermes_*
hermes|AppData/Local/hermes
hermes|AppData/Local/hermes_*
hermes|.config/Hermes
hermes|Library/Application Support/Hermes
hermes|AppData/Roaming/Hermes
# OpenClaw (formerly Clawdbot and Moltbot; profiles are ~/.openclaw-<profile>, ~/.clawdbot may be a symlink)
openclaw|.openclaw
openclaw|.openclaw-*
openclaw|.clawdbot
openclaw|.moltbot
openclaw|.config/openclaw
openclaw|Library/Application Support/OpenClaw
openclaw|Library/LaunchAgents/ai.openclaw.*
openclaw|.config/systemd/user/openclaw-*
openclaw|.config/systemd/user/clawdbot-*
# nanobot (instances are ~/.nanobot-<name>)
nanobot|.nanobot
nanobot|.nanobot-*
nanobot|Library/LaunchAgents/ai.nanobot.*
nanobot|.config/systemd/user/nanobot-*
# Agent Zero (state is under the install dir, not a dot dir: installer and launcher
# default ~/agent-zero/<instance>/usr, or a clone in ~/agent-zero or ~/Desktop/agent-zero)
agent-zero|agent-zero
agent-zero|Desktop/agent-zero
agent-zero|.agent-zero
agent-zero|.local/share/a0
agent-zero|Library/Application Support/A0
agent-zero|AppData/Local/A0
agent-zero|.config/Agent Zero Launcher
agent-zero|Library/Application Support/Agent Zero Launcher
agent-zero|AppData/Roaming/Agent Zero Launcher
# ShellGPT (~/.config on every OS; chats default to the temp dir, under the home only on Windows)
shellgpt|.config/shell_gpt
shellgpt|AppData/Local/Temp/chat_cache
shellgpt|AppData/Local/Temp/shell_gpt
# Local Deep Research (platformdirs data dir; history is in an encrypted per-user database)
local-deep-research|.local/share/local-deep-research
local-deep-research|Library/Application Support/local-deep-research
local-deep-research|AppData/Local/local-deep-research
local-deep-research|Documents/LocalDeepResearch
# Shared cross-agent directories (skills and instructions read by several agents)
shared|.agents
shared|.config/AGENTS.md
shared|.config/agents
# Ollama
ollama|.ollama
ollama|Library/Application Support/Ollama
ollama|AppData/Local/Ollama
'@

$PROJECT_CATALOG = @'
project|.claude
project|CLAUDE.md
project|CLAUDE.local.md
project|.mcp.json
project|AGENTS.md
project|AGENTS.override.md
project|AGENT.md
project|.agents
project|GEMINI.md
project|.gemini
project|.geminiignore
project|QWEN.md
project|.qwen
project|.qwenignore
project|.codex
project|.cursor
project|.cursorrules
project|.cursorignore
project|.cursorindexingignore
project|.windsurf
project|.windsurfrules
project|.windsurfignore
project|.codeiumignore
project|.devin
project|.devinignore
project|.antigravityignore
project|.clinerules
project|.clineignore
project|.cline
project|.roo
project|.roomodes
project|.rooignore
project|.roorules*
project|.rooprotected
project|.kilo
project|.kilocode
project|.kilocodemodes
project|.kilocodeignore
project|.kilocoderules
project|kilo.json*
project|.continue
project|.continuerc.json
project|.continueignore
project|.aider.chat.history.md
project|.aider.input.history
project|.aider.llm.history
project|.aider.conf.yml
project|.aider.model.settings.yml
project|.aider.model.metadata.json
project|.aiderignore
project|.opencode
project|opencode.json*
project|.crush
project|crush.json
project|.crush.json
project|crushrc
project|.crushrc
project|.crushignore
project|CRUSH.md
project|CRUSH.local.md
project|crush.md
project|crush.local.md
project|Crush.md
project|Crush.local.md
project|.goosehints
project|.goose
project|.zed
project|.rules
project|.github/copilot-instructions.md
project|.github/git-commit-instructions.md
project|.github/copilot
project|.github/instructions
project|.github/mcp.json
project|.github/hooks
project|.github/skills
project|.github/agents
project|.github/lsp.json
project|.vscode/mcp.json
project|.amp
project|.factory
project|.factory-plugin
project|.droid.yaml
project|.muse
project|.augment
project|.augment-guidelines
project|.augmentignore
project|.augment-plugin
project|.kiro
project|.kiroignore
project|.amazonq
project|AmazonQ.md
project|.pearairc.json
project|.pearaiignore
project|.pearai-agent
project|.pearai-agent-ignore
project|.pearai-agent-modes
project|.cody
project|.vscode/cody.json
project|.sourcegraph
project|.openinterpreter
project|.codewhale
project|.openhands
project|.pi
project|.pi/approved-plan.md
project|pi-session-*.html
project|.letta
project|.skills
project|.hermes.md
project|HERMES.md
project|.hermes
project|trajectory_samples.jsonl
project|failed_trajectories.jsonl
project|.openclaw
project|SOUL.md
project|IDENTITY.md
project|USER.md
project|TOOLS.md
project|BOOTSTRAP.md
project|MEMORY.md
project|.nanobot
project|HEARTBEAT.md
project|memory/MEMORY.md
project|memory/history.jsonl
project|memory/HISTORY.md
'@

$EXCLUDES = @'
.claude/cache
.claude/plugins/marketplaces
.claude/plugins/cache
.claude/plugins/*/node_modules
.claude/local/node_modules
.claude/image-cache
.claude/paste-cache
.claude/chrome
.claude/worktrees
.claude/checkpoints
.local/share/claude/versions
*/Claude*/Cache
*/Claude*/Code Cache
*/Claude*/GPUCache
*/Claude*/DawnGraphiteCache
*/Claude*/DawnWebGPUCache
*/Claude*/claude-code
*/Claude*/claude-code-vm
*/Claude*/vm_bundles
*/Claude*/sentry
.gemini/whisper_models
.gemini/bin
.gemini/tmp/bin
.gemini/extensions/*/node_modules
.gemini/extensions/*/.git
.gemini/cli-browser-profile
.gemini/antigravity-cli/bin
.gemini/antigravity*/brain/*/.system_generated/worktrees
.antigravity/extensions
AppData/Local/agy
.codex/packages
.codex/cache
.codex/.tmp
.codex/plugins/cache
.codex/skills/.system
.codex/worktrees
.codex/.sandbox
.codex/.sandbox-bin
.codex/tmp
.codex/visualizations
*/Roaming/ChatGPT/Cache
*/Roaming/ChatGPT/Code Cache
*/Roaming/ChatGPT/GPUCache
*/Roaming/ChatGPT/DawnGraphiteCache
*/Roaming/ChatGPT/DawnWebGPUCache
.copilot/pkg
.copilot/installed-plugins
.cache/copilot/pkg
Library/Caches/copilot/pkg
AppData/Local/copilot/pkg
.cursor/extensions
.cursor/worktrees
.cursor/plugins/marketplaces
.cursor-server/bin
.cursor-server/extensions
*/Cursor/User/globalStorage/state.vscdb.backup
.codeium/windsurf/implicit
.codeium/*/bin
.codeium/bin
.codeium/ws-browser*
.windsurf/extensions
.devin/extensions
AppData/Local/devin/bin
*/User/globalStorage/saoudrizwan.claude-dev/checkpoints
*/User/globalStorage/saoudrizwan.claude-dev/cache
*/User/globalStorage/rooveterinaryinc.roo-cline/checkpoints
*/User/globalStorage/rooveterinaryinc.roo-cline/tasks/*/checkpoints
*/User/globalStorage/rooveterinaryinc.roo-cline/cache
*/User/globalStorage/kilocode.kilo-code/checkpoints
*/User/globalStorage/kilocode.kilo-code/cache
*/User/globalStorage/ms-*
*/User/globalStorage/vscjava*
*/User/globalStorage/redhat*
*/User/globalStorage/eamodio*
*/User/globalStorage/golang*
*/User/globalStorage/rust-lang*
*/User/globalStorage/yzane.markdown-pdf
*/User/globalStorage/github.copilot-chat/logContextRecordings
*/User/globalStorage/github.copilot-chat/workspaceRecordings
*/User/workspaceStorage/*/GitHub.copilot-chat/codebase-external.sqlite*
*/User/workspaceStorage/*/ms-*
*/User/workspaceStorage/*/vscjava*
*/User/workspaceStorage/*/redhat*
*/User/workspaceStorage/*/rust-lang*
.cline/data/checkpoint-scratch
.cline/data/workspaces/chat
.cline/data/agent-plugins
.cline/plugins
.cline/worktrees
.vscode-mock/global-storage/tasks/*/checkpoints
.vscode-mock/global-storage/checkpoints
.roo/worktrees
.roo-code/mcp
.local/share/Roo-Code/MCP
AppData/Roaming/Roo-Code/MCP
.local/share/kilo/snapshot
.local/share/kilo/repos
.local/share/kilo/tool-output
.local/share/kilo/log
.local/share/kilo/worktree
.local/state/kilo/indexing
.local/share/kilo/state/indexing
.kilo/worktrees
.kilo/bin
.continue/index/lancedb
.continue/index/*.sqlite
.continue/.utils
.continue/node_modules
.continue/out
.continue/types
.continue/.diffs
.continue/.migrations
.continue/dev_data/devdata.sqlite
.aider/caches
.aider.tags.cache*
.local/share/opencode/bin
.local/share/opencode/snapshot
.local/share/opencode/worktree
.local/share/opencode/repos
.local/share/opencode/tool-output
.config/opencode/node_modules
.opencode/bin
.opencode/node_modules
.local/share/goose/models
.local/share/goose/model_catalog
.local/state/goose/codex
.config/goose/mcp-apps-cache
AppData/Roaming/Block/goose/data/models
AppData/Roaming/Block/goose/data/model_catalog
AppData/Roaming/Block/goose/data/codex
*/Goose/Cache
*/Goose/Code Cache
*/Goose/GPUCache
*/Goose/DawnGraphiteCache
*/Goose/DawnWebGPUCache
*/Goose/blob_storage
*/[Zz]ed/extensions
*/[Zz]ed/remote_extensions
*/[Zz]ed/node
*/[Zz]ed/languages
*/[Zz]ed/copilot
*/[Zz]ed/debug_adapters
*/[Zz]ed/external_agents
*/[Zz]ed/prettier
*/[Zz]ed/remote_servers
*/[Zz]ed/devcontainer
*/[Zz]ed/embeddings
*/[Zz]ed/server_state
*/[Zz]ed/hang_traces
*/[Zz]ed/build_timings
.qwen/updates
.qwen/extension-store
.qwen/extensions/*/node_modules
.qwen/bin
.qwen/sandbox
.qwen/scratch-workspaces
.qwen/locales
.qwen/arena
.qwen/artifacts
.qwen/resources
.qwen/startup-perf
.cache/amp/runner-desktop
.cache/amp/desktop
.cache/amp/bin
.cache/amp/obelisk-runs
.amp/bin
.factory/updates
.factory/cache/sounds
.factory/bin
.factory/tools
.factory/software-factory/*/*/repos
.factory/software-factory/*/*/worktrees
.factory/temp
.factory/worktrees
.factory/snapshots
.factory/generated-images
.local/share/muse/plugins/cache/builtin
.local/share/muse/skills/bundled
.local/share/muse/plugins/marketplaces
.local/bin/.muse-update.*
AppData/Local/Programs/muse/muse-bin-*.exe
AppData/Local/Programs/muse/.muse-update.*.exe
.muse/worktrees
.augment/binaries
.augment/vfs
.augment/knowledgebase
.augment/uploads
.augment/worktrees
.augment/plugins/marketplaces
.aws/amazonq/cli-checkouts
.aws/amazonq/knowledge_bases
.kiro/extensions
.kiro/cloud-cache
.kiro/sandbox-state
.kiro/sandbox-curl
*/User/globalStorage/kiro.kiroagent/*lance*
*/User/globalStorage/kiro.kiroagent/index
.pearai/extensions
.pearai/index/lancedb
.pearai/index/*.sqlite
.pearai/types
.pearai/out
.pearai/node_modules
.pearai/.diffs
.pearai/.migrations
.pearai/dev_data/devdata.sqlite
*/User/globalStorage/pearai.pearai-roo-cline/checkpoints
*/User/globalStorage/pearai.pearai-roo-cline/tasks/*/checkpoints
*/User/globalStorage/pearai.pearai-roo-cline/cache
*/globalStorage/sourcegraph.cody-ai/symf/symf-*
*/Cody-nodejs/symf/symf-*
*/Cody-nodejs/Data/symf/symf-*
*/Cody-nodejs/dist
*/Cody-nodejs/Config/dist
.twinny/embeddings/*/chunks.lance
.twinny/server/plugins/*/repos/*/checkout
.twinny/server/plugins/*/repos/*/index
.tabby/models
.tabby/index
.tabby/repositories
.openinterpreter/packages
.openinterpreter/cache
.openinterpreter/.tmp
.openinterpreter/tmp
.openinterpreter/plugins/cache
.openinterpreter/skills/.system
.openinterpreter/worktrees
.openinterpreter/.sandbox
.openinterpreter/.sandbox-bin
.openinterpreter/visualizations
.openinterpreter/models-cache
.openhands/cache
.openhands/agent-canvas/workspaces
.openhands/agent-canvas/tmux
.pi/agent/bin
.pi/agent/tools/fd*
.pi/agent/tools/rg*
.pi/agent/tmp
.pi/agent/npm/node_modules
.pi/agent/git/*/node_modules
.pi/agent/git/*/.git
.pi/npm/node_modules
.pi/git/*/node_modules
.pi/git/*/.git
.pi/server/*.sock
.letta/bin
.letta/mod-cache
.letta/tool_execution_dir
.letta/chroma
.memgpt/chroma
.hermes/hermes-agent/[!.]*
.hermes/hermes-agent/.[!e]*
AppData/Local/hermes/hermes-agent/[!.]*
AppData/Local/hermes/hermes-agent/.[!e]*
.hermes*/models
.hermes*/runtimes
.hermes*/node
.hermes*/installs
.hermes*/tools
.hermes*/sandboxes
.hermes*/checkpoints/store/objects
.hermes*/checkpoints/store/indexes
.hermes*/checkpoints/legacy-*
.hermes*/state-snapshots
.hermes*/backups
.hermes*/browser-profile
.hermes*/browser-profiles
.hermes*/browser_profiles
.hermes*/chrome-debug
.hermes*/bot-desktop/browser-profile
.hermes*/plugins/*/node_modules
.hermes*/plugins/*/.venv
AppData/Local/hermes*/models
AppData/Local/hermes*/runtimes
AppData/Local/hermes*/node
AppData/Local/hermes*/installs
AppData/Local/hermes*/tools
AppData/Local/hermes*/sandboxes
AppData/Local/hermes*/checkpoints/store/objects
AppData/Local/hermes*/checkpoints/store/indexes
AppData/Local/hermes*/checkpoints/legacy-*
AppData/Local/hermes*/state-snapshots
AppData/Local/hermes*/backups
AppData/Local/hermes*/browser-profile
AppData/Local/hermes*/browser-profiles
AppData/Local/hermes*/browser_profiles
AppData/Local/hermes*/chrome-debug
AppData/Local/hermes*/bot-desktop/browser-profile
AppData/Local/hermes*/plugins/*/node_modules
AppData/Local/hermes*/plugins/*/.venv
.config/Hermes/Cache
.config/Hermes/Code Cache
.config/Hermes/GPUCache
Library/Application Support/Hermes/Cache
Library/Application Support/Hermes/Code Cache
Library/Application Support/Hermes/GPUCache
AppData/Roaming/Hermes/Cache
AppData/Roaming/Hermes/Code Cache
AppData/Roaming/Hermes/GPUCache
.openclaw*/dev
.openclaw*/git
.openclaw*/npm
.openclaw*/npm-runtime
.openclaw*/tmp
.openclaw*/tools
.openclaw*/worktrees
.openclaw*/plugin-skills
.openclaw*/extensions/*/node_modules
.openclaw*/sandbox/skills-workspaces
.openclaw*/agents/*/agent/tmp
.openclaw*/agents/*/agent/.tmp
.openclaw*/browser/*/user-data/*/Cache
.openclaw*/browser/*/user-data/*/Code Cache
.openclaw*/browser/*/user-data/*/GPUCache
.openclaw*/browser/*/user-data/*/Service Worker
.clawdbot/tools
.clawdbot/npm
.nanobot*/bin
.nanobot*/run
.nanobot*/cache
agent-zero*/.venv
Desktop/agent-zero*/.venv
agent-zero*/.conda
Desktop/agent-zero*/.conda
agent-zero*/.git
Desktop/agent-zero*/.git
agent-zero*/tmp/playwright
Desktop/agent-zero*/tmp/playwright
agent-zero*/tmp/memory/embeddings
Desktop/agent-zero*/tmp/memory/embeddings
agent-zero*/usr/.time_travel
Desktop/agent-zero*/usr/.time_travel
agent-zero*/usr/workdir/*/.venv
Desktop/agent-zero*/usr/workdir/*/.venv
agent-zero*/usr/workdir/*/node_modules
Desktop/agent-zero*/usr/workdir/*/node_modules
.local/share/a0/browser-profiles
Library/Application Support/A0/Browser Profiles
AppData/Local/A0/Browser Profiles
*/Agent Zero Launcher/Cache
*/Agent Zero Launcher/Code Cache
*/Agent Zero Launcher/GPUCache
*/Agent Zero Launcher/docker_manager/cache
.local/share/local-deep-research/cache
.local/share/local-deep-research/models
.local/share/local-deep-research/journal_data
.local/share/local-deep-research/library
Library/Application Support/local-deep-research/cache
Library/Application Support/local-deep-research/models
Library/Application Support/local-deep-research/journal_data
Library/Application Support/local-deep-research/library
AppData/Local/local-deep-research/local-deep-research/cache
AppData/Local/local-deep-research/local-deep-research/models
AppData/Local/local-deep-research/local-deep-research/journal_data
AppData/Local/local-deep-research/local-deep-research/library
Documents/LocalDeepResearch/Library
.ollama/models
AppData/Local/Ollama/updates
Library/Caches/ollama
Library/Caches/com.electron.ollama
.time_travel
usr/.time_travel
workdir/*/.venv
workdir/*/node_modules
usr/workdir/*/.venv
usr/workdir/*/node_modules
tmp/playwright
tmp/memory/embeddings
models
index
repositories
journal_data
library
agent-canvas/workspaces
agent-canvas/tmux
hermes-agent/[!.]*
hermes-agent/.[!e]*
runtimes
node
installs
tools
sandboxes
checkpoints/store/objects
checkpoints/store/indexes
checkpoints/legacy-*
state-snapshots
backups
browser-profile
browser-profiles
browser_profiles
chrome-debug
bot-desktop/browser-profile
plugins/*/node_modules
plugins/*/.venv
npm
npm-runtime
worktrees
extensions/*/node_modules
sandbox/skills-workspaces
browser/*/user-data/*/Cache
browser/*/user-data/*/Code Cache
browser/*/user-data/*/GPUCache
browser/*/user-data/*/Service Worker
bin
mod-cache
tool_execution_dir
chroma
'@

$SECRET_GLOBS = @'
.claude/.credentials.json
.claude/.device-keys.json
.claude/hfi-auth.json
.claude/.session_ingress_token
.claude/remote/.oauth_token
.claude/remote/.api_key
.claude.json
.claude-*/.credentials.json
.claude-*/.device-keys.json
.claude-*/hfi-auth.json
.claude-*/.session_ingress_token
.claude-*/remote/.oauth_token
.claude-*/remote/.api_key
.claude-*/.claude.json
Library/Application Support/Claude*/config.json
Library/Application Support/Claude*/Cookies*
Library/Application Support/Claude*/host-creds-*.json
Library/Application Support/Claude*/ccd-session-secrets/*
.config/Claude*/config.json
.config/Claude*/Cookies*
.config/Claude*/host-creds-*.json
.config/Claude*/ccd-session-secrets/*
AppData/Roaming/Claude*/config.json
AppData/Roaming/Claude*/Cookies*
AppData/Roaming/Claude*/host-creds-*.json
AppData/Roaming/Claude*/ccd-session-secrets/*
AppData/Local/Claude*/config.json
AppData/Local/Claude*/Cookies*
AppData/Local/Claude*/host-creds-*.json
AppData/Local/Claude*/ccd-session-secrets/*
*/Claude*/Local State
*/Claude*/claude_desktop_config.json
*/Claude*/local-agent-mode-sessions/*/.audit-key
*.gemini/oauth_creds.json
*.gemini/gemini-credentials.json
*.gemini/mcp-oauth-tokens.json
*.gemini/a2a-oauth-tokens.json
*.gemini/.env
*.gemini/extensions/*/.env
*.gemini/antigravity-cli/antigravity-oauth-token
.qwen/oauth_creds.json
.qwen/mcp-oauth-tokens*.json
.qwen/extension-secrets-v1.json
.qwen/.env
.qwen/settings.json
.qwen/extensions/*/.qwen-extension-git-credentials.json
.qwen/channels/*.json
.codex/auth.json
.codex/.credentials.json
.codex/secrets/*
.codex/.sandbox-secrets/*
.codex/config.toml
.codex/.env
*/Roaming/ChatGPT/Network/Cookies*
*/Roaming/ChatGPT/Local State
.config/github-copilot/*.json
AppData/Local/github-copilot/*.json
.copilot/config.json
.copilot/mcp-oauth-config*
.copilot/mcp-config.json
.cursor/auth.json
.config/cursor/auth.json
AppData/Roaming/Cursor/auth.json
.cursor/mcp.json
.cursor/projects/*/mcp-auth.json
.vscode*/cli/token*.json
*/User/mcp.json
*/User/profiles/*/mcp.json
.codeium/config.json
.codeium/mcp_config.json
.codeium/windsurf/mcp_config.json
.config/devin/mcp_config.json
AppData/Roaming/devin/mcp_config.json
.local/share/devin/credentials.toml
AppData/Roaming/devin/credentials.toml
.cline/data/settings/providers.json
.cline/data/settings/cline_mcp_settings.json
.cline/data/settings/composio/*.json
.cline/data/secrets.json
.cline/data/connectors/settings.json
.cline/data/db/connectors.db*
.vscode-mock/global-storage/secrets.json
.local/share/kilo/auth.json
.local/share/kilo/mcp-auth.json
.local/share/kilo/kilo*.db*
.local/share/kilo/opencode*.db*
.config/kilo/kilo.json*
.config/kilo/opencode.json*
.config/kilo/config.json
.kilocode/cli/config.json
.continue/auth*.json
.continue/.env
.continue/config.yaml
.continue/config.json
.continue/config.ts
.continue/.configs/*/config.js*
.continue/mcpServers/*
.continue/index/globalContext.json
*/globalStorage/continue.continue/*.bin
.aider/oauth-keys.env
.aider.conf.yml
.aider.model.settings.yml
.local/share/opencode/auth.json
.local/share/opencode/mcp-auth.json
.local/share/opencode/opencode*.db*
.config/opencode/opencode.json*
.config/opencode/config.json
.opencode/opencode.json*
.local/share/crush/crush.json
AppData/Local/crush/crush.json
.config/crush/crush.json
.config/crush/crushrc
.config/crush/.crushrc
.crush/crush.json
.config/goose/secrets.yaml
.config/goose/config.yaml
.config/goose/githubcopilot/*
.config/goose/chatgpt_codex/*
.config/goose/gemini_oauth/*
.config/goose/kimicode/*
.config/goose/muse_code/*
.config/goose/huggingface/*
.config/goose/databricks/*
.config/goose/xai_oauth/*
.config/goose/roaming_node_key
.config/goose/tls/*
AppData/Roaming/Block/goose/config/secrets.yaml
AppData/Roaming/Block/goose/config/config.yaml
AppData/Roaming/Block/goose/config/githubcopilot/*
AppData/Roaming/Block/goose/config/chatgpt_codex/*
AppData/Roaming/Block/goose/config/gemini_oauth/*
AppData/Roaming/Block/goose/config/kimicode/*
AppData/Roaming/Block/goose/config/muse_code/*
AppData/Roaming/Block/goose/config/huggingface/*
AppData/Roaming/Block/goose/config/databricks/*
AppData/Roaming/Block/goose/config/xai_oauth/*
AppData/Roaming/Block/goose/config/roaming_node_key
AppData/Roaming/Block/goose/config/tls/*
.local/state/goose/logs/llm_request.*
AppData/Roaming/Block/goose/data/logs/llm_request.*
.config/zed/development_credentials
.config/zed/settings.json
.config/zed/settings_backup.json
.config/zed/global_settings.json
AppData/Roaming/Zed/development_credentials
AppData/Roaming/Zed/settings.json
AppData/Roaming/Zed/settings_backup.json
AppData/Roaming/Zed/global_settings.json
.var/app/dev.zed.Zed*/config/zed/settings.json
.var/app/dev.zed.Zed*/config/zed/development_credentials
.local/share/amp/secrets.json
.local/share/amp/accounts.json
.local/share/amp/accounts/*/secrets.json
.amp/oauth/*
.factory/auth.json
.factory/auth.v2.*
.factory/auth.encrypted
.factory/config.json
.factory/temp/env/*
.factory/prem-auth/*/credentials.*
.factory/mcp-oauth*
.config/muse/auth.json
.config/muse/settings.json
.augment/session.json
.augment/settings.json
.augment/settings.local.json
*/kiro-cli/data.sqlite3*
*/amazon-q/data.sqlite3*
.aws/sso/cache/*.json
.aws/amazonq/mcp.json
.kiro/settings/mcp.json
.kiro/powers/installed/*/mcp.json
.kiro/agents/*.json
.kiro/web-session/*
.kiro/secrets.json
.pearai/config.json
.pearai/config.ts
.pearai/.env
.pearai/.configs/*/config.js*
*/globalStorage/pearai.pearai-roo-cline/settings/pearai_agent_mcp_settings.json
.pearai-agent/mcp.json
*/Cody-nodejs/user-settings.json
*/Cody-nodejs/Config/user-settings.json
*/User/globalStorage/rjmacarthy.twinny/twinny-providers.json
.twinny/node/identity.json
.twinny/server/license
.twinny/server/plugins/*/settings.json
.tabby/config.toml
.tabby-client/agent/config.toml
.openinterpreter/auth.json
.openinterpreter/.credentials.json
.openinterpreter/credentials/*
.openinterpreter/device_id
.openinterpreter/secrets/*
.openinterpreter/.sandbox-secrets/*
.openinterpreter/.env
.openinterpreter/config.toml
.openhands/agent-canvas/secret-key.txt
.openhands/agent-canvas/api-key.txt
.openhands/settings.json
.openhands/secrets.json
.openhands/profiles/*
.openhands/provider-connections/*
.openhands/auth/*
.openhands/runtime-control/*
.openhands/agent_settings.json
.openhands/cloud/*
.openhands/mcp.json
.openhands/.jwt_secret
.openhands/.keys
.pi/agent/auth.json
.pi/agent/auth.json.*
.pi/agent/mcp-auth.json
.pi/agent/oauth.json*
.pi/agent/models.json
.pi/agent/mcp.json
.pi/mcp.json
.config/little-coder/models.json
.letta/settings.json
.letta/pg_uri
.letta/credentials
.letta/lc-local-backend/providers/auth.json
.letta/channels/*/accounts.json
.letta/channels/whatsapp/auth/*
.letta/agents/*/memory/.git/config
.letta/agents/*/memory/.git/letta-credential-helper.cmd
.config/letta/settings.json
.memgpt/credentials
.hermes*/.env
.hermes*/.env.bak*
.hermes*/.op.env
.hermes*/npmrc
.hermes*/auth.json
.hermes*/auth.json.*
.hermes*/auth/*
.hermes*/.anthropic_oauth.json
.hermes*/.copilot_jwt.json
.hermes*/google_*.json
.hermes*/google_chat_user_tokens/*
.hermes*/slack_tokens.json
.hermes*/honcho.json
.hermes*/mem0.json
.hermes*/webhook_subscriptions.json
.hermes*/teams_pipeline_store.json
.hermes*/mcp-tokens/*
.hermes*/vault/*
.hermes*/browser_auth/*
.hermes*/pairing/*
.hermes*/platforms/pairing/*
.hermes*/whatsapp/session/*
.hermes*/platforms/whatsapp/session/*
.hermes*/matrix/store/*
.hermes*/platforms/matrix/store/*
.hermes*/cache/bws_cache*.json
.hermes*/weixin/accounts/*
.hermes*/runtime/photon-sidecar.json
.hermes*/proxy/*
.hermes*/home/*
AppData/Local/hermes*/.env
AppData/Local/hermes*/.env.bak*
AppData/Local/hermes*/.op.env
AppData/Local/hermes*/npmrc
AppData/Local/hermes*/auth.json
AppData/Local/hermes*/auth.json.*
AppData/Local/hermes*/auth/*
AppData/Local/hermes*/.anthropic_oauth.json
AppData/Local/hermes*/.copilot_jwt.json
AppData/Local/hermes*/google_*.json
AppData/Local/hermes*/google_chat_user_tokens/*
AppData/Local/hermes*/slack_tokens.json
AppData/Local/hermes*/honcho.json
AppData/Local/hermes*/mem0.json
AppData/Local/hermes*/webhook_subscriptions.json
AppData/Local/hermes*/teams_pipeline_store.json
AppData/Local/hermes*/mcp-tokens/*
AppData/Local/hermes*/vault/*
AppData/Local/hermes*/browser_auth/*
AppData/Local/hermes*/pairing/*
AppData/Local/hermes*/platforms/pairing/*
AppData/Local/hermes*/whatsapp/session/*
AppData/Local/hermes*/platforms/whatsapp/session/*
AppData/Local/hermes*/matrix/store/*
AppData/Local/hermes*/platforms/matrix/store/*
AppData/Local/hermes*/cache/bws_cache*.json
AppData/Local/hermes*/weixin/accounts/*
AppData/Local/hermes*/runtime/photon-sidecar.json
AppData/Local/hermes*/proxy/*
AppData/Local/hermes*/home/*
.openclaw*/openclaw.json*
.openclaw*/clawdbot.json*
.openclaw*/.env
.openclaw*/credentials/*
.openclaw*/service-env/*
.openclaw*/agents/*/agent/auth-profiles.json*
.openclaw*/agents/*/agent/models.json
.openclaw*/browser/*/user-data/*/Cookies*
.clawdbot/clawdbot.json*
.clawdbot/.env
.clawdbot/credentials/*
.moltbot/moltbot.json*
.moltbot/.env
.moltbot/credentials/*
.config/openclaw/gateway.env
.nanobot*/config.json
.nanobot*/auth/*
.nanobot*/whatsapp-auth/*
.nanobot*/matrix-store/*
agent-zero*/usr/.env
Desktop/agent-zero*/usr/.env
agent-zero*/usr/secrets.env
Desktop/agent-zero*/usr/secrets.env
agent-zero*/usr/settings.json
Desktop/agent-zero*/usr/settings.json
agent-zero*/usr/projects/*/.a0proj/secrets.env
Desktop/agent-zero*/usr/projects/*/.a0proj/secrets.env
agent-zero*/.env
Desktop/agent-zero*/.env
agent-zero*/tmp/secrets.env
Desktop/agent-zero*/tmp/secrets.env
agent-zero*/tmp/settings.json
Desktop/agent-zero*/tmp/settings.json
agent-zero*/usr/plugins/_desktop/profiles/*/.ssh/*
Desktop/agent-zero*/usr/plugins/_desktop/profiles/*/.ssh/*
agent-zero*/usr/plugins/_desktop/profiles/*/.gnupg/*
Desktop/agent-zero*/usr/plugins/_desktop/profiles/*/.gnupg/*
.agent-zero/.env
.agent-zero/session_cookies.json
*/Agent Zero Launcher/docker_manager/state.json
*/Agent Zero Launcher/Local State
.config/shell_gpt/.sgptrc
.local/share/local-deep-research/.secret_key
Library/Application Support/local-deep-research/.secret_key
AppData/Local/local-deep-research/local-deep-research/.secret_key
.ollama/id_ed25519
.env
secrets.env
settings.json
projects/*/.a0proj/secrets.env
plugins/_desktop/profiles/*/.ssh/*
plugins/_desktop/profiles/*/.gnupg/*
usr/.env
usr/secrets.env
usr/settings.json
usr/projects/*/.a0proj/secrets.env
usr/plugins/_desktop/profiles/*/.ssh/*
usr/plugins/_desktop/profiles/*/.gnupg/*
tmp/secrets.env
tmp/settings.json
config.toml
id_ed25519
.secret_key
agent-canvas/secret-key.txt
agent-canvas/api-key.txt
secrets.json
profiles/*
provider-connections/*
runtime-control/*
agent_settings.json
cloud/*
mcp.json
.jwt_secret
.keys
pg_uri
credentials
lc-local-backend/providers/auth.json
channels/*/accounts.json
channels/whatsapp/auth/*
agents/*/memory/.git/config
agents/*/memory/.git/letta-credential-helper.cmd
.env.bak*
.op.env
npmrc
auth.json
auth.json.*
auth/*
.anthropic_oauth.json
.copilot_jwt.json
google_*.json
google_chat_user_tokens/*
slack_tokens.json
honcho.json
mem0.json
webhook_subscriptions.json
teams_pipeline_store.json
mcp-tokens/*
vault/*
browser_auth/*
pairing/*
platforms/pairing/*
whatsapp/session/*
platforms/whatsapp/session/*
matrix/store/*
platforms/matrix/store/*
cache/bws_cache*.json
weixin/accounts/*
runtime/photon-sidecar.json
proxy/*
home/*
openclaw.json*
clawdbot.json*
moltbot.json*
credentials/*
service-env/*
agents/*/agent/auth-profiles.json*
agents/*/agent/models.json
browser/*/user-data/*/Cookies*
config.json
whatsapp-auth/*
matrix-store/*
'@

# Docker and Podman named volumes, agent|glob matched against the volume name.
$DOCKER_VOLUMES = @'
# Matched against each volume name; the first matching line wins. A matched
# volume is collected whole as user "docker" with its _data directory as the
# home, so EXCLUDES and SECRET_GLOBS apply relative to the volume root.
# Agent Zero: a0_usr in the README docker run (Compose prefixes it as
# <project>_a0_usr) and a0-launcher-<slug>-usr in the A0 Launcher named-volume
# mode; both are mounted at /a0/usr
agent-zero|*a0_usr
agent-zero|a0-launcher-*-usr
# Local Deep Research: ldr_data in docker-compose.yml, mounted at /data
local-deep-research|*ldr_data
# Ollama: ollama in docs/docker.mdx, ollama_data in the Local Deep Research
# compose file; mounted at /root/.ollama
ollama|ollama
ollama|*ollama*
# Inferred names: the documentation of these tools bind-mounts the home directory
# instead of a named volume; a volume replacing it has the same layout (~/.tabby
# at /data, ~/.hermes at /opt/data, ~/.openclaw at /home/node/.openclaw, ...)
tabby|*tabby*
local-deep-research|*local-deep-research*
openhands|*openhands*
letta|*letta*
hermes|*hermes*
openclaw|*openclaw*
openclaw|*clawdbot*
nanobot|*nanobot*
'@


if ($Version) { Write-Output "$TOOL $ToolVersion"; exit 0 }

function Get-TableLines([string]$table) {
  $table -split "`r?`n" | Where-Object { $_ -ne '' -and -not $_.StartsWith('#') }
}

if ($List) {
  Write-Output '# home artifacts (agent|glob relative to home)'
  $CATALOG -split "`r?`n" | Where-Object { $_ -ne '' } | ForEach-Object { Write-Output $_ }
  Write-Output '# project artifacts (relative to each discovered project)'
  $PROJECT_CATALOG -split "`r?`n" | Where-Object { $_ -ne '' } | ForEach-Object { Write-Output $_ }
  Write-Output '# excluded unless --full'
  $EXCLUDES -split "`r?`n" | Where-Object { $_ -ne '' } | ForEach-Object { Write-Output $_ }
  Write-Output ''
  Write-Output '# credential files (flagged secret, skipped with --no-secrets)'
  $SECRET_GLOBS -split "`r?`n" | Where-Object { $_ -ne '' } | ForEach-Object { Write-Output $_ }
  Write-Output '# docker volumes (agent|volume name glob)'
  $DOCKER_VOLUMES -split "`r?`n" | Where-Object { $_ -ne '' } | ForEach-Object { Write-Output $_ }
  exit 0
}

if ($MaxFileSizeMB -lt 0) { Write-Error 'Invalid -MaxFileSizeMB'; exit 1 }
$MaxSize = [int64]$MaxFileSizeMB * 1024 * 1024

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
$Sep = [string][System.IO.Path]::DirectorySeparatorChar

function Convert-GlobToRegex([string]$glob, [bool]$starCrossesSeparator) {
  $sb = New-Object System.Text.StringBuilder
  [void]$sb.Append('^')
  $i = 0
  while ($i -lt $glob.Length) {
    $c = $glob[$i]
    switch ($c) {
      '*' { if ($starCrossesSeparator) { [void]$sb.Append('.*') } else { [void]$sb.Append('[^/]*') } }
      '?' { if ($starCrossesSeparator) { [void]$sb.Append('.') } else { [void]$sb.Append('[^/]') } }
      '[' {
        $j = $glob.IndexOf(']', $i + 1)
        if ($j -gt $i) {
          # [!...] is the sh negated class; the regex form is [^...]
          $cls = $glob.Substring($i, $j - $i + 1)
          if ($cls.StartsWith('[!')) { $cls = '[^' + $cls.Substring(2) }
          [void]$sb.Append($cls); $i = $j
        }
        else { [void]$sb.Append('\[') }
      }
      default { [void]$sb.Append([regex]::Escape([string]$c)) }
    }
    $i++
  }
  [void]$sb.Append('$')
  $sb.ToString()
}

$script:ExcludeRegexes = @()
$script:SecretRegexes = @()
foreach ($e in (Get-TableLines $EXCLUDES)) { $script:ExcludeRegexes += (Convert-GlobToRegex $e $true) }
foreach ($e in ($SECRET_GLOBS -split "`r?`n" | Where-Object { $_ -ne '' })) { $script:SecretRegexes += (Convert-GlobToRegex $e $true) }
if ($Full) { $script:ExcludeRegexes = @() }

function Test-AnyMatch([string]$rel, [string[]]$regexes) {
  foreach ($rx in $regexes) { if ($rel -match $rx) { return $true } }
  return $false
}

# Test-Path throws a real UnauthorizedAccessException on protected profiles
# even with -ErrorAction, so probe through .NET which never throws.
function Test-PathQuiet([string]$p, [string]$kind) {
  if (-not $p) { return $false }
  try {
    if ($kind -eq 'Leaf') { return [System.IO.File]::Exists($p) }
    if ($kind -eq 'Container') { return [System.IO.Directory]::Exists($p) }
    return ([System.IO.File]::Exists($p) -or [System.IO.Directory]::Exists($p))
  } catch { return $false }
}

function Join-PathSafe([string]$a, [string]$b) {
  $b = $b.Replace('\', $Sep).Replace('/', $Sep)
  if ($a.EndsWith('\') -or $a.EndsWith('/')) { return $a + $b }
  return $a + $Sep + $b
}

# Expand a catalog glob (segments split on /, * does not cross separators)
# under a base directory. Returns full paths of existing items.
function Expand-Glob([string]$base, [string]$pattern) {
  $segments = $pattern -split '/'
  $current = @($base)
  foreach ($seg in $segments) {
    if ($seg -eq '') { continue }
    $next = @()
    $isWild = ($seg -match '[\*\?\[]')
    foreach ($dir in $current) {
      if ($isWild) {
        $rx = Convert-GlobToRegex $seg $false
        try {
          $children = Get-ChildItem -LiteralPath $dir -Force -ErrorAction Stop
        } catch { $children = @() }
        foreach ($child in $children) { if ($child.Name -match $rx) { $next += $child.FullName } }
      } else {
        $candidate = Join-PathSafe $dir $seg
        if (Test-PathQuiet $candidate 'Any') { $next += $candidate }
      }
    }
    $current = $next
    if ($current.Count -eq 0) { break }
  }
  if ($current.Count -gt 0 -and $current[0] -eq $base) { return @() }
  return $current
}

function Get-RelPath([string]$base, [string]$full) {
  $b = $base.TrimEnd('\', '/')
  if ($full.Length -gt $b.Length -and $full.StartsWith($b, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $full.Substring($b.Length).TrimStart('\', '/').Replace('\', '/')
  }
  return $full.Replace('\', '/')
}

function Get-Epoch($dt) {
  try { return [int64]([DateTimeOffset]::new([DateTime]$dt).ToUnixTimeSeconds()) } catch { return [int64]0 }
}

function Get-OwnerName([string]$path) {
  try {
    $acl = [System.IO.File]::GetAccessControl($path)
    return $acl.GetOwner([System.Security.Principal.NTAccount]).Value
  } catch {
    try { return [System.IO.File]::GetAccessControl($path).GetOwner([System.Security.Principal.SecurityIdentifier]).Value } catch { return '' }
  }
}

function Get-FileSha256([string]$path) {
  try { return (Get-FileHash -LiteralPath $path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLower() } catch { return '' }
}

# Copy with FileShare.ReadWrite|Delete so files held open by a running editor
# (SQLite state stores, LevelDB) can still be read.
function Copy-FileShared([string]$src, [string]$dst) {
  $in = $null; $out = $null
  try {
    $in = New-Object System.IO.FileStream($src, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, ([System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete))
    $out = New-Object System.IO.FileStream($dst, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    $in.CopyTo($out)
  } finally {
    if ($out) { $out.Dispose() }
    if ($in) { $in.Dispose() }
  }
  try {
    $si = Get-Item -LiteralPath $src -Force
    [System.IO.File]::SetCreationTimeUtc($dst, $si.CreationTimeUtc)
    [System.IO.File]::SetLastWriteTimeUtc($dst, $si.LastWriteTimeUtc)
    [System.IO.File]::SetLastAccessTimeUtc($dst, $si.LastAccessTimeUtc)
  } catch { }
}

function Get-DirSize([string]$dir) {
  try {
    $m = Get-ChildItem -LiteralPath $dir -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum
    if ($m.Sum) { return [int64]$m.Sum } else { return [int64]0 }
  } catch { return [int64]0 }
}

function Get-LinkTarget($item) {
  try {
    $p = $item.PSObject.Properties['Target']
    if ($p -and $p.Value) { return ([string[]]$p.Value) -join ';' }
  } catch { }
  return ''
}

# ---------------------------------------------------------------------------
# Symlinks are recreated in the staging tree with their target string as
# stored, as the sh collector does with ln -s, so tar archives the link
# itself. PowerShell 7 (.NET 6+) has File/Directory.CreateSymbolicLink;
# Windows PowerShell 5.1 runs cmd.exe's mklink, which keeps the target
# verbatim, accepts one that does not exist, and works unprivileged in
# Developer Mode from Windows 10 1703. New-Item -ItemType SymbolicLink is not
# used: on 5.1 it resolves a relative target against the current directory
# and refuses a target that does not exist. ZipFile follows links, so the zip
# path never has them: none are made when zip is the archiver from the start,
# and they are removed before a fall back to zip.
# ---------------------------------------------------------------------------
$script:LinkApi = $null
$script:LinkApiError = ''
$script:LinkFileMethod = $null
$script:LinkDirMethod = $null
$script:CmdExe = ''
$script:StagedLinks = New-Object System.Collections.ArrayList
$script:LinkCounts = @{ zip = 0; failed = 0 }
function Get-LinkApi {
  if ($null -ne $script:LinkApi) { return $script:LinkApi }
  $script:LinkApi = ''
  # Looked up by reflection: the methods do not exist in .NET Framework.
  $script:LinkFileMethod = [System.IO.File].GetMethod('CreateSymbolicLink', [Type[]]@([string], [string]))
  $script:LinkDirMethod = [System.IO.Directory].GetMethod('CreateSymbolicLink', [Type[]]@([string], [string]))
  if ($null -ne $script:LinkFileMethod -and $null -ne $script:LinkDirMethod) { $script:LinkApi = 'dotnet' }
  elseif ($env:OS -eq 'Windows_NT') {
    $c = ''
    if ($env:SystemRoot) { $c = Join-PathSafe $env:SystemRoot 'System32\cmd.exe' }
    if ($c -ne '' -and (Test-PathQuiet $c 'Leaf')) { $script:CmdExe = $c; $script:LinkApi = 'mklink' }
    else { $script:LinkApiError = 'cmd.exe not found for mklink' }
  } else { $script:LinkApiError = 'no symlink API in this PowerShell' }
  return $script:LinkApi
}

# Runs cmd.exe /d /v:off /c mklink [/D] "link" "target" with an argument
# string built here, so PowerShell's native-argument quoting is not involved.
# Returns '' on success, otherwise mklink's message and exit code.
function Invoke-Mklink([string]$dest, [string]$target, [bool]$isDir) {
  # cmd expands %NAME% even inside quotes, and a quote would end the argument.
  if ($dest.Contains('%') -or $dest.Contains('"') -or $target.Contains('%') -or $target.Contains('"')) {
    return 'link path or target contains % or ", which cmd.exe mklink cannot take verbatim'
  }
  $sw = ''; if ($isDir) { $sw = '/D ' }
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $script:CmdExe
  $psi.Arguments = '/d /v:off /c mklink ' + $sw + '"' + $dest + '" "' + $target + '"'
  # The link path is absolute; a UNC current directory would add a cmd.exe warning to stderr.
  $psi.WorkingDirectory = $env:SystemRoot
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $pr = [System.Diagnostics.Process]::Start($psi)
  # mklink's messages are short, so reading one stream to the end cannot block on the other.
  $errText = $pr.StandardError.ReadToEnd()
  [void]$pr.StandardOutput.ReadToEnd()
  $pr.WaitForExit()
  if ($pr.ExitCode -eq 0) { return '' }
  $msg = ($errText -replace '\s+', ' ').Trim()
  if ($msg -eq '') { $msg = 'mklink failed' }
  return "$msg (mklink exit $($pr.ExitCode))"
}

# Makes the link at $dest; returns '' on success, otherwise the reason.
function Invoke-CreateSymlink([string]$dest, [string]$target, [bool]$isDir) {
  $api = Get-LinkApi
  try {
    if ($api -eq 'dotnet') {
      $m = $script:LinkFileMethod; if ($isDir) { $m = $script:LinkDirMethod }
      # Plain strings: Invoke rejects PSObject-wrapped arguments.
      $margs = New-Object 'object[]' 2; $margs[0] = [string]$dest; $margs[1] = [string]$target
      [void]$m.Invoke($null, $margs)
    } elseif ($api -eq 'mklink') {
      $why = Invoke-Mklink $dest $target $isDir
      if ($why -ne '') { return $why }
    } else { return $script:LinkApiError }
  } catch {
    # Invoke wraps the IOException; report the innermost message.
    $e = $_.Exception; while ($null -ne $e.InnerException) { $e = $e.InnerException }
    return $e.Message
  }
  [void]$script:StagedLinks.Add(@($dest, $isDir))
  return ''
}

# Recreates the reparse point $item at $dest; returns '' or the row's error.
function Add-StagedLink($item, [string]$dest) {
  if (-not $TarExe) { $script:LinkCounts.zip++; return 'not recreated in the archive: zip cannot store symlinks' }
  $vals = @()
  try { $p = $item.PSObject.Properties['Target']; if ($p -and $p.Value) { $vals = @([string[]]$p.Value) } } catch { }
  if ($vals.Count -ne 1 -or $vals[0] -eq '') { $script:LinkCounts.failed++; return 'not recreated in the archive: reparse point has no single link target' }
  # Only Windows distinguishes file and directory links.
  $isDir = ($env:OS -eq 'Windows_NT') -and (($item.Attributes -band [System.IO.FileAttributes]::Directory) -ne 0)
  $why = ''
  try {
    $d = Split-Path -Path $dest -Parent
    if (-not (Test-PathQuiet $d 'Any')) { New-Item -ItemType Directory -Path $d -Force -ErrorAction Stop | Out-Null }
    $why = Invoke-CreateSymlink $dest $vals[0] $isDir
  } catch { $why = $_.Exception.Message }
  if ($why -eq '') { return '' }
  $script:LinkCounts.failed++
  Write-CollectorLog "symlink not recreated: $($item.FullName): $why"
  return "not recreated in the archive: $why"
}

# Deletes the staged links themselves, never what they point to, so the
# cleanup does not depend on how each PowerShell version's Remove-Item
# -Recurse treats a directory link.
# Called after the log writer is closed, so it appends to the log directly.
# Returns how many links could not be removed.
function Clear-StagedLinks {
  $left = 0
  foreach ($l in @($script:StagedLinks)) {
    try { if ($l[1]) { [System.IO.Directory]::Delete($l[0]) } else { [System.IO.File]::Delete($l[0]) } }
    catch { $left++; [System.IO.File]::AppendAllText($LogPath, "could not remove staged link $($l[0]): $($_.Exception.Message)`n", $Utf8NoBom) }
  }
  $script:StagedLinks.Clear()
  return $left
}

# After a late fall back to zip the staged links are gone, so their rows lose
# archive_path and say why; the manifest is rewritten before it is archived.
function Clear-LinkArchivePaths([string]$reason) {
  $lines = [System.IO.File]::ReadAllLines($ManifestPath, $Utf8NoBom)
  $w = New-Object System.IO.StreamWriter($ManifestPath, $false, $Utf8NoBom)
  try {
    foreach ($ln in $lines) {
      if ($ln.Contains('"status":"symlink"')) {
        $o = $ln | ConvertFrom-Json
        if ($o.status -eq 'symlink' -and $o.archive_path) { $o.archive_path = ''; $o.error = $reason; $ln = $o | ConvertTo-Json -Compress -Depth 2 }
      }
      $w.WriteLine($ln)
    }
  } finally { $w.Close() }
}

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
$Mode = 'live'
if ($Root -ne '') {
  if (-not (Test-PathQuiet $Root 'Container')) { Write-Error "Root is not a directory: $Root"; exit 2 }
  $Root = (Resolve-Path -LiteralPath $Root).Path.TrimEnd('\', '/')
  $Mode = 'image'
}
# -Inventory writes nothing: no output directory, staging, log or archive.
if (-not $Inventory) {
if (-not (Test-PathQuiet $OutputDir 'Any')) { try { New-Item -ItemType Directory -Path $OutputDir -Force -ErrorAction Stop | Out-Null } catch { Write-Error "Cannot create output dir: $OutputDir"; exit 2 } }
$OutputDir = (Resolve-Path -LiteralPath $OutputDir).Path.TrimEnd('\', '/')
if ($OutputDir -eq '') { $OutputDir = $Sep }
}

$StartTs = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$Stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$HostName = $env:COMPUTERNAME; if (-not $HostName) { $HostName = [System.Net.Dns]::GetHostName() }
$HostSafe = ($HostName -replace '[^A-Za-z0-9._-]', '-')
$Name = "${HostSafe}_${Stamp}_agent-artifacts"
$Stage = Join-PathSafe $OutputDir ".stage-$Name"
$LogPath = Join-PathSafe $OutputDir "$Name.log"
$ManifestPath = Join-PathSafe $OutputDir "$Name.manifest.jsonl"
$SummaryPath = Join-PathSafe $OutputDir "$Name.collection.json"

$TarExe = $null
$tarCmd = $null
$IsWindowsHost = ($env:OS -eq 'Windows_NT')
if ($Inventory) { }
elseif ($IsWindowsHost) { $tarCmd = Get-Command tar.exe -ErrorAction SilentlyContinue } else { $tarCmd = Get-Command tar -ErrorAction SilentlyContinue }
if ($tarCmd) { $TarExe = $tarCmd.Source }
if ($TarExe) { $Archive = Join-PathSafe $OutputDir "$Name.tar.gz" } else { $Archive = Join-PathSafe $OutputDir "$Name.zip" }

$script:LogWriter = $null
$script:ManifestWriter = $null
if (-not $Inventory) {
  New-Item -ItemType Directory -Path (Join-PathSafe $Stage 'fs') -Force | Out-Null
  $script:LogWriter = New-Object System.IO.StreamWriter($LogPath, $false, $Utf8NoBom)
  $script:ManifestWriter = New-Object System.IO.StreamWriter($ManifestPath, $false, $Utf8NoBom)
  $script:LogWriter.AutoFlush = $true
}
$script:Counts = @{ collected = 0; symlink = 0; skipped_excluded = 0; skipped_size = 0; skipped_secret = 0; error_copy = 0; skipped_unmatched_volume = 0; bytes = [int64]0 }
$script:WalkErrors = 0
$script:ClaimedPaths = @{}
# Homes (and other bases) that gave at least one manifest row
$script:RowHomes = @{}

function Write-CollectorLog([string]$msg) {
  $ts = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
  if ($script:LogWriter) { $script:LogWriter.WriteLine("$ts $msg") }
  if (-not $Quiet) { [Console]::Error.WriteLine($msg) }
}

function Write-Row([string]$user, [string]$homeDir, [string]$agent, [string]$path, [string]$archivePath, [string]$type,
                   [int64]$size, [int64]$mtime, [int64]$atime, [int64]$ctime, [int64]$btime, [string]$owner, [string]$attributes,
                   [string]$sha, [bool]$secret, [string]$status, [string]$target, [string]$err) {
  $row = [ordered]@{
    user = $user; home = $homeDir; agent = $agent; path = $path; archive_path = $archivePath; type = $type
    size = $size; mtime = $mtime; atime = $atime; ctime = $ctime; btime = $btime; uid = 0; gid = 0; mode = ''
    owner = $owner; attributes = $attributes; sha256 = $sha; secret = $secret; status = $status; target = $target; error = $err
  }
  $script:ManifestWriter.WriteLine(($row | ConvertTo-Json -Compress -Depth 2))
  if ($script:Counts.ContainsKey($status)) { $script:Counts[$status]++ }
  $script:RowHomes[$homeDir] = $true
  if ($status -eq 'collected') { $script:Counts['bytes'] += $size }
}

function Get-ArchiveRel([string]$full) {
  if ($Mode -eq 'image') { return 'fs/' + (Get-RelPath $Root $full) }
  if ($full.Length -ge 3 -and $full[1] -eq ':') { return 'fs/' + $full.Substring(0, 1).ToUpper() + '/' + $full.Substring(3).Replace('\', '/') }
  return 'fs/' + $full.TrimStart('\').Replace('\', '/')
}

# ---------------------------------------------------------------------------
# Inventory accumulators. $script:Inv maps agent -> files, bytes, first and
# last mtime (epoch seconds, 0 when unknown) and the matched catalog globs, in
# order of first match. Add-File feeds it instead of copying under -Inventory.
# ---------------------------------------------------------------------------
$script:Inv = [ordered]@{}
function Get-InvEntry([string]$agent) {
  if (-not $script:Inv.Contains($agent)) {
    $script:Inv[$agent] = @{ files = 0; bytes = [int64]0; first = [int64]0; last = [int64]0; evidence = (New-Object System.Collections.ArrayList) }
  }
  return $script:Inv[$agent]
}
function Add-InvEvidence([string]$agent, [string]$glob) {
  $e = Get-InvEntry $agent
  if (-not $e.evidence.Contains($glob)) { [void]$e.evidence.Add($glob) }
}
function Add-InvFile([string]$agent, $item) {
  $e = Get-InvEntry $agent
  $e.files++
  try { $e.bytes += [int64]$item.Length } catch { }
  $mt = Get-Epoch $item.LastWriteTimeUtc
  if ($mt -gt 0) {
    if ($e.first -eq 0 -or $mt -lt $e.first) { $e.first = $mt }
    if ($mt -gt $e.last) { $e.last = $mt }
  }
}
function Format-InvTime([int64]$t) {
  if ($t -le 0) { return '' }
  return [DateTimeOffset]::FromUnixTimeSeconds($t).UtcDateTime.ToString('yyyy-MM-ddTHH:mm:ssZ', [Globalization.CultureInfo]::InvariantCulture)
}
# Agent lines of one accumulator, as compressed JSON in the documented key order.
function Get-InvLines([string]$user, $acc, [int]$projects) {
  foreach ($agent in @($acc.Keys)) {
    $e = $acc[$agent]
    # A match with no files of its own after exclusions and nested claims gives no line.
    if ($e.files -eq 0) { continue }
    $o = [ordered]@{ type = 'agent'; host = $HostName; user = $user; agent = $agent; files = [int64]$e.files; bytes = [int64]$e.bytes
      first = (Format-InvTime $e.first); last = (Format-InvTime $e.last); projects = $projects; evidence = (@($e.evidence) -join ',') }
    $o | ConvertTo-Json -Compress
  }
}

# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------
function Add-File([string]$user, [string]$homeDir, [string]$agent, $item) {
  if ($Inventory) {
    # Regular files only: reparse points are neither followed nor counted.
    if ((($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -eq 0) -and -not $item.PSIsContainer) { Add-InvFile $agent $item }
    return
  }
  $full = $item.FullName
  $hrel = Get-RelPath $homeDir $full
  $arel = Get-ArchiveRel $full
  $dest = Join-PathSafe $Stage $arel
  $isLink = (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
  $size = [int64]0; if (-not $item.PSIsContainer) { try { $size = [int64]$item.Length } catch { } }
  $mtime = Get-Epoch $item.LastWriteTimeUtc; $atime = Get-Epoch $item.LastAccessTimeUtc; $btime = Get-Epoch $item.CreationTimeUtc
  $owner = Get-OwnerName $full
  $attrs = [string]$item.Attributes
  $secret = Test-AnyMatch $hrel $script:SecretRegexes
  $type = 'file'; $status = 'collected'; $sha = ''; $target = ''; $err = ''
  if ($isLink) {
    $type = 'symlink'; $status = 'symlink'; $target = Get-LinkTarget $item
    $err = Add-StagedLink $item $dest
  } elseif ($secret -and $NoSecrets) {
    $status = 'skipped_secret'
  } elseif ($MaxSize -gt 0 -and $size -gt $MaxSize) {
    $status = 'skipped_size'
  } else {
    try {
      $d = Split-Path -Path $dest -Parent
      if (-not (Test-PathQuiet $d 'Any')) { New-Item -ItemType Directory -Path $d -Force -ErrorAction Stop | Out-Null }
      Copy-FileShared $full $dest
      $sha = Get-FileSha256 $dest
    } catch {
      $status = 'error_copy'; $err = $_.Exception.Message
      Write-CollectorLog "copy failed: ${full}: $err"
      try { if (Test-PathQuiet $dest 'Any') { Remove-Item -LiteralPath $dest -Force } } catch { }
    }
  }
  $apath = ''; if ($status -eq 'collected' -or ($status -eq 'symlink' -and $err -eq '')) { $apath = $arel }
  Write-Row $user $homeDir $agent $full $apath $type $size $mtime $atime 0 $btime $owner $attrs $sha $secret $status $target $err
}

function Add-Excluded([string]$user, [string]$homeDir, [string]$agent, $item) {
  if ($Inventory) { return }
  $full = $item.FullName
  if ($item.PSIsContainer) { $type = 'dir'; $size = Get-DirSize $full } else { $type = 'file'; $size = [int64]0; try { $size = [int64]$item.Length } catch { } }
  Write-Row $user $homeDir $agent $full '' $type $size (Get-Epoch $item.LastWriteTimeUtc) (Get-Epoch $item.LastAccessTimeUtc) 0 (Get-Epoch $item.CreationTimeUtc) '' ([string]$item.Attributes) '' $false 'skipped_excluded' '' ''
}

function Add-Tree([string]$user, [string]$homeDir, [string]$agent, [string]$dir) {
  $children = @()
  try { $children = @(Get-ChildItem -LiteralPath $dir -Force -ErrorAction Stop) }
  catch { $script:WalkErrors++; Write-CollectorLog "list failed: ${dir}: $($_.Exception.Message)"; return }
  foreach ($child in $children) {
    # A path matched by another catalog entry is collected under that entry.
    if ($script:ClaimedPaths.ContainsKey($child.FullName)) { continue }
    $hrel = Get-RelPath $homeDir $child.FullName
    if (Test-AnyMatch $hrel $script:ExcludeRegexes) { Add-Excluded $user $homeDir $agent $child; continue }
    $isLink = (($child.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
    if ($child.PSIsContainer -and -not $isLink) { Add-Tree $user $homeDir $agent $child.FullName }
    else { Add-File $user $homeDir $agent $child }
  }
}

function Add-Path([string]$user, [string]$homeDir, [string]$agent, [string]$path) {
  $item = $null
  try { $item = Get-Item -LiteralPath $path -Force -ErrorAction Stop } catch { $script:WalkErrors++; Write-CollectorLog "stat failed: ${path}: $($_.Exception.Message)"; return }
  $hrel = Get-RelPath $homeDir $path
  if (Test-AnyMatch $hrel $script:ExcludeRegexes) { Add-Excluded $user $homeDir $agent $item; return }
  $isLink = (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
  if ($item.PSIsContainer -and -not $isLink) { Add-Tree $user $homeDir $agent $path } else { Add-File $user $homeDir $agent $item }
}

function Invoke-CatalogCollection([string]$user, [string]$base, [string]$table, [string]$header = '') {
  # Expand every entry first so a nested match (.gemini/antigravity-cli inside
  # .gemini) is attributed to its own agent and collected once; Add-Tree skips
  # children that another entry claimed. $header, when given, is logged once
# before the first match, so a home with no matches leaves no progress line.
  # ($matches would shadow PowerShell's automatic regex variable.)
  $claimed = @()
  $script:ClaimedPaths = @{}
  foreach ($line in (Get-TableLines $table)) {
    $parts = @($line -split '\|', 2)
    if ($parts.Count -lt 2) { continue }
    $agent = $parts[0]; $pattern = $parts[1]
    foreach ($m in @(Expand-Glob $base $pattern)) {
      $claimed += ,@($agent, $m, $pattern)
      $script:ClaimedPaths[$m] = $true
    }
  }
  foreach ($pair in $claimed) {
    $agent = $pair[0]; $m = $pair[1]
    # -Inventory: shared entries still claim their paths above but
    # are not walked; every other match is recorded as evidence.
    if ($Inventory) {
      if ($agent -eq 'shared') { continue }
      Add-InvEvidence $agent $pair[2]
    }
    if ($header) { Write-CollectorLog $header; $header = '' }
    Write-CollectorLog "  [$agent] $m"
    Add-Path $user $base $agent $m
  }
  $script:ClaimedPaths = @{}
}

# ---------------------------------------------------------------------------
# User enumeration -> list of @{ user; home }
# ---------------------------------------------------------------------------
$SkipHomes = @('Public', 'Default', 'Default User', 'All Users', 'Shared', 'defaultuser0')
# Transient Windows service profiles: font driver hosts, desktop window manager, TEMP
$SkipHomeRe = '^(UMFD-\d+|DWM-\d+|TEMP)(\..*)?$'
function Get-UserHomes {
  $homes = @()
  if ($Mode -eq 'live') {
    try {
      foreach ($k in (Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList' -ErrorAction Stop)) {
        $p = (Get-ItemProperty -LiteralPath $k.PSPath -ErrorAction SilentlyContinue).ProfileImagePath
        if ($p) { $p = [Environment]::ExpandEnvironmentVariables($p); $homes += @{ user = (Split-Path -Leaf $p); home = $p } }
      }
    } catch { }
    $drive = $env:SystemDrive; if (-not $drive) { $drive = 'C:' }
    $driveRoot = $drive + $Sep; if ($Sep -eq '/') { $driveRoot = '/' }
    foreach ($g in @('Users/*', 'home/*')) { foreach ($d in (Expand-Glob $driveRoot $g)) { $homes += @{ user = (Split-Path -Leaf $d); home = $d } } }
  } else {
    foreach ($g in @('Users/*', 'home/*', 'root', 'var/root', 'usr/home/*', 'export/home/*')) {
      foreach ($d in (Expand-Glob $Root $g)) { $homes += @{ user = (Split-Path -Leaf $d); home = $d } }
    }
  }
  $wanted = @(); if ($Users -ne '') { $wanted = @($Users -split ',' | Where-Object { $_ -ne '' }) }
  $seen = @{}; $out = @()
  foreach ($h in $homes) {
    $hp = $h.home.TrimEnd('\', '/')
    if ($SkipHomes -contains $h.user -or $h.user -match $SkipHomeRe) { continue }
    if ([System.IO.File]::Exists($hp)) { continue }
    if ($wanted.Count -gt 0 -and -not ($wanted -contains $h.user)) { continue }
    if (-not (Test-PathQuiet $hp 'Container')) { if (-not ($script:InaccessibleHomes -contains $hp)) { $script:InaccessibleHomes += $hp }; continue }
    $key = $hp.ToLowerInvariant()
    if ($seen.ContainsKey($key)) { continue }
    $seen[$key] = $true
    $out += @{ user = $h.user; home = $hp }
  }
  return $out
}

$script:InaccessibleHomes = @()
$UserList = @(Get-UserHomes)

Write-CollectorLog "$TOOL $ToolVersion starting on $HostName ($([Environment]::OSVersion.VersionString), PowerShell $($PSVersionTable.PSVersion)) mode=$Mode root=$(if ($Root) { $Root } else { '\' })"
Write-CollectorLog "archive=$(if ($TarExe) { 'tar.gz via ' + $TarExe } else { 'zip (tar.exe not found)' }) max_file_size=${MaxFileSizeMB}MB full=$($Full.IsPresent) no_secrets=$($NoSecrets.IsPresent) no_docker=$($NoDocker.IsPresent)"
$IsAdmin = $false
try { $IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) } catch { }
if ($Inventory -and $PSBoundParameters.ContainsKey('OutputDir')) { Write-CollectorLog "NOTE: -Inventory writes nothing; -OutputDir $OutputDir ignored" }
if ($Mode -eq 'live' -and -not $IsAdmin) { Write-CollectorLog "WARNING: not running as Administrator; other users' profiles will probably be unreadable" }
if ($UserList.Count -eq 0) { Write-CollectorLog 'WARNING: no user profile directories found' }
foreach ($ih in $script:InaccessibleHomes) { Write-CollectorLog "profile not accessible (skipped): $ih" }

# ---------------------------------------------------------------------------
# Per-user collection
# ---------------------------------------------------------------------------
$script:InvUsers = @()
foreach ($u in $UserList) {
  $script:Inv = [ordered]@{}
  Invoke-CatalogCollection $u.user $u.home $CATALOG "User $($u.user) ($($u.home))"
  if ($Inventory) { $script:InvUsers += , @($u, $script:Inv) }
}

# ---------------------------------------------------------------------------
# Docker and Podman named volumes, enumerated from the filesystem as in the sh
# collector: <volumes dir>/<name>/_data. A volume whose name matches
# DOCKER_VOLUMES is collected whole as user "docker" with _data as its home;
# any other volume gets one skipped_unmatched_volume row with its size. This
# reaches Linux data roots in an image (or under PowerShell 7 on Linux) and
# Windows-container volumes under ProgramData\Docker. Docker Desktop keeps
# Linux volumes inside a WSL virtual disk, which is only noted. Failures are
# noted in collection.json and the summary and never stop the collection.
# ---------------------------------------------------------------------------
$script:Notes = @()
$script:Docker = @{ seen = $false; found = 0; collected = 0; unreadable = 0; desktop = $false }
function Add-Note([string]$msg) { $script:Notes += $msg; Write-CollectorLog "NOTE: $msg" }
$script:DockerVolumeRules = @()
foreach ($line in (Get-TableLines $DOCKER_VOLUMES)) {
  $parts = @($line -split '\|', 2)
  if ($parts.Count -lt 2) { continue }
  $script:DockerVolumeRules += , @($parts[0], (Convert-GlobToRegex $parts[1] $false), $parts[1])
}
$script:InvDocker = [ordered]@{}
# The first DOCKER_VOLUMES rule (agent, regex, glob) whose glob matches, or $null.
function Get-DockerVolumeRule([string]$name) {
  # Volume names are case-sensitive, as in the sh collector's case(1) match.
  foreach ($rule in $script:DockerVolumeRules) { if ($name -cmatch $rule[1]) { return , $rule } }
  return $null
}
function Test-IsLink([string]$p) {
  try {
    $it = Get-Item -LiteralPath $p -Force -ErrorAction Stop
    return (($it.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
  } catch { return $false }
}
function Test-DirReadable([string]$p) {
  try { [void][System.IO.Directory]::GetFileSystemEntries($p); return $true } catch { return $false }
}
# Each component of $rel is checked on the way down, so a data root the
# responder cannot enter, or a symlinked one, is reported rather than skipped.
function Invoke-VolumeDir([string]$base, [string]$rel) {
  $vd = $base
  $segs = @($rel -split '/')
  for ($i = 0; $i -lt $segs.Count; $i++) {
    $vd = Join-PathSafe $vd $segs[$i]
    if (Test-IsLink $vd) {
      $script:Docker.seen = $true
      Add-Note "docker: $vd is a symlink and was not followed; collect its target by hand"
      return
    }
    if (-not (Test-PathQuiet $vd 'Container')) { return }
    $last = ($i -eq $segs.Count - 1)
    # A directory that cannot be listed may still be searchable; go on when
    # the next component is visible, as the sh collector's -x test would.
    if (-not (Test-DirReadable $vd) -and ($last -or -not (Test-PathQuiet (Join-PathSafe $vd $segs[$i + 1]) 'Container'))) {
      $script:Docker.seen = $true; $script:Docker.unreadable++
      Add-Note "docker: $vd is not readable; run as root to collect the volumes under it"
      return
    }
  }
  $script:Docker.seen = $true
  $children = @(Get-ChildItem -LiteralPath $vd -Force -ErrorAction SilentlyContinue)
  Write-CollectorLog "Docker volumes in $vd"
  foreach ($v in $children) {
    if (-not $v.PSIsContainer) { continue }
    if (($v.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { continue }
    $script:Docker.found++
    $name = $v.Name
    $data = Join-PathSafe $v.FullName '_data'
    $rule = Get-DockerVolumeRule $name
    $agent = ''; if ($rule) { $agent = $rule[0] }
    $label = $agent; if (-not $label) { $label = 'unmatched' }
    if (-not (Test-DirReadable $v.FullName) -or ((Test-PathQuiet $data 'Container') -and -not (Test-DirReadable $data))) {
      $script:Docker.unreadable++
      Add-Note "docker: volume $name ($label) at $($v.FullName) is not readable; run as root to collect it"
    } elseif ((Test-IsLink $data) -or -not (Test-PathQuiet $data 'Container')) {
      Write-CollectorLog "  volume $name has no _data directory, skipped"
    } elseif (-not $agent -and $Inventory) {
    } elseif (-not $agent) {
      $attrs = ''; try { $attrs = [string](Get-Item -LiteralPath $data -Force -ErrorAction Stop).Attributes } catch { }
      Write-Row 'docker' $data '' $data '' 'dir' (Get-DirSize $data) 0 0 0 0 '' $attrs '' $false 'skipped_unmatched_volume' '' ''
    } else {
      Write-CollectorLog "  [$agent] $data"
      $script:WalkErrors = 0
      $script:ClaimedPaths = @{}
      if ($Inventory) {
        $saved = $script:Inv; $script:Inv = $script:InvDocker
        Add-InvEvidence $agent $rule[2]
        Add-Path 'docker' $data $agent $data
        $script:Inv = $saved
      } else {
        Add-Path 'docker' $data $agent $data
      }
      $script:Docker.collected++
      if ($script:WalkErrors -gt 0) {
        $script:Docker.unreadable++
        Add-Note "docker: volume $name ($agent) could not be walked completely ($($script:WalkErrors) unreadable paths, see collector.log); run as root to collect it"
      }
    }
  }
}

if (-not $NoDocker) {
  if ($Mode -eq 'image') { $dockerBase = $Root }
  elseif ($Sep -eq '/') { $dockerBase = '/' }
  else { $dockerBase = $env:SystemDrive; if (-not $dockerBase) { $dockerBase = 'C:' }; $dockerBase += $Sep }
  $programData = Join-PathSafe $dockerBase 'ProgramData'
  if ($Mode -eq 'live' -and $env:ProgramData) { $programData = $env:ProgramData }
  # Root Docker, root Podman and Windows-container Docker data roots, then the
  # rootless Docker and Podman roots of each (selected) user.
  Invoke-VolumeDir (Join-PathSafe $dockerBase 'var/lib') 'docker/volumes'
  Invoke-VolumeDir (Join-PathSafe $dockerBase 'var/lib') 'containers/storage/volumes'
  Invoke-VolumeDir $programData 'Docker/volumes'
  $desktopDirs = @(Join-PathSafe $programData 'DockerDesktop')
  foreach ($u in $UserList) {
    Invoke-VolumeDir (Join-PathSafe $u.home '.local/share') 'docker/volumes'
    Invoke-VolumeDir (Join-PathSafe $u.home '.local/share') 'containers/storage/volumes'
    $desktopDirs += (Join-PathSafe $u.home 'Library/Containers/com.docker.docker')
    $desktopDirs += (Join-PathSafe $u.home 'AppData/Local/Docker')
  }
  # Docker Desktop keeps Linux volumes inside a VM disk that no file walk reaches.
  foreach ($dd in $desktopDirs) {
    if ((Test-PathQuiet $dd 'Container') -and -not (Test-IsLink $dd)) {
      $script:Docker.seen = $true; $script:Docker.desktop = $true
      Add-Note "docker: Docker Desktop data at $dd; volumes inside its virtual machine disk are not collected"
    }
  }
}

# ---------------------------------------------------------------------------
# Project discovery: plain-text sources only, same list as the sh script.
# ---------------------------------------------------------------------------
function ConvertTo-LocalPath([string]$v) {
  $v = $v.Trim()
  if ($v -eq '') { return $null }
  if ($v.StartsWith('file://')) {
    $v = $v.Substring(7); try { $v = [uri]::UnescapeDataString($v) } catch { }
    # file:///c:/x is a drive path; file:///home/x keeps its leading slash
    if ($v -match '^/[A-Za-z]:') { $v = $v.Substring(1) }
  }
  $v = $v.Replace('\\', '\').Replace('\/', '/')
  if ($v -match '^[A-Za-z]:[\\/]') {
    $v = $v.Substring(0, 1).ToUpper() + $v.Substring(1).Replace('/', $Sep).Replace('\', $Sep)
    if ($Mode -eq 'image') { return $Root + $v.Substring(2) }
    return $v
  }
  if ($v.StartsWith('/')) {
    if ($Mode -eq 'image') { return $Root + $v.Replace('/', $Sep) }
    if ($Sep -eq '/') { return $v }
    return $null
  }
  return $null
}
# -Inventory never opens a credential file: a discovery source whose path
# relative to the home being scanned matches SECRET_GLOBS (.claude.json, the
# OpenClaw and nanobot configs, Tabby's config.toml) is skipped in that mode.
$script:DiscoveryHome = ''
function Test-InventorySecret([string]$f) {
  if (-not $Inventory -or -not $script:DiscoveryHome) { return $false }
  return (Test-AnyMatch (Get-RelPath $script:DiscoveryHome $f) $script:SecretRegexes)
}
function Get-JsonValues([string]$key, [string[]]$files) {
  $rx = '"' + [regex]::Escape($key) + '"\s*:\s*"((?:[^"\\]|\\.)*)"'
  foreach ($f in $files) {
    if (-not $f -or -not (Test-PathQuiet $f 'Leaf')) { continue }
    if (Test-InventorySecret $f) { continue }
    try { foreach ($m in [regex]::Matches([System.IO.File]::ReadAllText($f), $rx)) { $m.Groups[1].Value } } catch { }
  }
}
function Get-JsonKeys([string]$suffix, [string[]]$files) {
  $rx = '"([A-Za-z]:(?:[^"\\]|\\.)*|/(?:[^"\\]|\\.)*)"\s*:\s*' + $suffix
  foreach ($f in $files) {
    if (-not $f -or -not (Test-PathQuiet $f 'Leaf')) { continue }
    if (Test-InventorySecret $f) { continue }
    try { foreach ($m in [regex]::Matches([System.IO.File]::ReadAllText($f), $rx)) { $m.Groups[1].Value } } catch { }
  }
}
function Get-PathStrings([string[]]$files) {
  # every quoted absolute path, drive-letter path or file:// URI in the files
  $rx = '"((?:file:///|/|[A-Za-z]:\\\\)(?:[^"\\]|\\.)*)"'
  foreach ($f in $files) {
    if (-not $f -or -not (Test-PathQuiet $f 'Leaf')) { continue }
    if (Test-InventorySecret $f) { continue }
    try { foreach ($m in [regex]::Matches([System.IO.File]::ReadAllText($f), $rx)) { $m.Groups[1].Value } } catch { }
  }
}
function Get-YamlValues([string]$key, [string[]]$files) {
  $rx = '(?m)^' + [regex]::Escape($key) + ':[ \t]*["'']?([^"''\r\n]+)["'']?[ \t]*$'
  foreach ($f in $files) {
    if (-not $f -or -not (Test-PathQuiet $f 'Leaf')) { continue }
    if (Test-InventorySecret $f) { continue }
    try { foreach ($m in [regex]::Matches([System.IO.File]::ReadAllText($f), $rx)) { $m.Groups[1].Value } } catch { }
  }
}
function Get-Json5Values([string]$key, [string[]]$files) {
  # JSON5 allows unquoted keys and single-quoted strings (OpenClaw config)
  $rx = '(?<![\w$])["'']?' + [regex]::Escape($key) + '["'']?\s*:\s*(?:"((?:[^"\\]|\\.)*)"|''([^'']*)'')'
  foreach ($f in $files) {
    if (-not $f -or -not (Test-PathQuiet $f 'Leaf')) { continue }
    if (Test-InventorySecret $f) { continue }
    try {
      foreach ($m in [regex]::Matches([System.IO.File]::ReadAllText($f), $rx)) {
        if ($m.Groups[1].Success) { $m.Groups[1].Value } else { $m.Groups[2].Value }
      }
    } catch { }
  }
}
function Get-TomlFileUrls([string]$key, [string[]]$files) {
  # key = "file://..." lines (Tabby repositories)
  $rx = '(?m)^[ \t]*' + [regex]::Escape($key) + '[ \t]*=[ \t]*["''](file://[^"''\r\n]*)["'']'
  foreach ($f in $files) {
    if (-not $f -or -not (Test-PathQuiet $f 'Leaf')) { continue }
    if (Test-InventorySecret $f) { continue }
    try { foreach ($m in [regex]::Matches([System.IO.File]::ReadAllText($f), $rx)) { $m.Groups[1].Value } } catch { }
  }
}
function Get-CommonDir([string[]]$paths) {
  # deepest directory shared by absolute file paths (Twinny records indexed
  # files, not the workspace root); returned in the raw form for ConvertTo-LocalPath
  $common = $null
  foreach ($v in $paths) {
    $s = ([string]$v).Replace('\\', '\').Replace('\/', '/')
    if ($s.StartsWith('file://')) { continue }
    $parts = @($s -split '[\\/]')
    if ($parts.Count -lt 3) { continue }
    $parts = @($parts[0..($parts.Count - 2)])
    if ($null -eq $common) { $common = $parts; continue }
    $n = [Math]::Min($common.Count, $parts.Count); $k = 0
    while ($k -lt $n -and $common[$k] -eq $parts[$k]) { $k++ }
    if ($k -eq 0) { $common = @() } else { $common = @($common[0..($k - 1)]) }
  }
  if ($null -eq $common -or $common.Count -lt 2) { return $null }
  return ($common -join '/')
}
function Find-Projects {
  $found = @()
  foreach ($u in $UserList) {
    $h = $u.home
    $script:DiscoveryHome = $h
    $vals = @()
    $vals += Get-JsonValues 'project' @((Join-PathSafe $h '.claude/history.jsonl'))
    $vals += Get-JsonKeys '\{' @((Join-PathSafe $h '.claude.json'))
    # config homes moved with CLAUDE_CONFIG_DIR keep .claude.json inside
    $vals += Get-JsonValues 'project' @(Expand-Glob $h '.claude-*/history.jsonl')
    $vals += Get-JsonKeys '\{' @(Expand-Glob $h '.claude-*/.claude.json')
    $vals += Get-JsonValues 'cwd' @(Expand-Glob $h '.codex/sessions/*/*/*/*.jsonl')
    $vals += Get-JsonValues 'cwd' @(Expand-Glob $h '.qwen/projects/*/chats/*.jsonl')
    $vals += Get-JsonValues 'cwd' @(Expand-Glob $h '.cline/data/sessions/*/*.json')
    $vals += Get-JsonValues 'workspace_root' @(Expand-Glob $h '.cline/data/sessions/*/*.json')
    $vals += Get-JsonValues 'cwd' @(Expand-Glob $h '.cursor/chats/*/*/meta.json')
    $vals += Get-JsonValues 'workspaceDirectory' @((Join-PathSafe $h '.continue/sessions/sessions.json'))
    $vals += Get-JsonValues 'working_dir' @(Expand-Glob $h '.local/share/goose/sessions/*.jsonl')
    $vals += Get-JsonValues 'worktree' @(Expand-Glob $h '.local/share/opencode/storage/project/*.json')
    $vals += Get-JsonValues 'path' @((Join-PathSafe $h '.local/share/crush/projects.json'))
    $vals += Get-JsonKeys '"' @((Join-PathSafe $h '.gemini/projects.json'))
    $vals += Get-JsonKeys '"' @((Join-PathSafe $h '.gemini/trustedFolders.json'))
    foreach ($pr in (@(Expand-Glob $h '.gemini/tmp/*/.project_root') + @(Expand-Glob $h '.gemini/history/*/.project_root'))) { try { $vals += [System.IO.File]::ReadAllText($pr) } catch { } }
    $vals += Get-JsonValues 'workspace' @((Join-PathSafe $h '.gemini/antigravity-cli/history.jsonl'))
    $vals += Get-PathStrings (@((Join-PathSafe $h '.gemini/antigravity-cli/settings.json'), (Join-PathSafe $h '.gemini/antigravity-cli/cache/projects.json')) + @(Expand-Glob $h '.gemini/config/projects/*.json'))
    $vals += Get-JsonValues 'cwd' (@((Join-PathSafe $h '.local/share/amp/history.jsonl')) + @(Expand-Glob $h '.factory/sessions/*/*.jsonl') + @(Expand-Glob $h '.factory/sessions/*.jsonl') + @(Expand-Glob $h '.kiro/sessions/cli/*.json') + @(Expand-Glob $h '.cursor/acp-sessions/*/meta.json'))
    $vals += Get-JsonValues 'root' @(Expand-Glob $h '.kiro/workspace-roots/*/.trust-migration.json')
    $vals += Get-PathStrings (@(Expand-Glob $h '.kiro/sessions/*/sess_*/session.json') + @((Join-PathSafe $h '.config/Goose/recent-dirs.json'), (Join-PathSafe $h 'Library/Application Support/Goose/recent-dirs.json'), (Join-PathSafe $h 'AppData/Roaming/Goose/recent-dirs.json')))
    $vals += Get-YamlValues 'cwd' @(Expand-Glob $h '.copilot/session-state/*/workspace.yaml')
    $vals += Get-JsonValues 'workdir' (@(Expand-Glob $h '.hermes/checkpoints/store/projects/*.json') + @(Expand-Glob $h '.hermes/profiles/*/checkpoints/store/projects/*.json') + @(Expand-Glob $h 'AppData/Local/hermes/checkpoints/store/projects/*.json') + @(Expand-Glob $h 'AppData/Local/hermes/profiles/*/checkpoints/store/projects/*.json'))
    $vals += Get-JsonValues 'project' @((Join-PathSafe $h '.letta/sessions.jsonl'))
    $vals += Get-JsonValues 'cwd' (@(Expand-Glob $h '.letta/lc-local-backend/conversations/*/messages.jsonl') + @(Expand-Glob $h '.pi/agent/sessions/*/*.jsonl') + @(Expand-Glob $h '.pi/agent/*.jsonl') + @((Join-PathSafe $h '.pi/agent/crashes.json')) + @(Expand-Glob $h '.pi/agent/experimental/sessions/*/meta.json'))
    $vals += Get-JsonKeys '(?:true|false)' @((Join-PathSafe $h '.pi/agent/trust.json'))
    $vals += Get-JsonKeys '\{' @((Join-PathSafe $h '.config/muse/trust.json'))
    $vals += Get-JsonValues 'workspace_root' @(Expand-Glob $h '.local/share/muse/sessions/*/*/*/*/session.jsonl')
    $vals += Get-JsonValues 'cwd' (@(Expand-Glob $h '.openinterpreter/sessions/*/*/*/rollout-*.jsonl') + @(Expand-Glob $h '.openinterpreter/archived_sessions/rollout-*.jsonl') + @(Expand-Glob $h '.openinterpreter/archived_sessions/*/*/*/rollout-*.jsonl'))
    $vals += Get-JsonValues 'path' @((Join-PathSafe $h '.openhands/workspaces.json'))
    $vals += Get-JsonValues 'working_dir' (@(Expand-Glob $h '.openhands/agent-canvas/dev_conversations/*/meta.json') + @(Expand-Glob $h '.openhands/agent-canvas/conversations/*/meta.json') + @(Expand-Glob $h '.openhands/conversations/*/base_state.json'))
    $vals += Get-JsonValues 'workspaceDirectory' @((Join-PathSafe $h '.pearai/sessions/sessions.json'))
    $oc = @(Expand-Glob $h '.openclaw*/openclaw.json') + @((Join-PathSafe $h '.clawdbot/clawdbot.json'))
    $vals += Get-Json5Values 'workspace' $oc
    $vals += Get-Json5Values 'agentDir' $oc
    foreach ($nw in @(Expand-Glob $h '.nanobot*/sessions/*/.workspace')) { try { $vals += [System.IO.File]::ReadAllText($nw) } catch { } }
    $vals += Get-JsonValues 'workspace' @(Expand-Glob $h '.nanobot*/config.json')
    $vals += Get-TomlFileUrls 'git_url' @((Join-PathSafe $h '.tabby/config.toml'))
    foreach ($tm in @(Expand-Glob $h '.twinny/embeddings/*/manifest.json')) { $cd = Get-CommonDir @(Get-PathStrings @($tm)); if ($cd) { $vals += $cd } }
    foreach ($ws in (@(Expand-Glob $h 'AppData/Roaming/*/User') + @(Expand-Glob $h '.config/*/User') + @(Expand-Glob $h 'Library/Application Support/*/User') + @(Expand-Glob $h '.*-server*/data/User'))) {
      $vals += Get-JsonValues 'folder' @(Expand-Glob $ws 'workspaceStorage/*/workspace.json')
      $vals += Get-JsonValues 'cwdOnTaskInitialization' (@(Expand-Glob $ws 'globalStorage/saoudrizwan.claude-dev/state/taskHistory.json') + @(Expand-Glob $ws 'globalStorage/saoudrizwan.claude-dev/tasks/*/task_metadata.json'))
      $vals += Get-JsonValues 'workspace' (@(Expand-Glob $ws 'globalStorage/rooveterinaryinc.roo-cline/tasks/_index.json') + @(Expand-Glob $ws 'globalStorage/kilocode.kilo-code/tasks/_index.json'))
    }
    $script:DiscoveryHome = ''
    foreach ($v in $vals) {
      $lp = ConvertTo-LocalPath ([string]$v)
      if ($lp) { $found += @{ user = $u.user; path = $lp.TrimEnd('\', '/') } }
    }
  }
  foreach ($p in $Project) {
    $owner = ''
    foreach ($u in $UserList) { if ($p.StartsWith($u.home + $Sep, [System.StringComparison]::OrdinalIgnoreCase)) { $owner = $u.user; break } }
    $found += @{ user = $owner; path = $p.TrimEnd('\', '/') }
  }
  $seen = @{}; $out = @()
  $homeKeys = @{}; foreach ($u in $UserList) { $homeKeys[$u.home.ToLowerInvariant()] = $true }
  foreach ($f in $found) {
    $key = $f.path.ToLowerInvariant()
    if ($seen.ContainsKey($key)) { if ($seen[$key].user -eq '' -and $f.user -ne '') { $seen[$key].user = $f.user }; continue }
    if ($homeKeys.ContainsKey($key)) { continue }
    if (-not (Test-PathQuiet $f.path 'Container')) { continue }
    $seen[$key] = $f; $out += $f
  }
  return $out
}

$ProjectList = @()
if (-not $NoProjects) {
  $ProjectList = @(Find-Projects)
  if (-not $Inventory) { foreach ($pj in $ProjectList) {
    Write-CollectorLog "Project $(if ($pj.user) { '[' + $pj.user + '] ' })$($pj.path)"
    Invoke-CatalogCollection $pj.user $pj.path $PROJECT_CATALOG
  } }
}

# ---------------------------------------------------------------------------
# Inventory output: the host line, then one line per (user, agent), then the
# Docker volume agents as user docker. Nothing is written to disk.
# ---------------------------------------------------------------------------
if ($Inventory) {
  # A home is unreadable when .NET reports it missing although its parent
  # directory lists it (access denied; a ProfileList entry for a deleted
  # profile is not counted), or when its entries cannot be listed.
  $denied = @($script:InaccessibleHomes | Where-Object {
    $leaf = Split-Path -Leaf $_; $parent = Split-Path -Parent $_
    try { @([System.IO.Directory]::GetDirectories($parent, $leaf)).Count -gt 0 } catch { $false } })
  $unreadable = $denied.Count
  foreach ($u in $UserList) { if (-not (Test-DirReadable $u.home)) { $unreadable++; Write-CollectorLog "WARNING: home of $($u.user) is not readable: $($u.home)" } }
  $hostLine = [ordered]@{ type = 'host'; host = $HostName; collector = $ToolVersion; mode = $Mode; at = $StartTs
    users_scanned = ($UserList.Count + $denied.Count); users_unreadable = $unreadable; docker_volumes = $script:Docker.found }
  Write-Output ($hostLine | ConvertTo-Json -Compress)
  foreach ($pair in $script:InvUsers) {
    $u = $pair[0]
    $np = @($ProjectList | Where-Object { $_.user -eq $u.user }).Count
    Get-InvLines $u.user $pair[1] $np
  }
  Get-InvLines 'docker' $script:InvDocker 0
  exit 0
}

# ---------------------------------------------------------------------------
# Summary, archive, hashes
# ---------------------------------------------------------------------------
$EndTs = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
# Users whose home gave at least one manifest row, in enumeration order
$ActiveUsers = @($UserList | Where-Object { $script:RowHomes.ContainsKey($_.home) })
# 512 -> "512 B", 21868755 -> "20.9 MiB"
function Format-HumanSize([int64]$bytes) {
  $units = @('B', 'KiB', 'MiB', 'GiB', 'TiB')
  $v = [double]$bytes; $i = 0
  while ($v -ge 1024 -and $i -lt 4) { $v /= 1024; $i++ }
  if ($i -eq 0) { return "$bytes B" }
  return $v.ToString('0.0', [Globalization.CultureInfo]::InvariantCulture) + ' ' + $units[$i]
}
if ($script:LinkCounts.zip -gt 0) { Add-Note "$($script:LinkCounts.zip) symlinks are in the manifest only: the zip archive cannot store symlinks" }
if ($script:LinkCounts.failed -gt 0) { Add-Note "$($script:LinkCounts.failed) symlinks could not be recreated in the archive; each row's error says why" }
$summary = [ordered]@{
  tool = $TOOL; version = $ToolVersion; hostname = $HostName; mode = $Mode
  root = $(if ($Root) { $Root } else { '\' })
  platform = "Windows $([Environment]::OSVersion.Version) $env:PROCESSOR_ARCHITECTURE PowerShell $($PSVersionTable.PSVersion)"
  run_as = $(try { [Security.Principal.WindowsIdentity]::GetCurrent().Name } catch { [Environment]::UserDomainName + '\' + [Environment]::UserName })
  run_as_admin = $IsAdmin
  started = $StartTs; finished = $EndTs
  options = [ordered]@{ full = $Full.IsPresent; no_secrets = $NoSecrets.IsPresent; max_file_size_bytes = $MaxSize; users_filter = $Users; no_docker = $NoDocker.IsPresent }
  capabilities = [ordered]@{ hash_tool = 'Get-FileHash'; archiver = $(if ($TarExe) { 'tar.exe' } else { 'ZipFile' }) }
  users = @($UserList | ForEach-Object { $_.user })
  homes = @($UserList | ForEach-Object { $_.home })
  users_with_artifacts = @($ActiveUsers | ForEach-Object { $_.user })
  projects = @($ProjectList | ForEach-Object { $_.path })
  counts = [ordered]@{ collected = $script:Counts.collected; symlink = $script:Counts.symlink; skipped_excluded = $script:Counts.skipped_excluded; skipped_size = $script:Counts.skipped_size; skipped_secret = $script:Counts.skipped_secret; error_copy = $script:Counts.error_copy; skipped_unmatched_volume = $script:Counts.skipped_unmatched_volume; collected_bytes = $script:Counts.bytes }
  docker = [ordered]@{ volumes_found = $script:Docker.found; volumes_collected = $script:Docker.collected; unreadable = $script:Docker.unreadable; docker_desktop = $script:Docker.desktop }
  notes = @($script:Notes)
  archive = (Split-Path -Leaf $Archive)
}
[System.IO.File]::WriteAllText($SummaryPath, ($summary | ConvertTo-Json -Depth 4), $Utf8NoBom)

Write-CollectorLog 'Archiving'
$script:ManifestWriter.Close()
$script:LogWriter.Close()
Copy-Item -LiteralPath $ManifestPath -Destination (Join-PathSafe $Stage 'manifest.jsonl') -Force
Copy-Item -LiteralPath $SummaryPath -Destination (Join-PathSafe $Stage 'collection.json') -Force
Copy-Item -LiteralPath $LogPath -Destination (Join-PathSafe $Stage 'collector.log') -Force

if (Test-PathQuiet $Archive 'Any') { Remove-Item -LiteralPath $Archive -Force }
$archiveOk = $false
if ($TarExe) {
  & $TarExe -czf $Archive -C $Stage . 2>>$LogPath
  if ($LASTEXITCODE -eq 0 -and (Test-PathQuiet $Archive 'Any')) { $archiveOk = $true }
}
if (-not $archiveOk) {
  try {
    if (Test-PathQuiet $Archive 'Any') { Remove-Item -LiteralPath $Archive -Force }
    # ZipFile would follow the staged links, so they go first, and the
    # manifest and summary are rewritten to say they are not in the archive.
    if ($script:StagedLinks.Count -gt 0) {
      $nl = $script:StagedLinks.Count
      if ((Clear-StagedLinks) -gt 0) { throw 'staged symlinks could not be removed; not zipping through them' }
      Clear-LinkArchivePaths 'not in the archive: tar failed and zip cannot store symlinks'
      $script:Notes += "tar failed; $nl symlinks were removed from the staging tree before zipping, because zip cannot store symlinks"
      [System.IO.File]::AppendAllText($LogPath, "NOTE: tar failed; $nl staged symlinks removed before zipping`n", $Utf8NoBom)
      $summary.notes = @($script:Notes)
      [System.IO.File]::WriteAllText($SummaryPath, ($summary | ConvertTo-Json -Depth 4), $Utf8NoBom)
      Copy-Item -LiteralPath $ManifestPath -Destination (Join-PathSafe $Stage 'manifest.jsonl') -Force
      Copy-Item -LiteralPath $SummaryPath -Destination (Join-PathSafe $Stage 'collection.json') -Force
      Copy-Item -LiteralPath $LogPath -Destination (Join-PathSafe $Stage 'collector.log') -Force
    }
    $Archive = Join-PathSafe $OutputDir "$Name.zip"
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($Stage, $Archive, [System.IO.Compression.CompressionLevel]::Optimal, $false)
    $archiveOk = (Test-PathQuiet $Archive 'Any')
  } catch { [System.IO.File]::AppendAllText($LogPath, "FATAL: archive failed: $($_.Exception.Message)`n", $Utf8NoBom) }
}
if (-not $archiveOk) { Write-Error 'FATAL: archive not written'; exit 2 }

$ArchiveSha = Get-FileSha256 $Archive
$ArchiveSize = (Get-Item -LiteralPath $Archive).Length
[System.IO.File]::WriteAllText("$Archive.sha256", "$ArchiveSha  $(Split-Path -Leaf $Archive)`n", $Utf8NoBom)
[System.IO.File]::AppendAllText($LogPath, "$EndTs done: $Archive ($ArchiveSize bytes, sha256 $ArchiveSha)`n", $Utf8NoBom)
# The archive's size and hash follow on stdout, so stderr gets only "done".
if (-not $Quiet) { [Console]::Error.WriteLine('done') }

if (-not $KeepStaging) {
  # A link that could not be deleted keeps the staging directory, which the log names.
  if ((Clear-StagedLinks) -eq 0) { try { Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction Stop } catch { } }
  else { [System.IO.File]::AppendAllText($LogPath, "staging directory kept because a staged link could not be removed: $Stage`n", $Utf8NoBom) }
}

$c = $script:Counts
Write-Output "archive:    $Archive"
Write-Output "size:       $ArchiveSize ($(Format-HumanSize $ArchiveSize))"
Write-Output "sha256:     $ArchiveSha"
Write-Output "manifest:   $ManifestPath"
Write-Output "summary:    $SummaryPath"
Write-Output "log:        $LogPath"
Write-Output "users:      $($ActiveUsers.Count)"
Write-Output "projects:   $($ProjectList.Count)"
Write-Output "collected:  $($c.collected) files, $($c.bytes) bytes ($(Format-HumanSize $c.bytes))"
Write-Output "skipped:    $($c.skipped_excluded) excluded, $($c.skipped_size) too large, $($c.skipped_secret) secret"
Write-Output "errors:     $($c.error_copy)"
if ($script:Docker.seen) {
  $dl = "docker:     $($script:Docker.found) volumes found, $($script:Docker.collected) collected, $($script:Docker.unreadable) unreadable"
  if ($script:Docker.unreadable -gt 0) { $dl += ' (run as root to collect)' }
  if ($script:Docker.desktop) { $dl += '; Docker Desktop VM disk not collected' }
  Write-Output $dl
}
exit 0
