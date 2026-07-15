"""抖音短剧专业流水线 - 端到端自动化"""

import json
import subprocess
import re
import shutil
from pathlib import Path
from dataclasses import asdict, dataclass
from typing import Optional
from datetime import datetime

from .image_gen import ImageGenerator
from .bgm_engine import BGMEngine
from .video_effects import VideoEffects
from .templates import get_template, get_visual_config
from .ai_video import AIVideoError, SoraVideoGenerator, build_motion_prompt
from .viral import ViralPackage, build_viral_package
from ..config import DramaConfig
from ..tts_engine import TTSEngine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_FFMPEG_CANDIDATES = (
    PROJECT_ROOT / "tools" / "ffmpeg" / "ffmpeg.exe",
    PROJECT_ROOT / "tools" / "ffmpeg" / "ffmpeg",
)
FFMPEG = next(
    (str(candidate) for candidate in LOCAL_FFMPEG_CANDIDATES if candidate.exists()),
    shutil.which("ffmpeg") or "ffmpeg",
)


@dataclass
class PipelineConfig:
    """流水线配置"""
    project_name: str = ""
    template_name: str = "霸道总裁"
    topic: str = ""
    episodes: int = 3
    style: str = "爽文"
    mode: str = "pro"
    # AI 配置
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o"
    image_model: str = "gpt-image-1"
    image_quality: str = "high"
    video_engine: str = "auto"
    video_model: str = "sora-2-pro"
    video_poll_interval: float = 5.0
    video_timeout: float = 900.0
    tts_engine: str = "edge"
    tts_model: str = "gpt-4o-mini-tts"
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
    tts_speed: float = 1.0
    # 视频配置
    width: int = 1080
    height: int = 1920
    fps: int = 24
    # 效果开关
    enable_ken_burns: bool = True
    enable_bgm: bool = True
    enable_color_grade: bool = True
    enable_intro: bool = True
    enable_outro: bool = True
    enable_transitions: bool = True
    enable_viral_packaging: bool = True
    color_preset: str = "cinematic"
    bgm_volume: float = 0.25
    # 输出
    output_dir: Path = Path("output")


class DouyinPipeline:
    """抖音短剧专业流水线"""

    def __init__(self, config: PipelineConfig, ffmpeg_path: str = ""):
        self.config = config
        self.ffmpeg = ffmpeg_path or FFMPEG
        VideoEffects.FFMPEG = self.ffmpeg
        ffmpeg_path_obj = Path(self.ffmpeg)
        ffprobe_name = "ffprobe.exe" if ffmpeg_path_obj.suffix.lower() == ".exe" else "ffprobe"
        ffprobe_path = ffmpeg_path_obj.parent / ffprobe_name
        VideoEffects.FFPROBE = (
            str(ffprobe_path) if ffprobe_path.exists() else shutil.which("ffprobe") or ffprobe_name
        )
        self.image_gen = ImageGenerator(
            config.ai_api_key,
            config.ai_base_url,
            image_model=config.image_model,
            image_quality=config.image_quality,
            prefer_paid=config.mode == "pro",
        )
        self.bgm_engine = BGMEngine(self.ffmpeg)
        self.effects = VideoEffects()
        self.template = get_template(config.template_name)

        # 状态
        self.script = None
        self.audio_data = None
        self.video_outputs = []
        self.viral: Optional[ViralPackage] = None

    def set_script(self, script: dict):
        """直接设置剧本（跳过AI生成）"""
        self.script = script

    def run(self) -> Path:
        """运行完整流水线"""
        config = self.config
        output_dir = config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"  🎬 抖音短剧专业流水线")
        print(f"  模板: {config.template_name} | 主题: {config.topic}")
        print(f"  集数: {config.episodes} | 分辨率: {config.width}x{config.height}")
        print(f"{'='*60}\n")

        if not self.script:
            raise ValueError("请先设置剧本: pipeline.set_script(script)")

        visual = get_visual_config(self.template) if self.template else {
            "visual_style": "cinematic",
            "color_palette": "#1a1a2e,#e94560",
            "bgm_mood": "romantic_intense",
        }
        if config.enable_viral_packaging:
            self.viral = build_viral_package(self.script, self.template)

        if config.mode == "pro" and config.video_engine in {"auto", "sora"}:
            if config.ai_api_key:
                print(f"  🚀 Pro 视频模型: {config.video_model}")
            else:
                print("  ⚠️ 未配置 AI API key，视频运动将自动回退到电影感运镜")

        # 1. 生成封面
        print("[1/6] 生成封面图...")
        cover_path = output_dir / "cover.png"
        self.image_gen.generate_cover(
            self.script.get("title", "短剧"),
            self.script.get("genre", ""),
            visual["visual_style"],
            visual["color_palette"],
            cover_path,
            width=config.width,
            height=config.height,
            headline=self.viral.cover_headline if self.viral else "",
            subhead=self.viral.cover_subhead if self.viral else "",
            hook_text="高能反转" if self.viral else "",
        )
        print(f"  ✅ 封面: {cover_path}")

        # 2. 生成场景图
        print("[2/6] 生成场景图...")
        scene_images = self._generate_scene_images(visual)
        print(f"  ✅ 共 {len(scene_images)} 张场景图")

        # 3. 生成语音
        print("[3/6] 合成语音...")
        self.audio_data = self._generate_audio()
        print(f"  ✅ 语音合成完成")

        # 4. 生成BGM
        bgm_path = None
        if config.enable_bgm:
            print("[4/6] 生成BGM...")
            bgm_path = self._generate_bgm(visual)
            print(f"  ✅ BGM: {bgm_path}")

        # 5. 合成视频
        print("[5/6] 合成视频...")
        scene_videos = self._render_videos(scene_images, visual, bgm_path)
        print(f"  ✅ 共 {len(scene_videos)} 个场景视频")

        # 6. 合并 + 片头片尾
        print("[6/6] 合并 + 特效...")
        final_path = self._finalize(scene_videos, visual)
        print(f"\n{'='*60}")
        print(f"  🎉 短剧生成完成!")
        print(f"  📁 输出: {output_dir}")
        print(f"  🎬 视频: {final_path}")
        print(f"{'='*60}\n")

        return final_path

    def _generate_scene_images(self, visual: dict) -> dict:
        """生成所有场景图（v2: 优先AI场景图，其次角色合成）"""
        images_dir = self.config.output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        # 设置角色目录和AI场景目录
        char_dir = self.config.output_dir / "characters"
        scene_dir = self.config.output_dir / "scene_images"
        if char_dir.exists():
            ImageGenerator.CHARACTER_DIR = str(char_dir)
        if scene_dir.exists():
            ImageGenerator.SCENE_DIR = str(scene_dir)

        scene_images = {}

        for ep in self.script.get("episodes", []):
            ep_num = ep["episode_number"]
            for scene in ep.get("scenes", []):
                sc_num = scene["scene_number"]
                key = f"ep{ep_num}_sc{sc_num}"
                img_path = images_dir / f"{key}.png"

                self.image_gen.generate_scene(
                    scene, ep_num, img_path,
                    self.config.width, self.config.height,
                    visual.get("visual_style", "cinematic"),
                    visual.get("color_palette", "#1a1a2e,#e94560"),
                    scene_key=key
                )
                if self.config.enable_color_grade and img_path.exists():
                    graded_path = images_dir / f"{key}_graded.png"
                    self.effects.color_grade(img_path, graded_path, self.config.color_preset)
                    if graded_path.exists() and graded_path.stat().st_size > 0:
                        graded_path.replace(img_path)
                scene_images[key] = img_path

        return scene_images

    def _generate_audio(self) -> dict:
        """生成语音，优先复用缓存，没有缓存时调用配置的神经语音。"""
        audio_dir = self.config.output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        # 先检查当前项目缓存，再兼容项目根目录下的旧 audio/。
        for existing_audio in (audio_dir, Path("audio")):
            if not existing_audio.exists():
                continue
            result = {"episodes": []}
            reused = 0
            for ep in self.script.get("episodes", []):
                ep_num = ep["episode_number"]
                ep_data = {"episode_number": ep_num, "scenes": []}
                for scene in ep.get("scenes", []):
                    sc_num = scene["scene_number"]
                    src_dir = existing_audio / f"episode_{ep_num:02d}" / f"scene_{sc_num:02d}"
                    dst_dir = audio_dir / f"episode_{ep_num:02d}" / f"scene_{sc_num:02d}"
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    sc_data = {"scene_number": sc_num, "audio_files": []}
                    if src_dir.exists():
                        for f in sorted(src_dir.glob("line_*.mp3")):
                            dst = dst_dir / f.name
                            if f.resolve() != dst.resolve() and not dst.exists():
                                shutil.copy2(f, dst)
                            sc_data["audio_files"].append(str(dst))
                            reused += 1
                    ep_data["scenes"].append(sc_data)
                result["episodes"].append(ep_data)
            if reused:
                print(f"  📂 复用 {reused} 条已有语音")
                return result

        tts_config = DramaConfig(
            ai_api_key=self.config.ai_api_key,
            ai_base_url=self.config.ai_base_url,
            ai_model=self.config.ai_model,
            tts_engine=self.config.tts_engine,
            tts_model=self.config.tts_model,
            tts_voice=self.config.tts_voice,
            tts_speed=self.config.tts_speed,
        )
        return TTSEngine(tts_config).generate_full_audio(self.script, audio_dir)

    def _media_duration(self, media_path: Path) -> float:
        result = subprocess.run(
            [self.ffmpeg, "-hide_banner", "-i", str(media_path)],
            capture_output=True,
            text=True,
        )
        match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)", result.stderr)
        if not match:
            return 3.0
        return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))

    def _generate_bgm(self, visual: dict) -> Optional[Path]:
        """生成BGM"""
        bgm_dir = self.config.output_dir / "bgm"
        bgm_dir.mkdir(exist_ok=True)

        mood = visual.get("bgm_mood", "romantic_intense")

        # 估算总时长
        total_dur = 0
        for ep_data in self.audio_data.get("episodes", []):
            for sc_data in ep_data.get("scenes", []):
                for af in sc_data.get("audio_files", []):
                    if Path(af).exists():
                        total_dur += self._media_duration(Path(af))
                        total_dur += 0.3

        total_dur = max(total_dur, 30)

        bgm_path = bgm_dir / "background_music.mp3"
        self.bgm_engine.generate_bgm(mood, total_dur, bgm_path, self.config.bgm_volume)
        return bgm_path

    def _render_videos(self, scene_images: dict, visual: dict,
                       bgm_path: Optional[Path]) -> list[Path]:
        """渲染所有场景视频"""
        video_dir = self.config.output_dir / "videos"
        video_dir.mkdir(exist_ok=True)
        scene_videos = []
        engine = self.config.video_engine.lower().replace("_", "-")
        use_sora = engine == "sora" or (engine == "auto" and self.config.mode == "pro")
        sora = None
        if use_sora and self.config.ai_api_key:
            sora = SoraVideoGenerator(
                self.config.ai_api_key,
                self.config.ai_base_url,
                model=self.config.video_model,
                poll_interval=self.config.video_poll_interval,
                timeout=self.config.video_timeout,
            )

        for ep_data in self.audio_data.get("episodes", []):
            ep_num = ep_data["episode_number"]
            ep = self.script["episodes"][ep_num - 1]

            for sc_data in ep_data.get("scenes", []):
                sc_num = sc_data["scene_number"]
                scene = ep["scenes"][sc_num - 1]

                key = f"ep{ep_num}_sc{sc_num}"
                bg_path = scene_images.get(key)
                audio_files = [Path(f) for f in sc_data.get("audio_files", [])]
                out_path = video_dir / f"{key}.mp4"

                if not audio_files or not bg_path:
                    continue

                # 合并音频
                merged_audio = video_dir / f"audio_{key}.mp3"
                self._merge_audio(audio_files, merged_audio)

                # 混入BGM
                if bgm_path and bgm_path.exists():
                    final_audio = video_dir / f"final_audio_{key}.mp3"
                    self.bgm_engine.mix_bgm_with_dialogue(
                        merged_audio, bgm_path, final_audio, self.config.bgm_volume
                    )
                else:
                    final_audio = merged_audio

                rendered_with_ai = False
                if sora:
                    ai_dir = self.config.output_dir / "ai_video"
                    ai_dir.mkdir(exist_ok=True)
                    raw_clip = ai_dir / f"{key}_{self.config.video_model}.mp4"
                    try:
                        duration = self._media_duration(final_audio)
                        sora.generate(
                            build_motion_prompt(scene, visual.get("visual_style", "cinematic")),
                            raw_clip,
                            reference_image=bg_path,
                            seconds=SoraVideoGenerator.seconds_for_duration(duration),
                            size="720x1280",
                        )
                        self._mux_ai_clip(raw_clip, final_audio, out_path)
                        rendered_with_ai = out_path.exists() and out_path.stat().st_size > 0
                        print(f"  ✨ {key} · {self.config.video_model}")
                    except (AIVideoError, OSError, ValueError) as exc:
                        print(f"  ⚠️ {key} AI 视频失败，回退电影感运镜: {exc}")

                # 无云端视频或调用失败时使用稳定的本地电影感运镜。
                if not rendered_with_ai and self.config.enable_ken_burns:
                    self.effects.ken_burns_effect(
                        bg_path, final_audio, out_path,
                        self.config.width, self.config.height,
                        duration=self._media_duration(final_audio),
                    )
                elif not rendered_with_ai:
                    self.effects.add_animated_subtitles(
                        bg_path, final_audio, scene.get("dialogues", []),
                        out_path, self.config.width, self.config.height
                    )

                scene_videos.append(out_path)
                print(f"  🎬 {key}")

        return scene_videos

    def _mux_ai_clip(self, clip_path: Path, audio_path: Path, output_path: Path):
        """Replace generated audio and loop the visual only when dialogue runs longer."""
        filter_video = (
            f"scale={self.config.width}:{self.config.height}:force_original_aspect_ratio=increase,"
            f"crop={self.config.width}:{self.config.height},fps={self.config.fps},format=yuv420p"
        )
        result = subprocess.run([
            self.ffmpeg, "-y", "-stream_loop", "-1", "-i", str(clip_path),
            "-i", str(audio_path), "-vf", filter_video,
            "-map", "0:v:0", "-map", "1:a:0", "-shortest",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            str(output_path),
        ], capture_output=True)
        if result.returncode != 0:
            error = result.stderr.decode(errors="ignore")[-800:]
            raise AIVideoError(f"FFmpeg could not package AI video: {error}")

    def _merge_audio(self, audio_files: list[Path], output_path: Path):
        """合并音频文件"""
        if not audio_files:
            return

        if len(audio_files) == 1:
            subprocess.run([self.ffmpeg, "-y", "-i", str(audio_files[0]),
                           "-c", "copy", str(output_path)], capture_output=True)
            return

        silence = output_path.parent / "silence.mp3"
        subprocess.run([self.ffmpeg, "-y", "-f", "lavfi",
                       "-i", "anullsrc=r=44100:cl=mono", "-t", "0.3",
                       str(silence)], capture_output=True)

        concat_txt = output_path.parent / "concat_audio.txt"
        entries = []
        for i, af in enumerate(audio_files):
            if af.exists():
                entries.append(f"file '{af.as_posix()}'")
                if i < len(audio_files) - 1:
                    entries.append(f"file '{silence.as_posix()}'")
        concat_txt.write_text("\n".join(entries), encoding="utf-8")

        subprocess.run([self.ffmpeg, "-y", "-f", "concat", "-safe", "0",
                       "-i", str(concat_txt), "-c", "copy", str(output_path)],
                       capture_output=True)

    def _finalize(self, scene_videos: list[Path], visual: dict) -> Path:
        """合并所有场景 + 片头片尾 + 转场"""
        output_dir = self.config.output_dir

        # 生成片头
        intro_path = output_dir / "intro.mp4"
        if self.config.enable_intro:
            self.effects.generate_intro(
                self.script.get("title", "短剧"),
                self.script.get("genre", ""),
                intro_path,
                width=self.config.width,
                height=self.config.height,
                hook_text=self.viral.opening_hook if self.viral else "",
                subline=self.viral.cover_subhead if self.viral else "",
            )

        # 生成片尾
        outro_path = output_dir / "outro.mp4"
        if self.config.enable_outro:
            self.effects.generate_outro(
                outro_path,
                width=self.config.width,
                height=self.config.height,
                cta_text=self.viral.outro_cta if self.viral else "",
            )

        # 合并所有
        all_videos = []
        if self.config.enable_intro and intro_path.exists():
            all_videos.append(intro_path)
        all_videos.extend(scene_videos)
        if self.config.enable_outro and outro_path.exists():
            all_videos.append(outro_path)

        final_path = output_dir / "final_douyin.mp4"

        if self.config.enable_transitions and len(all_videos) > 1:
            self.effects.add_transition(all_videos, final_path, "fade")
        else:
            # 简单合并
            concat_txt = output_dir / "final_concat.txt"
            concat_txt.write_text("\n".join(
                [f"file '{f.as_posix()}'" for f in all_videos if f.exists()]
            ), encoding="utf-8")
            subprocess.run([self.ffmpeg, "-y", "-f", "concat", "-safe", "0",
                           "-i", str(concat_txt), "-c", "copy", str(final_path)],
                           capture_output=True)

        return final_path

    def export_douyin_package(self) -> dict:
        """导出抖音发布包"""
        output_dir = self.config.output_dir
        if self.config.enable_viral_packaging and not self.viral:
            self.viral = build_viral_package(self.script, self.template)
        viral_data = asdict(self.viral) if self.viral else {}
        package = {
            "title": self.viral.publish_title if self.viral else self.script.get("title", ""),
            "original_title": self.script.get("title", ""),
            "genre": self.script.get("genre", ""),
            "description": self.script.get("description", ""),
            "caption": self.viral.caption if self.viral else self.script.get("description", ""),
            "episodes": len(self.script.get("episodes", [])),
            "tags": self.viral.hashtags if self.viral else (self.template.tags if self.template else []),
            "viral": viral_data,
            "ai": {
                "mode": self.config.mode,
                "script_model": self.config.ai_model,
                "image_model": self.config.image_model,
                "video_engine": self.config.video_engine,
                "video_model": self.config.video_model,
                "tts_engine": self.config.tts_engine,
                "tts_model": self.config.tts_model,
            },
            "video": str(output_dir / "final_douyin.mp4"),
            "cover": str(output_dir / "cover.png"),
            "script": str(output_dir / "script.json"),
            "generated_at": datetime.now().isoformat(),
        }

        # 保存发布信息
        (output_dir / "douyin_package.json").write_text(
            json.dumps(package, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        # 保存剧本
        (output_dir / "script.json").write_text(
            json.dumps(self.script, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        if self.viral:
            (output_dir / "publish_copy.txt").write_text(
                f"{self.viral.publish_title}\n\n{self.viral.caption}\n",
                encoding="utf-8",
            )

        return package
