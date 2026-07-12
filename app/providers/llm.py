"""LLM Provider —— 智谱 glm-4.7 (Anthropic端点) 为主, MiniMax-Text-01 兜底。

glm-4.7 走智谱 Anthropic 兼容端点 (open.bigmodel.cn/api/anthropic),
文案质量最高。MiniMax-Text-01 作 fallback。
Key 从项目根 .env 或环境变量读。
"""

import json
import os
import re
import urllib.request
import urllib.error
from pathlib import Path


def _env(name):
    val = os.getenv(name, "").strip()
    if val:
        return val
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith(name + "="):
                return line.split("=", 1)[1].strip()
    return ""


# ===== Provider 配置 =====
_ANTHROPIC_KEY = _env("ANTHROPIC_API_KEY")
_ANTHROPIC_URL = (_env("ANTHROPIC_BASE_URL") or "https://open.bigmodel.cn/api/anthropic").rstrip("/") + "/v1/messages"
_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"  # 映射到 glm-4.7

_MINIMAX_KEY = _env("MINIMAX_API_KEY")
_MINIMAX_URL = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
_MINIMAX_MODEL = "MiniMax-Text-01"


def _anthropic_chat(prompt, system):
    """调用智谱 Anthropic 兼容端点 (glm-4.7)."""
    body = {
        "model": _ANTHROPIC_MODEL,
        "max_tokens": 2048,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        _ANTHROPIC_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "x-api-key": _ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )
    resp = urllib.request.urlopen(req, timeout=90)
    data = json.loads(resp.read().decode("utf-8"))
    blocks = data.get("content", [])
    texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    if not texts:
        raise RuntimeError("Anthropic endpoint returned no text: %s" % str(data)[:200])
    return "\n".join(texts).strip()


def _minimax_chat(prompt, system):
    """调用 MiniMax chatcompletion_v2."""
    body = {
        "model": _MINIMAX_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        _MINIMAX_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + _MINIMAX_KEY, "Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=90)
    data = json.loads(resp.read().decode("utf-8"))
    if data.get("base_resp", {}).get("status_code", -1) != 0:
        raise RuntimeError("MiniMax error: %s" % json.dumps(data.get("base_resp", {}), ensure_ascii=False)[:200])
    return data["choices"][0]["message"]["content"].strip()


def chat(prompt, system="你是助手,用中文回答。"):
    """优先 glm-4.7 (Anthropic端点), 失败回退 MiniMax-Text-01."""
    if _ANTHROPIC_KEY:
        try:
            return _anthropic_chat(prompt, system)
        except Exception as e:
            print("  [LLM] Anthropic/glm-4.7 failed (%s), trying MiniMax..." % str(e)[:80])
    if _MINIMAX_KEY:
        try:
            return _minimax_chat(prompt, system)
        except Exception as e:
            print("  [LLM] MiniMax failed (%s)" % str(e)[:80])
    raise RuntimeError("没有可用的 LLM (需 ANTHROPIC_API_KEY 或 MINIMAX_API_KEY)")


def chat_json(prompt, system="严格只输出 JSON。"):
    text = chat(prompt, system)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("LLM 没返回 JSON 对象: %s" % text[:200])
    return json.loads(m.group(0))


def chat_list(prompt, system="严格只输出 JSON 数组。"):
    text = chat(prompt, system)
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        raise ValueError("LLM 没返回 JSON 数组: %s" % text[:200])
    return json.loads(m.group(0))
