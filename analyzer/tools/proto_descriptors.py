#!/usr/bin/env python3
"""Extract protobuf message definitions from a binary that embeds its file
descriptors (Go binaries built with protobuf-go, among others), and query them.

Closed-source agents such as Antigravity CLI store transcripts as protobuf
blobs with no published schema. The shipped binary still carries the
serialized FileDescriptorProto for every message it links, which gives field
names, numbers, types and enum values. This is the evidence source for
`agent_analyzer/parsers/antigravity.py`; re-run it when a new release changes
the format.

    tools/proto_descriptors.py extract ~/.local/bin/agy descriptors.json
    tools/proto_descriptors.py show descriptors.json gemini_coder.Step exa.cortex_pb.CortexStepType
    tools/proto_descriptors.py find descriptors.json Summary

Standard library only. Extraction scans for `<name>.proto` strings preceded
by a field-1 length prefix and parses forward until the data stops looking
like a FileDescriptorProto, so it needs no knowledge of the binary's layout.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_analyzer.protobuf import iter_fields, read_varint

TYPES = {
    1: "double",
    2: "float",
    3: "int64",
    4: "uint64",
    5: "int32",
    6: "fixed64",
    7: "fixed32",
    8: "bool",
    9: "string",
    10: "group",
    11: "message",
    12: "bytes",
    13: "uint32",
    14: "enum",
    15: "sfixed32",
    16: "sfixed64",
    17: "sint32",
    18: "sint64",
}


def _s(x: bytes) -> str:
    return x.decode("utf-8", "replace")


def parse_enum(b: bytes) -> dict:
    e = {"name": "", "values": {}}
    for f, _wt, v in iter_fields(b):
        if f == 1:
            e["name"] = _s(v)
        elif f == 2:
            name, num = "", None
            for ff, _, vv in iter_fields(v):
                if ff == 1:
                    name = _s(vv)
                elif ff == 2:
                    num = vv
            e["values"][str(num)] = name
    return e


def parse_message(b: bytes) -> dict:
    m = {"name": "", "fields": [], "nested": [], "enums": [], "oneofs": []}
    for f, _wt, v in iter_fields(b):
        if f == 1:
            m["name"] = _s(v)
        elif f == 2:
            fd = {}
            for ff, _, vv in iter_fields(v):
                if ff == 1:
                    fd["name"] = _s(vv)
                elif ff == 3:
                    fd["number"] = vv
                elif ff == 4:
                    fd["label"] = vv
                elif ff == 5:
                    fd["type"] = vv
                elif ff == 6:
                    fd["type_name"] = _s(vv)
                elif ff == 9:
                    fd["oneof_index"] = vv
            m["fields"].append(fd)
        elif f == 3:
            m["nested"].append(parse_message(v))
        elif f == 4:
            m["enums"].append(parse_enum(v))
        elif f == 8:
            for ff, _, vv in iter_fields(v):
                if ff == 1:
                    m["oneofs"].append(_s(vv))
    return m


def parse_file_fields(data: bytes, start: int):
    """Parse FileDescriptorProto fields from `start` until the stream stops
    looking like one (a field outside 1..13 or a second `name`)."""
    i, n = start, len(data)
    seen_name = False
    fields = []
    while i < n:
        try:
            tag, j = read_varint(data, i)
        except ValueError:
            break
        f, wt = tag >> 3, tag & 7
        if f < 1 or f > 13 or wt not in (0, 2):
            break
        if f == 1 and seen_name:
            break
        if wt == 0:
            v, j = read_varint(data, j)
            fields.append((f, v))
            i = j
            continue
        try:
            ln, j = read_varint(data, j)
        except ValueError:
            break
        if ln > n - j or ln > 50_000_000:
            break
        chunk = data[j : j + ln]
        if f == 1:
            if not chunk.endswith(b".proto"):
                break
            seen_name = True
        fields.append((f, chunk))
        i = j + ln
    return fields


def extract(binary: Path) -> dict:
    data = binary.read_bytes()
    results: dict = {}
    for m in re.finditer(rb"\.proto", data):
        end = m.end()
        for back in range(7, 200):
            st = end - back
            if st < 2 or not re.fullmatch(rb"[A-Za-z0-9_./\-]+", data[st:end]):
                break
            for lb in (1, 2):
                ls = st - lb
                if ls < 1:
                    continue
                try:
                    ln, _ = read_varint(data, ls)
                except ValueError:
                    continue
                if ln != end - st or data[ls - 1] != 0x0A:
                    continue
                fields = parse_file_fields(data, ls - 1)
                if not any(f == 4 for f, _ in fields):
                    continue
                fd = {"name": "", "package": "", "messages": [], "enums": []}
                try:
                    for f, v in fields:
                        if f == 1:
                            fd["name"] = _s(v)
                        elif f == 2:
                            fd["package"] = _s(v)
                        elif f == 4:
                            fd["messages"].append(parse_message(v))
                        elif f == 5:
                            fd["enums"].append(parse_enum(v))
                except ValueError:
                    continue
                key = fd["name"]
                if key not in results or len(json.dumps(fd)) > len(json.dumps(results[key])):
                    results[key] = fd
    return results


def build_index(desc: dict) -> dict:
    index = {}

    def walk(prefix, m, fname):
        full = prefix + m["name"]
        index[full] = ("msg", m, fname)
        for n in m["nested"]:
            walk(full + ".", n, fname)
        for e in m["enums"]:
            index[full + "." + e["name"]] = ("enum", e, fname)

    for fname, fd in desc.items():
        pkg = fd["package"] + "." if fd["package"] else ""
        for m in fd["messages"]:
            walk(pkg, m, fname)
        for e in fd["enums"]:
            index[pkg + e["name"]] = ("enum", e, fname)
    return index


def show(index: dict, name: str) -> None:
    kind, obj, fname = index[name]
    if kind == "enum":
        print("enum %s  [%s]" % (name, fname))
        for num, nm in sorted(obj["values"].items(), key=lambda x: int(x[0])):
            print("  %s = %s" % (num, nm))
        return
    print("message %s  [%s]" % (name, fname))
    for f in sorted(obj["fields"], key=lambda f: f.get("number", 0)):
        label = {3: "repeated "}.get(f.get("label"), "")
        tn = f.get("type_name", "").lstrip(".") or TYPES.get(f.get("type"), "?")
        oo = " oneof#%d" % f["oneof_index"] if "oneof_index" in f else ""
        print("  %4d %s%s: %s%s" % (f.get("number", 0), label, f.get("name"), tn, oo))
    if obj["oneofs"]:
        print("  oneofs: %s" % obj["oneofs"])


def main(argv) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd = argv[1]
    if cmd == "extract":
        desc = extract(Path(argv[2]))
        Path(argv[3]).write_text(json.dumps(desc))
        print("%d descriptor files" % len(desc))
        return 0
    desc = json.loads(Path(argv[2]).read_text())
    index = build_index(desc)
    if cmd == "show":
        for name in argv[3:]:
            if name in index:
                show(index, name)
            else:
                print("not found: %s" % name)
            print()
        return 0
    if cmd == "find":
        q = argv[3].lower()
        for k in sorted(index):
            if q in k.lower():
                print(k)
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
