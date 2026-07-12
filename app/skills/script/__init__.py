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
            "1. 【钩子定义】第一句钩子 = 你(博主)自己的总结/感悟/反问, 不是书里的原话!\n"
            "   错误: 把书里人物对比/金句当钩子 (那是正文素材)\n"
            "   正确: 你读完书的洞察/反应/总结\n"
            "2. 字数严格 180-220 字 (读完约 30 秒), 少于 150 字直接重写\n"
            "3. 每句之间用 \\n 换行隔开 (字幕按 \\n 分段)\n"
            "4. 钩子简短 (<15 字), 正文可引用书里原话 (带引号), 收尾是你的感悟\n"
            "5. 只输出纯文案正文, 不要营销口吻/hashtag/感叹号\n"
            "6. 不要书名号, 不要用引号包裹整段\n"
        )
        state.script = llm.chat(prompt, system=system_msg)

        # 字数校验: 如果 LLM 还是写太短, 重试最多 3 次 (逐次加压)
        def _char_count(s):
            return len(s.replace("\n", "").replace(" ", "").replace("\u3000", ""))

        for attempt in range(3):
            cc = _char_count(state.script)
            if cc >= 150:
                break
            pressure = (
                prompt
                + "\n\n[第 " + str(attempt + 1) + " 次重试] 上次只写了 "
                + str(cc) + " 字, 严重不足!\n"
                + "这次必须写到 180-220 字, 读完约 30 秒。\n"
                + "结构参考(7-8 句, 每句用 \n 分隔):\n"
                + "  第1句: 钩子(你的总结, <15字)\n"
                + "  第2-6句: 正文, 可引用书里2-3句原话(带引号), 加你的解读\n"
                + "  第7-8句: 收尾感悟 + 留白反问\n"
                + "注意: 每多引用一句书里原话(带引号)就多15-20字, 合理利用!"
            )
            state.script = llm.chat(pressure, system=system_msg)

        # 清理 markdown 污染: ```代码块``` / 前后多余空行 / **加粗**
        import re as _re
        state.script = _re.sub(r"```[a-z]*\n?", "", state.script)
        state.script = state.script.replace("```", "")
        state.script = _re.sub(r"\*\*(.+?)\*\*", r"\1", state.script)
        state.script = state.script.strip("\n ").strip()
        return state

    def _output(self, state: VideoState) -> str:
        return f"{len(state.script)} 字"
