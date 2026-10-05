#!/bin/sh
# collect-agent-artifacts.sh - forensic collector for AI coding agent artifacts
#
# Copyright 2026 Sean Whalen
# SPDX-License-Identifier: Apache-2.0
# Licensed under the Apache License, Version 2.0; see the LICENSE file.
#
# Collects the on-disk state of AI coding agents (Claude Code, Gemini CLI,
# Antigravity, Codex CLI, Copilot CLI, Cursor, Windsurf, Continue, Aider,
# Ollama, ...) for every user on a host, from Docker and Podman named
# volumes, plus shell histories, into a single tar.gz with a JSONL manifest.
# Host state (processes, users, network) is left to the EDR it supplements.
#
# Portability: POSIX sh only. Runs under bash 3.2 (macOS /bin/sh), dash,
# ash/busybox, FreeBSD/OpenBSD sh and zsh in sh emulation. External tools used:
# find, cp, tar, gzip, du, awk, grep, sed, sort, cut, readlink, mkdir, rm,
# and one of sha256sum / shasum / sha256 / openssl.
#
# Modes:
#   live   (default)   collect from the running system
#   image  (-r ROOT)   collect from a mounted disk image / alternate root
# Either mode with --inventory writes nothing: it walks the catalog with lstat
# only and prints one JSON line per (user, agent) found to stdout.
#
# Exit codes: 0 archive written (per-file errors are recorded in the manifest),
#               or, with --inventory, the walk ran,
#             1 usage error, 2 fatal (no output dir, no tar, ...).

VERSION="1.7.0"
TOOL="collect-agent-artifacts"

LC_ALL=C
export LC_ALL
PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:$PATH"
export PATH
umask 077

# ---------------------------------------------------------------------------
# Artifact catalog. One entry per line: agent|path-glob (relative to each home
# directory). Every entry is tried for every home, so platform-specific paths
# are harmless on other platforms and a Windows image mounted on Linux works.
# ---------------------------------------------------------------------------
CATALOG='
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
# Shared cross-agent directories (skills, instructions, env files read by several agents)
shared|.agents
shared|.config/AGENTS.md
shared|.config/agents
shared|.env
# Ollama
ollama|.ollama
ollama|Library/Application Support/Ollama
ollama|AppData/Local/Ollama
# Shell history
shell-history|.bash_history
shell-history|.zsh_history
shell-history|.zsh_sessions
shell-history|.sh_history
shell-history|.history
shell-history|.local/share/fish/fish_history
shell-history|.config/fish/fish_history
shell-history|AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt
shell-history|.local/share/powershell/PSReadLine/ConsoleHost_history.txt
shell-history|.bash_sessions
'

# Project-level artifacts, relative to each discovered project directory.
PROJECT_CATALOG='
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
project|.env
'

# Paths (globs relative to home, project dir or Docker volume _data) skipped
# unless --full. Volume-relative forms of a tool's exclusions follow the
# home-relative ones at the end of the table. They are
# recorded in the manifest as skipped_excluded with their size. find(1) -path
# semantics: * also matches /.
EXCLUDES='
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
'

# Files holding credentials. Collected by default and flagged secret=true in
# the manifest; skipped with --no-secrets. Matched with case(1) globs against
# the path relative to the home, project or Docker volume _data directory;
# * also matches /. Volume-relative forms come last.
SECRET_GLOBS='.claude/.credentials.json
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
matrix-store/*'

# Docker and Podman named volumes, agent|glob matched against the volume name.
DOCKER_VOLUMES='
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
'


# ---------------------------------------------------------------------------
# Shared helper functions. Defined as a string so they can be eval'd here and
# prepended to the programs run by find -exec sh -c (which cannot inherit
# shell functions portably).
# ---------------------------------------------------------------------------
# heredoc_var: reads stdin into $_hv without its final newline, which is what
# VAR=$(cat <<'EOF' ...) gives. Used instead of that form because pdksh-derived
# shells (posh) scan a heredoc inside $(...) for parentheses and stop at the
# first case pattern's `)`.
heredoc_var() {
  _hv=
  while IFS= read -r _hv_l; do _hv="$_hv$_hv_l
"; done
  _hv=${_hv%?}
}
heredoc_var <<'EOF_COMMON'
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log_line() {
  printf '%s %s\n' "$(ts)" "$*" >>"$LOG"
  [ "${QUIET:-0}" = 1 ] || printf '%s\n' "$*" >&2
}
hash_file() {
  case "$HASH_TOOL" in
    sha256sum) sha256sum <"$1" 2>/dev/null | cut -d' ' -f1 ;;
    shasum)    shasum -a 256 <"$1" 2>/dev/null | cut -d' ' -f1 ;;
    sha256)    sha256 -q <"$1" 2>/dev/null ;;
    openssl)   openssl dgst -sha256 -r <"$1" 2>/dev/null | cut -d' ' -f1 ;;
    *)         printf '' ;;
  esac
}
# prints: size mtime atime ctime btime uid gid mode (lstat semantics)
stat_file() {
  case "$STAT_MODE" in
    gnu)  stat -c '%s %Y %X %Z %W %u %g %a' "$1" 2>/dev/null ;;
    gnu0) stat -c '%s %Y %X %Z 0 %u %g %a' "$1" 2>/dev/null ;;
    bsd)  stat -f '%z %m %a %c %B %u %g %Lp' "$1" 2>/dev/null ;;
    *)    printf '%s 0 0 0 0 0 0 0\n' "$(wc -c <"$1" 2>/dev/null | tr -d ' ')" ;;
  esac
}
_jt=$(printf '\t'); _jr=$(printf '\r'); _jn='
'
json_str() {
  case "$1" in
    *\\*|*'"'*|*"$_jt"*|*"$_jr"*|*"$_jn"*) ;;
    *) printf '%s' "$1"; return ;;
  esac
  printf '%s' "$1" | awk 'BEGIN{ORS=""} NR>1{printf "\\n"} {
    n=length($0)
    for(i=1;i<=n;i++){ c=substr($0,i,1)
      if(c=="\\") printf "\\\\"; else if(c=="\"") printf "\\\"";
      else if(c=="\t") printf "\\t"; else if(c=="\r") printf "\\r";
      else printf "%s", c } }'
}
num() { case "$1" in ''|*[!0-9]*) printf '0' ;; *) printf '%s' "$1" ;; esac; }
# emit_row manifest user home agent path archive_path type size mtime atime ctime btime uid gid mode sha secret status target error
emit_row() {
  printf '{"user":"%s","home":"%s","agent":"%s","path":"%s","archive_path":"%s","type":"%s","size":%s,"mtime":%s,"atime":%s,"ctime":%s,"btime":%s,"uid":%s,"gid":%s,"mode":"%s","sha256":"%s","secret":%s,"status":"%s","target":"%s","error":"%s"}\n' \
    "$(json_str "$2")" "$(json_str "$3")" "$(json_str "$4")" "$(json_str "$5")" \
    "$(json_str "$6")" "$7" "$(num "$8")" "$(num "$9")" "$(num "${10}")" "$(num "${11}")" \
    "$(num "${12}")" "$(num "${13}")" "$(num "${14}")" "${15}" "${16}" "${17}" "${18}" \
    "$(json_str "${19}")" "$(json_str "${20}")" >>"$1"
}
EOF_COMMON
COMMON=$_hv
eval "$COMMON"

# Program run by find -exec for every regular file / symlink to collect.
# args: stage root user home agent manifest files...
heredoc_var <<'EOF_STAGE'
stage=$1; root=$2; user=$3; home=$4; agent=$5; manifest=$6; shift 6
lastdir=
for f in "$@"; do
  rel=${f#"$root"}
  hrel=${f#"$home"/}
  dest="$stage/fs$rel"
  type=file; target=; status=collected; sha=; err=
  st=$(stat_file "$f"); [ -n "$st" ] || st='0 0 0 0 0 0 0 0'
  set -- $st
  size=$1; mtime=$2; atime=$3; ctime=$4; btime=$5; uid=$6; gid=$7; mode=$8
  secret=false
  oifs=$IFS; IFS='
'
  for p in $SECRET_GLOBS; do case "$hrel" in $p) secret=true ;; esac; done
  IFS=$oifs
  d=${dest%/*}
  if [ "$d" != "$lastdir" ]; then mkdir -p "$d" 2>>"$LOG"; lastdir=$d; fi
  if [ -L "$f" ]; then
    type=symlink; status=symlink
    target=$(readlink "$f" 2>/dev/null)
    ln -s "$target" "$dest" 2>/dev/null
  elif [ "$secret" = true ] && [ "${NO_SECRETS:-0}" = 1 ]; then
    status=skipped_secret
  elif [ "${MAX_SIZE:-0}" -gt 0 ] && [ "$(num "$size")" -gt "$MAX_SIZE" ]; then
    status=skipped_size
  elif err=$(cp -p "$f" "$dest" 2>&1); then
    sha=$(hash_file "$dest")
  else
    status=error_copy
    rm -f "$dest" 2>/dev/null
    log_line "copy failed: $f: $err"
  fi
  case "$status" in collected|symlink) apath="fs$rel" ;; *) apath= ;; esac
  emit_row "$manifest" "$user" "$home" "$agent" "$f" "$apath" "$type" "$size" "$mtime" "$atime" "$ctime" "$btime" "$uid" "$gid" "$mode" "$sha" "$secret" "$status" "$target" "$err"
done
EOF_STAGE
STAGE_PROG="$COMMON
$_hv"

# Program run by find -exec for every pruned (excluded) path.
# args: root user home agent manifest paths...
heredoc_var <<'EOF_SKIP'
root=$1; user=$2; home=$3; agent=$4; manifest=$5; shift 5
for f in "$@"; do
  rel=${f#"$root"}
  if [ -d "$f" ]; then
    type=dir; kb=$(du -sk "$f" 2>/dev/null | cut -f1); size=$(( $(num "$kb") * 1024 ))
    st='0 0 0 0 0 0 0 0'
  else
    type=file; st=$(stat_file "$f"); [ -n "$st" ] || st='0 0 0 0 0 0 0 0'
    size=${st%% *}
  fi
  set -- $st
  emit_row "$manifest" "$user" "$home" "$agent" "$f" "" "$type" "$size" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "" false skipped_excluded "" ""
done
EOF_SKIP
SKIP_PROG="$COMMON
$_hv"

# Program run by find -exec in --inventory mode for every regular file under a
# matched path: prints F|agent|size|mtime and copies, hashes and writes nothing.
# args: agent files...
heredoc_var <<'EOF_INV'
agent=$1; shift
for f in "$@"; do
  st=$(stat_file "$f")
  set -- $st
  printf 'F|%s|%s|%s\n' "$agent" "$(num "${1:-}")" "$(num "${2:-}")"
done
EOF_INV
INV_PROG="$COMMON
$_hv"

# ---------------------------------------------------------------------------
usage() {
  cat <<EOF
Usage: $0 [options]

  -o, --output DIR        Directory for the archive (default: current dir)
  -r, --root DIR          Alternate root, e.g. a mounted disk image (image mode)
  -u, --users LIST        Comma-separated usernames to collect (default: all)
  -p, --project DIR       Extra project directory to collect (repeatable)
      --full              Disable default size exclusions (model blobs, caches,
                          extension binaries)
      --no-secrets        Skip credential files instead of collecting them
      --no-projects       Skip project-level artifact discovery
      --no-docker         Skip Docker and Podman volume enumeration
      --max-file-size MB  Skip files larger than this (default 256, 0 = none)
  -k, --keep-staging      Keep the staging directory after archiving
      --inventory         Write nothing; print one JSON line per user and agent
                          found (file count, bytes, first and last mtime) to
                          stdout. -o is ignored
      --list              Print the artifact catalog and exit
  -q, --quiet             Only print the final summary
  -V, --version           Print version and exit
  -h, --help              This help

Environment: COLLECTOR_SH overrides the shell used for per-file workers
(default: sh). Run as root to collect every user's home.
EOF
}

OUTDIR=.
ROOT=
USERS=
EXTRA_PROJECTS=
FULL=0
NO_SECRETS=0
NO_PROJECTS=0
NO_DOCKER=0
MAX_MB=256
KEEP=0
QUIET=0
LIST=0
INVENTORY=0
OUTDIR_SET=0

while [ $# -gt 0 ]; do
  case "$1" in
    -o|--output)        [ $# -ge 2 ] || { usage >&2; exit 1; }; OUTDIR=$2; OUTDIR_SET=1; shift ;;
    -r|--root)          [ $# -ge 2 ] || { usage >&2; exit 1; }; ROOT=$2; shift ;;
    -u|--users)         [ $# -ge 2 ] || { usage >&2; exit 1; }; USERS=$2; shift ;;
    -p|--project)       [ $# -ge 2 ] || { usage >&2; exit 1; }; EXTRA_PROJECTS="$EXTRA_PROJECTS
$2"; shift ;;
    --full)             FULL=1 ;;
    --no-secrets)       NO_SECRETS=1 ;;
    --no-projects)      NO_PROJECTS=1 ;;
    --no-docker)        NO_DOCKER=1 ;;
    --max-file-size)    [ $# -ge 2 ] || { usage >&2; exit 1; }; MAX_MB=$2; shift ;;
    -k|--keep-staging)  KEEP=1 ;;
    --list)             LIST=1 ;;
    --inventory)        INVENTORY=1 ;;
    -q|--quiet)         QUIET=1 ;;
    -V|--version)       printf '%s %s\n' "$TOOL" "$VERSION"; exit 0 ;;
    -h|--help)          usage; exit 0 ;;
    *)                  printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 1 ;;
  esac
  shift
done

if [ "$LIST" = 1 ]; then
  printf '# home artifacts (agent|glob relative to home)\n%s\n' "$CATALOG" | grep -v '^$'
  printf '\n# project artifacts (relative to each discovered project)\n%s\n' "$PROJECT_CATALOG" | grep -v '^$'
  printf '\n# excluded unless --full\n%s\n' "$EXCLUDES" | grep -v '^$'
  printf '\n# credential files (flagged secret, skipped with --no-secrets)\n%s\n' "$SECRET_GLOBS"
  printf '\n# docker volumes (agent|volume name glob)\n%s\n' "$DOCKER_VOLUMES" | grep -v '^$'
  exit 0
fi

case "$MAX_MB" in ''|*[!0-9]*) printf 'Invalid --max-file-size: %s\n' "$MAX_MB" >&2; exit 1 ;; esac
MAX_SIZE=$(( MAX_MB * 1024 * 1024 ))

# Normalise root: "" for live, else absolute path without trailing slash.
if [ -n "$ROOT" ]; then
  [ -d "$ROOT" ] || { printf 'Root is not a directory: %s\n' "$ROOT" >&2; exit 2; }
  ROOT=$(cd "$ROOT" && pwd)
  [ "$ROOT" = / ] && ROOT=
fi
MODE=live
[ -n "$ROOT" ] && MODE=image
# --inventory writes nothing: no output directory, staging or log.

if [ "$INVENTORY" != 1 ]; then
  [ -d "$OUTDIR" ] || mkdir -p "$OUTDIR" 2>/dev/null || { printf 'Cannot create output dir: %s\n' "$OUTDIR" >&2; exit 2; }
  OUTDIR=$(cd "$OUTDIR" && pwd) || exit 2
  [ -w "$OUTDIR" ] || { printf 'Output dir not writable: %s\n' "$OUTDIR" >&2; exit 2; }
  command -v tar >/dev/null 2>&1 || { printf 'tar not found\n' >&2; exit 2; }
fi
command -v find >/dev/null 2>&1 || { printf 'find not found\n' >&2; exit 2; }

# Capability detection, exported for the worker programs.
if command -v sha256sum >/dev/null 2>&1; then HASH_TOOL=sha256sum
elif command -v shasum >/dev/null 2>&1 && shasum -a 256 /dev/null >/dev/null 2>&1; then HASH_TOOL=shasum
elif command -v sha256 >/dev/null 2>&1; then HASH_TOOL=sha256
elif command -v openssl >/dev/null 2>&1; then HASH_TOOL=openssl
else HASH_TOOL=none; fi

_st=$(stat -c '%s %W' / 2>/dev/null)
case "$_st" in
  '') if stat -f '%z' / >/dev/null 2>&1; then STAT_MODE=bsd; else STAT_MODE=none; fi ;;
  *[!0-9\ ]*) STAT_MODE=gnu0 ;;
  *) STAT_MODE=gnu ;;
esac

START_TS=$(ts)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
HOST=$(hostname 2>/dev/null || uname -n 2>/dev/null || printf unknown)
HOST_SAFE=$(printf '%s' "$HOST" | tr -c 'A-Za-z0-9._-' '-')
NAME="${HOST_SAFE}_${STAMP}_agent-artifacts"
STAGE="$OUTDIR/.stage-$NAME"
ARCHIVE="$OUTDIR/$NAME.tar.gz"
LOG="$OUTDIR/$NAME.log"
MANIFEST="$OUTDIR/$NAME.manifest.jsonl"
SUMMARY="$OUTDIR/$NAME.collection.json"
WORKER_SH=${COLLECTOR_SH:-sh}
if [ "$INVENTORY" = 1 ]; then
  STAGE=; LOG=/dev/null; MANIFEST=/dev/null
fi

export HASH_TOOL STAT_MODE MAX_SIZE SECRET_GLOBS NO_SECRETS LOG QUIET

# shellcheck disable=SC2317,SC2329 # invoked from the traps below
cleanup() {
  if [ "$KEEP" != 1 ] && [ -n "$STAGE" ] && [ -d "$STAGE" ]; then
    rm -rf "$STAGE"
  fi
}
trap 'cleanup' EXIT
trap 'log_line "interrupted"; cleanup; trap - EXIT; exit 130' INT TERM

if [ "$INVENTORY" != 1 ]; then
  mkdir -p "$STAGE/fs" || { printf 'Cannot create staging dir\n' >&2; exit 2; }
  : >"$LOG"; : >"$MANIFEST"
fi

[ "$FULL" = 1 ] && ACTIVE_EXCLUDES= || ACTIVE_EXCLUDES=$EXCLUDES

log_line "$TOOL $VERSION starting on $HOST ($(uname -s 2>/dev/null) $(uname -r 2>/dev/null)) mode=$MODE root=${ROOT:-/} uid=$(id -u 2>/dev/null)"
log_line "hash=$HASH_TOOL stat=$STAT_MODE max_file_size=${MAX_MB}MB full=$FULL no_secrets=$NO_SECRETS no_docker=$NO_DOCKER worker_sh=$WORKER_SH"
if [ "$MODE" = live ] && [ "$(id -u 2>/dev/null)" != 0 ]; then
  log_line "WARNING: not running as root; other users' homes will probably be unreadable"
fi
if [ "$INVENTORY" = 1 ] && [ "$OUTDIR_SET" = 1 ]; then
  log_line "NOTE: --inventory writes nothing; -o $OUTDIR ignored"
fi

# ---------------------------------------------------------------------------
# expand_glob BASE PATTERN -> matching paths, one per line
expand_glob() {
  _eg_ifs=$IFS
  IFS='
'
  for _eg_m in $1/$2; do
    if [ -e "$_eg_m" ] || [ -L "$_eg_m" ]; then printf '%s\n' "$_eg_m"; fi
  done
  IFS=$_eg_ifs
}

# collect_path USER HOME AGENT PATH
# With --inventory the same walk runs, but excluded subtrees are pruned
# without a manifest row and regular files are only stat'ed by INV_PROG.
collect_path() {
  _cp_user=$1; _cp_home=$2; _cp_agent=$3; _cp_m=$4
  if [ -d "$_cp_m" ] && [ ! -L "$_cp_m" ]; then
    set -- "$_cp_m"
    _cp_ifs=$IFS
    IFS='
'
    # Paths claimed by another catalog entry are left to that entry: a nested
    # entry such as .gemini/antigravity-cli is attributed to its own agent and
    # collected once, not swept up again by the enclosing .gemini entry.
    _cp_first=1
    for _cp_n in $NESTED_CLAIMS; do
      case "$_cp_n" in "$_cp_m"/*) ;; *) continue ;; esac
      if [ "$_cp_first" = 1 ]; then set -- "$@" '(' -path "$_cp_n"; _cp_first=0
      else set -- "$@" -o -path "$_cp_n"; fi
    done
    if [ "$_cp_first" = 0 ]; then set -- "$@" ')' -prune -o; fi
    _cp_first=1
    for _cp_e in $ACTIVE_EXCLUDES; do
      [ -n "$_cp_e" ] || continue
      if [ "$_cp_first" = 1 ]; then set -- "$@" '(' -path "$_cp_home/$_cp_e"; _cp_first=0
      else set -- "$@" -o -path "$_cp_home/$_cp_e"; fi
    done
    IFS=$_cp_ifs
    if [ "$_cp_first" = 0 ] && [ "$INVENTORY" = 1 ]; then
      set -- "$@" ')' -prune -o
    elif [ "$_cp_first" = 0 ]; then
      set -- "$@" ')' -prune -exec "$WORKER_SH" -c "$SKIP_PROG" sh "$ROOT" "$_cp_user" "$_cp_home" "$_cp_agent" "$MANIFEST" '{}' + -o
    fi
    if [ "$INVENTORY" = 1 ]; then
      set -- "$@" -type f -exec "$WORKER_SH" -c "$INV_PROG" sh "$_cp_agent" '{}' +
    else
      set -- "$@" '(' -type f -o -type l ')' -exec "$WORKER_SH" -c "$STAGE_PROG" sh "$STAGE" "$ROOT" "$_cp_user" "$_cp_home" "$_cp_agent" "$MANIFEST" '{}' +
    fi
    find "$@" 2>>"$LOG"
  elif [ "$INVENTORY" = 1 ]; then
    if [ -f "$_cp_m" ] && [ ! -L "$_cp_m" ]; then
      "$WORKER_SH" -c "$INV_PROG" sh "$_cp_agent" "$_cp_m"
    fi
  else
    "$WORKER_SH" -c "$STAGE_PROG" sh "$STAGE" "$ROOT" "$_cp_user" "$_cp_home" "$_cp_agent" "$MANIFEST" "$_cp_m"
  fi
}

# collect_tree USER BASE CATALOG
# Every entry is expanded first so that each matched path can be excluded
# from the walk of any enclosing match (see NESTED_CLAIMS in collect_path).
# With --inventory, each match of an inventoried agent first prints
# M|agent|glob on stdout, and shared and shell-history matches still claim
# their paths but are not walked. HEADER, when given, is logged once before
# the first match, so a home with no matches leaves no progress line.
collect_tree() {
  _ct_header=${4:-}
  _ct_matches=$(printf '%s\n' "$3" | while IFS='|' read -r _ct_agent _ct_pat; do
    case "$_ct_agent" in (''|'#'*) continue ;; esac
    expand_glob "$2" "$_ct_pat" | while IFS= read -r _ct_m; do
      printf '%s|%s|%s\n' "$_ct_agent" "$_ct_pat" "$_ct_m"
    done
  done)
  NESTED_CLAIMS=$(printf '%s\n' "$_ct_matches" | cut -d'|' -f3-)
  printf '%s\n' "$_ct_matches" | while IFS='|' read -r _ct_agent _ct_pat _ct_m; do
    [ -n "$_ct_agent" ] || continue
    if [ "$INVENTORY" = 1 ]; then
      case "$_ct_agent" in shared|shell-history) continue ;; esac
      printf 'M|%s|%s\n' "$_ct_agent" "$_ct_pat"
    fi
    if [ -n "$_ct_header" ]; then log_line "$_ct_header"; _ct_header=; fi
    log_line "  [$_ct_agent] $_ct_m"
    collect_path "$1" "$2" "$_ct_agent" "$_ct_m" </dev/null
  done
  NESTED_CLAIMS=
}

# ---------------------------------------------------------------------------
# User enumeration -> "user:home" lines (home is a full path incl. ROOT)
enumerate_users() {
  {
    if [ "$MODE" = live ] && command -v getent >/dev/null 2>&1; then
      getent passwd 2>/dev/null
    elif [ -f "$ROOT/etc/passwd" ]; then
      cat "$ROOT/etc/passwd"
    fi
  } | awk -F: -v r="$ROOT" 'NF>=6 && $6!="" {print $1":"r$6}'
  if [ "$MODE" = live ] && command -v dscl >/dev/null 2>&1; then
    dscl . -list /Users NFSHomeDirectory 2>/dev/null | awk 'NF>=2 {print $1":"$2}'
  fi
  for _eu_g in home/* Users/* root var/root usr/home/* export/home/*; do
    expand_glob "$ROOT" "$_eu_g" | while IFS= read -r _eu_h; do
      [ -d "$_eu_h" ] && printf '%s:%s\n' "${_eu_h##*/}" "$_eu_h"
    done
  done
}

filter_users() {
  awk -F: -v root="$ROOT" -v want="$USERS" '
    BEGIN { n=split(want, w, ","); for(i=1;i<=n;i++) if (w[i]!="") sel[w[i]]=1 }
    {
      u=$1; h=substr($0, index($0, ":")+1)
      rel=h; if (root!="" && index(h, root)==1) rel=substr(h, length(root)+1)
      if (rel=="" || rel=="/" || rel=="/bin" || rel=="/sbin" || rel=="/usr" || rel=="/usr/bin" || rel=="/usr/sbin" ||
          rel=="/dev" || rel=="/dev/null" || rel=="/proc" || rel=="/sys" || rel=="/nonexistent" || rel=="/var/empty" ||
          rel=="/Users/Shared" || rel=="/Users/Public" || rel=="/Users/Default" || rel=="/Users/All Users" || rel=="/Users/Default User") next
      if (n>0 && !(u in sel)) next
      if (seen[h]++) next
      print u":"h
    }'
}

USER_LIST=$(enumerate_users | filter_users | while IFS=: read -r u h; do [ -d "$h" ] && printf '%s:%s\n' "$u" "$h"; done)
if [ -z "$USER_LIST" ]; then
  log_line "WARNING: no user home directories found"
fi

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Per-user collection (--inventory walks the homes after project discovery)
# shellcheck disable=SC2030 # _h is per-iteration; inv_secret reads it below
[ "$INVENTORY" = 1 ] || printf '%s\n' "$USER_LIST" | while IFS=: read -r _u _h; do
  [ -n "$_h" ] || continue
  collect_tree "$_u" "$_h" "$CATALOG" "User $_u ($_h)"
done

# ---------------------------------------------------------------------------
# Docker and Podman named volumes. Enumerated from the filesystem, never with
# the docker binary, so the same code covers live hosts and disk images. Each
# volume is <volumes dir>/<name>/_data. A volume whose name matches
# DOCKER_VOLUMES is collected whole as user "docker" with _data as its home;
# any other volume gets one skipped_unmatched_volume row with its size.
# Failures (an unreadable volumes directory, a volume that cannot be walked)
# are counted, noted in collection.json and printed in the summary; they never
# stop the collection.
NOTES=
DOCKER_SEEN=0; DOCKER_FOUND=0; DOCKER_COLLECTED=0; DOCKER_UNREADABLE=0; DOCKER_DESKTOP=0
DOCKER_INV=
add_note() { NOTES="$NOTES
$1"; log_line "NOTE: $1"; }
# docker_volume_rule NAME -> the first DOCKER_VOLUMES line (agent|glob) whose glob matches
docker_volume_rule() {
  _dv_ifs=$IFS
  IFS='
'
  set -f
  for _dv_l in $DOCKER_VOLUMES; do
    case "$_dv_l" in ''|'#'*) continue ;; esac
    _dv_p=${_dv_l#*|}
    # shellcheck disable=SC2254 # the table entry is a glob
    case "$1" in $_dv_p) set +f; IFS=$_dv_ifs; printf '%s' "$_dv_l"; return 0 ;; esac
  done
  set +f
  IFS=$_dv_ifs
}
# find_errors_since LINE -> number of find(1) error lines appended to the log after LINE
find_errors_since() { tail -n "+$(( $1 + 1 ))" "$LOG" 2>/dev/null | grep -c '^find: '; }
# collect_volume_dir BASE REL: every <name>/_data under the volumes directory
# BASE/REL. Each component of REL is checked on the way down, so a data root
# the responder cannot enter (/var/lib/docker and /var/lib/containers are
# root-only) or a symlinked one is reported rather than silently skipped.
collect_volume_dir() {
  _vd=$1; _vr=$2/
  while [ -n "$_vr" ]; do
    _vd="$_vd/${_vr%%/*}"; _vr=${_vr#*/}
    if [ -L "$_vd" ]; then
      DOCKER_SEEN=1
      add_note "docker: $_vd is a symlink and was not followed; collect its target by hand"
      return
    fi
    [ -d "$_vd" ] || return
    if [ ! -x "$_vd" ] || { [ -z "$_vr" ] && [ ! -r "$_vd" ]; }; then
      DOCKER_SEEN=1; DOCKER_UNREADABLE=$(( DOCKER_UNREADABLE + 1 ))
      add_note "docker: $_vd is not readable; run as root to collect the volumes under it"
      return
    fi
  done
  DOCKER_SEEN=1
  log_line "Docker volumes in $_vd"
  _vd_list=$(expand_glob "$_vd" '*')
  while IFS= read -r _vv; do
    [ -n "$_vv" ] || continue
    if [ -L "$_vv" ] || [ ! -d "$_vv" ]; then continue; fi
    DOCKER_FOUND=$(( DOCKER_FOUND + 1 ))
    _vn=${_vv##*/}; _vdata="$_vv/_data"
    _vrule=$(docker_volume_rule "$_vn")
    _va=${_vrule%%|*}
    if [ ! -r "$_vv" ] || [ ! -x "$_vv" ] || { [ -d "$_vdata" ] && { [ ! -r "$_vdata" ] || [ ! -x "$_vdata" ]; }; }; then
      DOCKER_UNREADABLE=$(( DOCKER_UNREADABLE + 1 ))
      add_note "docker: volume $_vn (${_va:-unmatched}) at $_vv is not readable; run as root to collect it"
    elif [ -L "$_vdata" ] || [ ! -d "$_vdata" ]; then
      log_line "  volume $_vn has no _data directory, skipped"
    elif [ -z "$_va" ] && [ "$INVENTORY" = 1 ]; then
      :
    elif [ -z "$_va" ]; then
      _vkb=$(du -sk "$_vdata" 2>/dev/null | cut -f1)
      emit_row "$MANIFEST" docker "$_vdata" "" "$_vdata" "" dir "$(( $(num "$_vkb") * 1024 ))" 0 0 0 0 0 0 0 "" false skipped_unmatched_volume "" ""
    elif [ "$INVENTORY" = 1 ]; then
      log_line "  [$_va] $_vdata"
      DOCKER_INV="$DOCKER_INV
M|$_vrule
$(collect_path docker "$_vdata" "$_va" "$_vdata" </dev/null)"
      DOCKER_COLLECTED=$(( DOCKER_COLLECTED + 1 ))
    else
      log_line "  [$_va] $_vdata"
      _vl=$(wc -l <"$LOG" | tr -d ' ')
      collect_path docker "$_vdata" "$_va" "$_vdata" </dev/null
      _vfe=$(num "$(find_errors_since "$(num "$_vl")")")
      DOCKER_COLLECTED=$(( DOCKER_COLLECTED + 1 ))
      if [ "$_vfe" -gt 0 ]; then
        DOCKER_UNREADABLE=$(( DOCKER_UNREADABLE + 1 ))
        add_note "docker: volume $_vn ($_va) could not be walked completely ($_vfe unreadable paths, see collector.log); run as root to collect it"
      fi
    fi
  done <<EOF_VOLUMES
$_vd_list
EOF_VOLUMES
}

if [ "$NO_DOCKER" != 1 ]; then
  # Root Docker, root Podman and Windows-container Docker data roots, then the
  # rootless Docker and Podman roots of each (selected) user.
  collect_volume_dir "$ROOT/var/lib" docker/volumes </dev/null
  collect_volume_dir "$ROOT/var/lib" containers/storage/volumes </dev/null
  collect_volume_dir "$ROOT/ProgramData" Docker/volumes </dev/null
  # Docker Desktop keeps Linux volumes inside a VM disk that no file walk reaches.
  _dk_desktop="$ROOT/ProgramData/DockerDesktop"
  while IFS= read -r _dk_line; do
    [ -n "$_dk_line" ] || continue
    _dk_h=${_dk_line#*:}
    collect_volume_dir "$_dk_h/.local/share" docker/volumes </dev/null
    collect_volume_dir "$_dk_h/.local/share" containers/storage/volumes </dev/null
    _dk_desktop="$_dk_desktop
$_dk_h/Library/Containers/com.docker.docker
$_dk_h/AppData/Local/Docker"
  done <<EOF_DKUSERS
$USER_LIST
EOF_DKUSERS
  while IFS= read -r _dk_d; do
    if [ -n "$_dk_d" ] && [ -d "$_dk_d" ] && [ ! -L "$_dk_d" ]; then
      DOCKER_SEEN=1; DOCKER_DESKTOP=1
      add_note "docker: Docker Desktop data at $_dk_d; volumes inside its virtual machine disk are not collected"
    fi
  done <<EOF_DKDESKTOP
$_dk_desktop
EOF_DKDESKTOP
fi

# ---------------------------------------------------------------------------
# Project discovery: paths referenced by agent state files, prefixed with ROOT.
# Emits "user:path"; the user is whoever's state referenced the path. Only
# plain-text sources are read here (JSON/JSONL via grep); SQLite-backed agents
# (Zed, Goose, OpenCode, Kilo, Cline db/) are left to the analyst-side parser.
# inv_secret FILE -> true when --inventory is on and FILE, relative to the home
# being scanned ($_h), matches SECRET_GLOBS. Inventory never opens such a file,
# so discovery sources that are credential files (.claude.json, the OpenClaw
# and nanobot configs, Tabby's config.toml) are not read in that mode.
inv_secret() {
  [ "$INVENTORY" = 1 ] || return 1
  # shellcheck disable=SC2031 # _h is the calling loop's current home
  _is_r=${1#"$_h"/}
  _is_ifs=$IFS
  IFS='
'
  set -f
  for _is_p in $SECRET_GLOBS; do
    # shellcheck disable=SC2254 # the table entry is a glob
    case "$_is_r" in $_is_p) set +f; IFS=$_is_ifs; return 0 ;; esac
  done
  set +f
  IFS=$_is_ifs
  return 1
}
# Evaluated at the top of each discovery helper after its key is shifted off:
# drops the files inv_secret rejects from "$@".
# shellcheck disable=SC2016 # expanded where it is eval'd, not here
INV_DROP_SECRETS='if [ "$INVENTORY" = 1 ]; then _ids_n=$#; for _ids_f do inv_secret "$_ids_f" || set -- "$@" "$_ids_f"; done; shift "$_ids_n"; fi'
# json_vals KEY FILE... -> values of "KEY":"..." across the given files
json_vals() {
  _jv_k=$1; shift
  eval "$INV_DROP_SECRETS"
  [ $# -gt 0 ] || return 0
  grep -ho "\"$_jv_k\": *\"[^\"]*\"" "$@" 2>/dev/null | sed "s/^\"$_jv_k\": *\"//; s/\"\$//"
}
# abs_strings FILE... -> every quoted absolute path or file:// URI in the files
# (JSON arrays of workspace paths, object keys, nested values alike)
abs_strings() {
  eval "$INV_DROP_SECRETS"
  [ $# -gt 0 ] || return 0
  grep -ho '"\(file:\/\/\/\)\{0,1\}/[^"]*"' "$@" 2>/dev/null | sed 's/^"//; s/"$//; s/^file:\/\///; s/%20/ /g'
}
# yaml_vals KEY FILE... -> values of top-level "KEY: value" lines
yaml_vals() {
  _yv_k=$1; shift
  eval "$INV_DROP_SECRETS"
  [ $# -gt 0 ] || return 0
  grep -h "^$_yv_k: *" "$@" 2>/dev/null | sed "s/^$_yv_k: *//; s/^[\"']//; s/[\"']\$//"
}
# json5_vals KEY FILE... -> string values of KEY in JSON5 files, where the key
# may be unquoted and the value single-quoted (OpenClaw config)
json5_vals() {
  _j5_k=$1; shift
  eval "$INV_DROP_SECRETS"
  [ $# -gt 0 ] || return 0
  grep -Eho "(^|[^A-Za-z0-9_\$])[\"']?${_j5_k}[\"']? *: *(\"[^\"]*\"|'[^']*')" "$@" 2>/dev/null | sed "s/^.*${_j5_k}[\"']\{0,1\} *: *[\"']//; s/[\"']\$//"
}
# toml_file_urls KEY FILE... -> local paths of KEY = "file://..." lines (Tabby)
toml_file_urls() {
  _tf_k=$1; shift
  eval "$INV_DROP_SECRETS"
  [ $# -gt 0 ] || return 0
  grep -ho "^ *$_tf_k *= *[\"']file://[^\"']*[\"']" "$@" 2>/dev/null | sed "s/^ *$_tf_k *= *[\"']file:\/\///; s/[\"']\$//; s/%20/ /g"
}
# common_dir -> the deepest directory shared by the absolute file paths on stdin
# (Twinny records indexed files, not the workspace root)
common_dir() {
  awk '{ n=split($0, a, "/") - 1
    if (NR==1) { m=n; for (i=1;i<=m;i++) c[i]=a[i]; next }
    if (n<m) m=n
    for (i=1;i<=m;i++) if (a[i]!=c[i]) { m=i-1; break } }
    END { if (NR>0 && m>=2) { s=c[1]; for (i=2;i<=m;i++) s=s "/" c[i]; print s } }'
}
discover_projects() {
  _dp_ifs=$IFS
  IFS='
'
  printf '%s\n' "$USER_LIST" | while IFS=: read -r _u _h; do
    [ -n "$_h" ] || continue
    {
      json_vals project "$_h/.claude/history.jsonl"
      [ -f "$_h/.claude.json" ] && ! inv_secret "$_h/.claude.json" &&
        grep -o '"/[^"]*": *{' "$_h/.claude.json" 2>/dev/null | sed 's/^"//; s/": *{$//'
      # config homes moved with CLAUDE_CONFIG_DIR keep .claude.json inside
      json_vals project "$_h"/.claude-*/history.jsonl
      for _dp_cj in "$_h"/.claude-*/.claude.json; do
        [ -f "$_dp_cj" ] && ! inv_secret "$_dp_cj" &&
          grep -o '"/[^"]*": *{' "$_dp_cj" 2>/dev/null | sed 's/^"//; s/": *{$//'
      done
      [ -d "$_h/.codex/sessions" ] && find "$_h/.codex/sessions" -name '*.jsonl' -exec grep -ho '"cwd":"[^"]*"' {} + 2>/dev/null | sed 's/^"cwd":"//; s/"$//'
      json_vals cwd "$_h"/.qwen/projects/*/chats/*.jsonl "$_h"/.cline/data/sessions/*/*.json "$_h"/.cursor/chats/*/*/meta.json
      json_vals workspace_root "$_h"/.cline/data/sessions/*/*.json
      json_vals workspaceDirectory "$_h/.continue/sessions/sessions.json"
      json_vals working_dir "$_h"/.local/share/goose/sessions/*.jsonl
      json_vals worktree "$_h"/.local/share/opencode/storage/project/*.json
      json_vals path "$_h/.local/share/crush/projects.json"
      [ -f "$_h/.gemini/projects.json" ] && ! inv_secret "$_h/.gemini/projects.json" &&
        grep -o '"/[^"]*": *"' "$_h/.gemini/projects.json" 2>/dev/null | sed 's/^"//; s/": *"$//'
      [ -f "$_h/.gemini/trustedFolders.json" ] && ! inv_secret "$_h/.gemini/trustedFolders.json" &&
        grep -o '"/[^"]*": *"' "$_h/.gemini/trustedFolders.json" 2>/dev/null | sed 's/^"//; s/": *"$//'
      cat "$_h"/.gemini/tmp/*/.project_root "$_h"/.gemini/history/*/.project_root 2>/dev/null
      json_vals workspace "$_h/.gemini/antigravity-cli/history.jsonl"
      abs_strings "$_h/.gemini/antigravity-cli/settings.json" "$_h/.gemini/antigravity-cli/cache/projects.json" "$_h"/.gemini/config/projects/*.json
      json_vals cwd "$_h/.local/share/amp/history.jsonl" "$_h"/.factory/sessions/*/*.jsonl "$_h"/.factory/sessions/*.jsonl "$_h"/.kiro/sessions/cli/*.json "$_h"/.cursor/acp-sessions/*/meta.json
      json_vals root "$_h"/.kiro/workspace-roots/*/.trust-migration.json
      abs_strings "$_h"/.kiro/sessions/*/sess_*/session.json "$_h/.config/Goose/recent-dirs.json" "$_h/Library/Application Support/Goose/recent-dirs.json" "$_h/AppData/Roaming/Goose/recent-dirs.json"
      yaml_vals cwd "$_h"/.copilot/session-state/*/workspace.yaml
      json_vals workdir "$_h"/.hermes/checkpoints/store/projects/*.json "$_h"/.hermes/profiles/*/checkpoints/store/projects/*.json \
        "$_h"/AppData/Local/hermes/checkpoints/store/projects/*.json "$_h"/AppData/Local/hermes/profiles/*/checkpoints/store/projects/*.json
      json_vals project "$_h/.letta/sessions.jsonl"
      json_vals cwd "$_h"/.letta/lc-local-backend/conversations/*/messages.jsonl "$_h"/.pi/agent/sessions/*/*.jsonl "$_h"/.pi/agent/*.jsonl \
        "$_h/.pi/agent/crashes.json" "$_h"/.pi/agent/experimental/sessions/*/meta.json
      [ -f "$_h/.pi/agent/trust.json" ] && ! inv_secret "$_h/.pi/agent/trust.json" &&
        grep -o '"/[^"]*": *[tf]' "$_h/.pi/agent/trust.json" 2>/dev/null | sed 's/^"//; s/": *[tf]$//'
      [ -f "$_h/.config/muse/trust.json" ] && ! inv_secret "$_h/.config/muse/trust.json" &&
        grep -o '"/[^"]*": *{' "$_h/.config/muse/trust.json" 2>/dev/null | sed 's/^"//; s/": *{$//'
      json_vals workspace_root "$_h"/.local/share/muse/sessions/*/*/*/*/session.jsonl
      for _oi in "$_h/.openinterpreter/sessions" "$_h/.openinterpreter/archived_sessions"; do
        [ -d "$_oi" ] && find "$_oi" -name 'rollout-*.jsonl' -exec grep -ho '"cwd":"[^"]*"' {} + 2>/dev/null | sed 's/^"cwd":"//; s/"$//'
      done
      json_vals path "$_h/.openhands/workspaces.json"
      json_vals working_dir "$_h"/.openhands/agent-canvas/dev_conversations/*/meta.json "$_h"/.openhands/agent-canvas/conversations/*/meta.json "$_h"/.openhands/conversations/*/base_state.json
      json_vals workspaceDirectory "$_h/.pearai/sessions/sessions.json"
      json5_vals workspace "$_h"/.openclaw*/openclaw.json "$_h/.clawdbot/clawdbot.json"
      json5_vals agentDir "$_h"/.openclaw*/openclaw.json "$_h/.clawdbot/clawdbot.json"
      for _nw in "$_h"/.nanobot*/sessions/*/.workspace; do [ -f "$_nw" ] && awk 1 "$_nw"; done
      json_vals workspace "$_h"/.nanobot*/config.json
      toml_file_urls git_url "$_h/.tabby/config.toml"
      for _tm in "$_h"/.twinny/embeddings/*/manifest.json; do [ -f "$_tm" ] && abs_strings "$_tm" | common_dir; done
      for _ws in "$_h"/Library/Application\ Support/*/User "$_h"/.config/*/User "$_h"/AppData/Roaming/*/User "$_h"/.*-server*/data/User; do
        [ -d "$_ws" ] || continue
        [ -d "$_ws/workspaceStorage" ] && find "$_ws/workspaceStorage" -name workspace.json -exec grep -ho '"folder": *"file://[^"]*"' {} + 2>/dev/null | sed 's/^"folder": *"file:\/\///; s/"$//; s/%20/ /g'
        json_vals cwdOnTaskInitialization "$_ws"/globalStorage/saoudrizwan.claude-dev/state/taskHistory.json "$_ws"/globalStorage/saoudrizwan.claude-dev/tasks/*/task_metadata.json
        json_vals workspace "$_ws"/globalStorage/rooveterinaryinc.roo-cline/tasks/_index.json "$_ws"/globalStorage/kilocode.kilo-code/tasks/_index.json
      done
    } | grep '^/' | sed 's/\\\//\//g' | awk -v r="$ROOT" -v u="$_u" '{print u":"r$0}'
  done
  IFS=$_dp_ifs
  printf '%s\n' "$EXTRA_PROJECTS" | grep '^/' | while IFS= read -r _p; do
    _owner=$(printf '%s\n' "$USER_LIST" | awk -F: -v p="$_p" '{h=substr($0,index($0,":")+1); if (index(p, h"/")==1) {print $1; exit}}')
    printf '%s:%s\n' "$_owner" "$_p"
  done
}

PROJECT_LIST=
if [ "$NO_PROJECTS" != 1 ]; then
  PROJECT_LIST=$(discover_projects | awk '
    { i=index($0,":"); u=substr($0,1,i-1); p=substr($0,i+1)
      if (p=="") next
      if (!(p in owner)) { order[++n]=p; owner[p]=u } else if (owner[p]=="") owner[p]=u }
    END { for (k=1;k<=n;k++) print owner[order[k]]":"order[k] }' | while IFS= read -r _line; do
    _p=${_line#*:}
    [ -d "$_p" ] || continue
    case "
$USER_LIST" in (*":$_p
"*|*":$_p") continue ;; esac
    printf '%s\n' "$_line"
  done)
  [ "$INVENTORY" = 1 ] || printf '%s\n' "$PROJECT_LIST" | while IFS= read -r _line; do
    [ -n "$_line" ] || continue
    _owner=${_line%%:*}; _p=${_line#*:}
    log_line "Project ${_owner:+[$_owner] }$_p"
    collect_tree "$_owner" "$_p" "$PROJECT_CATALOG"
  done
fi

# ---------------------------------------------------------------------------
# Inventory output. Every line goes to stdout and nothing is written. The host
# line comes first but its counts are known only after the walk, so the agent
# lines are held in a variable until then.
# inv_aggregate: M|agent|glob and F|agent|size|mtime lines on stdin ->
# agent|files|bytes|first|last|evidence per agent with at least one file, in
# order of first match. A match with no files of its own after exclusions and
# nested claims (~/.gemini holding only antigravity-cli) gives no line.
# Dates are UTC from the epoch with plain arithmetic (no date -d, no strftime);
# an mtime of 0 (stat unavailable) is left out of first and last.
inv_aggregate() {
  awk -F'|' '
    function iso(t,   d, s, z, era, doe, yoe, y, doy, mp, dd, m) {
      if (t <= 0) return ""
      d = int(t / 86400); s = t - d * 86400
      z = d + 719468; era = int(z / 146097); doe = z - era * 146097
      yoe = int((doe - int(doe / 1460) + int(doe / 36524) - int(doe / 146096)) / 365)
      y = yoe + era * 400; doy = doe - (365 * yoe + int(yoe / 4) - int(yoe / 100))
      mp = int((5 * doy + 2) / 153); dd = doy - int((153 * mp + 2) / 5) + 1
      m = (mp < 10) ? mp + 3 : mp - 9; if (m <= 2) y++
      return sprintf("%04d-%02d-%02dT%02d:%02d:%02dZ", y, m, dd, int(s / 3600), int((s % 3600) / 60), s % 60)
    }
    $1 == "M" { a = $2
      if (!(a in seen)) { seen[a] = 1; order[++n] = a; files[a] = 0; bytes[a] = 0; ev[a] = "" }
      if (!((a, $3) in g)) { g[a, $3] = 1; ev[a] = ev[a] (ev[a] == "" ? "" : ",") $3 } }
    $1 == "F" { a = $2; files[a]++; bytes[a] += $3
      if ($4 > 0) {
        if (!(a in lo) || $4 < lo[a]) lo[a] = $4
        if (!(a in hi) || $4 > hi[a]) hi[a] = $4 } }
    END { for (k = 1; k <= n; k++) { a = order[k]; if (files[a] == 0) continue
      printf "%s|%d|%.0f|%s|%s|%s\n", a, files[a], bytes[a], iso(lo[a] + 0), iso(hi[a] + 0), ev[a] } }'
}
# inv_emit USER PROJECTS: inv_aggregate lines on stdin -> agent JSON lines
inv_emit() {
  while IFS='|' read -r _ie_a _ie_f _ie_b _ie_lo _ie_hi _ie_ev; do
    [ -n "$_ie_a" ] || continue
    printf '{"type":"agent","host":"%s","user":"%s","agent":"%s","files":%s,"bytes":%s,"first":"%s","last":"%s","projects":%s,"evidence":"%s"}\n' \
      "$(json_str "$HOST")" "$(json_str "$1")" "$(json_str "$_ie_a")" "$(num "$_ie_f")" "$(num "$_ie_b")" \
      "$_ie_lo" "$_ie_hi" "$(num "$2")" "$(json_str "$_ie_ev")"
  done
}
if [ "$INVENTORY" = 1 ]; then
  # A home counts as unreadable when it cannot be both listed and entered
  # (test -r and -x on the directory itself); its catalog globs match nothing.
  USERS_SCANNED=0; USERS_UNREADABLE=0
  while IFS=: read -r _u _h; do
    [ -n "$_h" ] || continue
    USERS_SCANNED=$(( USERS_SCANNED + 1 ))
    if [ ! -r "$_h" ] || [ ! -x "$_h" ]; then
      USERS_UNREADABLE=$(( USERS_UNREADABLE + 1 ))
      log_line "WARNING: home of $_u is not readable: $_h"
    fi
  done <<EOF_INVUSERS
$USER_LIST
EOF_INVUSERS
  INV_LINES=$(printf '%s\n' "$USER_LIST" | while IFS=: read -r _u _h; do
    [ -n "$_h" ] || continue
    _np=$(printf '%s\n' "$PROJECT_LIST" | awk -F: -v u="$_u" '$1 == u && length($0) > length(u) + 1 { n++ } END { print n + 0 }')
    collect_tree "$_u" "$_h" "$CATALOG" "User $_u ($_h)" | inv_aggregate | inv_emit "$_u" "$_np"
  done)
  printf '{"type":"host","host":"%s","collector":"%s","mode":"%s","at":"%s","users_scanned":%s,"users_unreadable":%s,"docker_volumes":%s}\n' \
    "$(json_str "$HOST")" "$VERSION" "$MODE" "$START_TS" \
    "$USERS_SCANNED" "$USERS_UNREADABLE" "$DOCKER_FOUND"
  [ -z "$INV_LINES" ] || printf '%s\n' "$INV_LINES"
  printf '%s\n' "$DOCKER_INV" | inv_aggregate | inv_emit docker 0
  exit 0
fi

# ---------------------------------------------------------------------------
# Summary, archive, hashes
END_TS=$(ts)
count_status() { num "$(grep -c "\"status\":\"$1\"" "$MANIFEST" 2>/dev/null)"; }
# Users whose home gave at least one manifest row, in enumeration order.
ACTIVE_USERS=$(printf '%s\n' "$USER_LIST" | while IFS=: read -r _u _h; do
  [ -n "$_h" ] || continue
  grep -F -q "\"home\":\"$(json_str "$_h")\"" "$MANIFEST" 2>/dev/null && printf '%s:%s\n' "$_u" "$_h"
done)
# human_size BYTES -> "512 B", "20.9 MiB"
human_size() {
  awk -v b="$(num "$1")" 'BEGIN { split("B KiB MiB GiB TiB", u, " "); i = 1
    while (b >= 1024 && i < 5) { b /= 1024; i++ }
    if (i == 1) printf "%d B", b; else printf "%.1f %s", b, u[i] }'
}
BYTES=$(awk -F'"size":' '/"status":"collected"/ {split($2,a,","); s+=a[1]} END{printf "%d", s}' "$MANIFEST")

json_list() { # newline-separated -> JSON array
  _jl_n=0
  printf '['
  printf '%s\n' "$1" | while IFS= read -r _jl_x; do
    [ -n "$_jl_x" ] || continue
    [ "$_jl_n" = 0 ] || printf ','
    printf '"%s"' "$(json_str "$_jl_x")"
    _jl_n=1
  done
  printf ']'
}

cat >"$SUMMARY" <<EOF
{
  "tool": "$TOOL",
  "version": "$VERSION",
  "hostname": "$(json_str "$HOST")",
  "mode": "$MODE",
  "root": "$(json_str "${ROOT:-/}")",
  "platform": "$(json_str "$(uname -s 2>/dev/null) $(uname -r 2>/dev/null) $(uname -m 2>/dev/null)")",
  "run_as_uid": "$(id -u 2>/dev/null)",
  "started": "$START_TS",
  "finished": "$END_TS",
  "options": {"full": $( [ "$FULL" = 1 ] && printf true || printf false ), "no_secrets": $( [ "$NO_SECRETS" = 1 ] && printf true || printf false ), "max_file_size_bytes": $MAX_SIZE, "users_filter": "$(json_str "$USERS")", "no_docker": $( [ "$NO_DOCKER" = 1 ] && printf true || printf false )},
  "capabilities": {"hash_tool": "$HASH_TOOL", "stat_mode": "$STAT_MODE", "worker_shell": "$(json_str "$WORKER_SH")"},
  "users": $(json_list "$(printf '%s\n' "$USER_LIST" | cut -d: -f1)"),
  "homes": $(json_list "$(printf '%s\n' "$USER_LIST" | sed 's/^[^:]*://')"),
  "users_with_artifacts": $(json_list "$(printf '%s\n' "$ACTIVE_USERS" | cut -d: -f1)"),
  "projects": $(json_list "$(printf '%s\n' "$PROJECT_LIST" | sed 's/^[^:]*://')"),
  "counts": {"collected": $(count_status collected), "symlink": $(count_status symlink), "skipped_excluded": $(count_status skipped_excluded), "skipped_size": $(count_status skipped_size), "skipped_secret": $(count_status skipped_secret), "error_copy": $(count_status error_copy), "skipped_unmatched_volume": $(count_status skipped_unmatched_volume), "collected_bytes": $BYTES},
  "docker": {"volumes_found": $DOCKER_FOUND, "volumes_collected": $DOCKER_COLLECTED, "unreadable": $DOCKER_UNREADABLE, "docker_desktop": $( [ "$DOCKER_DESKTOP" = 1 ] && printf true || printf false )},
  "notes": $(json_list "$NOTES"),
  "archive": "$(json_str "$NAME.tar.gz")"
}
EOF

log_line "Archiving"
cp "$MANIFEST" "$STAGE/manifest.jsonl"
cp "$SUMMARY" "$STAGE/collection.json"
cp "$LOG" "$STAGE/collector.log"

rm -f "$ARCHIVE"
if ! tar -czf "$ARCHIVE" -C "$STAGE" . 2>>"$LOG"; then
  rm -f "$ARCHIVE"
  if command -v gzip >/dev/null 2>&1 && tar -cf - -C "$STAGE" . 2>>"$LOG" | gzip >"$ARCHIVE"; then :
  else
    rm -f "$ARCHIVE"; ARCHIVE="$OUTDIR/$NAME.tar"
    tar -cf "$ARCHIVE" -C "$STAGE" . 2>>"$LOG" || { log_line "FATAL: tar failed"; exit 2; }
  fi
fi
[ -s "$ARCHIVE" ] || { log_line "FATAL: archive not written"; exit 2; }

ARCHIVE_SHA=$(hash_file "$ARCHIVE")
ARCHIVE_SIZE=$(stat_file "$ARCHIVE"); ARCHIVE_SIZE=${ARCHIVE_SIZE%% *}
printf '%s  %s\n' "$ARCHIVE_SHA" "${ARCHIVE##*/}" >"$ARCHIVE.sha256"
# The archive's size and hash follow on stdout, so stderr gets only "done".
printf '%s done: %s (%s bytes, sha256 %s)\n' "$(ts)" "$ARCHIVE" "$ARCHIVE_SIZE" "$ARCHIVE_SHA" >>"$LOG"
[ "$QUIET" = 1 ] || printf 'done\n' >&2

printf 'archive:    %s\nsize:       %s (%s)\nsha256:     %s\nmanifest:   %s\nsummary:    %s\nlog:        %s\nusers:      %s\nprojects:   %s\ncollected:  %s files, %s bytes (%s)\nskipped:    %s excluded, %s too large, %s secret\nerrors:     %s\n' \
  "$ARCHIVE" "$ARCHIVE_SIZE" "$(human_size "$ARCHIVE_SIZE")" "$ARCHIVE_SHA" "$MANIFEST" "$SUMMARY" "$LOG" \
  "$(printf '%s\n' "$ACTIVE_USERS" | grep -c .)" "$(printf '%s\n' "$PROJECT_LIST" | grep -c .)" \
  "$(count_status collected)" "$BYTES" "$(human_size "$BYTES")" "$(count_status skipped_excluded)" "$(count_status skipped_size)" "$(count_status skipped_secret)" "$(count_status error_copy)"
if [ "$DOCKER_SEEN" = 1 ]; then
  printf 'docker:     %s volumes found, %s collected, %s unreadable' "$DOCKER_FOUND" "$DOCKER_COLLECTED" "$DOCKER_UNREADABLE"
  [ "$DOCKER_UNREADABLE" -gt 0 ] && printf ' (run as root to collect)'
  [ "$DOCKER_DESKTOP" = 1 ] && printf '; Docker Desktop VM disk not collected'
  printf '\n'
fi
exit 0
