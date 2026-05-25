"""
widgets.py — 可复用 UI 组件（消息气泡、打字动画等）
"""
import threading

from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor

from config import cfg
from tts_service import play_audio


# ─── 消息气泡 ──────────────────────────────────────────────────────────────────
class MessageBubble(QFrame):
    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        self._wav: bytes | None = None

        # 滑入动画（用 maximumHeight，避免 QPainter 冲突）
        self.setMaximumHeight(0)
        self._slide_in = QPropertyAnimation(self, b"maximumHeight")
        self._slide_in.setDuration(300)
        self._slide_in.setStartValue(0)
        self._slide_in.setEndValue(300)  # 足够大的目标高度
        self._slide_in.setEasingCurve(QEasingCurve.OutCubic)
        # 动画结束后移除高度限制，让布局自适应
        self._slide_in.finished.connect(lambda: self.setMaximumHeight(16777215))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 6, 20, 6)
        outer.setSpacing(5)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)

        # 头像
        avatar = QLabel("我" if is_user else cfg.AI_NAME[0])
        avatar.setFixedSize(40, 40)
        avatar.setAlignment(Qt.AlignCenter)
        if is_user:
            avatar.setStyleSheet(
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                "stop:0 #8B5CF6, stop:1 #EC4899);"
                "border-radius: 20px; color: white;"
                "font-weight: 700; font-size: 13px;")
        else:
            avatar.setStyleSheet(
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                "stop:0 #06B6D4, stop:1 #8B5CF6);"
                "border-radius: 20px; color: white;"
                "font-weight: 700; font-size: 13px;")

        # 气泡
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setTextFormat(Qt.PlainText)
        bubble.setMaximumWidth(380)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        if is_user:
            bubble.setStyleSheet(
                "QLabel {"
                "  background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                "    stop:0 #7C3AED, stop:0.5 #9333EA, stop:1 #DB2777);"
                "  color: #FFFFFF; border-radius: 18px;"
                "  border-bottom-right-radius: 4px;"
                "  padding: 12px 16px; font-size: 14px;"
                "}")
            row.addStretch()
            row.addWidget(bubble)
            row.addWidget(avatar)
        else:
            bubble.setStyleSheet(
                "QLabel {"
                "  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "    stop:0 #1A1A3E, stop:1 #16162E);"
                "  color: #E2E8F0;"
                "  border: 1px solid rgba(99, 102, 241, 0.2);"
                "  border-radius: 18px; border-bottom-left-radius: 4px;"
                "  padding: 12px 16px; font-size: 14px;"
                "}")
            row.addWidget(avatar)
            row.addWidget(bubble)
            row.addStretch()

        # 阴影（只在 bubble 子组件上，不会与父组件冲突）
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 50) if is_user else QColor(99, 102, 241, 30))
        shadow.setOffset(0, 4)
        bubble.setGraphicsEffect(shadow)

        outer.addLayout(row)

        # 语音播放按钮（仅 AI 消息）
        if not is_user:
            self._play_btn = QPushButton("🔊 播放语音")
            self._play_btn.setCursor(Qt.PointingHandCursor)
            self._play_btn.setEnabled(False)
            self._play_btn.setFixedSize(110, 28)
            self._play_btn.setStyleSheet(
                "QPushButton {"
                "  background: transparent; color: #4B5563;"
                "  border: 1px solid #2D2D50; border-radius: 14px;"
                "  font-size: 11px; padding: 2px 12px;"
                "}"
                "QPushButton:enabled {"
                "  color: #A5B4FC; border-color: rgba(99, 102, 241, 0.4);"
                "}"
                "QPushButton:enabled:hover {"
                "  background: rgba(99, 102, 241, 0.15);"
                "  color: #C7D2FE; border-color: #6366F1;"
                "}")
            self._play_btn.clicked.connect(self._replay)
            btn_row = QHBoxLayout()
            btn_row.setContentsMargins(56, 0, 0, 0)
            btn_row.addWidget(self._play_btn)
            btn_row.addStretch()
            outer.addLayout(btn_row)
        else:
            self._play_btn = None

        # 启动滑入动画
        QTimer.singleShot(10, self._slide_in.start)

    def set_audio(self, wav: bytes):
        self._wav = wav
        if self._play_btn:
            self._play_btn.setEnabled(True)
            self._play_btn.setText("🔊 播放语音")

    def _replay(self):
        if self._wav:
            threading.Thread(target=play_audio, args=(self._wav,), daemon=True).start()


# ─── 输入中动画 ────────────────────────────────────────────────────────────────
class TypingDots(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 6, 20, 6)
        layout.setSpacing(12)

        avatar = QLabel(cfg.AI_NAME[0])
        avatar.setFixedSize(40, 40)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #06B6D4, stop:1 #8B5CF6);"
            "border-radius: 20px; color:white;"
            "font-weight: 700; font-size: 13px;")

        self._dot_container = QFrame()
        self._dot_container.setStyleSheet(
            "QFrame {"
            "  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "    stop:0 #1A1A3E, stop:1 #16162E);"
            "  border: 1px solid rgba(99, 102, 241, 0.2);"
            "  border-radius: 18px; border-bottom-left-radius: 4px;"
            "}")
        dot_lay = QHBoxLayout(self._dot_container)
        dot_lay.setContentsMargins(18, 10, 18, 10)
        dot_lay.setSpacing(6)

        self._dots = []
        for _ in range(3):
            dot = QLabel("●")
            dot.setFixedSize(12, 20)
            dot.setAlignment(Qt.AlignCenter)
            dot.setStyleSheet("color: #4B5580; font-size: 10px; background: transparent; border: none;")
            dot_lay.addWidget(dot)
            self._dots.append(dot)

        layout.addWidget(avatar)
        layout.addWidget(self._dot_container)
        layout.addStretch()

        self._step = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def _tick(self):
        active_color = "#A5B4FC"
        dim_color = "#4B5580"
        for i, dot in enumerate(self._dots):
            c = active_color if i == self._step else dim_color
            dot.setStyleSheet(f"color: {c}; font-size: 10px; background: transparent; border: none;")
        self._step = (self._step + 1) % 3

    def start(self):
        self._step = 0
        self._timer.start(350)
        self.setVisible(True)

    def stop(self):
        self._timer.stop()
        self.setVisible(False)
