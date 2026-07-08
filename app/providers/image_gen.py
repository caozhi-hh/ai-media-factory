"""Image Generation Provider —— 智谱 CogView 按文案生成油画风场景图(原则2)。
换图像厂商(即梦/Seedream)只改这里,不影响 Skill。"""

import json
import os
import urllib.request
from pathlib import Path

URL = "https://open.bigmodel.cn/api/paas/v4/images/generations"


def _key() -> str:
    k = os.getenv("ZHIPUAI_API_KEY")
    if not k:
        env = Path(__file__).resolve().parents[2] / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("ZHIPUAI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return k


def generate(prompt: str, out: str, size: str = "720x960", model: str = "cogview-3-flash") -> str:
    body = {"model": model, "prompt": prompt, "size": size}
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.loads(resp.read().decode("utf-8"))
    url = data["data"][0]["url"]
    img = urllib.request.urlopen(url, timeout=90).read()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(img)
    return out
