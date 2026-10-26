"""
Custom Protocol — Binary Framing & Header Serialization Module

Implements 12-byte binary packet header with network byte order (Big-Endian)
and framed socket reader/writer helpers for TCP streaming.
"""

from __future__ import annotations

import socket
import struct
from dataclasses import dataclass

# --- Constants ---
MAGIC_BYTES = b'NA'  # 0x4E 0x41
HEADER_SIZE = 12
FLAG_ENCRYPTED_PAYLOAD = 0x0001  # Flags field is 2 bytes

# Struct format: !2sBBHIH
# Magic 2s, Version B, Opcode B, Flags H, Payload Length I, Reserved/Seq H
_HEADER_STRUCT = struct.Struct('!2sBBHIH')


@dataclass
class BinaryPacketHeader:
    """12-byte binary packet header."""

    magic: bytes = MAGIC_BYTES
    version: int = 1
    opcode: int = 0
    flags: int = 0
    payload_length: int = 0
    seq: int = 0  # Reserved / sequence

    def to_bytes(self) -> bytes:
        """Serialize header to 12 bytes."""
        if len(self.magic) != 2:
            raise ValueError("Magic must be 2 bytes")
        return _HEADER_STRUCT.pack(
            self.magic,
            self.version & 0xFF,
            self.opcode & 0xFF,
            self.flags & 0xFFFF,
            self.payload_length & 0xFFFFFFFF,
            self.seq & 0xFFFF,
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "BinaryPacketHeader":
        """Deserialize header from 12 bytes."""
        if len(data) != HEADER_SIZE:
            raise ValueError(
                f"Header must be {HEADER_SIZE} bytes, got {len(data)}"
            )
        magic, version, opcode, flags, payload_length, seq = _HEADER_STRUCT.unpack(data)
        return cls(
            magic=magic,
            version=version,
            opcode=opcode,
            flags=flags,
            payload_length=payload_length,
            seq=seq,
        )


# --- Opcodes ---
class OpCode:
    """Protocol opcodes for Tracker rendezvous and P2P channels."""

    # Tracker control & rendezvous
    AUTH_REQ = 0x01
    AUTH_RESP = 0x02
    PEER_LIST_REQ = 0x03
    PEER_LIST_RESP = 0x04
    PEER_JOIN_EVENT = 0x05
    PEER_LEAVE_EVENT = 0x06
    RENDEZVOUS_REQ = 0x07
    RENDEZVOUS_OFFER = 0x08
    HEARTBEAT = 0x09
    DISCONNECT = 0x0A

    # Direct P2P
    P2P_HANDSHAKE = 0x10
    P2P_HANDSHAKE_ACK = 0x11
    MSG_DIRECT = 0x12
    MSG_BROADCAST_P2P = 0x13
    FILE_INIT = 0x14
    FILE_CHUNK = 0x15
    FILE_ACK = 0x16


# --- Socket helpers ---

def recv_exact(sock: socket.socket, n: int) -> bytes:
    """Receive exactly n bytes from socket, handling fragmentation."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Socket closed before receiving required bytes")
        buf.extend(chunk)
    return bytes(buf)


def send_packet(sock: socket.socket, opcode: int, payload: bytes, flags: int = 0, seq: int = 0, version: int = 1) -> None:
    """Send a framed packet: header + payload."""
    header = BinaryPacketHeader(
        version=version,
        opcode=opcode,
        flags=flags,
        payload_length=len(payload),
        seq=seq,
    )
    sock.sendall(header.to_bytes() + payload)


def recv_packet(sock: socket.socket) -> tuple[BinaryPacketHeader, bytes]:
    """Receive a framed packet, handling TCP fragmentation."""
    header_bytes = recv_exact(sock, HEADER_SIZE)
    header = BinaryPacketHeader.from_bytes(header_bytes)
    payload = recv_exact(sock, header.payload_length) if header.payload_length else b''
    return header, payload
