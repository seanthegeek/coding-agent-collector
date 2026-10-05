# Copyright 2026 Sean Whalen
# SPDX-License-Identifier: Apache-2.0
#
# Smoke test for Collect-AgentArtifacts.ps1: build a fake disk image, run the
# collector in image mode, and check the manifest and archive. Runs under
# Windows PowerShell 5.1 and PowerShell 7 on any OS:
#   powershell.exe -ExecutionPolicy Bypass -File tests\smoke.ps1
#   pwsh -File tests/smoke.ps1
[CmdletBinding()]
param([string]$Collector = '')
Set-StrictMode -Version 2
$ErrorActionPreference = 'Continue'
if ($Collector -eq '') { $Collector = Join-Path (Split-Path -Parent $PSScriptRoot) 'Collect-AgentArtifacts.ps1' }
$Sep = [string][System.IO.Path]::DirectorySeparatorChar
$Work = Join-Path ([System.IO.Path]::GetTempPath()) ("cac-smoke-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$Root = Join-Path $Work 'root'
$Out = Join-Path $Work 'out'
$script:fail = 0
function Ok([string]$m) { Write-Output "ok   $m" }
function Bad([string]$m) { Write-Output "FAIL $m"; $script:fail = 1 }
function Check([string]$name, [scriptblock]$cond) {
  $res = $false; $why = ''
  try { $res = [bool](& $cond) } catch { $res = $false; $why = " ($($_.Exception.Message))" }
  if ($res) { Ok $name } else { Bad ($name + $why) }
}
function P([string]$rel) { return (Join-Path $Root ($rel.Replace('/', $Sep))) }
function Mk([string]$rel, [string]$content) {
  $p = P $rel; $d = Split-Path -Parent $p
  if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
  [System.IO.File]::WriteAllText($p, $content, (New-Object System.Text.UTF8Encoding $false))
}
function MkBig([string]$rel, [int]$bytes) {
  $p = P $rel; $d = Split-Path -Parent $p
  if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
  $fs = [System.IO.File]::Create($p); $fs.SetLength($bytes); $fs.Close()
}

Write-Output "== $($PSVersionTable.PSEdition) $($PSVersionTable.PSVersion) on $([Environment]::OSVersion.Platform); work $Work"

# ---- fake image (a Windows profile tree plus a Linux-style home) -----------
Mk 'Users/alice/.claude/projects/-C-proj/s1.jsonl' '{"type":"user","message":{"role":"user","content":"hi"},"timestamp":"2026-10-03T00:00:00Z"}'
Mk 'Users/alice/.claude/history.jsonl' '{"display":"do things","timestamp":1759449600000,"project":"C:\\proj","sessionId":"s1"}'
Mk 'Users/alice/.claude/.credentials.json' '{"claudeAiOauth":{"accessToken":"sk-ant-oat-SECRET"}}'
Mk 'Users/alice/.claude.json' '{"projects":{"C:\\proj":{}}}'
Mk 'Users/alice/.claude/cache/junk.bin' 'cached junk'
Mk 'Users/alice/.claude/weird name with spaces & [brackets].txt' 'weird'
Mk 'proj/CLAUDE.md' '# proj'
Mk 'proj/.claude/settings.local.json' 'settings'
Mk 'Users/alice/.gemini/antigravity-cli/antigravity-oauth-token' 'token'
Mk 'Users/alice/.gemini/antigravity-cli/conversations/c1.db' 'db'
MkBig 'Users/alice/.gemini/antigravity-cli/bin/webm_encoder.exe' 300000
Mk 'Users/alice/.gemini/antigravity-cli/log/cli-1.log' 'log'
Mk 'Users/alice/.gemini/projects.json' '{"projects":{"C:\\gem":"gem"}}'
Mk 'gem/GEMINI.md' '# gem'
Mk 'Users/alice/.codex/sessions/2026/10/03/rollout-1.jsonl' '{"type":"session_meta","payload":{"cwd":"C:\\Users\\alice\\Documents\\app"}}'
Mk 'Users/alice/.codex/auth.json' '{"tokens":{"access_token":"x"}}'
MkBig 'Users/alice/.codex/packages/standalone/releases/1/codex.exe' 200000
Mk 'Users/alice/Documents/app/.cursorrules' 'rules'
Mk 'Users/alice/Documents/app/AGENTS.md' '# agents'
MkBig 'Users/alice/AppData/Roaming/Cursor/User/globalStorage/state.vscdb' 2100000
Mk 'Users/alice/AppData/Roaming/Cursor/User/globalStorage/ms-python.python/x' 'junk'
Mk 'Users/alice/AppData/Roaming/Cursor/User/workspaceStorage/abc/workspace.json' '{"folder":"file:///c%3A/Users/alice/Documents/app"}'
Mk 'Users/alice/AppData/Roaming/Code/User/globalStorage/saoudrizwan.claude-dev/state/taskHistory.json' '[{"id":"t1","cwdOnTaskInitialization":"C:\\cl"}]'
Mk 'Users/alice/AppData/Roaming/Code/User/globalStorage/saoudrizwan.claude-dev/checkpoints/x' 'ckpt'
Mk 'cl/.clinerules' 'rules'
Mk 'Users/alice/AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt' 'Get-Process'
Mk 'Users/alice/AppData/Roaming/Claude/config.json' '{"oauth:tokenCache":"enc"}'
Mk 'Users/alice/AppData/Roaming/Claude/claude_desktop_config.json' '{"mcpServers":{}}'
Mk 'Users/alice/AppData/Roaming/Claude/Cache/index' 'cache'
Mk 'Users/alice/.continue/sessions/sessions.json' '[{"sessionId":"a","workspaceDirectory":"C:\\cont"}]'
Mk 'Users/alice/.continue/index/globalContext.json' '{"mcpOauthStorage":{}}'
Mk 'Users/alice/.continue/index/lancedb/data.lance' 'vec'
Mk 'cont/.continuerc.json' '{}'
Mk 'Users/alice/.local/share/crush/projects.json' '{"projects":[{"path":"C:\\crushproj","data_dir":"C:\\crushproj\\.crush"}]}'
Mk 'crushproj/.crush/crush.db' 'sqlite'
Mk 'Users/alice/.cline/data/settings/providers.json' '{"anthropic":{"apiKey":"sk-x"}}'
Mk 'Users/alice/.env' 'TOKEN=1'
Mk 'Users/Public/Desktop/readme.txt' 'public'
Mk 'Users/Default/NTUSER.DAT' 'default'
Mk 'home/bob/.ollama/models/blobs/sha256-abc' 'blob'
Mk 'home/bob/.ollama/history' 'hist'
# 2026-10-04 a profile with no agent state: listed in users, not counted on stdout
New-Item -ItemType Directory -Path (P 'Users/dave') -Force | Out-Null
Mk 'home/bob/.bash_history' 'export FOO=1'
# v1.3 catalog revision fixtures
Mk 'Users/alice/.factory/cache/session-index/index.db' 'sqlite'
Mk 'Users/alice/.factory/cache/sounds/done.wav' 'ding'
Mk 'Users/alice/.factory/sessions/-C-droid/s1.jsonl' '{"type":"session_start","cwd":"C:\\droid"}'
Mk 'droid/AGENTS.md' '# droid'
Mk 'Users/alice/.kiro/powers/installed/p1/mcp.json' '{"mcpServers":{}}'
Mk 'Users/alice/.kiro/sessions/cli/k1.json' '{"id":"k1","cwd":"C:\\kiroproj"}'
Mk 'kiroproj/.kiroignore' 'steer'
Mk 'Users/alice/.vscode-server/data/User/globalStorage/state.vscdb' 'sqlite'
Mk 'Users/alice/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/state/taskHistory.json' '[{"id":"t2","cwdOnTaskInitialization":"C:\\remoteproj"}]'
Mk 'remoteproj/.clinerules' 'rules'
Mk 'Users/alice/.gemini/antigravity-ide/conversations/i1.db' 'db'
Mk 'Users/alice/.gemini/antigravity-cli/history.jsonl' '{"display":"hi","timestamp":1759449600000,"workspace":"C:\\agyproj"}'
Mk 'agyproj/.antigravityignore' 'ignore'
Mk 'Users/alice/.cursor/auth.json' '{"accessToken":"x"}'
Mk 'Users/alice/.copilot/pkg/copilot.exe' 'pkg'
Mk 'Users/alice/.copilot/config.json' '{"token":"x"}'
Mk 'Users/alice/.copilot/session-state/s1/workspace.yaml' "cwd: C:\\copproj`nbranch: main"
Mk 'copproj/AGENTS.md' '# cop'
Mk 'Users/alice/.claude/.device-keys.json' '{"k":"x"}'
Mk 'Users/alice/.local/share/amp/history.jsonl' '{"cwd":"C:\\ampproj","prompt":"hi"}'
Mk 'ampproj/.amp/settings.json' 'amp'
Mk 'kiloproj/.kilo/worktrees/w1/f' 'wt'
Mk 'Users/alice/.cline/data/sessions/s1/s2.json' '{"cwd":"C:\\kiloproj"}'
# 1.4.0 catalog round (2026-10-04): sixteen agents from the October 2026 backlog.
# Same case list as smoke.sh: kind|agent|path relative to alice's profile.
$Cases14 = @'
excl||.pearai/extensions
excl||.pearai/index/lancedb
excl||.pearai/types
excl||.pearai/out
excl||.pearai/node_modules
excl||.pearai/.diffs
excl||.pearai/.migrations
excl||.config/pearai/User/globalStorage/pearai.pearai-roo-cline/checkpoints
excl||.config/pearai/User/globalStorage/pearai.pearai-roo-cline/tasks/t1/checkpoints
excl||.config/pearai/User/globalStorage/pearai.pearai-roo-cline/cache
exclf||.pearai/index/codebase.sqlite
exclf||.pearai/dev_data/devdata.sqlite
secret||.pearai/config.json
secret||.pearai/config.ts
secret||.pearai/.env
secret||.pearai/.configs/c1/config.json
secret||.config/pearai/User/globalStorage/pearai.pearai-roo-cline/settings/pearai_agent_mcp_settings.json
agent|pearai|.config/pearai/User/globalStorage/state.vscdb
agent|pearai|.pearai/sessions/s1.json
exclf||.config/Code/User/globalStorage/sourcegraph.cody-ai/symf/symf-v0.0.16
exclf||.local/share/Cody-nodejs/symf/symf-v0.0.16
exclf||Library/Application Support/Cody-nodejs/Data/symf/symf-v0.0.16
excl||.local/share/Cody-nodejs/dist
excl||AppData/Roaming/Cody-nodejs/Config/dist
secret||.config/Cody-nodejs/user-settings.json
secret||AppData/Roaming/Cody-nodejs/Config/user-settings.json
agent|cody|.config/Code/User/globalStorage/sourcegraph.cody-ai/symf/indexroot/meta.json
agent|cody|.vscode/cody.json
agent|cody|.local/share/Cody-nodejs/JetBrains-globalState/cody-local-chatHistory-v2
excl||.twinny/embeddings/ws/chunks.lance
excl||.twinny/server/plugins/p1/repos/r1/checkout
excl||.twinny/server/plugins/p1/repos/r1/index
secret||.config/Code/User/globalStorage/rjmacarthy.twinny/twinny-providers.json
secret||.twinny/node/identity.json
secret||.twinny/server/license
secret||.twinny/server/plugins/p1/settings.json
agent|twinny|.config/Code/User/globalStorage/rjmacarthy.twinny/twinny-providers.json
agent|twinny|.vscode-server/data/User/globalStorage/rjmacarthy.twinny/state.json
excl||.tabby/models
excl||.tabby/index
excl||.tabby/repositories
secret||.tabby/config.toml
secret||.tabby-client/agent/config.toml
agent|tabby|.tabby/ee/db.sqlite
agent|tabby|.tabby/ee/db.sqlite-wal
agent|tabby|.tabby/ee/db.sqlite-shm
agent|tabby|.config/JetBrains/IntelliJIdea2025.2/options/intellij-tabby.xml
excl||.openinterpreter/packages
excl||.openinterpreter/cache
excl||.openinterpreter/.tmp
excl||.openinterpreter/tmp
excl||.openinterpreter/plugins/cache
excl||.openinterpreter/skills/.system
excl||.openinterpreter/worktrees
excl||.openinterpreter/.sandbox
excl||.openinterpreter/.sandbox-bin
excl||.openinterpreter/visualizations
excl||.openinterpreter/models-cache
secret||.openinterpreter/auth.json
secret||.openinterpreter/.credentials.json
secret||.openinterpreter/credentials/c1
secret||.openinterpreter/device_id
secret||.openinterpreter/secrets/s1
secret||.openinterpreter/.sandbox-secrets/s1
secret||.openinterpreter/.env
secret||.openinterpreter/config.toml
secret||.codex/.env
agent|open-interpreter|.openinterpreter/history.jsonl
excl||.openhands/cache
excl||.openhands/agent-canvas/workspaces
excl||.openhands/agent-canvas/tmux
secret||.openhands/agent-canvas/secret-key.txt
secret||.openhands/agent-canvas/api-key.txt
secret||.openhands/settings.json
secret||.openhands/secrets.json
secret||.openhands/profiles/p1.json
secret||.openhands/provider-connections/c1.json
secret||.openhands/auth/a1.json
secret||.openhands/runtime-control/r1
secret||.openhands/agent_settings.json
secret||.openhands/cloud/c1.json
secret||.openhands/mcp.json
secret||.openhands/.jwt_secret
secret||.openhands/.keys
agent|openhands|.config/OpenHands Agent Canvas/config.json
agent|openhands|.openhands/conversations/c1/events/event-00000-e1.json
excl||.pi/agent/bin
excl||.pi/agent/tmp
excl||.pi/agent/npm/node_modules
excl||.pi/agent/git/g1/node_modules
excl||.pi/agent/git/g1/.git
excl||.pi/npm/node_modules
excl||.pi/git/g1/node_modules
excl||.pi/git/g1/.git
exclf||.pi/agent/tools/fd
exclf||.pi/agent/tools/rg.exe
exclf||.pi/server/s1.sock
secret||.pi/agent/auth.json
secret||.pi/agent/auth.json.bak
secret||.pi/agent/mcp-auth.json
secret||.pi/agent/oauth.json
secret||.pi/agent/models.json
secret||.pi/agent/mcp.json
secret||.pi/mcp.json
secret||.config/little-coder/models.json
agent|pi|.pi/agent/settings.json
agent|little-coder|.pi/agent/little-coder-prompt-history.json
agent|little-coder|.little-coder/state.json
agent|little-coder|.cache/little-coder/log.txt
excl||.letta/bin
excl||.letta/mod-cache
excl||.letta/tool_execution_dir
excl||.letta/chroma
excl||.memgpt/chroma
secret||.letta/settings.json
secret||.letta/pg_uri
secret||.letta/credentials
secret||.letta/lc-local-backend/providers/auth.json
secret||.letta/channels/telegram/accounts.json
secret||.letta/channels/whatsapp/auth/creds.json
secret||.letta/agents/a1/memory/.git/config
secret||.letta/agents/a1/memory/.git/letta-credential-helper.cmd
secret||.config/letta/settings.json
secret||.memgpt/credentials
agent|letta|.letta/transcripts/a1/c1/transcript.jsonl
excl||.hermes/hermes-agent/hermes_cli
excl||.hermes/hermes-agent/.git
excl||AppData/Local/hermes/hermes-agent/hermes_cli
excl||AppData/Local/hermes/hermes-agent/.venv
excl||.hermes/models
excl||.hermes/runtimes
excl||.hermes/node
excl||.hermes/installs
excl||.hermes/tools
excl||.hermes/sandboxes
excl||.hermes/checkpoints/store/objects
excl||.hermes/checkpoints/store/indexes
excl||.hermes/checkpoints/legacy-1
excl||.hermes/state-snapshots
excl||.hermes/backups
excl||.hermes/browser-profile
excl||.hermes/browser-profiles
excl||.hermes/browser_profiles
excl||.hermes/chrome-debug
excl||.hermes/bot-desktop/browser-profile
excl||.hermes/plugins/p1/node_modules
excl||.hermes/plugins/p1/.venv
excl||AppData/Local/hermes/models
excl||AppData/Local/hermes/runtimes
excl||AppData/Local/hermes/node
excl||AppData/Local/hermes/installs
excl||AppData/Local/hermes/tools
excl||AppData/Local/hermes/sandboxes
excl||AppData/Local/hermes/checkpoints/store/objects
excl||AppData/Local/hermes/checkpoints/store/indexes
excl||AppData/Local/hermes/checkpoints/legacy-1
excl||AppData/Local/hermes/state-snapshots
excl||AppData/Local/hermes/backups
excl||AppData/Local/hermes/browser-profile
excl||AppData/Local/hermes/browser-profiles
excl||AppData/Local/hermes/browser_profiles
excl||AppData/Local/hermes/chrome-debug
excl||AppData/Local/hermes/bot-desktop/browser-profile
excl||AppData/Local/hermes/plugins/p1/node_modules
excl||AppData/Local/hermes/plugins/p1/.venv
excl||.hermes/profiles/work/models
excl||.hermes_dev/models
excl||.config/Hermes/Cache
excl||.config/Hermes/Code Cache
excl||.config/Hermes/GPUCache
excl||Library/Application Support/Hermes/Cache
excl||Library/Application Support/Hermes/Code Cache
excl||Library/Application Support/Hermes/GPUCache
excl||AppData/Roaming/Hermes/Cache
excl||AppData/Roaming/Hermes/Code Cache
excl||AppData/Roaming/Hermes/GPUCache
secret||.hermes/.env
secret||.hermes/.env.bak1
secret||.hermes/.op.env
secret||.hermes/npmrc
secret||.hermes/auth.json
secret||.hermes/auth.json.1
secret||.hermes/auth/google_oauth.json
secret||.hermes/.anthropic_oauth.json
secret||.hermes/.copilot_jwt.json
secret||.hermes/google_token.json
secret||.hermes/google_chat_user_tokens/u1.json
secret||.hermes/slack_tokens.json
secret||.hermes/honcho.json
secret||.hermes/mem0.json
secret||.hermes/webhook_subscriptions.json
secret||.hermes/teams_pipeline_store.json
secret||.hermes/mcp-tokens/t1.json
secret||.hermes/vault/vault.key
secret||.hermes/browser_auth/state.json
secret||.hermes/pairing/p1.json
secret||.hermes/platforms/pairing/p1.json
secret||.hermes/whatsapp/session/creds.json
secret||.hermes/platforms/whatsapp/session/creds.json
secret||.hermes/matrix/store/s1
secret||.hermes/platforms/matrix/store/s1
secret||.hermes/cache/bws_cache1.json
secret||.hermes/weixin/accounts/a1.json
secret||.hermes/runtime/photon-sidecar.json
secret||.hermes/proxy/ca.key
secret||.hermes/home/.gitconfig
secret||AppData/Local/hermes/.env
secret||AppData/Local/hermes/.env.bak1
secret||AppData/Local/hermes/.op.env
secret||AppData/Local/hermes/npmrc
secret||AppData/Local/hermes/auth.json
secret||AppData/Local/hermes/auth.json.1
secret||AppData/Local/hermes/auth/google_oauth.json
secret||AppData/Local/hermes/.anthropic_oauth.json
secret||AppData/Local/hermes/.copilot_jwt.json
secret||AppData/Local/hermes/google_token.json
secret||AppData/Local/hermes/google_chat_user_tokens/u1.json
secret||AppData/Local/hermes/slack_tokens.json
secret||AppData/Local/hermes/honcho.json
secret||AppData/Local/hermes/mem0.json
secret||AppData/Local/hermes/webhook_subscriptions.json
secret||AppData/Local/hermes/teams_pipeline_store.json
secret||AppData/Local/hermes/mcp-tokens/t1.json
secret||AppData/Local/hermes/vault/vault.key
secret||AppData/Local/hermes/browser_auth/state.json
secret||AppData/Local/hermes/pairing/p1.json
secret||AppData/Local/hermes/platforms/pairing/p1.json
secret||AppData/Local/hermes/whatsapp/session/creds.json
secret||AppData/Local/hermes/platforms/whatsapp/session/creds.json
secret||AppData/Local/hermes/matrix/store/s1
secret||AppData/Local/hermes/platforms/matrix/store/s1
secret||AppData/Local/hermes/cache/bws_cache1.json
secret||AppData/Local/hermes/weixin/accounts/a1.json
secret||AppData/Local/hermes/runtime/photon-sidecar.json
secret||AppData/Local/hermes/proxy/ca.key
secret||AppData/Local/hermes/home/.gitconfig
secret||.hermes/profiles/work/.env
secret||.hermes_dev/auth.json
secret||.hermes/hermes-agent/.env
secret||AppData/Local/hermes/hermes-agent/.env
agent|hermes|.hermes/state.db
agent|hermes|.hermes/state.db-wal
agent|hermes|.hermes/state.db-shm
agent|hermes|.hermes/cache/terminal/out1.txt
agent|hermes|.hermes/hermes-agent/.env.example
agent|hermes|.hermes_dev/config.yaml
agent|hermes|AppData/Local/hermes/cache/terminal/out1.txt
agent|hermes|.config/Hermes/connection.json
excl||.openclaw/dev
excl||.openclaw/git
excl||.openclaw/npm
excl||.openclaw/npm-runtime
excl||.openclaw/tmp
excl||.openclaw/tools
excl||.openclaw/worktrees
excl||.openclaw/plugin-skills
excl||.openclaw/extensions/e1/node_modules
excl||.openclaw/sandbox/skills-workspaces
excl||.openclaw/agents/main/agent/tmp
excl||.openclaw/agents/main/agent/.tmp
excl||.openclaw/browser/b1/user-data/Default/Cache
excl||.openclaw/browser/b1/user-data/Default/Code Cache
excl||.openclaw/browser/b1/user-data/Default/GPUCache
excl||.openclaw/browser/b1/user-data/Default/Service Worker
excl||.openclaw-work/tools
excl||.clawdbot/tools
excl||.clawdbot/npm
secret||.openclaw/openclaw.json
secret||.openclaw/clawdbot.json.bak
secret||.openclaw-work/.env
secret||.openclaw/credentials/c1.json
secret||.openclaw/service-env/gateway.env
secret||.openclaw/agents/main/agent/auth-profiles.json
secret||.openclaw/agents/main/agent/models.json
secret||.openclaw/browser/b1/user-data/Default/Cookies
secret||.clawdbot/clawdbot.json
secret||.clawdbot/.env
secret||.clawdbot/credentials/c1
secret||.moltbot/moltbot.json
secret||.moltbot/.env
secret||.moltbot/credentials/c1
secret||.config/openclaw/gateway.env
agent|openclaw|.openclaw/agents/main/agent/openclaw-agent.sqlite
agent|openclaw|.openclaw/agents/main/agent/openclaw-agent.sqlite-wal
agent|openclaw|.openclaw-work/openclaw.json
agent|openclaw|.config/systemd/user/openclaw-gateway.service
agent|openclaw|Library/LaunchAgents/ai.openclaw.gateway.plist
excl||.nanobot/bin
excl||.nanobot/run
excl||.nanobot-work/cache
secret||.nanobot/config.json
secret||.nanobot/auth/a1
secret||.nanobot-work/whatsapp-auth/a1
secret||.nanobot/matrix-store/s1
agent|nanobot|.nanobot-work/sessions/0123456789abcdef0123456789abcdef/Y2xpOmRpcmVjdA.jsonl
agent|nanobot|Library/LaunchAgents/ai.nanobot.gateway.plist
excl||agent-zero/.venv
excl||Desktop/agent-zero/.conda
excl||agent-zero/main/.git
excl||agent-zero/main/tmp/playwright
excl||agent-zero/main/tmp/memory/embeddings
excl||agent-zero/main/usr/.time_travel
excl||agent-zero/main/usr/workdir/w1/.venv
excl||agent-zero/main/usr/workdir/w1/node_modules
excl||.local/share/a0/browser-profiles
excl||Library/Application Support/A0/Browser Profiles
excl||AppData/Local/A0/Browser Profiles
excl||.config/Agent Zero Launcher/Cache
excl||.config/Agent Zero Launcher/Code Cache
excl||.config/Agent Zero Launcher/GPUCache
excl||.config/Agent Zero Launcher/docker_manager/cache
secret||agent-zero/main/usr/.env
secret||agent-zero/main/usr/secrets.env
secret||Desktop/agent-zero/usr/settings.json
secret||agent-zero/main/usr/projects/p1/.a0proj/secrets.env
secret||agent-zero/.env
secret||agent-zero/main/tmp/secrets.env
secret||agent-zero/main/tmp/settings.json
secret||agent-zero/main/usr/plugins/_desktop/profiles/d1/.ssh/id_ed25519
secret||agent-zero/main/usr/plugins/_desktop/profiles/d1/.gnupg/k1
secret||.agent-zero/.env
secret||.agent-zero/session_cookies.json
secret||.config/Agent Zero Launcher/docker_manager/state.json
secret||.config/Agent Zero Launcher/Local State
agent|agent-zero|agent-zero/main/usr/chats/c1/chat.json
agent|agent-zero|Desktop/agent-zero/usr/chats/c1/chat.json
agent|agent-zero|.local/share/a0/config.json
secret||.config/shell_gpt/.sgptrc
agent|shellgpt|AppData/Local/Temp/chat_cache/mychat
agent|shellgpt|.config/shell_gpt/roles/default.json
excl||.local/share/local-deep-research/cache
excl||.local/share/local-deep-research/models
excl||.local/share/local-deep-research/journal_data
excl||.local/share/local-deep-research/library
excl||Library/Application Support/local-deep-research/cache
excl||Library/Application Support/local-deep-research/models
excl||Library/Application Support/local-deep-research/journal_data
excl||Library/Application Support/local-deep-research/library
excl||AppData/Local/local-deep-research/local-deep-research/cache
excl||AppData/Local/local-deep-research/local-deep-research/models
excl||AppData/Local/local-deep-research/local-deep-research/journal_data
excl||AppData/Local/local-deep-research/local-deep-research/library
excl||Documents/LocalDeepResearch/Library
secret||.local/share/local-deep-research/.secret_key
secret||Library/Application Support/local-deep-research/.secret_key
secret||AppData/Local/local-deep-research/local-deep-research/.secret_key
agent|local-deep-research|.local/share/local-deep-research/encrypted_databases/u1.db
agent|local-deep-research|Documents/LocalDeepResearch/report.md
'@
$Cases14 = @($Cases14 -split "`r?`n" | Where-Object { $_ -ne '' })
foreach ($c in $Cases14) {
  $f = @($c -split '\|', 3)
  if ($f[0] -eq 'excl') { Mk "Users/alice/$($f[2])/f" 'x' } else { Mk "Users/alice/$($f[2])" 'x' }
}
Mk 'Users/alice/.hermes/checkpoints/store/projects/0123456789abcdef.json' '{"workdir":"C:\\hermesproj","created_at":1759536000}'
Mk 'hermesproj/.hermes.md' '# hermes'
Mk 'Users/alice/.letta/sessions.jsonl' '{"type":"start","project":"C:\\lettaproj","agentId":"a1"}'
Mk 'lettaproj/.letta/settings.json' '{"hooks":{}}'
Mk 'Users/alice/.letta/lc-local-backend/conversations/c1/messages.jsonl' '{"type":"session","id":"c1","cwd":"C:\\lettaproj2"}'
Mk 'lettaproj2/AGENTS.md' '# letta'
Mk 'Users/alice/.pi/agent/sessions/--C--piproj--/2026-10-04T00-00-00-000Z_u1.jsonl' '{"type":"session","version":3,"id":"u1","cwd":"C:\\piproj"}'
Mk 'piproj/.pi/settings.json' '{}'
Mk 'Users/alice/.pi/agent/2026-10-01T00-00-00-000Z_u2.jsonl' '{"type":"session","version":1,"id":"u2","cwd":"C:\\piproj2"}'
Mk 'piproj2/AGENTS.md' '# pi'
Mk 'Users/alice/.pi/agent/trust.json' '{"C:\\pitrust":true}'
Mk 'pitrust/pi-session-2026-10-04.html' '<html></html>'
Mk 'Users/alice/.pi/agent/crashes.json' '[{"cwd":"C:\\picrash","sessionFile":"x.jsonl"}]'
Mk 'picrash/AGENTS.md' '# pi'
Mk 'Users/alice/.pi/agent/experimental/sessions/s1/meta.json' '{"id":"s1","cwd":"C:\\piexp"}'
Mk 'piexp/AGENTS.md' '# pi'
Mk 'Users/alice/.openinterpreter/sessions/2026/10/04/rollout-2026-10-04T00-00-00-u1.jsonl' '{"type":"session_meta","payload":{"cwd":"C:\\oiproj"}}'
Mk 'oiproj/.openinterpreter/rules/r.md' 'rule'
Mk 'Users/alice/.openinterpreter/archived_sessions/rollout-2026-10-01T00-00-00-u2.jsonl' '{"type":"session_meta","payload":{"cwd":"C:\\oiarch"}}'
Mk 'oiarch/.codewhale/notes.md' 'notes'
Mk 'Users/alice/.openhands/workspaces.json' '{"workspaces":[{"id":"w1","path":"C:\\ohproj"}],"workspaceParents":[]}'
Mk 'ohproj/.openhands/setup.sh' 'echo setup'
Mk 'Users/alice/.openhands/agent-canvas/dev_conversations/a1/meta.json' '{"workspace":{"working_dir":"C:\\ohdev"}}'
Mk 'Users/alice/.openhands/agent-canvas/conversations/a2/meta.json' '{"workspace":{"working_dir":"C:\\ohcanvas"}}'
Mk 'Users/alice/.openhands/conversations/a3/base_state.json' '{"workspace":{"working_dir":"C:\\ohcli"}}'
foreach ($d in @('ohdev', 'ohcanvas', 'ohcli')) { Mk "$d/AGENTS.md" '# oh' }
Mk 'Users/alice/.pearai/sessions/sessions.json' '[{"sessionId":"s1","title":"t","workspaceDirectory":"C:\\pearproj"}]'
Mk 'pearproj/.pearairc.json' '{}'
Mk 'pearproj/.pearai-agent/mcp.json' '{"mcpServers":{}}'
Mk 'Users/alice/.openclaw/openclaw.json' "{`n  // JSON5`n  agents: {`n    defaults: { workspace: 'C:\\clawws' },`n    entries: { main: { agentDir: `"C:\\clawagent`" } },`n  },`n}"
Mk 'Users/alice/.clawdbot/clawdbot.json' '{"agents":{"defaults":{"workspace":"C:\\clawlegacy"}}}'
Mk 'Users/alice/.openclaw-work/openclaw.json' '{agents:{defaults:{workspace:"C:\\clawprofile"}}}'
Mk 'clawws/SOUL.md' '# soul'
Mk 'clawagent/AGENTS.md' '# a'
Mk 'clawlegacy/IDENTITY.md' '# id'
Mk 'clawprofile/MEMORY.md' '# mem'
Mk 'home/bob/.openclaw/openclaw.json' '{}'
Mk 'Users/alice/.nanobot/sessions/0123456789abcdef0123456789abcdef/.workspace' 'C:\nanows'
Mk 'nanows/HEARTBEAT.md' '# hb'
Mk 'Users/alice/.nanobot-work/config.json' '{"agents":{"defaults":{"workspace":"C:\\nanocfg"}}}'
Mk 'nanocfg/memory/MEMORY.md' '# mem'
Mk 'Users/alice/.tabby/config.toml' "[[repositories]]`nname = `"p`"`ngit_url = `"file:///C:/tabbyproj`"`n[[repositories]]`nname = `"u`"`ngit_url = 'file:///srv/tabbyunix'`n"
Mk 'tabbyproj/AGENTS.md' '# tabby'
Mk 'srv/tabbyunix/AGENTS.md' '# tabby'
Mk 'Users/alice/.twinny/embeddings/twinproj/manifest.json' '{"files":{"C:\\twinproj\\src\\a.ts":{"hash":"h1"},"C:\\twinproj\\b.ts":{"hash":"h2"}}}'
Mk 'twinproj/AGENTS.md' '# twin'
# --- 1.5.0 Docker volumes (2026-10-04): a root Docker volume matched to Agent
# Zero, an unmatched volume, and a rootless volume in alice's profile.
Mk 'var/lib/docker/volumes/a0_usr/_data/chats/ctx1/chat.json' '{"id":"ctx1","name":"chat","history":"[]"}'
Mk 'var/lib/docker/volumes/a0_usr/_data/.env' 'API_KEY_OPENAI=sk-x'
Mk 'var/lib/docker/volumes/a0_usr/_data/tmp/playwright/junk' 'junk'
Mk 'var/lib/docker/volumes/pgdata/_data/x' 'pg'
Mk 'var/lib/docker/volumes/metadata.db' 'metadata'
Mk 'Users/alice/.local/share/docker/volumes/tabby_data/_data/events/2026-10-01.json' '{"event":"completion"}'
# --- 2026-10-04 Muse Code: Meta's coding agent CLI. Same case list as smoke.sh,
# relative to alice's profile. The Windows binary is a file exclusion, the Linux
# launcher state is a dot-file glob inside ~/.local/bin, and two discovery
# sources point at projects.
$CasesMuse = @'
excl||.local/share/muse/plugins/cache/builtin
excl||.local/share/muse/skills/bundled
excl||.local/share/muse/plugins/marketplaces
excl||.local/bin/.muse-update.Ab12Cd
excl||.muse/worktrees
exclf||AppData/Local/Programs/muse/muse-bin-1.4.2-R1.exe
exclf||AppData/Local/Programs/muse/.muse-update.4242.exe
secret||.config/muse/auth.json
secret||.config/muse/settings.json
agent|muse-code|.config/muse/trust.json
agent|muse-code|.local/share/muse/session-index.db
agent|muse-code|.local/share/muse/plugins/cache/local/p1/plugin.json
agent|muse-code|.local/bin/.muse-version
agent|muse-code|.local/bin/.muse-update-lock/pid
agent|muse-code|.muse/projects/slug/tracking.json
agent|muse-code|AppData/Local/Programs/muse/.muse-version
agent|muse-code|AppData/Local/Programs/muse/.muse-launcher.ps1
agent|muse-code|AppData/LocalLow/muse-shell-sandbox-01a0f000-0000-7000-8000-000000000001/tmp1.txt
'@
$CasesMuse = @($CasesMuse -split "`r?`n" | Where-Object { $_ -ne '' })
foreach ($c in $CasesMuse) {
  $f = @($c -split '\|', 3)
  if ($f[0] -eq 'excl') { Mk "Users/alice/$($f[2])/f" 'x' } else { Mk "Users/alice/$($f[2])" 'x' }
}
Mk 'Users/alice/.local/bin/othertool' 'x'
Mk 'Users/alice/.config/muse/trust.json' '{"schema_version":1,"projects":{"C:\\musetrust":{"decision":"trusted"}}}'
Mk 'Users/alice/.local/share/muse/sessions/2026/10/04/01a0f000-0000-7000-8000-000000000001/session.jsonl' '{"schema_version":1,"stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"payload_type":"runtime.session.metadata","payload":{"kind":"metadata","record":{"model_id":"m","workspace_root":"C:\\museproj"}}}'
Mk 'museproj/.muse/hooks.json' '{}'
Mk 'museproj/.muse/worktrees/w1/f' 'x'
Mk 'musetrust/AGENTS.md' '# trusted'

# --- 2026-10-04 relocated Claude Code home: a config home moved with
# CLAUDE_CONFIG_DIR to ~/.claude-work, which keeps .claude.json inside it, and
# claude-code-router's ~/.claude-code-router, which the .claude-* catalog lines
# must not claim. The same files are in smoke.sh.
$CcwS = 'alice/.claude-work/projects/-srv-ccwork/0a0b0c0d-0000-4000-8000-000000000001.jsonl'
Mk "Users/$CcwS" '{"type":"user","cwd":"C:\\ccwork","message":{"role":"user","content":"hi"}}'
Mk 'Users/alice/.claude-work/history.jsonl' '{"display":"hi","project":"C:\\cchist","timestamp":1790848800000}'
Mk 'Users/alice/.claude-work/.claude.json' '{"projects":{"C:\\ccwork":{"allowedTools":[]}}}'
Mk 'Users/alice/.claude-work/.credentials.json' '{"claudeAiOauth":{"accessToken":"sk-ant-oat-SECRET"}}'
Mk 'Users/alice/.claude-code-router/config.json' '{"PORT":3456}'
Mk 'ccwork/.claude/settings.json' '{}'
Mk 'cchist/.claude/settings.json' '{}'
$clawLinkOk = $false
try {
  New-Item -ItemType SymbolicLink -Path (P 'home/bob/.clawdbot') -Target '.openclaw' -ErrorAction Stop | Out-Null
  $clawLinkOk = $true
} catch { Write-Output "note: symlink creation not permitted here, .clawdbot symlink check skipped" }
$linkOk = $false
try {
  New-Item -ItemType SymbolicLink -Path (P 'Users/alice/.gemini/antigravity-cli/cli.log') -Target (Join-Path 'log' 'cli-1.log') -ErrorAction Stop | Out-Null
  $linkOk = $true
} catch { Write-Output "note: symlink creation not permitted here, symlink checks skipped" }

# ---- runner ---------------------------------------------------------------
function Run([string]$name, [hashtable]$extra) {
  $o = Join-Path $Out $name
  New-Item -ItemType Directory -Path $o -Force | Out-Null
  $cargs = @{ Root = $Root; OutputDir = $o; Quiet = $true; MaxFileSizeMB = 1 }
  foreach ($k in $extra.Keys) { $cargs[$k] = $extra[$k] }
  $global:LASTEXITCODE = 0
  $script:stdout = & $Collector @cargs 2>&1 | Out-String
  $script:rc = $LASTEXITCODE
  $script:M = Get-ChildItem -LiteralPath $o -Filter '*.manifest.jsonl' | Select-Object -First 1
  $script:A = Get-ChildItem -LiteralPath $o | Where-Object { $_.Name -match '\.(tar\.gz|zip)$' } | Select-Object -First 1
  $script:S = Get-ChildItem -LiteralPath $o -Filter '*.collection.json' | Select-Object -First 1
  $script:Rows = @()
  if ($script:M) { $script:Rows = @(Get-Content -LiteralPath $script:M.FullName | ForEach-Object { $_ | ConvertFrom-Json }) }
}
function Row([string]$suffix) {
  $s = $suffix.Replace('\', '/')
  return ($script:Rows | Where-Object { ($_.path -replace '\\', '/').ToLowerInvariant().EndsWith($s.ToLowerInvariant()) } | Select-Object -First 1)
}
function StatusOf([string]$suffix) { $r = Row $suffix; if ($r) { return $r.status } else { return '' } }
function ArchiveEntries {
  if ($script:A.Name -like '*.tar.gz') { return @(& tar -tzf $script:A.FullName 2>$null) }
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $z = [System.IO.Compression.ZipFile]::OpenRead($script:A.FullName)
  try { return @($z.Entries | ForEach-Object { $_.FullName }) } finally { $z.Dispose() }
}

# ---- default run ----------------------------------------------------------
Run 'default' @{}
Check 'exit code 0' { $script:rc -eq 0 }
Check 'archive exists' { $null -ne $script:A -and $script:A.Length -gt 0 }
Check 'sha256 sidecar matches' { (Get-Content -LiteralPath "$($script:A.FullName).sha256").Split(' ')[0] -eq (Get-FileHash -LiteralPath $script:A.FullName -Algorithm SHA256).Hash.ToLower() }
Check 'transcript collected' { (StatusOf 'Users/alice/.claude/projects/-C-proj/s1.jsonl') -eq 'collected' }
$r = Row 'Users/alice/.claude/projects/-C-proj/s1.jsonl'
Check 'transcript hash correct' { $r -and $r.sha256 -eq (Get-FileHash -LiteralPath (P 'Users/alice/.claude/projects/-C-proj/s1.jsonl') -Algorithm SHA256).Hash.ToLower() }
Check 'transcript has owner and attributes fields' { $r -and $null -ne $r.owner -and $r.attributes -ne '' }
$r = Row 'Users/alice/.claude/.credentials.json'
Check 'secret collected and flagged' { $r -and $r.secret -eq $true -and $r.status -eq 'collected' }
Check 'antigravity token flagged secret' { (Row 'antigravity-cli/antigravity-oauth-token').secret -eq $true }
$r = Row 'Users/alice/.gemini/antigravity-cli/conversations/c1.db'
Check 'nested entry attributed to its own agent' { $r -and $r.agent -eq 'antigravity' }
Check 'nested entry collected exactly once' { @($script:Rows | Where-Object { $_.path -like '*antigravity-cli*conversations*c1.db' }).Count -eq 1 }
$r = Row 'Users/alice/.gemini/projects.json'
Check 'enclosing entry still attributed to gemini-cli' { $r -and $r.agent -eq 'gemini-cli' }
$r = Row 'Users/alice/AppData/Roaming/Code/User/globalStorage/saoudrizwan.claude-dev/state/taskHistory.json'
Check 'cline globalStorage attributed to cline, not vscode' { $r -and $r.agent -eq 'cline' }
Check 'cline globalStorage collected exactly once' { @($script:Rows | Where-Object { $_.path -like '*Roaming*Code*User*globalStorage*saoudrizwan.claude-dev*taskHistory.json' }).Count -eq 1 }
$r = Row 'Users/alice/.claude/cache'
Check 'cache dir skipped_excluded with size' { $r -and $r.type -eq 'dir' -and $r.size -gt 0 -and $r.status -eq 'skipped_excluded' }
Check 'cache contents not collected' { $null -eq (Row 'cache/junk.bin') }
Check 'antigravity bin excluded' { (StatusOf 'antigravity-cli/bin') -eq 'skipped_excluded' }
Check 'codex packages excluded' { (StatusOf 'Users/alice/.codex/packages') -eq 'skipped_excluded' }
Check 'ollama models excluded' { (StatusOf 'home/bob/.ollama/models') -eq 'skipped_excluded' }
Check 'ollama history collected (linux-style home in same image)' { (StatusOf 'home/bob/.ollama/history') -eq 'collected' }
Check 'bash history not collected' { -not ($script:Rows | Where-Object { $_.path -like '*.bash_history' }) }
Check 'PSReadLine history not collected' { -not ($script:Rows | Where-Object { $_.path -like '*ConsoleHost_history.txt' }) }
Check 'oversized file skipped_size' { (StatusOf 'Cursor/User/globalStorage/state.vscdb') -eq 'skipped_size' }
Check 'ms-python globalStorage excluded' { (StatusOf 'globalStorage/ms-python.python') -eq 'skipped_excluded' }
Check 'cline checkpoints excluded' { (StatusOf 'saoudrizwan.claude-dev/checkpoints') -eq 'skipped_excluded' }
Check 'weird filename collected' { (StatusOf 'weird name with spaces & [brackets].txt') -eq 'collected' }
if ($linkOk) {
  $r = Row 'antigravity-cli/cli.log'
  Check 'symlink recorded with target' { $r -and $r.type -eq 'symlink' -and $r.status -eq 'symlink' -and $r.target -like '*cli-1.log' }
}
Check 'project from history.jsonl (drive path mapped into image) collected' { (StatusOf 'proj/CLAUDE.md') -eq 'collected' }
Check 'project .claude settings collected' { (StatusOf 'proj/.claude/settings.local.json') -eq 'collected' }
Check 'project owner attributed' { (Row 'proj/CLAUDE.md').user -eq 'alice' }
Check 'project from workspace.json file URI collected' { (StatusOf 'Documents/app/.cursorrules') -eq 'collected' }
Check 'project from codex rollout cwd collected' { (StatusOf 'Documents/app/AGENTS.md') -eq 'collected' }
Check 'project from cline taskHistory collected' { (StatusOf 'cl/.clinerules') -eq 'collected' }
Check 'project from continue sessions.json collected' { (StatusOf 'cont/.continuerc.json') -eq 'collected' }
Check 'project from gemini projects.json collected' { (StatusOf 'gem/GEMINI.md') -eq 'collected' }
Check 'project-local crush.db from projects.json collected' { (StatusOf 'crushproj/.crush/crush.db') -eq 'collected' }
Check 'continue globalContext flagged secret' { (Row 'index/globalContext.json').secret -eq $true }
Check 'continue lancedb excluded' { (StatusOf 'index/lancedb') -eq 'skipped_excluded' }
Check 'cline providers.json flagged secret' { (Row 'settings/providers.json').secret -eq $true }
Check 'codex auth.json flagged secret' { (Row 'Users/alice/.codex/auth.json').secret -eq $true }
Check 'home .env not collected' { -not (Row 'Users/alice/.env') }
Check 'claude desktop config.json flagged secret' { (Row 'Roaming/Claude/config.json').secret -eq $true }
$r = Row 'Claude/claude_desktop_config.json'
Check 'factory session index not swallowed by cache exclusion' { (StatusOf 'Users/alice/.factory/cache/session-index/index.db') -eq 'collected' }
Check 'factory cache sounds excluded' { (StatusOf 'Users/alice/.factory/cache/sounds') -eq 'skipped_excluded' }
Check 'factory session cwd discovers project' { (StatusOf 'droid/AGENTS.md') -eq 'collected' }
$r2 = Row 'Users/alice/.kiro/powers/installed/p1/mcp.json'
Check 'kiro power mcp.json collected and flagged' { $r2 -and $r2.secret -eq $true -and $r2.status -eq 'collected' }
Check 'kiro cli session cwd discovers project' { (StatusOf 'kiroproj/.kiroignore') -eq 'collected' }
Check 'vscode-server User dir collected as vscode' { (Row 'Users/alice/.vscode-server/data/User/globalStorage/state.vscdb').agent -eq 'vscode' }
Check 'cline inside vscode-server attributed to cline' { (Row 'Users/alice/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/state/taskHistory.json').agent -eq 'cline' }
Check 'vscode-server taskHistory discovers project' { (StatusOf 'remoteproj/.clinerules') -eq 'collected' }
Check 'antigravity-ide attributed to antigravity' { (Row 'Users/alice/.gemini/antigravity-ide/conversations/i1.db').agent -eq 'antigravity' }
Check 'antigravity history workspace discovers project' { (StatusOf 'agyproj/.antigravityignore') -eq 'collected' }
Check 'cursor auth.json flagged secret' { (Row 'Users/alice/.cursor/auth.json').secret -eq $true }
Check 'copilot pkg excluded' { (StatusOf 'Users/alice/.copilot/pkg') -eq 'skipped_excluded' }
Check 'copilot config.json flagged secret' { (Row 'Users/alice/.copilot/config.json').secret -eq $true }
Check 'copilot workspace.yaml cwd discovers project' { (StatusOf 'copproj/AGENTS.md') -eq 'collected' }
Check 'claude device keys flagged secret' { (Row 'Users/alice/.claude/.device-keys.json').secret -eq $true }
Check 'amp history cwd discovers project' { (StatusOf 'ampproj/.amp/settings.json') -eq 'collected' }
Check 'project-level kilo worktrees excluded' { (StatusOf 'kiloproj/.kilo/worktrees') -eq 'skipped_excluded' }
Check 'claude desktop mcp config flagged secret' { $r -and $r.secret -eq $true -and $r.status -eq 'collected' }
Check 'claude desktop Cache excluded' { (StatusOf 'Roaming/Claude/Cache') -eq 'skipped_excluded' }
# 1.4.0 catalog round (2026-10-04)
foreach ($c in $Cases14) {
  $f = @($c -split '\|', 3); $r = Row "alice/$($f[2])"
  switch ($f[0]) {
    'excl' { Check "excluded: $($f[2])" { $r -and $r.status -eq 'skipped_excluded' } }
    'exclf' { Check "excluded: $($f[2])" { $r -and $r.status -eq 'skipped_excluded' } }
    'secret' { Check "secret: $($f[2])" { $r -and $r.secret -eq $true -and $r.status -eq 'collected' } }
    'agent' { Check "$($f[1]): $($f[2])" { $r -and $r.agent -eq $f[1] -and $r.status -eq 'collected' } }
  }
}
# On a case-insensitive filesystem .config/PearAI/User matches the same directory, so only attribution is checked here
$pr = @($script:Rows | Where-Object { ($_.path -replace '\\', '/') -like '*/.config/pearai/User/globalStorage/state.vscdb' })
Check 'pearai lowercase .config/pearai collected as pearai' { $pr.Count -ge 1 -and @($pr | Where-Object { $_.agent -ne 'pearai' }).Count -eq 0 }
Check 'cody nested globalStorage collected exactly once' { @($script:Rows | Where-Object { ($_.path -replace '\\', '/') -like '*sourcegraph.cody-ai/symf/indexroot/meta.json' }).Count -eq 1 }
Check 'twinny nested globalStorage collected exactly once' { @($script:Rows | Where-Object { ($_.path -replace '\\', '/') -like '*globalStorage/rjmacarthy.twinny/twinny-providers.json' }).Count -eq 1 }
Check 'little-coder history nested in .pi collected exactly once' { @($script:Rows | Where-Object { $_.path -like '*little-coder-prompt-history.json' }).Count -eq 1 }
Check 'hermes installer checkout excluded but its .env kept' { (StatusOf 'alice/.hermes/hermes-agent/hermes_cli') -eq 'skipped_excluded' -and (StatusOf 'alice/.hermes/hermes-agent/.env') -eq 'collected' }
if ($clawLinkOk) {
  $r = Row 'home/bob/.clawdbot'
  Check 'openclaw .clawdbot rename symlink recorded' { $r -and $r.agent -eq 'openclaw' -and $r.type -eq 'symlink' -and $r.status -eq 'symlink' -and $r.target -like '*.openclaw' }
}
Check 'hermes checkpoint workdir discovers project' { (StatusOf 'hermesproj/.hermes.md') -eq 'collected' -and (Row 'hermesproj/.hermes.md').user -eq 'alice' }
Check 'letta sessions.jsonl project discovers project' { (StatusOf 'lettaproj/.letta/settings.json') -eq 'collected' }
Check 'project .letta/settings.json flagged secret (accepted overmatch)' { (Row 'lettaproj/.letta/settings.json').secret -eq $true }
Check 'letta local backend messages cwd discovers project' { (StatusOf 'lettaproj2/AGENTS.md') -eq 'collected' }
Check 'pi session cwd discovers project' { (StatusOf 'piproj/.pi/settings.json') -eq 'collected' }
Check 'pi misplaced session cwd discovers project' { (StatusOf 'piproj2/AGENTS.md') -eq 'collected' }
Check 'pi trust.json keys discover project' { (StatusOf 'pitrust/pi-session-2026-10-04.html') -eq 'collected' }
Check 'pi crashes.json cwd discovers project' { (StatusOf 'picrash/AGENTS.md') -eq 'collected' }
Check 'pi experimental meta cwd discovers project' { (StatusOf 'piexp/AGENTS.md') -eq 'collected' }
Check 'open-interpreter rollout cwd discovers project' { (StatusOf 'oiproj/.openinterpreter/rules/r.md') -eq 'collected' }
Check 'open-interpreter archived rollout cwd discovers project' { (StatusOf 'oiarch/.codewhale/notes.md') -eq 'collected' }
Check 'openhands workspaces.json path discovers project' { (StatusOf 'ohproj/.openhands/setup.sh') -eq 'collected' }
Check 'openhands canvas dev conversation discovers project' { (StatusOf 'ohdev/AGENTS.md') -eq 'collected' }
Check 'openhands canvas conversation discovers project' { (StatusOf 'ohcanvas/AGENTS.md') -eq 'collected' }
Check 'openhands cli base_state discovers project' { (StatusOf 'ohcli/AGENTS.md') -eq 'collected' }
Check 'pearai sessions.json discovers project' { (StatusOf 'pearproj/.pearairc.json') -eq 'collected' }
$r = Row 'pearproj/.pearai-agent/mcp.json'
Check 'project .pearai-agent/mcp.json flagged secret' { $r -and $r.secret -eq $true -and $r.status -eq 'collected' }
Check 'openclaw JSON5 workspace discovers project' { (StatusOf 'clawws/SOUL.md') -eq 'collected' }
Check 'openclaw JSON5 agentDir discovers project' { (StatusOf 'clawagent/AGENTS.md') -eq 'collected' }
Check 'openclaw legacy clawdbot.json discovers project' { (StatusOf 'clawlegacy/IDENTITY.md') -eq 'collected' }
Check 'openclaw profile config discovers project' { (StatusOf 'clawprofile/MEMORY.md') -eq 'collected' }
Check 'nanobot .workspace marker discovers project' { (StatusOf 'nanows/HEARTBEAT.md') -eq 'collected' }
Check 'nanobot instance config workspace discovers project' { (StatusOf 'nanocfg/memory/MEMORY.md') -eq 'collected' }
Check 'tabby config.toml file:// git_url (drive) discovers project' { (StatusOf 'tabbyproj/AGENTS.md') -eq 'collected' }
Check 'tabby config.toml file:// git_url (unix) discovers project' { (StatusOf 'srv/tabbyunix/AGENTS.md') -eq 'collected' }
Check 'twinny manifest common prefix discovers project' { (StatusOf 'twinproj/AGENTS.md') -eq 'collected' }
# 1.5.0 Docker volumes (2026-10-04)
$r = Row 'var/lib/docker/volumes/a0_usr/_data/chats/ctx1/chat.json'
Check 'docker volume file collected as agent-zero, user docker' { $r -and $r.user -eq 'docker' -and $r.agent -eq 'agent-zero' -and $r.status -eq 'collected' -and ($r.home -replace '\\', '/').EndsWith('var/lib/docker/volumes/a0_usr/_data') }
$r = Row 'var/lib/docker/volumes/a0_usr/_data/.env'
Check 'docker volume .env flagged secret (volume-relative)' { $r -and $r.secret -eq $true -and $r.status -eq 'collected' }
Check 'docker volume tmp/playwright excluded (volume-relative)' { (StatusOf 'var/lib/docker/volumes/a0_usr/_data/tmp/playwright') -eq 'skipped_excluded' }
$r = Row 'var/lib/docker/volumes/pgdata/_data'
Check 'unmatched volume recorded skipped_unmatched_volume with size' { $r -and $r.user -eq 'docker' -and $r.type -eq 'dir' -and $r.size -gt 0 -and $r.status -eq 'skipped_unmatched_volume' }
Check 'unmatched volume contents not collected' { $null -eq (Row 'pgdata/_data/x') }
Check 'volumes dir metadata.db not collected' { $null -eq (Row 'volumes/metadata.db') }
$r = Row 'Users/alice/.local/share/docker/volumes/tabby_data/_data/events/2026-10-01.json'
Check 'rootless volume collected as tabby' { $r -and $r.user -eq 'docker' -and $r.agent -eq 'tabby' -and $r.status -eq 'collected' }
# 2026-10-04 Muse Code
foreach ($c in $CasesMuse) {
  $f = @($c -split '\|', 3); $r = Row "alice/$($f[2])"
  switch ($f[0]) {
    'excl' { Check "excluded: $($f[2])" { $r -and $r.agent -eq 'muse-code' -and $r.status -eq 'skipped_excluded' } }
    'exclf' { Check "excluded: $($f[2])" { $r -and $r.agent -eq 'muse-code' -and $r.status -eq 'skipped_excluded' } }
    'secret' { Check "secret: $($f[2])" { $r -and $r.agent -eq 'muse-code' -and $r.secret -eq $true -and $r.status -eq 'collected' } }
    'agent' { Check "$($f[1]): $($f[2])" { $r -and $r.agent -eq $f[1] -and $r.status -eq 'collected' } }
  }
}
$r = Row 'alice/AppData/Local/Programs/muse/muse-bin-1.4.2-R1.exe'
Check 'muse windows binary excluded with its size' { $r -and $r.type -eq 'file' -and $r.size -eq 1 -and $r.status -eq 'skipped_excluded' }
Check 'muse .local/bin glob leaves other tools alone' { $null -eq (Row 'alice/.local/bin/othertool') }
Check 'muse trust.json projects key discovers project' { (StatusOf 'musetrust/AGENTS.md') -eq 'collected' -and (Row 'musetrust/AGENTS.md').user -eq 'alice' }
$r = Row 'museproj/.muse/hooks.json'
Check 'muse session.jsonl workspace_root discovers project' { $r -and $r.user -eq 'alice' -and $r.agent -eq 'project' -and $r.status -eq 'collected' }
Check 'muse project .muse/worktrees excluded' { (StatusOf 'museproj/.muse/worktrees') -eq 'skipped_excluded' }
# 2026-10-04 relocated Claude Code home
$r = Row $CcwS
Check 'relocated claude home session collected as claude-code' { $r -and $r.agent -eq 'claude-code' -and $r.status -eq 'collected' }
$r = Row 'alice/.claude-work/history.jsonl'
Check 'relocated claude home history collected as claude-code' { $r -and $r.agent -eq 'claude-code' -and $r.status -eq 'collected' }
$r = Row 'alice/.claude-work/.credentials.json'
Check 'relocated claude home credentials flagged secret' { $r -and $r.agent -eq 'claude-code' -and $r.secret -eq $true -and $r.status -eq 'collected' }
$r = Row 'alice/.claude-work/.claude.json'
Check 'relocated claude home .claude.json flagged secret' { $r -and $r.agent -eq 'claude-code' -and $r.secret -eq $true -and $r.status -eq 'collected' }
Check 'claude-code-router not collected' { $null -eq (Row 'alice/.claude-code-router/config.json') }
$r = Row 'ccwork/.claude/settings.json'
Check 'relocated .claude.json projects key discovers project' { $r -and $r.user -eq 'alice' -and $r.agent -eq 'project' -and $r.status -eq 'collected' }
$r = Row 'cchist/.claude/settings.json'
Check 'relocated history.jsonl discovers project' { $r -and $r.user -eq 'alice' -and $r.agent -eq 'project' -and $r.status -eq 'collected' }
Check 'Public profile skipped' { $null -eq (Row 'Public/Desktop/readme.txt') }
Check 'Default profile skipped' { $null -eq (Row 'Default/NTUSER.DAT') }
$entries = ArchiveEntries
Check 'no live snapshot directory' { -not ($entries | Where-Object { $_ -match '(^|/)live/' }) }
Check 'manifest and summary inside archive' { ($entries | Where-Object { $_ -match 'manifest\.jsonl$' }) -and ($entries | Where-Object { $_ -match 'collection\.json$' }) }
Check 'archive layout is fs/<path relative to root>' { @($entries | Where-Object { $_ -match '(^|\./)fs/Users/alice/\.claude/history\.jsonl$' }).Count -eq 1 }
Check 'staging removed' { -not (Get-ChildItem -LiteralPath (Join-Path $Out 'default') -Filter '.stage-*' -Force) }
$sum = Get-Content -LiteralPath $script:S.FullName -Raw | ConvertFrom-Json
Check 'summary is valid JSON with zero copy errors' { $sum.counts.error_copy -eq 0 }
Check 'summary has no no_live option' { $null -eq $sum.options.PSObject.Properties['no_live'] }
Check 'summary counts match manifest' { $sum.counts.collected -eq @($script:Rows | Where-Object { $_.status -eq 'collected' }).Count }
Check 'manifest rows all parsed as JSON' { $script:Rows.Count -eq @(Get-Content -LiteralPath $script:M.FullName).Count }
Check 'archive layout for a docker volume file is fs/<path relative to root>' { @($entries | Where-Object { $_ -match '(^|\./)fs/var/lib/docker/volumes/a0_usr/_data/chats/ctx1/chat\.json$' }).Count -eq 1 }
Check 'summary counts skipped_unmatched_volume' { $sum.counts.skipped_unmatched_volume -eq 1 }
Check 'summary docker counts' { $sum.docker.volumes_found -eq 3 -and $sum.docker.volumes_collected -eq 2 -and $sum.docker.unreadable -eq 0 -and $sum.docker.docker_desktop -eq $false }
Check 'summary no_docker option false and notes empty' { $sum.options.no_docker -eq $false -and @($sum.notes).Count -eq 0 }
Check 'stdout docker line' { $script:stdout -match '(?m)^docker:     3 volumes found, 2 collected, 0 unreadable\s*$' }
Check 'profile without artifacts still listed in users' { @($sum.users) -contains 'dave' }
Check 'profile without artifacts not in users_with_artifacts' { @($sum.users_with_artifacts).Count -gt 0 -and -not (@($sum.users_with_artifacts) -contains 'dave') }
Check 'stdout users counts users_with_artifacts' { $script:stdout -match "(?m)^users:      $(@($sum.users_with_artifacts).Count)\s*$" }
Check 'log has no progress line for a profile without artifacts' { $lg = Get-Content -LiteralPath (Get-ChildItem -LiteralPath (Join-Path $Out 'default') -Filter '*.log' | Select-Object -First 1).FullName -Raw; $lg -notmatch 'User dave' -and $lg -match 'User alice' }
Check 'stdout size is human-readable' { $script:stdout -match '(?m)^size:       \d+ \([0-9.]+ (B|KiB|MiB)\)\s*$' }
Check 'stdout collected bytes are human-readable' { $script:stdout -match '(?m)^collected:  \d+ files, \d+ bytes \([0-9.]+ (B|KiB|MiB)\)\s*$' }

# cross-check archived bytes against manifest hashes
$x = Join-Path $Work 'x'; New-Item -ItemType Directory -Path $x -Force | Out-Null
if ($script:A.Name -like '*.tar.gz') { & tar -xzf $script:A.FullName -C $x 2>$null } else { [System.IO.Compression.ZipFile]::ExtractToDirectory($script:A.FullName, $x) }
$n = 0; $bad = 0
foreach ($row in ($script:Rows | Where-Object { $_.status -eq 'collected' -and $_.archive_path })) {
  $f = Join-Path $x ($row.archive_path.Replace('/', $Sep))
  if (-not (Test-Path -LiteralPath $f)) { $bad++; continue }
  if ((Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash.ToLower() -ne $row.sha256) { $bad++ }
  if ((Get-Item -LiteralPath $f -Force).Length -ne $row.size) { $bad++ }
  $n++
}
Check "archived file bytes match manifest hashes ($n files)" { $bad -eq 0 -and $n -gt 10 }

# ---- -NoSecrets -----------------------------------------------------------
Run 'nosecrets' @{ NoSecrets = $true }
Check 'NoSecrets exit 0' { $script:rc -eq 0 }
Check 'credentials skipped_secret' { (StatusOf 'Users/alice/.claude/.credentials.json') -eq 'skipped_secret' }
Check 'credentials absent from archive' { -not (ArchiveEntries | Where-Object { $_ -match 'credentials\.json$' }) }

# ---- -Full ----------------------------------------------------------------
Run 'full' @{ Full = $true }
Check 'Full exit 0' { $script:rc -eq 0 }
Check 'cache contents collected with -Full' { (StatusOf 'cache/junk.bin') -eq 'collected' }

# ---- -Users ---------------------------------------------------------------
Run 'users' @{ Users = 'bob' }
Check 'Users exit 0' { $script:rc -eq 0 }
Check 'only bob collected' { (-not ($script:Rows | Where-Object { $_.user -eq 'alice' })) -and ($script:Rows | Where-Object { $_.user -eq 'bob' }) }

# ---- -NoDocker -------------------------------------------------------------
Run 'nodocker' @{ NoDocker = $true }
Check 'NoDocker exit 0' { $script:rc -eq 0 }
Check 'NoDocker collects no volume' { -not ($script:Rows | Where-Object { ($_.path -replace '\\', '/') -like '*docker/volumes*' }) }
$sum = Get-Content -LiteralPath $script:S.FullName -Raw | ConvertFrom-Json
Check 'NoDocker recorded in options' { $sum.options.no_docker -eq $true }
Check 'NoDocker prints no docker line' { $script:stdout -notmatch '(?m)^docker:' }

# ---- Docker Desktop note ----------------------------------------------------
Mk 'Users/alice/AppData/Local/Docker/wsl/disk/readme.txt' 'vhdx lives here'
Run 'desktop' @{}
Check 'Docker Desktop exit 0' { $script:rc -eq 0 }
$sum = Get-Content -LiteralPath $script:S.FullName -Raw | ConvertFrom-Json
Check 'Docker Desktop noted in collection.json' { $sum.docker.docker_desktop -eq $true -and @($sum.notes | Where-Object { $_ -like 'docker: Docker Desktop data at *' }).Count -eq 1 }
Check 'Docker Desktop noted in stdout' { $script:stdout -match '(?m)^docker:     3 volumes found, 2 collected, 0 unreadable; Docker Desktop VM disk not collected\s*$' }
Remove-Item -LiteralPath (P 'Users/alice/AppData/Local/Docker') -Recurse -Force

# ---- -Inventory (1.6.0, 2026-10-04) ---------------------------------------
# Stat-only fleet inventory: JSON Lines on stdout, nothing written anywhere.
function Inv([hashtable]$extra) {
  $cargs = @{ Root = $Root; Inventory = $true; Quiet = $true }
  foreach ($k in $extra.Keys) { $cargs[$k] = $extra[$k] }
  $global:LASTEXITCODE = 0
  $script:invLines = @(& $Collector @cargs 2>$null | ForEach-Object { [string]$_ })
  $script:rc = $LASTEXITCODE
  $script:inv = @($script:invLines | ForEach-Object { $_ | ConvertFrom-Json })
}
function InvAgent([string]$user, [string]$agent) { return ($script:inv | Where-Object { $_.type -eq 'agent' } | Where-Object { $_.user -eq $user -and $_.agent -eq $agent } | Select-Object -First 1) }
# The raw line, for the timestamps: PowerShell 7's ConvertFrom-Json turns ISO strings into DateTime.
function InvRaw([string]$user, [string]$agent) { return ($script:invLines | Where-Object { $_.Contains('"user":"' + $user + '","agent":"' + $agent + '",') } | Select-Object -First 1) }
$hostKeys = 'type,host,collector,mode,at,users_scanned,users_unreadable,docker_volumes'
$agentKeys = 'type,host,user,agent,files,bytes,first,last,projects,evidence'
[System.IO.File]::SetLastWriteTimeUtc((P 'home/bob/.ollama/history'), (New-Object DateTime 2026, 9, 15, 1, 2, 3, ([DateTimeKind]::Utc)))
# bob's ~/.gemini holds only the nested antigravity-cli entry: no gemini-cli line.
Mk 'home/bob/.gemini/antigravity-cli/conversations/b1.db' 'db'
$invCwd = Join-Path $Out 'invcwd'
New-Item -ItemType Directory -Path $invCwd -Force | Out-Null
Push-Location -LiteralPath $invCwd
Inv @{}
Pop-Location
Check 'Inventory exit 0' { $script:rc -eq 0 }
Check 'Inventory writes nothing in the current directory' { @(Get-ChildItem -LiteralPath $invCwd -Force).Count -eq 0 }
Check 'Inventory first line is the host line, keys in order' { $script:inv[0].type -eq 'host' -and (@($script:inv[0].PSObject.Properties | ForEach-Object { $_.Name }) -join ',') -eq $hostKeys -and $script:inv[0].mode -eq 'image' -and $script:invLines[0] -match '"at":"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ"' }
Check 'Inventory host line counts' { $script:inv[0].users_unreadable -eq 0 -and $script:inv[0].docker_volumes -eq 3 -and $script:inv[0].users_scanned -ge 2 }
Check 'Inventory every later line is an agent line, keys in order' { $script:inv.Count -gt 10 -and @($script:inv | Select-Object -Skip 1 | Where-Object { $_.type -ne 'agent' -or (@($_.PSObject.Properties | ForEach-Object { $_.Name }) -join ',') -ne $agentKeys }).Count -eq 0 }
$r = InvAgent 'bob' 'ollama'
Check 'Inventory ollama line: one file, excluded models not counted' { $r -and $r.files -eq 1 -and $r.bytes -eq 4 -and (InvRaw 'bob' 'ollama').Contains('"first":"2026-09-15T01:02:03Z","last":"2026-09-15T01:02:03Z"') -and $r.evidence -eq '.ollama' }
$r = InvAgent 'alice' 'claude-code'
Check 'Inventory claude-code evidence in catalog order' { $r -and $r.evidence -eq '.claude,.claude.json*,.claude-*/projects,.claude-*/history.jsonl,.claude-*/.claude.json*,.claude-*/.credentials.json' }
Check 'Inventory first and last set for alice claude-code' { (InvRaw 'alice' 'claude-code') -match '"first":"20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ","last":"20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ"' }
Check 'Inventory: matched directory with no files of its own gives no line' { $null -eq (InvAgent 'bob' 'gemini-cli') -and ($b = InvAgent 'bob' 'antigravity') -and $b.files -eq 1 -and $b.bytes -eq 2 -and $b.evidence -eq '.gemini/antigravity-cli' }
Check 'Inventory: no agent line has zero files' { -not ($script:inv | Where-Object { $_.type -eq 'agent' } | Where-Object { $_.files -eq 0 }) }
Check 'Inventory projects counted per user' { $r.projects -ge 1 }
Check 'Inventory nested entry claimed from the enclosing agent' { (InvAgent 'alice' 'antigravity').evidence -like '*.gemini/antigravity-cli*' -and (InvAgent 'alice' 'gemini-cli').evidence -eq '.gemini' }
$r = InvAgent 'docker' 'agent-zero'
Check 'Inventory docker volume line' { $r -and $r.files -eq 2 -and $r.bytes -eq 61 -and $r.projects -eq 0 -and $r.evidence -eq '*a0_usr' }
$r = InvAgent 'docker' 'tabby'
Check 'Inventory rootless docker volume line' { $r -and $r.files -eq 1 -and $r.bytes -eq 22 -and $r.evidence -eq '*tabby*' }
Check 'Inventory shared not inventoried' { -not ($script:inv | Where-Object { $_.type -eq 'agent' } | Where-Object { @('shared', 'project', 'live') -contains $_.agent }) }
Check 'Inventory prints no path below a home' { -not ($script:invLines | Where-Object { $_.Contains($Root) -or $_.Contains($Root.Replace('\', '\\')) }) }
$invO = Join-Path $Out 'inv-o'
Inv @{ OutputDir = $invO }
Check 'Inventory with -OutputDir exit 0' { $script:rc -eq 0 }
Check 'Inventory with -OutputDir creates no output directory' { -not (Test-Path -LiteralPath $invO) }
Inv @{ Full = $true }
Check 'Inventory -Full counts excluded files' { $r = InvAgent 'bob' 'ollama'; $r -and $r.files -eq 2 -and $r.bytes -eq 8 }
Inv @{ Users = 'bob'; NoDocker = $true }
Check 'Inventory -Users keeps one user' { $a = @($script:inv | Where-Object { $_.type -eq 'agent' }); -not ($a | Where-Object { $_.user -eq 'alice' }) -and ($a | Where-Object { $_.user -eq 'bob' }) }
Check 'Inventory -NoDocker: no volumes, no docker lines' { $script:inv[0].users_scanned -eq 1 -and $script:inv[0].docker_volumes -eq 0 -and -not ($script:inv | Where-Object { $_.type -eq 'agent' } | Where-Object { $_.user -eq 'docker' }) }
# stderr is only observable from a child process: the collector logs through [Console]::Error.
$self = (Get-Process -Id $PID).Path
$errFile = Join-Path $Out 'inv-child.stderr'
$childOut = @(& $self -NoProfile -ExecutionPolicy Bypass -File $Collector -Root $Root -Inventory -OutputDir $invO 2>$errFile)
Check 'Inventory without -Quiet: stdout is pure JSON Lines, log on stderr' { $childOut.Count -gt 10 -and @($childOut | Where-Object { $_ -notmatch '^\{"type":"(host|agent)",' }).Count -eq 0 -and (Get-Content -LiteralPath $errFile -Raw) -match 'User ' }
Check 'Inventory child stdout parses line by line' { @($childOut | Where-Object { $_ -ne '' } | ForEach-Object { try { $null = $_ | ConvertFrom-Json; $true } catch { $false } } | Where-Object { -not $_ }).Count -eq 0 }
# Windows PowerShell 5.1 wraps redirected error-stream text at the console width, so a long path splits across lines.
Check 'Inventory -OutputDir noted on stderr' { ((Get-Content -LiteralPath $errFile -Raw) -replace '\s+', ' ') -match 'NOTE: -Inventory writes nothing; -OutputDir .*inv-o ignored' }
$childQ = @(& $self -NoProfile -ExecutionPolicy Bypass -File $Collector -Root $Root -Inventory -Quiet 2>$errFile)
Check 'Inventory -Quiet leaves stderr empty' { $childQ.Count -gt 10 -and -not ((Get-Content -LiteralPath $errFile -Raw) -match '\S') }
Remove-Item -LiteralPath (P 'home/bob/.gemini') -Recurse -Force
if ($Sep -eq '/' -and (& id -u) -ne '0') {
  New-Item -ItemType Directory -Path (P 'home/carol/.claude') -Force | Out-Null
  & chmod 000 (P 'home/carol')
  Inv @{}
  & chmod 700 (P 'home/carol')
  Check 'Inventory counts the unreadable home' { $script:inv[0].users_unreadable -eq 1 }
  Remove-Item -LiteralPath (P 'home/carol') -Recurse -Force
} else { Write-Output 'note: unreadable home inventory check needs a non-root POSIX host, skipped' }

# ---- live mode without the snapshot (1.6.0) --------------------------------
$lo = Join-Path $Out 'livemode'
New-Item -ItemType Directory -Path $lo -Force | Out-Null
$global:LASTEXITCODE = 0
$null = & $Collector -OutputDir $lo -Quiet -Users 'no-such-user-cac' -NoDocker -NoProjects 2>&1
Check 'live mode exit 0' { $LASTEXITCODE -eq 0 }
$lm = Get-ChildItem -LiteralPath $lo -Filter '*.manifest.jsonl' | Select-Object -First 1
$lj = Get-ChildItem -LiteralPath $lo -Filter '*.collection.json' | Select-Object -First 1
Check 'live mode manifest has no live rows' { $lm -and -not (Select-String -LiteralPath $lm.FullName -SimpleMatch '"agent":"live"') }
Check 'live mode collection.json has hostname and no no_live' { $j = Get-Content -LiteralPath $lj.FullName -Raw | ConvertFrom-Json; $j.hostname -ne '' -and $null -eq $j.options.PSObject.Properties['no_live'] }
Check 'live mode writes no live directory' { -not (Test-Path -LiteralPath (Join-Path $lo 'live')) -and -not (Get-ChildItem -LiteralPath $lo -Filter '.stage-*' -Force) }
Check '-NoLive is no longer a parameter' { $threw = $false; try { & $Collector -NoLive -List | Out-Null } catch { $threw = $true }; $threw }

# ---- -List ----------------------------------------------------------------
Check '-List prints catalog' { @(& $Collector -List | Select-String -SimpleMatch 'claude-code|.claude').Count -ge 1 }
Check '-List prints docker volume table' { @(& $Collector -List | Where-Object { $_ -eq 'agent-zero|*a0_usr' }).Count -eq 1 }

# 2026-10-04 bug round: #32, #38, #39
# A relative -Project is resolved against the current location (image mode
# too); a -Project that does not exist gets an error_read row and a log line.
Mk 'srv/relproj/AGENTS.md' '# rel'
$missingProj = Join-Path $Work 'nonexistent-cac'
$prevLoc = Get-Location
Set-Location -LiteralPath (P 'srv')
Run 'projargs' @{ Project = @('relproj', $missingProj) }
Set-Location -LiteralPath $prevLoc.Path
$sum = Get-Content -LiteralPath $script:S.FullName -Raw | ConvertFrom-Json
Check '-Project arguments exit 0' { $script:rc -eq 0 }
Check 'relative -Project resolved against the current location' { (StatusOf 'srv/relproj/AGENTS.md') -eq 'collected' -and @($sum.projects | Where-Object { $_ -eq (P 'srv/relproj') }).Count -eq 1 }
$mr = @($script:Rows | Where-Object { $_.path -eq $missingProj })
Check 'missing -Project gets one error_read dir row' { $mr.Count -eq 1 -and $mr[0].status -eq 'error_read' -and $mr[0].type -eq 'dir' -and $mr[0].home -eq $missingProj -and $mr[0].agent -eq '' -and $mr[0].archive_path -eq '' -and $mr[0].error -ne '' }
$plog = Get-ChildItem -LiteralPath (Join-Path $Out 'projargs') -Filter '*.log' | Select-Object -First 1
Check 'missing -Project logged' { (Get-Content -LiteralPath $plog.FullName -Raw).Contains("WARNING: project given with -Project is not a directory: ${missingProj}: ") }
Check 'missing -Project not listed in projects' { @($sum.projects | Where-Object { $_ -like '*nonexistent-cac*' }).Count -eq 0 }
Check 'missing -Project counted as error_read' { $sum.counts.error_read -eq 1 -and $script:stdout -match '(?m)^errors:     1 \(0 error_copy, 1 error_read\)\s*$' }
$dsum = Get-Content -LiteralPath (Get-ChildItem -LiteralPath (Join-Path $Out 'default') -Filter '*.collection.json' | Select-Object -First 1).FullName -Raw | ConvertFrom-Json
Check 'default run has no error_read rows' { $dsum.counts.error_read -eq 0 }
Remove-Item -LiteralPath (P 'srv/relproj') -Recurse -Force

# A read-only output directory exits 2 before any collection work: chmod on
# POSIX (not as root), a deny ACE for creating files on Windows.
$ro = Join-Path $Out 'readonly'
New-Item -ItemType Directory -Path $ro -Force | Out-Null
$roSet = $false
if ($Sep -eq '/') {
  if ((& id -u) -ne '0') { & chmod 555 $ro; $roSet = $true }
} else {
  $acl = Get-Acl -LiteralPath $ro
  $denyRule = New-Object System.Security.AccessControl.FileSystemAccessRule([Security.Principal.WindowsIdentity]::GetCurrent().User, 'CreateFiles, AppendData', 'Deny')
  $acl.AddAccessRule($denyRule); Set-Acl -LiteralPath $ro -AclObject $acl; $roSet = $true
}
if ($roSet) {
  $roErr = Join-Path $Out 'readonly.stderr'
  $null = & $self -NoProfile -ExecutionPolicy Bypass -File $Collector -Root $Root -OutputDir $ro -Quiet -NoDocker 2>$roErr
  $roRc = $LASTEXITCODE
  if ($Sep -eq '/') { & chmod 755 $ro } else { $acl = Get-Acl -LiteralPath $ro; [void]$acl.RemoveAccessRule($denyRule); Set-Acl -LiteralPath $ro -AclObject $acl }
  Check 'read-only output dir exits 2 before collecting' { $roRc -eq 2 -and ((Get-Content -LiteralPath $roErr -Raw) -replace '\s+', ' ') -match 'Output dir not writable: ' -and @(Get-ChildItem -LiteralPath $ro -Force).Count -eq 0 }
} else { Write-Output 'note: read-only output dir check needs a non-root user on POSIX, skipped' }

# An unreadable home and an unlistable directory inside a walk: POSIX and not
# root only, since chmod does not deny on Windows or to root.
if ($Sep -eq '/' -and (& id -u) -ne '0') {
  New-Item -ItemType Directory -Path (P 'home/erin/.claude') -Force | Out-Null
  Mk 'Users/alice/.claude/locked/f' 'x'
  & chmod 000 (P 'home/erin') (P 'Users/alice/.claude/locked')
  Run 'readperm' @{}
  & chmod 700 (P 'home/erin') (P 'Users/alice/.claude/locked')
  $sum = Get-Content -LiteralPath $script:S.FullName -Raw | ConvertFrom-Json
  Check 'unreadable paths exit 0' { $script:rc -eq 0 }
  $er = @($script:Rows | Where-Object { $_.path -eq (P 'home/erin') })
  Check 'unreadable home gets one error_read row' { $er.Count -eq 1 -and $er[0].status -eq 'error_read' -and $er[0].user -eq 'erin' -and $er[0].agent -eq '' -and $er[0].type -eq 'dir' -and $er[0].size -eq 0 -and $er[0].archive_path -eq '' -and $er[0].error -match 'denied' }
  Check 'unreadable home stays in users, not in users_with_artifacts' { @($sum.users) -contains 'erin' -and -not (@($sum.users_with_artifacts) -contains 'erin') }
  $lr = Row 'Users/alice/.claude/locked'
  Check 'unlistable directory in a walk gets an error_read row' { $lr -and $lr.status -eq 'error_read' -and $lr.agent -eq 'claude-code' -and $lr.type -eq 'dir' -and $lr.error -match 'denied' }
  Check 'rest of the home still collected' { (StatusOf 'Users/alice/.claude/projects/-C-proj/s1.jsonl') -eq 'collected' }
  Check 'unreadable paths counted' { $sum.counts.error_read -eq 2 -and $script:stdout -match '(?m)^errors:     2 \(0 error_copy, 2 error_read\)\s*$' }
  Remove-Item -LiteralPath (P 'home/erin'), (P 'Users/alice/.claude/locked') -Recurse -Force
} else { Write-Output 'note: unreadable home and directory checks need a non-root POSIX host, skipped' }

if ($script:fail -eq 0) { Write-Output "ALL PASSED ($($PSVersionTable.PSEdition) $($PSVersionTable.PSVersion))"; Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue }
else { Write-Output "FAILURES; work dir kept: $Work" }
exit $script:fail
