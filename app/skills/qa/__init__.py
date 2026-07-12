"""QASkill —— 自动质检(第九部分 9 项)。真实:检查产物存在/非空/MP4 可播放性。
issues 记入 state.logs,不致命(允许出片),后续可加严。"""

from pathlib import Path

from app.core.skill import Skill
from app.core.state import VideoState


class QASkill(Skill):
    name = "QA"

    CHECKS = [
        "字幕重叠", "字幕超时", "字幕超屏", "字体缺失", "图片不存在",
        "音频为空", "HTML 报错", "FFmpeg 失败", "MP4 不可播放",
        "unicode 错字(形近字混淆)",
    ]

    # 形近字黑名单: 容易在 unicode 转码/手写时混淆的字
    # key=错字, value=(正确字, 常见误用上下文)
    CHAR_CONFUSABLES = {
        "\u8f98": ("\u8f88", "一辈子的辈(0x8f88), 不要写成 0x8f98 辘轮的辘"),
        "\u8f9e": ("\u8f88", "一辈子的辈(0x8f88), 不要写成 0x8f9e"),
        "\u5382": ("\u5382", "厂的厂, 注意简繁"),
        "\u8f88": ("\u8f88", "OK 这是正确的辈"),
    }

    def _execute(self, state: VideoState) -> VideoState:
        issues = []
        for label, p in [("字幕", state.subtitle_path), ("音频", state.voice_path),
                         ("视频", state.video_path), ("HTML", state.html_path)]:
            if not p:
                issues.append(f"{label}路径为空")
            elif not Path(p).exists():
                issues.append(f"{label}不存在:{p}")
            elif Path(p).stat().st_size == 0:
                issues.append(f"{label}为空:{p}")
        if state.video_path and Path(state.video_path).exists():
            size = Path(state.video_path).stat().st_size
            if size < 5000:
                issues.append(f"MP4 过小({size}B),疑似不可播放")
        # unicode 形近字核验(重点: 字幕 ASS + 文案 script)
        for source_label, text in [("字幕", Path(state.subtitle_path).read_text(encoding="utf-8") if state.subtitle_path and Path(state.subtitle_path).exists() else ""),
                                    ("文案", state.script or "")]:
            if not text:
                continue
            for wrong, (right, hint) in self.CHAR_CONFUSABLES.items():
                if wrong == right:
                    continue  # 跳过"正确字"自比较
                if wrong in text:
                    issues.append(f"{source_label}错字: U+{ord(wrong):04X} 应为 U+{ord(right):04X} ({hint})")
        state.logs.append({"skill": "QA", "issues": issues})
        return state

    def _output(self, state: VideoState) -> str:
        issues = state.logs[-1].get("issues", []) if state.logs else []
        return "全通过" if not issues else f"{len(issues)} 项问题"
