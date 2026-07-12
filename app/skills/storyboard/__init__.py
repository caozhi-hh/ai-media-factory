"""StoryboardSkill —— 拆分镜。

LLM 输出统一 JSON 结构:
{
  "visual_style": "所有分镜共享的视觉风格描述(画风+色调+构图+主角外貌)",
  "scenes": [
    {"scene": 1, "text": "...", "text_en": "...", "image_prompt": "..."}
  ]
}

关键改进:6 张图共享同一 visual_style,场景之间形成连贯的视觉叙事,
避免出现像 6 张拼贴画那样彼此毫无关联的情况。
"""

from app.core.skill import Skill
from app.core.state import VideoState
from app.providers import llm


class StoryboardSkill(Skill):
    name = "Storyboard"

    def _execute(self, state: VideoState) -> VideoState:
        r = state.research or {}
        prompt = (
            "你是抖音讲书号的分镜师。把口播稿拆成 4-6 个分镜。\n"
            "请输出一个 JSON 对象,包含两个字段:\n\n"
            "1. visual_style (字符串):所有分镜共享的统一视觉风格描述。\n"
            "   【画风硬性要求】必须用象征性/隐喻性的插画风格, 禁止纪实风/真人照片风。可选:\n"
            "     - flat illustration (扁平插画, 适合商业/财经/实用类书)\n"
            "     - anime style (动漫风, 适合文学/成长/治愈类书)\n"
            "     - watercolor (水彩, 适合诗歌/散文/温情类书)\n"
            "     - minimalist vector (极简矢量, 适合社科/科普类书)\n"
            "   【禁止】realistic / photorealistic / real photo / documentary / 真人\n"
            "   必须包含:画风 + 色调 + 构图(vertical 9:16) + 统一的象征性意象(不要真人主角)。\n"
            "   例: 'flat illustration, deep navy and gold, vertical 9:16, coins and ladders as symbols, no people'\n"
            "   这个 visual_style 必须能让所有帧看起来像同一组系列插画。\n\n"
            "2. scenes (数组):每个元素是一个分镜对象,字段:\n"
            "   - scene: 序号\n"
            "   - text: 一句金句字幕(≤10 个中文字,精炼有感染力)\n"
            "   - text_en: 该金句的英文翻译(简短自然)\n"
            "   - image_prompt: 该分镜的场景描述(只描述本帧的主体动作、情绪、构图变化,\n"
            "     不需要重复 visual_style 里的画风/色调/主角外貌——这些会被自动注入)。\n"
            "   要求场景之间是同一主角在同一视觉世界里的连续叙事,不是 6 张拼贴画。\n\n"
            f"书名:{state.book}\n作者:{r.get('author', '')}\n口播稿:\n{state.script}"
        )
        result = llm.chat_json(prompt, system="严格只输出 JSON 对象,字段为 visual_style 和 scenes。")
        visual_style = (result.get("visual_style") or "").strip()
        scenes = result.get("scenes") or []
        if not isinstance(scenes, list) or not scenes:
            scenes = [{"scene": 1, "text": (state.script or "")[:10], "text_en": "",
                       "image_prompt": "文艺场景,油画质感", "duration": 6.0}]
        for sc in scenes:
            sc.setdefault("duration", 4.0)
            sc.setdefault("text_en", "")
            sc.setdefault("image_prompt", "文艺场景,油画质感")
        # 把 visual_style 注入到第一个 scene 上作为整组共享标记
        if visual_style and scenes:
            scenes[0]["visual_style"] = visual_style
        state.storyboard = scenes
        return state

    def _output(self, state: VideoState) -> str:
        return f"{len(state.storyboard)} 个分镜(统一视觉风格)"