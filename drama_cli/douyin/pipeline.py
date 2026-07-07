"""抖音短剧专业流水线 - 端到端自动化"""

import json
import subprocess
import os
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from .image_gen import ImageGenerator
from .bgm_engine import BGMEngine
from .video_effects import VideoEffects
from .templates import DramaTemplate, get_template, get_visual_config, build_prompt


FFMPEG = r"C:\Users\D0901\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\vm\tools\app\ffmpeg\ffmpeg.exe"
if not Path(FFMPEG).exists():
    FFMPEG = "ffmpeg"


@dataclass
class PipelineConfig:
    """流水线配置"""
    project_name: str = ""
    template_name: str = "霸道总裁"
    topic: str = ""
    episodes: int = 3
    style: str = "爽文"
    # AI 配置
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o"
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
        ffprobe_path = ffmpeg_path_obj.parent / "ffprobe.exe"
        VideoEffects.FFPROBE = str(ffprobe_path)
        self.image_gen = ImageGenerator(config.ai_api_key, config.ai_base_url)
        self.bgm_engine = BGMEngine(self.ffmpeg)
        self.effects = VideoEffects()
        self.template = get_template(config.template_name)

        # 状态
        self.script = None
        self.audio_data = None
        self.video_outputs = []

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

        # 1. 生成封面
        print("[1/6] 生成封面图...")
        cover_path = output_dir / "cover.png"
        self.image_gen.generate_cover(
            self.script.get("title", "短剧"),
            self.script.get("genre", ""),
            visual["visual_style"],
            visual["color_palette"],
            cover_path
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
                scene_images[key] = img_path

        return scene_images

    def _generate_audio(self) -> dict:
        """生成语音 - 优先使用已有音频，避免重复生成"""
        audio_dir = self.config.output_dir / "audio"

        # 尝试复用已有音频
        existing_audio = Path("audio")  # 项目根目录下的 audio/
        if existing_audio.exists():
            print("  📂 检测到已有音频，复用中...")
            result = {"episodes": []}
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
                            if not dst.exists():
                                import shutil
                                shutil.copy2(f, dst)
                            sc_data["audio_files"].append(str(dst))
                    ep_data["scenes"].append(sc_data)
                result["episodes"].append(ep_data)
            return result

        return result

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
                        r = subprocess.run([
                            "ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", af
                        ], capture_output=True, text=True)
                        try:
                            total_dur += float(r.stdout.strip())
                        except:
                            total_dur += 3
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

                # 渲染视频
                if self.config.enable_ken_burns:
                    self.effects.ken_burns_effect(
                        bg_path, final_audio, out_path,
                        self.config.width, self.config.height
                    )
                else:
                    self.effects.add_animated_subtitles(
                        bg_path, final_audio, scene.get("dialogues", []),
                        out_path, self.config.width, self.config.height
                    )

                scene_videos.append(out_path)
                print(f"  🎬 {key}")

        return scene_videos

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
                intro_path
            )

        # 生成片尾
        outro_path = output_dir / "outro.mp4"
        if self.config.enable_outro:
            self.effects.generate_outro(outro_path)

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
        package = {
            "title": self.script.get("title", ""),
            "genre": self.script.get("genre", ""),
            "description": self.script.get("description", ""),
            "episodes": len(self.script.get("episodes", [])),
            "tags": self.template.tags if self.template else [],
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

        return package