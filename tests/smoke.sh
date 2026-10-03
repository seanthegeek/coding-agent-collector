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
  "$ROOT/home/ollama/.ollama/models/blobs" "$ROOT/nonexistent"
cat >"$ROOT/etc/passwd" <<EOF
root:x:0:0:root:/root:/bin/sh
alice:x:1000:1000:Alice:/home/alice:/bin/bash
ollama:x:999:999::/home/ollama:/usr/sbin/nologin
nobody:x:65534:65534::/nonexistent:/usr/sbin/nologin
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

run() { # run NAME ARGS...
  _n=$1; shift
  mkdir -p "$OUT/$_n"
  COLLECTOR_SH="$SHELL_UNDER_TEST" "$SHELL_UNDER_TEST" "$SCRIPT" -r "$ROOT" -o "$OUT/$_n" -q --max-file-size 1 "$@" >"$OUT/$_n.stdout" 2>"$OUT/$_n.stderr"
  _rc=$?
  M=$(ls "$OUT/$_n"/*.manifest.jsonl 2>/dev/null)
  A=$(ls "$OUT/$_n"/*.tar.gz 2>/dev/null)
  S=$(ls "$OUT/$_n"/*.collection.json 2>/dev/null)
  return $_rc
}
row() { grep -F "\"path\":\"$1\"" "$M" | head -n1; }
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
check "shell history collected" "[ \"\$(status_of \"$ROOT/home/alice/.bash_history\")\" = collected ]"
check "no live dir in image mode" "! tar -tzf \"\$A\" | grep -q '^./live/'"
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

# ---- --list ---------------------------------------------------------------
check "--list prints catalog" "\"$SHELL_UNDER_TEST\" \"$SCRIPT\" --list | grep -q '^claude-code|.claude$'"

if [ "$fail" = 0 ]; then printf 'ALL PASSED (%s)\n' "$SHELL_UNDER_TEST"; rm -rf "$WORK"; else printf 'FAILURES (%s); work dir kept: %s\n' "$SHELL_UNDER_TEST" "$WORK"; fi
exit $fail
