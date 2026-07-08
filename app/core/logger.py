"""日志格式器 —— 第十部分:统一 START/SUCCESS/FAILED/TIME/OUTPUT,定位 Bug 容易。"""

SEP = "-" * 40


def start(name: str) -> None:
    print(f"\n[{name}] START")
    print(SEP)


def success(name: str, elapsed: float, output: str = "") -> None:
    print(f"[{name}] SUCCESS")
    print(f"  耗时: {elapsed:.1f}s")
    if output:
        print(f"  输出: {output}")
    print(SEP)


def failed(name: str, elapsed: float, error: str) -> None:
    print(f"[{name}] FAILED")
    print(f"  耗时: {elapsed:.1f}s")
    print(f"  错误: {error}")
    print(SEP)


def skip(name: str) -> None:
    print(f"[{name}] 跳过(已完成)")
