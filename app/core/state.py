"""VideoState —— 全流程唯一数据对象(原则7),支持序列化断点恢复(原则8)。

字段严格按 ARCHITECTURE.md 第四节。所有 Skill 只传它、只改它、不自己存状态。
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class VideoState:
    book: str = ""
    topic: str = ""
    research: dict | None = None
    script: str | None = None
    voice_path: str | None = None
    subtitle_path: str | None = None
    storyboard: list | None = None
    html_path: str | None = None
    video_path: str | None = None
    publish_url: str | None = None
    logs: list = field(default_factory=list)
    status: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, path: str) -> "VideoState":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**data)
