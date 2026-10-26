# Sequence Diagrams — Tracker-Coordinated P2P with TCP Hole Punching

Visual sequence flows for Tracker registration, NAT traversal via TCP Hole Punching, direct P2P text messaging, and direct P2P chunked file transfer.

---

## 1. Tracker Registration & Endpoint Discovery

```mermaid
sequenceDiagram
    autonumber
    actor Alice as Peer Alice (Private: 192.168.1.10:9101)
    participant NAT_A as Alice's NAT
    participant T as Central Tracker (Port: 9000)
    participant NAT_B as Bob's NAT
    actor Bob as Peer Bob (Private: 10.0.0.5:9102)

    Alice->>NAT_A: TCP Connect (Tracker 9000)
    NAT_A->>T: Outbound mapping created (Alice Public: 203.0.113.1:45123)
    Alice->>T: AUTH_REQ {"username": "alice", "local_ip": "192.168.1.10", "local_port": 9101}
    T->>T: Detect public endpoint from socket (203.0.113.1:45123)
    T-->>Alice: AUTH_RESP {"status": "OK", "public_ip": "203.0.113.1", "public_port": 45123}

    loop Every 5 seconds
        Alice->>T: HEARTBEAT (UDP datagram)
    end
```

---

## 2. TCP Hole Punching Flow (Simultaneous TCP Open)

```mermaid
sequenceDiagram
    autonumber
    actor Alice as Peer Alice
    participant NAT_A as Alice's NAT
    participant T as Central Tracker
    participant NAT_B as Bob's NAT
    actor Bob as Peer Bob

    Alice->>T: RENDEZVOUS_REQ {"target": "bob"}
    T->>T: Look up Bob's public & private endpoints
    par Signal Alice and Bob
        T-->>Alice: RENDEZVOUS_OFFER {"peer": "bob", "public": "198.51.100.2:58102", "local": "10.0.0.5:9102"}
        T-->>Bob: RENDEZVOUS_OFFER {"peer": "alice", "public": "203.0.113.1:45123", "local": "192.168.1.10:9101"}
    end

    Note over Alice,Bob: Both peers bind socket using SO_REUSEADDR on their local ports

    par Simultaneous TCP SYN Outbound
        Alice->>NAT_A: TCP SYN to Bob (198.51.100.2:58102)
        NAT_A->>NAT_B: SYN packets punch outbound hole in NAT_A
        Bob->>NAT_B: TCP SYN to Alice (203.0.113.1:45123)
        NAT_B->>NAT_A: SYN packets punch outbound hole in NAT_B
    end

    Note over NAT_A,NAT_B: NATs permit incoming SYN packets because matching outbound state exists!
    Alice<<->>Bob: TCP Handshake completes (Simultaneous Open: SYN/ACK)
    Alice->>Bob: P2P_HANDSHAKE {"sender": "alice"}
    Bob-->>Alice: P2P_HANDSHAKE_ACK {"status": "OK"}
    Note over Alice,Bob: Direct P2P TCP connection ESTABLISHED!
```

---

## 3. Direct P2P Text Messaging (Unicast & Mesh Broadcast)

> **No Server Relay**: Messages flow directly across the hole-punched TCP connection.

```mermaid
sequenceDiagram
    autonumber
    actor Alice as Peer Alice
    actor Bob as Peer Bob
    participant T as Central Tracker

    Note over Alice,Bob: Communicating over direct hole-punched TCP socket!
    Alice->>Bob: MSG_DIRECT {"text": "Hello Bob!", "timestamp": 1729700000} [AES-256-GCM]
    Bob-->>Alice: P2P_ACK {"status": "DELIVERED"}
    Note over Bob: Decrypts & displays message in CLI
```

---

## 4. Direct P2P 64KB Chunked File Transfer Flow

> **No Server Relay**: 64KB binary chunks and SHA-256 integrity acknowledgments stream directly between peers.

```mermaid
sequenceDiagram
    autonumber
    actor Alice as Peer Alice (Sender)
    actor Bob as Peer Bob (Receiver)
    participant T as Central Tracker

    Note over Alice: Calculate file size and SHA-256 digest
    Alice->>Bob: FILE_INIT {"filename": "data.zip", "size": 131072, "sha256": "e3b0c442..."}
    Bob-->>Alice: FILE_ACK {"status": "READY"}

    Alice->>Bob: FILE_CHUNK {"seq_id": 0, "total_chunks": 2, "payload": 65536 bytes}
    Bob-->>Alice: FILE_ACK {"seq_id": 0, "status": "CHUNK_OK"}

    Alice->>Bob: FILE_CHUNK {"seq_id": 1, "total_chunks": 2, "payload": 65536 bytes}
    Bob-->>Alice: FILE_ACK {"seq_id": 1, "status": "CHUNK_OK"}

    Note over Bob: Reassembles chunks, calculates SHA-256 hash
    Bob->>Bob: Compare calculated SHA-256 with metadata hash
    Bob-->>Alice: FILE_ACK {"status": "VERIFIED", "sha256_match": true}
    Note over Alice,Bob: File transfer complete with verified integrity
```
