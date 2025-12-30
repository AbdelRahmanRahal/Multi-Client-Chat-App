import socket
import ssl
import sys

if len(sys.argv) < 2:
    print("Usage: python client.py <username> [server_ip]")
    sys.exit(1)

USERNAME = sys.argv[1]
SERVER_IP = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
PORT = 5000

sock = socket.socket()
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE
conn = context.wrap_socket(sock)

conn.connect((SERVER_IP, PORT))
conn.sendall(USERNAME.encode())
