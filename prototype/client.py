import protocol
import socket
import socket
import threading
from protocol.packet import OpCode, send_packet, recv_packet
import json

def start(host='127.0.0.1', port=12345):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((host, port))
        
        # 1. Prepare JSON payload
        payload_dict = {
            "username": "alice",
            "local_ip": f"{client.getsockname()[0]}",
            "local_port": f"{client.getsockname()[1]}",
        }
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        # 2. Send framed packet over TCP socket
        send_packet(
            sock=client,
            opcode=OpCode.AUTH_REQ,
            payload=payload_bytes,
            flags=0,
            seq=0,
        )
        header, payload = recv_packet(client)
        if(header.opcode == protocol.OpCode.AUTH_RESP):
            print(payload.decode("utf-8"))
        

if __name__ == '__main__':
    start()
            




