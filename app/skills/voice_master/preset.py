"""Voice Master 风格预设读取(原则6 配置化)。"""

import json
from pathlib import Path


def load(style: str = "book") -> dict:
    path = Path(__file__).parent / "presets" / f"{style}.json"
    return json.loads(path.read_text(encoding="utf-8"))
