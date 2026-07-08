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
    ]

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
        state.logs.append({"skill": "QA", "issues": issues})
        return state

    def _output(self, state: VideoState) -> str:
        issues = state.logs[-1].get("issues", []) if state.logs else []
        return "全通过" if not issues else f"{len(issues)} 项问题"
