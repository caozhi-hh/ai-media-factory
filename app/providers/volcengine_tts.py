# -*- coding: utf-8 -*-
"""Volcengine (Doubao) TTS Provider - large model voices like yuanboxiaoshu 2.0.
Credentials read from project root .env:
  VOLC_TTS_APPID / VOLC_TTS_TOKEN / VOLC_TTS_CLUSTER
API: HTTP non-stream (openspeech.bytedance.com/api/v1/tts)
"""

import base64
import json
import os
import time
import urllib.request
from pathlib import Path

URL = "https://openspeech.bytedance.com/api/v1/tts"

# Default voice: yuanboxiaoshu 2.0 (warm, refined, calm male voice)
DEFAULT_VOICE = "zh_male_yuanboxiaoshu_uranus_bigtts"


def _env(name):
    """Read from system env first, then project root .env."""
    val = os.getenv(name, "").strip()
    if val:
        return val
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(name + "="):
                return line.split("=", 1)[1].strip()
    return ""


def _do_request(body, token, retries=3):
    """Send TTS request with retry on transient SSL/network errors."""
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                URL,
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": "Bearer; " + token,
                    "Content-Type": "application/json",
                    "Resource-Id": "volc.megatts.tts",
                },
            )
            resp = urllib.request.urlopen(req, timeout=60)
            return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last_err = e
            # SSL/connection errors are transient - retry after short delay
            print(f"  [Volcengine] attempt {attempt+1}/{retries} failed: {str(e)[:80]}")
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    raise last_err


def generate(text, out_path, voice_type=DEFAULT_VOICE,
             speed_ratio=1.0, volume_ratio=1.0):
    """Synthesize speech and save to out_path. Returns out_path.

    Requires .env:
      VOLC_TTS_APPID=your AppID
      VOLC_TTS_TOKEN=your Access Token
      VOLC_TTS_CLUSTER=volcano_tts  (large model voices usually volcano_tts)
    """
    appid = _env("VOLC_TTS_APPID")
    token = _env("VOLC_TTS_TOKEN")
    cluster = _env("VOLC_TTS_CLUSTER") or "volcano_tts"
    if not appid or not token:
        raise RuntimeError(
            "Missing Volcengine credentials. Configure in .env:\n"
            "  VOLC_TTS_APPID=your AppID\n"
            "  VOLC_TTS_TOKEN=your Access Token\n"
            "  VOLC_TTS_CLUSTER=volcano_tts\n"
            "Get: https://console.volcengine.com/speech/service/8"
        )

    body = {
        "app": {
            "appid": appid,
            "token": token,
            "cluster": cluster,
        },
        "user": {"uid": "ai-media-factory"},
        "audio": {
            "voice_type": voice_type,
            "encoding": "mp3",
            "speed_ratio": speed_ratio,
            "volume_ratio": volume_ratio,
            "rate": 24000,
        },
        "request": {
            "reqid": os.urandom(16).hex(),
            "text": text,
            "text_type": "plain",
            "operation": "query",
        },
    }

    data = _do_request(body, token, retries=3)
    if data.get("code") != 3000:
        raise RuntimeError("Volcengine TTS failed: code=%s message=%s" % (data.get("code"), data.get("message")))
    audio = base64.b64decode(data["data"])
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(audio)
    return out_path
