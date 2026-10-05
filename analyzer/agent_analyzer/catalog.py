"""The shared artifact catalog.

`catalog.txt` is a verbatim copy of `collect-agent-artifacts.sh --list` and is
the analyzer's detection database: the same `agent|glob` table that tells the
collectors what to gather tells the analyzer what a loose directory contains.
`collectors/tests/catalog-sync.sh` fails when the copy drifts. Regenerate it
with:

    collectors/collect-agent-artifacts.sh --list > analyzer/agent_analyzer/catalog.txt

Glob semantics match the collectors: catalog globs do not cross `/`, exclusion
and secret globs do, `[...]` classes work everywhere.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

CATALOG_FILE = Path(__file__).with_name("catalog.txt")


@dataclass
class Entry:
    agent: str
    glob: str
    segments: tuple[str, ...]
    regexes: tuple[re.Pattern[str], ...]

    @property
    def first_segment(self) -> str:
        return self.segments[0]


@dataclass
class Catalog:
    entries: list[Entry] = field(default_factory=list)
    project_entries: list[Entry] = field(default_factory=list)
    excludes: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    docker_volumes: list[Entry] = field(default_factory=list)  # agent|volume name glob
    text: str = ""

    @property
    def agents(self) -> list[str]:
        seen: dict[str, None] = {}
        for e in self.entries:
            seen.setdefault(e.agent)
        return list(seen)

    def first_segment_regexes(self) -> list[re.Pattern[str]]:
        seen: dict[str, re.Pattern[str]] = {}
        for e in self.entries:
            seen.setdefault(e.first_segment, e.regexes[0])
        return list(seen.values())

    def nested_matches(self, agent_dir: Path, onerror=None) -> Iterator[tuple[Entry, Path]]:
        """Yield (entry, path) for catalog globs that live inside agent_dir
        when agent_dir itself is the first segment of their glob, for example
        .gemini/antigravity-cli inside a .gemini directory given as the root."""
        listing_cache: dict[Path, list[str]] = {}
        for entry in self.entries:
            if len(entry.segments) < 2 or entry.regexes[0].fullmatch(agent_dir.name) is None:
                continue
            for hit in _expand(agent_dir, entry.regexes[1:], listing_cache, onerror):
                yield entry, hit

    def matches_in_home(self, home: Path, onerror=None) -> Iterator[tuple[Entry, Path]]:
        """Yield (entry, path) for every catalog glob that exists under home.

        Expansion is segment by segment through real directory listings, so
        the cost is proportional to the catalog, not to the size of the tree.
        Symlinks are never followed. A directory that cannot be listed
        matches nothing and is passed, as the OSError, to `onerror` once.
        """
        listing_cache: dict[Path, list[str]] = {}
        for entry in self.entries:
            for hit in _expand(home, entry.regexes, listing_cache, onerror):
                yield entry, hit


def glob_segment_to_regex(seg: str) -> re.Pattern[str]:
    """Convert one glob path segment to a regex. `*` and `?` never match `/`;
    `[...]` passes through with `!` meaning negation as in sh."""
    out = []
    i = 0
    while i < len(seg):
        c = seg[i]
        if c == "*":
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "[":
            j = seg.find("]", i + 1)
            if j == -1:
                out.append(re.escape(c))
            else:
                body = seg[i + 1 : j]
                if body.startswith("!"):
                    body = "^" + body[1:]
                body = body.replace("\\", "\\\\")
                out.append("[" + body + "]")
                i = j
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("".join(out))


def _expand(
    base: Path,
    regexes: tuple[re.Pattern[str], ...],
    cache: dict[Path, list[str]],
    onerror=None,
) -> Iterator[Path]:
    if not regexes:
        yield base
        return
    names = cache.get(base)
    if names is None:
        try:
            names = os.listdir(base)
        except OSError as e:
            names = []
            if onerror is not None:
                onerror(e)
        cache[base] = names
    rx = regexes[0]
    rest = regexes[1:]
    for name in names:
        if rx.fullmatch(name) is None:
            continue
        child = base / name
        if rest:
            if child.is_dir() and not child.is_symlink():
                yield from _expand(child, rest, cache, onerror)
        else:
            yield child


def _make_entry(agent: str, glob: str) -> Entry:
    segments = tuple(s for s in glob.split("/") if s)
    return Entry(agent, glob, segments, tuple(glob_segment_to_regex(s) for s in segments))


def load(path: Path = CATALOG_FILE) -> Catalog:
    text = path.read_text(encoding="utf-8")
    return parse(text)


def parse(text: str) -> Catalog:
    cat = Catalog(text=text)
    section = "home"
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        if line.startswith("#"):
            head = line[1:].strip().lower()
            if head.startswith("home artifacts"):
                section = "home"
            elif head.startswith("project artifacts"):
                section = "project"
            elif head.startswith("excluded"):
                section = "exclude"
            elif head.startswith("credential files"):
                section = "secret"
            elif head.startswith("docker volumes"):
                section = "docker"
            continue
        if section == "home":
            agent, _, glob = line.partition("|")
            cat.entries.append(_make_entry(agent, glob))
        elif section == "project":
            agent, _, glob = line.partition("|")
            cat.project_entries.append(_make_entry(agent, glob))
        elif section == "exclude":
            cat.excludes.append(line)
        elif section == "docker":
            agent, _, glob = line.partition("|")
            cat.docker_volumes.append(_make_entry(agent, glob))
        else:
            cat.secrets.append(line)
    return cat
