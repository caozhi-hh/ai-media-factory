"""HyperFramesSkill —— 视频生成子流程(第八部分)。
Storyboard→HTML→Asset→Subtitle→Timeline→Render 中的中间四步在此编排:
asset_manager 真实(CogView 生成分镜图),其余生成 timeline.json 给 Render。"""

from app.core.skill import Skill
from app.core.state import VideoState
from app.skills.hyperframes import (
    asset_manager,
    html_generator,
    subtitle_manager,
    timeline_builder,
)


class HyperFramesSkill(Skill):
    name = "HyperFrames"

    def _execute(self, state: VideoState) -> VideoState:
        html = html_generator.generate(state.storyboard)
        asset_manager.collect(state.storyboard, state.book)
        subs = subtitle_manager.align(state.subtitle_path)
        timeline_builder.build(html, state.storyboard, subs)
        state.html_path = html
        return state

    def _output(self, state: VideoState) -> str:
        n = len([s for s in (state.storyboard or []) if s.get("image_path")])
        return f"{n} 张背景图"
