"""ShellGPT chat and REPL sessions.

Validated against source, TheR1D/shell_gpt at a082bd5 (1.5.1) and the
pre-1.5.0 function-call shape at 6bd0bde, with a synthetic fixture; no real
install was used. See `analyzer/research/shellgpt.md`.

Files: every file directly under a `chat_cache/` directory, at any depth.
ShellGPT keeps its chat cache in the temp directory, not the home
(`tempfile.gettempdir()/chat_cache`, before 0.9.0
`gettempdir()/shell_gpt/chat_cache`), so the catalog reaches it only on
Windows as `AppData/Local/Temp/chat_cache/<id>` or
`AppData/Local/Temp/shell_gpt/chat_cache/<id>`; a copied Linux or macOS
temp directory given as loose input matches by the same directory name. The
response cache (`cache/<md5>`, a bare response string) and the config under
`.config/shell_gpt/` (`.sgptrc` holds the API key) are not read.

Each file is named by the chat id typed after `--chat` or `--repl` and holds
one single-line JSON array of OpenAI chat messages, rewritten in full on
every turn and cut to the system message plus the last `CHAT_CACHE_LENGTH`
messages. Fields read: `role`, `content`, `tool_calls[].{id,
function.{name, arguments}}` and `tool_call_id` (1.5.0 and later), and the
legacy `function_call.{name, arguments}` on assistant messages with
`{"role": "function", "name", "content"}` results (1.1.0 to 1.4.x).

Rows: `system`, `user` and `assistant` messages map to their role (an
assistant message with no content yields no row of its own); each
`tool_calls[]` entry is a `tool_use` whose text is the `shell_command`
argument when present, else the arguments; a `tool` message is a
`tool_result` joined on `tool_call_id`. A legacy `function_call` has no id,
so the parser synthesises `function_call_<array index>` and gives it to the
`function` message that immediately follows it, which is how ShellGPT itself
paired them. Nothing in the file records a time, model, working directory
or branch: those columns stay empty. The only time is the file's mtime,
which is in the manifest but not passed to parsers. The session id is the
file name, and `source_line` is 1 for every row since the file is one line.
A file cut mid-write yields the messages before the cut and one `system`
row.
"""
from __future__ import annotations

import json
import re
from typing import Iterator, List, Tuple

from ..inputs import Artifact
from ..model import Row, compact
from .base import Options, Parser, text_of

CHAT_RX = re.compile(r"(^|/)chat_cache/[^/]+$")


def _d(value) -> dict:
    return value if isinstance(value, dict) else {}


def load_messages(raw: str) -> Tuple[List[dict], str]:
    """(messages, error). A whole array parses at once; a truncated one is
    decoded element by element so the messages before the cut survive."""
    try:
        data = json.loads(raw)
    except ValueError as e:
        err = str(e)
    else:
        if isinstance(data, list):
            return [m for m in data if isinstance(m, dict)], ""
        return [], "not a JSON array"
    s = raw.lstrip()
    if not s.startswith("["):
        return [], err
    dec = json.JSONDecoder()
    out: List[dict] = []
    i = 1
    while True:
        while i < len(s) and s[i] in " \t\r\n,":
            i += 1
        if i >= len(s) or s[i] == "]":
            break
        try:
            value, i = dec.raw_decode(s, i)
        except ValueError:
            break
        if isinstance(value, dict):
            out.append(value)
    return out, "truncated after %d message(s): %s" % (len(out), err)


def call_text(arguments) -> str:
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except ValueError:
            return arguments
        if isinstance(parsed, dict) and isinstance(parsed.get("shell_command"), str):
            return parsed["shell_command"]
        return arguments
    if isinstance(arguments, dict):
        if isinstance(arguments.get("shell_command"), str):
            return arguments["shell_command"]
        return json.dumps(arguments, ensure_ascii=False, sort_keys=True)
    return "" if arguments is None else str(arguments)


class ShellGptParser(Parser):
    agent = "shellgpt"
    name = "shellgpt"

    def wants(self, artifact: Artifact) -> bool:
        return bool(CHAT_RX.search(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        session_id = artifact.disk_path.name

        def mk(turn_type: str, text: str, tool_name: str = "", tool_use_id: str = "") -> Row:
            row = self.base_row(artifact)
            row.session_id = session_id
            row.turn_type = turn_type
            row.tool_name, row.tool_use_id = tool_name, tool_use_id
            row.source_line = 1
            row.text = compact(text, opts.max_text_length)
            return row

        with open(artifact.disk_path, "rb") as fh:
            raw = fh.read().decode("utf-8", errors="replace")
        messages, error = load_messages(raw)
        if not any("role" in m for m in messages):
            yield mk("system", "parser: not a ShellGPT chat file" + (": " + error if error else ""))
            return

        names = {}          # tool call id -> function name
        pending = ("", "")  # (synthetic id, name) of a legacy function_call awaiting its result
        for i, m in enumerate(messages):
            role = str(m.get("role") or "")
            content = text_of(m.get("content"))
            prev, pending = pending, ("", "")
            if role in ("system", "user"):
                yield mk(role, content)
            elif role == "assistant":
                if content.strip():
                    yield mk("assistant", content)
                for call in m.get("tool_calls") or []:
                    call = _d(call)
                    fn = _d(call.get("function"))
                    call_id, name = str(call.get("id") or ""), str(fn.get("name") or "")
                    names[call_id] = name
                    yield mk("tool_use", call_text(fn.get("arguments")), name, call_id)
                fc = m.get("function_call")
                if isinstance(fc, dict):
                    pending = ("function_call_%d" % i, str(fc.get("name") or ""))
                    yield mk("tool_use", call_text(fc.get("arguments")), pending[1], pending[0])
            elif role == "tool":
                call_id = str(m.get("tool_call_id") or "")
                yield mk("tool_result", content, names.get(call_id, ""), call_id)
            elif role == "function":
                yield mk("tool_result", content, str(m.get("name") or prev[1]), prev[0])
            else:
                yield mk("system", "%s: %s" % (role or "message", content))
        if error:
            yield mk("system", "parser: " + error)
