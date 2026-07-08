# -*- coding: utf-8 -*-
"""MiniMax image generation provider.

API: POST https://api.minimaxi.com/v1/image_generation
Model: image-01 (Hailuo / 海螺图像)
Auth: Bearer token (no group_id needed)
Returns image URL, we download to local file.

Get key: https://platform.minimaxi.com -> API Key
"""

import json
import os
import urllib.request
import urllib.error
from pathlib import Path

URL = "https://api.minimaxi.com/v1/image_generation"
MODEL = "image-01"


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


def generate(prompt, out_path, size="720x960"):
    """Generate an image and save to out_path. Returns out_path.

    Args:
        prompt: text description of the image
        out_path: where to save the jpg
        size: WxH string, converted to aspect_ratio (e.g. 720x960 -> "3:4")
    """
    key = _env("MINIMAX_API_KEY")
    if not key:
        raise RuntimeError("Missing MINIMAX_API_KEY in .env")

    # Convert pixel size to aspect ratio
    w, h = (int(x) for x in size.lower().split("x"))
    ratios = {(1,1):"1:1",(3,4):"3:4",(4,3):"4:3",(9,16):"9:16",(16,9):"16:9"}
    from math import gcd
    g = gcd(w, h)
    ar = ratios.get((w//g, h//g))
    if not ar:
        # pick closest from common ratios
        r = w / h
        ar = "3:4" if r < 0.85 else ("4:3" if r > 1.15 else "1:1")

    body = {
        "model": MODEL,
        "prompt": prompt,
        "aspect_ratio": ar,
        "response_format": "url",
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=90)
        data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        raise RuntimeError("MiniMax HTTP %s: %s" % (e.code, detail))
    if data.get("base_resp", {}).get("status_code", -1) != 0:
        raise RuntimeError("MiniMax error: %s" % json.dumps(data.get("base_resp", {}), ensure_ascii=False))
    urls = data.get("data", {}).get("image_urls", [])
    if not urls:
        raise RuntimeError("MiniMax returned no image URLs")
    # Download the image
    img_req = urllib.request.Request(urls[0], headers={"User-Agent": "Mozilla/5.0"})
    img_data = urllib.request.urlopen(img_req, timeout=60).read()
    if len(img_data) < 5000:
        raise RuntimeError("MiniMax image too small (%d bytes)" % len(img_data))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(img_data)
    return out_path


if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else "A lonely man in a rainy Latin American town, oil painting, cinematic"
    out = sys.argv[2] if len(sys.argv) > 2 else "work/minimax_test.jpg"
    print("Generating:", p[:60])
    generate(p, out)
    print("Saved:", out, Path(out).stat().st_size, "bytes")
