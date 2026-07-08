# -*- coding: utf-8 -*-
"""通义千问万相图片生成 Provider (wanxiang/text2image).
Credentials from .env: DASHSCOPE_API_KEY
Model: wanxiang2.1-t2i-turbo (fast) or wanxiang-v1
Async task mode: submit -> poll -> download.
"""

import json
import os
import time
import urllib.request
from pathlib import Path

URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
MODEL = "wanxiang2.1-t2i-turbo"


def _key():
    k = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if k:
        return k
    env = Path(__file__).resolve().parents[2] / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DASHSCOPE_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


def generate(prompt, out_path, size="720*960", model=MODEL, n=1):
    """Generate image and save to out_path. Returns out_path."""
    api_key = _key()
    if not api_key:
        raise RuntimeError("Missing DASHSCOPE_API_KEY in .env")
    # size format for wanxiang: "720*960" not "720x960"
    sz = size.replace("x", "*")
    body = {
        "model": model,
        "input": {"prompt": prompt},
        "parameters": {"size": sz, "n": n},
    }
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        },
    )
    resp = urllib.request.urlopen(req, timeout=60)
    data = json.loads(resp.read().decode("utf-8"))
    task_id = data.get("output", {}).get("task_id")
    if not task_id:
        raise RuntimeError("Wanxiang submit failed: " + json.dumps(data, ensure_ascii=False)[:300])

    # poll
    poll_url = "https://dashscope.aliyuncs.com/api/v1/tasks/" + task_id
    for _ in range(60):
        time.sleep(2)
        req2 = urllib.request.Request(poll_url, headers={"Authorization": "Bearer " + api_key})
        r = urllib.request.urlopen(req2, timeout=30)
        d = json.loads(r.read().decode("utf-8"))
        status = d.get("output", {}).get("task_status")
        if status == "SUCCEEDED":
            results = d.get("output", {}).get("results", [])
            if not results:
                raise RuntimeError("Wanxiang no results: " + json.dumps(d, ensure_ascii=False)[:200])
            img_url = results[0].get("url")
            img = urllib.request.urlopen(img_url, timeout=90).read()
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_bytes(img)
            return out_path
        if status == "FAILED":
            raise RuntimeError("Wanxiang task failed: " + json.dumps(d, ensure_ascii=False)[:300])
    raise RuntimeError("Wanxiang task timeout (120s)")
