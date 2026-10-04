"""Open Interpreter transcripts.

The current Open Interpreter is a Rust fork of Codex CLI that keeps Codex's
rollout format and moves the home to `~/.openinterpreter`; checked against
openinterpreter/openinterpreter at 2767e5f (see
`research/open-interpreter.md`). Rollouts and history are read by the shared
`RolloutParser` in `codex.py`, so the field names listed there apply. Files:

* `.openinterpreter/sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl`
  and the same under `.openinterpreter/archived_sessions/`, plain or
  `.jsonl.zst` (`rollout/src/lib.rs:84-85`, `rollout/src/compression.rs:25`).
  `session_meta.originator` is still `codex_cli_rs` in the fork, so only the
  file's location tells it from Codex. Tool names follow the emulated
  harness (`Bash`, `Read` under the claude-code harness), not the Codex set.
* `.openinterpreter/history.jsonl`: `{session_id, ts, text}`.
* `.openinterpreter/external_agent_session_imports.json`: the `/import`
  ledger, `records[]` with `source_path`, `content_sha256`,
  `imported_thread_id`, `imported_at` and optional `source_modified_at`
  (epoch seconds; `external-agent-sessions/src/ledger.rs:18-30`). Each
  record becomes one `system` row with the imported thread's id as
  `session_id`, so the analyst can see that the turns of that rollout were
  authored in another agent (Claude Code or Cursor) and that their record
  timestamps are import time.

Not parsed: `session_index.jsonl` (thread renames) and the zcode harness's
oversized tool results under `.zcode/cli/artifacts/`.
"""
from __future__ import annotations

from .codex import RolloutParser


class OpenInterpreterParser(RolloutParser):
    agent = "open-interpreter"
    name = "open-interpreter"
    home_prefix = ".openinterpreter"
    ledger_name = "external_agent_session_imports.json"
