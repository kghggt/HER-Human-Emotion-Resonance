"""
chat_window.py — 主聊天窗口
"""
import threading
import logging

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QLabel, QPushButton, QLineEdit, QFrame,
    QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QColor

from config import cfg
from ai_client import get_ai_response, reset_client
from tts_service import get_tts_audio, start_tts_service
from widgets import MessageBubble, TypingDots
from settings_dialog import SettingsDialog


# ─── Qt 信号（跨线程安全通信）──────────────────────────────────────────────────
class _Signals(QObject):
    ai_done    = pyqtSignal(str)   # AI 回复文本
    tts_ready  = pyqtSignal(bytes) # TTS 语音就绪
    error      = pyqtSignal(str)   # 错误提示
    busy       = pyqtSignal(bool)  # 是否禁用输入


# ─── 主窗口 ────────────────────────────────────────────────────────────────────
class ChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._signals = _Signals()
        self._signals.ai_done.connect(self._on_ai_done)
        self._signals.tts_ready.connect(self._on_tts_ready)
        self._signals.error.connect(self._on_error)
        self._signals.busy.connect(self._set_busy)
        self._last_ai_bubble: MessageBubble | None = None

        self._build_ui()
        self._add_msg(
            f"嘿～我是{cfg.AI_NAME}，有什么想和我聊的吗？💗", is_user=False
        )

    # ── 构建 UI ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setWindowTitle(f"✨ {cfg.AI_NAME} · AI 伴侣")
        self.resize(540, 800)
        self.setMinimumSize(420, 620)
        self.setStyleSheet("background-color: #080818;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_chat_area(), stretch=1)
        root.addWidget(self._build_input_area())

    def _build_header(self) -> QFrame:
        hdr = QFrame()
        hdr.setFixedHeight(72)
        hdr.setStyleSheet(
            "QFrame#header {"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "    stop:0 #0C0C24, stop:0.5 #12122E, stop:1 #0C0C24);"
            "  border-bottom: 1px solid rgba(99, 102, 241, 0.15);"
            "}")
        hdr.setObjectName("header")

        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(24, 0, 24, 0)

        # 头像
        self._hdr_avatar = QLabel(cfg.AI_NAME[0])
        self._hdr_avatar.setFixedSize(46, 46)
        self._hdr_avatar.setAlignment(Qt.AlignCenter)
        self._hdr_avatar.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #06B6D4, stop:0.5 #8B5CF6, stop:1 #EC4899);"
            "border-radius: 23px; color: white;"
            "font-weight: 800; font-size: 16px;")

        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(24)
        glow.setColor(QColor(139, 92, 246, 100))
        glow.setOffset(0, 0)
        self._hdr_avatar.setGraphicsEffect(glow)

        # 名字 + 状态
        info = QVBoxLayout()
        info.setSpacing(2)
        self._hdr_name = QLabel(cfg.AI_NAME)
        self._hdr_name.setStyleSheet(
            "color: #F1F5F9; font-size: 16px; font-weight: 700;"
            "background: transparent;")
        self._status = QLabel("● 在线")
        self._status.setStyleSheet(
            "color: #34D399; font-size: 11px;"
            "background: transparent;")
        info.addWidget(self._hdr_name)
        info.addWidget(self._status)

        # 设置按钮
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(40, 40)
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setStyleSheet(
            "QPushButton {"
            "  background: rgba(255,255,255,0.04); color: #6B7280;"
            "  font-size: 19px; border: 1px solid rgba(255,255,255,0.06);"
            "  border-radius: 20px;"
            "}"
            "QPushButton:hover {"
            "  background: rgba(139, 92, 246, 0.15);"
            "  color: #A5B4FC; border-color: rgba(139, 92, 246, 0.3);"
            "}")

        settings_btn.clicked.connect(self._open_settings)

        lay.addWidget(self._hdr_avatar)
        lay.addSpacing(14)
        lay.addLayout(info)
        lay.addStretch()
        lay.addWidget(settings_btn)
        return hdr

    def _build_chat_area(self) -> QScrollArea:
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background: #080818; }"
            "QScrollBar:vertical {"
            "  background: transparent; width: 6px; margin: 4px 1px;"
            "}"
            "QScrollBar::handle:vertical {"
            "  background: rgba(139, 92, 246, 0.3); border-radius: 3px;"
            "  min-height: 30px;"
            "}"
            "QScrollBar::handle:vertical:hover {"
            "  background: rgba(139, 92, 246, 0.5);"
            "}"
            "QScrollBar::add-line:vertical,"
            "QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical,"
            "QScrollBar::sub-page:vertical { background: transparent; }")

        self._chat_widget = QWidget()
        self._chat_widget.setStyleSheet("background: #080818;")
        self._chat_layout = QVBoxLayout(self._chat_widget)
        self._chat_layout.setContentsMargins(0, 16, 0, 16)
        self._chat_layout.setSpacing(4)
        self._chat_layout.addStretch()

        self._typing = TypingDots()
        self._typing.setVisible(False)
        self._chat_layout.addWidget(self._typing)

        self._scroll.setWidget(self._chat_widget)
        return self._scroll

    def _build_input_area(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(80)
        bar.setObjectName("inputBar")
        bar.setStyleSheet(
            "QFrame#inputBar {"
            "  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "    stop:0 #0C0C22, stop:1 #080818);"
            "  border-top: 1px solid rgba(99, 102, 241, 0.1);"
            "}")

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(12)

        self._input = QLineEdit()
        self._input.setPlaceholderText("说点什么吧～")
        self._input.setFixedHeight(50)
        self._input.setStyleSheet(
            "QLineEdit {"
            "  background: rgba(255, 255, 255, 0.04);"
            "  color: #E2E8F0;"
            "  border: 1.5px solid rgba(99, 102, 241, 0.15);"
            "  border-radius: 25px;"
            "  padding: 0 22px; font-size: 14px;"
            "  selection-background-color: #7C3AED;"
            "}"
            "QLineEdit:focus {"
            "  border-color: rgba(139, 92, 246, 0.5);"
            "  background: rgba(255, 255, 255, 0.06);"
            "}"
            "QLineEdit::placeholder {"
            "  color: #4B5563;"
            "}")

        self._btn = QPushButton("➤")
        self._btn.setFixedSize(50, 50)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setStyleSheet(
            "QPushButton {"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "    stop:0 #7C3AED, stop:1 #DB2777);"
            "  color: white; font-weight: bold; font-size: 18px;"
            "  border-radius: 25px; border: none;"
            "}"
            "QPushButton:hover {"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "    stop:0 #6D28D9, stop:1 #BE185D);"
            "}"
            "QPushButton:pressed {"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "    stop:0 #5B21B6, stop:1 #9D174D);"
            "}"
            "QPushButton:disabled {"
            "  background: rgba(255, 255, 255, 0.06);"
            "  color: #4B5563;"
            "}")

        # 发送按钮发光
        btn_glow = QGraphicsDropShadowEffect()
        btn_glow.setBlurRadius(20)
        btn_glow.setColor(QColor(124, 58, 237, 80))
        btn_glow.setOffset(0, 2)
        self._btn.setGraphicsEffect(btn_glow)

        self._input.returnPressed.connect(self._send)
        self._btn.clicked.connect(self._send)

        lay.addWidget(self._input)
        lay.addWidget(self._btn)
        return bar

    # ── 设置 ─────────────────────────────────────────────────────────────────
    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_():
            reset_client()  # 重建客户端以使用新的 API Key
            self._refresh_ui()

    def _refresh_ui(self):
        self.setWindowTitle(f"✨ {cfg.AI_NAME} · AI 伴侣")
        self._hdr_avatar.setText(cfg.AI_NAME[0])
        self._hdr_name.setText(cfg.AI_NAME)

    def init_tts(self):
        """后台初始化 TTS，不阻塞窗口显示"""
        self._signals.busy.emit(True)
        self._status.setText("● 正在加载语音引擎…")
        self._status.setStyleSheet(
            "color: #FBBF24; font-size: 11px; background: transparent;")
        tts_ok = start_tts_service()
        if not tts_ok:
            logging.info("TTS not available — text-only mode")
        self._signals.busy.emit(False)

    # ── 消息管理 ─────────────────────────────────────────────────────────────
    def _add_msg(self, text: str, is_user: bool) -> MessageBubble:
        bubble = MessageBubble(text, is_user)
        n = self._chat_layout.count()
        self._chat_layout.insertWidget(n - 1, bubble)
        QApplication.processEvents()
        QTimer.singleShot(30, self._scroll_bottom)
        return bubble

    def _scroll_bottom(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── 发送 & 后台工作线程 ───────────────────────────────────────────────────
    def _send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._add_msg(text, is_user=True)
        self._input.clear()
        self._signals.busy.emit(True)
        threading.Thread(target=self._worker, args=(text,), daemon=True).start()

    def _worker(self, text: str):
        try:
            reply = get_ai_response(text)
            self._signals.ai_done.emit(reply)
            wav = get_tts_audio(reply)
            if wav:
                self._signals.tts_ready.emit(wav)
        except Exception as e:
            logging.error(f"Worker error: {e}")
            self._signals.error.emit("出错了呢～可能网络不太好 💦")
        finally:
            self._signals.busy.emit(False)

    # ── 信号槽（主线程执行，Qt 安全）────────────────────────────────────────
    def _on_ai_done(self, text: str):
        self._last_ai_bubble = self._add_msg(text, is_user=False)

    def _on_tts_ready(self, wav: bytes):
        if self._last_ai_bubble:
            self._last_ai_bubble.set_audio(wav)

    def _on_error(self, text: str):
        self._add_msg(text, is_user=False)

    def _set_busy(self, busy: bool):
        self._input.setEnabled(not busy)
        self._btn.setEnabled(not busy)
        if busy:
            self._typing.start()
            self._scroll_bottom()
            self._status.setText("● 正在回复…")
            self._status.setStyleSheet(
                "color: #FBBF24; font-size: 11px; background: transparent;")
        else:
            self._typing.stop()
            self._status.setText("● 在线")
            self._status.setStyleSheet(
                "color: #34D399; font-size: 11px; background: transparent;")
