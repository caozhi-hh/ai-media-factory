"""Agent —— 组装 workflow + state,驱动 scheduler 跑完整链(系统目标)。

Agent 自己不懂业务:workflow 来自 yaml,state 来自调用方,执行交给 scheduler。
"""

from . import scheduler
from .state import VideoState
from .workflow import load_workflow


class Agent:
    def __init__(self, workflow_path: str, state_path: str = "output/state.json"):
        self.skills = load_workflow(workflow_path)
        self.state_path = state_path

    def run(self, state: VideoState) -> VideoState:
        return scheduler.run(state, self.skills, self.state_path)
