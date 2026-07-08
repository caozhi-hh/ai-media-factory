# -*- coding: utf-8 -*-
import base64, json, os, time, urllib.request
from pathlib import Path

BASE = "https://openspeech.bytedance.com/api/v1/mega_tts"
RESOURCE_ID = "seed-icl-1.0"

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

def _post(path, body, token):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": "Bearer;" + token,
            "Content-Type": "application/json",
            "Resource-Id": RESOURCE_ID,
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")
        try:
            detail = json.dumps(json.loads(detail), ensure_ascii=False)
        except Exception:
            pass
        raise RuntimeError("Voice clone API HTTP %s: %s" % (e.code, detail))

def train(sample_wav, speaker_id=None, appid=None, token=None):
    appid = appid or _env("VOLC_TTS_APPID")
    token = token or _env("VOLC_TTS_TOKEN")
    if not appid or not token:
        raise RuntimeError("Missing VOLC_TTS_APPID / VOLC_TTS_TOKEN")
    if not speaker_id:
        speaker_id = "S_" + os.urandom(8).hex()[:12]
    audio_b64 = base64.b64encode(Path(sample_wav).read_bytes()).decode("ascii")
    body = {
        "appid": appid,
        "speaker_id": speaker_id,
        "audios": [{
            "audio_bytes": audio_b64,
            "audio_format": "wav",
            "sample_rate": 16000,
            "channel": 1,
        }],
        "source": 2,
        "language": 0,
        "model_type": 1,
    }
    return _post("/audio/upload", body, token), speaker_id

def status(speaker_id, appid=None, token=None):
    appid = appid or _env("VOLC_TTS_APPID")
    token = token or _env("VOLC_TTS_TOKEN")
    body = {"appid": appid, "speaker_id": speaker_id}
    return _post("/status", body, token)

if __name__ == "__main__":
    import sys
    sample = sys.argv[1] if len(sys.argv) > 1 else "work/ref_voice_16k.wav"
    sid = sys.argv[2] if len(sys.argv) > 2 else None
    print("Training voice clone from:", sample)
    resp, sid = train(sample, speaker_id=sid)
    print("Speaker ID:", sid)
    print(json.dumps(resp, ensure_ascii=False, indent=2))
