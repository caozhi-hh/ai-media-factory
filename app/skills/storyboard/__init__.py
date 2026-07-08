"""StoryboardSkill —— 拆分镜。LLM 生成金句(中文)+ 英文翻译 + 油画场景描述。"""

from app.core.skill import Skill
from app.core.state import VideoState
from app.providers import llm


class StoryboardSkill(Skill):
    name = "Storyboard"

    def _execute(self, state: VideoState) -> VideoState:
        r = state.research or {}
        prompt = (
            "你是抖音讲书号的分镜师。把口播稿拆成 4-6 个分镜,每个分镜输出 JSON 对象:\n"
            '- scene: 序号\n'
            '- text: 一句金句字幕(≤10 个中文字,精炼有感染力)\n'
            '- text_en: 该金句的英文翻译(简短自然)\n'
            '- image_prompt: 油画/插画风场景描述(贴合金句氛围,结尾加"油画质感")\n'
            f"\n书名:{state.book}\n作者:{r.get('author', '')}\n口播稿:\n{state.script}"
        )
        scenes = llm.chat_list(prompt, system="严格只输出 JSON 数组。")
        if not scenes:
            scenes = [{"scene": 1, "text": (state.script or "")[:10], "text_en": "",
                       "image_prompt": "文艺场景,油画质感", "duration": 6.0}]
        for sc in scenes:
            sc.setdefault("duration", 4.0)
            sc.setdefault("text_en", "")
            sc.setdefault("image_prompt", "文艺场景,油画质感")
        state.storyboard = scenes
        return state

    def _output(self, state: VideoState) -> str:
        return f"{len(state.storyboard)} 个分镜"
