"""
Unit tests for protocol/packet.py
"""

import unittest
import socket
from protocol.packet import (
    BinaryPacketHeader,
    MAGIC_BYTES,
    HEADER_SIZE,
    FLAG_ENCRYPTED_PAYLOAD,
    OpCode,
    send_packet,
    recv_packet,
    recv_exact,
)


class TestBinaryPacketHeader(unittest.TestCase):
    def test_header_size(self):
        self.assertEqual(HEADER_SIZE, 12)

    def test_struct_format(self):
        # Verify round-trip with known values
        hdr = BinaryPacketHeader(
            magic=MAGIC_BYTES,
            version=1,
            opcode=OpCode.AUTH_REQ,
            flags=FLAG_ENCRYPTED_PAYLOAD,
            payload_length=123456,
            seq=42,
        )
        data = hdr.to_bytes()
        self.assertEqual(len(data), HEADER_SIZE)
        hdr2 = BinaryPacketHeader.from_bytes(data)
        self.assertEqual(hdr2.magic, MAGIC_BYTES)
        self.assertEqual(hdr2.version, 1)
        self.assertEqual(hdr2.opcode, OpCode.AUTH_REQ)
        self.assertEqual(hdr2.flags, FLAG_ENCRYPTED_PAYLOAD)
        self.assertEqual(hdr2.payload_length, 123456)
        self.assertEqual(hdr2.seq, 42)

    def test_magic_bytes(self):
        self.assertEqual(MAGIC_BYTES, b'NA')

    def test_roundtrip_zero_payload(self):
        hdr = BinaryPacketHeader(opcode=OpCode.HEARTBEAT, payload_length=0)
        data = hdr.to_bytes()
        hdr2 = BinaryPacketHeader.from_bytes(data)
        self.assertEqual(hdr2.payload_length, 0)

    def test_large_payload_length(self):
        # Payload length up to 4GB
        large_len = 100 * 1024 * 1024  # 100 MB
        hdr = BinaryPacketHeader(payload_length=large_len)
        data = hdr.to_bytes()
        hdr2 = BinaryPacketHeader.from_bytes(data)
        self.assertEqual(hdr2.payload_length, large_len)


class TestSocketHelpers(unittest.TestCase):
    def test_send_recv_small_payload(self):
        s1, s2 = socket.socketpair()
        try:
            payload = b"hello world"
            send_packet(s1, OpCode.MSG_DIRECT, payload, flags=0, seq=7)
            hdr, recv_payload = recv_packet(s2)
            self.assertEqual(hdr.opcode, OpCode.MSG_DIRECT)
            self.assertEqual(hdr.seq, 7)
            self.assertEqual(recv_payload, payload)
        finally:
            s1.close()
            s2.close()

    def test_send_recv_large_payload(self):
        s1, s2 = socket.socketpair()
        try:
            # > 64 KB
            payload = b"A" * (70 * 1024)
            send_packet(s1, OpCode.FILE_CHUNK, payload)
            hdr, recv_payload = recv_packet(s2)
            self.assertEqual(hdr.opcode, OpCode.FILE_CHUNK)
            self.assertEqual(len(recv_payload), len(payload))
            self.assertEqual(recv_payload, payload)
        finally:
            s1.close()
            s2.close()

    def test_recv_exact_fragmentation(self):
        s1, s2 = socket.socketpair()
        try:
            data = b"1234567890"
            # Send in two parts
            s1.sendall(data[:4])
            s1.sendall(data[4:])
            received = recv_exact(s2, len(data))
            self.assertEqual(received, data)
        finally:
            s1.close()
            s2.close()

    def test_flags_encrypted(self):
        s1, s2 = socket.socketpair()
        try:
            payload = b"secret"
            send_packet(s1, OpCode.MSG_DIRECT, payload, flags=FLAG_ENCRYPTED_PAYLOAD)
            hdr, recv_payload = recv_packet(s2)
            self.assertEqual(hdr.flags, FLAG_ENCRYPTED_PAYLOAD)
            self.assertEqual(recv_payload, payload)
        finally:
            s1.close()
            s2.close()


if __name__ == "__main__":
    unittest.main()
