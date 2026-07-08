"""PublishSkill —— 发布(只做发布)。V0.1 假 publish_url,后续各平台 plugin(plugins/*,第十一部分)。"""

from app.core.skill import Skill
from app.core.state import VideoState


class PublishSkill(Skill):
    name = "Publish"

    def _execute(self, state: VideoState) -> VideoState:
        state.publish_url = f"file://{state.video_path}"
        return state

    def _output(self, state: VideoState) -> str:
        return state.publish_url
