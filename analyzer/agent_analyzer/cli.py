"""Command line: detect agents in an input, or write the CSV timeline."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import VERSION, catalog as catalog_mod
from .inputs import Collection, open_input
from .model import SESSION_COLUMNS, TIMELINE_COLUMNS, Row, summarise
from .parsers import ALL, Options, by_agent

PROG = "analyze-agent-artifacts"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog=PROG,
        description="Detect AI coding agent state in a collection and parse it into a CSV timeline.",
    )
    ap.add_argument("--version", action="version", version="%s %s" % (PROG, VERSION))
    sub = ap.add_subparsers(dest="command", required=True)

    def add_input(p: argparse.ArgumentParser) -> None:
        p.add_argument("input", type=Path,
                       help="collector archive (.tar.gz or .zip), extracted collection, or any directory")
        p.add_argument("--host", default="", help="host name to record when the input has no collection.json")
        p.add_argument("--user", default="", help="user name to record for a home whose owner cannot be inferred")
        p.add_argument("--work-dir", type=Path, default=None,
                       help="where to extract an archive (default: a temporary directory removed afterwards)")
        p.add_argument("--keep-extracted", action="store_true", help="do not delete the extracted archive")

    d = sub.add_parser("detect", help="list the homes, users and agents found in the input")
    add_input(d)
    d.add_argument("--json", action="store_true", help="machine-readable output")
    d.add_argument("--files", action="store_true", help="list every attributed file")

    t = sub.add_parser("timeline", help="parse transcripts into timeline.csv and sessions.csv")
    add_input(t)
    t.add_argument("-o", "--output", type=Path, required=True, help="output directory")
    t.add_argument("--max-text-length", type=int, default=0,
                   help="cut the text column to this many characters; 0 keeps the full text (default)")
    t.add_argument("--include-thinking", action="store_true",
                   help="emit thinking and reasoning blocks as rows of type thinking")
    t.add_argument("--agent", action="append", default=[],
                   help="only parse this agent (repeatable); default is every agent with a parser")

    c = sub.add_parser("catalog", help="print the bundled artifact catalog")
    c.add_argument("--agents", action="store_true", help="print agent names and whether a parser exists")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "catalog":
        return cmd_catalog(args)
    cat = catalog_mod.load()
    try:
        col = open_input(args.input, cat, work_dir=args.work_dir, host=args.host)
    except (FileNotFoundError, ValueError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    try:
        if args.user:
            for h in col.homes:
                if not h.user:
                    h.user = args.user
        if args.command == "detect":
            return cmd_detect(args, col)
        return cmd_timeline(args, col)
    finally:
        if not args.keep_extracted:
            col.cleanup()
        elif col._tmp:
            print("extracted to: %s" % col._tmp, file=sys.stderr)


# ---- catalog --------------------------------------------------------------------

def cmd_catalog(args: argparse.Namespace) -> int:
    cat = catalog_mod.load()
    if not args.agents:
        sys.stdout.write(cat.text)
        return 0
    parsers = by_agent()
    for agent in cat.agents:
        print("%-20s %s" % (agent, "parser" if agent in parsers else "detect only"))
    return 0


# ---- detect ---------------------------------------------------------------------

def detect_table(col: Collection) -> List[dict]:
    parsers = by_agent()
    rows: Dict[Tuple[str, str, str], dict] = OrderedDict()
    for a in col.artifacts:
        key = (a.home.user, a.home.original, a.agent)
        r = rows.get(key)
        if r is None:
            r = rows[key] = {
                "user": a.home.user, "home": a.home.original or str(a.home.disk_path),
                "agent": a.agent, "files": 0, "bytes": 0, "parser": a.agent in parsers,
                "inferred": a.home.inferred,
            }
        r["files"] += 1
        if a.manifest is not None:
            r["bytes"] += int(a.manifest.get("size") or 0)
        else:
            try:
                r["bytes"] += a.disk_path.lstat().st_size
            except OSError:
                pass
    return list(rows.values())


def cmd_detect(args: argparse.Namespace, col: Collection) -> int:
    table = detect_table(col)
    if args.json:
        out = {
            "input": str(col.source), "kind": col.kind, "host": col.host, "notes": col.notes,
            "homes": [{"user": h.user, "home": h.original, "inferred": h.inferred} for h in col.homes],
            "agents": table,
        }
        if args.files:
            out["files"] = [{"user": a.home.user, "agent": a.agent, "path": a.original} for a in col.artifacts]
        json.dump(out, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    print("input:   %s" % col.source)
    print("kind:    %s%s" % (col.kind, "" if col.kind != "loose" else " (no manifest; user and home inferred from paths)"))
    print("host:    %s" % (col.host or "(unknown)"))
    for n in col.notes:
        print("note:    %s" % n)
    if not table:
        print("no agent artifacts found")
        return 1
    print()
    print("%-14s %-32s %-18s %8s %12s  %s" % ("user", "home", "agent", "files", "bytes", "parser"))
    for r in table:
        print("%-14s %-32s %-18s %8d %12d  %s" % (
            r["user"] or "?", r["home"][:32], r["agent"], r["files"], r["bytes"], "yes" if r["parser"] else "detect only"))
    if args.files:
        print()
        for a in col.artifacts:
            print("%s\t%s\t%s" % (a.home.user, a.agent, a.original))
    return 0


# ---- timeline -------------------------------------------------------------------

def collect_rows(col: Collection, opts: Options, agents: List[str]) -> Tuple[List[Row], Counter, List[str]]:
    parsers = by_agent()
    rows: List[Row] = []
    counts: Counter = Counter()
    problems: List[str] = []
    for a in col.artifacts:
        if agents and a.agent not in agents:
            continue
        for p in parsers.get(a.agent, []):
            if not p.wants(a):
                continue
            try:
                for row in p.parse(a, opts):
                    rows.append(row)
                    counts[(a.agent, row.turn_type)] += 1
            except OSError as e:
                problems.append("%s: %s" % (a.original, e))
    rows.sort(key=lambda r: (r.timestamp_utc == "", r.timestamp_utc, r.source_file, r.source_line))
    return rows, counts, problems


def write_csv(path: Path, header: List[str], rows) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow(r.as_list())


def cmd_timeline(args: argparse.Namespace, col: Collection) -> int:
    opts = Options(max_text_length=args.max_text_length, include_thinking=args.include_thinking)
    args.output.mkdir(parents=True, exist_ok=True)
    rows, counts, problems = collect_rows(col, opts, args.agent)
    sessions = summarise(rows)
    timeline = args.output / "timeline.csv"
    sess = args.output / "sessions.csv"
    write_csv(timeline, TIMELINE_COLUMNS, rows)
    write_csv(sess, SESSION_COLUMNS, sessions)
    detect = detect_table(col)
    with open(args.output / "detect.json", "w", encoding="utf-8") as fh:
        json.dump({"input": str(col.source), "kind": col.kind, "host": col.host, "notes": col.notes,
                   "agents": detect}, fh, indent=2)
    print("input:     %s (%s)" % (col.source, col.kind))
    print("host:      %s" % (col.host or "(unknown)"))
    for n in col.notes:
        print("note:      %s" % n)
    for p in problems:
        print("problem:   %s" % p)
    parsed_agents = sorted({a for a, _ in counts})
    unparsed = [r["agent"] for r in detect if not r["parser"]]
    print("agents:    parsed %s; detected only %s" % (
        ", ".join(parsed_agents) or "none", ", ".join(sorted(set(unparsed))) or "none"))
    print("rows:      %d in %s" % (len(rows), timeline))
    for (agent, tt), n in sorted(counts.items()):
        print("           %-14s %-12s %d" % (agent, tt, n))
    print("sessions:  %d in %s" % (len(sessions), sess))
    return 0 if rows else 1
