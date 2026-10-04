"""Read-only access to collected SQLite databases.

Agents that use WAL mode (OpenCode, Crush, Goose, Kilo, Antigravity's
conversation stores) keep recent rows in a `-wal` sidecar until a checkpoint,
so the database, its `-wal` and its `-shm` are copied together into a scratch
directory and opened there. The originals are never opened, let alone
written, which matters because SQLite would otherwise checkpoint the WAL into
the evidence copy."""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def open_copy(path: Path) -> Iterator[sqlite3.Connection]:
    path = Path(path)
    tmp = tempfile.mkdtemp(prefix="cac-sqlite-")
    try:
        target = Path(tmp) / path.name
        shutil.copyfile(path, target)
        for suffix in ("-wal", "-shm", "-journal"):
            side = Path(str(path) + suffix)
            if side.is_file():
                shutil.copyfile(side, Path(str(target) + suffix))
        con = sqlite3.connect(str(target))
        try:
            con.row_factory = sqlite3.Row
            yield con
        finally:
            con.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def table_names(con: sqlite3.Connection) -> set:
    return {r[0] for r in con.execute("select name from sqlite_master where type='table'")}


def is_sqlite(path: Path) -> bool:
    try:
        with open(path, "rb") as fh:
            return fh.read(16) == b"SQLite format 3\x00"
    except OSError:
        return False
