"""RenderSkill - 合成最终视频（抖音爆款讲书风格）。

每个分段: Pollinations 图片(已去水印) + 缓慢向前推进(Ken Burns)。
标题: 书名大字 + 作者小字。
字幕: ASS 硬字幕(中英 + 淡入)。
配音 + BGM 混音。
"""

import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

from app.core.skill import Skill
from app.core.state import VideoState
from app.providers import config

FONT_BOLD = "C\\:/Windows/Fonts/msyhbd.ttc"
FONT = "C\\:/Windows/Fonts/msyh.ttc"
BGM = "assets/bgm.aac"


def _escape(t) -> str:
    return str(t).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")


def _audio_duration(path: str, exe: str) -> float:
    r = subprocess.run([exe, "-i", path], capture_output=True, text=True, errors="ignore")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", r.stderr)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4)) / 100
    return 30.0


class RenderSkill(Skill):
    name = "Render"

    def _segment_vf(self, title, author, watermark, frames):
        vf = (
            "scale=864:1152:force_original_aspect_ratio=increase,crop=864:1152,setsar=1,"
            f"zoompan=z='min(zoom+0.0006,1.10)':d={frames}:s=720x960:fps=30,"
            f"drawtext=fontfile='{FONT_BOLD}':text='{_escape(title)}':fontcolor=0xE8DFC8:fontsize=52:borderw=2:bordercolor=0x222222@0.7:x=(w-text_w)/2:y=h*0.06,"
            f"drawtext=fontfile='{FONT}':text='{_escape(author)}':fontcolor=0xC8A858:fontsize=22:borderw=1:bordercolor=0x222222@0.5:x=(w-text_w)/2:y=h*0.06+72"
        )
        if watermark:
            vf += f",drawtext=fontfile='{FONT}':text='{_escape(watermark)}':fontcolor=white:fontsize=18:borderw=1:bordercolor=black:x=16:y=h-38"
        return vf

    def _execute(self, state: VideoState) -> VideoState:
        path = "output/book.mp4"
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        watermark = config.load("video").get("watermark", "@读书博主")
        dur = _audio_duration(state.voice_path, exe)
        scenes = [s for s in (state.storyboard or []) if s.get("image_path") and Path(s["image_path"]).exists()]
        n = max(len(scenes), 1)
        seg = dur / n
        frames = max(int(seg * 30), 1)
        title = f"\u300a{state.book}\u300b"
        author = ((state.research or {}).get("author", "") + "/著").strip("/") or "无名/著"

        segs = []
        for i, sc in enumerate(scenes):
            seg_path = f"output/_seg{i}.mp4"
            vf = self._segment_vf(title, author, watermark, frames)
            try:
                subprocess.run(
                    [exe, "-y", "-loop", "1", "-i", sc["image_path"],
                     "-vf", vf, "-t", f"{seg:.3f}",
                     "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", seg_path],
                    check=True, capture_output=True, text=True, errors="ignore",
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"分段 {i} 失败:\n{(e.stderr or '')[-500:]}") from e
            segs.append(seg_path)

        concat_list = "output/_concat.txt"
        Path(concat_list).write_text("".join(f"file '{Path(s).name}'\n" for s in segs), encoding="utf-8")

        sub_path = state.subtitle_path or "output/subtitle.ass"
        sub = f"subtitles={sub_path}"
        cmd = [exe, "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-i", state.voice_path]
        if Path(BGM).exists():
            import subprocess as _sp, imageio_ffmpeg as _iff
            _exe = _iff.get_ffmpeg_exe()
            _r = _sp.run([_exe,"-i",BGM], capture_output=True, text=True, errors="ignore")
            _m = re.search(r"Duration: (\d+):(\d+):(\d+)", _r.stderr)
            _dur = 0
            if _m:
                _dur = int(_m.group(1))*3600 + int(_m.group(2))*60 + int(_m.group(3))
            # BGM 足够长(比配音长 10 秒以上)才从 30% 高潮处开始,否则从头播放避免不够长
            if _dur > dur + 10:
                _start = max(0, int(_dur * 0.3))
            else:
                _start = 0
            cmd += ["-ss", str(_start), "-i", BGM]
            # 关键:每段滤镜必须用分号分隔,否则 ffmpeg 会把 [a] 误判为 trailing garbage
            fc = (
                f"[0:v]{sub}[v];"
                "[2:a]highpass=f=80,volume=0.08,afade=t=in:st=0:d=1[bg];"
                "[1:a][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]"
            )
            maps = ["-map", "[v]", "-map", "[a]"]
        else:
            fc = f"[0:v]{sub}[v]"
            maps = ["-map", "[v]", "-map", "1:a"]
        cmd += ["-filter_complex", fc] + maps + [
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "128k", "-shortest", path]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, errors="ignore")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"合成失败:\n{(e.stderr or '')[-600:]}") from e

        for s in segs:
            try:
                Path(s).unlink()
            except OSError:
                pass
        state.video_path = path
        return state

    def _output(self, state: VideoState) -> str:
        return state.video_path
