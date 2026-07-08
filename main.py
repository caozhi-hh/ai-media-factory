"""AI Media Factory —— 输入主题,跑 Book Workflow,输出 output/book.mp4。

用法:
  python main.py "活着"           # 全新跑
  python main.py "活着" --resume  # 从 output/state.json 断点续跑
"""

import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8")

from app.core.agent import Agent
from app.core.state import VideoState

WORKFLOW = "workflows/book.yaml"
STATE_PATH = "output/state.json"


def main():
    parser = argparse.ArgumentParser(description="AI Media Factory")
    parser.add_argument("book", help="书名,如 活着")
    parser.add_argument("--resume", action="store_true", help="从 state.json 断点续跑")
    args = parser.parse_args()

    agent = Agent(WORKFLOW, STATE_PATH)

    if args.resume:
        state = VideoState.load(STATE_PATH)
        print(f"▶ 续跑:{state.book}")
    else:
        state = VideoState(book=args.book)
        print(f"▶ 新任务:{args.book}")

    state = agent.run(state)
    print(f"\n✅ 完成: {state.video_path}")


if __name__ == "__main__":
    main()
