"""视频生成引擎 - 将剧本+语音合成视频"""

import subprocess
import json
import shutil
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import DramaConfig

console = Console()
logger = logging.getLogger(__name__)


def _detect_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    raise RuntimeError(
        "需要安装 FFmpeg: https://ffmpeg.org/download.html"
    )


def _get_font(size: int = 32):
    """跨平台字体检测"""
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    logger.warning("No CJK font found, using PIL default (subtitles may look poor)")
    return ImageFont.load_default()


class VideoGenerator:
    """视频生成器"""

    def __init__(self, config: DramaConfig):
        self.config = config
        self.ffmpeg = _detect_ffmpeg()

    def _check_ffmpeg(self):
        """检查 FFmpeg (已由 _detect_ffmpeg 完成)"""
        pass

    def _create_scene_image(
        self, scene: dict, episode_num: int, output_path: Path
    ):
        """为场景创建背景图"""
        width = self.config.video_width
        height = self.config.video_height

        # 创建渐变背景
        img = Image.new("RGB", (width, height), self.config.bg_color)
        draw = ImageDraw.Draw(img)

        # 绘制渐变效果
        for y in range(height):
            ratio = y / height
            r = int(26 * (1 - ratio) + 10 * ratio)
            g = int(26 * (1 - ratio) + 10 * ratio)
            b = int(46 * (1 - ratio) + 30 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 添加文字
        font_large = _get_font(48)
        font_medium = _get_font(32)
        font_small = _get_font(24)

        # 场景信息
        ep_text = f"第 {episode_num} 集"
        scene_text = f"场景 {scene.get('scene_number', '')}: {scene.get('location', '')}"
        time_text = scene.get('time', '')
        desc_text = scene.get('visual_description', '')[:80]

        # 居中绘制
        draw.text(
            (width // 2, height // 2 - 120),
            ep_text, fill=(255, 215, 0), font=font_large, anchor="mm"
        )
        draw.text(
            (width // 2, height // 2 - 50),
            scene_text, fill=(255, 255, 255), font=font_medium, anchor="mm"
        )
        draw.text(
            (width // 2, height // 2),
            time_text, fill=(200, 200, 200), font=font_small, anchor="mm"
        )
        draw.text(
            (width // 2, height // 2 + 80),
            desc_text, fill=(180, 180, 180), font=font_small, anchor="mm"
        )

        img.save(output_path)

    def _create_subtitle_frame(
        self, character: str, line: str, emotion: str = "",
        width: int = 1080, height: int = 300
    ) -> Image.Image:
        """创建字幕帧"""
        img = Image.new("RGBA", (width, height), (0, 0, 0, 180))
        draw = ImageDraw.Draw(img)

        font_char = _get_font(36)
        font_line = _get_font(32)

        # 角色名
        char_text = f"{character}"
        if emotion:
            char_text += f" [{emotion}]"
        draw.text((60, 30), char_text, fill=(255, 215, 0), font=font_char)

        # 台词
        draw.text((60, 90), line, fill=(255, 255, 255), font=font_line)

        return img

    def generate_scene_video(
        self, scene: dict, episode_num: int,
        audio_files: list[Path], output_path: Path
    ):
        """为一个场景生成完整视频"""
        width = self.config.video_width
        height = self.config.video_height

        # 1. 创建场景背景图
        bg_path = output_path.parent / "scene_bg.png"
        self._create_scene_image(scene, episode_num, bg_path)

        if not audio_files:
            cmd = [
                self.ffmpeg, "-y",
                "-loop", "1", "-i", str(bg_path),
                "-t", "3",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-vf", f"scale={width}:{height}",
                str(output_path)
            ]
            subprocess.run(cmd, capture_output=True)
            return

        # 2. 合并音频
        merged_audio = output_path.parent / "merged_audio.mp3"
        self._merge_audio_with_silence(audio_files, merged_audio)

        # 3. 创建字幕
        dialogues = scene.get("dialogues", [])
        subtitle_path = self._create_subtitle_file(
            dialogues, audio_files, output_path.parent
        )

        # 4. 合成视频 — 字幕烧录
        if subtitle_path and subtitle_path.exists():
            # 使用 subtitles filter 烧录 SRT 字幕到画面
            # force_style 确保字幕可读：白色文字 + 黑色描边 + 半透明背景
            subtitle_filter = (
                f"scale={width}:{height},"
                f"subtitles={subtitle_path.as_posix()}:"
                f"force_style='FontSize=28,PrimaryColour=&H00FFFFFF,"
                f"OutlineColour=&H00000000,BackColour=&H80000000,"
                f"BorderStyle=4,Outline=2,Shadow=1'"
            )
            cmd = [
                self.ffmpeg, "-y",
                "-loop", "1", "-i", str(bg_path),
                "-i", str(merged_audio),
                "-vf", subtitle_filter,
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                str(output_path)
            ]
        else:
            # 无字幕：仅缩放
            cmd = [
                self.ffmpeg, "-y",
                "-loop", "1", "-i", str(bg_path),
                "-i", str(merged_audio),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                "-vf", f"scale={width}:{height}",
                str(output_path)
            ]

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            err_msg = result.stderr.decode(errors="ignore")[-500:]
            logger.error(f"FFmpeg failed for {output_path.name}: {err_msg}")
            raise RuntimeError(f"视频合成失败: {err_msg}")

    def _merge_audio_with_silence(self, audio_files: list[Path], output_path: Path):
        """合并音频文件，中间插入静音"""
        if len(audio_files) == 1:
            # 单文件直接复制
            subprocess.run(
                [self.ffmpeg, "-y", "-i", str(audio_files[0]),
                 "-c", "copy", str(output_path)],
                capture_output=True
            )
            return

        # 创建 concat 文件，中间插入静音
        concat_list = []
        silence_path = output_path.parent / "silence.mp3"

        # 生成 0.3 秒静音
        subprocess.run([
            self.ffmpeg, "-y", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono",
            "-t", "0.3", str(silence_path)
        ], capture_output=True)

        concat_file = output_path.parent / "concat.txt"
        lines = []
        for i, f in enumerate(audio_files):
            if f.exists():
                lines.append(f"file '{f.as_posix()}'")
                if i < len(audio_files) - 1:
                    lines.append(f"file '{silence_path.as_posix()}'")

        concat_file.write_text("\n".join(lines), encoding="utf-8")

        subprocess.run([
            self.ffmpeg, "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_file), "-c", "copy", str(output_path)
        ], capture_output=True)

    def _get_audio_duration(self, audio_path: Path) -> float:
        """获取音频时长"""
        import os as _os
        ffprobe_path = str(Path(_os.path.dirname(self.ffmpeg)) / "ffprobe.exe")
        result = subprocess.run([
            ffprobe_path, "-v", "error", "-show_entries",
            "format=duration", "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ], capture_output=True, text=True)
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 10.0

    def _create_subtitle_file(
        self, dialogues: list, audio_files: list[Path],
        output_dir: Path
    ) -> Path:
        """创建 SRT 字幕文件"""
        if not dialogues or not audio_files:
            return None

        srt_path = output_dir / "subtitles.srt"
        lines = []

        current_time = 0.0
        for i, (d, af) in enumerate(zip(dialogues, audio_files)):
            if not af.exists():
                continue
            duration = self._get_audio_duration(af)

            start = self._format_time(current_time)
            end = self._format_time(current_time + duration)

            lines.append(str(i + 1))
            lines.append(f"{start} --> {end}")
            lines.append(f"{d['character']}: {d['line']}")
            lines.append("")

            current_time += duration + 0.3

        srt_path.write_text("\n".join(lines), encoding="utf-8")
        return srt_path

    def _format_time(self, seconds: float) -> str:
        """格式化为 SRT 时间格式"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def generate_full_video(
        self, script: dict, audio_data: dict, output_dir: Path
    ) -> list[Path]:
        """生成完整短剧视频"""
        output_dir.mkdir(parents=True, exist_ok=True)
        video_files = []

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]生成视频中...", total=None)

            for ep_data in audio_data.get("episodes", []):
                ep_num = ep_data["episode_number"]
                ep = script["episodes"][ep_num - 1]

                for scene_data in ep_data.get("scenes", []):
                    scene_num = scene_data["scene_number"]
                    scene = ep["scenes"][scene_num - 1]

                    progress.update(
                        task,
                        description=f"[cyan]合成视频: 第{ep_num}集 场景{scene_num}..."
                    )

                    video_path = output_dir / f"ep{ep_num:02d}_sc{scene_num:02d}.mp4"
                    audio_files = [Path(f) for f in scene_data.get("audio_files", [])]

                    try:
                        self.generate_scene_video(
                            scene, ep_num, audio_files, video_path
                        )
                        video_files.append(video_path)
                    except RuntimeError as e:
                        console.print(
                            f"[red]✗ 视频生成失败 (第{ep_num}集 场景{scene_num}): {e}[/red]"
                        )
                        logger.exception(f"Scene video generation failed for ep{ep_num} sc{scene_num}")

        return video_files

    def merge_episodes(
        self, video_files: list[Path], output_path: Path
    ):
        """合并所有场景为完整剧集"""
        if not video_files:
            return

        concat_file = output_path.parent / "video_concat.txt"
        lines = [f"file '{f.as_posix()}'" for f in video_files if f.exists()]
        concat_file.write_text("\n".join(lines), encoding="utf-8")

        subprocess.run([
            self.ffmpeg, "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_file), "-c", "copy", str(output_path)
        ], capture_output=True)

        concat_file.unlink(missing_ok=True)