# -*- coding: utf-8 -*-
"""Asset Manager - image gen: free providers first, CogView last resort."""
from pathlib import Path

def _remove_watermark(path):
    from PIL import Image, ImageFilter
    img = Image.open(path).convert("RGB")
    w, h = img.size
    wm_w, wm_h = 280, 200
    offset = 240
    src_box = (w - wm_w, h - wm_h - offset, w, h - offset)
    src = img.crop(src_box)
    img.paste(src, (w - wm_w, h - wm_h, w, h))
    blend = img.filter(ImageFilter.GaussianBlur(radius=1))
    edge = 10
    for (x1, y1, x2, y2) in [(w-wm_w-edge,h-wm_h,w-wm_w+edge,h),(w-wm_w,h-wm_h-edge,w,h-wm_h+edge)]:
        img.paste(blend.crop((x1,y1,x2,y2)),(x1,y1,x2,y2))
    img.save(path, quality=95)

def collect(storyboard, book):
    paths = []
    assets = Path("assets/scenes")
    assets.mkdir(parents=True, exist_ok=True)
    for i, sc in enumerate(storyboard or []):
        prompt = (sc.get("image_prompt") or book) + ", oil painting, cinematic, detailed, no watermark"
        out = str(assets / ("scene_" + str(i) + ".jpg"))
        # 1. MiniMax (Hailuo) - highest quality, use first
        try:
            from app.providers import minimax_gen
            minimax_gen.generate(prompt, out, size="720x960")
            sc["image_path"] = out
            paths.append(out)
            print("  [AssetManager] scene", i, "via MiniMax")
            continue
        except Exception as e:
            print("  [AssetManager] MiniMax failed:", str(e)[:100])
        # 2. Free providers (Pollinations / HF / etc)
        try:
            from app.providers import free_gen
            free_gen.generate(prompt, out, size="720x960")
            sc["image_path"] = out
            paths.append(out)
            print("  [AssetManager] scene", i, "via free_gen")
            continue
        except Exception as e:
            print("  [AssetManager] free_gen failed:", str(e)[:100])
        # Last resort: CogView
        try:
            from app.providers import image_gen
            image_gen.generate(prompt, out, size="720x960")
            _remove_watermark(out)
            sc["image_path"] = out
            paths.append(out)
            print("  [AssetManager] scene", i, "via CogView (last resort)")
        except Exception as e2:
            sc["image_path"] = None
            print("  [AssetManager] scene", i, "ALL FAILED:", str(e2)[:100])
    return paths
