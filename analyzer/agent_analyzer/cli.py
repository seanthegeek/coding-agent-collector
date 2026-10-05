"""Command line: detect agents in an input, or write the JSONL timeline."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

from . import VERSION
from . import catalog as catalog_mod
from . import inventory as inventory_mod
from .filters import FORMS_HELP, RowFilter, parse_bound
from .inputs import Collection, describe_error, error_reason, open_input
from .model import Row, summarise
from .parsers import ALL, Options, by_agent

PROG = "analyze-agent-artifacts"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Detect AI coding agent state in a collection and parse it into a JSONL timeline."
        ),
    )
    ap.add_argument("--version", action="version", version="%s %s" % (PROG, VERSION))
    sub = ap.add_subparsers(dest="command", required=True)

    def add_input(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "input",
            type=Path,
            help="collector archive (.tar.gz or .zip), extracted collection, or any directory",
        )
        p.add_argument(
            "--host", default="", help="host name to record when the input has no collection.json"
        )
        p.add_argument(
            "--user",
            default="",
            help="user name to record for a home whose owner cannot be inferred",
        )
        p.add_argument(
            "--work-dir",
            type=Path,
            default=None,
            help="where to extract an archive (default: a temporary directory removed afterwards)",
        )
        p.add_argument(
            "--keep-extracted", action="store_true", help="do not delete the extracted archive"
        )

    d = sub.add_parser("detect", help="list the homes, users and agents found in the input")
    add_input(d)
    d.add_argument("--json", action="store_true", help="machine-readable output")
    d.add_argument("--files", action="store_true", help="list every attributed file")

    t = sub.add_parser("timeline", help="parse transcripts into timeline.jsonl and sessions.jsonl")
    add_input(t)
    t.add_argument("-o", "--output", type=Path, required=True, help="output directory")
    t.add_argument(
        "--include-thinking",
        action="store_true",
        help="emit thinking and reasoning blocks as rows of type thinking",
    )
    t.add_argument(
        "--agent",
        action="append",
        default=[],
        help="only parse this agent (repeatable); default is every agent with a parser",
    )
    t.add_argument(
        "--since",
        metavar="WHEN",
        default="",
        help="keep rows at or after WHEN; see --until for the forms",
    )
    t.add_argument(
        "--until",
        metavar="WHEN",
        default="",
        help="keep rows at or before WHEN. UTC unless an offset is given; a value without a "
        "time of day (2026-10-01, 2026-10, today) covers that whole period. " + FORMS_HELP,
    )
    t.add_argument(
        "--keep-undated",
        action="store_true",
        help="with --since or --until, also keep rows that have no timestamp",
    )
    t.add_argument(
        "--match",
        metavar="REGEX",
        action="append",
        default=[],
        help="keep rows whose text matches this Python regular expression (repeatable, any may "
        "match); a matched tool call keeps its result and a matched result its call",
    )
    t.add_argument(
        "-i",
        "--ignore-case",
        action="store_true",
        help="make --match case-insensitive",
    )

    i = sub.add_parser("inventory", help="merge collector --inventory outputs into one fleet CSV")
    i.add_argument(
        "input",
        type=Path,
        nargs="+",
        help="a saved stdout of collect-agent-artifacts --inventory, or a directory of them",
    )
    i.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(inventory_mod.DEFAULT_NAME),
        help="CSV to write (default: %s in the current directory)" % inventory_mod.DEFAULT_NAME,
    )

    c = sub.add_parser("catalog", help="print the bundled artifact catalog")
    c.add_argument(
        "--agents", action="store_true", help="print agent names and whether a parser exists"
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "catalog":
        return cmd_catalog(args)
    if args.command == "inventory":
        return cmd_inventory(args)
    if args.command == "timeline":
        # Checked before an archive is extracted, so a typo fails at once.
        try:
            args.row_filter = build_filter(args)
        except ValueError as e:
            print("error: %s" % e, file=sys.stderr)
            return 2
    cat = catalog_mod.load()
    try:
        col = open_input(args.input, cat, work_dir=args.work_dir, host=args.host)
    except OSError as e:
        print("error: %s" % describe_error(args.input, e), file=sys.stderr)
        return 2
    except ValueError as e:
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


# ---- inventory ------------------------------------------------------------------


def cmd_inventory(args: argparse.Namespace) -> int:
    try:
        files = inventory_mod.input_files(args.input)
    except OSError as e:
        print("error: %s" % describe_error("", e), file=sys.stderr)
        return 2
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    rows: list[list[str]] = []
    for f in files:
        try:
            got, junk = inventory_mod.read_file(f)
        except OSError as e:
            print("error: %s" % describe_error(f, e), file=sys.stderr)
            return 2
        if junk:
            print(
                "skipped %d non-inventory line%s in %s" % (junk, "" if junk == 1 else "s", f),
                file=sys.stderr,
            )
        rows.extend(got)
    if args.output.parent != Path(""):
        args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(inventory_mod.INVENTORY_COLUMNS)
        w.writerows(rows)
    hosts = {r[0] for r in rows}
    print(
        "rows:   %d from %d host%s in %s"
        % (len(rows), len(hosts), "" if len(hosts) == 1 else "s", args.output)
    )
    roll = inventory_mod.rollup(rows)
    if roll:
        print()
        print("%-22s %6s %6s  %s" % ("agent", "hosts", "users", "latest"))
        for agent, nh, nu, last in roll:
            print("%-22s %6d %6d  %s" % (agent, nh, nu, last))
    return 0 if rows else 1


# ---- detect ---------------------------------------------------------------------


def detect_table(col: Collection) -> list[dict]:
    parsers = by_agent()
    rows: dict[tuple[str, str, str], dict] = OrderedDict()
    for a in col.artifacts:
        key = (a.home.user, a.home.original, a.agent)
        r = rows.get(key)
        if r is None:
            r = rows[key] = {
                "user": a.home.user,
                "home": a.home.original or str(a.home.disk_path),
                "agent": a.agent,
                "files": 0,
                "bytes": 0,
                "parser": a.agent in parsers,
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
            "input": str(col.source),
            "kind": col.kind,
            "host": col.host,
            "notes": col.notes,
            "homes": [
                {"user": h.user, "home": h.original, "inferred": h.inferred} for h in col.homes
            ],
            "agents": table,
            "problems": col.problems,
        }
        if args.files:
            out["files"] = [
                {"user": a.home.user, "agent": a.agent, "path": a.original} for a in col.artifacts
            ]
        json.dump(out, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    print("input:   %s" % col.source)
    print(
        "kind:    %s%s"
        % (
            col.kind,
            "" if col.kind != "loose" else " (no manifest; user and home inferred from paths)",
        )
    )
    print("host:    %s" % (col.host or "(unknown)"))
    for n in col.notes:
        print("note:    %s" % n)
    for p in col.problems:
        print("problem: %s" % p)
    if not table:
        print("no agent artifacts found")
        return 1
    print()
    print("%-14s %-32s %-18s %8s %12s  %s" % ("user", "home", "agent", "files", "bytes", "parser"))
    for r in table:
        print(
            "%-14s %-32s %-18s %8d %12d  %s"
            % (
                r["user"] or "?",
                r["home"][:32],
                r["agent"],
                r["files"],
                r["bytes"],
                "yes" if r["parser"] else "detect only",
            )
        )
    if args.files:
        print()
        for a in col.artifacts:
            print("%s\t%s\t%s" % (a.home.user, a.agent, a.original))
    return 0


# ---- timeline -------------------------------------------------------------------

# Agent name the collector gives to files found through PROJECT_CATALOG inside
# a discovered repository. Such a file may belong to any agent (Crush's
# .crush/crush.db, Aider's .aider.chat.history.md), so it is offered to every
# parser instead of to the parsers of one agent.
PROJECT_AGENT = "project"


def parsers_for(artifact, parsers: dict[str, list]) -> list:
    if artifact.agent == PROJECT_AGENT:
        return ALL
    own = parsers.get(artifact.agent, [])
    # Parsers that read another agent's files (Cody and Twinny rows inside
    # the state.vscdb of `vscode` or a fork) say so in `reads_agents`.
    return own + [p for p in ALL if artifact.agent in p.reads_agents and p not in own]


def collect_rows(
    col: Collection, opts: Options, agents: list[str]
) -> tuple[list[Row], Counter, list[str]]:
    parsers = by_agent()
    rows: list[Row] = []
    counts: Counter = Counter()
    problems: list[str] = list(col.problems)
    for a in col.artifacts:
        for p in parsers_for(a, parsers):
            # Filter on the parser's agent, so --agent aider also takes the
            # repository-level Aider files the manifest calls `project`.
            if agents and p.agent not in agents:
                continue
            if not p.wants(a):
                continue
            try:
                for row in p.parse(a, opts):
                    rows.append(row)
                    counts[(p.agent, row.turn_type)] += 1
            except OSError as e:
                problems.append("%s: %s" % (a.original, error_reason(e)))
    rows.sort(key=lambda r: (r.timestamp_utc == "", r.timestamp_utc, r.source_file, r.source_line))
    return rows, counts, problems


# No spaces after separators: the same layout as `jq -c`, so a grep pattern
# such as '"agent":"codex-cli"' matches both the file and jq's output.
JSONL_SEPARATORS = (",", ":")


def jsonl_line(record: dict) -> str:
    """One JSON object on one line, keys in schema order. Non-ASCII text is
    written as UTF-8 rather than escaped, so grep finds it as typed. U+2028
    and U+2029 are escaped because some line readers (Python's
    str.splitlines among them) split on them, and a record holding a lone
    surrogate, which UTF-8 cannot encode, falls back to ASCII escapes."""
    s = json.dumps(record, ensure_ascii=False, separators=JSONL_SEPARATORS)
    try:
        s.encode("utf-8")
    except UnicodeEncodeError:
        return json.dumps(record, separators=JSONL_SEPARATORS)
    return s.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def write_jsonl(path: Path, rows) -> None:
    with open(path, "w", newline="\n", encoding="utf-8") as fh:
        for r in rows:
            fh.write(jsonl_line(r.as_dict()))
            fh.write("\n")


def build_filter(args: argparse.Namespace) -> RowFilter:
    """The row filter from --since, --until, --keep-undated and --match.
    Raises ValueError with a message for the user on a bad value."""
    since = parse_bound(args.since) if args.since else ""
    until = parse_bound(args.until, end=True) if args.until else ""
    if since and until and since > until:
        raise ValueError("--since %s is after --until %s" % (since, until))
    flags = re.IGNORECASE if args.ignore_case else 0
    patterns = []
    for m in args.match:
        try:
            patterns.append(re.compile(m, flags))
        except re.error as e:
            raise ValueError("--match %r: %s" % (m, e)) from None
    return RowFilter(since, until, args.keep_undated, patterns)


def cmd_timeline(args: argparse.Namespace, col: Collection) -> int:
    opts = Options(include_thinking=args.include_thinking)
    rf: RowFilter = args.row_filter
    args.output.mkdir(parents=True, exist_ok=True)
    rows, counts, problems = collect_rows(col, opts, args.agent)
    parsed_agents = sorted({a for a, _ in counts})
    if rf.active:
        rows = rf.apply(rows)
        counts = Counter((r.agent, r.turn_type) for r in rows)
    sessions = summarise(rows)
    timeline = args.output / "timeline.jsonl"
    sess = args.output / "sessions.jsonl"
    write_jsonl(timeline, rows)
    write_jsonl(sess, sessions)
    detect = detect_table(col)
    with open(args.output / "detect.json", "w", encoding="utf-8") as fh:
        json.dump(
            {
                "input": str(col.source),
                "kind": col.kind,
                "host": col.host,
                "notes": col.notes,
                "agents": detect,
                "problems": problems,
            },
            fh,
            indent=2,
        )
    print("input:     %s (%s)" % (col.source, col.kind))
    print("host:      %s" % (col.host or "(unknown)"))
    for n in col.notes:
        print("note:      %s" % n)
    for p in problems:
        print("problem:   %s" % p)
    if rf.since or rf.until:
        print(
            "window:    %s to %s%s"
            % (
                rf.since or "(start)",
                rf.until or "(end)",
                ", undated rows kept" if rf.keep_undated else "",
            )
        )
    if rf.patterns:
        print(
            "match:     %s%s"
            % (
                " | ".join(p.pattern for p in rf.patterns),
                " (ignore case)" if args.ignore_case else "",
            )
        )
    if rf.active:
        print(
            "filtered:  %d outside the window, %d without a timestamp, %d not matching"
            % (rf.dropped_window, rf.dropped_undated, rf.dropped_match)
        )
    # Project-tagged files are routed to every parser, so they are never
    # "detected only" in their own right.
    unparsed = [r["agent"] for r in detect if not r["parser"] and r["agent"] != PROJECT_AGENT]
    print(
        "agents:    parsed %s; detected only %s"
        % (", ".join(parsed_agents) or "none", ", ".join(sorted(set(unparsed))) or "none")
    )
    print("rows:      %d in %s" % (len(rows), timeline))
    for (agent, tt), n in sorted(counts.items()):
        print("           %-14s %-12s %d" % (agent, tt, n))
    print("sessions:  %d in %s" % (len(sessions), sess))
    return 0 if rows else 1
