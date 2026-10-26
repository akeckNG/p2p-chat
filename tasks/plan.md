# Implementation Plan: Distributed Tracker-Coordinated P2P Collaboration with TCP Hole Punching

## Overview
This project develops a resilient, distributed Peer-to-Peer (P2P) Collaboration Application in Python using raw sockets (`socket` library) over TCP and UDP. The system employs a **Hybrid Tracker-P2P Architecture with NAT Traversal via TCP Hole Punching (RFC 5382 Simultaneous TCP Open)**:
- The **Central Server acts strictly as a Tracker & STUN/Rendezvous Coordinator**: It records peers' private and public (reflexive) endpoints, coordinates TCP hole-punching rendezvous requests (`RENDEZVOUS_REQ` / `RENDEZVOUS_OFFER`), and monitors peer liveness via UDP heartbeats. **No text chat messages or file chunks pass through the server**.
- **Peers establish direct P2P connections using TCP Hole Punching**: Using `SO_REUSEADDR` / `SO_REUSEPORT` on bound sockets, peers perform simultaneous outbound TCP connects to punch holes in NAT state tables. Direct messaging (`/msg`), mesh broadcast (`/broadcast`), and 64KB chunked file transfers (`/sendfile` with SHA-256 verification and progress bars) are executed directly peer-to-peer.
- Wire traffic employs a custom 12-byte binary packet header with 32-bit payload lengths in Network Byte Order (Big-Endian) and authenticated AES-256-GCM payload encryption.

---

## Architecture Decisions & Standards

1. **Protocol Framing & Header Layout**:
   - **Network Byte Order**: Big-Endian (`!`) for all wire formats.
   - **Header Size**: Exactly 12 bytes (`!2sBBHIH`):
     - Magic Bytes (2 bytes): `0x4E 0x41` (ASCII "NA").
     - Version (1 byte): `0x01`.
     - Type / Opcode (1 byte): `AUTH_REQ (0x01)`, `RENDEZVOUS_REQ (0x07)`, `RENDEZVOUS_OFFER (0x08)`, `MSG_DIRECT (0x12)`, `FILE_CHUNK (0x15)`, etc.
     - Flags (2 bytes): Bitfield including `FLAG_ENCRYPTED (0x0001)`.
     - Payload Length (4 bytes, `!I`): Allows payloads up to 4 GB (crucial for 64 KB+ file chunks).
     - Reserved / Sequence (2 bytes, `!H`): Reserved or sequence numbering.

2. **TCP Hole Punching Architecture (RFC 5382)**:
   - **Reflexive Endpoint Discovery**: When a peer connects to the Tracker, the Tracker inspects `sock.getpeername()` to capture the peer's observed public endpoint `(public_ip, public_port)`. The peer also reports its local interface endpoint `(local_ip, local_port)`.
   - **Rendezvous Signaling**: When Peer A initiates contact with Peer B, Peer A sends `RENDEZVOUS_REQ` to the Tracker. The Tracker immediately sends `RENDEZVOUS_OFFER` to both Peer A and Peer B with each other's public and local endpoints.
   - **Simultaneous TCP Open Execution**:
     - Both peers configure a TCP socket with `SO_REUSEADDR` (and `SO_REUSEPORT` where supported).
     - Both peers initiate non-blocking simultaneous `connect()` attempts to each other's public and local endpoints.
     - The outbound SYN packets punch through each peer's NAT. The inbound SYN packets match the open state entry, completing the simultaneous TCP handshake.
   - **LAN / Localhost Optimization**: Attempt local endpoint connection first; if local fails or peers are on distinct subnets, fall back seamlessly to public hole-punched endpoint.

3. **Routing Model**:
   - **Unicast Messaging (`/msg <user> <text>`)**: Direct TCP hole-punched connection from sender peer to recipient peer. Zero server transit.
   - **Mesh Broadcast Messaging (`/broadcast <text>`)**: Direct peer-to-peer delivery to all active peers in the directory. Zero server transit.
   - **Chunked File Transfer (`/sendfile <user> <file>`)**: Direct peer-to-peer transmission of `FILE_INIT` (metadata & SHA-256) and 64 KB `FILE_CHUNK` packets, acknowledged by direct `FILE_ACK`. Zero server transit.

4. **Security Model**:
   - Symmetric authenticated encryption: AES-256-GCM (`cryptography.hazmat.primitives.ciphers.aead.AESGCM`).
   - 12-byte Nonce/IV prepended to ciphertext; GCM authentication tag validated upon receipt.

---

## Phased Task Roadmap

### Phase 1: Custom Protocol & Framing Foundation (Week 1)
- [x] **Task 1: Protocol Design & P2P Specification**: Define 12-byte binary header, opcodes for Tracker rendezvous and direct P2P data channels, and document sequence diagrams for TCP hole punching.
- [ ] **Task 2: Binary Framing & Header Serializer**: Implement `protocol/packet.py` with big-endian 12-byte header struct (`!2sBBHIH`), 32-bit length, socket stream helpers (`send_packet`, `recv_packet`), and unit tests.
- [ ] **Task 3: Basic TCP Socket Handshake**: Build minimal TCP client and server scripts verifying reliable connection, handshake packet exchange, and clean teardown.

#### Checkpoint: Foundation
- [ ] Unit tests for `protocol/packet.py` pass with payloads > 64 KB.
- [ ] Handshake verified over raw TCP socket with zero framing errors.

---

### Phase 2: Central Tracker & Rendezvous Signaling (Week 2)
- [ ] **Task 4: Multi-Threaded Tracker Engine**: Build Tracker TCP server (Port 9000) using thread-per-peer architecture to service 10–20 concurrent peers.
- [ ] **Task 5: Thread-Safe Peer Table with Endpoint Discovery**: Implement `PeerTable` on Tracker storing `(username, public_ip, public_port, local_ip, local_port, socket, last_heartbeat)`. Protect with `threading.RLock`.
- [ ] **Task 6: Peer Registration & Rendezvous Broker**: Implement `AUTH_REQ` / `AUTH_RESP` returning detected public endpoint, and implement `RENDEZVOUS_REQ` / `RENDEZVOUS_OFFER` signaling flow.

#### Checkpoint: Tracker & Rendezvous
- [ ] 10 concurrent peers register with Tracker and receive verified public and private endpoints.
- [ ] Tracker successfully dispatches coordinated rendezvous offers to pairs of peers on demand.

---

### Phase 3: TCP Hole Punching & Direct P2P Channels (Week 3)
- [ ] **Task 7: TCP Hole Punching Engine**: Implement simultaneous TCP open routine with `SO_REUSEADDR`, port binding, concurrent connection attempts to public/local endpoints, and `P2P_HANDSHAKE`.
- [ ] **Task 8: Direct P2P Text Messaging (Unicast & Mesh Broadcast)**: Implement `/msg` (direct hole-punched P2P connection) and `/broadcast` (direct delivery across active peers). Verify zero Tracker transit.
- [ ] **Task 9: Direct P2P 64KB Chunked File Transfer**: Implement sender chunking (64KB), `FILE_INIT` (metadata + SHA-256), sequential `FILE_CHUNK` streaming, receiver reassembly, SHA-256 verification, and `FILE_ACK`.

#### Checkpoint: Direct P2P Data Channels
- [ ] Two peers successfully establish direct TCP connection via hole punching / simultaneous open.
- [ ] Text messages and 50MB+ file chunks stream directly between peers with zero bytes passing through Tracker port 9000.

---

### Phase 4: Network Resilience & Security (Week 4)
- [ ] **Task 10: Socket Error Handling & Graceful Teardown**: Implement timeouts (`socket.settimeout`), catch socket exceptions (`BrokenPipeError`, `ConnectionResetError`), trap `SIGINT`/`SIGTERM` to send `DISCONNECT` and close sockets.
- [ ] **Task 11: UDP Heartbeat & Tracker Inactivity Watchdog**: Client sends periodic UDP heartbeat to Tracker every 5s; Tracker watchdog evicts inactive peers after 15s and broadcasts `PEER_LEAVE_EVENT`.
- [ ] **Task 12: AES-256-GCM Payload Encryption Layer**: Implement payload encryption/decryption with AES-256-GCM, set `FLAG_ENCRYPTED` in header, and authenticate tag on peer receipt.

#### Checkpoint: Resilience & Security
- [ ] Abruptly killing a peer (`kill -9`) triggers Tracker UDP timeout eviction after 15 seconds.
- [ ] Wire packets are encrypted; tampered payloads are rejected by GCM tag validation.

---

### Phase 5: Interactive CLI Interface (Week 5)
- [ ] **Task 13: Asynchronous CLI Client**: Dual-thread CLI with background message/event receiver and foreground user prompt for commands (`/users`, `/msg`, `/broadcast`, `/sendfile`, `/help`, `/quit`).
- [ ] **Task 14: Dynamic File Transfer Progress Bar**: Live terminal progress bar displaying transfer speed (KB/s), percentage (%), and ETA during P2P file uploads and downloads.

#### Checkpoint: User Interface
- [ ] Incoming P2P messages do not collide with active command input prompt.
- [ ] File transfer progress bar renders smoothly and completes with verified checksum.

---

### Phase 6: Testing, Refactoring & Project Delivery (Week 6)
- [ ] **Task 15: Concurrency Simulation & Hole Punching Stress Testing**: Script running 10–20 concurrent peer instances testing concurrent rendezvous and direct P2P data exchange.
- [ ] **Task 16: Code Quality, PEP8 & README**: Code refactor, full type hints, docstrings, and comprehensive `README.md` with execution guide.
- [ ] **Task 17: Technical Explanation Report (PDF)**: Compile the 4-part Technical Report (Architecture Diagram, Protocol Specification, Sequence Diagrams, Challenges & Solutions covering TCP Hole Punching).

#### Checkpoint: Final Acceptance
- [ ] All 10 development rubric milestones (1 pt each = 10/10) fully implemented and verified under Tracker P2P architecture with TCP Hole Punching.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Symmetric NAT Failure in TCP Hole Punching | High | Detect NAT type; bind local port using `SO_REUSEADDR`/`SO_REUSEPORT`; attempt both reflexive and local endpoints concurrently. |
| Timing Desynchronization in Simultaneous Open | Medium | Tracker coordinates rendezvous offer with immediate initiation from both sides plus connection retry loops. |
| TCP Stream Fragmentation & Concatenation | High | Strict 12-byte header with 4-byte payload length; loop `recv()` until complete packet payload is read. |
| Payload Length Overflow (>255B) | Critical | Use 4-byte unsigned integer (`!I`) for `payload_length` instead of 1-byte char (`B`). |
| Port Conflict on Multi-Peer Localhost | Medium | Support `--local-port` configuration or bind to ephemeral port; use `SO_REUSEADDR`. |
| UDP Heartbeat Mapping | Medium | Embed `username` in UDP heartbeat payload so Tracker maps datagram to the correct peer session. |
