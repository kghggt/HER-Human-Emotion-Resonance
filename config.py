"""
config.py — 从 .env 文件加载配置，支持运行时热更新和写回
"""
import os
import sys
from dotenv import load_dotenv, set_key

# PyInstaller 打包后 __file__ 指向临时目录，需要改用 exe 所在目录
if getattr(sys, "frozen", False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))

ENV_FILE = os.path.join(_APP_DIR, ".env")

# 默认值（恢复默认 / 首次创建 .env 时使用）
DEFAULTS = {
    "DEEPSEEK_API_KEY":  "",
    "DEEPSEEK_BASE_URL": "https://api.siliconflow.cn/v1",
    "DEEPSEEK_MODEL":    "deepseek-ai/DeepSeek-V3",
    "TEMPERATURE":       "0.8",
    "MAX_TOKENS":        "300",
    "SOVITS_URL":        "http://127.0.0.1:9880",
    "REFER_WAV_PATH":    "flag.wav",
    "PROMPT_TEXT":       "不过，既然现在意识到了，还不算晚。",
    "PROMPT_LANGUAGE":   "zh",
    "TEXT_LANGUAGE":     "zh",
    "AI_NAME":           "小雪",
    "SYSTEM_PROMPT":     "你是用户亲密的AI伴侣，回答温柔简短。",
    "MAX_HISTORY":       "20",
}

# 字段 -> 中文标签映射（供设置界面使用）
FIELD_LABELS = {
    "DEEPSEEK_API_KEY":  "API Key",
    "DEEPSEEK_BASE_URL": "API 地址",
    "DEEPSEEK_MODEL":    "模型名称",
    "TEMPERATURE":       "创意度 (Temperature)",
    "MAX_TOKENS":        "最大回复长度",
    "SOVITS_URL":        "TTS 服务地址",
    "REFER_WAV_PATH":    "参考音频路径",
    "PROMPT_TEXT":       "参考音频文本",
    "PROMPT_LANGUAGE":   "参考语言",
    "TEXT_LANGUAGE":     "合成语言",
    "AI_NAME":           "AI 名字",
    "SYSTEM_PROMPT":     "系统 Prompt",
    "MAX_HISTORY":       "对话历史轮数",
}


class Config:
    def __init__(self):
        self.reload()

    def reload(self):
        load_dotenv(ENV_FILE, override=True)

        def _get(key: str) -> str:
            return os.getenv(key, DEFAULTS.get(key, ""))

        def _require(key: str) -> str:
            val = os.getenv(key)
            if not val:
                print(f"[WARN] 缺少必要配置项: {key}，请填写 API Key")
            return val or ""

        self.DEEPSEEK_API_KEY  = _require("DEEPSEEK_API_KEY")
        self.DEEPSEEK_BASE_URL = _get("DEEPSEEK_BASE_URL")
        self.DEEPSEEK_MODEL    = _get("DEEPSEEK_MODEL")
        self.TEMPERATURE       = float(_get("TEMPERATURE"))
        self.MAX_TOKENS        = int(_get("MAX_TOKENS"))
        self.SOVITS_URL        = _get("SOVITS_URL")
        self.REFER_WAV_PATH    = _get("REFER_WAV_PATH")
        self.PROMPT_TEXT       = _get("PROMPT_TEXT")
        self.PROMPT_LANGUAGE   = _get("PROMPT_LANGUAGE")
        self.TEXT_LANGUAGE     = _get("TEXT_LANGUAGE")
        self.AI_NAME           = _get("AI_NAME")
        self.SYSTEM_PROMPT     = _get("SYSTEM_PROMPT")
        self.MAX_HISTORY       = int(_get("MAX_HISTORY"))

    def save_to_env(self, updates: dict) -> None:
        """将 updates 中的 key=value 写回 .env 文件"""
        for key, value in updates.items():
            if key in DEFAULTS:
                set_key(ENV_FILE, key, str(value))
        self.reload()

    @staticmethod
    def create_default_env() -> str:
        """首次运行时生成 .env 模板文件，返回文件路径"""
        if os.path.exists(ENV_FILE):
            return ENV_FILE
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write("# AI 伴侣 配置文件\n")
            f.write("# 请填写以下设置后重新启动程序\n\n")
            for key, value in DEFAULTS.items():
                if key == "DEEPSEEK_API_KEY":
                    f.write(f"{key}=在此填写你的 API Key\n")
                else:
                    f.write(f"{key}={value}\n")
        return ENV_FILE


cfg = Config()
