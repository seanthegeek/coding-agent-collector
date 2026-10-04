"""Fleet inventory: read the JSON Lines a collector prints with --inventory
(sh) or -Inventory (PowerShell), one saved stdout per host, and flatten them
into one CSV with a per-agent rollup.

Record shapes, from collect-agent-artifacts.sh and Collect-AgentArtifacts.ps1
(collector 1.6.0):

  {"type":"host","host":...,"collector":...,"mode":...,"at":...,
   "users_scanned":N,"users_unreadable":N,"docker_volumes":N}
  {"type":"agent","host":...,"user":...,"agent":...,"files":N,"bytes":N,
   "first":...,"last":...,"projects":N,"evidence":...}

A host line opens a run; the agent lines after it belong to that run until
the next host line. Anything else on a line (console banners, prompts, a
PowerShell error record) is junk: skipped and counted, never fatal.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .timeutil import to_utc

DEFAULT_NAME = "fleet-inventory.csv"

INVENTORY_COLUMNS = [
    "host", "collector", "mode", "at", "user", "agent", "files", "bytes",
    "first", "last", "projects", "evidence",
]

HOST_FIELDS = ("host", "collector", "mode", "at")
AGENT_FIELDS = ("user", "agent", "files", "bytes", "first", "last", "projects", "evidence")
TIME_FIELDS = ("at", "first", "last")


def input_files(paths: Iterable[Path]) -> list[Path]:
    """Each INPUT as given, or for a directory its regular files (not
    recursive, symlinks not followed), sorted by name."""
    out: list[Path] = []
    for p in paths:
        if p.is_symlink():
            raise FileNotFoundError("%s is a symlink; give its target" % p)
        if p.is_dir():
            out.extend(sorted(c for c in p.iterdir() if c.is_file() and not c.is_symlink()))
        elif p.is_file():
            out.append(p)
        else:
            raise FileNotFoundError("%s does not exist" % p)
    return out


def _cell(field: str, value) -> str:
    if value is None:
        return ""
    if field in TIME_FIELDS:
        return to_utc(value)
    return str(value)


def _record(line: str) -> dict | None:
    line = line.strip().lstrip("﻿")
    if not line.startswith("{"):
        return None
    try:
        r = json.loads(line)
    except ValueError:
        return None
    if not isinstance(r, dict) or r.get("type") not in ("host", "agent"):
        return None
    return r


def read_file(path: Path) -> tuple[list[list[str]], int]:
    """Rows for one captured stdout, and the number of junk lines skipped."""
    rows: list[list[str]] = []
    junk = 0
    host: dict[str, str] | None = None
    host_has_agents = False

    def close_host() -> None:
        if host is not None and not host_has_agents:
            rows.append([host[f] for f in HOST_FIELDS] + [""] * len(AGENT_FIELDS))

    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        for line in fh:
            r = _record(line)
            if r is None:
                if line.strip():
                    junk += 1
                continue
            if r["type"] == "host":
                close_host()
                host = {f: _cell(f, r.get(f)) for f in HOST_FIELDS}
                host_has_agents = False
                continue
            if host is not None:
                head = [host[f] for f in HOST_FIELDS]
                host_has_agents = True
            else:
                # An agent line with no host line before it: its own host
                # field, and the run fields left empty.
                head = [_cell("host", r.get("host")), "", "", ""]
            rows.append(head + [_cell(f, r.get(f)) for f in AGENT_FIELDS])
    close_host()
    return rows, junk


def rollup(rows: list[list[str]]) -> list[tuple[str, int, int, str]]:
    """(agent, hosts, users, latest last) per agent. users counts distinct
    (host, user) pairs. Sorted by hosts, then users, descending, then name."""
    hosts: dict[str, set] = {}
    users: dict[str, set] = {}
    latest: dict[str, str] = {}
    ih, iu, ia, il = (INVENTORY_COLUMNS.index(c) for c in ("host", "user", "agent", "last"))
    for r in rows:
        a = r[ia]
        if not a:
            continue
        hosts.setdefault(a, set()).add(r[ih])
        users.setdefault(a, set()).add((r[ih], r[iu]))
        if r[il] > latest.get(a, ""):
            latest[a] = r[il]
        else:
            latest.setdefault(a, "")
    out = [(a, len(hosts[a]), len(users[a]), latest[a]) for a in hosts]
    out.sort(key=lambda t: (-t[1], -t[2], t[0]))
    return out
