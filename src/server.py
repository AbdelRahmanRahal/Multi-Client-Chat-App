import os
import socket
import ssl
import threading
import sys

from client_handler import handle_client
from server_state import UPLOADS_DIR

HOST = "0.0.0.0"
PORT = 5000

# SSL Context setup with error handling
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
cert_file = "cert.pem"
key_file = "key.pem"

if os.path.exists(cert_file) and os.path.exists(key_file):
    try:
        context.load_cert_chain(cert_file, key_file)
        print(f"✓ SSL certificates loaded: {cert_file}, {key_file}")
    except ssl.SSLError as e:
        print(f"Error: Could not load SSL certificates: {e}")
        print("Please check the certificate files and their permissions.")
        sys.exit(1)
else:
    print(f"Error: SSL certificate files not found ({cert_file}, {key_file})")
    print(" This server requires SSL to run.")
    print(" To generate self-signed certificates, run:")
    print("   openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 365")
    sys.exit(1)


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((HOST, PORT))
        server.listen(100)
        print("=" * 50)
        print(f" Multi-Client Chat Server Running...")
        print(f" Listening on {HOST}:{PORT}")
        print(f" Uploads directory: {UPLOADS_DIR}")
        print("=" * 50)

        while True:
            try:
                raw, addr = server.accept()
                print(f"📥 New connection from {addr[0]}:{addr[1]}")
                conn = context.wrap_socket(raw, server_side=True)
                threading.Thread(target=handle_client,
                                 args=(conn,), daemon=True).start()
            except ssl.SSLError as e:
                print(f"⚠ SSL error: {e}")
                try:
                    raw.close()
                except:
                    pass
            except Exception as e:
                print(f"⚠ Error accepting connection: {e}")

    except OSError as e:
        print(f" Error starting server: {e}")
        print(f"   Port {PORT} may already be in use.")
    except KeyboardInterrupt:
        print("\n Server shutting down...")
    finally:
        server.close()


if __name__ == "__main__":
    main()
