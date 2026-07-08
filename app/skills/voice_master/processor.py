"""Voice Master 编排 —— 读预设 + 调 ffmpeg provider 后处理。V0.1:原样复制(后续接 ffmpeg 响度归一/降噪)。"""

from app.skills.voice_master import ffmpeg, preset


def master(voice_path: str, style: str = "book") -> str:
    preset.load(style)
    out = "output/master.mp3"
    ffmpeg.normalize(voice_path, out)
    return out
