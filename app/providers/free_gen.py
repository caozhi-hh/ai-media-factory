# -*- coding: utf-8 -*-
"""Free image generation provider.

Tries multiple free endpoints in order:
1. Pollinations.AI (flux / turbo) - no key needed, but may rate-limit
2. Hugging Face Inference API (FLUX.1-schnell) - needs HF token, free tier
3. CogView (Zhipu) - existing fallback

Returns the first successful result.
"""
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Optional HF token
HF_TOKEN = os.getenv("HF_TOKEN", "")


def _env(p: Path) -> str:
    env = p / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("HF_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _pollinations(prompt: str, out: str, width: int = 720, height: int = 960,
                  model: str = "flux", seed: int = 42) -> str:
    """Pollinations.AI - free, no API key. Direct image download."""
    enc = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{enc}?width={width}&height={height}&model={model}&nologo=true&seed={seed}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "image/*",
    })
    # Pollinations may take time to generate; retry up to 4 times
    last_err = None
    for attempt in range(4):
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            data = resp.read()
            if len(data) > 5000:  # valid image, not error page
                Path(out).parent.mkdir(parents=True, exist_ok=True)
                Path(out).write_bytes(data)
                return out
            last_err = f"response too small ({len(data)} bytes)"
        except Exception as e:
            last_err = str(e)
        time.sleep(3)
    raise RuntimeError(f"Pollinations failed: {last_err}")


def _huggingface(prompt: str, out: str, width: int = 720, height: int = 960) -> str:
    """Hugging Face Inference API - FLUX.1-schnell (free tier, no token works for some models)."""
    token = HF_TOKEN or _env(_root())
    models = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-xl-base-1.0",
    ]
    for model in models:
        url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        body = json.dumps({
            "inputs": prompt,
            "parameters": {"width": width, "height": height, "num_inference_steps": 4},
        }).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=body, headers=headers)
            resp = urllib.request.urlopen(req, timeout=120)
            data = resp.read()
            if len(data) > 5000:
                Path(out).parent.mkdir(parents=True, exist_ok=True)
                Path(out).write_bytes(data)
                return out
        except Exception as e:
            err = str(e)
            # 503 = model loading, retry once
            if "503" in err:
                time.sleep(15)
                try:
                    req = urllib.request.Request(url, data=body, headers=headers)
                    resp = urllib.request.urlopen(req, timeout=120)
                    data = resp.read()
                    if len(data) > 5000:
                        Path(out).parent.mkdir(parents=True, exist_ok=True)
                        Path(out).write_bytes(data)
                        return out
                except Exception:
                    pass
            continue
    raise RuntimeError("All HF models failed")


def generate(prompt: str, out: str, size: str = "720x960") -> str:
    """Try free providers in order. Falls back to CogView."""
    w, h = (int(x) for x in size.replace("*", "x").split("x"))

    # 1. Pollinations (truly free, no key)
    try:
        return _pollinations(prompt, out, width=w, height=h, seed=hash(prompt) % 100000)
    except Exception as e:
        print(f"  [free_gen] Pollinations: {str(e)[:80]}")

    # 2. Hugging Face
    try:
        return _huggingface(prompt, out, width=w, height=h)
    except Exception as e:
        print(f"  [free_gen] HuggingFace: {str(e)[:80]}")

    # 3. Fallback: CogView (already has key)
    from app.providers import image_gen
    return image_gen.generate(prompt, out, size=size)
