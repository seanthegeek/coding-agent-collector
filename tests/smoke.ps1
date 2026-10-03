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
Mk 'home/bob/.bash_history' 'export FOO=1'
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
$r = Row 'Users/alice/.claude/cache'
Check 'cache dir skipped_excluded with size' { $r -and $r.type -eq 'dir' -and $r.size -gt 0 -and $r.status -eq 'skipped_excluded' }
Check 'cache contents not collected' { $null -eq (Row 'cache/junk.bin') }
Check 'antigravity bin excluded' { (StatusOf 'antigravity-cli/bin') -eq 'skipped_excluded' }
Check 'codex packages excluded' { (StatusOf 'Users/alice/.codex/packages') -eq 'skipped_excluded' }
Check 'ollama models excluded' { (StatusOf 'home/bob/.ollama/models') -eq 'skipped_excluded' }
Check 'ollama history collected (linux-style home in same image)' { (StatusOf 'home/bob/.ollama/history') -eq 'collected' }
Check 'bash history collected' { (StatusOf 'home/bob/.bash_history') -eq 'collected' }
Check 'PSReadLine history collected' { (StatusOf 'PSReadLine/ConsoleHost_history.txt') -eq 'collected' }
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
Check 'home .env flagged secret' { (Row 'Users/alice/.env').secret -eq $true }
Check 'claude desktop config.json flagged secret' { (Row 'Roaming/Claude/config.json').secret -eq $true }
$r = Row 'Claude/claude_desktop_config.json'
Check 'claude desktop mcp config collected unflagged' { $r -and $r.secret -eq $false -and $r.status -eq 'collected' }
Check 'claude desktop Cache excluded' { (StatusOf 'Roaming/Claude/Cache') -eq 'skipped_excluded' }
Check 'Public profile skipped' { $null -eq (Row 'Public/Desktop/readme.txt') }
Check 'Default profile skipped' { $null -eq (Row 'Default/NTUSER.DAT') }
$entries = ArchiveEntries
Check 'no live dir in image mode' { -not ($entries | Where-Object { $_ -match '(^|/)live/' }) }
Check 'manifest and summary inside archive' { ($entries | Where-Object { $_ -match 'manifest\.jsonl$' }) -and ($entries | Where-Object { $_ -match 'collection\.json$' }) }
Check 'archive layout is fs/<path relative to root>' { @($entries | Where-Object { $_ -match '(^|\./)fs/Users/alice/\.claude/history\.jsonl$' }).Count -eq 1 }
Check 'staging removed' { -not (Get-ChildItem -LiteralPath (Join-Path $Out 'default') -Filter '.stage-*' -Force) }
$sum = Get-Content -LiteralPath $script:S.FullName -Raw | ConvertFrom-Json
Check 'summary is valid JSON with zero copy errors' { $sum.counts.error_copy -eq 0 }
Check 'summary counts match manifest' { $sum.counts.collected -eq @($script:Rows | Where-Object { $_.status -eq 'collected' }).Count }
Check 'manifest rows all parsed as JSON' { $script:Rows.Count -eq @(Get-Content -LiteralPath $script:M.FullName).Count }

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

# ---- -List ----------------------------------------------------------------
Check '-List prints catalog' { @(& $Collector -List | Select-String -SimpleMatch 'claude-code|.claude').Count -ge 1 }

if ($script:fail -eq 0) { Write-Output "ALL PASSED ($($PSVersionTable.PSEdition) $($PSVersionTable.PSVersion))"; Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue }
else { Write-Output "FAILURES; work dir kept: $Work" }
exit $script:fail
