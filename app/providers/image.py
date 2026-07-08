"""Image Provider —— 拉背景图(原则2)。支持 source: picsum(在线)/ local(用户自放图)。"""

import hashlib
import shutil
import urllib.request
from pathlib import Path


def fetch_background(out: str, bg_cfg: dict, w: int = 1080, h: int = 1920) -> str:
    source = bg_cfg.get("source", "picsum")
    if source == "local":
        src = bg_cfg.get("local_path", "assets/background.jpg")
        if Path(src).exists():
            shutil.copyfile(src, out)
            return out
    seed = str(bg_cfg.get("seed", "book"))
    sid = hashlib.md5(seed.encode()).hexdigest()[:10]
    urllib.request.urlretrieve(f"https://picsum.photos/seed/{sid}/{w}/{h}", out)
    return out
