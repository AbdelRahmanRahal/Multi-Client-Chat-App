import base64
import json
import os
import socket
import ssl
import threading

from database import ChatDatabase

HOST = "0.0.0.0"
PORT = 5000
UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

db = ChatDatabase()
clients = {}  # username: conn
clients_lock = threading.Lock()  # Thread-safe access to clients dict


# SSL Context setup with error handling
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
cert_file = "cert.pem"
key_file = "key.pem"

if os.path.exists(cert_file) and os.path.exists(key_file):
    try:
        context.load_cert_chain(cert_file, key_file)
        print(f"✓ SSL certificates loaded: {cert_file}, {key_file}")
    except Exception as e:
        print(f"Warning: Could not load SSL certificates: {e}")
        print(" Server will continue but SSL may not work properly.")
else:
    print(
        f"Warning: SSL certificate files not found ({cert_file}, {key_file})")
    print(" Server will continue but SSL may not work properly.")
    print(" To generate self-signed certificates, run:")
    print("   openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 365")


def broadcast(data, exclude=None):
    """Send data to all clients except exclude"""
    with clients_lock:
        clients_copy = dict(clients)  # Create a copy to avoid lock issues

    for user, conn in clients_copy.items():
        if user != exclude:
            try:
                conn.sendall(data)
            except (ConnectionError, OSError, BrokenPipeError) as e:
                # Client disconnected, will be cleaned up on next status update
                pass


def broadcast_status():
    """Send online users list"""
    with clients_lock:
        users_list = list(clients.keys())
        clients_copy = dict(clients)

    data = json.dumps({"type": "status", "users": users_list}).encode()
    for conn in clients_copy.values():
        try:
            conn.sendall(data)
        except (ConnectionError, OSError, BrokenPipeError):
            # Client disconnected, will be cleaned up
            pass


def handle_client(conn):
    username = None
    try:
        # Receive username
        username_data = conn.recv(1024)
        if not username_data:
            conn.close()
            return

        username = username_data.decode().strip()

        # Validate username
        if not username:
            conn.sendall(json.dumps(
                {"type": "error", "message": "Username cannot be empty"}).encode())
            conn.close()
            return

        # Check for duplicate username
        with clients_lock:
            if username in clients:
                conn.sendall(json.dumps(
                    {"type": "error", "message": f"Username '{username}' is already taken"}).encode())
                conn.close()
                return
            clients[username] = conn

        print(f"✓ Client connected: {username}")
        broadcast_status()

        # Send chat history - format messages to match client expectations
        history = db.get_messages()
        formatted_history = []
        for msg in history:
            formatted_msg = {
                "sender": msg.get("sender", ""),
                "content": msg.get("content", ""),
                "type": msg.get("type", "group"),
                "timestamp": msg.get("timestamp", "")
            }
            # For private messages, include receiver info
            if msg.get("type") == "private":
                formatted_msg["receiver"] = msg.get("receiver", "")
            formatted_history.append(formatted_msg)

        conn.sendall(json.dumps(
            {"type": "history", "messages": formatted_history}).encode())

        while True:
            data = conn.recv(8192)
            if not data:
                break
            msg = json.loads(data.decode())
            t = msg.get("type")

            if t == "group":
                content = msg.get("content", "").strip()
                if content:
                    db.insert_message(username, "group", content, "group")
                    payload = json.dumps(
                        {"type": "group", "sender": username, "content": content}).encode()
                    broadcast(payload, exclude=username)

            elif t == "private":
                to = msg.get("to")
                content = msg.get("content", "").strip()

                if not to or not content:
                    continue

                db.insert_message(username, to, content, "private")
                payload = json.dumps({
                    "type": "private",
                    "sender": username,
                    "to": to,
                    "content": content
                }).encode()

                # Send to recipient if online
                with clients_lock:
                    if to in clients:
                        try:
                            clients[to].sendall(payload)
                        except (ConnectionError, OSError, BrokenPipeError):
                            # Recipient disconnected
                            pass

            elif t == "file":
                filename = msg.get("filename", "unknown_file")
                filedata_str = msg.get("filedata", "")

                if not filedata_str:
                    continue

                try:
                    filedata = base64.b64decode(filedata_str)
                except Exception as e:
                    print(f"Error decoding file data from {username}: {e}")
                    continue

                # Handle filename collisions by adding timestamp
                base_name, ext = os.path.splitext(filename)
                safe_filename = filename
                counter = 1
                while os.path.exists(os.path.join(UPLOADS_DIR, safe_filename)):
                    safe_filename = f"{base_name}_{counter}{ext}"
                    counter += 1

                path = os.path.join(UPLOADS_DIR, safe_filename)
                try:
                    with open(path, "wb") as f:
                        f.write(filedata)
                    db.insert_message(username, "FILE", safe_filename, "file")
                    payload = json.dumps(
                        {"type": "file", "sender": username, "filename": safe_filename, "filedata": filedata_str}).encode()
                    broadcast(payload, exclude=username)
                except Exception as e:
                    print(f"Error saving file from {username}: {e}")

            elif t == "search":
                keyword = msg.get("content", "")
                results = db.search(keyword)
                conn.sendall(json.dumps(
                    {"type": "search_result", "results": results}).encode())

            elif t == "typing":
                to = msg.get("to")
                payload = json.dumps(
                    {"type": "typing", "sender": username}).encode()

                # If private typing, send only to recipient
                if to:
                    with clients_lock:
                        if to in clients:
                            try:
                                clients[to].sendall(payload)
                            except (ConnectionError, OSError, BrokenPipeError):
                                pass
                else:
                    # Group typing indicator
                    broadcast(payload, exclude=username)

    except json.JSONDecodeError as e:
        print(f"JSON decode error from {username}: {e}")
    except (ConnectionError, OSError, BrokenPipeError) as e:
        print(f"Client {username} disconnected: {e}")
    except Exception as e:
        print(f"Unexpected error with client {username}: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up client
        with clients_lock:
            if username and username in clients:
                clients.pop(username)
                print(f" Client disconnected: {username}")

        broadcast_status()
        try:
            conn.close()
        except:
            pass


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
