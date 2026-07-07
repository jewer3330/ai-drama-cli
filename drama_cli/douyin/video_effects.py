"""专业视频特效引擎 - 转场、动画、Ken Burns、调色、字幕动画"""

import subprocess
import shutil
import math
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import random

logger = logging.getLogger(__name__)


def _detect_ffmpeg() -> str:
    """自动检测 ffmpeg 路径"""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        logger.info(f"FFmpeg detected at: {ffmpeg}")
        return ffmpeg
    raise RuntimeError(
        "未找到 ffmpeg。请安装 FFmpeg 并确保它在系统 PATH 中。\n"
        "下载地址: https://ffmpeg.org/download.html"
    )


def _detect_font(font_names: list[str], font_size: int = 32) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """自动检测可用字体，找不到返回默认字体"""
    from PIL import ImageFont
    for name in font_names:
        try:
            return ImageFont.truetype(name, font_size)
        except (OSError, IOError):
            continue
    logger.warning(f"未找到系统字体，使用 PIL 默认字体（字幕效果可能不佳）")
    return ImageFont.load_default()


class VideoEffects:
    """抖音级视频特效引擎"""

    FFMPEG = _detect_ffmpeg()
    FFPROBE = str(Path(FFMPEG).parent / "ffprobe.exe")

    # 字体自动检测 (Windows/跨平台)
    _FONT_CANDIDATES = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]

    @staticmethod
    def _get_font(size: int = 32) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return _detect_font(VideoEffects._FONT_CANDIDATES, size)

    @staticmethod
    def _get_bold_font(size: int = 32) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        bold_candidates = [
            "C:/Windows/Fonts/msyhbd.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/System/Library/Fonts/PingFang.ttc",
        ] + VideoEffects._FONT_CANDIDATES
        return _detect_font(bold_candidates, size)

    @staticmethod
    def _run(cmd, check=True):
        """运行命令并检查结果"""
        r = subprocess.run(cmd, capture_output=True)
        if check and r.returncode != 0:
            err = r.stderr.decode(errors="ignore")[-300:]
            logger.error(f"FFmpeg failed: {err}")
            raise RuntimeError(f"FFmpeg failed: {err}")
        return r

    @staticmethod
    def _get_duration(media_path: Path) -> float:
        """获取媒体时长"""
        if not media_path.exists():
            logger.warning(f"Media file not found: {media_path}")
            return 10.0
        r = subprocess.run([
            VideoEffects.FFPROBE, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(media_path)
        ], capture_output=True, text=True)
        try:
            return float(r.stdout.strip())
        except (ValueError, AttributeError):
            logger.warning(f"Could not determine duration for {media_path}, using default 10.0s")
            return 10.0

    @staticmethod
    def ken_burns_effect(
        bg_path: Path, audio_path: Path, output_path: Path,
        width: int = 1080, height: int = 1920,
        zoom_ratio: float = 1.15, duration: float = None
    ):
        """Ken Burns 效果 - 缓慢缩放+平移"""
        if duration is None:
            duration = VideoEffects._get_duration(audio_path)

        # 计算缩放参数
        # 从 1.0 缩放到 zoom_ratio，同时轻微平移
        start_scale = 1.0
        end_scale = zoom_ratio
        pan_x = random.randint(-30, 30)
        pan_y = random.randint(-20, 20)

        # 构建 zoompan 滤镜
        filter_complex = (
            f"[0:v]scale={int(width*1.2)}:{int(height*1.2)}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
            f"zoompan=z='min({start_scale}+({end_scale}-{start_scale})*on/{duration*24},{end_scale})':"
            f"x='iw/2-(iw/zoom/2)+{pan_x}*on/{duration*24}':"
            f"y='ih/2-(ih/zoom/2)+{pan_y}*on/{duration*24}':"
            f"d={int(duration*24)}:s={width}x{height}[v]"
        )

        cmd = [
            VideoEffects.FFMPEG, "-y",
            "-loop", "1", "-i", str(bg_path),
            "-i", str(audio_path),
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)

    @staticmethod
    def add_transition(scene_videos: list[Path], output_path: Path,
                       transition_type: str = "fade"):
        """添加场景转场效果"""
        if not scene_videos:
            return

        if len(scene_videos) == 1:
            # 单文件：直接用 ffmpeg stream copy
            subprocess.run([
                VideoEffects.FFMPEG, "-y",
                "-i", str(scene_videos[0]),
                "-c", "copy",
                str(output_path)
            ], capture_output=True)
            return

        # 构建 concat filter
        filter_parts = []
        for i, v in enumerate(scene_videos):
            filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")

        concat_inputs = "".join([f"[v{i}]" for i in range(len(scene_videos))])

        if transition_type == "fade":
            # 淡入淡出
            transition = f"concat=n={len(scene_videos)}:v=1:a=0"
            filter_complex = ";".join(filter_parts) + f";{concat_inputs}{transition}[v]"
        elif transition_type == "dissolve":
            # 交叉溶解 - 更复杂，需要 xfade
            filter_complex = VideoEffects._build_xfade(scene_videos, "fade", 0.5)
        elif transition_type == "slide":
            filter_complex = VideoEffects._build_xfade(scene_videos, "wipeleft", 0.3)
        else:
            filter_complex = ";".join(filter_parts) + f";{concat_inputs}concat=n={len(scene_videos)}:v=1:a=0[v]"

        # 音频合并
        audio_filter = VideoEffects._build_audio_concat(scene_videos)

        cmd = [VideoEffects.FFMPEG, "-y"]
        for v in scene_videos:
            cmd.extend(["-i", str(v)])
        cmd.extend([
            "-filter_complex", f"{filter_complex};{audio_filter}",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            str(output_path)
        ])
        subprocess.run(cmd, capture_output=True)

    @staticmethod
    def _get_media_duration_safe(media_path: Path) -> float:
        """安全获取媒体时长，预计算避免 shell 注入"""
        r = subprocess.run([
            VideoEffects.FFPROBE, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(media_path)
        ], capture_output=True, text=True)
        try:
            return float(r.stdout.strip())
        except (ValueError, AttributeError):
            logger.warning(f"Could not get duration for {media_path}")
            return 5.0

    @staticmethod
    def _build_xfade(videos: list[Path], transition: str, duration: float) -> str:
        """构建交叉淡化转场（安全：预计算时长，不在 filter_complex 中嵌入命令替换）"""
        if len(videos) < 2:
            return f"[0:v]null[v]"

        # 预计算每个视频的时长，避免 shell 注入
        offsets = []
        running_offset = 0.0
        for i in range(len(videos) - 1):
            dur = VideoEffects._get_media_duration_safe(videos[i])
            running_offset += dur - duration  # 上一个视频末尾 - 转场重叠
            offsets.append(running_offset)

        parts = [f"[0:v]null[vt0]"]
        for i in range(1, len(videos)):
            offset = offsets[i - 1]
            parts.append(
                f"[vt{i-1}][{i}:v]xfade=transition={transition}:duration={duration}:offset={offset:.3f}[vt{i}]"
            )

        return ";".join(parts) + f"[vt{len(videos)-1}]null[v]"

    @staticmethod
    def _build_audio_concat(videos: list[Path]) -> str:
        """构建音频合并"""
        inputs = "".join([f"[{i}:a]" for i in range(len(videos))])
        return f"{inputs}concat=n={len(videos)}:v=0:a=1[a]"

    @staticmethod
    def color_grade(bg_path: Path, output_path: Path, preset: str = "cinematic"):
        """应用电影级调色"""
        presets = {
            "cinematic": "eq=contrast=1.15:brightness=-0.05:saturation=1.1,colorbalance=rs=0.1:gs=-0.05:bs=-0.1",
            "warm": "eq=contrast=1.1:brightness=0.05:saturation=1.2,colorbalance=rs=0.2:gs=0.05:bs=-0.15",
            "cool": "eq=contrast=1.1:brightness=-0.05:saturation=1.1,colorbalance=rs=-0.15:gs=0.0:bs=0.2",
            "vintage": "eq=contrast=1.0:brightness=0.1:saturation=0.8,colorbalance=rs=0.15:gs=-0.05:bs=-0.1,hue=h=5",
            "noir": "eq=contrast=1.3:brightness=-0.1:saturation=0.3,colorchannelmixer=.3:.3:.3:0:.3:.3:.3:0:.3:.3:.3",
            "drama": "eq=contrast=1.2:brightness=-0.08:saturation=1.15,colorbalance=rs=0.15:gs=-0.1:bs=-0.05",
        }

        filter_str = presets.get(preset, presets["cinematic"])
        cmd = [
            VideoEffects.FFMPEG, "-y",
            "-i", str(bg_path),
            "-vf", filter_str,
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)

    @staticmethod
    def add_animated_subtitles(
        bg_path: Path, audio_path: Path, dialogues: list,
        output_path: Path, width: int = 1080, height: int = 1920,
        per_line_audio_dir: Path = None
    ):
        """添加动画字幕

        Args:
            per_line_audio_dir: 逐句音频文件所在目录（用于精确时间对齐）。
                               若提供，会根据每句音频的实际时长计算字幕时间；
                               否则回退到旧版均匀分配逻辑。
        """
        import os
        os.chdir(str(bg_path.parent))

        drawtext_filters = []
        line_times = VideoEffects._calculate_line_times(
            dialogues, audio_path, per_line_audio_dir
        )

        font_normal = "C\\:/Windows/Fonts/msyh.ttc"
        font_bold = "C\\:/Windows/Fonts/msyhbd.ttc"

        for i, (d, (start, end)) in enumerate(zip(dialogues, line_times)):
            char = d["character"].replace("'", "\\'").replace(":", "\\:")
            line = d["line"].replace("'", "\\'").replace(":", "\\:")
            emotion = d.get("emotion", "").replace("'", "\\'").replace(":", "\\:")

            char_display = f"{char} [{emotion}]" if emotion else char

            # 字幕背景
            dt_bg = (
                f"drawbox=x=0:y=h-280:w=iw:h=280:"
                f"color=black@0.65:t=fill:"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )
            drawtext_filters.append(dt_bg)

            # 角色名
            dt_char = (
                f"drawtext=text='{char_display}':"
                f"fontfile='{font_bold}':"
                f"fontsize=34:fontcolor=FFD700:"
                f"x=80:y=h-260:"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )
            drawtext_filters.append(dt_char)

            # 台词
            dt_line = (
                f"drawtext=text='{line}':"
                f"fontfile='{font_normal}':"
                f"fontsize=30:fontcolor=white:"
                f"x=80:y=h-210:"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )
            drawtext_filters.append(dt_line)

            # 分隔线
            dt_sep = (
                f"drawbox=x=80:y=h-200:w=w-160:h=2:"
                f"color=FFD700@0.5:t=fill:"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )
            drawtext_filters.append(dt_sep)

        vf = f"scale={width}:{height}"
        if drawtext_filters:
            vf += "," + ",".join(drawtext_filters)

        cmd = [
            VideoEffects.FFMPEG, "-y",
            "-loop", "1", "-i", str(bg_path),
            "-i", str(audio_path),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)

    @staticmethod
    def _calculate_line_times(
        dialogues: list, audio_path: Path, per_line_audio_dir: Path = None
    ) -> list:
        """计算每句台词的时间段

        优先模式（per_line_audio_dir 提供）：逐句用 ffprobe 获取每句音频的实际时长，
        按实际时长累加计算字幕起止时间。这要求 TTS 引擎是逐句生成独立音频文件的。

        回退模式：按音频总长均匀分配（不准确但兼容旧数据）。
        """
        if not dialogues:
            return []

        # 优先：基于逐句音频文件计算精确时间
        if per_line_audio_dir and per_line_audio_dir.exists():
            mp3_files = sorted(per_line_audio_dir.glob("line_*.mp3"))
            if mp3_files and len(mp3_files) == len(dialogues):
                times = []
                current_time = 0.0
                for i, mp3_path in enumerate(mp3_files):
                    dur = VideoEffects._get_media_duration_safe(mp3_path)
                    # 留 0.1s 间隙防止字幕重叠
                    gap = 0.15 if i < len(mp3_files) - 1 else 0.0
                    start = current_time
                    end = current_time + dur + gap
                    times.append((start, end))
                    current_time = end
                logger.info(
                    f"Subtitle timing: {len(times)} lines aligned to per-line audio "
                    f"(total duration: {current_time:.2f}s)"
                )
                return times
            else:
                logger.warning(
                    f"per_line_audio_dir has {len(mp3_files) if mp3_files else 0} files "
                    f"but {len(dialogues)} dialogues — falling back to uniform split"
                )

        # 回退：均匀分配（不准确，但保证不崩溃）
        total_dur = VideoEffects._get_duration(audio_path)
        per_line = total_dur / len(dialogues)
        logger.warning(
            f"Using uniform subtitle timing ({per_line:.2f}s per line). "
            f"Consider providing per-line audio files for accurate sync."
        )
        return [(i * per_line, (i + 1) * per_line - 0.1) for i in range(len(dialogues))]

    @staticmethod
    def add_vignette(bg_path: Path, output_path: Path, intensity: float = 0.3):
        """添加暗角效果"""
        cmd = [
            VideoEffects.FFMPEG, "-y", "-i", str(bg_path),
            "-vf", f"vignette=PI/{intensity*10}",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)

    @staticmethod
    def add_film_grain(bg_path: Path, output_path: Path, amount: float = 0.05):
        """添加胶片颗粒感"""
        cmd = [
            VideoEffects.FFMPEG, "-y", "-i", str(bg_path),
            "-vf", f"noise=alls={amount}:allf=t",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)

    @staticmethod
    def generate_intro(title: str, genre: str, output_path: Path,
                       width: int = 1080, height: int = 1920,
                       duration: float = 3.0):
        """生成片头动画"""
        from PIL import Image, ImageDraw, ImageFont

        frames = int(duration * 24)
        temp_dir = output_path.parent / "intro_frames"
        temp_dir.mkdir(exist_ok=True)

        font_title = VideoEffects._get_bold_font(64)
        font_genre = VideoEffects._get_font(32)

        for i in range(frames):
            progress = i / frames
            # 缓动函数
            ease = progress ** 0.5

            img = Image.new("RGB", (width, height), "#0a0a1a")
            draw = ImageDraw.Draw(img)

            # 发光粒子
            for _ in range(30):
                px = random.randint(0, width)
                py = random.randint(0, height)
                alpha = int(100 * ease * random.random())
                draw.ellipse([px, py, px + 2, py + 2], fill=(alpha, alpha, alpha + 50))

            # 标题淡入
            alpha = int(255 * min(progress * 3, 1))
            draw.text((width // 2, int(height // 2 - 60 * (1 - ease))),
                      title, fill=(alpha, alpha // 2, 0), font=font_title, anchor="mm")

            # 类型
            if progress > 0.3:
                genre_alpha = int(255 * min((progress - 0.3) * 3, 1))
                draw.text((width // 2, height // 2 + 60),
                          genre, fill=(genre_alpha, genre_alpha, genre_alpha),
                          font=font_genre, anchor="mm")

            frame_path = temp_dir / f"frame_{i:04d}.png"
            img.save(frame_path)

        # 合成视频
        cmd = [
            VideoEffects.FFMPEG, "-y",
            "-framerate", "24",
            "-i", str(temp_dir / "frame_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)

        # 清理
        for f in temp_dir.iterdir():
            f.unlink()
        temp_dir.rmdir()

    @staticmethod
    def generate_outro(output_path: Path, width: int = 1080, height: int = 1920,
                       duration: float = 2.0):
        """生成片尾"""
        from PIL import Image, ImageDraw, ImageFont

        frames = int(duration * 24)
        temp_dir = output_path.parent / "outro_frames"
        temp_dir.mkdir(exist_ok=True)

        font = VideoEffects._get_font(28)
        font_sm = VideoEffects._get_font(22)

        for i in range(frames):
            progress = i / frames
            alpha = int(255 * (1 - progress))

            img = Image.new("RGB", (width, height), "#0a0a1a")
            draw = ImageDraw.Draw(img)

            draw.text((width // 2, height // 2 - 40),
                      "感谢观看", fill=(alpha, alpha, alpha), font=font, anchor="mm")
            draw.text((width // 2, height // 2 + 30),
                      "DramaCLI Pro · AI短剧工厂", fill=(alpha // 2, alpha // 2, alpha // 2),
                      font=font_sm, anchor="mm")

            frame_path = temp_dir / f"frame_{i:04d}.png"
            img.save(frame_path)

        cmd = [
            VideoEffects.FFMPEG, "-y",
            "-framerate", "24",
            "-i", str(temp_dir / "frame_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)

        for f in temp_dir.iterdir():
            f.unlink()
        temp_dir.rmdir()