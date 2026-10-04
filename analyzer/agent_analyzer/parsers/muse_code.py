"""Muse Code (Meta) session logs.

Closed source. Validated against the shipped Linux binary 1.4.2-R4684.1
(serde field names from `strings`), the vendor skills unpacked beside it
(`read-session/SKILL.md`, `doctor/scripts/session-evidence.py`) and a real
install on Linux, October 2026, with a synthetic fixture; see
`research/muse-code.md`. Files, relative to the home (the same layout on
macOS and Windows, which resolve `XDG_DATA_HOME` or the home):

* `.local/share/muse/sessions/YYYY/MM/DD/<session id>/session.jsonl` and
  `.../<session id>/subagent/<child id>/session.jsonl` (one log per
  subagent, same format). One JSON object per line, three shapes:
  - envelope: `stream.id` (session id, or the subagent's own id),
    `recorded_at` (integer microseconds since the epoch, UTC),
    `payload_type`, `payload`.
  - `retained_frame`: `children[].child_index`, `children[].record_json`
    (a JSON string holding a whole envelope; the observed children are
    permission records, which give no rows).
  - `retained_marker`: a placeholder for a live-only record; skipped.
  A file whose first parseable record is neither an envelope nor a frame
  is not Muse and gives no rows.
* `payload_type: "runtime.session"`, `payload.kind: "run"`, `payload.run_id`,
  `payload.event.kind`:
  - `started` (`prompt`): `user` in a top-level log, `system` in a
    subagent log (the task the runtime gave the child).
  - `inbox_item_queued` (`source.source`, `payload.prompt`, `body`,
    `summary`): `user` when the source is `user_steer`, else `system`.
  - `assistant_message_committed` (`text`): `assistant`.
  - `reasoning_summary_committed` (`message_id`, `text`) and
    `reasoning_committed` with non-empty `text`: `thinking`, only with
    `include_thinking`. `reasoning_summary_delta` (`message_id`, `text`)
    repeats the committed record and is skipped, unless its `message_id`
    has no committed record (a cut log): then the deltas joined by a blank
    line give one `thinking` row at the last delta.
  - `assistant_tool_calls_committed` (`tool_calls[].name`, `.call_id`,
    `.args`, a JSON string or an object): one `tool_use` each.
  - `tool_result_batch_committed` (`results[].tool_call_id`, `.text`), and
    the alternative names `tool_results_committed`, `tool_result_committed`
    and `tool_result` (`tool_call_id` or `call_id`; `text`, `output`,
    `result`, `tool_result_model_visible_content` or `content`): one
    `tool_result` each, joined on the call id. A result `text` that decodes
    to an object with `output` (bash) gives that output, prefixed
    `[exit N]` when `exit_code` is non-zero.
  - `provider_tool_call_completed` (`call_id`, `status`, `action`,
    `results`): a `tool_use` and a `tool_result`, not observed on disk.
  - `terminal` (`terminal`, `reason`): a `system` row unless `completed`.
  - `context_compaction_installed`, `run_retracted`, `turn_task_died`:
    `system` rows with the event as compact JSON.
  - `model_completed` (`model`): no row; the run's model when
    `run.model.configured` gave none.
* `payload.kind: "approval"`: `requested` (`tool_name`, `tool_call_id`,
  `raw_args`, `pending_action_id`) and `decision_applied` (`decision`,
  `decision_source.kind`, `pending_action_id`, joined to the request) are
  `system` rows carrying the tool name and call id.
* Fact records, read from `payload.record` then `payload`:
  `runtime.session.metadata` (`workspace_root`, `model_id`),
  `runtime.session.route_facts` (`cwd`, the project fallback),
  `session.workspace_branch.observed` (`reference.kind`, `reference.name`),
  `run.model.configured` (`model_id`, `run_stream.id` = the run id) fill
  columns and give no row. `session.name.changed` (`new_name`) and
  `runtime.model_reconfigure.completed` (`effective.model_id`) are
  `system` rows. `runtime.user_intent.accepted` (`intent_id`,
  `model_messages[].content[].text`) repeats the run's `started` prompt
  and is used only when that run has no `started` record.
  `user_shell.command` (`command_id`, `command_text`) and
  `user_shell.result` (`command_id`, `visible_output`, `exit_code`,
  `terminal_state`) are a `tool_use` and `tool_result` named `user_shell`;
  `subagent.control.spawn_accepted` and `.start_attested` are `system`
  rows of compact JSON. These three are binary field names only, not
  observed. Task, effect, telemetry and every unknown type are skipped.
* A subagent log records no workspace: its project path and branch come
  from the parent `session.jsonl` above its `subagent/` directory, read up
  to `PARENT_SCAN_LINES` lines.
* `.local/share/muse/tui-history.jsonl`: two lines per prompt, a JSON
  string (the text) then `{project, session}`. No timestamp.

Not read: `approval-review/*.jsonl` (the automated reviewer's log, on a
synthetic clock), `tool-outputs/`, `cli-*.log`, `.msp-view-v1/`, the
SQLite stores.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from pathlib import Path

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, iter_jsonl
from .pi import error_row

SESSION_RX = re.compile(
    r"^\.local/share/muse/sessions/\d{4}/\d{2}/\d{2}/[^/]+/(?:subagent/[^/]+/)*session\.jsonl$"
)
HISTORY_REL = ".local/share/muse/tui-history.jsonl"
PARENT_SCAN_LINES = 2000

ARG_KEYS = (
    "command",
    "cmd",
    "url",
    "query",
    "path",
    "file_path",
    "target_path",
    "target",
    "filename",
)
RESULT_KEYS = ("text", "output", "result", "tool_result_model_visible_content", "content")
RESULT_EVENTS = ("tool_result_batch_committed", "tool_results_committed", "tool_result_committed")
LOGGED_EVENTS = ("context_compaction_installed", "run_retracted", "turn_task_died")
SUBAGENT_CONTROL = ("subagent.control.spawn_accepted", "subagent.control.start_attested")


def _dict(v) -> dict:
    return v if isinstance(v, dict) else {}


def _str(v) -> str:
    if v is None:
        return ""
    return v if isinstance(v, str) else compact_json(v)


def _fact(payload: dict) -> dict:
    """A fact record's fields: `payload.record`, falling back to `payload`."""
    rec = payload.get("record")
    return rec if isinstance(rec, dict) else payload


def micros_to_utc(value) -> str:
    """`recorded_at` is microseconds; `to_utc` reads large numbers as ms."""
    if isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)):
        return to_utc(value / 1_000_000)
    if isinstance(value, str) and value.isdigit():
        return to_utc(int(value) / 1_000_000)
    return ""


def args_summary(args) -> str:
    if isinstance(args, str):
        try:
            decoded = json.loads(args)
        except ValueError:
            return args
        args = decoded
    if isinstance(args, dict):
        for k in ARG_KEYS:
            v = args.get(k)
            if v not in (None, ""):
                return _str(v)
        return compact_json(args)
    return _str(args)


def result_text(text) -> str:
    """A tool result's text; bash results are a JSON object with `output`."""
    if not isinstance(text, str):
        return _str(text)
    if text.startswith("{"):
        try:
            obj = json.loads(text)
        except ValueError:
            return text
        if isinstance(obj, dict) and "output" in obj:
            out = _str(obj.get("output"))
            code = obj.get("exit_code")
            if code not in (None, 0):
                out = "[exit %s] %s" % (code, out)
            return out
    return text


def records(path, errors: list) -> Iterator[tuple[int, dict]]:
    """(line, envelope) for every envelope, frames unpacked in child order,
    markers dropped. Stops at once when the first record is not Muse."""
    first = True
    for n, rec in iter_jsonl(path, errors):
        if first:
            first = False
            if "retained_frame" not in rec and not ("stream" in rec and "payload_type" in rec):
                return
        if "retained_marker" in rec:
            continue
        if "retained_frame" in rec:
            children = [c for c in rec.get("children") or [] if isinstance(c, dict)]
            children.sort(key=lambda c: c.get("child_index") or 0)
            for c in children:
                try:
                    inner = json.loads(c.get("record_json") or "")
                except (TypeError, ValueError) as e:
                    errors.append((n, "retained_frame child: %s" % e))
                    continue
                if isinstance(inner, dict):
                    yield n, inner
            continue
        yield n, rec


def workspace(recs: Iterable[tuple[int, dict]], limit: int = 0) -> tuple[str, str]:
    """(project path, branch) from a session log's records: the last
    metadata `workspace_root` (else `route_facts` `cwd`) and the last branch
    name. `limit` caps the lines read (0 reads them all)."""
    project = cwd = branch = ""
    for n, rec in recs:
        if limit and n > limit:
            break
        ptype = rec.get("payload_type")
        payload = _dict(rec.get("payload"))
        fact = _fact(payload)
        if ptype == "runtime.session.metadata":
            ws = fact.get("workspace_root") or payload.get("workspace_root")
            if ws:
                project = str(ws)
        elif ptype == "runtime.session.route_facts" and fact.get("cwd"):
            cwd = str(fact.get("cwd"))
        elif ptype == "session.workspace_branch.observed":
            ref = _dict(fact.get("reference"))
            if ref.get("kind") == "branch" and ref.get("name"):
                branch = str(ref.get("name"))
    return project or cwd, branch


class MuseCodeParser(Parser):
    agent = "muse-code"
    name = "muse-code"

    def __init__(self) -> None:
        self._parent_cache: dict[Path, tuple[str, str]] = {}

    def wants(self, artifact: Artifact) -> bool:
        return artifact.rel == HISTORY_REL or bool(SESSION_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if artifact.rel == HISTORY_REL:
            yield from self._parse_history(artifact, opts)
        else:
            yield from self._parse_session(artifact, opts)

    # -- session logs -------------------------------------------------------

    def _parent_workspace(self, artifact: Artifact) -> tuple[str, str]:
        """Project and branch of the nearest ancestor log that has them,
        walking up through `subagent/<id>/` levels. Symlinks are not read."""
        d = artifact.disk_path.parent
        while d.parent.name == "subagent":
            d = d.parent.parent
            log = d / "session.jsonl"
            if log.is_symlink() or not log.is_file():
                continue
            if log not in self._parent_cache:
                self._parent_cache[log] = workspace(records(log, []), PARENT_SCAN_LINES)
            found = self._parent_cache[log]
            if found[0]:
                return found
        return "", ""

    def _parse_session(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        recs = list(records(artifact.disk_path, errors))
        if not recs:
            if errors:
                yield error_row(self, artifact, errors)
            return
        is_subagent = "/subagent/" in artifact.rel

        # Pre-pass: values a row may need before the record that sets them.
        run_model: dict[str, str] = {}
        run_completed_model: dict[str, str] = {}
        started_runs: set[str] = set()
        committed_summaries: set[str] = set()
        last_delta: dict[str, int] = {}
        session_model = ""
        for i, (_, rec) in enumerate(recs):
            ptype = rec.get("payload_type")
            payload = _dict(rec.get("payload"))
            fact = _fact(payload)
            if ptype == "run.model.configured":
                rid = _dict(fact.get("run_stream")).get("id")
                if rid and fact.get("model_id"):
                    run_model[str(rid)] = str(fact.get("model_id"))
            elif ptype == "runtime.session.metadata" and fact.get("model_id") and not session_model:
                session_model = str(fact.get("model_id"))
            elif ptype == "runtime.session" and payload.get("kind") == "run":
                ev = _dict(payload.get("event"))
                rid = str(payload.get("run_id") or "")
                kind = ev.get("kind")
                if kind == "started":
                    started_runs.add(rid)
                elif kind == "model_completed" and ev.get("model"):
                    run_completed_model.setdefault(rid, str(ev.get("model")))
                elif kind == "reasoning_summary_committed":
                    committed_summaries.add(str(ev.get("message_id") or ""))
                elif kind == "reasoning_summary_delta":
                    last_delta[str(ev.get("message_id") or "")] = i

        # Defaults for rows before the first metadata record; a subagent log
        # records no workspace of its own and takes its parent's.
        project, branch = workspace(recs)
        if is_subagent and not project:
            project, branch = self._parent_workspace(artifact)
        session_id = ""
        deltas: dict[str, list[str]] = {}
        calls: dict[str, str] = {}
        approvals: dict[str, tuple[str, str]] = {}
        shell_ids: list[str] = []

        for i, (n, rec) in enumerate(recs):
            ptype = rec.get("payload_type")
            payload = _dict(rec.get("payload"))
            fact = _fact(payload)
            sid = _dict(rec.get("stream")).get("id")
            if sid and not session_id:
                session_id = str(sid)
            run_id = str(payload.get("run_id") or "")
            model = run_model.get(run_id) or run_completed_model.get(run_id) or session_model

            def row(
                turn: str,
                text: str,
                tool_name: str = "",
                tool_use_id: str = "",
                n=n,
                rec=rec,
                model=model,
                session_id=session_id,
                project=project,
                branch=branch,
            ) -> Row:
                r = self.base_row(artifact)
                r.source_line = n
                r.timestamp_utc = micros_to_utc(rec.get("recorded_at"))
                r.session_id = session_id
                r.project_path = project
                r.git_branch = branch
                r.model = model
                r.turn_type = turn
                r.tool_name = tool_name
                r.tool_use_id = tool_use_id
                r.text = compact(text, opts.max_text_length)
                return r

            if ptype == "runtime.session.metadata":
                if fact.get("model_id"):
                    session_model = str(fact.get("model_id"))
                ws = fact.get("workspace_root") or payload.get("workspace_root")
                if ws:
                    project = str(ws)
            elif ptype == "session.workspace_branch.observed":
                ref = _dict(fact.get("reference"))
                branch = str(ref.get("name") or "") if ref.get("kind") == "branch" else ""
            elif ptype == "session.name.changed":
                yield row("system", "session name: %s" % _str(fact.get("new_name")))
            elif ptype == "runtime.model_reconfigure.completed":
                m = _str(_dict(fact.get("effective")).get("model_id"))
                if m:
                    session_model = m
                yield row("system", "model: %s" % m, model=m or model)
            elif ptype == "runtime.user_intent.accepted":
                intent = str(payload.get("intent_id") or "")
                if intent and intent not in started_runs:
                    parts = []
                    for msg in payload.get("model_messages") or []:
                        for c in _dict(msg).get("content") or []:
                            t = _dict(c).get("text")
                            if isinstance(t, str):
                                parts.append(t)
                    if parts:
                        yield row(
                            "system" if is_subagent else "user",
                            "\n".join(parts),
                            model=run_model.get(intent) or model,
                        )
            elif ptype == "user_shell.command":
                cid = _str(fact.get("command_id"))
                shell_ids.append(cid)
                yield row("tool_use", _str(fact.get("command_text")), "user_shell", cid)
            elif ptype == "user_shell.result":
                cid = _str(fact.get("command_id")) or (shell_ids[-1] if shell_ids else "")
                out = _str(fact.get("visible_output"))
                notes = []
                if fact.get("exit_code") not in (None, 0):
                    notes.append("exit %s" % fact.get("exit_code"))
                state = fact.get("terminal_state")
                if state and state != "completed":
                    notes.append(str(state))
                if notes:
                    out = "[%s] %s" % (", ".join(notes), out)
                yield row("tool_result", out, "user_shell", cid)
            elif ptype in SUBAGENT_CONTROL:
                yield row("system", "%s: %s" % (ptype, compact_json(fact)))
            elif ptype == "runtime.session":
                kind = payload.get("kind")
                ev = _dict(payload.get("event"))
                if kind == "run":
                    yield from self._run_event(
                        ev,
                        i,
                        row,
                        opts,
                        is_subagent,
                        calls,
                        deltas,
                        committed_summaries,
                        last_delta,
                    )
                elif kind == "approval":
                    ekind = ev.get("kind")
                    if ekind == "requested":
                        tname = _str(ev.get("tool_name"))
                        tid = _str(ev.get("tool_call_id"))
                        approvals[_str(ev.get("pending_action_id"))] = (tname, tid)
                        yield row(
                            "system",
                            "approval requested: %s" % _str(ev.get("raw_args")),
                            tname,
                            tid,
                        )
                    elif ekind == "decision_applied":
                        tname, tid = approvals.get(_str(ev.get("pending_action_id")), ("", ""))
                        src = _str(_dict(ev.get("decision_source")).get("kind"))
                        yield row(
                            "system",
                            "approval %s by %s" % (_str(ev.get("decision")), src),
                            tname,
                            tid,
                        )
            # Task and effect records, telemetry, permission records and
            # unknown payload types are bookkeeping: no row.

        if errors:
            r = error_row(self, artifact, errors, session_id, project)
            r.git_branch = branch
            yield r

    def _run_event(
        self,
        ev: dict,
        i: int,
        row,
        opts: Options,
        is_subagent: bool,
        calls: dict[str, str],
        deltas: dict[str, list[str]],
        committed_summaries: set[str],
        last_delta: dict[str, int],
    ) -> Iterator[Row]:
        kind = ev.get("kind")
        if kind == "started":
            prompt = _str(ev.get("prompt"))
            if is_subagent:
                yield row("system", "subagent task: %s" % prompt)
            else:
                yield row("user", prompt)
        elif kind == "inbox_item_queued":
            src = _str(_dict(ev.get("source")).get("source"))
            text = _str(_dict(ev.get("payload")).get("prompt")) or _str(ev.get("body"))
            if src == "user_steer":
                yield row("user", text)
            else:
                yield row("system", "inbox %s: %s" % (src, text or _str(ev.get("summary"))))
        elif kind == "assistant_message_committed":
            text = _str(ev.get("text"))
            if text:
                yield row("assistant", text)
        elif kind in ("reasoning_summary_committed", "reasoning_committed"):
            # reasoning_committed text was empty in every observed record;
            # its content is the opaque encrypted_content.
            if opts.include_thinking and ev.get("text"):
                yield row("thinking", _str(ev.get("text")))
        elif kind == "reasoning_summary_delta":
            mid = _str(ev.get("message_id"))
            if mid in committed_summaries:
                return
            deltas.setdefault(mid, []).append(_str(ev.get("text")))
            if last_delta.get(mid) == i and opts.include_thinking:
                yield row("thinking", "\n\n".join(t for t in deltas.pop(mid) if t))
        elif kind == "assistant_tool_calls_committed":
            for call in ev.get("tool_calls") or []:
                call = _dict(call)
                name = _str(call.get("name"))
                cid = _str(call.get("call_id"))
                calls[cid] = name
                yield row("tool_use", args_summary(call.get("args")), name, cid)
        elif kind in RESULT_EVENTS or kind == "tool_result":
            results = ev.get("results")
            items = results if isinstance(results, list) else [ev]
            for res in items:
                res = _dict(res)
                cid = _str(res.get("tool_call_id") or res.get("call_id"))
                raw = next((res[k] for k in RESULT_KEYS if res.get(k) is not None), "")
                yield row("tool_result", result_text(raw), calls.get(cid, ""), cid)
        elif kind == "provider_tool_call_completed":
            cid = _str(ev.get("call_id"))
            action = _dict(ev.get("action"))
            name = _str(action.get("type")) or "provider_tool"
            calls[cid] = name
            yield row("tool_use", args_summary(action) if action else "", name, cid)
            text = compact_json(ev.get("results")) if ev.get("results") is not None else ""
            status = _str(ev.get("status"))
            if status and status != "completed":
                text = "[%s] %s" % (status, text)
            yield row("tool_result", text, name, cid)
        elif kind == "terminal":
            term = _str(ev.get("terminal"))
            if term and term != "completed":
                yield row("system", "run %s: %s" % (term, _str(ev.get("reason"))))
        elif kind in LOGGED_EVENTS:
            yield row("system", "%s: %s" % (kind, compact_json(ev)))

    # -- prompt history -----------------------------------------------------

    def _parse_history(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        pending: tuple[int, str] | None = None

        def emit(line: int, text: str, meta: dict) -> Row:
            r = self.base_row(artifact)
            r.source_line = line
            r.turn_type = "user"
            r.session_id = _str(meta.get("session"))
            r.project_path = _str(meta.get("project"))
            r.text = compact(text, opts.max_text_length)
            return r

        with open(artifact.disk_path, "rb") as fh:
            for n, raw in enumerate(fh, 1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw.decode("utf-8", errors="replace"))
                except ValueError as e:
                    errors.append((n, str(e)))
                    continue
                if isinstance(rec, str):
                    if pending is not None:
                        yield emit(pending[0], pending[1], {})
                    pending = (n, rec)
                elif isinstance(rec, dict) and pending is not None:
                    yield emit(pending[0], pending[1], rec)
                    pending = None
        if pending is not None:
            yield emit(pending[0], pending[1], {})
        if errors:
            yield error_row(self, artifact, errors)
