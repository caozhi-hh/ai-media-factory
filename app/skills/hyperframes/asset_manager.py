# -*- coding: utf-8 -*-
"""Asset Manager - image gen: free providers first, CogView last resort.

关键改进:从首个带 visual_style 的 scene 取出统一视觉风格描述,
拼到每张图的 prompt 前缀,保证 6 张图风格连贯。
"""
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


def _resolve_visual_style(storyboard):
    """从第一个带 visual_style 的 scene 中取出统一视觉风格描述。"""
    if not storyboard:
        return ""
    for sc in storyboard:
        vs = (sc.get("visual_style") or "").strip()
        if vs:
            return vs
    return ""


def collect(storyboard, book):
    paths = []
    assets = Path("assets/scenes")
    assets.mkdir(parents=True, exist_ok=True)
    # 共享视觉风格(由 StoryboardSkill 注入到首个 scene)
    visual_style = _resolve_visual_style(storyboard)
    style_prefix = (visual_style + ", ") if visual_style else ""
    for i, sc in enumerate(storyboard or []):
        scene_desc = (sc.get("image_prompt") or book)
        # 关键:把 visual_style 拼在前面,保证 6 张图风格一致
        prompt = style_prefix + scene_desc + ", oil painting, cinematic, detailed, no watermark"
        out = str(assets / ("scene_" + str(i) + ".jpg"))
        # 1. Hailuo (MiniMax) - highest quality, use first
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