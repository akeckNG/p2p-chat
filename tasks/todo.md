# Project Todo List: Tracker-Coordinated P2P Collaboration with TCP Hole Punching

## Phase 1: Protocol Design & Framing Foundation (Week 1)

### Task 1: Protocol Design & P2P Specification (with TCP Hole Punching)
**Description:** Define binary packet structure (12-byte header), opcode definitions for Tracker rendezvous and direct P2P data channels, and document sequence diagrams for simultaneous TCP open.
**Acceptance criteria:**
- [x] Define Binary Packet Header layout (12 bytes: Magic `0x4E41`, Version, Opcode, Flags, 32-bit Payload Length, Sequence/Reserved).
- [x] Define Opcodes for Tracker rendezvous (`AUTH_REQ`, `AUTH_RESP`, `PEER_LIST_REQ`, `PEER_LIST_RESP`, `PEER_JOIN_EVENT`, `PEER_LEAVE_EVENT`, `RENDEZVOUS_REQ`, `RENDEZVOUS_OFFER`, `HEARTBEAT`, `DISCONNECT`) and P2P communication (`P2P_HANDSHAKE`, `P2P_HANDSHAKE_ACK`, `MSG_DIRECT`, `MSG_BROADCAST_P2P`, `FILE_INIT`, `FILE_CHUNK`, `FILE_ACK`).
- [x] Document sequence diagrams for Tracker registration, TCP Hole Punching (Simultaneous TCP Open), direct P2P messaging, and P2P chunked file transfer without server relay.
- [x] Update Protocol Specification document (`docs/protocol_spec.md`).
**Verification:**
- [x] Manual check: Review `docs/protocol_spec.md` and `docs/sequence_diagrams.md`.
**Dependencies:** None
**Files likely touched:**
- `docs/protocol_spec.md`
- `docs/sequence_diagrams.md`
**Estimated scope:** Small (2 files)

---

### Task 2: Binary Framing & Header Serialization Module
**Description:** Implement `protocol/packet.py` to pack and unpack the 12-byte binary header with network byte order (Big-Endian `!`), support 32-bit payload lengths up to 4GB, and implement framed socket reader/writer helper functions (`send_packet`, `recv_packet`) to handle TCP streaming fragmentation.
**Acceptance criteria:**
- [x] Header struct format uses `!2sBBHIH` (Magic 2B, Version 1B, Type 1B, Flags 2B, Payload Length 4B, Reserved/Seq 2B = 12 bytes).
- [x] Serialization (`to_bytes`) and deserialization (`from_bytes`) round-trip cleanly without data corruption.
- [x] Implement socket helper `recv_exact(sock, n)` and `recv_packet(sock)` to ensure complete header and payload reads without fragmentation errors.
- [x] Unit tests verify payloads > 64 KB serialize and deserialize correctly.
**Verification:**
- [x] Tests pass: `python3 -m unittest tests/test_packet.py`
**Dependencies:** Task 1
**Files likely touched:**
- `protocol/packet.py`
- `tests/test_packet.py`
**Estimated scope:** Small (2 files)

---

### Task 3: Basic TCP Socket Handshake
**Description:** Build minimal standalone TCP Server and Client scripts to establish connection, exchange a handshake packet, receive an acknowledgment, and terminate cleanly.
**Acceptance criteria:**
- [ ] Server binds to configured host/port (e.g., `0.0.0.0:9000`) using raw Python `socket`.
- [ ] Client connects to Server over TCP and sends an initial connection probe/handshake.
- [ ] Server responds with an ACK packet; Client verifies receipt.
- [ ] Both endpoints close sockets gracefully.
**Verification:**
- [ ] Manual check: Run test script verifying socket connection and clean handshake exchange.
**Dependencies:** Task 2
**Files likely touched:**
- `server/tracker.py`
- `client/tracker_client.py`
- `common/config.py`
**Estimated scope:** Medium (3 files)

---

### Checkpoint: Foundation
- [x] Header and packet serialization tests pass with 64KB+ payloads (fixing 1-byte overflow bug).
- [ ] Basic TCP handshake completes reliably over localhost without socket leaks.

---

## Phase 2: Central Tracker & Rendezvous Signaling (Week 2)

### Task 4: Multi-Threaded Tracker Concurrency Engine
**Description:** Implement multi-threading architecture (`threading.Thread`) on the Tracker where each connecting peer is serviced by a dedicated worker thread, preventing blocking and Tracker crashes on abrupt disconnects.
**Acceptance criteria:**
- [ ] Tracker listens on TCP port 9000 and dispatches incoming connections to dedicated worker threads.
- [ ] Abrupt peer disconnect does not crash the Tracker or impact other connected peers.
- [ ] Tracker handles at least 10–20 concurrent peer connections.
**Verification:**
- [ ] Tests pass: Test script establishing 15 concurrent connections simultaneously.
**Dependencies:** Task 3
**Files likely touched:**
- `server/tracker.py`
- `server/peer_handler.py`
**Estimated scope:** Medium (2 files)

---

### Task 5: Thread-Safe Peer Table with Public/Private Endpoint Discovery
**Description:** Create a thread-safe `PeerTable` on the Tracker storing active peer records: username, detected public endpoint `(public_ip, public_port)` from `sock.getpeername()`, local endpoint `(local_ip, local_port)`, socket handle, registration time, and last heartbeat timestamp.
**Acceptance criteria:**
- [ ] `PeerTable` stores both public (reflexive) and private local endpoints for each peer.
- [ ] Supports register, unregister, find by username, and get all active peers.
- [ ] All read/write operations are protected by `threading.RLock`.
- [ ] Rejects duplicate usernames with an appropriate error response.
**Verification:**
- [ ] Tests pass: Concurrent multi-threaded registration and lookup unit tests.
**Dependencies:** Task 4
**Files likely touched:**
- `server/peer_table.py`
- `tests/test_peer_table.py`
**Estimated scope:** Small (2 files)

---

### Task 6: Peer Registration & Rendezvous Signaling Flow
**Description:** Implement peer registration via `AUTH_REQ` and the TCP Hole Punching rendezvous signaling (`RENDEZVOUS_REQ` and `RENDEZVOUS_OFFER`). Tracker acts as signaling broker, coordinating connection offers to both target peers simultaneously.
**Acceptance criteria:**
- [ ] Peer sends `AUTH_REQ` with its username and local interface endpoint.
- [ ] Tracker confirms registration and returns detected public endpoint in `AUTH_RESP`.
- [ ] Peer A sends `RENDEZVOUS_REQ {target: "bob"}` when it wants to initiate P2P communication.
- [ ] Tracker dispatches `RENDEZVOUS_OFFER` to both Peer A and Peer B with each other's public and local endpoints.
**Verification:**
- [ ] Manual check: Start Tracker, connect two peers; issue rendezvous request and observe offer packets delivered to both peers.
**Dependencies:** Task 5
**Files likely touched:**
- `server/peer_handler.py`
- `client/tracker_client.py`
- `protocol/packet.py`
**Estimated scope:** Medium (3 files)

---

### Checkpoint: Tracker & Rendezvous
- [ ] Tracker correctly detects reflexive public endpoints and dispatches dual rendezvous offers.
- [ ] Tracker performs purely discovery/signaling coordination with zero message or file traffic.

---

## Phase 3: TCP Hole Punching & Direct P2P Channels (Week 3)

### Task 7: TCP Hole Punching Engine (Simultaneous TCP Open)
**Description:** Implement TCP Hole Punching routine using `SO_REUSEADDR` / `SO_REUSEPORT`. Upon receiving a `RENDEZVOUS_OFFER`, both peers initiate simultaneous outbound TCP connections to each other's endpoints, completing simultaneous open without third-party relays.
**Acceptance criteria:**
- [ ] Sockets configured with `SO_REUSEADDR` to bind to the peer's designated port.
- [ ] Initiates non-blocking simultaneous `connect()` attempts to target peer's public and local endpoints.
- [ ] Completes TCP handshake (Simultaneous Open) and establishes direct peer socket.
- [ ] Exchanges `P2P_HANDSHAKE` / `P2P_HANDSHAKE_ACK` to confirm peer identity.
**Verification:**
- [ ] Tests pass: Unit test running hole punching routine between two peers on distinct ports.
**Dependencies:** Task 2, Task 6
**Files likely touched:**
- `client/tcp_puncher.py`
- `client/p2p_session.py`
**Estimated scope:** Medium (2 files)

---

### Task 8: Direct P2P Text Messaging (Unicast & Mesh Broadcast)
**Description:** Implement direct peer-to-peer text messaging over the established hole-punched TCP connections. Unicast messages (`/msg`) transmit directly to target peer. Broadcast messages (`/broadcast`) deliver directly to each active peer (Mesh broadcast).
**Acceptance criteria:**
- [ ] Direct message (`MSG_DIRECT`) connects directly to recipient peer socket without sending data to Tracker.
- [ ] Broadcast message (`MSG_BROADCAST_P2P`) delivers directly to each online peer.
- [ ] All message packets contain sender username, timestamp, and message body.
**Verification:**
- [ ] Manual check: Send unicast and broadcast messages between peers; verify Tracker port 9000 sees zero message traffic.
**Dependencies:** Task 7
**Files likely touched:**
- `client/p2p_session.py`
- `client/peer_handler.py`
- `client/cli.py`
**Estimated scope:** Medium (3 files)

---

### Task 9: Direct P2P 64KB Chunked File Transfer & Integrity Verification
**Description:** Implement direct peer-to-peer file transfer over hole-punched TCP sockets. Sender slices file into 64KB chunks, sends metadata packet (`FILE_INIT`), streams sequential `FILE_CHUNK` packets directly to recipient socket, and receiver reassembles and verifies SHA-256 hash before issuing `FILE_ACK`.
**Acceptance criteria:**
- [ ] Sender connects directly to recipient peer socket, sends `FILE_INIT` (filename, size, SHA-256 hash).
- [ ] Sender streams 64 KB `FILE_CHUNK` packets directly over TCP.
- [ ] Receiver reassembles chunks, calculates SHA-256 digest, and compares against metadata.
- [ ] Receiver sends `FILE_ACK` with verification status; if hash matches, file is saved to download directory.
- [ ] Zero file chunks pass through Tracker.
**Verification:**
- [ ] Manual check: Transfer 20MB+ file directly between two hole-punched peers; confirm SHA-256 matches and Tracker network traffic remains zero.
**Dependencies:** Task 7, Task 8
**Files likely touched:**
- `client/file_transfer.py`
- `client/peer_handler.py`
- `tests/test_p2p_transfer.py`
**Estimated scope:** Medium (3 files)

---

### Checkpoint: Direct P2P Data Channels
- [ ] Direct TCP hole punching successfully connects peers without relay servers.
- [ ] Unicast/broadcast text messages and 64KB chunked file transfers stream directly between peers and verify data integrity via SHA-256.

---

## Phase 4: Network Resilience & Security (Week 4)

### Task 10: Socket Error Handling & Graceful Teardown
**Description:** Implement socket timeouts, catch network exceptions (`BrokenPipeError`, `ConnectionResetError`, `TimeoutError`), and handle `SIGINT`/`SIGTERM` to send `DISCONNECT` to Tracker and gracefully close peer sockets.
**Acceptance criteria:**
- [ ] Sockets configured with non-blocking checks or timeouts (`socket.settimeout`).
- [ ] Sudden peer termination handled cleanly without crashing Tracker or other peers.
- [ ] Capturing `Ctrl+C` sends `DISCONNECT` to Tracker, notifies active P2P peers, and closes local sockets.
**Verification:**
- [ ] Manual check: Kill peer with `kill -9`; verify Tracker updates peer table and notifies remaining peers.
**Dependencies:** Task 4, Task 7
**Files likely touched:**
- `server/peer_handler.py`
- `client/tracker_client.py`
- `client/tcp_puncher.py`
**Estimated scope:** Small (3 files)

---

### Task 11: UDP Heartbeat & Tracker Inactivity Watchdog
**Description:** Implement periodic UDP heartbeats sent from each peer to Tracker every 5s. Tracker runs a watchdog thread that automatically evicts peers silent for > 15s and broadcasts `PEER_LEAVE_EVENT`.
**Acceptance criteria:**
- [ ] Peer runs background thread transmitting UDP datagrams (`HEARTBEAT` opcode + username) to Tracker every 5 seconds.
- [ ] Tracker UDP listener receives heartbeat and updates peer `last_heartbeat` timestamp in `PeerTable`.
- [ ] Tracker watchdog checks every 3 seconds; cleans up sessions inactive for > 15s and emits `PEER_LEAVE_EVENT`.
**Verification:**
- [ ] Manual check: Suspend peer (`kill -STOP <pid>`); verify Tracker evicts peer after 15 seconds.
**Dependencies:** Task 5, Task 10
**Files likely touched:**
- `server/heartbeat_watchdog.py`
- `client/heartbeat_sender.py`
**Estimated scope:** Small (2 files)

---

### Task 12: Symmetric Payload Encryption Layer (AES-256-GCM)
**Description:** Implement symmetric authenticated encryption using AES-256-GCM from the `cryptography` library. Direct P2P message and file payloads are encrypted with IV/Nonce prepended, header flag `FLAG_ENCRYPTED` set, and GCM tag authenticated on receipt.
**Acceptance criteria:**
- [ ] `SecurityManager` provides `encrypt(payload: bytes) -> bytes` and `decrypt(data: bytes) -> bytes` using AES-256-GCM.
- [ ] Packet header sets `FLAG_ENCRYPTED` (0x0001) whenever payload is encrypted.
- [ ] Receiving peer authenticates GCM tag; raises error if ciphertext has been modified in transit.
- [ ] Direct messages and file payloads are encrypted over the wire.
**Verification:**
- [ ] Tests pass: Unit test encrypting, decrypting, and detecting tampered payloads.
**Dependencies:** Task 2, Task 8
**Files likely touched:**
- `common/security.py`
- `protocol/packet.py`
- `tests/test_security.py`
**Estimated scope:** Small (3 files)

---

### Checkpoint: Resilience & Security
- [ ] Inactive peers evicted automatically via UDP watchdog.
- [ ] All P2P message and file wire traffic encrypted with AES-256-GCM.

---

## Phase 5: Interactive CLI Interface (Week 5)

### Task 13: Asynchronous CLI Client Architecture
**Description:** Build asynchronous CLI interface for peers. Background listener prints incoming P2P messages and presence notifications cleanly, while foreground prompt accepts slash commands.
**Acceptance criteria:**
- [ ] Implement command suite:
  - `/users` – Display live peers discovered from Tracker.
  - `/msg <username> <text>` – Send direct P2P message (establishing TCP hole punch if not already open).
  - `/broadcast <text>` – Send P2P broadcast message to all online peers.
  - `/sendfile <username> <filepath>` – Send file directly to peer.
  - `/help` – Show available commands.
  - `/quit` – Disconnect and exit cleanly.
- [ ] Incoming messages do not disrupt the active command prompt line.
**Verification:**
- [ ] Manual check: Execute all slash commands in CLI; verify correct behavior and clean prompt formatting.
**Dependencies:** Task 8, Task 9
**Files likely touched:**
- `client/cli.py`
- `client/main.py`
**Estimated scope:** Medium (2 files)

---

### Task 14: Visual File Transfer Progress Bar
**Description:** Implement live terminal progress bar for outgoing and incoming P2P chunked file transfers, displaying transfer percentage, speed (KB/s or MB/s), and estimated time remaining (ETA).
**Acceptance criteria:**
- [ ] Progress bar updates dynamically during `FILE_CHUNK` streaming.
- [ ] Calculates rolling transfer speed and remaining ETA.
- [ ] Displays final confirmation with elapsed time and verified SHA-256 checksum.
**Verification:**
- [ ] Manual check: Send 30MB+ file directly between two peers; verify progress bar renders smoothly.
**Dependencies:** Task 9, Task 13
**Files likely touched:**
- `client/ui_progress.py`
- `client/file_transfer.py`
**Estimated scope:** Small (2 files)

---

### Checkpoint: User Interface & Experience
- [ ] Complete collaboration CLI operates smoothly with all slash commands.
- [ ] P2P file transfers show live progress bars and verify data integrity on completion.

---

## Phase 6: Testing, Refactoring & Project Delivery (Week 6)

### Task 15: Concurrency Simulation & Stress Testing
**Description:** Run automated simulation with 10–20 concurrent peer processes communicating simultaneously through Tracker discovery, TCP hole-punched direct connections, and P2P messaging/file transfers.
**Acceptance criteria:**
- [ ] Automated script spawns Tracker and 15+ mock peers performing concurrent logins, P2P chats, and file transfers.
- [ ] Zero Tracker crashes, zero unhandled thread exceptions, and no data corruption.
**Verification:**
- [ ] Run test: `python3 tests/stress_test.py`
**Dependencies:** Task 4, Task 7, Task 9, Task 11
**Files likely touched:**
- `tests/stress_test.py`
**Estimated scope:** Medium (1-2 files)

---

### Task 16: Code Cleanup, Typing, Comments & Documentation
**Description:** Refactor codebase for clean PEP8 compliance, complete type hints, comprehensive docstrings, and author a detailed `README.md` with installation and execution instructions.
**Acceptance criteria:**
- [ ] Code passes PEP8 styling (`flake8` / `black` / `ruff`).
- [ ] `README.md` includes: Architecture diagram, prerequisites, installation steps, how to run Tracker and Peers, command guide, and test commands.
**Verification:**
- [ ] Manual check: Follow `README.md` instructions from a clean environment and verify everything runs cleanly.
**Dependencies:** All previous tasks
**Files likely touched:**
- `README.md`
- Entire codebase refactor
**Estimated scope:** Medium (3+ files)

---

### Task 17: Technical Explanation Report (PDF Deliverable)
**Description:** Author the required 4-part Technical Explanation Report PDF: System Architecture Diagram, Protocol Specification, Sequence Diagrams, and 1-page Challenges & Solutions Reflection covering TCP Hole Punching and NAT traversal.
**Acceptance criteria:**
- [ ] Section 1: High-level System Architecture Diagram explaining Tracker vs P2P interactions over TCP and UDP.
- [ ] Section 2: Complete Protocol Specification detailing 12-byte header, opcode listing, and payload framing.
- [ ] Section 3: Sequence diagrams illustrating Registration, TCP Hole Punching (Simultaneous Open), Direct Messaging, and Direct P2P File Transfer.
- [ ] Section 4: 1-page reflection on network challenges faced (TCP hole punching NAT state transitions, socket reuse with `SO_REUSEADDR`, race conditions) and solutions implemented.
**Verification:**
- [ ] Manual check: Review compiled Technical Report PDF against Assignment 1 submission criteria.
**Dependencies:** Task 1, Task 16
**Files likely touched:**
- `docs/report.md`
- `docs/report.pdf`
**Estimated scope:** Small (2 files)

---

### Final Project Checkpoint
- [ ] All 10 development rubric milestones (1 pt each = 10/10) fully implemented and verified under Tracker P2P architecture with TCP Hole Punching.
- [ ] Clean git commit history and packaged submission ready for delivery.
