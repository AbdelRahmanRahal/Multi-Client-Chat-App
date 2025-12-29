import json
import re
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser, QLineEdit, QPushButton

from client_connection import conn, USERNAME


class PrivateChat(QWidget):
    def __init__(self, username, main_chat):
        super().__init__()
        self.username = username
        self.main_chat = main_chat
        self.setWindowTitle(f"💬 Private Chat - {username}")
        self.resize(450, 600)
        self.typing_users = {}
        self.typing_timer = QTimer()
        self.typing_timer.setSingleShot(True)
        self.typing_timer.timeout.connect(self.send_typing_notification)
        self.last_typing_sent = 0

        self.hide_typing_timer = QTimer()
        self.hide_typing_timer.setSingleShot(True)
        self.hide_typing_timer.timeout.connect(self.remove_typing_indicator)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Header with username
        header = QHBoxLayout()
        header_label = QLabel(f"💬 {username}")
        header_label.setFont(QFont("Arial", 12, QFont.Bold))
        header.addWidget(header_label)
        header.addStretch()
        main_layout.addLayout(header)

        # Chat area
        self.chat = QTextBrowser()
        self.chat.setSource = lambda url: None
        self.chat.setOpenExternalLinks(False)  # Now this will work!
        self.chat.setFont(QFont("Segoe UI", 10))
        main_layout.addWidget(self.chat)

        # Typing indicator label
        self.typing_label = QLabel()
        self.typing_label.setFont(QFont("Segoe UI", 9, QFont.StyleItalic))
        self.typing_label.hide()
        main_layout.addWidget(self.typing_label)

        # Input area
        input_container = QHBoxLayout()
        input_container.setSpacing(8)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message...")
        self.input.setMinimumHeight(35)
        send_btn = QPushButton("Send")
        send_btn.setMinimumWidth(80)
        send_btn.setMinimumHeight(35)

        input_container.addWidget(self.input)
        input_container.addWidget(send_btn)
        main_layout.addLayout(input_container)

        # Connect signals
        send_btn.clicked.connect(self.send_message)
        self.input.returnPressed.connect(self.send_message)
        self.input.textChanged.connect(self.on_text_changed)

        # Apply styling
        if main_chat.dark_mode:
            self.setStyleSheet(main_chat.dark_stylesheet())
        else:
            self.setStyleSheet(main_chat.light_stylesheet())

    def send_message(self):
        msg = self.input.text().strip()
        if msg:
            # Stop typing timer
            self.typing_timer.stop()
            # Remove typing indicator if showing
            self.remove_typing_indicator()

            payload = {"type": "private", "to": self.username, "content": msg}
            conn.sendall(json.dumps(payload).encode())
            self.show_message(USERNAME, msg)  # show locally
            self.input.clear()
            self.last_typing_sent = 0

    def show_message(self, sender, content):
        time = datetime.now().strftime("%H:%M")
        is_own = sender == USERNAME
        align = Qt.AlignRight if is_own else Qt.AlignLeft

        if is_own:
            bg_color = "#007AFF" if self.main_chat.dark_mode else "#007AFF"
            text_color = "#FF8C00" if self.main_chat.dark_mode else "#FFFFFF"
        else:
            bg_color = "#2C2C2E" if self.main_chat.dark_mode else "#E5E5EA"
            text_color = "#FF8C00" if self.main_chat.dark_mode else "#000000"

        bubble = f"""
        <div style="background:{bg_color};color:{text_color};padding:10px 14px;border-radius:18px;
        margin:4px 0;max-width:75%;display:inline-block;box-shadow:0 2px 4px rgba(0,0,0,0.1);">
        <div style="font-weight:600;font-size:13px;margin-bottom:4px;">{sender}</div>
        <div style="font-size:14px;line-height:1.4;word-wrap:break-word;">{content}</div>
        <div style="font-size:11px;opacity:0.7;margin-top:4px;text-align:right;">{time}</div>
        </div>
        """
        self.chat.setAlignment(align)
        self.chat.append(bubble)
        self.chat.moveCursor(QTextCursor.End)

        # Remove typing indicator when message is shown
        self.remove_typing_indicator()

    def on_text_changed(self):
        """Handle text changes with debouncing"""
        text = self.input.text()
        if text.strip():
            # Debounce: only send typing notification every 2 seconds
            current_time = datetime.now().timestamp()
            if current_time - self.last_typing_sent > 2:
                self.send_typing_notification()
            else:
                # Restart timer to send notification after delay
                self.typing_timer.stop()
                self.typing_timer.start(2000)  # 2 seconds
        else:
            # Text cleared, stop typing timer
            self.typing_timer.stop()
            self.remove_typing_indicator()

    def send_typing_notification(self):
        """Send typing notification to server"""
        if self.input.text().strip():
            conn.sendall(json.dumps(
                {"type": "typing", "to": self.username}).encode())
            self.last_typing_sent = datetime.now().timestamp()

    def show_typing_indicator(self, sender):
        """Show typing indicator in private chat"""
        if sender == USERNAME:
            return

        self.hide_typing_timer.stop()

        typing_color = "#888888" if self.main_chat.dark_mode else "#666666"
        self.typing_label.setStyleSheet(
            f"color: {typing_color}; margin-left: 5px; font-style: italic;")
        self.typing_label.setText(f"✍️ {sender} is typing...")
        self.typing_label.show()

        self.hide_typing_timer.start(3000)

    def remove_typing_indicator(self):
        """Remove typing indicator from chat"""
        self.typing_label.clear()
        self.typing_label.hide()
