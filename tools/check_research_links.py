#!/usr/bin/env python3
"""Verify every GitHub blob link in the research documents.

Each citation in collectors/research/*.md and analyzer/research/*.md links to
a file and line range at the commit the document reviewed. This checks that
the path exists at that commit and that the line range lies inside the file.
It is the first review gate for a research round: a citation that does not
resolve, or a claim with no citation, is unverified.

Usage: tools/check_research_links.py [--repos DIR] [FILE...]

With --repos, a checkout under DIR whose HEAD is the cited commit is used
instead of the network (name the checkout after the repository, e.g.
DIR/gemini-cli). Otherwise each file is fetched once from
raw.githubusercontent.com. Exit status 1 when any link fails.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAT = re.compile(
    r"https://github\.com/([^/\s)]+/[^/\s)]+)/blob/([0-9a-f]{40})/([^\s)#]+)"
    r"(?:#L(\d+)(?:-L(\d+))?)?")


def line_count_local(repos: pathlib.Path, repo: str, sha: str, path: str):
    name = repo.split("/")[1]
    d = repos / name
    if not (d / ".git").exists():
        return None
    head = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    if head != sha:
        return None
    f = d / path
    if not f.is_file():
        return -1
    with open(f, "rb") as fh:
        return sum(1 for _ in fh)


def line_count_remote(repo: str, sha: str, path: str):
    url = "https://raw.githubusercontent.com/%s/%s/%s" % (repo, sha, path)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        return -1 if e.code == 404 else None
    except urllib.error.URLError:
        return None
    return data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repos", type=pathlib.Path, help="directory of local checkouts")
    ap.add_argument("files", nargs="*", type=lambda s: pathlib.Path(s).resolve())
    args = ap.parse_args()
    files = args.files or sorted(
        list((ROOT / "collectors" / "research").glob("*.md"))
        + list((ROOT / "analyzer" / "research").glob("*.md")))
    cache = {}
    total = bad = 0
    for f in files:
        n = 0
        for m in PAT.finditer(f.read_text(encoding="utf-8")):
            repo, sha, path, l1, l2 = m.groups()
            total += 1
            n += 1
            key = (repo, sha, path)
            if key not in cache:
                count = None
                if args.repos:
                    count = line_count_local(args.repos, repo, sha, path)
                if count is None:
                    count = line_count_remote(repo, sha, path)
                cache[key] = count
            count = cache[key]
            rel = f.relative_to(ROOT)
            if count is None:
                print("%s: could not fetch %s@%s/%s" % (rel, repo, sha[:8], path))
                bad += 1
            elif count < 0:
                print("%s: missing file %s@%s/%s" % (rel, repo, sha[:8], path))
                bad += 1
            elif l1:
                lo, hi = int(l1), int(l2 or l1)
                if lo < 1 or hi > count or hi < lo:
                    print("%s: L%s-L%s outside %s (%d lines)" % (rel, l1, l2 or l1, path, count))
                    bad += 1
        if n:
            print("%4d %s" % (n, f.relative_to(ROOT)))
    print("total links %d, problems %d" % (total, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
