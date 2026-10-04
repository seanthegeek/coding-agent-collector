"""Minimal protocol buffers wire decoder and encoder driven by hand-written
schemas, so parsers for agents that store protobuf (Antigravity, Windsurf)
need no generated code and no third-party package.

A schema is a dict: message name -> {field number: (field name, kind)} where
kind is one of 'str', 'bytes', 'int', 'bool', 'float', 'double', 'ts'
(google.protobuf.Timestamp, decoded to a UTC string), or another message
name for a nested message. Prefix the field name with '+' for a repeated
field (packed scalars are handled). Unknown fields are skipped, so a schema
only needs the fields a parser reads.
"""

from __future__ import annotations

import struct
from typing import Any

from .timeutil import to_utc

Schema = dict[str, dict[int, tuple[str, str]]]

SCALARS = ("str", "bytes", "int", "bool", "float", "double", "ts")


def read_varint(b: bytes, i: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        if i >= len(b):
            raise ValueError("truncated varint")
        c = b[i]
        i += 1
        result |= (c & 0x7F) << shift
        shift += 7
        if not c & 0x80:
            return result, i
        if shift > 70:
            raise ValueError("varint too long")


def iter_fields(b: bytes):
    """Yield (field_number, wire_type, value) for each field on the wire.
    Length-delimited values are returned as bytes, varints as int, fixed
    widths as raw bytes."""
    i = 0
    n = len(b)
    while i < n:
        tag, i = read_varint(b, i)
        field = tag >> 3
        wt = tag & 7
        if wt == 0:
            v, i = read_varint(b, i)
            yield field, wt, v
        elif wt == 1:
            yield field, wt, b[i : i + 8]
            i += 8
        elif wt == 5:
            yield field, wt, b[i : i + 4]
            i += 4
        elif wt == 2:
            ln, i = read_varint(b, i)
            if ln > n - i:
                raise ValueError("truncated length-delimited field")
            yield field, wt, b[i : i + ln]
            i += ln
        else:
            raise ValueError("unsupported wire type %d" % wt)


def _timestamp(b: bytes) -> str:
    seconds = 0
    nanos = 0
    for f, wt, v in iter_fields(b):
        if f == 1 and wt == 0:
            seconds = v
        elif f == 2 and wt == 0:
            nanos = v
    if not seconds:
        return ""
    return to_utc(seconds + nanos / 1e9)


def _scalar(kind: str, wt: int, v) -> Any:
    if kind == "str":
        return v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v)
    if kind == "bytes":
        return v if isinstance(v, bytes) else b""
    if kind == "int":
        if isinstance(v, bytes):
            return struct.unpack("<q", v)[0] if len(v) == 8 else struct.unpack("<i", v)[0]
        return v
    if kind == "bool":
        return bool(v)
    if kind == "float":
        return struct.unpack("<f", v)[0] if isinstance(v, bytes) and len(v) == 4 else float(v)
    if kind == "double":
        return struct.unpack("<d", v)[0] if isinstance(v, bytes) and len(v) == 8 else float(v)
    if kind == "ts":
        return _timestamp(v) if isinstance(v, bytes) else to_utc(v)
    raise ValueError(kind)


def decode(b: bytes, message: str, schema: Schema) -> dict[str, Any]:
    """Decode bytes as `message` per `schema`. Returns a dict of the fields
    present; repeated fields are lists. Never raises on unknown fields; a
    malformed buffer raises ValueError."""
    fields = schema[message]
    out: dict[str, Any] = {}
    for num, wt, v in iter_fields(b):
        spec = fields.get(num)
        if spec is None:
            continue
        name, kind = spec
        repeated = name.startswith("+")
        if repeated:
            name = name[1:]
        if kind in SCALARS:
            if repeated and kind in ("int", "bool") and wt == 2 and isinstance(v, bytes):
                vals = []
                i = 0
                while i < len(v):
                    x, i = read_varint(v, i)
                    vals.append(bool(x) if kind == "bool" else x)
                out.setdefault(name, []).extend(vals)
                continue
            try:
                val = _scalar(kind, wt, v)
            except (struct.error, ValueError):
                continue
        else:
            if not isinstance(v, bytes):
                continue
            try:
                val = decode(v, kind, schema)
            except ValueError:
                continue
        if repeated:
            out.setdefault(name, []).append(val)
        else:
            out[name] = val
    return out


# ---- encoder, used by the tests to build fixtures -------------------------


def _write_varint(n: int) -> bytes:
    out = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        if n:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _tag(field: int, wt: int) -> bytes:
    return _write_varint((field << 3) | wt)


def _encode_scalar(field: int, kind: str, v) -> bytes:
    if kind == "str":
        data = str(v).encode("utf-8")
        return _tag(field, 2) + _write_varint(len(data)) + data
    if kind == "bytes":
        return _tag(field, 2) + _write_varint(len(v)) + bytes(v)
    if kind in ("int", "bool"):
        return _tag(field, 0) + _write_varint(int(v) & 0xFFFFFFFFFFFFFFFF)
    if kind == "float":
        return _tag(field, 5) + struct.pack("<f", v)
    if kind == "double":
        return _tag(field, 1) + struct.pack("<d", v)
    if kind == "ts":
        # v is epoch seconds (float allowed)
        seconds = int(v)
        nanos = round((v - seconds) * 1e9)
        body = _tag(1, 0) + _write_varint(seconds)
        if nanos:
            body += _tag(2, 0) + _write_varint(nanos)
        return _tag(field, 2) + _write_varint(len(body)) + body
    raise ValueError(kind)


def encode(values: dict[str, Any], message: str, schema: Schema) -> bytes:
    """Encode a dict as `message`. Repeated fields take lists."""
    by_name = {}
    for num, (name, kind) in schema[message].items():
        by_name[name.lstrip("+")] = (num, kind, name.startswith("+"))
    out = bytearray()
    for name, v in values.items():
        num, kind, repeated = by_name[name]
        items = v if repeated else [v]
        for item in items:
            if kind in SCALARS:
                out += _encode_scalar(num, kind, item)
            else:
                body = encode(item, kind, schema)
                out += _tag(num, 2) + _write_varint(len(body)) + body
    return bytes(out)
