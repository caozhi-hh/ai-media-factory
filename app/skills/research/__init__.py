"""ResearchSkill —— 搜集资料(只做搜集)。真实:智谱 LLM 读 prompts/research.md 生成。"""

from pathlib import Path

from app.core.skill import Skill
from app.core.state import VideoState
from app.providers import llm


class ResearchSkill(Skill):
    name = "Research"

    def _execute(self, state: VideoState) -> VideoState:
        prompt = Path("prompts/research.md").read_text(encoding="utf-8").replace("{{book}}", state.book)
        data = llm.chat_json(prompt, system="你是图书研究助手,严格只输出 JSON。")
        state.research = {
            "title": data.get("title", state.book),
            "author": data.get("author", "未知"),
            "summary": data.get("summary", ""),
        }
        return state

    def _output(self, state: VideoState) -> str:
        return f"{state.research['title']} / {state.research['author']}"
