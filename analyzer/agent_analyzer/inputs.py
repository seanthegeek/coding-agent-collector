"""Open whatever the analyst points at and turn it into attributed artifacts.

Three input shapes are accepted:

* a collector archive (`*_agent-artifacts.tar.gz` or `.zip`), extracted to a
  work directory first;
* an extracted collection: a directory holding `manifest.jsonl`,
  `collection.json` and `fs/`;
* a loose directory: anything else, such as a copied home directory, a
  mounted image, another collector's output, or a single agent directory
  like `.claude` copied on its own.

With a manifest, attribution (host, user, home, agent) is read from it. Without
one, homes are discovered by matching the catalog against the tree and the
user is inferred from the path, which the output marks by leaving `host`
empty unless `--host` is given.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Dict, Iterator, List, Optional, Tuple

from .catalog import Catalog

PARSE_STATUSES = ("collected",)

# Parent directories whose children are user homes, as the collectors enumerate
# them. Matched against the path of a discovered home relative to the root.
HOME_PARENTS = ("home", "Users", "usr/home", "export/home")
ROOT_HOMES = ("root", "var/root")


@dataclass
class Home:
    disk_path: Path          # where the home is on the analyst's disk
    original: str            # path on the source host, best effort
    user: str
    host: str = ""
    inferred: bool = False   # True when user/original came from the path, not a manifest


@dataclass
class Artifact:
    disk_path: Path
    original: str            # path on the source host
    rel: str                 # path relative to the home, posix
    agent: str
    home: Home
    manifest: Optional[dict] = None


@dataclass
class Collection:
    source: Path
    kind: str                # archive | collected | loose
    root: Path               # directory that holds fs/ (collected) or the tree itself (loose)
    host: str = ""
    manifest: Optional[List[dict]] = None
    summary: Optional[dict] = None
    homes: List[Home] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    _tmp: Optional[str] = None

    def cleanup(self) -> None:
        if self._tmp and os.path.isdir(self._tmp):
            shutil.rmtree(self._tmp, ignore_errors=True)
            self._tmp = None

    def artifacts_for(self, agent: str) -> List[Artifact]:
        return [a for a in self.artifacts if a.agent == agent]

    def agents(self) -> List[str]:
        seen: Dict[str, None] = {}
        for a in self.artifacts:
            seen.setdefault(a.agent)
        return list(seen)


def open_input(path: Path, catalog: Catalog, work_dir: Optional[Path] = None, host: str = "") -> Collection:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_file():
        col = _open_archive(path, work_dir)
    elif (path / "manifest.jsonl").is_file() and (path / "fs").is_dir():
        col = Collection(source=path, kind="collected", root=path)
    else:
        col = Collection(source=path, kind="loose", root=path)
    if host:
        col.host = host
    if col.kind in ("archive", "collected"):
        _load_collected(col, catalog)
    else:
        _discover_loose(col, catalog)
    return col


# ---- archives -----------------------------------------------------------------

def _open_archive(path: Path, work_dir: Optional[Path]) -> Collection:
    if work_dir:
        work_dir.mkdir(parents=True, exist_ok=True)
        dest = Path(tempfile.mkdtemp(prefix="cac-", dir=str(work_dir)))
    else:
        dest = Path(tempfile.mkdtemp(prefix="cac-analyzer-"))
    col = Collection(source=path, kind="archive", root=dest)
    col._tmp = str(dest)
    sidecar = Path(str(path) + ".sha256")
    if sidecar.is_file():
        col.notes.append(_verify_sidecar(path, sidecar))
    if zipfile.is_zipfile(path):
        _extract_zip(path, dest)
    elif tarfile.is_tarfile(path):
        _extract_tar(path, dest)
    else:
        col.cleanup()
        raise ValueError("%s is neither a tar nor a zip archive" % path)
    # An archive produced by the collector unpacks to manifest.jsonl + fs/ at
    # the top; anything else is treated as a loose tree.
    if not ((dest / "manifest.jsonl").is_file() and (dest / "fs").is_dir()):
        col.kind = "loose"
    return col


def _verify_sidecar(archive: Path, sidecar: Path) -> str:
    expected = sidecar.read_text(encoding="utf-8", errors="replace").split()
    expected = expected[0].lower() if expected else ""
    h = hashlib.sha256()
    with open(archive, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    actual = h.hexdigest()
    if actual == expected:
        return "archive sha256 verified against %s" % sidecar.name
    return "WARNING archive sha256 %s does not match %s (%s)" % (actual, sidecar.name, expected)


def _safe_member(dest: Path, name: str) -> bool:
    p = PurePosixPath(name)
    return not p.is_absolute() and ".." not in p.parts and not re.match(r"^[A-Za-z]:", name)


def _skip_links(member, dest):
    """Extraction filter: regular files and directories go through the data
    filter; symlinks and hard links are not materialised. The collector
    recreates symlinks with their original absolute targets, which the data
    filter would reject; their targets are in the manifest `target` field."""
    if member.issym() or member.islnk() or member.isdev():
        return None
    return tarfile.data_filter(member, dest)


def _extract_tar(path: Path, dest: Path) -> None:
    with tarfile.open(path, "r:*") as tf:
        if hasattr(tarfile, "data_filter"):
            tf.extractall(dest, filter=_skip_links)
            return
        members = [m for m in tf.getmembers()
                   if _safe_member(dest, m.name) and not (m.issym() or m.islnk() or m.isdev())]
        tf.extractall(dest, members=members)


def _extract_zip(path: Path, dest: Path) -> None:
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if not _safe_member(dest, name):
                continue
            target = dest / name
            if name.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


# ---- collected layout (manifest present) --------------------------------------

def _load_collected(col: Collection, catalog: Catalog) -> None:
    root = col.root
    summary_path = root / "collection.json"
    if summary_path.is_file():
        try:
            col.summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            col.notes.append("collection.json unreadable: %s" % e)
    if not col.host and col.summary:
        col.host = str(col.summary.get("hostname") or "")
    rows: List[dict] = []
    bad = 0
    with open(root / "manifest.jsonl", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                bad += 1
    if bad:
        col.notes.append("%d manifest rows did not parse" % bad)
    col.manifest = rows
    homes: Dict[Tuple[str, str], Home] = {}
    for r in rows:
        if r.get("status") not in PARSE_STATUSES or r.get("type") != "file":
            continue
        user = str(r.get("user") or "")
        home_orig = str(r.get("home") or "")
        key = (user, home_orig)
        home = homes.get(key)
        if home is None:
            home = Home(disk_path=root / _archive_dir_for_home(r), original=home_orig, user=user, host=col.host)
            homes[key] = home
        orig = str(r.get("path") or "")
        archive_path = str(r.get("archive_path") or "")
        rel = _relative_to_home(orig, home_orig)
        col.artifacts.append(Artifact(
            disk_path=root / archive_path, original=orig, rel=rel,
            agent=str(r.get("agent") or ""), home=home, manifest=r,
        ))
    col.homes = list(homes.values())


def _archive_dir_for_home(row: dict) -> str:
    """fs/<home> as the collector lays it out, derived from one row so Windows
    drive-letter layouts (fs/C/Users/alice) are handled without guessing."""
    orig = str(row.get("path") or "")
    home = str(row.get("home") or "")
    ap = str(row.get("archive_path") or "")
    rel = _relative_to_home(orig, home)
    if rel and ap.replace("\\", "/").endswith(rel):
        return ap.replace("\\", "/")[: -len(rel)].rstrip("/")
    return "fs" + home.replace("\\", "/")


def _relative_to_home(path: str, home: str) -> str:
    p = path.replace("\\", "/")
    h = home.replace("\\", "/").rstrip("/")
    if h and (p == h or p.startswith(h + "/")):
        return p[len(h) :].lstrip("/")
    return p.lstrip("/")


# ---- loose layout (no manifest) ------------------------------------------------

def _discover_loose(col: Collection, catalog: Catalog) -> None:
    root = col.root
    tree = root / "fs" if (root / "fs").is_dir() and not (root / "manifest.jsonl").exists() else root
    if tree is not root:
        col.notes.append("fs/ found without manifest.jsonl; treating fs/ as the root")
    homes: List[Home] = []

    # The analyst may have pointed at an agent directory itself (~/.claude,
    # ~/.codex copied out on its own). Its parent is then the home, restricted
    # to this one directory, and nothing inside it is a home.
    for e in catalog.entries:
        if len(e.segments) == 1 and e.agent != "shared" and e.regexes[0].fullmatch(tree.name):
            parent = tree.resolve().parent
            home = Home(disk_path=tree.parent, original="", user=_user_from_parts(parent.parts[1:]),
                        host=col.host, inferred=True)
            col.notes.append("root is a %s directory; treating its parent as the home" % e.agent)
            homes.append(home)
            _add_hits(col, home, [(e, tree)])
            col.homes = homes
            return

    first_rx = catalog.first_segment_regexes()
    for dirpath, dirnames, filenames in os.walk(tree, followlinks=False):
        here = Path(dirpath)
        names = dirnames + filenames
        if any(rx.fullmatch(n) for n in names for rx in first_rx):
            hits = list(catalog.matches_in_home(here))
            # A directory holding only shared files (AGENTS.md, .env) is a
            # project, not a home; it needs a hit from a real agent.
            if any(entry.agent != "shared" for entry, _ in hits):
                homes.append(_make_home(here, tree, col.host))
                _add_hits(col, homes[-1], hits)
                dirnames[:] = []       # a home does not contain other homes
                continue
        dirnames[:] = [d for d in dirnames if not (here / d).is_symlink()]
    col.homes = homes


def _user_from_parts(parts) -> str:
    """Owner of a home from its path components, by the conventions the
    collectors use to enumerate homes: home/<u>, Users/<u>, usr/home/<u>,
    export/home/<u>, root, var/root. Empty when none applies."""
    parts = [p for p in parts if p]
    for parent in HOME_PARENTS:
        pp = parent.split("/")
        if len(parts) >= len(pp) + 1 and parts[-len(pp) - 1 : -1] == pp:
            return parts[-1]
    if "/".join(parts) in ROOT_HOMES:
        return "root"
    return ""


def _make_home(here: Path, tree: Path, host: str) -> Home:
    rel = here.relative_to(tree).as_posix() if here != tree else ""
    parts = rel.split("/") if rel else []
    user = _user_from_parts(parts)
    if not user and parts and parts[-1] != "fs":
        user = parts[-1]       # a directory that holds agent state is usually named after its owner
    return Home(disk_path=here, original="/" + rel if rel else "", user=user, host=host, inferred=True)


def _add_hits(col: Collection, home: Home, hits) -> None:
    seen: Dict[Path, None] = {}
    for entry, hit in hits:
        for f in _walk_files(hit):
            if f in seen:
                continue
            seen[f] = None
            rel = f.relative_to(home.disk_path).as_posix()
            col.artifacts.append(Artifact(
                disk_path=f, original=(home.original.rstrip("/") + "/" + rel) if home.original else rel,
                rel=rel, agent=entry.agent, home=home,
            ))


def _walk_files(p: Path) -> Iterator[Path]:
    if p.is_symlink():
        return
    if p.is_file():
        yield p
        return
    for dirpath, dirnames, filenames in os.walk(p, followlinks=False):
        here = Path(dirpath)
        dirnames[:] = [d for d in dirnames if not (here / d).is_symlink()]
        for n in filenames:
            f = here / n
            if not f.is_symlink():
                yield f
