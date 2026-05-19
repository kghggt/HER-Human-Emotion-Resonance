"""
settings_dialog.py — 设置对话框，可视化编辑所有配置项
"""
from PyQt5.QtWidgets import (
    QDialog, QTabWidget, QWidget, QFormLayout, QLineEdit,
    QSlider, QSpinBox, QComboBox, QTextEdit, QPushButton,
    QHBoxLayout, QVBoxLayout, QFileDialog, QLabel, QMessageBox,
)
from PyQt5.QtCore import Qt
from config import cfg, DEFAULTS, FIELD_LABELS


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(520, 480)
        self.setMinimumSize(460, 400)
        self.setStyleSheet("""
            QDialog { background-color: #0A0A1B; }
            QTabWidget::pane { border: 1px solid #2D2D50; background: #0D0D22; }
            QTabBar::tab {
                background: #1E1E38; color: #8888BB; padding: 8px 20px;
                border: 1px solid #2D2D50; border-bottom: none;
                border-top-left-radius: 8px; border-top-right-radius: 8px;
            }
            QTabBar::tab:selected { background: #0D0D22; color: #E2E8F0; }
            QLabel { color: #A0A0CC; font-size: 13px; }
            QLineEdit, QTextEdit, QSpinBox, QComboBox {
                background: #1E1E38; color: #E2E8F0;
                border: 1px solid #3D3D6B; border-radius: 6px;
                padding: 6px 10px; font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus { border-color: #7C3AED; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #1E1E38; color: #E2E8F0;
                selection-background-color: #7C3AED; border: 1px solid #3D3D6B;
            }
            QSlider::groove:horizontal {
                height: 6px; background: #1E1E38; border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px; margin: -5px 0; background: #7C3AED;
                border-radius: 8px;
            }
            QPushButton {
                border-radius: 8px; padding: 8px 20px;
                font-size: 13px; font-weight: bold;
            }
        """)

        self._build_ui()
        self._load_values()

    def _build_ui(self):
        root = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._llm_tab(), "LLM 模型")
        tabs.addTab(self._tts_tab(), "TTS 语音")
        tabs.addTab(self._persona_tab(), "角色设定")
        root.addWidget(tabs)

        # 底部按钮
        btn_row = QHBoxLayout()

        reset_btn = QPushButton("恢复默认")
        reset_btn.setStyleSheet("""
            QPushButton { background: #2D2D50; color: #A0A0CC; }
            QPushButton:hover { background: #3D3D6B; }
        """)
        reset_btn.clicked.connect(self._reset_defaults)

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton { background: #2D2D50; color: #A0A0CC; }
            QPushButton:hover { background: #3D3D6B; }
        """)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #7C3AED, stop:1 #DB2777);
                color: white;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #6D28D9, stop:1 #BE185D);
            }
        """)
        save_btn.clicked.connect(self._save)

        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

    def _make_form(self) -> QFormLayout:
        form = QFormLayout()
        form.setContentsMargins(20, 16, 20, 16)
        form.setSpacing(10)
        return form

    # ── LLM 页 ───────────────────────────────────────────────────────────────
    def _llm_tab(self) -> QWidget:
        w = QWidget()
        form = self._make_form()

        self.llm_key = QLineEdit()
        self.llm_key.setEchoMode(QLineEdit.Password)
        self.llm_key.setPlaceholderText("sk-xxxxxxxx")
        form.addRow("API Key *", self.llm_key)

        self.llm_url = QLineEdit()
        form.addRow("API 地址", self.llm_url)

        self.llm_model = QLineEdit()
        form.addRow("模型名称", self.llm_model)

        self.llm_temp = QSlider(Qt.Horizontal)
        self.llm_temp.setRange(0, 20)
        self.llm_temp_label = QLabel("0.8")
        temp_row = QHBoxLayout()
        temp_row.addWidget(self.llm_temp)
        temp_row.addWidget(self.llm_temp_label)
        self.llm_temp.valueChanged.connect(
            lambda v: self.llm_temp_label.setText(f"{v/10:.1f}")
        )
        form.addRow("创意度", temp_row)

        self.llm_tokens = QSpinBox()
        self.llm_tokens.setRange(50, 2000)
        self.llm_tokens.setSingleStep(50)
        form.addRow("最大回复长度", self.llm_tokens)

        w.setLayout(form)
        return w

    # ── TTS 页 ───────────────────────────────────────────────────────────────
    def _tts_tab(self) -> QWidget:
        w = QWidget()
        form = self._make_form()

        self.tts_url = QLineEdit()
        form.addRow("TTS 服务地址", self.tts_url)

        self.tts_wav = QLineEdit()
        wav_row = QHBoxLayout()
        wav_row.addWidget(self.tts_wav)
        pick_btn = QPushButton("浏览...")
        pick_btn.setStyleSheet("""
            QPushButton { background: #2D2D50; color: #A0A0CC;
                padding: 6px 14px; border-radius: 6px; font-size: 12px; }
            QPushButton:hover { background: #3D3D6B; }
        """)
        pick_btn.clicked.connect(lambda: self._pick_wav())
        wav_row.addWidget(pick_btn)
        form.addRow("参考音频", wav_row)

        self.tts_prompt = QLineEdit()
        form.addRow("参考文本", self.tts_prompt)

        self.tts_plang = QComboBox()
        self.tts_plang.addItems(["zh", "en", "ja"])
        form.addRow("参考语言", self.tts_plang)

        self.tts_tlang = QComboBox()
        self.tts_tlang.addItems(["zh", "en", "ja"])
        form.addRow("合成语言", self.tts_tlang)

        w.setLayout(form)
        return w

    # ── 角色页 ──────────────────────────────────────────────────────────────
    def _persona_tab(self) -> QWidget:
        w = QWidget()
        form = self._make_form()

        self.per_name = QLineEdit()
        form.addRow("AI 名字", self.per_name)

        self.per_prompt = QTextEdit()
        self.per_prompt.setMaximumHeight(160)
        form.addRow("系统 Prompt", self.per_prompt)

        self.per_history = QSpinBox()
        self.per_history.setRange(4, 100)
        form.addRow("对话历史轮数", self.per_history)

        w.setLayout(form)
        return w

    # ── 数据读写 ──────────────────────────────────────────────────────────────
    def _load_values(self):
        self.llm_key.setText(cfg.DEEPSEEK_API_KEY)
        self.llm_url.setText(cfg.DEEPSEEK_BASE_URL)
        self.llm_model.setText(cfg.DEEPSEEK_MODEL)
        temp_int = int(cfg.TEMPERATURE * 10)
        self.llm_temp.setValue(temp_int)
        self.llm_temp_label.setText(f"{temp_int/10:.1f}")
        self.llm_tokens.setValue(cfg.MAX_TOKENS)

        self.tts_url.setText(cfg.SOVITS_URL)
        self.tts_wav.setText(cfg.REFER_WAV_PATH)
        self.tts_prompt.setText(cfg.PROMPT_TEXT)
        self.tts_plang.setCurrentText(cfg.PROMPT_LANGUAGE)
        self.tts_tlang.setCurrentText(cfg.TEXT_LANGUAGE)

        self.per_name.setText(cfg.AI_NAME)
        self.per_prompt.setPlainText(cfg.SYSTEM_PROMPT)
        self.per_history.setValue(cfg.MAX_HISTORY)

    def _save(self):
        if not self.llm_key.text().strip():
            QMessageBox.warning(self, "提示", "API Key 不能为空")
            return

        updates = {
            "DEEPSEEK_API_KEY":  self.llm_key.text().strip(),
            "DEEPSEEK_BASE_URL": self.llm_url.text().strip(),
            "DEEPSEEK_MODEL":    self.llm_model.text().strip(),
            "TEMPERATURE":       self.llm_temp.value() / 10,
            "MAX_TOKENS":        self.llm_tokens.value(),
            "SOVITS_URL":        self.tts_url.text().strip(),
            "REFER_WAV_PATH":    self.tts_wav.text().strip(),
            "PROMPT_TEXT":       self.tts_prompt.text().strip(),
            "PROMPT_LANGUAGE":   self.tts_plang.currentText(),
            "TEXT_LANGUAGE":     self.tts_tlang.currentText(),
            "AI_NAME":           self.per_name.text().strip(),
            "SYSTEM_PROMPT":     self.per_prompt.toPlainText().strip(),
            "MAX_HISTORY":       self.per_history.value(),
        }
        cfg.save_to_env(updates)
        self.accept()

    def _reset_defaults(self):
        self.llm_key.clear()
        self.llm_url.setText(DEFAULTS["DEEPSEEK_BASE_URL"])
        self.llm_model.setText(DEFAULTS["DEEPSEEK_MODEL"])
        self.llm_temp.setValue(int(float(DEFAULTS["TEMPERATURE"]) * 10))
        self.llm_tokens.setValue(int(DEFAULTS["MAX_TOKENS"]))
        self.tts_url.setText(DEFAULTS["SOVITS_URL"])
        self.tts_wav.setText(DEFAULTS["REFER_WAV_PATH"])
        self.tts_prompt.setText(DEFAULTS["PROMPT_TEXT"])
        self.tts_plang.setCurrentText(DEFAULTS["PROMPT_LANGUAGE"])
        self.tts_tlang.setCurrentText(DEFAULTS["TEXT_LANGUAGE"])
        self.per_name.setText(DEFAULTS["AI_NAME"])
        self.per_prompt.setPlainText(DEFAULTS["SYSTEM_PROMPT"])
        self.per_history.setValue(int(DEFAULTS["MAX_HISTORY"]))

    def _pick_wav(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择参考音频", "", "WAV 文件 (*.wav);;所有文件 (*)")
        if path:
            self.tts_wav.setText(path)
