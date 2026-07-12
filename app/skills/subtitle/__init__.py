# -*- coding: utf-8 -*-
"""SubtitleSkill - ASS subtitle with Chinese + English translation (LLM)."""
import re
import subprocess
from pathlib import Path
import imageio_ffmpeg
from app.core.skill import Skill
from app.core.state import VideoState
from app.providers import llm


def _ts(s):
    return "%d:%02d:%05.2f" % (int(s // 3600), int((s % 3600) // 60), s % 60)


def _dur(path):
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    r = subprocess.run([exe, "-i", path], capture_output=True, text=True, errors="ignore")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", r.stderr)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4)) / 100
    return 30.0


def _split_sentences(script):
    """切分口播稿. 优先级: \n 段落 > 句末标点 > 逗号.
    引号包裹的段落 (中文""/英文"")整段保留, 不按逗号切."""
    if not script:
        return []
    # 防御: 清理可能残留的 markdown 标记 (代码块/加粗/列表符)
    import re as _mdre
    script = _mdre.sub(r"```[a-z]*\n?", "", script).replace("```", "")
    script = _mdre.sub(r"\\*\\*(.+?)\\*\\*", r"\1", script)
    script = _mdre.sub(r"^\\s*[-*]\\s+", "", script, flags=_mdre.MULTILINE)
    DQ = chr(34)  # ASCII 双引号
    Q_OPEN = chr(0x201c) + chr(0x201d) + DQ + chr(0x300a) + chr(0x3010)
    Q_CLOSE = chr(0x201d) + chr(0x201d) + DQ + chr(0x300b) + chr(0x3011)
    paras = []
    for seg in script.splitlines():
        seg = seg.strip()
        # 先检测引号包裹 (在 strip 之前)
        has_cn = chr(0x201c) in seg and chr(0x201d) in seg
        has_en = DQ in seg and seg.count(DQ) >= 2
        is_q = has_cn or has_en
        # 再 strip 首尾引号/书名号
        while seg and seg[0] in Q_OPEN:
            seg = seg[1:].strip()
        while seg and seg[-1] in Q_CLOSE:
            seg = seg[:-1].strip()
        if seg:
            paras.append((seg, is_q))
    if not paras:
        return [script[:20]]
    result = []
    for para, is_q in paras:
        sentences = re.split(r"(?<=[\u3002\uff1f\uff01!?])", para)
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            # 过滤纯标点/引号段
            if re.fullmatch(r"[\s\u3000-\u303f\u2018-\u201f\u300a-\u3011\u2014\u2026\"\u201c\u201d]+", s):
                continue
            # 切分条件: 非引文 + 单句 > 22 字 + 含逗号
            if not is_q and len(s) > 22 and re.search(r"[\uff0c,\uff1b;]", s):
                subs = re.split(r"([\uff0c,\uff1b;])", s)
                chunks = []
                cur = ""
                for sub in subs:
                    if sub in "\uff0c,\uff1b;":
                        cur += sub
                        if cur.strip():
                            chunks.append(cur)
                        cur = ""
                    else:
                        cur += sub
                if cur.strip():
                    chunks.append(cur)
                # 合并过短 chunks
                merged = []
                for c in chunks:
                    if merged and len(merged[-1]) < 10:
                        merged[-1] += c
                    else:
                        merged.append(c)
                result.extend(merged)
            else:
                result.append(s)
    return result

def _translate_batch(sentences):
    """Batch translate CN sentences to EN via LLM."""
    if not sentences:
        return []
    joined = "\n".join("%d. %s" % (i + 1, s) for i, s in enumerate(sentences))
    prompt = ("Translate each Chinese sentence to natural English. "
              "Keep them concise and emotional (for a book trailer). "
              "Output ONLY the English, one line each, same order, numbered:\n" + joined)
    try:
        text = llm.chat(prompt, system="You are a literary translator. Output ONLY the English translations, one per line, NO numbering, NO bullets, NO quotes.")
        results = []
        for line in text.strip().splitlines():
            # 兼容 LLM 可能加的 "1. " / "1) " 编号, 也兼容纯文本
            m = re.match(r"\s*(?:\d+[\.\)]\s*)?(.+)", line.strip())
            if m:
                results.append(m.group(1).strip())
        if len(results) == len(sentences):
            return results
        # fallback: take any non-empty lines
        results = [l for l in text.strip().splitlines() if l.strip()]
        if len(results) >= len(sentences):
            return results[:len(sentences)]
        # pad if short
        while len(results) < len(sentences):
            results.append(results[-1] if results else "")
        return results[:len(sentences)]
    except Exception:
        return [""] * len(sentences)


def _make_ass(script, total, en_translations=None):
    """生成 ASS 字幕. 样式分工: 第一句=HOOK(亮金), 末句=END(暖米), 中间=CN(白).
    详见 prompts/hook_styles.md. HOOK_EN 必须 18pt 防英文超屏."""
    sentences = _split_sentences(script)
    if not sentences:
        sentences = [script[:20]]
    total_chars = sum(len(s) for s in sentences)
    bs = chr(92)
    nl = chr(10)
    n = len(sentences)
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 720",
        "PlayResY: 960",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        # CN/EN: 中段正文(白色)
        "Style: CN,Microsoft YaHei UI,34,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,2.5,0,2,50,50,235,1",
        "Style: EN,Arial,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,-1,0,0,100,100,0,0,1,1.5,0,2,50,50,265,1",
        # HOOK: 钩子句(亮金 0xFFD080, 抓人冲击)
        "Style: HOOK,Microsoft YaHei UI,34,&H00FFD080,&H00FFD080,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,2.5,0,2,50,50,235,1",
        # HOOK_EN: 钩子英文(亮金, 缩小到 18pt 防超屏, 不是 20pt)
        "Style: HOOK_EN,Arial,18,&H00FFD080,&H00FFD080,&H00000000,&H80000000,0,-1,0,0,100,100,0,0,1,1.5,0,2,50,50,265,1",
        # END: 收尾句(暖米 0xC8E6F5, 比 HOOK 柔, 与金色呼应但不混淆)
        "Style: END,Microsoft YaHei UI,34,&H00C8E6F5,&H00C8E6F5,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,2.5,0,2,50,50,235,1",
        "Style: END_EN,Arial,18,&H00C8E6F5,&H00C8E6F5,&H00000000,&H80000000,0,-1,0,0,100,100,0,0,1,1.5,0,2,50,50,265,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    en_list = en_translations or []
    cur = 0.0
    for idx, s in enumerate(sentences):
        dur = total * len(s) / total_chars
        st = cur
        en_t = cur + dur
        cur = en_t
        # 样式判定: 第一句=HOOK, 末句=END, 中间=CN
        if n == 1:
            cn_style, en_style = "HOOK", "HOOK_EN"
        elif idx == 0:
            cn_style, en_style = "HOOK", "HOOK_EN"
        elif idx == n - 1:
            cn_style, en_style = "END", "END_EN"
        else:
            cn_style, en_style = "CN", "EN"
        tag_cn = "{" + bs + "fad(280,180)}"
        # 字数上限保护: CN 单句 > 16 字自动折行 (ASS 用 \N 软换行, 防超屏)
        if len(s) > 16:
            # 按逗号位置折行: parts=["前半","，","后半"], 逗号=parts[1]
            import re as _re
            parts = _re.split(r"([，,；;])", s)
            if len(parts) >= 3:
                line1 = parts[0] + parts[1]
                line2 = "".join(parts[2:])
                if len(line2) > 16:
                    p2 = _re.split(r"([，,；;])", line2)
                    if len(p2) >= 3:
                        line2 = p2[0] + p2[1] + chr(92) + "N" + "".join(p2[2:])
                s = line1 + chr(92) + "N" + line2 if line2.strip() else s
            else:
                mid = len(s) // 2
                s = s[:mid] + chr(92) + "N" + s[mid:]
        lines.append("Dialogue: 0,%s,%s,%s,,0,0,0,,%s%s" % (_ts(st), _ts(en_t), cn_style, tag_cn, s))
        en_text = en_list[idx] if idx < len(en_list) else ""
        if en_text:
            tag_en = "{" + bs + "fad(300,200)" + bs + "i1}"
            lines.append("Dialogue: 0,%s,%s,%s,,0,0,0,,%s%s" % (_ts(st), _ts(en_t), en_style, tag_en, en_text))
    return nl.join(lines)


class SubtitleSkill(Skill):
    name = "Subtitle"

    def _execute(self, state):
        path = "output/subtitle.ass"
        total = _dur(state.voice_path) if state.voice_path else 30.0
        sentences = _split_sentences(state.script or "")
        en = _translate_batch(sentences)
        ass = _make_ass(state.script or "", total, en)
        Path(path).write_text(ass, encoding="utf-8")
        state.subtitle_path = path
        return state

    def _output(self, state):
        return state.subtitle_path
