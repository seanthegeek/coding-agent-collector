"""Read extension global state out of a VS Code family `state.vscdb`.

`<editor User dir>/globalStorage/state.vscdb` is SQLite with one table,
`ItemTable(key TEXT, value BLOB)`. An extension's whole `globalState` is one
row whose `key` is the extension id (`sourcegraph.cody-ai`,
`rjmacarthy.twinny`, `pearai.pearai-roo-cline`) and whose `value` is UTF-8
JSON text; see microsoft/vscode at d7622a529314,
`src/vs/platform/extensionManagement/common/extensionStorage.ts:159-176`.
SecretStorage rows have keys starting `secret://` and hold encrypted
credentials; they are never read here, whatever key a caller asks for.

The database is opened through `sqlite_util.open_copy`, so the `-wal`
sidecar is applied and the evidence copy is never opened. A file that is
not SQLite at all yields nothing; a damaged SQLite file or a value that is
not JSON is reported in the returned problem list."""
from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from . import sqlite_util

STATE_DB_RX = re.compile(r"(?:^|/)User/globalStorage/state\.vscdb$")
# Catalog agents whose `User/` directory holds a VS Code family state.vscdb.
# An extension installed in a fork writes its global state to the fork's
# database, which the catalog attributes to the fork, so parsers for such
# extensions list all of these in `reads_agents`.
EDITOR_AGENTS = ("vscode", "cursor", "windsurf", "pearai", "kiro", "antigravity")
SECRET_PREFIX = "secret://"


def _text(value) -> str:
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")
    return "" if value is None else str(value)


def read_items(path: Path, keys: Iterable[str]) -> tuple[dict[str, object], list[str]]:
    """(key -> decoded JSON value, problems) for the requested `ItemTable`
    keys present in the database. A value that is not valid JSON is returned
    as its text and noted in problems, so a caller can still try to recover
    from it."""
    wanted = [k for k in keys if isinstance(k, str) and not k.startswith(SECRET_PREFIX)]
    path = Path(path)
    out: dict[str, object] = {}
    problems: list[str] = []
    if not wanted or path.is_symlink() or not sqlite_util.is_sqlite(path):
        return out, problems
    try:
        with sqlite_util.open_copy(path) as con:
            if "ItemTable" not in sqlite_util.table_names(con):
                return out, problems
            sql = "select key, value from ItemTable where key in (%s)" % ",".join("?" * len(wanted))
            rows = [(r[0], r[1]) for r in con.execute(sql, wanted)]
    except (sqlite3.DatabaseError, OSError) as e:
        return out, ["state.vscdb unreadable: %s" % e]
    for key, value in rows:
        if not isinstance(key, str) or key.startswith(SECRET_PREFIX):
            continue
        text = _text(value)
        try:
            out[key] = json.loads(text)
        except ValueError as e:
            out[key] = text
            problems.append("ItemTable value for %s is not valid JSON (%s)" % (key, e))
    return out, problems


def read_item(path: Path, key: str) -> tuple[object, list[str]]:
    """The decoded JSON value of one `ItemTable` key, or None, and problems."""
    values, problems = read_items(path, [key])
    return values.get(key), problems


__all__ = ["SECRET_PREFIX", "STATE_DB_RX", "read_item", "read_items"]
