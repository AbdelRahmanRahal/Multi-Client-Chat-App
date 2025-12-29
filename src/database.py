import sqlite3
from datetime import datetime

class ChatDatabase:
    def __init__(self):
        self.conn = sqlite3.connect("chat.db", check_same_thread=False)
        self.create_table()

    def create_table(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            content TEXT,
            timestamp TEXT,
            type TEXT
        )
        """)
        self.conn.commit()

    def insert_message(self, sender, receiver, content, msg_type):
        self.conn.execute("""
        INSERT INTO messages (sender, receiver, content, timestamp, type)
        VALUES (?, ?, ?, ?, ?)
        """, (sender, receiver, content,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg_type))
        self.conn.commit()

    def get_messages(self):
        rows = self.conn.execute("SELECT sender, receiver, content, timestamp, type FROM messages").fetchall()
        return [{"sender": r[0], "receiver": r[1], "content": r[2], "timestamp": r[3], "type": r[4]} for r in rows]

    def search(self, keyword):
        rows = self.conn.execute("SELECT sender, content, timestamp FROM messages WHERE content LIKE ?", (f"%{keyword}%",)).fetchall()
        return [{"sender": r[0], "content": r[1], "timestamp": r[2]} for r in rows]
