"""音频后处理 Provider —— 封装 ffmpeg(原则2 Provider 可替换)。V0.1 假实现:原样复制。"""

import shutil
from pathlib import Path


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def normalize(inp: str, out: str) -> None:
    Path(out).write_bytes(Path(inp).read_bytes())
