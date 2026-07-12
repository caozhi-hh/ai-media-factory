"""LLM Provider —— MiniMax Text-01 为主, 智谱 glm-4-flash 兜底。

MiniMax-Text-01 写文案质量高、字数足(200+字), 智谱免费模型做 fallback。
Research/Script/Storyboard 等共用, 换厂商只改这里。
Key 从项目根 .env 读。
"""

import json
import os
import re
import urllib.request
import urllib.error
from pathlib import Path

from openai import OpenAI


def _env(name):
    """从环境变量或 .env 文件读 key."""
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
_MINIMAX_KEY = _env("MINIMAX_API_KEY")
_ZHIPU_KEY = _env("ZHIPUAI_API_KEY")

# MiniMax (主): 文案质量高, 字数足
_MINIMAX_URL = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
_MINIMAX_MODEL = "MiniMax-Text-01"

# 智谱 (兜底): OpenAI 兼容协议, glm-4-flash 免费
_zhipu_client = None
if _ZHIPU_KEY:
    _zhipu_client = OpenAI(api_key=_ZHIPU_KEY, base_url="https://open.bigmodel.cn/api/paas/v4")
_ZHIPU_MODEL = "glm-4-flash"


def _minimax_chat(prompt: str, system: str) -> str:
    """调用 MiniMax chatcompletion_v2 (类 OpenAI 协议)."""
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
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("MiniMax no choices")
    return choices[0]["message"]["content"].strip()


def _zhipu_chat(prompt: str, system: str) -> str:
    """调用智谱 glm-4-flash (OpenAI 兼容)."""
    if not _zhipu_client:
        raise RuntimeError("ZHIPUAI_API_KEY 未配置")
    resp = _zhipu_client.chat.completions.create(
        model=_ZHIPU_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


def chat(prompt: str, system: str = "你是助手,用中文回答。") -> str:
    """主用 MiniMax-Text-01, 失败回退智谱 glm-4-flash."""
    if _MINIMAX_KEY:
        try:
            return _minimax_chat(prompt, system)
        except Exception as e:
            print("  [LLM] MiniMax failed (%s), falling back to Zhipu..." % str(e)[:80])
    if _zhipu_client:
        return _zhipu_chat(prompt, system)
    raise RuntimeError("没有可用的 LLM key (MINIMAX_API_KEY / ZHIPUAI_API_KEY 都没配)")


def chat_json(prompt: str, system: str = "严格只输出 JSON。") -> dict:
    """要求 LLM 输出 JSON 对象,容错提取首个 {...}。"""
    text = chat(prompt, system)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"LLM 没返回 JSON 对象:{text[:200]}")
    return json.loads(m.group(0))


def chat_list(prompt: str, system: str = "严格只输出 JSON 数组。") -> list:
    """要求 LLM 输出 JSON 数组,容错提取首个 [...]."""
    text = chat(prompt, system)
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        raise ValueError(f"LLM 没返回 JSON 数组:{text[:200]}")
    return json.loads(m.group(0))
