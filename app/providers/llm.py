"""LLM Provider —— 智谱 glm-4-flash(paas/v4 OpenAI 协议,免费)。

Research/Script/Storyboard 等共用,换厂商(豆包/通义/OpenAI)只改这里(原则2)。
Key 从项目根 .env 读(原则6,不硬编码)。
"""

import json
import os
import re
from pathlib import Path

from openai import OpenAI

_KEY = os.getenv("ZHIPUAI_API_KEY")
if not _KEY:
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("ZHIPUAI_API_KEY="):
                _KEY = line.split("=", 1)[1].strip()
                break
if not _KEY:
    raise RuntimeError("没找到 ZHIPUAI_API_KEY,请检查项目根 .env")

_client = OpenAI(api_key=_KEY, base_url="https://open.bigmodel.cn/api/paas/v4")
MODEL = "glm-4-flash"


def chat(prompt: str, system: str = "你是助手,用中文回答。") -> str:
    resp = _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


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
