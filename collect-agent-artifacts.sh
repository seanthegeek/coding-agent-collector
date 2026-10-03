#!/bin/sh
# collect-agent-artifacts.sh - forensic collector for AI coding agent artifacts
#
# Copyright 2026 Sean Whalen
# SPDX-License-Identifier: Apache-2.0
# Licensed under the Apache License, Version 2.0; see the LICENSE file.
#
# Collects the on-disk state of AI coding agents (Claude Code, Gemini CLI,
# Antigravity, Codex CLI, Copilot CLI, Cursor, Windsurf, Continue, Aider,
# Ollama, ...) for every user on a host, plus shell histories and a live
# system snapshot, into a single tar.gz with a JSONL manifest.
#
# Portability: POSIX sh only. Runs under bash 3.2 (macOS /bin/sh), dash,
# ash/busybox, FreeBSD/OpenBSD sh and zsh in sh emulation. External tools used:
# find, cp, tar, gzip, du, awk, grep, sed, sort, cut, readlink, mkdir, rm,
# and one of sha256sum / shasum / sha256 / openssl.
#
# Modes:
#   live   (default)   collect from the running system
#   image  (-r ROOT)   collect from a mounted disk image / alternate root
#
# Exit codes: 0 archive written (per-file errors are recorded in the manifest),
#             1 usage error, 2 fatal (no output dir, no tar, ...).

VERSION="1.0.0"
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
claude-code|.claude
claude-code|.claude.json*
claude-desktop|Library/Application Support/Claude
claude-desktop|.config/Claude
claude-desktop|AppData/Roaming/Claude
gemini-cli|.gemini
antigravity|.antigravity
antigravity|.cache/antigravity
antigravity|.config/Antigravity/User
antigravity|.config/Antigravity/logs
antigravity|Library/Application Support/Antigravity/User
antigravity|Library/Application Support/Antigravity/logs
antigravity|AppData/Roaming/Antigravity/User
antigravity|AppData/Roaming/Antigravity/logs
codex-cli|.codex
copilot-cli|.copilot
cursor|.cursor
cursor|Library/Application Support/Cursor/User
cursor|Library/Application Support/Cursor/logs
cursor|.config/Cursor/User
cursor|.config/Cursor/logs
cursor|AppData/Roaming/Cursor/User
cursor|AppData/Roaming/Cursor/logs
vscode|.vscode*/extensions/extensions.json
vscode|Library/Application Support/Code*/User
vscode|Library/Application Support/Code*/logs
vscode|.config/Code*/User
vscode|.config/Code*/logs
vscode|AppData/Roaming/Code*/User
vscode|AppData/Roaming/Code*/logs
vscode|.config/VSCodium/User
vscode|Library/Application Support/VSCodium/User
vscode|AppData/Roaming/VSCodium/User
windsurf|.codeium
windsurf|Library/Application Support/Windsurf/User
windsurf|.config/Windsurf/User
windsurf|AppData/Roaming/Windsurf/User
continue|.continue
aider|.aider*
opencode|.config/opencode
opencode|.local/share/opencode
amp|.config/amp
amp|.local/share/amp
goose|.config/goose
goose|.local/share/goose
zed|.config/zed
zed|.local/share/zed
zed|Library/Application Support/Zed
qwen-code|.qwen
kiro|.kiro
cline|.cline
augment|.augment
factory-droid|.factory
crush|.config/crush
crush|.local/share/crush
ollama|.ollama
chatgpt-desktop|Library/Application Support/com.openai.chat
chatgpt-desktop|AppData/Local/Packages/OpenAI.ChatGPT-Desktop_*/LocalCache
shell-history|.bash_history
shell-history|.zsh_history
shell-history|.zsh_sessions
shell-history|.sh_history
shell-history|.history
shell-history|.local/share/fish/fish_history
shell-history|.config/fish/fish_history
shell-history|AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt
'

# Project-level artifacts, relative to each discovered project directory.
PROJECT_CATALOG='
project|.claude
project|CLAUDE.md
project|CLAUDE.local.md
project|.mcp.json
project|AGENTS.md
project|GEMINI.md
project|.gemini
project|.codex
project|.cursor
project|.cursorrules
project|.windsurfrules
project|.windsurf
project|.aider*
project|.github/copilot-instructions.md
project|.roo
project|.clinerules
project|.kiro
project|.continue
project|.vscode/mcp.json
'

# Paths (globs relative to home or project dir) skipped unless --full. They are
# recorded in the manifest as skipped_excluded with their size. find(1) -path
# semantics: * also matches /.
EXCLUDES='
.claude/cache
.claude/plugins/marketplaces
.claude/plugins/*/node_modules
.claude/worktrees
.gemini/antigravity-cli/bin
.codex/packages
.codex/cache
.codex/.tmp/plugins
.antigravity/extensions
.cursor/extensions
.codeium/*/bin
.codeium/bin
.continue/index
.aider/caches
.aider.tags.cache*
.ollama/models
.local/share/zed/extensions
.local/share/zed/node
.local/share/zed/languages
.local/share/zed/copilot
Library/Application Support/Zed/extensions
Library/Application Support/Zed/node
Library/Application Support/Zed/languages
Library/Application Support/Zed/copilot
.local/share/opencode/bin
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
'

# Files holding credentials. Collected by default and flagged secret=true in
# the manifest; skipped with --no-secrets.
SECRET_GLOBS='.claude/.credentials.json
.gemini/oauth_creds.json
.gemini/antigravity-cli/antigravity-oauth-token
.codex/auth.json
.ollama/id_ed25519
.config/amp/secrets.json
.copilot/auth*.json
.continue/auth*.json'

AGENT_PROC_RE='claude|gemini|antigravity|codex|copilot|cursor|windsurf|codeium|ollama|aider|opencode|[/ ]amp( |$)|goose|continue|[/ ]zed( |$)|qwen|kiro|cline|augment|droid|crush'

# ---------------------------------------------------------------------------
# Shared helper functions. Defined as a string so they can be eval'd here and
# prepended to the programs run by find -exec sh -c (which cannot inherit
# shell functions portably).
# ---------------------------------------------------------------------------
COMMON=$(cat <<'EOF_COMMON'
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
)
eval "$COMMON"

# Program run by find -exec for every regular file / symlink to collect.
# args: stage root user home agent manifest files...
STAGE_PROG="$COMMON
$(cat <<'EOF_STAGE'
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
)"

# Program run by find -exec for every pruned (excluded) path.
# args: root user home agent manifest paths...
SKIP_PROG="$COMMON
$(cat <<'EOF_SKIP'
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
)"

# ---------------------------------------------------------------------------
usage() {
  cat <<EOF
Usage: $0 [options]

  -o, --output DIR        Directory for the archive (default: current dir)
  -r, --root DIR          Alternate root, e.g. a mounted disk image (image mode;
                          disables the live snapshot)
  -u, --users LIST        Comma-separated usernames to collect (default: all)
  -p, --project DIR       Extra project directory to collect (repeatable)
      --full              Disable default size exclusions (model blobs, caches,
                          extension binaries)
      --no-secrets        Skip credential files instead of collecting them
      --no-live           Skip the live system snapshot
      --no-projects       Skip project-level artifact discovery
      --max-file-size MB  Skip files larger than this (default 256, 0 = none)
  -k, --keep-staging      Keep the staging directory after archiving
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
NO_LIVE=0
NO_PROJECTS=0
MAX_MB=256
KEEP=0
QUIET=0
LIST=0

while [ $# -gt 0 ]; do
  case "$1" in
    -o|--output)        [ $# -ge 2 ] || { usage >&2; exit 1; }; OUTDIR=$2; shift ;;
    -r|--root)          [ $# -ge 2 ] || { usage >&2; exit 1; }; ROOT=$2; shift ;;
    -u|--users)         [ $# -ge 2 ] || { usage >&2; exit 1; }; USERS=$2; shift ;;
    -p|--project)       [ $# -ge 2 ] || { usage >&2; exit 1; }; EXTRA_PROJECTS="$EXTRA_PROJECTS
$2"; shift ;;
    --full)             FULL=1 ;;
    --no-secrets)       NO_SECRETS=1 ;;
    --no-live)          NO_LIVE=1 ;;
    --no-projects)      NO_PROJECTS=1 ;;
    --max-file-size)    [ $# -ge 2 ] || { usage >&2; exit 1; }; MAX_MB=$2; shift ;;
    -k|--keep-staging)  KEEP=1 ;;
    --list)             LIST=1 ;;
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
[ -n "$ROOT" ] && { MODE=image; NO_LIVE=1; }

[ -d "$OUTDIR" ] || mkdir -p "$OUTDIR" 2>/dev/null || { printf 'Cannot create output dir: %s\n' "$OUTDIR" >&2; exit 2; }
OUTDIR=$(cd "$OUTDIR" && pwd) || exit 2
[ -w "$OUTDIR" ] || { printf 'Output dir not writable: %s\n' "$OUTDIR" >&2; exit 2; }
command -v tar >/dev/null 2>&1 || { printf 'tar not found\n' >&2; exit 2; }
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

export HASH_TOOL STAT_MODE MAX_SIZE SECRET_GLOBS NO_SECRETS LOG QUIET

cleanup() {
  if [ "$KEEP" != 1 ] && [ -n "$STAGE" ] && [ -d "$STAGE" ]; then
    rm -rf "$STAGE"
  fi
}
trap 'cleanup' EXIT
trap 'log_line "interrupted"; cleanup; trap - EXIT; exit 130' INT TERM

mkdir -p "$STAGE/fs" || { printf 'Cannot create staging dir\n' >&2; exit 2; }
: >"$LOG"; : >"$MANIFEST"

[ "$FULL" = 1 ] && ACTIVE_EXCLUDES= || ACTIVE_EXCLUDES=$EXCLUDES

log_line "$TOOL $VERSION starting on $HOST ($(uname -s 2>/dev/null) $(uname -r 2>/dev/null)) mode=$MODE root=${ROOT:-/} uid=$(id -u 2>/dev/null)"
log_line "hash=$HASH_TOOL stat=$STAT_MODE max_file_size=${MAX_MB}MB full=$FULL no_secrets=$NO_SECRETS worker_sh=$WORKER_SH"
if [ "$MODE" = live ] && [ "$(id -u 2>/dev/null)" != 0 ]; then
  log_line "WARNING: not running as root; other users' homes will probably be unreadable"
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
collect_path() {
  _cp_user=$1; _cp_home=$2; _cp_agent=$3; _cp_m=$4
  if [ -d "$_cp_m" ] && [ ! -L "$_cp_m" ]; then
    set -- "$_cp_m"
    _cp_first=1
    _cp_ifs=$IFS
    IFS='
'
    for _cp_e in $ACTIVE_EXCLUDES; do
      [ -n "$_cp_e" ] || continue
      if [ "$_cp_first" = 1 ]; then set -- "$@" '(' -path "$_cp_home/$_cp_e"; _cp_first=0
      else set -- "$@" -o -path "$_cp_home/$_cp_e"; fi
    done
    IFS=$_cp_ifs
    if [ "$_cp_first" = 0 ]; then
      set -- "$@" ')' -prune -exec "$WORKER_SH" -c "$SKIP_PROG" sh "$ROOT" "$_cp_user" "$_cp_home" "$_cp_agent" "$MANIFEST" '{}' + -o
    fi
    set -- "$@" '(' -type f -o -type l ')' -exec "$WORKER_SH" -c "$STAGE_PROG" sh "$STAGE" "$ROOT" "$_cp_user" "$_cp_home" "$_cp_agent" "$MANIFEST" '{}' +
    find "$@" 2>>"$LOG"
  else
    "$WORKER_SH" -c "$STAGE_PROG" sh "$STAGE" "$ROOT" "$_cp_user" "$_cp_home" "$_cp_agent" "$MANIFEST" "$_cp_m"
  fi
}

# collect_tree USER BASE CATALOG
collect_tree() {
  printf '%s\n' "$3" | while IFS='|' read -r _ct_agent _ct_pat; do
    case "$_ct_agent" in ''|'#'*) continue ;; esac
    expand_glob "$2" "$_ct_pat" | while IFS= read -r _ct_m; do
      log_line "  [$_ct_agent] $_ct_m"
      collect_path "$1" "$2" "$_ct_agent" "$_ct_m" </dev/null
    done
  done
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
# Live snapshot
record_generated() { # record_generated AGENT RELPATH
  _rg_agent=$1; _rg_rel=$2; _rg_f="$STAGE/$2"
  [ -s "$_rg_f" ] || { rm -f "$_rg_f"; return; }
  _rg_st=$(stat_file "$_rg_f"); [ -n "$_rg_st" ] || _rg_st='0 0 0 0 0 0 0 0'
  _rg_secret=false; case "$_rg_rel" in live/environ/*) _rg_secret=true ;; esac
  # shellcheck disable=SC2086
  set -- $_rg_st
  emit_row "$MANIFEST" "" "" "$_rg_agent" "" "$_rg_rel" file "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$(hash_file "$_rg_f")" "$_rg_secret" collected "" ""
}
live_cmd() { # live_cmd RELPATH CMD...
  _lc_rel=$1; shift
  { printf '# %s\n' "$*"; "$@" 2>&1; } >>"$STAGE/$_lc_rel"
}

if [ "$NO_LIVE" != 1 ]; then
  log_line "Live snapshot"
  mkdir -p "$STAGE/live"
  live_cmd live/system.txt hostname
  live_cmd live/system.txt uname -a
  live_cmd live/system.txt date -u
  live_cmd live/system.txt uptime
  live_cmd live/system.txt id
  live_cmd live/system.txt mount
  live_cmd live/system.txt df -k
  [ -f /etc/os-release ] && live_cmd live/system.txt cat /etc/os-release
  command -v sw_vers >/dev/null 2>&1 && live_cmd live/system.txt sw_vers
  if command -v getent >/dev/null 2>&1; then live_cmd live/users.txt getent passwd; else live_cmd live/users.txt cat /etc/passwd; fi
  command -v dscl >/dev/null 2>&1 && live_cmd live/users.txt dscl . -list /Users NFSHomeDirectory
  live_cmd live/logins.txt who
  live_cmd live/logins.txt last -n 50
  if ! ps -axo pid,ppid,user,lstart,etime,args >>"$STAGE/live/processes.txt" 2>/dev/null; then
    ps -eo pid,ppid,user,etime,args >>"$STAGE/live/processes.txt" 2>/dev/null || ps aux >>"$STAGE/live/processes.txt" 2>/dev/null || ps >>"$STAGE/live/processes.txt" 2>&1
  fi
  grep -iE "$AGENT_PROC_RE" "$STAGE/live/processes.txt" | grep -v "$TOOL" >"$STAGE/live/agent-processes.txt" 2>/dev/null
  if [ -d /proc ] && [ "$NO_SECRETS" != 1 ]; then
    for _pid in $(awk 'NR>0 && $1 ~ /^[0-9]+$/ {print $1}' "$STAGE/live/agent-processes.txt"); do
      if [ -r "/proc/$_pid/environ" ]; then
        mkdir -p "$STAGE/live/environ"
        tr '\0' '\n' <"/proc/$_pid/environ" >"$STAGE/live/environ/$_pid.txt" 2>/dev/null
        readlink "/proc/$_pid/cwd" >>"$STAGE/live/environ/$_pid.txt" 2>/dev/null
      fi
    done
  fi
  if command -v ss >/dev/null 2>&1; then live_cmd live/network.txt ss -tunap
  elif command -v netstat >/dev/null 2>&1; then netstat -anp >>"$STAGE/live/network.txt" 2>/dev/null || live_cmd live/network.txt netstat -an; fi
  command -v launchctl >/dev/null 2>&1 && live_cmd live/services.txt launchctl list
  command -v systemctl >/dev/null 2>&1 && live_cmd live/services.txt systemctl list-units --type=service --all --no-pager
  for _lf in system users logins processes agent-processes network services; do record_generated live "live/$_lf.txt"; done
  for _ef in "$STAGE"/live/environ/*.txt; do [ -f "$_ef" ] && record_generated live "live/environ/${_ef##*/}"; done
fi

# ---------------------------------------------------------------------------
# Per-user collection
printf '%s\n' "$USER_LIST" | while IFS=: read -r _u _h; do
  [ -n "$_h" ] || continue
  log_line "User $_u ($_h)"
  collect_tree "$_u" "$_h" "$CATALOG"
done

# ---------------------------------------------------------------------------
# Project discovery: paths referenced by agent state files, prefixed with ROOT.
# Emits "user:path"; the user is whoever's state referenced the path.
discover_projects() {
  printf '%s\n' "$USER_LIST" | while IFS=: read -r _u _h; do
    [ -n "$_h" ] || continue
    {
      [ -f "$_h/.claude/history.jsonl" ] && grep -o '"project":"[^"]*"' "$_h/.claude/history.jsonl" 2>/dev/null | sed 's/^"project":"//; s/"$//'
      [ -f "$_h/.claude.json" ] && grep -o '"/[^"]*": *{' "$_h/.claude.json" 2>/dev/null | sed 's/^"//; s/": *{$//'
      [ -d "$_h/.codex/sessions" ] && find "$_h/.codex/sessions" -name '*.jsonl' -exec grep -ho '"cwd":"[^"]*"' {} + 2>/dev/null | sed 's/^"cwd":"//; s/"$//'
      for _ws in "$_h"/Library/Application\ Support/*/User/workspaceStorage "$_h"/.config/*/User/workspaceStorage "$_h"/AppData/Roaming/*/User/workspaceStorage; do
        [ -d "$_ws" ] || continue
        find "$_ws" -name workspace.json -exec grep -ho '"folder": *"file://[^"]*"' {} + 2>/dev/null | sed 's/^"folder": *"file:\/\///; s/"$//; s/%20/ /g'
      done
    } | grep '^/' | sed 's/\\\//\//g' | awk -v r="$ROOT" -v u="$_u" '{print u":"r$0}'
  done
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
$USER_LIST" in *":$_p
"*|*":$_p") continue ;; esac
    printf '%s\n' "$_line"
  done)
  printf '%s\n' "$PROJECT_LIST" | while IFS= read -r _line; do
    [ -n "$_line" ] || continue
    _owner=${_line%%:*}; _p=${_line#*:}
    log_line "Project ${_owner:+[$_owner] }$_p"
    collect_tree "$_owner" "$_p" "$PROJECT_CATALOG"
  done
fi

# ---------------------------------------------------------------------------
# Summary, archive, hashes
END_TS=$(ts)
count_status() { num "$(grep -c "\"status\":\"$1\"" "$MANIFEST" 2>/dev/null)"; }
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
  "options": {"full": $( [ "$FULL" = 1 ] && printf true || printf false ), "no_secrets": $( [ "$NO_SECRETS" = 1 ] && printf true || printf false ), "no_live": $( [ "$NO_LIVE" = 1 ] && printf true || printf false ), "max_file_size_bytes": $MAX_SIZE, "users_filter": "$(json_str "$USERS")"},
  "capabilities": {"hash_tool": "$HASH_TOOL", "stat_mode": "$STAT_MODE", "worker_shell": "$(json_str "$WORKER_SH")"},
  "users": $(json_list "$(printf '%s\n' "$USER_LIST" | cut -d: -f1)"),
  "homes": $(json_list "$(printf '%s\n' "$USER_LIST" | sed 's/^[^:]*://')"),
  "projects": $(json_list "$(printf '%s\n' "$PROJECT_LIST" | sed 's/^[^:]*://')"),
  "counts": {"collected": $(count_status collected), "symlink": $(count_status symlink), "skipped_excluded": $(count_status skipped_excluded), "skipped_size": $(count_status skipped_size), "skipped_secret": $(count_status skipped_secret), "error_copy": $(count_status error_copy), "collected_bytes": $BYTES},
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
log_line "done: $ARCHIVE ($ARCHIVE_SIZE bytes, sha256 $ARCHIVE_SHA)"

printf 'archive:    %s\nsize:       %s\nsha256:     %s\nmanifest:   %s\nsummary:    %s\nlog:        %s\nusers:      %s\nprojects:   %s\ncollected:  %s files, %s bytes\nskipped:    %s excluded, %s too large, %s secret\nerrors:     %s\n' \
  "$ARCHIVE" "$ARCHIVE_SIZE" "$ARCHIVE_SHA" "$MANIFEST" "$SUMMARY" "$LOG" \
  "$(printf '%s\n' "$USER_LIST" | grep -c .)" "$(printf '%s\n' "$PROJECT_LIST" | grep -c .)" \
  "$(count_status collected)" "$BYTES" "$(count_status skipped_excluded)" "$(count_status skipped_size)" "$(count_status skipped_secret)" "$(count_status error_copy)"
exit 0
