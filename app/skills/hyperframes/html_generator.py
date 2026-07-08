"""HTML Generator —— 分镜→HTML 场景(第八部分子流程)。V0.1 占位 HTML。"""

from pathlib import Path


def generate(storyboard: list) -> str:
    path = "output/scenes.html"
    scenes = "".join(f'<div class="scene">{s["text"]}</div>' for s in (storyboard or []))
    Path(path).write_text(f"<html><body>{scenes}</body></html>", encoding="utf-8")
    return path
