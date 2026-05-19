"""
assistant.py — AI 伴侣聊天助手（主程序）
修复: 线程安全 / 死循环 / 对话历史溢出 / API Key 泄露
"""
import os
import sys
import time
import socket
import subprocess
import threading
import logging
import tempfile
import winsound
import requests

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QLabel, QPushButton, QLineEdit,
    QFrame, QSizePolicy, QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QColor, QFont
from openai import OpenAI

from config import cfg
from settings_dialog import SettingsDialog

# ─── 日志 ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename="assistant.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
logging.info("Assistant started")

# ─── TTS 服务生命周期 ──────────────────────────────────────────────────────────
_tts_proc: subprocess.Popen | None = None


def _tts_is_running() -> bool:
    try:
        s = socket.create_connection(("127.0.0.1", 9880), timeout=1)
        s.close()
        return True
    except Exception:
        return False


def _find_tts_dir() -> str | None:
    """在与 exe 同级的目录中查找 GPT-SoVITS"""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(base, "GPT-SoVITS")
    return d if os.path.isdir(d) else None


def start_tts_service() -> bool:
    global _tts_proc
    if _tts_is_running():
        logging.info("TTS service already running")
        return True

    tts_dir = _find_tts_dir()
    if not tts_dir:
        logging.warning("GPT-SoVITS not found — text-only mode")
        return False

    python_exe = os.path.join(tts_dir, "runtime", "python.exe")
    api_script = os.path.join(tts_dir, "api2.py")
    if not os.path.exists(python_exe) or not os.path.exists(api_script):
        logging.warning("TTS runtime missing — text-only mode")
        return False

    try:
        _tts_proc = subprocess.Popen(
            [python_exe, api_script,
             "-s", "SoVITS_weights/Her_e8_s880.pth",
             "-g", "GPT_weights/Her-e15.ckpt"],
            cwd=tts_dir,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        logging.error(f"Failed to start TTS: {e}")
        return False

    # 轮询等待就绪
    for i in range(40):
        time.sleep(2)
        if _tts_is_running():
            logging.info(f"TTS ready after {i * 2}s")
            return True
    logging.warning("TTS startup timeout — text-only mode")
    return False


def stop_tts_service():
    global _tts_proc
    if _tts_proc:
        try:
            _tts_proc.terminate()
            _tts_proc.wait(timeout=5)
        except Exception:
            _tts_proc.kill()
        _tts_proc = None
        logging.info("TTS service stopped")


# ─── AI 客户端 ────────────────────────────────────────────────────────────────
_client: OpenAI | None = None
_history: list[dict] = []
_history_lock = threading.Lock()


def _ensure_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=cfg.DEEPSEEK_API_KEY, base_url=cfg.DEEPSEEK_BASE_URL)
    return _client


def get_ai_response(user_input: str) -> str:
    global _history
    with _history_lock:
        messages = [{"role": "system", "content": cfg.SYSTEM_PROMPT}]
        messages += _history
        messages.append({"role": "user", "content": user_input})

    client = _ensure_client()
    resp = client.chat.completions.create(
        model=cfg.DEEPSEEK_MODEL,
        messages=messages,
        temperature=cfg.TEMPERATURE,
        max_tokens=cfg.MAX_TOKENS,
        stream=False,
    )
    answer = resp.choices[0].message.content.strip()

    with _history_lock:
        _history.append({"role": "user", "content": user_input})
        _history.append({"role": "assistant", "content": answer})
        # 限制历史长度，避免 token 浪费
        if len(_history) > cfg.MAX_HISTORY:
            _history = _history[-cfg.MAX_HISTORY:]

    logging.info(f"AI replied, len={len(answer)}")
    return answer


def get_tts_audio(text: str) -> bytes | None:
    # 过滤 GBK 不支持的字符，避免 TTS 服务端崩溃
    safe_text = text.encode("gbk", errors="replace").decode("gbk")
    params = {
        "refer_wav_path": cfg.REFER_WAV_PATH,
        "prompt_text": cfg.PROMPT_TEXT,
        "prompt_language": cfg.PROMPT_LANGUAGE,
        "text": safe_text,
        "text_language": cfg.TEXT_LANGUAGE,
    }
    try:
        r = requests.get(cfg.SOVITS_URL, params=params, stream=True, timeout=60)
        if r.status_code == 200:
            logging.info("TTS OK")
            return r.content
        logging.error(f"TTS failed: {r.status_code}")
    except Exception as e:
        logging.error(f"TTS error: {e}")
    return None


def play_audio(wav_bytes: bytes) -> None:
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            tmp = f.name
        winsound.PlaySound(tmp, winsound.SND_FILENAME)
        os.unlink(tmp)
    except Exception as e:
        logging.error(f"Audio error: {e}")


# ─── Qt 信号（跨线程安全通信）──────────────────────────────────────────────────
class _Signals(QObject):
    ai_done    = pyqtSignal(str)   # AI 回复文本
    error      = pyqtSignal(str)   # 错误提示
    busy       = pyqtSignal(bool)  # 是否禁用输入


# ─── 消息气泡 ──────────────────────────────────────────────────────────────────
class MessageBubble(QFrame):
    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 5, 16, 5)
        layout.setSpacing(10)

        avatar = QLabel("我" if is_user else cfg.AI_NAME[0])
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            f"""background: {'qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7C3AED,stop:1 #DB2777)'
                              if is_user else
                              'qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0EA5E9,stop:1 #6366F1)'};
               border-radius: 18px; color: white;
               font-weight: bold; font-size: 12px;"""
        )

        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setTextFormat(Qt.PlainText)
        bubble.setMaximumWidth(360)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        if is_user:
            bubble.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 #7C3AED, stop:1 #DB2777);
                    color: white; border-radius: 16px;
                    border-bottom-right-radius: 3px;
                    padding: 10px 14px; font-size: 14px;
                }""")
            layout.addStretch()
            layout.addWidget(bubble)
            layout.addWidget(avatar)
        else:
            bubble.setStyleSheet("""
                QLabel {
                    background-color: #1E1E3A; color: #E2E8F0;
                    border: 1px solid #2D2D50;
                    border-radius: 16px; border-bottom-left-radius: 3px;
                    padding: 10px 14px; font-size: 14px;
                }""")
            layout.addWidget(avatar)
            layout.addWidget(bubble)
            layout.addStretch()

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 70))
        shadow.setOffset(0, 2)
        bubble.setGraphicsEffect(shadow)


# ─── 输入中动画 ────────────────────────────────────────────────────────────────
class TypingDots(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 5, 16, 5)
        layout.setSpacing(10)

        avatar = QLabel(cfg.AI_NAME[0])
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("""background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 #0EA5E9, stop:1 #6366F1);
            border-radius: 18px; color:white; font-weight:bold; font-size:12px;""")

        self._lbl = QLabel("● ○ ○")
        self._lbl.setStyleSheet("""QLabel {
            background-color: #1E1E3A; color: #8888BB;
            border: 1px solid #2D2D50; border-radius: 16px;
            border-bottom-left-radius: 3px;
            padding: 10px 18px; font-size: 14px;}""")

        layout.addWidget(avatar)
        layout.addWidget(self._lbl)
        layout.addStretch()

        self._step = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def _tick(self):
        frames = ["● ○ ○", "○ ● ○", "○ ○ ●"]
        self._step = (self._step + 1) % 3
        self._lbl.setText(frames[self._step])

    def start(self):
        self._timer.start(400)
        self.setVisible(True)

    def stop(self):
        self._timer.stop()
        self.setVisible(False)


# ─── 主窗口 ────────────────────────────────────────────────────────────────────
class ChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._signals = _Signals()
        self._signals.ai_done.connect(self._on_ai_done)
        self._signals.error.connect(self._on_error)
        self._signals.busy.connect(self._set_busy)

        self._build_ui()
        self._add_msg(f"嘿～我是{cfg.AI_NAME}，有什么想和我聊的吗？💗", is_user=False)

    # ── 构建 UI ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setWindowTitle(f"✨ {cfg.AI_NAME} · AI 伴侣")
        self.resize(500, 760)
        self.setMinimumSize(400, 580)
        self.setStyleSheet("background-color: #0A0A1B;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_chat_area(), stretch=1)
        root.addWidget(self._build_divider())
        root.addWidget(self._build_input_area())

    def _build_header(self) -> QFrame:
        hdr = QFrame()
        hdr.setFixedHeight(68)
        hdr.setStyleSheet("""QFrame {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #12122A, stop:1 #1A1A3E);
            border-bottom: 1px solid #2D2D50;}""")

        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(20, 0, 20, 0)

        av = QLabel(cfg.AI_NAME[0])
        av.setFixedSize(42, 42)
        av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet("""background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 #0EA5E9, stop:1 #6366F1);
            border-radius:21px; color:white; font-weight:bold; font-size:15px;""")

        info = QVBoxLayout()
        info.setSpacing(1)
        name = QLabel(cfg.AI_NAME)
        name.setStyleSheet("color:#E2E8F0; font-size:15px; font-weight:bold;")
        self._status = QLabel("● 在线")
        self._status.setStyleSheet("color:#34D399; font-size:11px;")
        info.addWidget(name)
        info.addWidget(self._status)

        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(36, 36)
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #8888BB;
                font-size: 18px; border: none; border-radius: 18px; }
            QPushButton:hover { background: #2D2D50; color: #E2E8F0; }
        """)
        settings_btn.clicked.connect(self._open_settings)

        lay.addWidget(av)
        lay.addSpacing(12)
        lay.addLayout(info)
        lay.addStretch()
        lay.addWidget(settings_btn)
        return hdr

    def _build_chat_area(self) -> QScrollArea:
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { border:none; background:#0A0A1B; }
            QScrollBar:vertical { background:#0A0A1B; width:5px; }
            QScrollBar::handle:vertical { background:#3D3D6B; border-radius:2px; min-height:20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }""")

        self._chat_widget = QWidget()
        self._chat_widget.setStyleSheet("background:#0A0A1B;")
        self._chat_layout = QVBoxLayout(self._chat_widget)
        self._chat_layout.setContentsMargins(0, 12, 0, 12)
        self._chat_layout.setSpacing(2)
        self._chat_layout.addStretch()

        self._typing = TypingDots()
        self._typing.setVisible(False)
        self._chat_layout.addWidget(self._typing)

        self._scroll.setWidget(self._chat_widget)
        return self._scroll

    def _build_divider(self) -> QFrame:
        d = QFrame()
        d.setFixedHeight(1)
        d.setStyleSheet("background:#1E1E38;")
        return d

    def _build_input_area(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(76)
        bar.setStyleSheet("background:#0D0D22;")

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        self._input = QLineEdit()
        self._input.setPlaceholderText("说点什么吧～")
        self._input.setFixedHeight(48)
        self._input.setStyleSheet("""
            QLineEdit {
                background:#1E1E38; color:#E2E8F0;
                border:1.5px solid #3D3D6B; border-radius:24px;
                padding: 0 18px; font-size:14px;}
            QLineEdit:focus { border-color:#7C3AED; }""")

        self._btn = QPushButton("发送")
        self._btn.setFixedSize(70, 48)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #7C3AED, stop:1 #DB2777);
                color:white; font-weight:bold; font-size:13px;
                border-radius:24px; border:none;}
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #6D28D9, stop:1 #BE185D);}
            QPushButton:pressed {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #5B21B6, stop:1 #9D174D);}
            QPushButton:disabled { background:#2D2D50; color:#6B6B9E; }""")

        self._input.returnPressed.connect(self._send)
        self._btn.clicked.connect(self._send)

        lay.addWidget(self._input)
        lay.addWidget(self._btn)
        return bar

    # ── 设置 ─────────────────────────────────────────────────────────────────
    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_():
            global _client
            _client = None  # 重建客户端以使用新的 API Key
            self._refresh_ui()

    def _refresh_ui(self):
        self.setWindowTitle(f"✨ {cfg.AI_NAME} · AI 伴侣")
        hdr = self.layout().itemAt(0).widget()
        hdr_lay = hdr.layout()
        hdr_lay.itemAt(2).widget().setText(cfg.AI_NAME[0])
        name_label = hdr_lay.itemAt(3).itemAt(0).widget()
        name_label.setText(cfg.AI_NAME)

    def _init_tts(self):
        """后台初始化 TTS，不阻塞窗口显示"""
        self._signals.busy.emit(True)
        self._status.setText("● 正在加载语音引擎…")
        self._status.setStyleSheet("color:#FBBF24; font-size:11px;")
        tts_ok = start_tts_service()
        if not tts_ok:
            import logging
            logging.info("TTS not available — text-only mode")
        self._signals.busy.emit(False)

    # ── 消息管理 ─────────────────────────────────────────────────────────────
    def _add_msg(self, text: str, is_user: bool):
        bubble = MessageBubble(text, is_user)
        # 插入到 typing 指示器之前
        n = self._chat_layout.count()
        self._chat_layout.insertWidget(n - 1, bubble)
        QApplication.processEvents()
        QTimer.singleShot(30, self._scroll_bottom)

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
                threading.Thread(target=play_audio, args=(wav,), daemon=True).start()
        except Exception as e:
            logging.error(f"Worker error: {e}")
            self._signals.error.emit("出错了呢～可能网络不太好 💦")
        finally:
            self._signals.busy.emit(False)

    # ── 信号槽（主线程执行，Qt 安全）────────────────────────────────────────
    def _on_ai_done(self, text: str):
        self._add_msg(text, is_user=False)

    def _on_error(self, text: str):
        self._add_msg(text, is_user=False)

    def _set_busy(self, busy: bool):
        self._input.setEnabled(not busy)
        self._btn.setEnabled(not busy)
        if busy:
            self._typing.start()
            self._scroll_bottom()
            self._status.setText("● 正在回复…")
            self._status.setStyleSheet("color:#FBBF24; font-size:11px;")
        else:
            self._typing.stop()
            self._status.setText("● 在线")
            self._status.setStyleSheet("color:#34D399; font-size:11px;")


# ─── 入口 ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 首次启动：无 .env 或 API Key 为空时自动弹出设置
    from config import ENV_FILE, cfg
    if not os.path.exists(ENV_FILE) or not cfg.DEEPSEEK_API_KEY:
        from settings_dialog import SettingsDialog
        cfg.create_default_env()
        dlg = SettingsDialog()
        if not dlg.exec_():
            sys.exit(0)

    # 先显示窗口，后台异步启动 TTS
    win = ChatWindow()
    win.show()
    threading.Thread(target=win._init_tts, daemon=True).start()

    ret = app.exec_()
    stop_tts_service()
    sys.exit(ret)
