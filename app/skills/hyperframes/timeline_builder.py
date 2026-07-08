"""Timeline Builder —— storyboard+场景图+字幕→timeline.json(第八部分子流程)。"""

import json
from pathlib import Path


def build(html_path: str, storyboard: list, subs: str) -> str:
    path = "output/timeline.json"
    Path(path).write_text(
        json.dumps({
            "html": html_path,
            "scenes": [
                {"scene": s.get("scene"), "image": s.get("image_path"),
                 "text": s.get("text"), "duration": s.get("duration", 4.0)}
                for s in (storyboard or [])
            ],
            "subs": str(subs),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
