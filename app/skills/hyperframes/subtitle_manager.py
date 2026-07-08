"""Subtitle Manager —— 字幕对齐到时间轴(第八部分子流程)。V0.1 占位。"""

from pathlib import Path


def align(subtitle_path: str) -> str:
    Path(subtitle_path).read_text(encoding="utf-8")
    return subtitle_path
