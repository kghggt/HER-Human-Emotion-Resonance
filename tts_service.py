"""
tts_service.py — GPT-SoVITS TTS 服务生命周期管理 + 语音合成与播放
"""
import os
import sys
import time
import socket
import subprocess
import tempfile
import winsound
import logging
import re
import requests

from config import cfg

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


# ─── 语音合成与播放 ────────────────────────────────────────────────────────────
# 正则：匹配括号/星号内的动作描述
# 支持：（害羞） (微笑) 【轻声】 [撦嘴] *摸头*
_STAGE_DIR_RE = re.compile(
    r"[\uff08\(\u3010\[].*?[\uff09\)\u3011\]]"  # 括号类
    r"|\*[^*]+\*"                                 # *动作*
)


def _strip_stage_directions(text: str) -> str:
    """移除括号/星号内的动作描述，让 TTS 只念“说的话”"""
    cleaned = _STAGE_DIR_RE.sub("", text)
    # 清理多余空格
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def get_tts_audio(text: str) -> bytes | None:
    # 去掉动作/神态描述，只合成“说的话”
    spoken_text = _strip_stage_directions(text)
    if not spoken_text:
        return None
    # 过滤 GBK 不支持的字符，避免 TTS 服务端崩溃
    safe_text = spoken_text.encode("gbk", errors="replace").decode("gbk")
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
