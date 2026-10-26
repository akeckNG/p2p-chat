# Protocol Specification — Tracker-Coordinated P2P with TCP Hole Punching

A custom application-layer protocol built on raw TCP and UDP sockets for distributed collaboration. The protocol uses a fixed **12-byte Binary Packet Header** in **Network Byte Order (Big-Endian)**, supporting dual Tracker coordination, NAT traversal via **TCP Hole Punching (Simultaneous TCP Open)**, and direct Peer-to-Peer (P2P) communication.

---

## 1. Binary Packet Header (12 Bytes)

| Offset | Field Name | Size | Type / Format | Value / Meaning |
|:------:|:-----------|:----:|:-------------:|:----------------|
| `0–1` | **Magic Bytes** | 2 bytes | `2s` | `0x4E 0x41` (ASCII `"NA"` for Network Application) |
| `2` | **Version** | 1 byte | `B` (uint8) | Protocol version (`0x01`) |
| `3` | **Opcode / Type**| 1 byte | `B` (uint8) | Message Opcode (see §2) |
| `4–5` | **Flags** | 2 bytes | `H` (uint16) | `0x0001` = `FLAG_ENCRYPTED` (AES-256-GCM payload) |
| `6–9` | **Payload Length**| 4 bytes | `I` (uint32) | Length of following payload in bytes (0 to $2^{32}-1$) |
| `10–11`| **Reserved / Seq** | 2 bytes | `H` (uint16) | Reserved for sequence numbering / packet index |

**Struct format string:** `!2sBBHIH` (Total: exactly 12 bytes).

---

## 2. Protocol Opcodes

### Tracker Control & Rendezvous Channel (TCP Port 9000 & UDP Port 9000)

| Opcode | Hex | Description | Direction |
|:-------|:---:|:------------|:---------:|
| `AUTH_REQ` | `0x01` | Peer registers `{username, local_ip, local_port}` | Peer $\rightarrow$ Tracker |
| `AUTH_RESP` | `0x02` | Tracker confirms registration, returns observed public endpoint `{public_ip, public_port}` and online peer directory | Tracker $\rightarrow$ Peer |
| `PEER_LIST_REQ` | `0x03` | Peer requests full active peer directory | Peer $\rightarrow$ Tracker |
| `PEER_LIST_RESP` | `0x04` | Tracker returns array of peers with private & public endpoints | Tracker $\rightarrow$ Peer |
| `PEER_JOIN_EVENT` | `0x05` | Tracker notifies active peers that a new peer joined | Tracker $\rightarrow$ Peers |
| `PEER_LEAVE_EVENT`| `0x06` | Tracker notifies active peers that a peer left/timed out | Tracker $\rightarrow$ Peers |
| `RENDEZVOUS_REQ` | `0x07` | Peer A asks Tracker to coordinate TCP Hole Punch to Peer B | Peer A $\rightarrow$ Tracker |
| `RENDEZVOUS_OFFER`| `0x08` | Tracker dispatches connection endpoints to both Peer A and Peer B | Tracker $\rightarrow$ Peers A & B |
| `HEARTBEAT` | `0x09` | Periodic UDP presence ping (every 5 seconds) | Peer $\rightarrow$ Tracker |
| `DISCONNECT` | `0x0A` | Graceful peer unregistration | Peer $\rightarrow$ Tracker |

### Direct P2P Channel (TCP Hole-Punched Sockets)

> **Zero server transit**: Neither text chat payloads nor file chunks are routed through the Tracker.

| Opcode | Hex | Description | Direction |
|:-------|:---:|:------------|:---------:|
| `P2P_HANDSHAKE` | `0x10` | Initiates direct P2P link `{sender_username}` | Peer A $\leftrightarrow$ Peer B |
| `P2P_HANDSHAKE_ACK`| `0x11` | Confirms direct P2P link `{status: "OK"}` | Peer B $\leftrightarrow$ Peer A |
| `MSG_DIRECT` | `0x12` | 1-on-1 private chat message | Peer A $\rightarrow$ Peer B |
| `MSG_BROADCAST_P2P`| `0x13` | Mesh broadcast chat message | Peer A $\rightarrow$ All Peers |
| `FILE_INIT` | `0x14` | File metadata `{filename, size, sha256}` | Sender $\rightarrow$ Receiver |
| `FILE_CHUNK` | `0x15` | 64 KB chunk `{seq_id, total_chunks, data}` | Sender $\rightarrow$ Receiver |
| `FILE_ACK` | `0x16` | Chunk confirmation or final transfer integrity verification | Receiver $\rightarrow$ Sender |

---

## 3. TCP Hole Punching Mechanism (RFC 5382 / Simultaneous TCP Open)

1. **Endpoint Discovery**:
   - When a peer connects to the Tracker, the Tracker inspects `sock.getpeername()` to identify the peer's **public (reflexive) endpoint** `(public_ip, public_port)`.
   - The peer also submits its **private local endpoint** `(local_ip, local_port)`.
   - The Tracker records both in the `PeerTable`.

2. **Rendezvous Signaling**:
   - Peer A initiates a direct connection to Peer B by sending `RENDEZVOUS_REQ {target: "bob"}` to the Tracker.
   - The Tracker acts as a STUN/signaling server and sends `RENDEZVOUS_OFFER` simultaneously to both Peer A and Peer B containing each other's public and local endpoints.

3. **Simultaneous TCP Open Execution**:
   - Both peers configure their TCP socket with `SO_REUSEADDR` (and `SO_REUSEPORT` where supported) to bind to their registered local port.
   - Both peers initiate simultaneous `connect()` attempts to each other's endpoints:
     - The outbound SYN punches a dynamic state entry in each peer's local NAT/firewall.
     - When the cross-traffic SYN arrives, the NAT permits it through because it matches an active outbound session.
     - The TCP state machine transitions through **Simultaneous Open (SYN-SENT $\rightarrow$ SYN-RECEIVED $\rightarrow$ ESTABLISHED)**.
   - Once connected, both peers exchange `P2P_HANDSHAKE` and begin streaming direct messages or 64KB file chunks.
