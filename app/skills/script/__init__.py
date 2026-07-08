"""ScriptSkill —— 写文案(只做写稿)。真实:智谱 LLM 读 prompts/script.md,基于 research 写口播稿。"""

from pathlib import Path

from app.core.skill import Skill
from app.core.state import VideoState
from app.providers import llm


class ScriptSkill(Skill):
    name = "Script"

    def _execute(self, state: VideoState) -> VideoState:
        tpl = Path("prompts/script.md").read_text(encoding="utf-8")
        r = state.research or {}
        research_block = (
            f"标题:{r.get('title','')}\n作者:{r.get('author','')}\n摘要:{r.get('summary','')}"
        )
        prompt = tpl.replace("{{research}}", research_block)
        state.script = llm.chat(prompt, system="你是抖音讲书顶流博主,文学素养极高,文字有质感有情绪。只输出纯文案正文,80-110字,金句开头,不要营销口吻/hashtag/感叹号。")
        return state

    def _output(self, state: VideoState) -> str:
        return f"{len(state.script)} 字"
