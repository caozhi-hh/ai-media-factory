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
        # 读 hook_styles.md 注入钩子分类指引
        hook_path = Path("prompts/hook_styles.md")
        hook_guide = hook_path.read_text(encoding="utf-8") if hook_path.exists() else ""
        # 根据书的主题粗判钩子类型
        book = state.book or ""
        fiction_keywords = ["小说", "活着", "月亮", "小王子", "山", "岛", "人"]
        biz_keywords = ["富爸爸", "穷查理", "投资", "管理", "创业", "商业", "财富", "钱"]
        if any(k in book for k in biz_keywords):
            hook_type = "C. 数字冲击型 (公式: [数字] + [反差] + [震撼结论])"
        elif any(k in book for k in fiction_keywords):
            hook_type = "A. 治愈型 (公式: 这本书 + 治好了/懂了我 + [长期情绪])"
        else:
            hook_type = "B. 反常识型 (公式: [普遍观点] + 其实是错的)"

        system_msg = (
            "你是抖音讲书顶流博主, 文学素养极高, 文字有质感有情绪。"
            f"本次钩子类型: {hook_type}\n\n"
            "硬性要求:\n"
            "1. 字数严格 180-220 字 (读完约 30 秒), 少于 150 字直接重写\n"
            "2. 每句之间用 \\n 换行隔开 (字幕按 \\n 分段)\n"
            "3. 第一句必须是钩子 (按指定类型)\n"
            "4. 只输出纯文案正文, 不要营销口吻/hashtag/感叹号\n"
            "5. 不要书名号《》, 不要用中文引号包裹整段\n"
        )
        state.script = llm.chat(prompt, system=system_msg)

        # 字数校验: 如果 LLM 还是写太短, 重试一次 (加更狠的约束)
        if len(state.script.replace("\n", "").replace(" ", "")) < 120:
            retry_prompt = prompt + "\n\n[重要] 上次生成太短, 这次必须写到 200 字以上, 至少 5-6 句话, 每句用 \\n 分隔!"
            state.script = llm.chat(retry_prompt, system=system_msg + " 字数不够, 务必写到 200 字!")
        return state

    def _output(self, state: VideoState) -> str:
        return f"{len(state.script)} 字"
