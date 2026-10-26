import socket
import threading
import protocol
import json
from protocol.packet import send_packet, recv_packet

HOST = '127.0.0.1'
PORT = 12345
ADDR = (HOST, PORT)

def handle_client(conn, addr):
    with conn:
        header, payload = recv_packet(conn)
        print(addr)
        payload_dict = {
            "status": "OK",
            "public_ip": f"{addr[0]}",
            "public_port": f"{addr[1]}"
            }
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        # 2. Send framed packet over TCP socket

        if header.opcode == protocol.OpCode.AUTH_REQ:
            send_packet(
            sock=conn,
            opcode=protocol.OpCode.AUTH_RESP,
            payload=payload_bytes,
            flags=0,
            seq=0,
        )


def auth(payload):
    pass

def start():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.listen()
    
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

if __name__ == '__main__':
    start()