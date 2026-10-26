import protocol
import socket
import socket
import threading
from protocol.packet import OpCode, send_packet, recv_packet
import json

def user_register_request(socket, username = None):
    payload_dict = {
        "username": f"{username}",
        "local_ip": f"{socket.getsockname()[0]}",
        "local_port": f"{socket.getsockname()[1]}",
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    # 2. Send framed packet over TCP socket
    send_packet(
        sock=socket,
        opcode=OpCode.AUTH_REQ,
        payload=payload_bytes,
        flags=0,
        seq=0,
    )
    header, payload = recv_packet(socket)
    if(header.opcode == protocol.OpCode.AUTH_RESP):
        response = json.loads(payload.decode("utf-8"))
        return response["status"]

    raise ConnectionError("wrong format")

def start(host='127.0.0.1', port=12345):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((host, port))
        
        status = user_register_request(client, "nam")
        print(status)
        

if __name__ == '__main__':
    start()
            




