"""little-coder's own files.

Validated against source, itayinbarr/little-coder at 89d4fa0a (pinning pi
0.83.x, October 2026), with a synthetic fixture; see
`research/little-coder.md`. little-coder is a launcher and extension set for
pi, so its transcripts are pi session files in pi's directory, parsed by
`pi.py` under agent `pi` with a system row naming little-coder. This parser
reads what little-coder writes itself:

* `~/.pi/agent/little-coder-prompt-history.json`: a JSON array of up to
  100 prompt strings, oldest first. No timestamps and no session ids, so
  the `user` rows have neither; `source_line` is the 1-based array index.
  A truncated array still yields the prompts before the cut.
* `~/.little-coder/checkpoints/<session file name>/<path with
  [^A-Za-z0-9._-] replaced by _>`: the pre-edit copy of each file a
  session's first `write`/`edit` touched, or an empty `<name>.absent`
  sentinel when the file did not exist yet. The directory name is the pi
  session file's basename (`<time>_<session id>.jsonl`), or `default` when
  there was no session file. One system row per directory, emitted on its
  alphabetically first file, names the session and the files; its
  timestamp is the earliest file mtime (the first checkpoint, kept by the
  collector's `cp -p`). The session id is taken from the directory name,
  and the project path from the pi session header when that file was
  collected in the same home.
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterator
from pathlib import Path

from ..inputs import Artifact
from ..model import Row, compact
from ..timeutil import to_utc
from .base import Options, Parser
from .cline_legacy import iter_json_array
from .pi import read_session

HISTORY_REL = ".pi/agent/little-coder-prompt-history.json"
CHECKPOINT_RX = re.compile(r"^\.little-coder/checkpoints/([^/]+)/[^/]+$")
SESSION_FILE_RX = re.compile(r"_([^_/]+)\.jsonl$")


def _regular_files(d: Path) -> list[os.DirEntry]:
    try:
        return sorted((e for e in os.scandir(d) if e.is_file(follow_symlinks=False)), key=lambda e: e.name)
    except OSError:
        return []


def _session_header(home: Path, name: str) -> dict | None:
    sessions = home / ".pi/agent/sessions"
    if sessions.is_symlink() or not sessions.is_dir():
        return None
    for d in sorted(sessions.iterdir()):
        f = d / name
        if not d.is_symlink() and d.is_dir() and not f.is_symlink() and f.is_file():
            return read_session(f).header or None
    return None


class LittleCoderParser(Parser):
    agent = "little-coder"
    name = "little-coder"

    def wants(self, artifact: Artifact) -> bool:
        return artifact.rel == HISTORY_REL or bool(CHECKPOINT_RX.match(artifact.rel))

    def parse(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        if artifact.rel == HISTORY_REL:
            yield from self._parse_history(artifact, opts)
        else:
            yield from self._parse_checkpoints(artifact, opts)

    def _parse_history(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        errors: list = []
        for n, v in iter_json_array(artifact.disk_path, errors):
            if not isinstance(v, str) or not v:
                continue
            row = self.base_row(artifact)
            row.source_line = n
            row.turn_type = "user"
            row.text = compact(v, opts.max_text_length)
            yield row
        if errors:
            row = self.base_row(artifact)
            row.turn_type = "system"
            row.source_line = errors[0][0]
            row.text = "parser: %s" % errors[0][1]
            yield row

    def _parse_checkpoints(self, artifact: Artifact, opts: Options) -> Iterator[Row]:
        set_name = CHECKPOINT_RX.match(artifact.rel).group(1)
        files = _regular_files(artifact.disk_path.parent)
        if not files or files[0].name != artifact.disk_path.name:
            return    # the set's row comes from its first file
        mtimes: list[float] = []
        names: list[tuple[str, bool]] = []
        for e in files:
            try:
                mtimes.append(e.stat(follow_symlinks=False).st_mtime)
            except OSError:
                pass
            absent = e.name.endswith(".absent")
            names.append((e.name[: -len(".absent")] if absent else e.name, absent))
        m = SESSION_FILE_RX.search(set_name)
        row = self.base_row(artifact)
        row.source_line = 0
        row.turn_type = "system"
        row.session_id = m.group(1) if m else ""
        header = _session_header(artifact.home.disk_path, set_name) if m else None
        if header:
            row.session_id = str(header.get("id") or row.session_id)
            row.project_path = str(header.get("cwd") or "")
        row.timestamp_utc = to_utc(min(mtimes)) if mtimes else ""
        listed = "; ".join(n + (" (did not exist)" if a else "") for n, a in names)
        what = "pi session %s" % set_name if m else "no session file (%s)" % set_name
        row.text = compact("little-coder checkpoints for %s: %d pre-edit file(s)%s: %s" % (
            what, len(names), "" if header else ", session file not collected", listed), opts.max_text_length)
        yield row

