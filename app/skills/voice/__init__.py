# -*- coding: utf-8 -*-
"""VoiceSkill - text to speech. Supports edge_tts and volcengine providers.
Falls back to edge_tts if volcengine has transient SSL/network errors.
"""

import asyncio
import time

from app.core.skill import Skill
from app.core.state import VideoState
from app.providers import config


class VoiceSkill(Skill):
    name = "Voice"

    def _execute(self, state: VideoState) -> VideoState:
        cfg = config.load("voice")
        provider = cfg.get("provider", "edge_tts")
        path = "output/voice.mp3"

        if provider == "voice_clone":
            # Cloned voice via WebSocket (bidirectional stream protocol)
            from app.providers import voice_clone_tts
            try:
                voice_clone_tts.generate(state.script, path)
            except Exception as e:
                err = str(e)
                print(f"  [Voice] Voice clone failed: {err[:120]}")
                print(f"  [Voice] Falling back to volcengine preset...")
                from app.providers import volcengine_tts
                volcengine_tts.generate(state.script, path)
        elif provider == "volcengine":
            from app.providers import volcengine_tts
            voice = cfg.get("model", volcengine_tts.DEFAULT_VOICE)
            speed = float(cfg.get("speed_ratio", 1.0))
            volume = float(cfg.get("volume_ratio", 1.0))
            try:
                volcengine_tts.generate(state.script, path, voice_type=voice,
                                        speed_ratio=speed, volume_ratio=volume)
            except Exception as e:
                err = str(e)
                print(f"  [Voice] Volcengine failed: {err[:120]}")
                print(f"  [Voice] Falling back to edge_tts...")
                import edge_tts
                fallback = "zh-CN-YunxiNeural"  # 温润青年男声
                rate = cfg.get("rate", "+0%")
                volume_tts = cfg.get("volume", "+0%")
                asyncio.run(
                    edge_tts.Communicate(state.script, fallback, rate=rate, volume=volume_tts).save(path)
                )
        else:
            import edge_tts
            voice = cfg.get("model", "zh-CN-YunxiNeural")
            rate = cfg.get("rate", "+0%")
            volume = cfg.get("volume", "+0%")
            asyncio.run(
                edge_tts.Communicate(state.script, voice, rate=rate, volume=volume).save(path)
            )
        state.voice_path = path
        return state

    def _output(self, state: VideoState) -> str:
        cfg = config.load("voice")
        return "%s [%s %s]" % (state.voice_path, cfg.get("provider", "edge_tts"), cfg.get("model", "?"))
