#!/bin/sh
# Copyright 2026 Sean Whalen
# SPDX-License-Identifier: Apache-2.0
#
# Fails if the artifact tables embedded in collect-agent-artifacts.sh and
# Collect-AgentArtifacts.ps1 differ, or if the analyzer's bundled copy of the
# --list output is stale. All three must stay a single source of truth.
HERE=$(cd "$(dirname "$0")" && pwd)
SH="$HERE/../collect-agent-artifacts.sh"
PS="$HERE/../Collect-AgentArtifacts.ps1"
ANALYZER_COPY="$HERE/../../analyzer/agent_analyzer/catalog.txt"
fail=0

sh_table() { # sh_table NAME -> lines of the sh table (blank lines dropped)
  if [ "$1" = SECRET_GLOBS ]; then
    sed -n "/^SECRET_GLOBS='/,/'\$/p" "$SH" | sed "1s/^SECRET_GLOBS='//; \$s/'\$//"
  else
    sed -n "/^$1='\$/,/^'\$/p" "$SH" | sed '1d;$d'
  fi | grep -v '^$'
}
ps_table() { # ps_table NAME -> lines of the PowerShell here-string
  sed -n "/^\$$1 = @'/,/^'@/p" "$PS" | sed '1d;$d' | tr -d '\r' | grep -v '^$'
}

for t in CATALOG PROJECT_CATALOG EXCLUDES SECRET_GLOBS; do
  a=$(sh_table "$t"); b=$(ps_table "$t")
  n=$(printf '%s\n' "$a" | grep -c .)
  if [ "$n" -lt 5 ]; then printf 'FAIL %s: could not extract table from sh (%s lines)\n' "$t" "$n"; fail=1; continue; fi
  if [ "$a" = "$b" ]; then
    printf 'ok   %s (%s lines)\n' "$t" "$n"
  else
    printf 'FAIL %s differs:\n' "$t"; fail=1
    printf '%s\n' "$a" >"${TMPDIR:-/tmp}/cac-sync-sh.$$"; printf '%s\n' "$b" >"${TMPDIR:-/tmp}/cac-sync-ps.$$"
    diff "${TMPDIR:-/tmp}/cac-sync-sh.$$" "${TMPDIR:-/tmp}/cac-sync-ps.$$" | head -20
    rm -f "${TMPDIR:-/tmp}/cac-sync-sh.$$" "${TMPDIR:-/tmp}/cac-sync-ps.$$"
  fi
done

# The --list / -List outputs must also match when a PowerShell is available.
PWSH=
if command -v pwsh >/dev/null 2>&1; then PWSH=pwsh; fi
if [ -n "$PWSH" ]; then
  if [ "$("$SH" --list)" = "$($PWSH -NoProfile -File "$PS" -List | tr -d '\r')" ]; then printf 'ok   --list output identical under %s\n' "$PWSH"
  else printf 'FAIL --list output differs under %s\n' "$PWSH"; fail=1; fi
fi

# The analyzer detects agents with a verbatim copy of the --list output.
if [ -f "$ANALYZER_COPY" ]; then
  if [ "$("$SH" --list)" = "$(cat "$ANALYZER_COPY")" ]; then printf 'ok   analyzer catalog.txt matches --list\n'
  else
    printf 'FAIL analyzer catalog.txt is stale; run: collectors/collect-agent-artifacts.sh --list > analyzer/agent_analyzer/catalog.txt\n'; fail=1
  fi
fi

[ "$fail" = 0 ] && echo "CATALOGS IN SYNC"
exit $fail
