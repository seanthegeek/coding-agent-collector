<#
.SYNOPSIS
  Forensic collector for AI coding agent artifacts on Windows.

.DESCRIPTION
  Windows counterpart of collect-agent-artifacts.sh. Collects the on-disk state
  of AI coding agents (Claude Code, Gemini CLI, Antigravity, Codex CLI, Copilot
  CLI, Cursor, Windsurf, Continue, Aider, Ollama, ...) for every user profile on
  a host, plus PowerShell history and a live system snapshot, into a single
  tar.gz (via the built-in tar.exe on Windows 10 1803+) or zip, with a JSONL
  manifest. Same catalog, manifest schema and archive layout as the sh script.

  Windows PowerShell 5.1 compatible. No modules, no prompts, nothing from stdin.
  Run as:  powershell.exe -ExecutionPolicy Bypass -File Collect-AgentArtifacts.ps1 -OutputDir C:\ir

.PARAMETER OutputDir
  Directory for the archive (default: current directory).
.PARAMETER Root
  Alternate root such as a mounted disk image (image mode; disables the live snapshot).
.PARAMETER Users
  Comma-separated profile names to collect (default: all).
.PARAMETER Project
  Extra project directory to collect (repeatable).
.PARAMETER Full
  Disable default size exclusions.
.PARAMETER NoSecrets
  Skip credential files instead of collecting them.
.PARAMETER NoLive
  Skip the live system snapshot.
.PARAMETER NoProjects
  Skip project-level artifact discovery.
.PARAMETER MaxFileSizeMB
  Skip files larger than this (default 256, 0 = none).
.PARAMETER KeepStaging
  Keep the staging directory after archiving.
.PARAMETER List
  Print the artifact catalog and exit.
.PARAMETER Quiet
  Only print the final summary.
.PARAMETER Version
  Print version and exit.

.NOTES
  Copyright 2026 Sean Whalen
  SPDX-License-Identifier: Apache-2.0
  Exit codes: 0 archive written (per-file errors are in the manifest),
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
  [switch]$NoLive,
  [switch]$NoProjects,
  [int]$MaxFileSizeMB = 256,
  [Alias('k')][switch]$KeepStaging,
  [switch]$List,
  [Alias('q')][switch]$Quiet,
  [switch]$Version
)

Set-StrictMode -Version 2
$ErrorActionPreference = 'Continue'
$ToolVersion = '1.1.0'
$TOOL = 'collect-agent-artifacts'

# ---------------------------------------------------------------------------
# Artifact catalog. Identical to the tables in collect-agent-artifacts.sh;
# tests/catalog-sync.sh fails if they drift. agent|glob relative to each home.
# ---------------------------------------------------------------------------
$CATALOG = @'
# Anthropic
claude-code|.claude
claude-code|.claude.json*
claude-desktop|Library/Application Support/Claude
claude-desktop|Library/Application Support/Claude-3p
claude-desktop|Library/Logs/Claude
claude-desktop|Library/Logs/Claude-3p
claude-desktop|.config/Claude
claude-desktop|.config/Claude-3p
claude-desktop|AppData/Roaming/Claude
claude-desktop|AppData/Roaming/Claude-3p
claude-desktop|AppData/Local/Claude-3p
# Google
gemini-cli|.gemini
gemini-cli|.cache/.gemini
antigravity|.antigravity
antigravity|.cache/antigravity
antigravity|.config/Antigravity/User
antigravity|.config/Antigravity/logs
antigravity|Library/Application Support/Antigravity/User
antigravity|Library/Application Support/Antigravity/logs
antigravity|AppData/Roaming/Antigravity/User
antigravity|AppData/Roaming/Antigravity/logs
# OpenAI
codex-cli|.codex
chatgpt-desktop|Library/Application Support/com.openai.chat
chatgpt-desktop|AppData/Local/Packages/OpenAI.ChatGPT-Desktop_*/LocalCache/Roaming/ChatGPT
# GitHub Copilot (CLI, and the OAuth token store used by Copilot plugins)
copilot-cli|.copilot
copilot|.config/github-copilot
copilot|AppData/Local/github-copilot
# Cursor
cursor|.cursor
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
vscode|Library/Application Support/VSCodium/User
vscode|.config/VSCodium/User
vscode|AppData/Roaming/VSCodium/User
# Windsurf (rebranding to Devin)
windsurf|.codeium
windsurf|.windsurf/extensions/extensions.json
windsurf|.config/devin
windsurf|AppData/Roaming/devin
windsurf|Library/Application Support/Windsurf/User
windsurf|.config/Windsurf/User
windsurf|AppData/Roaming/Windsurf/User
windsurf|Library/Application Support/Devin/User
windsurf|.config/Devin/User
windsurf|AppData/Roaming/Devin/User
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
# Goose (XDG on macOS too; Electron app dir is separate)
goose|.config/goose
goose|.local/share/goose
goose|.local/state/goose
goose|.config/Goose
goose|Library/Application Support/Goose
goose|AppData/Roaming/Block/goose
goose|AppData/Roaming/Goose
goose|.goose
# Zed (config in ~/.config/zed on macOS too; data under Library)
zed|.config/zed
zed|.local/share/zed
zed|Library/Application Support/Zed
zed|Library/Logs/Zed
zed|AppData/Roaming/Zed
zed|AppData/Local/Zed
# Qwen Code
qwen-code|.qwen
# Amp (data dir is ~/.local/share/amp on every OS; threads are server-side)
amp|.config/amp
amp|.local/share/amp
amp|.cache/amp/logs
amp|AppData/Local/amp/logs
# Factory Droid
factory-droid|.factory
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
# Shared cross-agent directories (skills, instructions, env files read by several agents)
shared|.agents
shared|.config/AGENTS.md
shared|.config/agents
shared|.env
# Ollama
ollama|.ollama
# Shell history
shell-history|.bash_history
shell-history|.zsh_history
shell-history|.zsh_sessions
shell-history|.sh_history
shell-history|.history
shell-history|.local/share/fish/fish_history
shell-history|.config/fish/fish_history
shell-history|AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt
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
project|.devin
project|.clinerules
project|.cline
project|.roo
project|.roomodes
project|.rooignore
project|.kilo
project|.kilocode
project|.kilocodemodes
project|.kilocodeignore
project|kilo.json*
project|.continue
project|.continuerc.json
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
project|.goosehints
project|.goose
project|.zed
project|.rules
project|.github/copilot-instructions.md
project|.vscode/mcp.json
project|.amp
project|.factory
project|.droid.yaml
project|.augment
project|.augment-guidelines
project|.augmentignore
project|.kiro
project|.amazonq
project|AmazonQ.md
project|.env
'@

$EXCLUDES = @'
.claude/cache
.claude/plugins/marketplaces
.claude/plugins/*/node_modules
.claude/worktrees
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
.gemini/antigravity-cli/bin
.antigravity/extensions
.codex/packages
.codex/cache
.codex/.tmp
.codex/plugins/cache
.codex/skills/.system
.codex/db-backups
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
.cursor/extensions
.cursor/worktrees
*/Cursor/User/globalStorage/state.vscdb.backup
.codeium/windsurf/implicit
.codeium/*/bin
.codeium/bin
.windsurf/extensions
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
*/User/workspaceStorage/*/ms-*
*/User/workspaceStorage/*/vscjava*
*/User/workspaceStorage/*/redhat*
*/User/workspaceStorage/*/rust-lang*
.cline/data/checkpoint-scratch
.vscode-mock/global-storage/tasks/*/checkpoints
.local/share/kilo/snapshot
.local/share/kilo/repos
.local/share/kilo/tool-output
.local/share/kilo/log
.local/state/kilo/indexing
.local/share/kilo/state/indexing
.kilocode/worktrees
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
.local/share/goose/apps
.local/state/goose/codex
AppData/Roaming/Block/goose/data/models
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
.qwen/updates
.qwen/extension-store
.qwen/extensions/*/node_modules
.qwen/bin
.qwen/sandbox
.qwen/scratch-workspaces
.qwen/locales
.cache/amp/runner-desktop
.cache/amp/desktop
.factory/updates
.factory/cache
.factory/temp
.factory/worktrees
.factory/snapshots
.factory/generated-images
.augment/binaries
.augment/vfs
.augment/knowledgebase
.augment/uploads
.augment/worktrees
.aws/amazonq/cli-checkouts
.aws/amazonq/knowledge_bases
.kiro/powers
*/User/globalStorage/kiro.kiroagent/*lance*
.ollama/models
'@

$SECRET_GLOBS = @'
.claude/.credentials.json
Library/Application Support/Claude*/config.json
Library/Application Support/Claude*/Cookies*
Library/Application Support/Claude*/host-creds-*.json
Library/Application Support/Claude*/ccd-session-secrets/*
.config/Claude*/config.json
.config/Claude*/Cookies*
AppData/Roaming/Claude*/config.json
AppData/Roaming/Claude*/Cookies*
AppData/Local/Claude*/config.json
AppData/Local/Claude*/Cookies*
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
.codex/auth.json
.codex/.credentials.json
.codex/secrets/*
*/Roaming/ChatGPT/Network/Cookies*
.config/github-copilot/*.json
AppData/Local/github-copilot/*.json
.codeium/config.json
.cline/data/settings/providers.json
.cline/data/secrets.json
.cline/data/connectors/settings.json
.cline/data/db/connectors.db*
.vscode-mock/global-storage/secrets.json
.local/share/kilo/auth.json
.local/share/kilo/mcp-auth.json
.kilocode/cli/config.json
.continue/auth*.json
.continue/.env
.continue/config.yaml
.continue/config.json
.continue/config.ts
.continue/.configs/*/config.js*
.continue/mcpServers/*
.continue/index/globalContext.json
.aider/oauth-keys.env
.aider.conf.yml
.aider.model.settings.yml
.local/share/opencode/auth.json
.local/share/opencode/mcp-auth.json
.local/share/opencode/opencode*.db*
.config/opencode/opencode.json*
.config/opencode/config.json
.local/share/crush/crush.json
.config/crush/crush.json
.config/crush/crushrc
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
.config/goose/roaming_node_key
.config/goose/tls/*
AppData/Roaming/Block/goose/config/secrets.yaml
.local/state/goose/logs/llm_request.*
.config/zed/development_credentials
.config/zed/settings.json
AppData/Roaming/Zed/development_credentials
AppData/Roaming/Zed/settings.json
.local/share/amp/secrets.json
.local/share/amp/accounts.json
.config/amp/secrets.json
.factory/auth.json
.factory/prem-auth/*/credentials.*
.factory/mcp-oauth*
.augment/session.json
*/kiro-cli/data.sqlite3*
*/amazon-q/data.sqlite3*
.aws/sso/cache/*.json
.kiro/settings/mcp.json
.ollama/id_ed25519
.env
'@

$AGENT_PROC_RE = 'claude|gemini|antigravity|codex|copilot|cursor|windsurf|codeium|devin|ollama|aider|opencode|\\amp(\.exe)?( |$)|goose|continue|\\cn(\.exe)?( |$)|\\zed(\.exe)?( |$)|qwen|kiro|cline|roo-cline|kilo|augment|auggie|droid|crush|amazon-q'

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
        if ($j -gt $i) { [void]$sb.Append($glob.Substring($i, $j - $i + 1)); $i = $j }
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
# Setup
# ---------------------------------------------------------------------------
$Mode = 'live'
if ($Root -ne '') {
  if (-not (Test-PathQuiet $Root 'Container')) { Write-Error "Root is not a directory: $Root"; exit 2 }
  $Root = (Resolve-Path -LiteralPath $Root).Path.TrimEnd('\', '/')
  $Mode = 'image'; $NoLive = $true
}
if (-not (Test-PathQuiet $OutputDir 'Any')) { try { New-Item -ItemType Directory -Path $OutputDir -Force -ErrorAction Stop | Out-Null } catch { Write-Error "Cannot create output dir: $OutputDir"; exit 2 } }
$OutputDir = (Resolve-Path -LiteralPath $OutputDir).Path.TrimEnd('\', '/')
if ($OutputDir -eq '') { $OutputDir = $Sep }

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
$IsWindowsHost = ($env:OS -eq 'Windows_NT')
if ($IsWindowsHost) { $tarCmd = Get-Command tar.exe -ErrorAction SilentlyContinue } else { $tarCmd = Get-Command tar -ErrorAction SilentlyContinue }
if ($tarCmd) { $TarExe = $tarCmd.Source }
if ($TarExe) { $Archive = Join-PathSafe $OutputDir "$Name.tar.gz" } else { $Archive = Join-PathSafe $OutputDir "$Name.zip" }

New-Item -ItemType Directory -Path (Join-PathSafe $Stage 'fs') -Force | Out-Null
$script:LogWriter = New-Object System.IO.StreamWriter($LogPath, $false, $Utf8NoBom)
$script:ManifestWriter = New-Object System.IO.StreamWriter($ManifestPath, $false, $Utf8NoBom)
$script:LogWriter.AutoFlush = $true
$script:Counts = @{ collected = 0; symlink = 0; skipped_excluded = 0; skipped_size = 0; skipped_secret = 0; error_copy = 0; bytes = [int64]0 }

function Write-Log([string]$msg) {
  $ts = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
  $script:LogWriter.WriteLine("$ts $msg")
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
  if ($status -eq 'collected') { $script:Counts['bytes'] += $size }
}

function Get-ArchiveRel([string]$full) {
  if ($Mode -eq 'image') { return 'fs/' + (Get-RelPath $Root $full) }
  if ($full.Length -ge 3 -and $full[1] -eq ':') { return 'fs/' + $full.Substring(0, 1).ToUpper() + '/' + $full.Substring(3).Replace('\', '/') }
  return 'fs/' + $full.TrimStart('\').Replace('\', '/')
}

# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------
function Add-File([string]$user, [string]$homeDir, [string]$agent, $item) {
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
      Write-Log "copy failed: ${full}: $err"
      try { if (Test-PathQuiet $dest 'Any') { Remove-Item -LiteralPath $dest -Force } } catch { }
    }
  }
  $apath = ''; if ($status -eq 'collected') { $apath = $arel }
  Write-Row $user $homeDir $agent $full $apath $type $size $mtime $atime 0 $btime $owner $attrs $sha $secret $status $target $err
}

function Add-Excluded([string]$user, [string]$homeDir, [string]$agent, $item) {
  $full = $item.FullName
  if ($item.PSIsContainer) { $type = 'dir'; $size = Get-DirSize $full } else { $type = 'file'; $size = [int64]0; try { $size = [int64]$item.Length } catch { } }
  Write-Row $user $homeDir $agent $full '' $type $size (Get-Epoch $item.LastWriteTimeUtc) (Get-Epoch $item.LastAccessTimeUtc) 0 (Get-Epoch $item.CreationTimeUtc) '' ([string]$item.Attributes) '' $false 'skipped_excluded' '' ''
}

function Add-Tree([string]$user, [string]$homeDir, [string]$agent, [string]$dir) {
  $children = @()
  try { $children = @(Get-ChildItem -LiteralPath $dir -Force -ErrorAction Stop) }
  catch { Write-Log "list failed: ${dir}: $($_.Exception.Message)"; return }
  foreach ($child in $children) {
    $hrel = Get-RelPath $homeDir $child.FullName
    if (Test-AnyMatch $hrel $script:ExcludeRegexes) { Add-Excluded $user $homeDir $agent $child; continue }
    $isLink = (($child.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
    if ($child.PSIsContainer -and -not $isLink) { Add-Tree $user $homeDir $agent $child.FullName }
    else { Add-File $user $homeDir $agent $child }
  }
}

function Add-Path([string]$user, [string]$homeDir, [string]$agent, [string]$path) {
  $item = $null
  try { $item = Get-Item -LiteralPath $path -Force -ErrorAction Stop } catch { Write-Log "stat failed: ${path}: $($_.Exception.Message)"; return }
  $hrel = Get-RelPath $homeDir $path
  if (Test-AnyMatch $hrel $script:ExcludeRegexes) { Add-Excluded $user $homeDir $agent $item; return }
  $isLink = (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
  if ($item.PSIsContainer -and -not $isLink) { Add-Tree $user $homeDir $agent $path } else { Add-File $user $homeDir $agent $item }
}

function Invoke-CatalogCollection([string]$user, [string]$base, [string]$table) {
  foreach ($line in (Get-TableLines $table)) {
    $parts = @($line -split '\|', 2)
    if ($parts.Count -lt 2) { continue }
    $agent = $parts[0]; $pattern = $parts[1]
    foreach ($m in (Expand-Glob $base $pattern)) {
      Write-Log "  [$agent] $m"
      Add-Path $user $base $agent $m
    }
  }
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
    if (-not (Test-PathQuiet $hp 'Container')) { $script:InaccessibleHomes += $hp; continue }
    if ($wanted.Count -gt 0 -and -not ($wanted -contains $h.user)) { continue }
    $key = $hp.ToLowerInvariant()
    if ($seen.ContainsKey($key)) { continue }
    $seen[$key] = $true
    $out += @{ user = $h.user; home = $hp }
  }
  return $out
}

$script:InaccessibleHomes = @()
$UserList = @(Get-UserHomes)

Write-Log "$TOOL $ToolVersion starting on $HostName ($([Environment]::OSVersion.VersionString), PowerShell $($PSVersionTable.PSVersion)) mode=$Mode root=$(if ($Root) { $Root } else { '\' })"
Write-Log "archive=$(if ($TarExe) { 'tar.gz via ' + $TarExe } else { 'zip (tar.exe not found)' }) max_file_size=${MaxFileSizeMB}MB full=$($Full.IsPresent) no_secrets=$($NoSecrets.IsPresent)"
$IsAdmin = $false
try { $IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) } catch { }
if ($Mode -eq 'live' -and -not $IsAdmin) { Write-Log "WARNING: not running as Administrator; other users' profiles will probably be unreadable" }
if ($UserList.Count -eq 0) { Write-Log 'WARNING: no user profile directories found' }
foreach ($ih in $script:InaccessibleHomes) { Write-Log "profile not accessible (skipped): $ih" }

# ---------------------------------------------------------------------------
# Live snapshot
# ---------------------------------------------------------------------------
function Write-LiveFile([string]$rel, [scriptblock]$body) {
  $p = Join-PathSafe $Stage $rel
  $d = Split-Path -Path $p -Parent
  if (-not (Test-PathQuiet $d 'Any')) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
  $text = ''
  try { $text = (& $body | Out-String -Width 4096) } catch { $text = "error: $($_.Exception.Message)" }
  [System.IO.File]::AppendAllText($p, $text, $Utf8NoBom)
}
function Register-Generated([string]$agent, [string]$rel) {
  $p = Join-PathSafe $Stage $rel
  if (-not (Test-PathQuiet $p 'Any')) { return }
  $it = Get-Item -LiteralPath $p -Force
  if ($it.Length -eq 0) { Remove-Item -LiteralPath $p -Force; return }
  Write-Row '' '' $agent '' $rel 'file' ([int64]$it.Length) (Get-Epoch $it.LastWriteTimeUtc) (Get-Epoch $it.LastAccessTimeUtc) 0 (Get-Epoch $it.CreationTimeUtc) '' '' (Get-FileSha256 $p) $false 'collected' '' ''
}

if (-not $NoLive) {
  Write-Log 'Live snapshot'
  Write-LiveFile 'live/system.txt' { "# hostname`n$HostName"; "# date -u`n$((Get-Date).ToUniversalTime().ToString('o'))"; '# Win32_OperatingSystem'; Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture, InstallDate, LastBootUpTime, LocalDateTime, RegisteredUser | Format-List; '# Win32_ComputerSystem'; Get-CimInstance Win32_ComputerSystem | Select-Object Name, Domain, Manufacturer, Model, UserName, TotalPhysicalMemory | Format-List; '# whoami'; whoami.exe /all; '# volumes'; Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID, VolumeName, FileSystem, Size, FreeSpace | Format-Table -AutoSize }
  Write-LiveFile 'live/users.txt' { '# ProfileList'; Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList' | ForEach-Object { $v = Get-ItemProperty -LiteralPath $_.PSPath; "$($_.PSChildName)`t$($v.ProfileImagePath)" }; '# Win32_UserAccount (local)'; Get-CimInstance Win32_UserAccount -Filter 'LocalAccount=True' | Select-Object Name, SID, Disabled, Lockout, PasswordRequired | Format-Table -AutoSize }
  Write-LiveFile 'live/logins.txt' { '# query user'; query.exe user 2>&1; '# Win32_LoggedOnUser'; Get-CimInstance Win32_LoggedOnUser | ForEach-Object { "$($_.Antecedent.Domain)\$($_.Antecedent.Name)`tLogon $($_.Dependent.LogonId)" } | Sort-Object -Unique }
  Write-LiveFile 'live/processes.txt' { Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId, SessionId, @{n='CreationDate';e={$_.CreationDate.ToUniversalTime().ToString('o')}}, ExecutablePath, CommandLine | Format-Table -AutoSize -Wrap }
  Write-LiveFile 'live/agent-processes.txt' { Get-CimInstance Win32_Process | Where-Object { ($_.CommandLine -and $_.CommandLine -match $AGENT_PROC_RE) -or ($_.ExecutablePath -and $_.ExecutablePath -match $AGENT_PROC_RE) } | Where-Object { $_.CommandLine -notmatch 'Collect-AgentArtifacts' } | ForEach-Object { $o = $null; try { $o = $_ | Invoke-CimMethod -MethodName GetOwner } catch { }; [pscustomobject]@{ ProcessId = $_.ProcessId; ParentProcessId = $_.ParentProcessId; User = $(if ($o) { "$($o.Domain)\$($o.User)" } else { '' }); CreationDate = $_.CreationDate.ToUniversalTime().ToString('o'); ExecutablePath = $_.ExecutablePath; CommandLine = $_.CommandLine } } | Format-List }
  Write-LiveFile 'live/network.txt' { if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) { Get-NetTCPConnection | Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort, State, OwningProcess, @{n='Process';e={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName}} | Format-Table -AutoSize } else { netstat.exe -ano } }
  Write-LiveFile 'live/services.txt' { Get-CimInstance Win32_Service | Select-Object Name, State, StartMode, StartName, PathName | Format-Table -AutoSize -Wrap }
  Write-LiveFile 'live/scheduled-tasks.txt' { if (Get-Command Get-ScheduledTask -ErrorAction SilentlyContinue) { Get-ScheduledTask | ForEach-Object { $t = $_; foreach ($a in $t.Actions) { [pscustomobject]@{ TaskPath = $t.TaskPath; TaskName = $t.TaskName; State = $t.State; Author = $t.Author; Execute = $a.Execute; Arguments = $a.Arguments } } } | Format-Table -AutoSize -Wrap } else { schtasks.exe /query /fo LIST /v } }
  foreach ($lf in @('system', 'users', 'logins', 'processes', 'agent-processes', 'network', 'services', 'scheduled-tasks')) { Register-Generated 'live' "live/$lf.txt" }
}

# ---------------------------------------------------------------------------
# Per-user collection
# ---------------------------------------------------------------------------
foreach ($u in $UserList) {
  Write-Log "User $($u.user) ($($u.home))"
  Invoke-CatalogCollection $u.user $u.home $CATALOG
}

# ---------------------------------------------------------------------------
# Project discovery: plain-text sources only, same list as the sh script.
# ---------------------------------------------------------------------------
function ConvertTo-LocalPath([string]$v) {
  $v = $v.Trim()
  if ($v -eq '') { return $null }
  if ($v.StartsWith('file://')) { $v = $v.Substring(7).TrimStart('/'); try { $v = [uri]::UnescapeDataString($v) } catch { } }
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
function Get-JsonValues([string]$key, [string[]]$files) {
  $rx = '"' + [regex]::Escape($key) + '"\s*:\s*"((?:[^"\\]|\\.)*)"'
  foreach ($f in $files) {
    if (-not $f -or -not (Test-PathQuiet $f 'Leaf')) { continue }
    try { foreach ($m in [regex]::Matches([System.IO.File]::ReadAllText($f), $rx)) { $m.Groups[1].Value } } catch { }
  }
}
function Get-JsonKeys([string]$suffix, [string[]]$files) {
  $rx = '"([A-Za-z]:(?:[^"\\]|\\.)*|/(?:[^"\\]|\\.)*)"\s*:\s*' + $suffix
  foreach ($f in $files) {
    if (-not $f -or -not (Test-PathQuiet $f 'Leaf')) { continue }
    try { foreach ($m in [regex]::Matches([System.IO.File]::ReadAllText($f), $rx)) { $m.Groups[1].Value } } catch { }
  }
}
function Find-Projects {
  $found = @()
  foreach ($u in $UserList) {
    $h = $u.home
    $vals = @()
    $vals += Get-JsonValues 'project' @((Join-PathSafe $h '.claude/history.jsonl'))
    $vals += Get-JsonKeys '\{' @((Join-PathSafe $h '.claude.json'))
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
    foreach ($pr in (Expand-Glob $h '.gemini/tmp/*/.project_root')) { try { $vals += [System.IO.File]::ReadAllText($pr) } catch { } }
    foreach ($ws in (@(Expand-Glob $h 'AppData/Roaming/*/User') + @(Expand-Glob $h '.config/*/User') + @(Expand-Glob $h 'Library/Application Support/*/User'))) {
      $vals += Get-JsonValues 'folder' @(Expand-Glob $ws 'workspaceStorage/*/workspace.json')
      $vals += Get-JsonValues 'cwdOnTaskInitialization' (@(Expand-Glob $ws 'globalStorage/saoudrizwan.claude-dev/state/taskHistory.json') + @(Expand-Glob $ws 'globalStorage/saoudrizwan.claude-dev/tasks/*/task_metadata.json'))
      $vals += Get-JsonValues 'workspace' (@(Expand-Glob $ws 'globalStorage/rooveterinaryinc.roo-cline/tasks/_index.json') + @(Expand-Glob $ws 'globalStorage/kilocode.kilo-code/tasks/_index.json'))
    }
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
  foreach ($pj in $ProjectList) {
    Write-Log "Project $(if ($pj.user) { '[' + $pj.user + '] ' })$($pj.path)"
    Invoke-CatalogCollection $pj.user $pj.path $PROJECT_CATALOG
  }
}

# ---------------------------------------------------------------------------
# Summary, archive, hashes
# ---------------------------------------------------------------------------
$EndTs = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$summary = [ordered]@{
  tool = $TOOL; version = $ToolVersion; hostname = $HostName; mode = $Mode
  root = $(if ($Root) { $Root } else { '\' })
  platform = "Windows $([Environment]::OSVersion.Version) $env:PROCESSOR_ARCHITECTURE PowerShell $($PSVersionTable.PSVersion)"
  run_as = $(try { [Security.Principal.WindowsIdentity]::GetCurrent().Name } catch { [Environment]::UserDomainName + '\' + [Environment]::UserName })
  run_as_admin = $IsAdmin
  started = $StartTs; finished = $EndTs
  options = [ordered]@{ full = $Full.IsPresent; no_secrets = $NoSecrets.IsPresent; no_live = [bool]$NoLive; max_file_size_bytes = $MaxSize; users_filter = $Users }
  capabilities = [ordered]@{ hash_tool = 'Get-FileHash'; archiver = $(if ($TarExe) { 'tar.exe' } else { 'ZipFile' }) }
  users = @($UserList | ForEach-Object { $_.user })
  homes = @($UserList | ForEach-Object { $_.home })
  projects = @($ProjectList | ForEach-Object { $_.path })
  counts = [ordered]@{ collected = $script:Counts.collected; symlink = $script:Counts.symlink; skipped_excluded = $script:Counts.skipped_excluded; skipped_size = $script:Counts.skipped_size; skipped_secret = $script:Counts.skipped_secret; error_copy = $script:Counts.error_copy; collected_bytes = $script:Counts.bytes }
  archive = (Split-Path -Leaf $Archive)
}
[System.IO.File]::WriteAllText($SummaryPath, ($summary | ConvertTo-Json -Depth 4), $Utf8NoBom)

Write-Log 'Archiving'
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

if (-not $KeepStaging) { try { Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction Stop } catch { } }

$c = $script:Counts
Write-Output "archive:    $Archive"
Write-Output "size:       $ArchiveSize"
Write-Output "sha256:     $ArchiveSha"
Write-Output "manifest:   $ManifestPath"
Write-Output "summary:    $SummaryPath"
Write-Output "log:        $LogPath"
Write-Output "users:      $($UserList.Count)"
Write-Output "projects:   $($ProjectList.Count)"
Write-Output "collected:  $($c.collected) files, $($c.bytes) bytes"
Write-Output "skipped:    $($c.skipped_excluded) excluded, $($c.skipped_size) too large, $($c.skipped_secret) secret"
Write-Output "errors:     $($c.error_copy)"
exit 0
