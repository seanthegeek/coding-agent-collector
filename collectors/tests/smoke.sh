#!/bin/sh
# Copyright 2026 Sean Whalen
# SPDX-License-Identifier: Apache-2.0
# Smoke test: build a fake disk image, run the collector in image mode under a
# given shell, and check the manifest and archive. Usage:
#   tests/smoke.sh [SHELL]     (SHELL defaults to sh; used for both the script
#                               and the find -exec workers via COLLECTOR_SH)
set -u
SHELL_UNDER_TEST=${1:-sh}
HERE=$(cd "$(dirname "$0")" && pwd)
SCRIPT="$HERE/../collect-agent-artifacts.sh"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/cac-smoke.XXXXXX")
ROOT="$WORK/root"
OUT="$WORK/out"
fail=0
ok()   { printf 'ok   %s\n' "$1"; }
bad()  { printf 'FAIL %s\n' "$1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

# ---- fake image -----------------------------------------------------------
mkdir -p "$ROOT/etc" "$ROOT/home/alice/.claude/projects/-srv-proj" "$ROOT/home/alice/.claude/cache" \
  "$ROOT/home/alice/.gemini/antigravity-cli/conversations" "$ROOT/home/alice/.gemini/antigravity-cli/bin" \
  "$ROOT/Users/bob/Library/Application Support/Cursor/User/globalStorage/ms-python.python" \
  "$ROOT/Users/bob/Library/Application Support/Cursor/User/workspaceStorage/abc" \
  "$ROOT/Users/bob/.codex/sessions/2026/10/03" "$ROOT/srv/proj/.claude" "$ROOT/Users/bob/Documents/app" \
  "$ROOT/home/ollama/.ollama/models/blobs" "$ROOT/nonexistent" "$ROOT/home/dave"
cat >"$ROOT/etc/passwd" <<EOF
root:x:0:0:root:/root:/bin/sh
alice:x:1000:1000:Alice:/home/alice:/bin/bash
ollama:x:999:999::/home/ollama:/usr/sbin/nologin
nobody:x:65534:65534::/nonexistent:/usr/sbin/nologin
dave:x:1001:1001:Dave:/home/dave:/bin/sh
EOF
printf '{"type":"user","message":{"role":"user","content":"hi"},"timestamp":"2026-10-03T00:00:00Z"}\n' >"$ROOT/home/alice/.claude/projects/-srv-proj/s1.jsonl"
printf '{"display":"do things","timestamp":1759449600000,"project":"/srv/proj","sessionId":"s1"}\n' >"$ROOT/home/alice/.claude/history.jsonl"
printf '{"claudeAiOauth":{"accessToken":"sk-ant-oat-SECRET"}}\n' >"$ROOT/home/alice/.claude/.credentials.json"
printf '{"projects":{"/srv/proj":{}}}\n' >"$ROOT/home/alice/.claude.json"
printf 'cached junk\n' >"$ROOT/home/alice/.claude/cache/junk.bin"
printf 'weird "name" with spaces and a \\ backslash\n' >"$ROOT/home/alice/.claude/weird \"name\" with spaces \\ bs.txt"
printf 'token\n' >"$ROOT/home/alice/.gemini/antigravity-cli/antigravity-oauth-token"
printf 'db\n' >"$ROOT/home/alice/.gemini/antigravity-cli/conversations/c1.db"
head -c 300000 /dev/zero >"$ROOT/home/alice/.gemini/antigravity-cli/bin/webm_encoder"
ln -s log/cli-1.log "$ROOT/home/alice/.gemini/antigravity-cli/cli.log"
printf 'export FOO=1\n' >"$ROOT/home/alice/.bash_history"
printf 'settings\n' >"$ROOT/srv/proj/.claude/settings.local.json"
printf '# proj\n' >"$ROOT/srv/proj/CLAUDE.md"
head -c 2100000 /dev/zero >"$ROOT/Users/bob/Library/Application Support/Cursor/User/globalStorage/state.vscdb"
printf 'junk\n' >"$ROOT/Users/bob/Library/Application Support/Cursor/User/globalStorage/ms-python.python/x"
printf '{"folder":"file:///Users/bob/Documents/app"}\n' >"$ROOT/Users/bob/Library/Application Support/Cursor/User/workspaceStorage/abc/workspace.json"
printf 'rules\n' >"$ROOT/Users/bob/Documents/app/.cursorrules"
printf '{"cwd":"/Users/bob/Documents/app"}\n' >"$ROOT/Users/bob/.codex/sessions/2026/10/03/rollout-1.jsonl"
printf 'blob\n' >"$ROOT/home/ollama/.ollama/models/blobs/sha256-abc"
printf 'hist\n' >"$ROOT/home/ollama/.ollama/history"
# --- source-verified layouts for the per-platform catalog entries ---
mkdir -p "$ROOT/home/alice/.continue/sessions" "$ROOT/home/alice/.continue/index/lancedb" "$ROOT/srv/cont" \
  "$ROOT/home/alice/.local/share/crush" "$ROOT/srv/crushproj/.crush" "$ROOT/srv/gem" "$ROOT/home/alice/.gemini/tmp/gem" \
  "$ROOT/home/alice/.cline/data/settings" "$ROOT/home/alice/.cline/data/sessions/s1" "$ROOT/srv/clineproj" \
  "$ROOT/home/alice/.local/share/opencode" \
  "$ROOT/Users/bob/Library/Application Support/Claude/Cache" "$ROOT/Users/bob/Library/Application Support/Zed/extensions" \
  "$ROOT/Users/bob/Library/Application Support/Zed/threads" "$ROOT/Users/bob/.config/zed" \
  "$ROOT/Users/bob/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/state" \
  "$ROOT/Users/bob/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/checkpoints" "$ROOT/Users/bob/clineproj"
printf '[{"sessionId":"a","workspaceDirectory":"/srv/cont"}]\n' >"$ROOT/home/alice/.continue/sessions/sessions.json"
printf '{"mcpOauthStorage":{}}\n' >"$ROOT/home/alice/.continue/index/globalContext.json"
printf 'vec\n' >"$ROOT/home/alice/.continue/index/lancedb/data.lance"
printf '{}\n' >"$ROOT/srv/cont/.continuerc.json"
printf '{"projects":[{"path":"/srv/crushproj","data_dir":"/srv/crushproj/.crush"}]}\n' >"$ROOT/home/alice/.local/share/crush/projects.json"
printf 'sqlite\n' >"$ROOT/srv/crushproj/.crush/crush.db"
printf '{"projects":{"/srv/gem":"gem"}}\n' >"$ROOT/home/alice/.gemini/projects.json"
printf '/srv/gem\n' >"$ROOT/home/alice/.gemini/tmp/gem/.project_root"
printf '# gem\n' >"$ROOT/srv/gem/GEMINI.md"
printf '{"anthropic":{"apiKey":"sk-x"}}\n' >"$ROOT/home/alice/.cline/data/settings/providers.json"
printf '{"id":"s1","cwd":"/srv/clineproj","workspace_root":"/srv/clineproj"}\n' >"$ROOT/home/alice/.cline/data/sessions/s1/s1.json"
printf 'rules\n' >"$ROOT/srv/clineproj/.clinerules"
printf '{"openai":{"type":"api","key":"x"}}\n' >"$ROOT/home/alice/.local/share/opencode/auth.json"
printf 'TOKEN=1\n' >"$ROOT/home/alice/.env"
printf '{"oauth:tokenCache":"enc"}\n' >"$ROOT/Users/bob/Library/Application Support/Claude/config.json"
printf '{"mcpServers":{}}\n' >"$ROOT/Users/bob/Library/Application Support/Claude/claude_desktop_config.json"
printf 'cache\n' >"$ROOT/Users/bob/Library/Application Support/Claude/Cache/index"
printf 'ext\n' >"$ROOT/Users/bob/Library/Application Support/Zed/extensions/foo.wasm"
printf 'db\n' >"$ROOT/Users/bob/Library/Application Support/Zed/threads/threads.db"
printf '{"language_models":{}}\n' >"$ROOT/Users/bob/.config/zed/settings.json"
printf '[{"id":"t1","cwdOnTaskInitialization":"/Users/bob/clineproj"}]\n' >"$ROOT/Users/bob/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/state/taskHistory.json"
printf 'ckpt\n' >"$ROOT/Users/bob/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/checkpoints/x"
printf 'rules\n' >"$ROOT/Users/bob/clineproj/.clinerules"
# --- v1.3 catalog revision: exclusions that must not swallow evidence, new secrets, remote server dirs, discovery sources ---
mkdir -p "$ROOT/home/alice/.factory/cache/session-index" "$ROOT/home/alice/.factory/cache/sounds" "$ROOT/home/alice/.factory/sessions/-srv-droid" "$ROOT/srv/droid" \
  "$ROOT/home/alice/.kiro/powers/installed/p1" "$ROOT/home/alice/.kiro/sessions/cli" "$ROOT/srv/kiroproj" \
  "$ROOT/home/alice/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/state" "$ROOT/srv/remoteproj" \
  "$ROOT/home/alice/.gemini/antigravity-ide/conversations" "$ROOT/home/alice/.gemini/config" "$ROOT/srv/agyproj" \
  "$ROOT/home/alice/.cursor/projects/-srv-proj" "$ROOT/home/alice/.copilot/pkg" "$ROOT/home/alice/.copilot/session-state/s1" "$ROOT/srv/copproj" \
  "$ROOT/home/alice/.claude/image-cache" "$ROOT/home/alice/.local/share/amp" "$ROOT/srv/ampproj/.amp" \
  "$ROOT/home/alice/.windsurf/transcripts" "$ROOT/srv/kiloproj/.kilo/worktrees/w1" "$ROOT/Users/bob/Library/Application Support/Ollama"
printf 'sqlite\n' >"$ROOT/home/alice/.factory/cache/session-index/index.db"
printf 'ding\n' >"$ROOT/home/alice/.factory/cache/sounds/done.wav"
printf '{"type":"session_start","cwd":"/srv/droid"}\n' >"$ROOT/home/alice/.factory/sessions/-srv-droid/s1.jsonl"
printf '# droid\n' >"$ROOT/srv/droid/AGENTS.md"
printf '{"mcpServers":{"x":{"env":{"TOKEN":"t"}}}}\n' >"$ROOT/home/alice/.kiro/powers/installed/p1/mcp.json"
printf '{"id":"k1","cwd":"/srv/kiroproj"}\n' >"$ROOT/home/alice/.kiro/sessions/cli/k1.json"
printf 'steer\n' >"$ROOT/srv/kiroproj/.kiroignore"
printf 'sqlite\n' >"$ROOT/home/alice/.vscode-server/data/User/globalStorage/state.vscdb"
printf '[{"id":"t2","cwdOnTaskInitialization":"/srv/remoteproj"}]\n' >"$ROOT/home/alice/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/state/taskHistory.json"
printf 'rules\n' >"$ROOT/srv/remoteproj/.clinerules"
printf 'db\n' >"$ROOT/home/alice/.gemini/antigravity-ide/conversations/i1.db"
printf '{"mcpServers":{}}\n' >"$ROOT/home/alice/.gemini/config/mcp_config.json"
printf '{"display":"hi","timestamp":1759449600000,"workspace":"/srv/agyproj"}\n' >"$ROOT/home/alice/.gemini/antigravity-cli/history.jsonl"
printf 'ignore\n' >"$ROOT/srv/agyproj/.antigravityignore"
printf '{"accessToken":"x"}\n' >"$ROOT/home/alice/.cursor/auth.json"
printf '{"tok":"x"}\n' >"$ROOT/home/alice/.cursor/projects/-srv-proj/mcp-auth.json"
printf 'pkg\n' >"$ROOT/home/alice/.copilot/pkg/copilot"
printf '{"token":"x"}\n' >"$ROOT/home/alice/.copilot/config.json"
printf 'cwd: /srv/copproj\nbranch: main\n' >"$ROOT/home/alice/.copilot/session-state/s1/workspace.yaml"
printf '# cop\n' >"$ROOT/srv/copproj/AGENTS.md"
printf '{"k":"x"}\n' >"$ROOT/home/alice/.claude/.device-keys.json"
printf 'img\n' >"$ROOT/home/alice/.claude/image-cache/a.png"
printf '{"cwd":"/srv/ampproj","prompt":"hi"}\n' >"$ROOT/home/alice/.local/share/amp/history.jsonl"
printf 'amp\n' >"$ROOT/srv/ampproj/.amp/settings.json"
printf '{"step":1}\n' >"$ROOT/home/alice/.windsurf/transcripts/t1.jsonl"
printf 'wt\n' >"$ROOT/srv/kiloproj/.kilo/worktrees/w1/f"
printf '{"cwd":"/srv/kiloproj"}\n' >"$ROOT/home/alice/.cline/data/sessions/s1/s2.json"
printf 'db\n' >"$ROOT/Users/bob/Library/Application Support/Ollama/db.sqlite"

# --- 1.4.0 catalog round (2026-10-04): sixteen agents from the October 2026 backlog.
# One case per new exclusion, secret glob and attributed agent, as kind|agent|path
# relative to alice's home: excl is a directory and exclf a file that must be
# skipped_excluded, secret must be collected and flagged, agent must be collected
# under that agent. The same list is in smoke.ps1.
CASES14='
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
'
H="$ROOT/home/alice"; B="$ROOT/Users/bob"
printf '%s\n' "$CASES14" | while IFS='|' read -r _k _a _r; do
  [ -n "$_r" ] || continue
  case "$_k" in
    excl) mkdir -p "$H/$_r"; printf 'x\n' >"$H/$_r/f" ;;
    *) mkdir -p "$H/$(dirname "$_r")"; printf 'x\n' >"$H/$_r" ;;
  esac
done
# discovery sources, one project each
mkdir -p "$H/.hermes/checkpoints/store/projects" "$ROOT/srv/hermesproj" "$H/.letta/lc-local-backend/conversations/c1" "$ROOT/srv/lettaproj/.letta" "$ROOT/srv/lettaproj2" \
  "$H/.pi/agent/sessions/--srv-piproj--" "$H/.pi/agent/experimental/sessions/s1" "$ROOT/srv/piproj/.pi" "$ROOT/srv/piproj2" "$ROOT/srv/pitrust" "$ROOT/srv/picrash" "$ROOT/srv/piexp" \
  "$H/.openinterpreter/sessions/2026/10/04" "$H/.openinterpreter/archived_sessions/2026/10/01" "$ROOT/srv/oiproj/.openinterpreter/rules" "$ROOT/srv/oiarch/.codewhale" \
  "$H/.openhands/agent-canvas/dev_conversations/a1" "$H/.openhands/agent-canvas/conversations/a2" "$H/.openhands/conversations/a3" \
  "$ROOT/srv/ohproj/.openhands" "$ROOT/srv/ohdev" "$ROOT/srv/ohcanvas" "$ROOT/srv/ohcli" "$H/.pearai/sessions" "$ROOT/srv/pearproj/.pearai-agent" \
  "$ROOT/srv/clawws" "$ROOT/srv/clawagent" "$ROOT/srv/clawlegacy" "$ROOT/srv/clawprofile" "$B/.openclaw" \
  "$H/.nanobot/sessions/0123456789abcdef0123456789abcdef" "$ROOT/srv/nanows" "$ROOT/srv/nanocfg/memory" "$ROOT/srv/tabbyproj" \
  "$H/.twinny/embeddings/twinproj" "$ROOT/srv/twinproj/src"
printf '{"workdir":"/srv/hermesproj","created_at":1759536000}\n' >"$H/.hermes/checkpoints/store/projects/0123456789abcdef.json"
printf '# hermes\n' >"$ROOT/srv/hermesproj/.hermes.md"
printf '{"type":"start","project":"/srv/lettaproj","agentId":"a1"}\n' >"$H/.letta/sessions.jsonl"
printf '{"hooks":{}}\n' >"$ROOT/srv/lettaproj/.letta/settings.json"
printf '{"type":"session","id":"c1","cwd":"/srv/lettaproj2"}\n' >"$H/.letta/lc-local-backend/conversations/c1/messages.jsonl"
printf '# letta\n' >"$ROOT/srv/lettaproj2/AGENTS.md"
printf '{"type":"session","version":3,"id":"u1","cwd":"/srv/piproj"}\n' >"$H/.pi/agent/sessions/--srv-piproj--/2026-10-04T00-00-00-000Z_u1.jsonl"
printf '{}\n' >"$ROOT/srv/piproj/.pi/settings.json"
printf '{"type":"session","version":1,"id":"u2","cwd":"/srv/piproj2"}\n' >"$H/.pi/agent/2026-10-01T00-00-00-000Z_u2.jsonl"
printf '# pi\n' >"$ROOT/srv/piproj2/AGENTS.md"
printf '{"/srv/pitrust":true}\n' >"$H/.pi/agent/trust.json"
printf '<html></html>\n' >"$ROOT/srv/pitrust/pi-session-2026-10-04.html"
printf '[{"cwd":"/srv/picrash","sessionFile":"x.jsonl"}]\n' >"$H/.pi/agent/crashes.json"
printf '# pi\n' >"$ROOT/srv/picrash/AGENTS.md"
printf '{"id":"s1","cwd":"/srv/piexp"}\n' >"$H/.pi/agent/experimental/sessions/s1/meta.json"
printf '# pi\n' >"$ROOT/srv/piexp/AGENTS.md"
printf '{"type":"session_meta","payload":{"cwd":"/srv/oiproj"}}\n' >"$H/.openinterpreter/sessions/2026/10/04/rollout-2026-10-04T00-00-00-u1.jsonl"
printf 'rule\n' >"$ROOT/srv/oiproj/.openinterpreter/rules/r.md"
printf '{"type":"session_meta","payload":{"cwd":"/srv/oiarch"}}\n' >"$H/.openinterpreter/archived_sessions/2026/10/01/rollout-2026-10-01T00-00-00-u2.jsonl"
printf 'notes\n' >"$ROOT/srv/oiarch/.codewhale/notes.md"
printf '{"workspaces":[{"id":"w1","path":"/srv/ohproj"}],"workspaceParents":[]}\n' >"$H/.openhands/workspaces.json"
printf 'echo setup\n' >"$ROOT/srv/ohproj/.openhands/setup.sh"
printf '{"workspace":{"working_dir":"/srv/ohdev"}}\n' >"$H/.openhands/agent-canvas/dev_conversations/a1/meta.json"
printf '{"workspace":{"working_dir":"/srv/ohcanvas"}}\n' >"$H/.openhands/agent-canvas/conversations/a2/meta.json"
printf '{"workspace":{"working_dir":"/srv/ohcli"}}\n' >"$H/.openhands/conversations/a3/base_state.json"
for _d in ohdev ohcanvas ohcli; do printf '# oh\n' >"$ROOT/srv/$_d/AGENTS.md"; done
printf '[{"sessionId":"s1","title":"t","workspaceDirectory":"/srv/pearproj"}]\n' >"$H/.pearai/sessions/sessions.json"
printf '{}\n' >"$ROOT/srv/pearproj/.pearairc.json"
printf '{"mcpServers":{}}\n' >"$ROOT/srv/pearproj/.pearai-agent/mcp.json"
printf "{\n  // JSON5\n  agents: {\n    defaults: { workspace: '/srv/clawws' },\n    entries: { main: { agentDir: \"/srv/clawagent\" } },\n  },\n}\n" >"$H/.openclaw/openclaw.json"
printf '{"agents":{"defaults":{"workspace":"/srv/clawlegacy"}}}\n' >"$H/.clawdbot/clawdbot.json"
printf '{agents:{defaults:{workspace:"/srv/clawprofile"}}}\n' >"$H/.openclaw-work/openclaw.json"
printf '# soul\n' >"$ROOT/srv/clawws/SOUL.md"
printf '# a\n' >"$ROOT/srv/clawagent/AGENTS.md"
printf '# id\n' >"$ROOT/srv/clawlegacy/IDENTITY.md"
printf '# mem\n' >"$ROOT/srv/clawprofile/MEMORY.md"
printf '{}\n' >"$B/.openclaw/openclaw.json"
ln -s .openclaw "$B/.clawdbot"
printf '/srv/nanows' >"$H/.nanobot/sessions/0123456789abcdef0123456789abcdef/.workspace"
printf '# hb\n' >"$ROOT/srv/nanows/HEARTBEAT.md"
printf '{"agents":{"defaults":{"workspace":"/srv/nanocfg"}}}\n' >"$H/.nanobot-work/config.json"
printf '# mem\n' >"$ROOT/srv/nanocfg/memory/MEMORY.md"
printf '[[repositories]]\nname = "p"\ngit_url = "file:///srv/tabbyproj"\n' >"$H/.tabby/config.toml"
printf '# tabby\n' >"$ROOT/srv/tabbyproj/AGENTS.md"
printf '{"files":{"/srv/twinproj/src/a.ts":{"hash":"h1"},"/srv/twinproj/b.ts":{"hash":"h2"}}}\n' >"$H/.twinny/embeddings/twinproj/manifest.json"
printf '# twin\n' >"$ROOT/srv/twinproj/AGENTS.md"

# --- 1.5.0 Docker volumes (2026-10-04): a root Docker volume matched to Agent
# Zero, an unmatched volume, and a rootless volume in alice's home.
DV="$ROOT/var/lib/docker/volumes"
mkdir -p "$DV/a0_usr/_data/chats/ctx1" "$DV/a0_usr/_data/tmp/playwright" "$DV/pgdata/_data" \
  "$H/.local/share/docker/volumes/tabby_data/_data/events"
printf '{"id":"ctx1","name":"chat","history":"[]"}\n' >"$DV/a0_usr/_data/chats/ctx1/chat.json"
printf 'API_KEY_OPENAI=sk-x\n' >"$DV/a0_usr/_data/.env"
printf 'junk\n' >"$DV/a0_usr/_data/tmp/playwright/junk"
printf 'pg\n' >"$DV/pgdata/_data/x"
printf '{"event":"completion"}\n' >"$H/.local/share/docker/volumes/tabby_data/_data/events/2026-10-01.json"
printf 'metadata\n' >"$DV/metadata.db"

# --- 2026-10-04 Muse Code: Meta's coding agent CLI. Cases in the CASES14 form,
# relative to alice's home; the same list is in smoke.ps1. The Windows binary is
# a file exclusion, the Linux launcher state is a dot-file glob inside
# ~/.local/bin, and two discovery sources point at projects.
CASES_MUSE='
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
'
printf '%s\n' "$CASES_MUSE" | while IFS='|' read -r _k _a _r; do
  [ -n "$_r" ] || continue
  case "$_k" in
    excl) mkdir -p "$H/$_r"; printf 'x\n' >"$H/$_r/f" ;;
    *) mkdir -p "$H/$(dirname "$_r")"; printf 'x\n' >"$H/$_r" ;;
  esac
done
printf 'x\n' >"$H/.local/bin/othertool"
MUSE_S="$H/.local/share/muse/sessions/2026/10/04/01a0f000-0000-7000-8000-000000000001"
mkdir -p "$MUSE_S" "$ROOT/srv/museproj/.muse/worktrees/w1" "$ROOT/srv/musetrust"
printf '{"schema_version":1,"projects":{"/srv/musetrust":{"decision":"trusted"}}}\n' >"$H/.config/muse/trust.json"
printf '{"schema_version":1,"stream":{"kind":"session","id":"01a0f000-0000-7000-8000-000000000001"},"payload_type":"runtime.session.metadata","payload":{"kind":"metadata","record":{"model_id":"m","workspace_root":"/srv/museproj"}}}\n' >"$MUSE_S/session.jsonl"
printf '{}\n' >"$ROOT/srv/museproj/.muse/hooks.json"
printf 'x\n' >"$ROOT/srv/museproj/.muse/worktrees/w1/f"
printf '# trusted\n' >"$ROOT/srv/musetrust/AGENTS.md"

# --- 2026-10-04 relocated Claude Code home: a config home moved with
# CLAUDE_CONFIG_DIR to ~/.claude-work, which keeps .claude.json inside it, and
# claude-code-router's ~/.claude-code-router, which the .claude-* catalog lines
# must not claim. The same files are in smoke.ps1.
CCW="$H/.claude-work"
CCW_S="$CCW/projects/-srv-ccwork/0a0b0c0d-0000-4000-8000-000000000001.jsonl"
mkdir -p "$CCW/projects/-srv-ccwork" "$H/.claude-code-router" "$ROOT/srv/ccwork/.claude" "$ROOT/srv/cchist/.claude"
printf '{"type":"user","cwd":"/srv/ccwork","message":{"role":"user","content":"hi"}}\n' >"$CCW_S"
printf '{"display":"hi","project":"/srv/cchist","timestamp":1790848800000}\n' >"$CCW/history.jsonl"
printf '{"projects":{"/srv/ccwork":{"allowedTools":[]}}}\n' >"$CCW/.claude.json"
printf '{"claudeAiOauth":{"accessToken":"sk-ant-oat-SECRET"}}\n' >"$CCW/.credentials.json"
printf '{"PORT":3456}\n' >"$H/.claude-code-router/config.json"
printf '{}\n' >"$ROOT/srv/ccwork/.claude/settings.json"
printf '{}\n' >"$ROOT/srv/cchist/.claude/settings.json"

run() { # run NAME ARGS...
  _n=$1; shift
  mkdir -p "$OUT/$_n"
  COLLECTOR_SH="$SHELL_UNDER_TEST" "$SHELL_UNDER_TEST" "$SCRIPT" -r "$ROOT" -o "$OUT/$_n" -q --max-file-size 1 "$@" >"$OUT/$_n.stdout" 2>"$OUT/$_n.stderr"
  _rc=$?
  M=$(ls "$OUT/$_n"/*.manifest.jsonl 2>/dev/null)
  # shellcheck disable=SC2034 # A and S are read by the eval'd check strings
  A=$(ls "$OUT/$_n"/*.tar.gz 2>/dev/null)
  # shellcheck disable=SC2034
  S=$(ls "$OUT/$_n"/*.collection.json 2>/dev/null)
  return "$_rc"
}
row() { grep -F "\"path\":\"$1\"" "$M" | head -n1; }
# shellcheck disable=SC2317,SC2329 # called from the eval'd check strings
status_of() { row "$1" | sed 's/.*"status":"\([^"]*\)".*/\1/'; }

printf '== shell: %s (%s)\n' "$SHELL_UNDER_TEST" "$(command -v "$SHELL_UNDER_TEST")"

# ---- default run ----------------------------------------------------------
run default; check "exit code 0" "[ $? -eq 0 ]"
check "archive exists" "[ -s \"\$A\" ]"
check "sha256 sidecar matches" "[ \"\$(cut -d' ' -f1 \"\$A.sha256\")\" = \"\$(sha256sum \"\$A\" | cut -d' ' -f1)\" ]"
check "transcript collected" "[ \"\$(status_of \"$ROOT/home/alice/.claude/projects/-srv-proj/s1.jsonl\")\" = collected ]"
check "transcript hash correct" "[ \"\$(row \"$ROOT/home/alice/.claude/projects/-srv-proj/s1.jsonl\" | sed 's/.*\"sha256\":\"\([^\"]*\)\".*/\1/')\" = \"\$(sha256sum \"$ROOT/home/alice/.claude/projects/-srv-proj/s1.jsonl\" | cut -d' ' -f1)\" ]"
check "secret collected and flagged" "row \"$ROOT/home/alice/.claude/.credentials.json\" | grep -q '\"secret\":true,\"status\":\"collected\"'"
check "antigravity token flagged secret" "row \"$ROOT/home/alice/.gemini/antigravity-cli/antigravity-oauth-token\" | grep -q '\"secret\":true'"
check "cache dir skipped_excluded with size" "row \"$ROOT/home/alice/.claude/cache\" | grep -q '\"type\":\"dir\",\"size\":[1-9][0-9]*.*\"status\":\"skipped_excluded\"'"
check "cache contents not collected" "! grep -q 'cache/junk.bin' \"\$M\""
check "nested entry attributed to its own agent" "row \"$ROOT/home/alice/.gemini/antigravity-cli/conversations/c1.db\" | grep -q '\"agent\":\"antigravity\"'"
check "nested entry collected exactly once" "[ \"\$(grep -c 'antigravity-cli/conversations/c1.db' \"\$M\")\" = 1 ]"
check "enclosing entry still attributed to gemini-cli" "row \"$ROOT/home/alice/.gemini/projects.json\" | grep -q '\"agent\":\"gemini-cli\"'"
check "antigravity bin excluded" "[ \"\$(status_of \"$ROOT/home/alice/.gemini/antigravity-cli/bin\")\" = skipped_excluded ]"
check "ollama models excluded" "[ \"\$(status_of \"$ROOT/home/ollama/.ollama/models\")\" = skipped_excluded ]"
check "ollama history collected (service account home)" "[ \"\$(status_of \"$ROOT/home/ollama/.ollama/history\")\" = collected ]"
check "oversized file skipped_size" "[ \"\$(status_of \"$ROOT/Users/bob/Library/Application Support/Cursor/User/globalStorage/state.vscdb\")\" = skipped_size ]"
check "ms-python globalStorage excluded" "[ \"\$(status_of \"$ROOT/Users/bob/Library/Application Support/Cursor/User/globalStorage/ms-python.python\")\" = skipped_excluded ]"
check "symlink recorded with target" "row \"$ROOT/home/alice/.gemini/antigravity-cli/cli.log\" | grep -q '\"type\":\"symlink\".*\"status\":\"symlink\",\"target\":\"log/cli-1.log\"'"
check "symlink present in archive" "tar -tzf \"\$A\" | grep -q 'antigravity-cli/cli.log'"
check "weird filename collected" "grep -q 'weird \\\\\"name\\\\\" with spaces \\\\\\\\ bs.txt.*\"status\":\"collected\"' \"\$M\""
check "project from history.jsonl collected" "[ \"\$(status_of \"$ROOT/srv/proj/CLAUDE.md\")\" = collected ]"
check "project .claude settings collected" "[ \"\$(status_of \"$ROOT/srv/proj/.claude/settings.local.json\")\" = collected ]"
check "project owner attributed" "row \"$ROOT/srv/proj/CLAUDE.md\" | grep -q '\"user\":\"alice\"'"
check "project from cursor workspace.json collected" "[ \"\$(status_of \"$ROOT/Users/bob/Documents/app/.cursorrules\")\" = collected ]"
check "bob (no passwd entry) found via /Users glob" "grep -q '\"user\":\"bob\"' \"\$M\""
check "nobody home skipped" "! grep -q '\"home\":\"$ROOT/nonexistent\"' \"\$M\""
check "shell history not collected" "! grep -q '.bash_history' \"\$M\""
check "continue sessions.json discovers project" "[ \"\$(status_of \"$ROOT/srv/cont/.continuerc.json\")\" = collected ]"
check "continue globalContext flagged secret" "row \"$ROOT/home/alice/.continue/index/globalContext.json\" | grep -q '\"secret\":true,\"status\":\"collected\"'"
check "continue lancedb excluded" "[ \"\$(status_of \"$ROOT/home/alice/.continue/index/lancedb\")\" = skipped_excluded ]"
check "crush projects.json discovers project-local crush.db" "[ \"\$(status_of \"$ROOT/srv/crushproj/.crush/crush.db\")\" = collected ]"
check "gemini projects.json / .project_root discovers project" "[ \"\$(status_of \"$ROOT/srv/gem/GEMINI.md\")\" = collected ]"
check "cline session cwd discovers project" "[ \"\$(status_of \"$ROOT/srv/clineproj/.clinerules\")\" = collected ]"
check "cline providers.json flagged secret" "row \"$ROOT/home/alice/.cline/data/settings/providers.json\" | grep -q '\"secret\":true'"
check "opencode auth.json flagged secret" "row \"$ROOT/home/alice/.local/share/opencode/auth.json\" | grep -q '\"secret\":true'"
check "home .env not collected" "[ -z \"\$(row \"$ROOT/home/alice/.env\")\" ]"
check "claude desktop config.json flagged secret" "row \"$ROOT/Users/bob/Library/Application Support/Claude/config.json\" | grep -q '\"secret\":true'"
check "claude desktop mcp config flagged secret" "row \"$ROOT/Users/bob/Library/Application Support/Claude/claude_desktop_config.json\" | grep -q '\"secret\":true,\"status\":\"collected\"'"
check "claude desktop Cache excluded" "[ \"\$(status_of \"$ROOT/Users/bob/Library/Application Support/Claude/Cache\")\" = skipped_excluded ]"
check "zed extensions excluded via [Zz]ed glob" "[ \"\$(status_of \"$ROOT/Users/bob/Library/Application Support/Zed/extensions\")\" = skipped_excluded ]"
check "zed threads.db collected" "[ \"\$(status_of \"$ROOT/Users/bob/Library/Application Support/Zed/threads/threads.db\")\" = collected ]"
check "zed settings.json flagged secret" "row \"$ROOT/Users/bob/.config/zed/settings.json\" | grep -q '\"secret\":true'"
check "cline globalStorage attributed to cline, not cursor" "row \"$ROOT/Users/bob/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/state/taskHistory.json\" | grep -q '\"agent\":\"cline\"'"
check "cline globalStorage collected exactly once" "[ \"\$(grep -c 'Cursor/User/globalStorage/saoudrizwan.claude-dev/state/taskHistory.json' \"\$M\")\" = 1 ]"
check "cursor state.vscdb still attributed to cursor" "row \"$ROOT/Users/bob/Library/Application Support/Cursor/User/globalStorage/state.vscdb\" | grep -q '\"agent\":\"cursor\"'"
check "factory session index not swallowed by cache exclusion" "[ \"\$(status_of \"$ROOT/home/alice/.factory/cache/session-index/index.db\")\" = collected ]"
check "factory cache sounds excluded" "[ \"\$(status_of \"$ROOT/home/alice/.factory/cache/sounds\")\" = skipped_excluded ]"
check "factory session cwd discovers project" "[ \"\$(status_of \"$ROOT/srv/droid/AGENTS.md\")\" = collected ]"
check "kiro power mcp.json collected and flagged" "row \"$ROOT/home/alice/.kiro/powers/installed/p1/mcp.json\" | grep -q '\"secret\":true,\"status\":\"collected\"'"
check "kiro cli session cwd discovers project" "[ \"\$(status_of \"$ROOT/srv/kiroproj/.kiroignore\")\" = collected ]"
check "vscode-server User dir collected as vscode" "row \"$ROOT/home/alice/.vscode-server/data/User/globalStorage/state.vscdb\" | grep -q '\"agent\":\"vscode\"'"
check "cline inside vscode-server attributed to cline" "row \"$ROOT/home/alice/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/state/taskHistory.json\" | grep -q '\"agent\":\"cline\"'"
check "vscode-server taskHistory discovers project" "[ \"\$(status_of \"$ROOT/srv/remoteproj/.clinerules\")\" = collected ]"
check "antigravity-ide attributed to antigravity" "row \"$ROOT/home/alice/.gemini/antigravity-ide/conversations/i1.db\" | grep -q '\"agent\":\"antigravity\"'"
check "gemini config dir attributed to antigravity" "row \"$ROOT/home/alice/.gemini/config/mcp_config.json\" | grep -q '\"agent\":\"antigravity\"'"
check "antigravity history workspace discovers project" "[ \"\$(status_of \"$ROOT/srv/agyproj/.antigravityignore\")\" = collected ]"
check "cursor auth.json flagged secret" "row \"$ROOT/home/alice/.cursor/auth.json\" | grep -q '\"secret\":true'"
check "cursor project mcp-auth.json flagged secret" "row \"$ROOT/home/alice/.cursor/projects/-srv-proj/mcp-auth.json\" | grep -q '\"secret\":true'"
check "copilot pkg excluded" "[ \"\$(status_of \"$ROOT/home/alice/.copilot/pkg\")\" = skipped_excluded ]"
check "copilot config.json flagged secret" "row \"$ROOT/home/alice/.copilot/config.json\" | grep -q '\"secret\":true'"
check "copilot workspace.yaml cwd discovers project" "[ \"\$(status_of \"$ROOT/srv/copproj/AGENTS.md\")\" = collected ]"
check "claude device keys flagged secret" "row \"$ROOT/home/alice/.claude/.device-keys.json\" | grep -q '\"secret\":true'"
check "claude image-cache excluded" "[ \"\$(status_of \"$ROOT/home/alice/.claude/image-cache\")\" = skipped_excluded ]"
check "amp history cwd discovers project" "[ \"\$(status_of \"$ROOT/srv/ampproj/.amp/settings.json\")\" = collected ]"
check "windsurf transcripts collected" "row \"$ROOT/home/alice/.windsurf/transcripts/t1.jsonl\" | grep -q '\"agent\":\"windsurf\".*\"status\":\"collected\"'"
check "project-level kilo worktrees excluded" "[ \"\$(status_of \"$ROOT/srv/kiloproj/.kilo/worktrees\")\" = skipped_excluded ]"
check "ollama desktop app dir collected" "[ \"\$(status_of \"$ROOT/Users/bob/Library/Application Support/Ollama/db.sqlite\")\" = collected ]"
check "cline taskHistory in globalStorage discovers project" "[ \"\$(status_of \"$ROOT/Users/bob/clineproj/.clinerules\")\" = collected ]"
check "cline checkpoints in globalStorage excluded" "[ \"\$(status_of \"$ROOT/Users/bob/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/checkpoints\")\" = skipped_excluded ]"
# 1.4.0 catalog round (2026-10-04)
printf '%s\n' "$CASES14" >"$WORK/cases14"
while IFS='|' read -r _k _a _r; do
  [ -n "$_r" ] || continue
  _row=$(row "$H/$_r")
  case "$_k" in
    excl|exclf) case "$_row" in *'"status":"skipped_excluded"'*) ok "excluded: $_r" ;; *) bad "excluded: $_r" ;; esac ;;
    secret) case "$_row" in *'"secret":true,"status":"collected"'*) ok "secret: $_r" ;; *) bad "secret: $_r" ;; esac ;;
    agent) case "$_row" in *"\"agent\":\"$_a\""*'"status":"collected"'*) ok "$_a: $_r" ;; *) bad "$_a: $_r" ;; esac ;;
  esac
done <"$WORK/cases14"
check "pearai lowercase .config/pearai collected" "[ \"\$(grep -c '/.config/pearai/User/globalStorage/state.vscdb\"' \"\$M\")\" = 1 ]"
check "cody nested globalStorage collected exactly once" "[ \"\$(grep -c 'sourcegraph.cody-ai/symf/indexroot/meta.json' \"\$M\")\" = 1 ]"
check "twinny nested globalStorage collected exactly once" "[ \"\$(grep -c 'globalStorage/rjmacarthy.twinny/twinny-providers.json' \"\$M\")\" = 1 ]"
check "little-coder history nested in .pi collected exactly once" "[ \"\$(grep -c 'little-coder-prompt-history.json' \"\$M\")\" = 1 ]"
check "hermes installer checkout excluded but its .env kept" "[ \"\$(status_of \"$H/.hermes/hermes-agent/hermes_cli\")\" = skipped_excluded ] && [ \"\$(status_of \"$H/.hermes/hermes-agent/.env\")\" = collected ]"
check "openclaw .clawdbot rename symlink recorded" "row \"$B/.clawdbot\" | grep -q '\"agent\":\"openclaw\".*\"type\":\"symlink\".*\"status\":\"symlink\",\"target\":\".openclaw\"'"
check "hermes checkpoint workdir discovers project" "row \"$ROOT/srv/hermesproj/.hermes.md\" | grep -q '\"user\":\"alice\".*\"status\":\"collected\"'"
check "letta sessions.jsonl project discovers project" "[ \"\$(status_of \"$ROOT/srv/lettaproj/.letta/settings.json\")\" = collected ]"
check "project .letta/settings.json flagged secret (accepted overmatch)" "row \"$ROOT/srv/lettaproj/.letta/settings.json\" | grep -q '\"secret\":true'"
check "letta local backend messages cwd discovers project" "[ \"\$(status_of \"$ROOT/srv/lettaproj2/AGENTS.md\")\" = collected ]"
check "pi session cwd discovers project" "[ \"\$(status_of \"$ROOT/srv/piproj/.pi/settings.json\")\" = collected ]"
check "pi misplaced session cwd discovers project" "[ \"\$(status_of \"$ROOT/srv/piproj2/AGENTS.md\")\" = collected ]"
check "pi trust.json keys discover project" "[ \"\$(status_of \"$ROOT/srv/pitrust/pi-session-2026-10-04.html\")\" = collected ]"
check "pi crashes.json cwd discovers project" "[ \"\$(status_of \"$ROOT/srv/picrash/AGENTS.md\")\" = collected ]"
check "pi experimental meta cwd discovers project" "[ \"\$(status_of \"$ROOT/srv/piexp/AGENTS.md\")\" = collected ]"
check "open-interpreter rollout cwd discovers project" "[ \"\$(status_of \"$ROOT/srv/oiproj/.openinterpreter/rules/r.md\")\" = collected ]"
check "open-interpreter archived rollout cwd discovers project" "[ \"\$(status_of \"$ROOT/srv/oiarch/.codewhale/notes.md\")\" = collected ]"
check "openhands workspaces.json path discovers project" "[ \"\$(status_of \"$ROOT/srv/ohproj/.openhands/setup.sh\")\" = collected ]"
check "openhands canvas dev conversation discovers project" "[ \"\$(status_of \"$ROOT/srv/ohdev/AGENTS.md\")\" = collected ]"
check "openhands canvas conversation discovers project" "[ \"\$(status_of \"$ROOT/srv/ohcanvas/AGENTS.md\")\" = collected ]"
check "openhands cli base_state discovers project" "[ \"\$(status_of \"$ROOT/srv/ohcli/AGENTS.md\")\" = collected ]"
check "pearai sessions.json discovers project" "[ \"\$(status_of \"$ROOT/srv/pearproj/.pearairc.json\")\" = collected ]"
check "project .pearai-agent/mcp.json flagged secret" "row \"$ROOT/srv/pearproj/.pearai-agent/mcp.json\" | grep -q '\"secret\":true,\"status\":\"collected\"'"
check "openclaw JSON5 workspace discovers project" "[ \"\$(status_of \"$ROOT/srv/clawws/SOUL.md\")\" = collected ]"
check "openclaw JSON5 agentDir discovers project" "[ \"\$(status_of \"$ROOT/srv/clawagent/AGENTS.md\")\" = collected ]"
check "openclaw legacy clawdbot.json discovers project" "[ \"\$(status_of \"$ROOT/srv/clawlegacy/IDENTITY.md\")\" = collected ]"
check "openclaw profile config discovers project" "[ \"\$(status_of \"$ROOT/srv/clawprofile/MEMORY.md\")\" = collected ]"
check "nanobot .workspace marker discovers project" "[ \"\$(status_of \"$ROOT/srv/nanows/HEARTBEAT.md\")\" = collected ]"
check "nanobot instance config workspace discovers project" "[ \"\$(status_of \"$ROOT/srv/nanocfg/memory/MEMORY.md\")\" = collected ]"
check "tabby config.toml file:// git_url discovers project" "[ \"\$(status_of \"$ROOT/srv/tabbyproj/AGENTS.md\")\" = collected ]"
check "twinny manifest common prefix discovers project" "[ \"\$(status_of \"$ROOT/srv/twinproj/AGENTS.md\")\" = collected ]"
# 1.5.0 Docker volumes (2026-10-04)
A0="$DV/a0_usr/_data"
check "docker volume file collected as agent-zero, user docker" "row \"$A0/chats/ctx1/chat.json\" | grep -q '\"user\":\"docker\",\"home\":\"$A0\",\"agent\":\"agent-zero\".*\"status\":\"collected\"'"
check "docker volume file archived under fs/<original path>" "tar -tzf \"\$A\" | grep -q '^./fs/var/lib/docker/volumes/a0_usr/_data/chats/ctx1/chat.json\$'"
check "docker volume .env flagged secret (volume-relative)" "row \"$A0/.env\" | grep -q '\"secret\":true,\"status\":\"collected\"'"
check "docker volume tmp/playwright excluded (volume-relative)" "[ \"\$(status_of \"$A0/tmp/playwright\")\" = skipped_excluded ]"
check "unmatched volume recorded skipped_unmatched_volume with size" "row \"$DV/pgdata/_data\" | grep -q '\"user\":\"docker\".*\"type\":\"dir\",\"size\":[1-9][0-9]*.*\"status\":\"skipped_unmatched_volume\"'"
check "unmatched volume contents not collected" "! grep -q 'pgdata/_data/x' \"\$M\""
check "volumes dir metadata.db not collected" "! grep -q 'volumes/metadata.db' \"\$M\""
check "rootless volume collected as tabby" "row \"$H/.local/share/docker/volumes/tabby_data/_data/events/2026-10-01.json\" | grep -q '\"user\":\"docker\".*\"agent\":\"tabby\".*\"status\":\"collected\"'"
check "summary counts skipped_unmatched_volume" "grep -q '\"skipped_unmatched_volume\": 1' \"\$S\""
check "summary docker counts" "grep -q '\"docker\": {\"volumes_found\": 3, \"volumes_collected\": 2, \"unreadable\": 0' \"\$S\""
check "summary no_docker option false" "grep -q '\"no_docker\": false' \"\$S\""
check "stdout docker line" "grep -q '^docker:     3 volumes found, 2 collected, 0 unreadable\$' \"$OUT/default.stdout\""
# 2026-10-04 summary: only homes with manifest rows are counted and logged; sizes are also human-readable
check "home without artifacts still listed in users" "tr -d '\n' <\"\$S\" | grep -q '\"users\": \\[[^]]*\"dave\"'"
check "home without artifacts not in users_with_artifacts" "grep -q '\"users_with_artifacts\": \\[\"' \"\$S\" && ! grep '\"users_with_artifacts\"' \"\$S\" | grep -q dave"
check "stdout users counts users_with_artifacts" "[ \"\$(sed -n 's/^users: *//p' \"$OUT/default.stdout\")\" = \"\$(grep '\"users_with_artifacts\"' \"\$S\" | tr ',' '\\n' | grep -c '\"')\" ]"
check "log has no progress line for a home without artifacts" "! grep -q 'User dave' \"$OUT\"/default/*.log && grep -q 'User alice' \"$OUT\"/default/*.log"
check "stdout size is human-readable" "grep -q '^size:       [0-9]* ([0-9.]* \\(B\\|KiB\\|MiB\\))\$' \"$OUT/default.stdout\""
check "stdout collected bytes are human-readable" "grep -q '^collected:  [0-9]* files, [0-9]* bytes ([0-9.]* \\(B\\|KiB\\|MiB\\))\$' \"$OUT/default.stdout\""
check "log done line keeps size and sha256" "grep -q ' done: .* ([0-9]* bytes, sha256 [0-9a-f]\\{64\\})\$' \"$OUT\"/default/*.log"
# 2026-10-04 Muse Code
printf '%s\n' "$CASES_MUSE" >"$WORK/casesmuse"
while IFS='|' read -r _k _a _r; do
  [ -n "$_r" ] || continue
  _row=$(row "$H/$_r")
  case "$_k" in
    excl|exclf) case "$_row" in *'"agent":"muse-code"'*'"status":"skipped_excluded"'*) ok "excluded: $_r" ;; *) bad "excluded: $_r" ;; esac ;;
    secret) case "$_row" in *'"agent":"muse-code"'*'"secret":true,"status":"collected"'*) ok "secret: $_r" ;; *) bad "secret: $_r" ;; esac ;;
    agent) case "$_row" in *"\"agent\":\"$_a\""*'"status":"collected"'*) ok "$_a: $_r" ;; *) bad "$_a: $_r" ;; esac ;;
  esac
done <"$WORK/casesmuse"
check "muse windows binary excluded with its size" "row \"$H/AppData/Local/Programs/muse/muse-bin-1.4.2-R1.exe\" | grep -q '\"type\":\"file\",\"size\":2,.*\"status\":\"skipped_excluded\"'"
check "muse .local/bin glob leaves other tools alone" "! grep -q '/.local/bin/othertool\"' \"\$M\""
check "muse trust.json projects key discovers project" "row \"$ROOT/srv/musetrust/AGENTS.md\" | grep -q '\"user\":\"alice\".*\"status\":\"collected\"'"
check "muse session.jsonl workspace_root discovers project" "row \"$ROOT/srv/museproj/.muse/hooks.json\" | grep -q '\"user\":\"alice\",\"home\":\"$ROOT/srv/museproj\",\"agent\":\"project\".*\"status\":\"collected\"'"
check "muse project .muse/worktrees excluded" "[ \"\$(status_of \"$ROOT/srv/museproj/.muse/worktrees\")\" = skipped_excluded ]"
# 2026-10-04 relocated Claude Code home
check "relocated claude home session collected as claude-code" "row \"$CCW_S\" | grep -q '\"agent\":\"claude-code\".*\"status\":\"collected\"'"
check "relocated claude home history collected as claude-code" "row \"$CCW/history.jsonl\" | grep -q '\"agent\":\"claude-code\".*\"status\":\"collected\"'"
check "relocated claude home credentials flagged secret" "row \"$CCW/.credentials.json\" | grep -q '\"agent\":\"claude-code\".*\"secret\":true,\"status\":\"collected\"'"
check "relocated claude home .claude.json flagged secret" "row \"$CCW/.claude.json\" | grep -q '\"agent\":\"claude-code\".*\"secret\":true,\"status\":\"collected\"'"
check "claude-code-router not collected" "! grep -q '/.claude-code-router/' \"\$M\""
check "relocated .claude.json projects key discovers project" "row \"$ROOT/srv/ccwork/.claude/settings.json\" | grep -q '\"user\":\"alice\".*\"agent\":\"project\".*\"status\":\"collected\"'"
check "relocated history.jsonl discovers project" "row \"$ROOT/srv/cchist/.claude/settings.json\" | grep -q '\"user\":\"alice\".*\"agent\":\"project\".*\"status\":\"collected\"'"
check "no live snapshot directory" "! tar -tzf \"\$A\" | grep -q '^./live/'"
check "summary has no no_live option" "! grep -q no_live \"\$S\""
check "manifest and summary inside archive" "tar -tzf \"\$A\" | grep -q '^./manifest.jsonl' && tar -tzf \"\$A\" | grep -q '^./collection.json'"
check "staging removed" "[ -z \"\$(ls -d \"$OUT/default\"/.stage-* 2>/dev/null)\" ]"
check "no copy errors" "grep -q '\"error_copy\": 0' \"\$S\""
if command -v python3 >/dev/null 2>&1; then
  check "manifest is valid JSONL" "python3 -c 'import json,sys; [json.loads(l) for l in open(sys.argv[1])]' \"\$M\""
  check "summary is valid JSON" "python3 -c 'import json,sys; json.load(open(sys.argv[1]))' \"\$S\""
  check "archived file bytes match staged hash" "cd \"\$WORK\" && mkdir -p x && tar -xzf \"\$A\" -C x && python3 - \"\$M\" x <<'PY'
import json,sys,hashlib,os
m,root=sys.argv[1],sys.argv[2]; n=0
for l in open(m):
    r=json.loads(l)
    if r['status']!='collected' or not r['archive_path']: continue
    p=os.path.join(root,r['archive_path'])
    assert hashlib.sha256(open(p,'rb').read()).hexdigest()==r['sha256'], p
    assert os.path.getsize(p)==r['size'], p
    n+=1
assert n>5
PY"
fi

# ---- --no-secrets ---------------------------------------------------------
run nosecrets --no-secrets; check "no-secrets exit 0" "[ $? -eq 0 ]"
check "credentials skipped_secret" "[ \"\$(status_of \"$ROOT/home/alice/.claude/.credentials.json\")\" = skipped_secret ]"
check "credentials absent from archive" "! tar -tzf \"\$A\" | grep -q credentials.json"

# ---- --full ---------------------------------------------------------------
run full --full; check "full exit 0" "[ $? -eq 0 ]"
check "cache contents collected with --full" "[ \"\$(status_of \"$ROOT/home/alice/.claude/cache/junk.bin\")\" = collected ]"

# ---- -u filter ------------------------------------------------------------
run users -u bob; check "users exit 0" "[ $? -eq 0 ]"
check "only bob collected" "! grep -q '\"user\":\"alice\"' \"\$M\" && grep -q '\"user\":\"bob\"' \"\$M\""

# ---- --no-docker ----------------------------------------------------------
run nodocker --no-docker; check "no-docker exit 0" "[ $? -eq 0 ]"
check "no-docker collects no volume" "! grep -q 'docker/volumes' \"\$M\""
check "no-docker recorded in options" "grep -q '\"no_docker\": true' \"\$S\""
check "no-docker prints no docker line" "! grep -q '^docker:' \"$OUT/nodocker.stdout\""

# ---- unreadable volume (needs a non-root user; chmod 000 does not stop root)
if [ "$(id -u)" != 0 ]; then
  mkdir -p "$DV/hermes_data/_data/sessions"
  printf '{}\n' >"$DV/hermes_data/_data/sessions/s.json"
  chmod 000 "$DV/hermes_data/_data"
  # a root-only data root, as /var/lib/containers is for a non-root responder
  mkdir -p "$ROOT/var/lib/containers/storage/volumes/x_ollama/_data"
  chmod 000 "$ROOT/var/lib/containers"
  run dockerperm; check "unreadable volume exit 0" "[ $? -eq 0 ]"
  chmod 700 "$DV/hermes_data/_data" "$ROOT/var/lib/containers"
  check "unreadable volume and data root counted in stdout" "grep -q '^docker:     4 volumes found, 2 collected, 2 unreadable (run as root to collect)\$' \"$OUT/dockerperm.stdout\""
  check "unreadable volume noted in collection.json" "grep -q 'docker: volume hermes_data (hermes) at .* is not readable' \"\$S\""
  check "unreadable data root noted in collection.json" "grep -q 'docker: [^\"]*/var/lib/containers is not readable' \"\$S\""
  check "other volumes still collected" "[ \"\$(status_of \"$A0/chats/ctx1/chat.json\")\" = collected ]"
  rm -rf "$DV/hermes_data" "$ROOT/var/lib/containers"
else
  printf 'skip unreadable volume check (running as root)\n'
fi

# ---- Docker Desktop note (macOS layout) -----------------------------------
mkdir -p "$B/Library/Containers/com.docker.docker/Data"
run desktop; check "docker desktop exit 0" "[ $? -eq 0 ]"
check "docker desktop noted in stdout" "grep -q '^docker:     3 volumes found, 2 collected, 0 unreadable; Docker Desktop VM disk not collected\$' \"$OUT/desktop.stdout\""
check "docker desktop noted in collection.json" "grep -q '\"docker: Docker Desktop data at .*com.docker.docker; volumes inside its virtual machine disk are not collected\"' \"\$S\" && grep -q '\"docker_desktop\": true' \"\$S\""
rm -rf "$B/Library/Containers"

# ---- --inventory (1.6.0, 2026-10-04) ---------------------------------------
# Stat-only fleet inventory: JSON Lines on stdout, nothing written anywhere.
inv() { # inv NAME ARGS... -> $OUT/NAME.stdout and $OUT/NAME.stderr
  _n=$1; shift
  COLLECTOR_SH="$SHELL_UNDER_TEST" "$SHELL_UNDER_TEST" "$SCRIPT" -r "$ROOT" --inventory "$@" >"$OUT/$_n.stdout" 2>"$OUT/$_n.stderr"
}
# shellcheck disable=SC2317,SC2329 # called from the eval'd check strings
agent_line() { grep -F "\"user\":\"$2\",\"agent\":\"$3\"," "$OUT/$1.stdout" | head -n1; }
INV_HOST_RE='^{"type":"host","host":"[^"]*","collector":"[0-9.]*","mode":"image","at":"[0-9-]*T[0-9:]*Z","users_scanned":[0-9]*,"users_unreadable":[0-9]*,"docker_volumes":[0-9]*}$'
INV_AGENT_RE='^{"type":"agent","host":"[^"]*","user":"[^"]*","agent":"[^"]*","files":[0-9]*,"bytes":[0-9]*,"first":"[^"]*","last":"[^"]*","projects":[0-9]*,"evidence":"[^"]*"}$'
TZ=UTC0 touch -t 202609150102.03 "$ROOT/home/ollama/.ollama/history"
mkdir -p "$OUT/invcwd" "$B/.gemini/antigravity-cli/conversations"
# bob's ~/.gemini holds only the nested antigravity-cli entry: no gemini-cli line.
printf 'db\n' >"$B/.gemini/antigravity-cli/conversations/b1.db"
(cd "$OUT/invcwd" && inv inventory -q); check "inventory exit 0" "[ $? -eq 0 ]"
check "inventory writes nothing in the current directory" "[ -z \"\$(ls -A \"$OUT/invcwd\")\" ]"
check "inventory -q leaves stderr empty" "[ ! -s \"$OUT/inventory.stderr\" ]"
check "inventory first line is the host line, keys in order" "head -n1 \"$OUT/inventory.stdout\" | grep -q '$INV_HOST_RE'"
check "inventory host line counts" "head -n1 \"$OUT/inventory.stdout\" | grep -q '\"users_unreadable\":0,\"docker_volumes\":3}\$'"
check "inventory every later line is an agent line, keys in order" "[ \"\$(sed 1d \"$OUT/inventory.stdout\" | grep -vc '$INV_AGENT_RE')\" = 0 ] && [ \"\$(grep -c . \"$OUT/inventory.stdout\")\" -gt 10 ]"
check "inventory ollama line: one file, excluded models not counted" "agent_line inventory ollama ollama | grep -q '\"files\":1,\"bytes\":5,\"first\":\"2026-09-15T01:02:03Z\",\"last\":\"2026-09-15T01:02:03Z\",\"projects\":0,\"evidence\":\".ollama\"}\$'"
check "inventory claude-code evidence in catalog order" "agent_line inventory alice claude-code | grep -q '\"evidence\":\".claude,.claude.json\\*,.claude-\\*/projects,.claude-\\*/history.jsonl,.claude-\\*/.claude.json\\*,.claude-\\*/.credentials.json\"}\$'"
check "inventory first and last set for alice claude-code" "agent_line inventory alice claude-code | grep -q '\"first\":\"20[0-9-]*T[0-9:]*Z\",\"last\":\"20[0-9-]*T[0-9:]*Z\"'"
check "inventory nested entry claimed from the enclosing agent" "agent_line inventory alice antigravity | grep -q '\"evidence\":\"[^\"]*.gemini/antigravity-cli' && agent_line inventory alice gemini-cli | grep -q '\"evidence\":\".gemini\"'"
check "inventory: matched directory with no files of its own gives no line" "[ -z \"\$(agent_line inventory bob gemini-cli)\" ] && agent_line inventory bob antigravity | grep -q '\"files\":1,\"bytes\":3,.*\"evidence\":\".gemini/antigravity-cli\"}\$'"
check "inventory: no agent line has zero files" "! grep -q '\"files\":0,' \"$OUT/inventory.stdout\""
check "inventory projects counted per user" "agent_line inventory alice claude-code | grep -q '\"projects\":[1-9]'"
check "inventory docker volume line" "agent_line inventory docker agent-zero | grep -q '\"files\":2,\"bytes\":63,.*\"projects\":0,\"evidence\":\"\\*a0_usr\"}\$'"
check "inventory rootless docker volume line" "agent_line inventory docker tabby | grep -q '\"files\":1,\"bytes\":23,.*\"evidence\":\"\\*tabby\\*\"}\$'"
check "inventory shared not inventoried" "! grep -q '\"agent\":\"\\(shared\\|project\\|live\\)\"' \"$OUT/inventory.stdout\""
check "inventory prints no path below a home" "! grep -q '$ROOT' \"$OUT/inventory.stdout\""
if command -v python3 >/dev/null 2>&1; then
  check "inventory stdout is valid JSON Lines" "python3 -c 'import json,sys; [json.loads(l) for l in open(sys.argv[1])]' \"$OUT/inventory.stdout\""
fi
inv inventory-o -o "$OUT/inv-o"; check "inventory with -o exit 0" "[ $? -eq 0 ]"
check "inventory with -o creates no output directory" "[ ! -e \"$OUT/inv-o\" ]"
check "inventory with -o notes it on stderr" "grep -q 'NOTE: --inventory writes nothing; -o .*inv-o ignored' \"$OUT/inventory-o.stderr\""
check "inventory without -q logs to stderr only" "[ -s \"$OUT/inventory-o.stderr\" ] && [ \"\$(grep -vc '$INV_HOST_RE' \"$OUT/inventory-o.stdout\" | head -n1)\" = \"\$(grep -c '$INV_AGENT_RE' \"$OUT/inventory-o.stdout\")\" ]"
inv inventory-full -q --full
check "inventory --full counts excluded files" "agent_line inventory-full ollama ollama | grep -q '\"files\":2,\"bytes\":10,'"
inv inventory-u -q -u bob --no-docker
check "inventory -u keeps one user" "! grep -q '\"user\":\"alice\"' \"$OUT/inventory-u.stdout\" && grep -q '\"user\":\"bob\"' \"$OUT/inventory-u.stdout\""
check "inventory --no-docker: no volumes, no docker lines" "head -n1 \"$OUT/inventory-u.stdout\" | grep -q '\"users_scanned\":1,\"users_unreadable\":0,\"docker_volumes\":0}' && ! grep -q '\"user\":\"docker\"' \"$OUT/inventory-u.stdout\""
rm -rf "$B/.gemini"
if [ "$(id -u)" != 0 ]; then
  mkdir -p "$ROOT/home/carol/.claude"
  chmod 000 "$ROOT/home/carol"
  inv inventory-perm -q; check "inventory unreadable home exit 0" "[ $? -eq 0 ]"
  chmod 700 "$ROOT/home/carol"
  check "inventory counts the unreadable home" "head -n1 \"$OUT/inventory-perm.stdout\" | grep -q '\"users_unreadable\":1,'"
  check "inventory scanned count includes it" "[ \"\$(head -n1 \"$OUT/inventory-perm.stdout\" | sed 's/.*\"users_scanned\":\\([0-9]*\\).*/\\1/')\" = \"\$(( \$(head -n1 \"$OUT/inventory.stdout\" | sed 's/.*\"users_scanned\":\\([0-9]*\\).*/\\1/') + 1 ))\" ]"
  rm -rf "$ROOT/home/carol"
else
  printf 'skip unreadable home inventory check (running as root)\n'
fi

# ---- live mode without the snapshot (1.6.0) --------------------------------
mkdir -p "$OUT/livehost"
COLLECTOR_SH="$SHELL_UNDER_TEST" "$SHELL_UNDER_TEST" "$SCRIPT" -o "$OUT/livehost" -q -u no-such-user-cac --no-docker --no-projects >/dev/null 2>&1
check "live mode exit 0" "[ $? -eq 0 ]"
LA=$(ls "$OUT/livehost"/*.tar.gz 2>/dev/null)
check "live mode writes no live directory" "! tar -tzf \"$LA\" | grep -q '^./live/'"
check "live mode manifest has no live rows" "! tar -xzOf \"$LA\" ./manifest.jsonl | grep -q '\"agent\":\"live\"'"
check "live mode collection.json has hostname and no no_live" "tar -xzOf \"$LA\" ./collection.json | grep -q '\"hostname\": \"[^\"]' && ! tar -xzOf \"$LA\" ./collection.json | grep -q no_live"
check "--no-live is no longer an option" "! \"$SHELL_UNDER_TEST\" \"$SCRIPT\" --no-live -o \"$OUT/nolive\" -q >/dev/null 2>&1"

# ---- --list ---------------------------------------------------------------
check "--list prints catalog" "\"$SHELL_UNDER_TEST\" \"$SCRIPT\" --list | grep -q '^claude-code|.claude$'"
check "--list prints docker volume table" "\"$SHELL_UNDER_TEST\" \"$SCRIPT\" --list | grep -q '^agent-zero|\\*a0_usr$'"

# 2026-10-04 bug round: #31
# collection.json names the archive and archiver actually used, and records
# the project options. A PATH shim tar that rejects -z forces the tar | gzip
# fallback; a shim gzip that fails as well forces the plain .tar fallback. The
# collector puts the system directories first on PATH, so these runs use a
# copy of it whose PATH line puts the shim directory first.
SUMS=$(ls "$OUT/default"/*.collection.json)
check "#31 default summary: archiver tar -z, .tar.gz" "grep -q '\"archiver\": \"tar -z\"' \"$SUMS\" && grep -q '\"archive\": \"[^\"]*\\.tar\\.gz\"' \"$SUMS\""
check "#31 default summary: no_projects false, projects empty" "grep -q '\"no_projects\": false, \"projects\": \\[\\]' \"$SUMS\""
SHIM="$WORK/shim31"; mkdir -p "$SHIM"
REAL_TAR=$(command -v tar)
# shellcheck disable=SC2016 # $1 and $@ belong to the shim, not to this script
printf '#!/bin/sh\ncase "$1" in *z*) echo "tar: -z not supported" >&2; exit 2 ;; esac\nexec "%s" "$@"\n' "$REAL_TAR" >"$SHIM/tar"
chmod +x "$SHIM/tar"
sed "s|^PATH=\"/usr/bin:|PATH=\"$SHIM:/usr/bin:|" "$SCRIPT" >"$SHIM/collector.sh"
check "#31 shimmed collector copy puts the shim first" "grep -q '^PATH=\"$SHIM:/usr/bin:' \"$SHIM/collector.sh\""
_sc31=$SCRIPT; SCRIPT="$SHIM/collector.sh"
run tgz31 -p "$ROOT/srv/ccwork" -p "$ROOT/srv/cchist"; _rc31=$?
check "#31 tar | gzip fallback exit 0" "[ $_rc31 -eq 0 ] && [ -s \"\$A\" ]"
check "#31 tar | gzip: on-disk summary names tar | gzip" "grep -q '\"archiver\": \"tar | gzip\"' \"\$S\" && grep -q \"\\\"archive\\\": \\\"\${A##*/}\\\"\" \"\$S\""
check "#31 tar | gzip: archived summary matches on-disk" "tar -xzOf \"\$A\" ./collection.json | cmp -s - \"\$S\""
check "#31 -p values recorded in options.projects" "grep -q '\"no_projects\": false, \"projects\": \\[\"$ROOT/srv/ccwork\",\"$ROOT/srv/cchist\"\\]' \"\$S\""
printf '#!/bin/sh\ncat >/dev/null; echo "gzip: broken" >&2; exit 1\n' >"$SHIM/gzip"
chmod +x "$SHIM/gzip"
run tar31 --no-projects; _rc31=$?
SCRIPT=$_sc31
T31=$(ls "$OUT/tar31"/*.tar 2>/dev/null)
check "#31 plain tar fallback exit 0, no .tar.gz left" "[ $_rc31 -eq 0 ] && [ -s \"$T31\" ] && [ -z \"\$A\" ]"
check "#31 plain tar: on-disk summary names .tar and tar" "grep -q '\"archiver\": \"tar\"' \"\$S\" && grep -q \"\\\"archive\\\": \\\"\${T31##*/}\\\"\" \"\$S\""
check "#31 plain tar: archived summary matches on-disk" "tar -xOf \"$T31\" ./collection.json | cmp -s - \"\$S\""
check "#31 plain tar: sidecar names .tar" "grep -q \"  \${T31##*/}\\\$\" \"$T31.sha256\""
check "#31 --no-projects recorded" "grep -q '\"no_projects\": true, \"projects\": \\[\\]' \"\$S\""
if command -v python3 >/dev/null 2>&1; then
  check "#31 fallback summaries are valid JSON" "python3 -c 'import json,sys; [json.load(open(f)) for f in sys.argv[1:]]' \"\$S\" \"$OUT\"/tgz31/*.collection.json"
fi

if [ "$fail" = 0 ]; then printf 'ALL PASSED (%s)\n' "$SHELL_UNDER_TEST"; rm -rf "$WORK"; else printf 'FAILURES (%s); work dir kept: %s\n' "$SHELL_UNDER_TEST" "$WORK"; fi
exit "$fail"
