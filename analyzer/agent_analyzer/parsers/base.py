"""Parser interface. A parser owns one agent name from the catalog, says which
of that agent's artifacts it reads, and yields timeline rows from each."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass

from ..inputs import Artifact
from ..model import Row


@dataclass
class Options:
    include_thinking: bool = False


class Parser:
    agent: str = ""
    name: str = ""
    # Other catalog agents whose artifacts this parser is also offered: an
    # extension whose chats are rows of the editor's own state.vscdb, which
    # the catalog attributes to `vscode` or to a fork such as `cursor`, lists
    # those editors here (`vscode_state.EDITOR_AGENTS`).
    reads_agents: tuple[str, ...] = ()

    def wants(self, artifact: Artifact) -> bool:
        raise NotImplementedError

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        raise NotImplementedError

    def base_row(self, artifact: Artifact) -> Row:
        return Row(
            host=artifact.home.host,
            user=artifact.home.user,
            agent=self.agent,
            source_file=artifact.original,
        )


def iter_jsonl(path, errors: list) -> Iterator[tuple[int, dict]]:
    """Yield (line_number, record) for each JSON object line. Bad lines are
    counted in `errors` as (line_number, message) and skipped: a transcript
    truncated mid-write by a running agent must not lose its earlier turns."""
    with open(path, "rb") as fh:
        for n, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw.decode("utf-8", errors="replace"))
            except ValueError as e:
                errors.append((n, str(e)))
                continue
            if isinstance(rec, dict):
                yield n, rec


def text_of(content) -> str:
    """Flatten the content field of a chat message: a string, or a list of
    typed blocks whose text lives under `text`."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, str):
                parts.append(b)
            elif isinstance(b, dict):
                t = b.get("text")
                if isinstance(t, str):
                    parts.append(t)
                elif b.get("type") == "image":
                    parts.append("[image]")
        return "\n".join(parts)
    if isinstance(content, dict):
        t = content.get("text")
        return t if isinstance(t, str) else json.dumps(content, ensure_ascii=False)
    return str(content)


def compact_json(value) -> str:
    try:
        s = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError):
        s = str(value)
    return s
