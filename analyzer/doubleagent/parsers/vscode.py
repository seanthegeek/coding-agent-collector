"""VS Code chat sessions (GitHub Copilot Chat and other chat participants).

Validated against source, microsoft/vscode at d7622a529314 (see
`analyzer/research/vscode.md`), with a synthetic fixture; no real install
was checked. The store is VS Code's own, so the same parser covers every
editor data directory the catalog attributes to `vscode`: Code, Code -
Insiders, VSCodium, Positron and Trae under `.config`, `Library/Application
Support` or `AppData/Roaming`, and the remote-server layout
`.vscode-server*/data`, `.vscodium-server*/data`, `.positron-server/data`.
Files, relative to that directory's `User/`:

* `workspaceStorage/<hash>/chatSessions/<sessionId>.jsonl` (1.109 and
  later) or `.json` (earlier), with `workspaceStorage/<hash>/workspace.json`
  (`folder` or `workspace`, a file URI) giving the project path;
* `globalStorage/emptyWindowChatSessions/<sessionId>.jsonl` or `.json`;
* `globalStorage/transferredChatSessions/<sessionId>.json`.

`.jsonl` files are an object mutation log replayed in order: `{"kind": 0,
"v": <session>}` sets the whole object, `{"kind": 1, "k": [path], "v"}`
sets a value, `{"kind": 2, "k": [path], "v": [items], "i"?}` pushes items
(truncating to `i` first), `{"kind": 3, "k": [path]}` deletes. `.json`
files are the session object itself.

Session fields: `sessionId`, `creationDate` (ms), `responderUsername`,
`initialLocation`, `customTitle`, `workingDirectory` (URI), `requests[]`.
Request fields: `requestId`, `timestamp` (ms), `message` (`{text}` or a
string), `variableData.variables[].name`, `modelId`,
`isSystemInitiated`, `isCanceled`, `response[]`, `responseTimestamp` (ms),
`result.errorDetails.message`. Response parts: a bare `{value}` markdown
string (or `{kind: "markdownContent", content: {value}}`), `{kind:
"inlineReference", name?, inlineReference}`, `{kind: "thinking", value}`
(string or list), `{kind: "toolInvocationSerialized", toolCallId, toolId,
invocationMessage, pastTenseMessage, isComplete, toolSpecificData
(`commandLine.original` or `rawInput`), resultDetails (`{input, output:
[{value}], isError}` or a list of URIs), resultError}`, `{kind:
"textEditGroup", uri}`. Legacy `response` may be a string or a list of
strings. Other part kinds (progress, confirmation, undo stops, code block
URIs) are skipped.

The Copilot Chat extension is closed source, so `modelId` (the `model`
column) and `responderUsername` (in the session-start row) are passed
through as opaque strings; `agent.id` is not used. User rows carry
the request `timestamp`, response rows `responseTimestamp` (falling back to
the request time). Contiguous markdown and inline references become one
`assistant` row; each tool invocation becomes a `tool_use` and a
`tool_result` row sharing `toolCallId`. There is no git branch.
`source_line` is the log line that created the request (`.jsonl`) or 0
(`.json`).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .antigravity import uri_to_path
from .base import Options, Parser, compact_json, iter_jsonl

USER_DIR = (
    r"^(?:(?:\.config|Library/Application Support|AppData/Roaming)/(?:Code[^/]*|VSCodium[^/]*|Positron|Trae[^/]*)"
    r"|\.vscode-server[^/]*/data|\.vscodium-server[^/]*/data|\.positron-server/data)/User/"
)
SESSION_RX = re.compile(
    USER_DIR + r"(?:workspaceStorage/[^/]+/chatSessions/[^/]+\.jsonl?"
    r"|globalStorage/emptyWindowChatSessions/[^/]+\.jsonl?"
    r"|globalStorage/transferredChatSessions/[^/]+\.json)$"
)


class MutationError(ValueError):
    pass


def apply_mutation(state, rec: dict):
    """Apply one mutation-log record to `state` and return the new state."""
    kind = rec.get("kind")
    if kind == 0:
        return rec.get("v")
    path = rec.get("k")
    if not isinstance(path, list) or (not path and kind != 2):
        raise MutationError("bad path %r" % (path,))
    if kind == 2 and not path:
        target = state
    else:
        parent = _walk(state, path[:-1])
        key = path[-1]
        if kind == 1:
            _set(parent, key, rec.get("v"))
            return state
        if kind == 3:
            try:
                del parent[key]
            except (KeyError, IndexError, TypeError):
                pass
            return state
        if kind != 2:
            raise MutationError("unknown kind %r" % (kind,))
        try:
            target = parent[key]
        except (KeyError, IndexError, TypeError):
            target = None
        if target is None:
            target = []
            _set(parent, key, target)
    if not isinstance(target, list):
        raise MutationError("push to non-list at %r" % (path,))
    if isinstance(rec.get("i"), int):
        del target[rec["i"] :]
    items = rec.get("v")
    target.extend(items if isinstance(items, list) else [items])
    return state


def _walk(state, path):
    cur = state
    for k in path:
        try:
            cur = cur[k]
        except (KeyError, IndexError, TypeError):
            raise MutationError("path %r not found" % (path,)) from None
    return cur


def _set(parent, key, value):
    if isinstance(parent, list) and isinstance(key, int):
        if key == len(parent):
            parent.append(value)
        elif 0 <= key < len(parent):
            parent[key] = value
        else:
            raise MutationError("index %r out of range" % (key,))
    elif isinstance(parent, dict):
        parent[key] = value
    else:
        raise MutationError("cannot set %r" % (key,))


def md_text(v) -> str:
    """An IMarkdownString (`{value}`), a plain string or a list of either."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        val = v.get("value")
        return val if isinstance(val, str) else ""
    if isinstance(v, list):
        return "\n".join(md_text(x) for x in v)
    return str(v)


def uri_text(u) -> str:
    """A serialized URI (`{scheme, path, ...}` or `{$mid, fsPath}`), a URI
    string, or a location `{uri, range}`."""
    if isinstance(u, str):
        return uri_to_path(u)
    if isinstance(u, dict):
        if "uri" in u:
            return uri_text(u["uri"])
        for k in ("fsPath", "path", "external"):
            if isinstance(u.get(k), str):
                return u[k]
    return compact_json(u) if u is not None else ""


def tool_call_text(part: dict) -> str:
    tsd = part.get("toolSpecificData")
    if isinstance(tsd, dict):
        cl = tsd.get("commandLine")
        if isinstance(cl, dict) and (cl.get("userEdited") or cl.get("original")):
            return str(cl.get("userEdited") or cl.get("original"))
        if "rawInput" in tsd:
            raw = tsd["rawInput"]
            return raw if isinstance(raw, str) else compact_json(raw)
    rd = part.get("resultDetails")
    if isinstance(rd, dict) and isinstance(rd.get("input"), str) and rd["input"]:
        return rd["input"]
    return md_text(part.get("invocationMessage"))


def tool_result_text(part: dict) -> str:
    rd = part.get("resultDetails")
    text = ""
    is_error = bool(part.get("resultError"))
    if isinstance(rd, dict):
        out = rd.get("output")
        if isinstance(out, list):
            vals = []
            for o in out:
                if isinstance(o, dict):
                    v = o.get("value", o.get("text"))
                    vals.append(v if isinstance(v, str) else compact_json(v))
                elif isinstance(o, str):
                    vals.append(o)
            text = "\n".join(vals)
        elif out is not None:
            text = out if isinstance(out, str) else compact_json(out)
        is_error = is_error or bool(rd.get("isError"))
    elif isinstance(rd, list):
        text = "\n".join(uri_text(u) for u in rd)
    if part.get("resultError"):
        err = part["resultError"]
        text = "\n".join(x for x in (md_text(err) if not isinstance(err, bool) else "", text) if x)
    if not text:
        text = md_text(part.get("pastTenseMessage"))
    if not text and part.get("isComplete") is False:
        text = "[incomplete]"
    return ("[error] " + text) if is_error else text


class VsCodeParser(Parser):
    agent = "vscode"
    name = "vscode"

    def wants(self, artifact: Artifact) -> bool:
        return bool(SESSION_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        req_lines: dict[int, int] = {}
        problems: list[str] = []
        first_bad = 0
        if artifact.rel.endswith(".jsonl"):
            errors: list = []
            state = None
            for n, rec in iter_jsonl(artifact.disk_path, errors):
                try:
                    state = apply_mutation(state, rec)
                except MutationError as e:
                    errors.append((n, str(e)))
                    continue
                self._track(rec, state, n, req_lines)
            if errors:
                first_bad = min(e[0] for e in errors)
                problems.append(
                    "parser: %d unparseable line(s), first at line %d" % (len(errors), first_bad)
                )
        else:
            try:
                with open(artifact.disk_path, "rb") as fh:
                    state = json.loads(fh.read().decode("utf-8", errors="replace"))
            except ValueError as e:
                state = None
                problems.append("parser: file is not valid JSON (%s)" % e)
        if not isinstance(state, dict):
            state = {}
        session_id = str(state.get("sessionId") or Path(artifact.rel).name.rsplit(".", 1)[0])
        project = self._workspace_folder(artifact) or uri_to_path(
            str(state.get("workingDirectory") or "")
        )

        def base(turn_type: str, text: str, ts, line: int, model: str = "") -> Row:
            row = self.base_row(artifact)
            row.session_id = session_id
            row.project_path = project
            row.timestamp_utc = to_utc(ts)
            row.source_line = line
            row.model = model
            row.turn_type = turn_type
            row.text = compact(text)
            return row

        if state:
            yield base(
                "system",
                " ".join(
                    x
                    for x in (
                        "session start:",
                        "responder=%s" % state["responderUsername"]
                        if state.get("responderUsername")
                        else "",
                        "location=%s" % state["initialLocation"]
                        if state.get("initialLocation")
                        else "",
                        "title=%s" % state["customTitle"] if state.get("customTitle") else "",
                    )
                    if x
                ),
                state.get("creationDate"),
                req_lines.get(-1, 0),
            )
        requests = state.get("requests")
        if not isinstance(requests, list):
            requests = []
        for i, req in enumerate(requests):
            if isinstance(req, dict):
                yield from self._request_rows(req, req_lines.get(i, 0), base, opts)
        for p in problems:
            yield base("system", p, None, first_bad)

    @staticmethod
    def _track(rec: dict, state, n: int, req_lines: dict[int, int]) -> None:
        """Remember the log line that created each request."""
        kind, path = rec.get("kind"), rec.get("k") or []
        if kind == 0:
            req_lines.clear()
            req_lines[-1] = n
            reqs = state.get("requests") if isinstance(state, dict) else None
            for i in range(len(reqs) if isinstance(reqs, list) else 0):
                req_lines[i] = n
        elif path == ["requests"]:
            reqs = state.get("requests") if isinstance(state, dict) else None
            total = len(reqs) if isinstance(reqs, list) else 0
            start = 0
            if kind == 2:
                start = (
                    rec["i"] if isinstance(rec.get("i"), int) else total - len(rec.get("v") or [])
                )
            for i in list(req_lines):
                if i >= start:
                    del req_lines[i]
            for i in range(max(start, 0), total):
                req_lines[i] = n
        elif kind == 1 and len(path) == 2 and path[0] == "requests" and isinstance(path[1], int):
            req_lines[path[1]] = n

    @staticmethod
    def _workspace_folder(artifact: Artifact) -> str:
        parts = artifact.rel.split("/")
        if len(parts) < 4 or parts[-2] != "chatSessions" or parts[-4] != "workspaceStorage":
            return ""
        ws = artifact.disk_path.parent.parent / "workspace.json"
        try:
            if ws.is_symlink() or not ws.is_file():
                return ""
            with open(ws, "rb") as fh:
                data = json.loads(fh.read().decode("utf-8", errors="replace"))
        except (OSError, ValueError):
            return ""
        if not isinstance(data, dict):
            return ""
        return uri_to_path(str(data.get("folder") or data.get("workspace") or ""))

    def _request_rows(self, req: dict, line: int, base, opts: Options) -> Iterator[Row]:
        model = str(req.get("modelId") or "")
        req_ts = req.get("timestamp")
        resp_ts = req.get("responseTimestamp") or req_ts
        msg = req.get("message")
        text = (
            msg
            if isinstance(msg, str)
            else (msg.get("text") if isinstance(msg, dict) else "") or ""
        )
        names = []
        vd = req.get("variableData")
        for v in (vd.get("variables") if isinstance(vd, dict) else None) or []:
            if isinstance(v, dict) and v.get("name"):
                names.append(str(v["name"]))
        if names:
            text = "%s\n[attached: %s]" % (text, ", ".join(names))
        if req.get("isSystemInitiated"):
            yield base("system", "system initiated: " + text, req_ts, line, model)
        else:
            yield base("user", text, req_ts, line, model)

        response = req.get("response")
        if isinstance(response, (str, dict)):
            response = [response]
        run: list[str] = []

        def flush():
            joined = "".join(run).strip()
            del run[:]
            if joined:
                return base("assistant", joined, resp_ts, line, model)
            return None

        for part in response or []:
            if isinstance(part, str):
                run.append(part)
                continue
            if not isinstance(part, dict):
                continue
            kind = part.get("kind")
            if kind is None and "value" in part:
                run.append(md_text(part))
                continue
            if kind == "markdownContent":
                run.append(md_text(part.get("content")))
                continue
            if kind == "inlineReference":
                run.append(str(part.get("name") or uri_text(part.get("inlineReference"))))
                continue
            row = flush()
            if row:
                yield row
            if kind == "thinking":
                if opts.include_thinking:
                    t = md_text(part.get("value"))
                    if t:
                        yield base("thinking", t, resp_ts, line, model)
            elif kind == "toolInvocationSerialized":
                tid = str(part.get("toolCallId") or "")
                tname = str(part.get("toolId") or "")
                use = base("tool_use", tool_call_text(part), resp_ts, line, model)
                use.tool_name, use.tool_use_id = tname, tid
                yield use
                res = base("tool_result", tool_result_text(part), resp_ts, line, model)
                res.tool_name, res.tool_use_id = tname, tid
                yield res
            elif kind == "textEditGroup":
                yield base("system", "edit: " + uri_text(part.get("uri")), resp_ts, line, model)
        row = flush()
        if row:
            yield row
        result = req.get("result")
        err = result.get("errorDetails") if isinstance(result, dict) else None
        if isinstance(err, dict) and err.get("message"):
            yield base("system", "error: %s" % err["message"], resp_ts, line, model)
        elif req.get("isCanceled"):
            yield base("system", "canceled", resp_ts, line, model)


__all__ = ["VsCodeParser", "apply_mutation", "tool_call_text", "tool_result_text"]
