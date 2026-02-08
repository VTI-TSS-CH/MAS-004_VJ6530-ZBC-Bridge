from __future__ import annotations

import math
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class ZbcMapping:
    message_id: int
    command_id: int
    codec: str = "u16le"
    scale: float = 1.0
    offset: float = 0.0


def encode_value(value: str, codec: str, scale: float = 1.0, offset: float = 0.0) -> bytes:
    codec = (codec or "u16le").strip().lower()
    if codec == "ascii":
        return (str(value) + "\x00").encode("utf-8")

    f = float(value)
    x = (f - offset) / (scale if abs(scale) > 1e-12 else 1.0)

    if codec in ("u8", "uint8"):
        return struct.pack("<B", int(round(x)))
    if codec in ("u16", "u16le", "uint16"):
        return struct.pack("<H", int(round(x)))
    if codec in ("u32", "u32le", "uint32"):
        return struct.pack("<I", int(round(x)))
    if codec in ("i16", "i16le", "int16"):
        return struct.pack("<h", int(round(x)))
    if codec in ("i32", "i32le", "int32"):
        return struct.pack("<i", int(round(x)))
    if codec in ("f32", "f32le", "float", "float32"):
        return struct.pack("<f", float(x))
    raise ValueError(f"unsupported codec: {codec}")


def decode_value(data: bytes, codec: str, scale: float = 1.0, offset: float = 0.0) -> str:
    codec = (codec or "u16le").strip().lower()
    if codec == "ascii":
        return data.split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()

    if codec in ("u8", "uint8"):
        raw = struct.unpack_from("<B", data, 0)[0]
    elif codec in ("u16", "u16le", "uint16"):
        raw = struct.unpack_from("<H", data, 0)[0]
    elif codec in ("u32", "u32le", "uint32"):
        raw = struct.unpack_from("<I", data, 0)[0]
    elif codec in ("i16", "i16le", "int16"):
        raw = struct.unpack_from("<h", data, 0)[0]
    elif codec in ("i32", "i32le", "int32"):
        raw = struct.unpack_from("<i", data, 0)[0]
    elif codec in ("f32", "f32le", "float", "float32"):
        raw = struct.unpack_from("<f", data, 0)[0]
    else:
        raise ValueError(f"unsupported codec: {codec}")

    val = float(raw) * (scale if abs(scale) > 1e-12 else 1.0) + offset
    if math.isfinite(val) and abs(val - round(val)) < 1e-9:
        return str(int(round(val)))
    return f"{val:.6f}".rstrip("0").rstrip(".")
