from __future__ import annotations

import socket
import struct
import threading

from .mapper import ZbcMapping, decode_value, encode_value
from .protocol import (
    START,
    FLAG_ACK,
    FLAG_NAK,
    build_ack,
    build_message,
    build_packet,
    parse_message,
    parse_packet,
)


class ZbcBridgeClient:
    """Minimal synchronous ZBC client for Videojet 6530."""

    def __init__(self, host: str, port: int, timeout_s: float = 2.0):
        self.host = (host or "").strip()
        self.port = int(port or 0)
        self.timeout_s = float(timeout_s)
        self._trx = 0
        self._lock = threading.Lock()

    def write(self, mapping: ZbcMapping, value: str) -> tuple[int, bytes]:
        body = struct.pack("<H", mapping.command_id & 0xFFFF) + encode_value(value, mapping.codec, mapping.scale, mapping.offset)
        return self.transact(mapping.message_id, body)

    def read(self, mapping: ZbcMapping) -> str:
        body = struct.pack("<H", mapping.command_id & 0xFFFF)
        msg_id, payload = self.transact(mapping.message_id, body)
        if len(payload) >= 2 and struct.unpack("<H", payload[:2])[0] == (mapping.command_id & 0xFFFF):
            payload = payload[2:]
        return decode_value(payload, mapping.codec, mapping.scale, mapping.offset)

    def transact(self, message_id: int, body: bytes = b"") -> tuple[int, bytes]:
        if not self.host or self.port <= 0:
            raise RuntimeError("host/port not configured")

        with socket.create_connection((self.host, self.port), timeout=self.timeout_s) as sock:
            sock.settimeout(self.timeout_s)
            trx = self._next_trx()

            message = build_message(message_id, body)
            packet = build_packet(flags=0x03, transaction_id=trx, sequence_id=0, payload=message, checksum=True)
            sock.sendall(packet)

            first = self._read_packet(sock)
            if first.flags & FLAG_NAK:
                raise RuntimeError("ZBC transport NAK")

            response = first
            if (first.flags & FLAG_ACK) and not first.payload:
                response = self._read_packet(sock)
            if response.flags & FLAG_NAK:
                raise RuntimeError("ZBC payload NAK")

            if response.payload:
                sock.sendall(build_ack(response))

            return parse_message(response.payload)

    def _next_trx(self) -> int:
        with self._lock:
            self._trx = (self._trx + 1) & 0xFFFF
            return self._trx

    def _read_packet(self, sock: socket.socket):
        start = _recv_exact(sock, 1)
        while start and start[0] != START:
            start = _recv_exact(sock, 1)

        hdr_rest = _recv_exact(sock, 9)
        size = int.from_bytes(hdr_rest[1:3], "little", signed=False)
        remaining = size - 10
        if remaining < 0:
            raise RuntimeError("invalid packet size")
        tail = _recv_exact(sock, remaining) if remaining else b""
        return parse_packet(start + hdr_rest + tail)


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    out = bytearray()
    while len(out) < n:
        chunk = sock.recv(n - len(out))
        if not chunk:
            raise RuntimeError("socket closed")
        out.extend(chunk)
    return bytes(out)
