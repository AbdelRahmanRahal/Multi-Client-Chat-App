import base64
import json
import os
import sys
import threading
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import *

from client_connection import conn, USERNAME
from signals import Signals
from private_chat import PrivateChat


class Chat(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"💬 Multi-Client Chat - {USERNAME}")
        self.resize(1000, 700)
        self.setMinimumSize(800, 500)

        self.sig = Signals()
        self.sig.status.connect(self.update_users)
        self.sig.message.connect(self.show_message)
        self.sig.typing.connect(self.show_typing)

        self.typing_users = {}
        self.typing_timers = {}  # Track typing timers per user
        self.typing_indicator_ids = {}  # Track typing indicator HTML IDs
        self.private_chats = {}
        self.dark_mode = True
        self.connected = True
        self.last_typing_sent = 0  # Track last typing notification time
        self.typing_debounce_timer = QTimer()
        self.typing_debounce_timer.setSingleShot(True)
        self.typing_debounce_timer.timeout.connect(self.send_group_typing)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 8, 10, 8)
        toolbar.setSpacing(10)

        # Title
        title_label = QLabel(f"💬 Chat - {USERNAME}")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        toolbar.addWidget(title_label)

        toolbar.addStretch()

        # Connection status
        self.status_label = QLabel("🟢 Connected")
        self.status_label.setFont(QFont("Arial", 9))
        toolbar.addWidget(self.status_label)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search messages...")
        self.search_input.setMaximumWidth(200)
        self.search_input.setMinimumHeight(30)
        self.search_input.returnPressed.connect(self.search_messages)
        toolbar.addWidget(self.search_input)

        search_btn = QPushButton("Search")
        search_btn.setMinimumHeight(30)
        search_btn.clicked.connect(self.search_messages)
        toolbar.addWidget(search_btn)

        # Theme toggle
        self.mode_btn = QPushButton("🌙")
        self.mode_btn.setToolTip("Toggle Dark/Light Mode")
        self.mode_btn.setMinimumSize(40, 30)
        self.mode_btn.clicked.connect(self.toggle_mode)
        toolbar.addWidget(self.mode_btn)

        main_layout.addLayout(toolbar)

        # Splitter for chat and users
        splitter = QSplitter(Qt.Horizontal)

        # Left side - Chat area
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(10, 10, 10, 10)
        chat_layout.setSpacing(10)

        self.chat = QTextBrowser()
        self.chat.setSource = lambda url: None
        self.chat.setOpenExternalLinks(False)  # Now this will work!
        self.chat.setFont(QFont("Segoe UI", 10))
        chat_layout.addWidget(self.chat)

        # Input area
        input_container = QHBoxLayout()
        input_container.setSpacing(8)

        self.input = QLineEdit()
        self.input.setPlaceholderText(
            "Type a message... (Press Enter to send)")
        self.input.setMinimumHeight(40)
        self.input.returnPressed.connect(self.send_group)

        # Handling files
        self.chat.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.chat.anchorClicked.connect(self.handle_file_click)

        # Button container
        btn_container = QHBoxLayout()
        btn_container.setSpacing(5)

        emoji_btn = QPushButton("😊")
        emoji_btn.setToolTip("Insert emoji")
        emoji_btn.setMinimumSize(40, 40)
        emoji_btn.clicked.connect(lambda: self.input.insert("😊"))

        file_btn = QPushButton("📎")
        file_btn.setToolTip("Send file")
        file_btn.setMinimumSize(40, 40)
        file_btn.clicked.connect(self.send_file)

        private_btn = QPushButton("💬")
        private_btn.setToolTip("Private chat with selected user")
        private_btn.setMinimumSize(40, 40)
        private_btn.clicked.connect(self.open_selected_private_chat)

        send_btn = QPushButton("Send")
        send_btn.setToolTip("Send message (Enter)")
        send_btn.setMinimumSize(80, 40)
        send_btn.clicked.connect(self.send_group)

        btn_container.addWidget(emoji_btn)
        btn_container.addWidget(file_btn)
        btn_container.addWidget(private_btn)
        btn_container.addWidget(send_btn)

        input_container.addWidget(self.input)
        input_container.addLayout(btn_container)
        chat_layout.addLayout(input_container)

        splitter.addWidget(chat_widget)

        # Right side - Users panel
        users_widget = QWidget()
        users_layout = QVBoxLayout(users_widget)
        users_layout.setContentsMargins(10, 10, 10, 10)
        users_layout.setSpacing(8)

        users_label = QLabel("👥 Online Users")
        users_label.setFont(QFont("Arial", 11, QFont.Bold))
        users_layout.addWidget(users_label)

        self.users = QListWidget()
        self.users.itemDoubleClicked.connect(self.open_private_chat)
        self.users.setMinimumWidth(200)
        users_layout.addWidget(self.users)

        splitter.addWidget(users_widget)

        # Set splitter proportions (70% chat, 30% users)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([700, 300])

        main_layout.addWidget(splitter)

        # Connect signals
        self.input.textChanged.connect(self.on_group_text_changed)

        # Apply styling
        self.setStyleSheet(self.dark_stylesheet())

        # Start listening thread
        threading.Thread(target=self.listen, daemon=True).start()

    def toggle_mode(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.setStyleSheet(self.dark_stylesheet())
            self.mode_btn.setText("🌙")
            self.mode_btn.setToolTip("Switch to Light Mode")
        else:
            self.setStyleSheet(self.light_stylesheet())
            self.mode_btn.setText("☀️")
            self.mode_btn.setToolTip("Switch to Dark Mode")

        # Update private chat windows
        for chat in self.private_chats.values():
            if self.dark_mode:
                chat.setStyleSheet(self.dark_stylesheet())
            else:
                chat.setStyleSheet(self.light_stylesheet())

    def dark_stylesheet(self):
        return """
        QWidget {
            background: #0D1117;
            color: #E6EDF3;
        }
        QTextEdit {
            background: #161B22;
            border: 1px solid #30363D;
            border-radius: 8px;
            color: #E6EDF3;
            padding: 10px;
            font-size: 14px;
        }
        QLineEdit {
            background: #161B22;
            border: 2px solid #30363D;
            border-radius: 8px;
            color: #E6EDF3;
            padding: 8px 12px;
            font-size: 14px;
        }
        QLineEdit:focus {
            border: 2px solid #58A6FF;
            background: #1C2128;
        }
        QListWidget {
            background: #161B22;
            border: 1px solid #30363D;
            border-radius: 8px;
            color: #E6EDF3;
            padding: 5px;
        }
        QListWidget::item {
            padding: 8px;
            border-radius: 6px;
            margin: 2px;
        }
        QListWidget::item:hover {
            background: #21262D;
        }
        QListWidget::item:selected {
            background: #1F6FEB;
            color: white;
        }
        QPushButton {
            background: #238636;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            color: white;
            font-weight: 600;
            font-size: 13px;
        }
        QPushButton:hover {
            background: #2EA043;
        }
        QPushButton:pressed {
            background: #1F6FEB;
        }
        QLabel {
            color: #E6EDF3;
        }
        QSplitter::handle {
            background: #30363D;
            width: 2px;
        }
        QSplitter::handle:hover {
            background: #58A6FF;
        }
        """

    def light_stylesheet(self):
        return """
        QWidget {
            background: #FFFFFF;
            color: #1F2328;
        }
        QTextEdit {
            background: #F6F8FA;
            border: 1px solid #D1D9DE;
            border-radius: 8px;
            color: #1F2328;
            padding: 10px;
            font-size: 14px;
        }
        QLineEdit {
            background: #F6F8FA;
            border: 2px solid #D1D9DE;
            border-radius: 8px;
            color: #1F2328;
            padding: 8px 12px;
            font-size: 14px;
        }
        QLineEdit:focus {
            border: 2px solid #0969DA;
            background: #FFFFFF;
        }
        QListWidget {
            background: #F6F8FA;
            border: 1px solid #D1D9DE;
            border-radius: 8px;
            color: #1F2328;
            padding: 5px;
        }
        QListWidget::item {
            padding: 8px;
            border-radius: 6px;
            margin: 2px;
        }
        QListWidget::item:hover {
            background: #E7ECF0;
        }
        QListWidget::item:selected {
            background: #0969DA;
            color: white;
        }
        QPushButton {
            background: #2DA44E;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            color: white;
            font-weight: 600;
            font-size: 13px;
        }
        QPushButton:hover {
            background: #2EA043;
        }
        QPushButton:pressed {
            background: #0969DA;
        }
        QLabel {
            color: #1F2328;
        }
        QSplitter::handle {
            background: #D1D9DE;
            width: 2px;
        }
        QSplitter::handle:hover {
            background: #0969DA;
        }
        """

    def send_group(self):
        msg = self.input.text().strip()
        if msg:
            # Stop typing timer and remove indicator
            self.typing_debounce_timer.stop()
            self.remove_typing(USERNAME)

            payload = {"type": "group", "content": msg}
            conn.sendall(json.dumps(payload).encode())
            self.show_message(USERNAME, msg)  # show locally
            self.input.clear()
            self.last_typing_sent = 0

    def send_file(self):
        path, _ = QFileDialog.getOpenFileName(self)
        if path:
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            payload = {"type": "file", "filename": os.path.basename(
                path), "filedata": data}
            conn.sendall(json.dumps(payload).encode())
            self.show_message(USERNAME, f"Sent file: {os.path.basename(path)}")
            self.remove_typing(USERNAME)

    def handle_file_click(self, url):
        # The URL comes in as 'file:filename.ext'
        self.chat.setSource(url.fromLocalFile(""))
        url_str = url.toString()
        if url_str.startswith("file:"):
            filename = url_str.split("file:")[1]

            # Retrieve the base64 data we saved earlier
            filedata_base64 = getattr(self, 'download_cache', {}).get(filename)

            if not filedata_base64:
                QMessageBox.warning(self, "Download Error",
                                    "File data not found in current session.")
                return

            # Open Save File Dialog
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save File", filename)

            if save_path:
                try:
                    with open(save_path, "wb") as f:
                        f.write(base64.b64decode(filedata_base64))
                    QMessageBox.information(
                        self, "Success", f"File saved to:\n{save_path}")
                except Exception as e:
                    QMessageBox.critical(
                        self, "Error", f"Could not save file: {e}")

    def search_messages(self):
        key = self.search_input.text().strip()
        if key:
            conn.sendall(json.dumps(
                {"type": "search", "content": key}).encode())

    def on_group_text_changed(self):
        """Handle text changes in group chat with debouncing"""
        text = self.input.text()
        if text.strip():
            # Debounce: only send typing notification every 2 seconds
            current_time = datetime.now().timestamp()
            if current_time - self.last_typing_sent > 2:
                self.send_group_typing()
            else:
                # Restart timer to send notification after delay
                self.typing_debounce_timer.stop()
                self.typing_debounce_timer.start(2000)  # 2 seconds
        else:
            # Text cleared, stop typing
            self.typing_debounce_timer.stop()
            self.remove_typing(USERNAME)

    def send_group_typing(self):
        """Send typing notification for group chat"""
        if self.input.text().strip():
            conn.sendall(json.dumps({"type": "typing", "to": None}).encode())
            self.last_typing_sent = datetime.now().timestamp()

    def show_message(self, msg_or_sender, content=None):
        if isinstance(msg_or_sender, dict):
            msg = msg_or_sender
            sender = msg.get("sender")
            content = msg.get("content", msg.get("filename", ""))
            msg_type = msg.get("type")
        else:
            sender = msg_or_sender
            msg_type = "group"

        # Private messages
        if msg_type == "private":
            target = msg.get("sender") if msg.get(
                "sender") != USERNAME else msg.get("to")
            if target not in self.private_chats:
                self.private_chats[target] = PrivateChat(target, self)
            self.private_chats[target].show_message(msg.get("sender"), content)
            return

        # Group/file messages
        time = datetime.now().strftime("%H:%M")
        date = datetime.now().strftime("%Y-%m-%d")
        is_own = sender == USERNAME

        if is_own:
            bg_color = "#007AFF" if self.dark_mode else "#007AFF"
            text_color = "#FF8C00" if self.dark_mode else "#000000"
        else:
            bg_color = "#2C2C2E" if self.dark_mode else "#E5E5EA"
            text_color = "#FF8C00" if self.dark_mode else "#000000"

        # File message styling
        if msg_type == "file":
            file_icon = "📎"
            # Get the actual data if it's there
            file_data = msg.get("filedata", "")
            # We store the data inside the link using a custom scheme or just the filename
            content = f'<a href="file:{content}" style="color:#58A6FF; text-decoration:none;">{file_icon} {content}</a>'
            # Store the data globally so we can access it when clicked
            if file_data:
                if not hasattr(self, 'download_cache'):
                    self.download_cache = {}
                self.download_cache[msg.get("filename")] = file_data

        bubble = f"""
        <div style="background:{bg_color};color:{text_color};padding:12px 16px;border-radius:18px;
        margin:6px 0;max-width:75%;display:inline-block;box-shadow:0 2px 8px rgba(0,0,0,0.15);">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px;opacity:0.9;">{sender}</div>
        <div style="font-size:14px;line-height:1.5;word-wrap:break-word;white-space:pre-wrap;">{content}</div>
        <div style="font-size:11px;opacity:0.7;margin-top:6px;text-align:right;">{time}</div>
        </div>
        """

        align = Qt.AlignRight if is_own else Qt.AlignLeft
        self.chat.setAlignment(align)
        self.chat.append(bubble)
        self.chat.moveCursor(QTextCursor.End)

    def show_typing(self, sender):
        """Show typing indicator in group chat"""
        if sender == USERNAME:
            return

        # Check if this is a private message typing indicator
        # If sender is in private chats, show in that window instead
        if sender in self.private_chats:
            self.private_chats[sender].show_typing_indicator(sender)
            return

        # Group chat typing indicator
        # Remove existing indicator for this user if any
        if sender in self.typing_users:
            self.remove_typing(sender)

        self.typing_users[sender] = True
        typing_color = "#888888" if self.dark_mode else "#666666"
        typing_html = f'<div id="typing_{sender}" style="color:{typing_color};font-style:italic;padding:4px;font-size:12px;">✍️ {sender} is typing...</div>'
        self.chat.append(typing_html)
        self.chat.moveCursor(QTextCursor.End)
        self.typing_indicator_ids[sender] = f"typing_{sender}"

        # Auto-remove after 3 seconds
        QTimer.singleShot(3000, lambda s=sender: self.remove_typing(s))

    def remove_typing(self, sender):
        """Remove typing indicator from group chat"""
        if sender in self.typing_users:
            # Remove from tracking
            self.typing_users.pop(sender, None)

            # Remove HTML element
            if sender in self.typing_indicator_ids:
                html = self.chat.toHtml()
                import re
                pattern = rf'<div id="typing_{re.escape(sender)}"[^>]*>.*?</div>'
                html = re.sub(pattern, '', html, flags=re.DOTALL)
                self.chat.setHtml(html)
                self.chat.moveCursor(QTextCursor.End)
                self.typing_indicator_ids.pop(sender, None)

    def open_private_chat(self, item):
        username = item.text().replace("🟢 ", "").strip()
        if username not in self.private_chats:
            self.private_chats[username] = PrivateChat(username, self)
        self.private_chats[username].show()
        self.private_chats[username].raise_()
        self.private_chats[username].activateWindow()

    def open_selected_private_chat(self):
        user = self.users.currentItem()
        if user:
            self.open_private_chat(user)
        else:
            QMessageBox.information(
                self, "No User Selected", "Please select a user from the list first.")

    def update_users(self, users):
        self.users.clear()
        for user in users:
            if user != USERNAME:  # Don't show self in list
                item = QListWidgetItem(f"🟢 {user}")
                self.users.addItem(item)

        # Update connection status
        if self.connected:
            self.status_label.setText(f"🟢 Connected ({len(users)} users)")
        else:
            self.status_label.setText("🔴 Disconnected")

    def listen(self):
        while True:
            try:
                data = conn.recv(8192)
                if not data:
                    self.connected = False
                    self.status_label.setText("🔴 Disconnected")
                    break
                msg = json.loads(data.decode())
                if msg["type"] == "status":
                    self.sig.status.emit(msg["users"])
                elif msg["type"] == "history":
                    for m in msg["messages"]:
                        self.sig.message.emit({
                            "sender": m["sender"],
                            "content": m["content"],
                            "type": m.get("type", "group"),
                            "status": "",
                            "filename": m["content"] if m.get("type") == "file" else ""
                        })
                elif msg["type"] == "typing":
                    sender = msg.get("sender")
                    to_user = msg.get("to")
                    # If it's a private typing indicator, route to private chat
                    if to_user and to_user == USERNAME and sender in self.private_chats:
                        # Show in private chat window
                        self.private_chats[sender].show_typing_indicator(
                            sender)
                    else:
                        # Group typing indicator
                        self.sig.typing.emit(sender)
                else:
                    self.sig.message.emit(msg)
                self.connected = True
                if self.status_label.text().startswith("🔴"):
                    self.status_label.setText("🟢 Connected")
            except Exception as e:
                self.connected = False
                self.status_label.setText("🔴 Connection Error")
                break


app = QApplication(sys.argv)
Chat().show()
sys.exit(app.exec_())
