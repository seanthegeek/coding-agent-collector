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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

CATALOG_FILE = Path(__file__).with_name("catalog.txt")


@dataclass
class Entry:
    agent: str
    glob: str
    segments: Tuple[str, ...]
    regexes: Tuple["re.Pattern[str]", ...]

    @property
    def first_segment(self) -> str:
        return self.segments[0]


@dataclass
class Catalog:
    entries: List[Entry] = field(default_factory=list)
    project_entries: List[Entry] = field(default_factory=list)
    excludes: List[str] = field(default_factory=list)
    secrets: List[str] = field(default_factory=list)
    text: str = ""

    @property
    def agents(self) -> List[str]:
        seen: Dict[str, None] = {}
        for e in self.entries:
            seen.setdefault(e.agent)
        return list(seen)

    def first_segment_regexes(self) -> List["re.Pattern[str]"]:
        seen: Dict[str, "re.Pattern[str]"] = {}
        for e in self.entries:
            seen.setdefault(e.first_segment, e.regexes[0])
        return list(seen.values())

    def matches_in_home(self, home: Path) -> Iterator[Tuple[Entry, Path]]:
        """Yield (entry, path) for every catalog glob that exists under home.

        Expansion is segment by segment through real directory listings, so
        the cost is proportional to the catalog, not to the size of the tree.
        Symlinks are never followed.
        """
        listing_cache: Dict[Path, List[str]] = {}
        for entry in self.entries:
            for hit in _expand(home, entry.regexes, listing_cache):
                yield entry, hit


def glob_segment_to_regex(seg: str) -> "re.Pattern[str]":
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


def _expand(base: Path, regexes: Tuple["re.Pattern[str]", ...], cache: Dict[Path, List[str]]) -> Iterator[Path]:
    if not regexes:
        yield base
        return
    names = cache.get(base)
    if names is None:
        try:
            names = os.listdir(base)
        except OSError:
            names = []
        cache[base] = names
    rx = regexes[0]
    rest = regexes[1:]
    for name in names:
        if rx.fullmatch(name) is None:
            continue
        child = base / name
        if rest:
            if child.is_dir() and not child.is_symlink():
                yield from _expand(child, rest, cache)
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
            continue
        if section == "home":
            agent, _, glob = line.partition("|")
            cat.entries.append(_make_entry(agent, glob))
        elif section == "project":
            agent, _, glob = line.partition("|")
            cat.project_entries.append(_make_entry(agent, glob))
        elif section == "exclude":
            cat.excludes.append(line)
        else:
            cat.secrets.append(line)
    return cat
