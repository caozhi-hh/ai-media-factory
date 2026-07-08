"""Workflow 加载器 —— 读 workflows/*.yaml,按 steps 实例化 Skill 列表(原则4 配置化)。

V0.1 用极简 yaml 解析(只认 name: 和 - 列表),零依赖;后续复杂配置接 pyyaml。
每个 step 对应 app/skills/{step}/ 包,自动找其中 Skill 的具体子类实例化
(不依赖类名拼写,skill 内部类名随意)。改 workflow 只改 yaml,不改 python。
"""

import importlib
import inspect
from pathlib import Path

from .skill import Skill


def _parse_yaml(text: str) -> dict:
    data = {"name": "", "steps": []}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("name:"):
            data["name"] = line[len("name:"):].strip()
        elif line.startswith("- "):
            data["steps"].append(line[2:].strip())
    return data


def _find_skill_class(module) -> type[Skill]:
    for _, cls in inspect.getmembers(module, inspect.isclass):
        if issubclass(cls, Skill) and cls is not Skill and cls.__module__ == module.__name__:
            return cls
    raise ImportError(f"模块 {module.__name__} 里没找到 Skill 子类")


def load_workflow(yaml_path: str) -> list[Skill]:
    data = _parse_yaml(Path(yaml_path).read_text(encoding="utf-8"))
    skills: list[Skill] = []
    for step in data["steps"]:
        module = importlib.import_module(f"app.skills.{step}")
        skills.append(_find_skill_class(module)())
    return skills
