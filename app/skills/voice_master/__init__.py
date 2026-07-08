"""VoiceMasterSkill —— 音频后处理(第七部分独立)。Voice 永远先于 VoiceMaster。
V0.1 假实现:复制 voice.wav → master.wav。后续 ffmpeg 降噪/响度归一/拼接。"""

from app.core.skill import Skill
from app.core.state import VideoState
from app.skills.voice_master import processor


class VoiceMasterSkill(Skill):
    name = "VoiceMaster"

    def _execute(self, state: VideoState) -> VideoState:
        state.voice_path = processor.master(state.voice_path)
        return state

    def _output(self, state: VideoState) -> str:
        return state.voice_path
