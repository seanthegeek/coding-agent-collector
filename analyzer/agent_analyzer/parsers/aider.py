"""Aider chat, input and LLM history files.

Validated against source, Aider-AI/aider at 5dc9490 (`aider/io.py`,
`aider/utils.py`, `aider/coders/base_coder.py`) and prompt_toolkit's
`FileHistory`, with a synthetic fixture; see `analyzer/research/aider.md`.

Aider writes into the git root of the repository it runs in (else the
working directory), so these files usually arrive through the collector's
project catalog: the manifest attributes them to agent `project` with the
project directory as the home, and `artifact.rel` is the bare file name.
The CLI offers every `project` artifact to every parser, so this parser
takes those too and labels the rows `aider`. A history file directly in a home is
attributed to `aider` by the main catalog. Either way `project_path` is the
directory holding the file. Files:

* `.aider.chat.history.md`, appended markdown. `# aider chat started at
  YYYY-MM-DD HH:MM:SS` opens a session; `#### ` lines are user input (one
  per input line, `#### <blank>` for empty input, slash commands included);
  `> ` blockquote lines are tool and system output (applied edits, commits,
  errors; `>>>>>>> REPLACE` is not one); anything else is assistant
  markdown, SEARCH/REPLACE blocks included. Consecutive lines of one kind
  are one row.
* `.aider.input.history`, prompt_toolkit `FileHistory`: `# YYYY-MM-DD
  HH:MM:SS.ffffff` then one `+<line>` per input line.
* `.aider.llm.history`, only with `--llm-history-file`: `TO LLM
  YYYY-MM-DDTHH:MM:SS` followed by `-------`-separated messages whose lines
  are prefixed with the upper-case role, and `LLM RESPONSE <ts>` followed by
  `ASSISTANT <line>` lines.

Every timestamp in these files is host local time with no zone, and the
collection does not record the host's zone, so they are emitted as if they
were UTC; correct them by the host's offset. The session id is synthesised
as `<path of .aider.chat.history.md>#<header timestamp>`. Chat history rows
take the session header's time, or, from a user prompt on, the time of the
matching `.aider.input.history` entry (same text, between this header and
the next). Input and LLM history rows are assigned to the last session
header at or before their own time when the chat history sits beside them.
No model, git branch or tool call id is recorded. Each `TO LLM` request
becomes one `system` row naming the message count and the last user
message; the full prompt is at `source_file:source_line`.
"""

from __future__ import annotations

import bisect
import re
from collections.abc import Callable, Iterator
from pathlib import Path

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser

CHAT = ".aider.chat.history.md"
INPUT = ".aider.input.history"
LLM = ".aider.llm.history"
FILE_RX = re.compile(r"^(?:.*/)?(\.aider\.(?:chat\.history\.md|input\.history|llm\.history))$")
HEADER_RX = re.compile(r"^# aider chat started at (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s*$")
INPUT_TS_RX = re.compile(r"^# (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d(?:\.\d+)?)\s*$")
LLM_RX = re.compile(r"^(TO LLM|LLM RESPONSE) (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)\s*$")
ROLE_TURN = {"USER": "user", "ASSISTANT": "assistant", "SYSTEM": "system"}


def _lines(path: Path) -> Iterator[tuple[int, str]]:
    with open(path, "rb") as fh:
        for n, raw in enumerate(fh, 1):
            yield n, raw.decode("utf-8", errors="replace").rstrip("\r\n")


def _norm(s: str) -> str:
    return " ".join(s.split())


def sibling(original: str, name: str) -> str:
    """The path of `name` in the directory holding `original`, keeping the
    source host's separator."""
    i = max(original.rfind("/"), original.rfind("\\"))
    if i < 0:
        return name
    return original[: i + 1] + name


def project_dir(original: str) -> str:
    i = max(original.rfind("/"), original.rfind("\\"))
    return original[:i] if i > 0 else original[: i + 1]


def read_input_history(path: Path, errors: list | None = None) -> list[tuple[int, str, str]]:
    """(line, local timestamp, text) per prompt_toolkit FileHistory entry."""
    out: list[list] = []
    for n, line in _lines(path):
        m = INPUT_TS_RX.match(line)
        if m:
            out.append([n, m.group(1), []])
        elif line.startswith("+"):
            if not out:
                out.append([n, "", []])
            out[-1][2].append(line[1:])
        elif line.strip() and errors is not None:
            errors.append((n, "not a FileHistory line"))
    return [(e[0], e[1], "\n".join(e[2])) for e in out]


def read_headers(path: Path) -> list[str]:
    """Session header timestamps of a chat history, in file order."""
    if not path.is_file() or path.is_symlink():
        return []
    return [m.group(1) for _, line in _lines(path) for m in [HEADER_RX.match(line)] if m]


class AiderParser(Parser):
    agent = "aider"
    name = "aider"

    def wants(self, artifact: Artifact) -> bool:
        return bool(FILE_RX.match(artifact.rel))

    def base_row(self, artifact: Artifact) -> Row:
        row = Row(
            host=artifact.home.host,
            user=artifact.home.user,
            agent="aider",
            source_file=artifact.original,
        )
        row.project_path = project_dir(artifact.original)
        return row

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        m = FILE_RX.match(artifact.rel)
        assert m is not None  # wants() accepted only matching paths
        kind = m.group(1)
        if kind == CHAT:
            yield from self._parse_chat(artifact, opts)
        elif kind == INPUT:
            yield from self._parse_input(artifact, opts)
        else:
            yield from self._parse_llm(artifact, opts)

    def _session_for(self, artifact: Artifact) -> Callable[[str], str]:
        """Map a local timestamp to the session id of the last chat header at
        or before it, using the chat history beside this file."""
        headers = sorted(read_headers(artifact.disk_path.parent / CHAT))
        chat = sibling(artifact.original, CHAT)

        def lookup(ts: str) -> str:
            if not ts or not headers:
                return ""
            i = bisect.bisect_right(headers, ts.replace("T", " ")[:19])
            return "%s#%s" % (chat, headers[i - 1]) if i else ""

        return lookup

    # ---- .aider.chat.history.md ------------------------------------------------

    def _parse_chat(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        headers = read_headers(artifact.disk_path)
        inputs = []
        inp = artifact.disk_path.parent / INPUT
        if inp.is_file() and not inp.is_symlink():
            try:
                inputs = [e for e in read_input_history(inp) if e[1]]
            except OSError:
                inputs = []
        next_input = 0
        session_id = ""
        header = ""
        next_header = ""
        n_header = 0
        ts = ""
        kind = ""
        buf: list[str] = []
        start = 0

        def flush() -> Iterator[Row]:
            nonlocal next_input, ts
            text = "\n".join(buf).strip()
            if not text or not kind:
                return
            if kind == "user" and header:
                for j in range(next_input, len(inputs)):
                    ets = inputs[j][1]
                    if ets[:19] < header:
                        continue
                    if next_header and ets[:19] >= next_header:
                        break
                    if _norm(inputs[j][2]) == _norm(text):
                        ts = to_utc(ets)
                        next_input = j + 1
                        break
            row = self.base_row(artifact)
            row.source_line = start
            row.timestamp_utc = ts
            row.session_id = session_id
            row.turn_type = {"user": "user", "tool": "tool_result", "assistant": "assistant"}[kind]
            row.text = compact(text, opts.max_text_length)
            yield row

        for n, line in _lines(artifact.disk_path):
            m = HEADER_RX.match(line)
            if m:
                yield from flush()
                kind, buf = "", []
                header = m.group(1)
                n_header += 1
                next_header = headers[n_header] if n_header < len(headers) else ""
                ts = to_utc(header)
                session_id = "%s#%s" % (artifact.original, header)
                row = self.base_row(artifact)
                row.source_line = n
                row.timestamp_utc = ts
                row.session_id = session_id
                row.turn_type = "system"
                row.text = "aider chat started at %s (local time)" % header
                yield row
                continue
            if line.startswith("#### ") or line.rstrip() == "####":
                new, content = "user", line[5:]
            elif line.startswith("> ") or line == ">":
                new, content = "tool", line[2:]
            else:
                new, content = "assistant", line
            if new != kind:
                yield from flush()
                kind, buf, start = new, [], n
            if not any(b.strip() for b in buf):
                start = n
            buf.append(content.rstrip() if new != "assistant" else content)
        yield from flush()

    # ---- .aider.input.history --------------------------------------------------

    def _parse_input(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        session_for = self._session_for(artifact)
        for n, ts, text in read_input_history(artifact.disk_path, errors):
            row = self.base_row(artifact)
            row.source_line = n
            row.timestamp_utc = to_utc(ts)
            row.session_id = session_for(ts)
            row.turn_type = "user"
            row.text = compact(text, opts.max_text_length)
            yield row
        yield from self._errors(artifact, errors)

    # ---- .aider.llm.history ----------------------------------------------------

    def _parse_llm(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        session_for = self._session_for(artifact)
        block: dict | None = None

        def emit(b: dict | None) -> Iterator[Row]:
            if b is None:
                return
            row = self.base_row(artifact)
            row.source_line = b["line"]
            row.timestamp_utc = to_utc(b["ts"])
            row.session_id = session_for(b["ts"])
            if b["kind"] == "LLM RESPONSE":
                text = "\n".join(_strip_role(ln, "ASSISTANT") for ln in b["lines"]).strip()
                if not text:
                    return
                row.turn_type = "assistant"
                row.text = compact(text, opts.max_text_length)
                yield row
                return
            msgs: list[tuple[str, list[str]]] = []
            for ln in b["lines"]:
                if ln == "-------":
                    msgs.append(("", []))
                elif msgs:
                    role, body = msgs[-1]
                    if not role:
                        role = ln.split(" ", 1)[0]
                        msgs[-1] = (role, body)
                    body.append(_strip_role(ln, role))
            counts: dict[str, int] = {}
            last_user = ""
            for role, body in msgs:
                counts[role] = counts.get(role, 0) + 1
                if role == "USER":
                    last_user = "\n".join(body)
            row.turn_type = "system"
            row.text = compact(
                "TO LLM: %d message(s) (%s); last user message: %s"
                % (len(msgs), ", ".join("%s %d" % kv for kv in counts.items()), last_user),
                opts.max_text_length,
            )
            yield row

        for n, line in _lines(artifact.disk_path):
            m = LLM_RX.match(line)
            if m:
                yield from emit(block)
                block = {"kind": m.group(1), "ts": m.group(2), "line": n, "lines": []}
            elif block is not None:
                block["lines"].append(line)
            elif line.strip():
                errors.append((n, "text before the first TO LLM / LLM RESPONSE marker"))
        yield from emit(block)
        yield from self._errors(artifact, errors)

    def _errors(self, artifact: Artifact, errors: list) -> Iterator[Row]:
        if errors:
            row = self.base_row(artifact)
            row.turn_type = "system"
            row.source_line = errors[0][0]
            row.text = "parser: %d unparseable line(s), first at line %d" % (
                len(errors),
                errors[0][0],
            )
            yield row


def _strip_role(line: str, role: str) -> str:
    if line == role:
        return ""
    if role and line.startswith(role + " "):
        return line[len(role) + 1 :]
    return line
