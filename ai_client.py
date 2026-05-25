"""
ai_client.py — AI 对话客户端，管理 OpenAI 兼容 API 调用与对话历史
"""
import threading
import logging
from openai import OpenAI

from config import cfg

# ─── AI 客户端 ────────────────────────────────────────────────────────────────
_client: OpenAI | None = None
_history: list[dict] = []
_history_lock = threading.Lock()


def _ensure_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=cfg.DEEPSEEK_API_KEY, base_url=cfg.DEEPSEEK_BASE_URL)
    return _client


def reset_client() -> None:
    """重建客户端（在 API Key / Base URL 变更后调用）"""
    global _client
    _client = None


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
