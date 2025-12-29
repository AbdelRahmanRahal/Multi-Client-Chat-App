import os
import threading
from database import ChatDatabase

UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

db = ChatDatabase()
clients = {}  # username: conn
clients_lock = threading.Lock()  # Thread-safe access to clients dict
