# -*- coding: utf-8 -*-
"""Volcengine Doubao Voice Clone TTS - synthesize speech with a cloned voice.

Cloned voices (S_xxxxx from the voice-clone console) require the bidirectional
stream WebSocket protocol (NOT the HTTP /api/v1/tts endpoint).

Tested config:
  AppID:        3224107954
  Resource-Id:  volc.megatts.default   (voice-clone 1.0 trained speaker)
  Speaker:      S_PnSPW7a82            (cloned from reference male voice)
  Endpoint:     wss://openspeech.bytedance.com/api/v3/tts/bidirection
  Auth headers: X-Api-App-Key / X-Api-Access-Key / X-Api-Resource-Id

Credentials are read from .env:
  VOLC_CLONE_APPID / VOLC_CLONE_TOKEN  (clone synthesis app)
  VOLC_CLONE_SPEAKER  (the cloned speaker id, e.g. S_PnSPW7a82)
Falls back to VOLC_TTS_APPID / VOLC_TTS_TOKEN if the clone ones are absent.
"""

import asyncio
import base64
import json
import os
import uuid
from pathlib import Path

try:
    import websockets
except ImportError:
    websockets = None

WS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
RESOURCE_ID = "volc.megatts.default"

# ---- Binary protocol constants ----
PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001
FULL_CLIENT_REQUEST = 0b0001
AUDIO_ONLY_RESPONSE = 0b1011
ERROR_INFORMATION = 0b1111
MsgTypeFlagWithEvent = 0b100
JSON = 0b0001
EVENT_StartSession = 100
EVENT_FinishSession = 102
EVENT_TaskRequest = 200
EVENT_SessionStarted = 150
EVENT_SessionFinished = 152


def _env(name):
    val = os.getenv(name, "").strip()
    if val:
        return val
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(name + "="):
                return line.split("=", 1)[1].strip()
    return ""


def _creds():
    appid = _env("VOLC_CLONE_APPID") or _env("VOLC_TTS_APPID")
    token = _env("VOLC_CLONE_TOKEN") or _env("VOLC_TTS_TOKEN")
    return appid, token


def _header_bytes(message_type, flags, serial=JSON):
    return bytes([
        (PROTOCOL_VERSION << 4) | DEFAULT_HEADER_SIZE,
        (message_type << 4) | flags,
        (serial << 4) | 0,
        0,
    ])


def _event_bytes(event, session_id):
    out = bytearray()
    out.extend(event.to_bytes(4, "big", signed=True))
    sid = session_id.encode()
    out.extend(len(sid).to_bytes(4, "big", signed=True))
    out.extend(sid)
    return bytes(out)


def _payload(event, text, speaker):
    params = {
        "user": {"uid": "ai-media-factory"},
        "event": event,
        "namespace": "BidirectionalTTS",
        "req_params": {
            "text": text,
            "speaker": speaker,
            "audio_params": {"format": "mp3", "speech_rate": 0, "loudness_rate": 0},
            "additions": json.dumps({"aigc_metadata": {}, "cache_config": {}, "post_process": {"pitch": 0}}),
        },
    }
    return json.dumps(params).encode("utf-8")


def _frame(header, optional=None, payload=None):
    out = bytearray(header)
    if optional:
        out.extend(optional)
    if payload:
        out.extend(len(payload).to_bytes(4, "big", signed=True))
        out.extend(payload)
    return bytes(out)


async def _synth(appid, token, speaker, text, speed_ratio=1.0):
    """Run a WebSocket TTS session and return raw mp3 bytes."""
    if websockets is None:
        raise RuntimeError("websockets library not installed: pip install websockets")
    session_id = uuid.uuid4().hex
    headers = {
        "X-Api-App-Key": appid,
        "X-Api-Access-Key": token,
        "X-Api-Resource-Id": RESOURCE_ID,
        "X-Api-Connect-Id": uuid.uuid4().hex,
    }
    audio = bytearray()
    async with websockets.connect(WS_URL, additional_headers=headers, max_size=1000000000, open_timeout=15) as ws:
        # StartSession
        await ws.send(_frame(
            _header_bytes(FULL_CLIENT_REQUEST, MsgTypeFlagWithEvent),
            _event_bytes(EVENT_StartSession, session_id),
            _payload(EVENT_StartSession, "", speaker),
        ))
        # Wait for SessionStarted
        while True:
            r = await asyncio.wait_for(ws.recv(), timeout=15)
            if isinstance(r, str):
                raise RuntimeError("Server text: " + r[:200])
            mt = (r[1] >> 4) & 0x0F
            flags = r[1] & 0x0F
            ev = int.from_bytes(r[4:8], "big", signed=True) if (flags == MsgTypeFlagWithEvent and len(r) >= 8) else None
            if mt == ERROR_INFORMATION:
                offset = 8 if flags == MsgTypeFlagWithEvent else 4
                plen = int.from_bytes(r[offset:offset+4], "big", signed=True) if len(r) >= offset+4 else 0
                raise RuntimeError("StartSession error: " + r[offset+4:offset+4+plen].decode("utf-8", "ignore")[:200])
            if ev == EVENT_SessionStarted:
                break
        # TaskRequest + FinishSession
        await ws.send(_frame(
            _header_bytes(FULL_CLIENT_REQUEST, MsgTypeFlagWithEvent),
            _event_bytes(EVENT_TaskRequest, session_id),
            _payload(EVENT_TaskRequest, text, speaker),
        ))
        await ws.send(_frame(
            _header_bytes(FULL_CLIENT_REQUEST, MsgTypeFlagWithEvent),
            _event_bytes(EVENT_FinishSession, session_id),
            b"{}",
        ))
        # Receive audio until SessionFinished
        while True:
            r = await asyncio.wait_for(ws.recv(), timeout=30)
            if isinstance(r, str):
                continue
            mt = (r[1] >> 4) & 0x0F
            flags = r[1] & 0x0F
            ev = int.from_bytes(r[4:8], "big", signed=True) if (flags == MsgTypeFlagWithEvent and len(r) >= 8) else None
            if mt == ERROR_INFORMATION:
                offset = 8 if flags == MsgTypeFlagWithEvent else 4
                plen = int.from_bytes(r[offset:offset+4], "big", signed=True) if len(r) >= offset+4 else 0
                raise RuntimeError("TTS error: " + r[offset+4:offset+4+plen].decode("utf-8", "ignore")[:200])
            if mt == AUDIO_ONLY_RESPONSE:
                # Audio data follows header(4) + optional(8 if event flag)
                offset = 8 if flags == MsgTypeFlagWithEvent else 4
                audio.extend(r[offset:])
            if ev == EVENT_SessionFinished:
                break
    return bytes(audio)


def generate(text, out_path, voice_type=None, speed_ratio=1.0, volume_ratio=1.0):
    """Synthesize speech with a cloned voice via WebSocket. Returns out_path.

    Args:
        text: the text to speak
        out_path: where to save the mp3
        voice_type: the cloned speaker id (S_xxxxx). If None, reads VOLC_CLONE_SPEAKER from .env
    """
    appid, token = _creds()
    if not appid or not token:
        raise RuntimeError("Missing voice clone credentials. Configure in .env:\n"
                           "  VOLC_CLONE_APPID=your AppID\n"
                           "  VOLC_CLONE_TOKEN=your Token\n"
                           "  VOLC_CLONE_SPEAKER=S_xxxxx")
    speaker = voice_type or _env("VOLC_CLONE_SPEAKER")
    if not speaker:
        raise RuntimeError("Missing VOLC_CLONE_SPEAKER (cloned speaker id like S_xxxxx) in .env")
    audio = asyncio.run(_synth(appid, token, speaker, text, speed_ratio))
    if not audio or len(audio) < 100:
        raise RuntimeError("Voice clone TTS returned empty/short audio (%d bytes)" % len(audio))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(audio)
    return out_path


if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else "百年孤独，是马尔克斯写给时间的一首诗。"
    out = sys.argv[2] if len(sys.argv) > 2 else "work/clone_demo.mp3"
    print("Synthesizing:", text, flush=True)
    generate(text, out)
    print("Saved:", out, Path(out).stat().st_size, "bytes", flush=True)
