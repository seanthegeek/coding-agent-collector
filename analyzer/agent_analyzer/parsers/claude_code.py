"""Claude Code transcripts.

Validated against a real install (Claude Code 2.1.286 to 2.1.289, October
2026) and the shipped 2.1.289 package; the evidence is in
`analyzer/research/claude-code.md`. Files:

* `~/.claude/projects/<slug>/<session>.jsonl`: one JSON object per line.
  Records with `type` user, assistant, system or attachment carry `uuid`,
  `parentUuid`, `timestamp` (ISO 8601 Z), `sessionId`, `cwd`, `gitBranch`,
  `version` and `isSidechain`. `message.content` is a string or a list of
  blocks typed text, thinking (`thinking`, `signature`), redacted_thinking,
  tool_use (`id`, `name`, `input`) or tool_result (`tool_use_id`, `content`,
  `is_error`); a tool_result `content` list holds `text` blocks and
  `tool_reference` blocks (`tool_name`).
  - `user` records: `isMeta`, `origin.kind` (human, task-notification,
    peer, coordinator, auto-continuation), `isCompactSummary` and
    `interruptedMessageId` say who wrote the text; the text markers
    `<task-notification>`, `<command-name>`, `<command-message>`,
    `<local-command-stdout>`, `<local-command-caveat>`, `<system-reminder>`
    and `<fork-boilerplate>` (the task of a forked subagent, after the
    context it inherited) do the same when no field does. Only text the
    person typed becomes a `user` row; the rest is a `system` row labelled
    `task notification:`, `peer message:`, `coordinator message:`,
    `auto-continuation:`, `slash command:`, `command output:`,
    `compaction summary:`, `interrupted:`, `subagent task:` or `context:`.
  - `assistant` records: `message.model`; `wireToolInputs[<tool_use id>]`
    is the input as the model sent it, used for the Bash command because
    the stored `input.command` lacks its `cd <dir> &&` prefix. A record
    with `isApiErrorMessage` or model `<synthetic>` is a local API error
    (`apiErrorStatus`, `error`) and becomes a `system` row `api error:`.
    Empty thinking blocks (the text was not returned, only a `signature`)
    are skipped; `redacted_thinking` is `[redacted]`.
  - `system` records: `subtype` and `content`; `turn_duration` uses
    `durationMs` and `messageCount`; a subtype without `content`
    (`api_error`, `memory_saved`, ...) is shown with the compact JSON of
    its fields other than the envelope.
  - `attachment` records, by `attachment.type`: `queued_command`
    (`prompt`, `origin.kind`) is a `user` row when `origin.kind` is human,
    else a labelled `system` row; `hook_system_message` (`hookName`,
    `content`) is `hook:`; `edited_text_file` (`filename`; the `snippet`
    is not shown) is `edited file:`. Every other attachment type is
    runtime context (system prompt, tool lists, reminders, environment
    snapshot, `remote_session_change` with the session's PR and commit)
    and is skipped.
  - Session-state records carry no `timestamp`, `cwd` or `gitBranch`; their
    rows take the latest timestamp, cwd and branch seen in the file (the
    first ones when none has been seen yet). `ai-title` (`aiTitle`),
    `custom-title` (`customTitle`) and `agent-name` (`agentName`) become
    `session title:` once per distinct value per session; `relocated`
    (`relocatedCwd`) becomes `cwd changed:` and sets `project_path` for
    every later row of the file; `pr-link` (`prUrl`, `prNumber`) is re-
    appended on every metadata flush and is emitted once per session and
    URL (the first record wins); `queue-operation` (`operation`, `content`,
    `timestamp`) is `queue <operation>: <content>`, except an `enqueue`
    whose `content` a `queued_command` attachment or a `user` record of the
    same file delivers: the prompt text stays on that record's row, and the
    enqueue keeps the time it was typed as `prompt queued: delivered at
    line N` (the first delivering line after the enqueue, else the first).
    The other state types (mode, last-prompt, cost-state,
    file-history-snapshot, file-history-delta, bridge-session, atis-latch,
    permission-mode, ...) are skipped.
* `~/.claude/projects/<slug>/<session>/subagents/[<dir>/]agent-<id>.jsonl`:
  subagent transcripts in the same format; `sessionId` is the parent
  session's id and `agentId` the subagent's. Each file starts with a
  `system` row `subagent <agentId> of <sessionId>`, and its first `user`
  record (the parent's task) is `subagent task:`. A forked subagent's file
  starts with a copy of the forking agent's context, whose `uuid`s and tool
  ids match no other file reliably, so those rows are kept; its
  `<fork-boilerplate>` block is the `subagent task:` row.
* `~/.claude/projects/<slug>/<session>/tool-results/<name>.txt`: the full
  output of a tool result too large to keep inline. The tool_result text is
  then a stub, `<persisted-output>` ... `Full output saved to: <path>` ...,
  and the `tool_result` row carries the file's text instead. The file is
  looked up only in the transcript's own session directory (the stub's
  directory name must equal it) and never through a symlink; when it is
  missing the stub is kept with a note.
* `~/.claude/history.jsonl`: `{display, project, sessionId, timestamp}` per
  prompt, `timestamp` in epoch milliseconds. Kept even when the session file
  exists because it survives session deletion.

The same files under a config home moved with `CLAUDE_CONFIG_DIR` to a
`.claude-<name>` directory in the home (such as `~/.claude-work`) are read
too: `SESSION_RX` and `HISTORY_RX` accept `.claude` or `.claude-<name>` as
the first path component, matching the catalog's `.claude-*/projects` and
`.claude-*/history.jsonl` entries. A config home anywhere else is not
collected.

Not read: the `.meta.json` subagent sidecars, `sessions/*.json` and
`paste-cache/` (excluded by the collector).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser, compact_json, iter_jsonl, text_of

SESSION_RX = re.compile(r"^\.claude(?:-[^/]+)?/projects/[^/]+/.*\.jsonl$")
SUBAGENT_RX = re.compile(r"/subagents/(?:[^/]+/)*agent-([^/]+)\.jsonl$")
HISTORY_RX = re.compile(r"^\.claude(?:-[^/]+)?/history\.jsonl$")
PERSISTED_MARK = "<persisted-output>"
PERSISTED_RX = re.compile(r"Full output saved to: ([^\r\n]*?tool-results[/\\][^/\\\r\n]+?\.txt)")

# Which tool_use input field best identifies the action, per tool name.
TOOL_KEYS = {
    "Bash": ("command",),
    "Read": ("file_path",),
    "Write": ("file_path",),
    "Edit": ("file_path",),
    "MultiEdit": ("file_path",),
    "NotebookEdit": ("notebook_path",),
    "Glob": ("pattern", "path"),
    "Grep": ("pattern", "path"),
    "WebFetch": ("url",),
    "WebSearch": ("query",),
    "Agent": ("description", "prompt"),
    "Task": ("description", "prompt"),
    "Skill": ("skill", "args"),
    "LS": ("path",),
}

# Text markers at the start of a user record's text, and the label of the
# system row they become.
TEXT_MARKERS = (
    ("<task-notification>", "task notification"),
    ("<command-name>", "slash command"),
    ("<command-message>", "slash command"),
    ("<local-command-stdout>", "command output"),
    ("<local-command-caveat>", "context"),
    ("<system-reminder>", "context"),
    ("<fork-boilerplate>", "subagent task"),
)
FORK_MARK = "<fork-boilerplate>"

# `origin.kind` values that are not the person, and their labels.
ORIGIN_LABELS = {
    "task-notification": "task notification",
    "peer": "peer message",
    "coordinator": "coordinator message",
    "auto-continuation": "auto-continuation",
}

TITLE_FIELDS = {"ai-title": "aiTitle", "custom-title": "customTitle", "agent-name": "agentName"}

# Envelope fields of a system record, left out of its detail JSON.
SYSTEM_ENVELOPE = frozenset(
    (
        "type",
        "subtype",
        "uuid",
        "parentUuid",
        "logicalParentUuid",
        "timestamp",
        "sessionId",
        "session_id",
        "cwd",
        "gitBranch",
        "version",
        "isSidechain",
        "userType",
        "entrypoint",
        "slug",
        "agentId",
        "isMeta",
        "content",
    )
)

TRANSCRIPT_TYPES = ("user", "assistant", "system", "attachment")


def tool_summary(name: str, inp) -> str:
    if not isinstance(inp, dict):
        return compact_json(inp)
    keys = TOOL_KEYS.get(name)
    if keys:
        vals = [str(inp[k]) for k in keys if inp.get(k) not in (None, "")]
        if vals:
            return " | ".join(vals)
    for k in ("command", "file_path", "path", "pattern", "url", "query", "description"):
        if inp.get(k) not in (None, ""):
            return str(inp[k])
    return compact_json(inp)


def result_text(content) -> str:
    """A tool_result's text; a `tool_reference` block is its tool name."""
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_reference":
                parts.append(str(b.get("tool_name") or ""))
            else:
                parts.append(text_of([b]))
        return "\n".join(p for p in parts if p)
    return text_of(content)


def marker_label(text: str) -> str:
    head = text.lstrip()
    for mark, label in TEXT_MARKERS:
        if head.startswith(mark):
            return label
    return ""


def session_dir(artifact: Artifact) -> Path:
    """The directory that holds a transcript's sidecars: `<session>/` next to
    a session file, or the directory above `subagents/` for a subagent."""
    p = artifact.disk_path
    if SUBAGENT_RX.search(artifact.rel):
        d = p.parent
        while d.name != "subagents" and d != d.parent:
            d = d.parent
        return d.parent
    return p.with_suffix("")


def persisted_text(artifact: Artifact, stub: str) -> str:
    """The full text of a `<persisted-output>` stub's file, or the stub with
    a note when the file is not in this session's `tool-results/`."""
    m = PERSISTED_RX.search(stub)
    if not m:
        return stub
    parts = re.split(r"[/\\]", m.group(1))
    name = parts[-1]
    sdir = session_dir(artifact)
    note = "%s\n[persisted output not found: tool-results/%s]" % (stub, name)
    if len(parts) < 3 or parts[-3] != sdir.name or name in (".", ".."):
        return note
    tdir = sdir / "tool-results"
    f = tdir / name
    try:
        if sdir.is_symlink() or tdir.is_symlink() or f.is_symlink() or not f.is_file():
            return note
        return f.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return note


class ClaudeCodeParser(Parser):
    agent = "claude-code"
    name = "claude-code"

    def wants(self, artifact: Artifact) -> bool:
        return bool(HISTORY_RX.match(artifact.rel)) or bool(SESSION_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if HISTORY_RX.match(artifact.rel):
            yield from self._parse_history(artifact, opts)
        else:
            yield from self._parse_session(artifact, opts)

    def _parse_history(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        for n, rec in iter_jsonl(artifact.disk_path, errors):
            row = self.base_row(artifact)
            row.source_line = n
            row.timestamp_utc = to_utc(rec.get("timestamp"))
            row.session_id = str(rec.get("sessionId") or "")
            row.project_path = str(rec.get("project") or "")
            row.turn_type = "user"
            row.text = compact(rec.get("display"))
            yield row

    @staticmethod
    def _prescan(artifact: Artifact) -> tuple[dict, bool, str, str]:
        """The lines that deliver each prompt by an attachment or a user
        record (so a queue enqueue can point at them instead of repeating the
        text), whether the file is a fork, and the first cwd and branch (for
        state records before any transcript one)."""
        delivered: dict[str, list[int]] = {}
        fork = False
        cwd = branch = ""

        def deliver(text: str, n: int) -> None:
            if text:
                delivered.setdefault(text, []).append(n)

        for n, rec in iter_jsonl(artifact.disk_path, []):
            rtype = rec.get("type")
            if not cwd and rec.get("cwd"):
                cwd = str(rec.get("cwd"))
            if not branch and rec.get("gitBranch"):
                branch = str(rec.get("gitBranch"))
            if rtype == "attachment":
                att = rec.get("attachment") or {}
                if isinstance(att, dict) and att.get("type") == "queued_command":
                    deliver(text_of(att.get("prompt")), n)
            elif rtype == "user":
                content = (rec.get("message") or {}).get("content")
                if isinstance(content, str):
                    deliver(content, n)
                elif isinstance(content, list):
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "text":
                            t = str(b.get("text") or "")
                            deliver(t, n)
                            if t.lstrip().startswith(FORK_MARK):
                                fork = True
        return delivered, fork, cwd, branch

    def _parse_session(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        delivered, is_fork, first_cwd, first_branch = self._prescan(artifact)
        sub = SUBAGENT_RX.search(artifact.rel)
        file_agent_id = sub.group(1) if sub else ""
        header_done = not sub
        task_done = not sub or is_fork
        session_id = ""
        last_ts = ""
        last_cwd = first_cwd
        last_branch = first_branch
        relocated = ""
        seen_pr: set = set()
        seen_title: set = set()

        for n, rec in iter_jsonl(artifact.disk_path, errors):
            rtype = rec.get("type")
            sid = rec.get("sessionId") or rec.get("session_id")
            if sid:
                session_id = str(sid)
            ts = to_utc(rec.get("timestamp"))
            if ts:
                last_ts = ts
            if rec.get("cwd"):
                last_cwd = str(rec.get("cwd"))
            if rec.get("gitBranch"):
                last_branch = str(rec.get("gitBranch"))

            def base(ts=ts) -> Row:
                row = self.base_row(artifact)
                row.source_line = n
                row.timestamp_utc = ts
                row.session_id = session_id
                row.project_path = relocated or last_cwd
                row.git_branch = last_branch
                return row

            def state_row(text: str) -> Row:
                row = base(ts or last_ts)
                row.turn_type = "system"
                row.text = compact(text)
                return row

            if not header_done and rtype in TRANSCRIPT_TYPES:
                header_done = True
                row = base()
                row.turn_type = "system"
                row.text = "subagent %s of %s" % (
                    rec.get("agentId") or file_agent_id,
                    session_id,
                )
                yield row

            if rtype == "user":
                yield from self._user(rec, base, artifact, opts, not task_done)
                task_done = True
            elif rtype == "assistant":
                yield from self._assistant(rec, base, opts)
            elif rtype == "system":
                row = base()
                row.turn_type = "system"
                subtype = str(rec.get("subtype") or "system")
                detail = text_of(rec.get("content"))
                if subtype == "turn_duration":
                    detail = "%s ms, %s messages" % (rec.get("durationMs"), rec.get("messageCount"))
                elif not detail:
                    rest = {k: v for k, v in rec.items() if k not in SYSTEM_ENVELOPE}
                    detail = compact_json(rest) if rest else ""
                row.text = compact("%s: %s" % (subtype, detail) if detail else subtype)
                yield row
            elif rtype == "attachment":
                row = self._attachment(rec, base)
                if row is not None:
                    yield row
            elif rtype in TITLE_FIELDS:
                title = str(rec.get(TITLE_FIELDS[rtype]) or "")
                if title and (session_id, title) not in seen_title:
                    seen_title.add((session_id, title))
                    yield state_row("session title: " + title)
            elif rtype == "relocated":
                new_cwd = str(rec.get("relocatedCwd") or "")
                if new_cwd:
                    relocated = new_cwd
                    yield state_row("cwd changed: " + new_cwd)
            elif rtype == "pr-link":
                url = str(rec.get("prUrl") or rec.get("prNumber") or "")
                if (session_id, url) not in seen_pr:
                    seen_pr.add((session_id, url))
                    yield state_row("pr-link: " + url)
            elif rtype == "queue-operation":
                content = text_of(rec.get("content"))
                lines = delivered.get(content) if rec.get("operation") == "enqueue" else None
                if lines:
                    at = next((x for x in lines if x > n), lines[0])
                    yield state_row("prompt queued: delivered at line %d" % at)
                    continue
                yield state_row("queue %s: %s" % (rec.get("operation"), content))
        if errors:
            row = self.base_row(artifact)
            row.session_id = session_id
            row.turn_type = "system"
            row.source_line = errors[0][0]
            row.text = "parser: %d unparseable line(s), first at line %d" % (
                len(errors),
                errors[0][0],
            )
            yield row

    def _user(self, rec, base, artifact: Artifact, opts: Options, is_task: bool) -> Iterator[Row]:
        content = (rec.get("message") or {}).get("content")
        origin = rec.get("origin") or {}
        kind = origin.get("kind") if isinstance(origin, dict) else None
        if rec.get("isCompactSummary"):
            record_label = "compaction summary"
        elif is_task:
            record_label = "subagent task"
        elif rec.get("interruptedMessageId"):
            record_label = "interrupted"
        else:
            record_label = ""

        def text_row(text: str) -> Row:
            label = (
                record_label
                or marker_label(text)
                or ORIGIN_LABELS.get(str(kind), "")
                or ("context" if rec.get("isMeta") else "")
            )
            row = base()
            if label:
                row.turn_type = "system"
                text = "%s: %s" % (label, text)
            else:
                row.turn_type = "user"
            row.text = compact(text)
            return row

        if not isinstance(content, list):
            yield text_row(text_of(content))
            return
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "tool_result":
                row = base()
                row.turn_type = "tool_result"
                row.tool_use_id = str(block.get("tool_use_id") or "")
                text = result_text(block.get("content"))
                if text.lstrip().startswith(PERSISTED_MARK):
                    text = persisted_text(artifact, text)
                if block.get("is_error"):
                    text = "[error] " + text
                row.text = compact(text)
                yield row
            elif btype in ("text", "image"):
                yield text_row(text_of([block]))

    def _assistant(self, rec, base, opts: Options) -> Iterator[Row]:
        msg = rec.get("message") or {}
        model = str(msg.get("model") or "")
        content = msg.get("content")
        if rec.get("isApiErrorMessage") or model == "<synthetic>":
            row = base()
            row.turn_type = "system"
            status = " ".join(
                str(v) for v in (rec.get("apiErrorStatus"), rec.get("error")) if v not in (None, "")
            )
            text = text_of(content)
            row.text = compact(
                "api error: %s" % ": ".join(p for p in (status, text) if p),
            )
            yield row
            return
        wire = rec.get("wireToolInputs")
        blocks = (
            content if isinstance(content, list) else [{"type": "text", "text": text_of(content)}]
        )
        for block in blocks:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "tool_use":
                row = base()
                row.turn_type = "tool_use"
                row.model = model
                row.tool_name = str(block.get("name") or "")
                row.tool_use_id = str(block.get("id") or "")
                inp = block.get("input")
                if row.tool_name == "Bash" and isinstance(wire, dict):
                    sent = wire.get(row.tool_use_id)
                    if isinstance(sent, dict) and sent.get("command"):
                        inp = sent
                row.text = compact(tool_summary(row.tool_name, inp))
                yield row
            elif btype == "text":
                text = block.get("text")
                if not text:
                    continue
                row = base()
                row.turn_type = "assistant"
                row.model = model
                row.text = compact(text)
                yield row
            elif btype in ("thinking", "redacted_thinking") and opts.include_thinking:
                if btype == "thinking":
                    text = block.get("thinking")
                    if not text:
                        continue
                else:
                    text = "[redacted]"
                row = base()
                row.turn_type = "thinking"
                row.model = model
                row.text = compact(text)
                yield row

    @staticmethod
    def _attachment(rec, base) -> Row | None:
        att = rec.get("attachment") or {}
        if not isinstance(att, dict):
            return None
        atype = att.get("type")
        if atype == "queued_command":
            text = text_of(att.get("prompt"))
            origin = att.get("origin") or {}
            kind = origin.get("kind") if isinstance(origin, dict) else None
            row = base()
            if kind == "human" and not att.get("isMeta"):
                label = marker_label(text)
            else:
                label = marker_label(text) or ORIGIN_LABELS.get(str(kind), "") or "queued command"
            if label:
                row.turn_type = "system"
                text = "%s: %s" % (label, text)
            else:
                row.turn_type = "user"
            row.text = compact(text)
            return row
        if atype == "hook_system_message":
            row = base()
            row.turn_type = "system"
            name = str(att.get("hookName") or att.get("hookEvent") or "")
            body = text_of(att.get("content"))
            row.text = compact("hook: %s" % ": ".join(p for p in (name, body) if p))
            return row
        if atype == "edited_text_file":
            row = base()
            row.turn_type = "system"
            row.text = compact("edited file: %s" % (att.get("filename") or ""))
            return row
        return None
