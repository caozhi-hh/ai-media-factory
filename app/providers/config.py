"""Config Provider —— 读 config/*.yaml(原则6 配置化,禁止硬编码)。"""

from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[2]


def load(name: str) -> dict:
    return yaml.safe_load((_ROOT / "config" / f"{name}.yaml").read_text(encoding="utf-8"))
