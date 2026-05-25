"""
assistant.py — AI 伴侣聊天助手（入口）
"""
import os
import sys
import threading
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase, QFont

from config import ENV_FILE, cfg
from chat_window import ChatWindow
from tts_service import stop_tts_service
from settings_dialog import SettingsDialog

# ─── 日志 ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename="assistant.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
logging.info("Assistant started")

# ─── 入口 ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 高 DPI 缩放 — 必须在 QApplication 创建前设置
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 全局字体：优先 "Microsoft YaHei UI"，回退到 "Segoe UI"
    preferred = ["Microsoft YaHei UI", "Segoe UI", "PingFang SC"]
    families = QFontDatabase().families()
    chosen = next((f for f in preferred if f in families), "")
    if chosen:
        app.setFont(QFont(chosen, 10))

    # 首次启动：无 .env 或 API Key 为空时自动弹出设置
    if not os.path.exists(ENV_FILE) or not cfg.DEEPSEEK_API_KEY:
        cfg.create_default_env()
        dlg = SettingsDialog()
        if not dlg.exec_():
            sys.exit(0)

    # 先显示窗口，后台异步启动 TTS
    win = ChatWindow()
    win.show()
    threading.Thread(target=win.init_tts, daemon=True).start()

    ret = app.exec_()
    stop_tts_service()
    sys.exit(ret)
