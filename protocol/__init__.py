"""Giao thức Ứng dụng Tùy chỉnh (Custom Protocol) — Bước 1: Thiết kế Giao thức."""

from .packet import (
    BinaryPacketHeader,
    FLAG_ENCRYPTED_PAYLOAD,
    HEADER_SIZE,
    MAGIC_BYTES,
    OpCode,
)

__all__ = [
    "BinaryPacketHeader",
    "MAGIC_BYTES",
    "HEADER_SIZE",
    "OpCode",
    "FLAG_ENCRYPTED_PAYLOAD",
]
