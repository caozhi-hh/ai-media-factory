"""Skill 抽象基类 —— 所有 Skill 统一接口(原则1/7)。

模板方法 run() 自动打 START/SUCCESS/FAILED/TIME/OUTPUT 日志(第十部分)、
写 state.status[name](断点恢复用)、异常上抛。
子类只实现 _execute(state) -> state,可选重写 _output(state) 给日志填输出。
"""

import time
from abc import ABC, abstractmethod

from . import logger
from .state import VideoState


class Skill(ABC):
    name: str = "Skill"

    @abstractmethod
    def _execute(self, state: VideoState) -> VideoState:
        ...

    def run(self, state: VideoState) -> VideoState:
        logger.start(self.name)
        t0 = time.time()
        try:
            state = self._execute(state)
            state.status[self.name] = "SUCCESS"
            logger.success(self.name, time.time() - t0, self._output(state))
            return state
        except Exception as e:
            state.status[self.name] = "FAILED"
            logger.failed(self.name, time.time() - t0, str(e))
            raise

    def _output(self, state: VideoState) -> str:
        return ""
