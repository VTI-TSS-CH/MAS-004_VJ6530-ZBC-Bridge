from __future__ import annotations

from dataclasses import dataclass
import struct

START = 0xA5
END = 0xE4

FLAG_SQS = 1 << 0
FLAG_FIN = 1 << 1
FLAG_ACK = 1 << 2
FLAG_NAK = 1 << 3
FLAG_CS = 1 << 4


@dataclass(frozen=True)
class Packet:
    flags: int
    size: int
    transaction_id: int
    sequence_id: int
    payload: bytes


def crc16_ccitt(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= (b & 0xFF) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF


def header_checksum(header_without_checksum: bytes) -> int:
    return (~(sum(header_without_checksum) & 0xFF)) & 0xFF


def build_message(message_id: int, body: bytes = b"") -> bytes:
    body = body or b""
    return struct.pack("<HI", message_id & 0xFFFF, 6 + len(body)) + body


def parse_message(payload: bytes) -> tuple[int, bytes]:
    if len(payload) < 6:
        raise ValueError("message too short")
    message_id, length = struct.unpack("<HI", payload[:6])
    if length < 6 or length > len(payload):
        raise ValueError("message length invalid")
    return message_id, payload[6:length]


def build_packet(flags: int, transaction_id: int, sequence_id: int, payload: bytes, checksum: bool = True) -> bytes:
    payload = payload or b""
    if checksum and payload:
        flags |= FLAG_CS
    else:
        flags &= ~FLAG_CS

    size = 10 + len(payload) + (2 if (flags & FLAG_CS) else 0)
    header = struct.pack("<BBHHHB", START, flags & 0xFF, size & 0xFFFF, transaction_id & 0xFFFF, sequence_id & 0xFFFF, END)
    out = bytearray(header)
    out.append(header_checksum(header))
    out.extend(payload)
    if flags & FLAG_CS:
        out.extend(struct.pack("<H", crc16_ccitt(payload)))
    return bytes(out)


def parse_packet(packet: bytes) -> Packet:
    if len(packet) < 10:
        raise ValueError("packet too short")
    start, flags, size, trx, seq, end = struct.unpack("<BBHHHB", packet[:9])
    hcs = packet[9]
    if start != START or end != END:
        raise ValueError("framing invalid")
    if size != len(packet):
        raise ValueError("packet size mismatch")
    if hcs != header_checksum(packet[:9]):
        raise ValueError("header checksum mismatch")

    has_cs = bool(flags & FLAG_CS)
    data = packet[10: len(packet) - (2 if has_cs else 0)]
    if has_cs:
        recv_crc = struct.unpack("<H", packet[-2:])[0]
        if recv_crc != crc16_ccitt(data):
            raise ValueError("payload checksum mismatch")

    return Packet(flags=flags, size=size, transaction_id=trx, sequence_id=seq, payload=data)


def build_ack(ref_packet: Packet) -> bytes:
    flags = (ref_packet.flags & (FLAG_SQS | FLAG_FIN | FLAG_CS)) | FLAG_ACK
    flags &= ~FLAG_NAK
    return build_packet(flags, ref_packet.transaction_id, ref_packet.sequence_id, b"", checksum=False)
