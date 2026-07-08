"""Scheduler —— 断点恢复(原则8):跳过已 SUCCESS 的 Skill,每个 Skill 成功后立即存盘。

失败时 state.status[name]=FAILED 已在 Skill.run 写好,scheduler 不吞异常,
main 层捕获后可用 --resume 续跑,已完成的不重跑。
"""

from . import logger
from .skill import Skill
from .state import VideoState


def run(state: VideoState, skills: list[Skill], state_path: str) -> VideoState:
    for skill in skills:
        if state.status.get(skill.name) == "SUCCESS":
            logger.skip(skill.name)
            continue
        state = skill.run(state)
        state.save(state_path)
    return state
