"""语音合成引擎 - 将剧本台词转为语音"""

import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import DramaConfig

console = Console()


class TTSEngine:
    """TTS 语音合成引擎"""

    def __init__(self, config: DramaConfig):
        self.config = config
        self._check_dependencies()

    def _check_dependencies(self):
        """检查依赖"""
        if self.config.tts_engine == "edge":
            try:
                import edge_tts
            except ImportError:
                raise RuntimeError(
                    "需要安装 edge-tts: pip install edge-tts"
                )

    async def _edge_tts(self, text: str, voice: str, output_path: Path,
                        speed: float = 1.0):
        """使用 Edge TTS 生成语音"""
        import edge_tts

        rate = f"{int((speed - 1.0) * 100):+d}%"
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(str(output_path))

    def _openai_tts(self, text: str, voice: str, output_path: Path,
                    speed: float = 1.0):
        """使用 OpenAI TTS"""
        from openai import OpenAI
        client = OpenAI(
            api_key=self.config.ai_api_key,
            base_url=self.config.ai_base_url
        )
        supported_voices = [
            "alloy", "ash", "ballad", "coral", "echo", "fable", "onyx",
            "nova", "sage", "shimmer", "verse", "marin", "cedar",
        ]
        kwargs = {
            "model": self.config.tts_model,
            "voice": voice if voice in supported_voices else "marin",
            "input": text,
            "speed": speed,
        }
        if not self.config.tts_model.startswith("tts-1"):
            kwargs["instructions"] = self.config.tts_instructions
        response = client.audio.speech.create(**kwargs)
        response.stream_to_file(str(output_path))

    def generate_line(self, text: str, voice: str, output_path: Path,
                      speed: float = 1.0) -> Path:
        """生成单句语音"""
        if self.config.tts_engine == "edge":
            asyncio.run(self._edge_tts(text, voice, output_path, speed))
        elif self.config.tts_engine == "openai":
            self._openai_tts(text, voice, output_path, speed)
        else:
            raise ValueError(f"不支持的 TTS 引擎: {self.config.tts_engine}")
        return output_path

    def generate_scene_audio(
        self, dialogues: list, voice_map: dict, scene_dir: Path
    ) -> list[Path]:
        """为一个场景生成所有对话音频"""
        audio_files = []
        scene_dir.mkdir(parents=True, exist_ok=True)

        for i, d in enumerate(dialogues):
            character = d["character"]
            line = d["line"]
            voice = voice_map.get(character, self.config.tts_voice)

            audio_path = scene_dir / f"line_{i:03d}_{character}.mp3"

            try:
                self.generate_line(line, voice, audio_path)
                audio_files.append(audio_path)
            except Exception as e:
                console.print(f"[red]✗ 语音生成失败 ({character}): {e}[/red]")

        return audio_files

    def generate_full_audio(
        self, script: dict, output_dir: Path, progress=None
    ) -> dict:
        """为整个剧本生成所有语音"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 构建角色-声音映射
        voice_map = {}
        voice_presets = {
            "温柔": "zh-CN-XiaoxiaoNeural",
            "霸气": "zh-CN-YunxiNeural",
            "活泼": "zh-CN-XiaoyiNeural",
            "冷淡": "zh-CN-YunyangNeural",
            "男声": "zh-CN-YunxiNeural",
            "女声": "zh-CN-XiaoxiaoNeural",
        }

        for char in script.get("characters", []):
            style = char.get("voice_style", "")
            voice_map[char["name"]] = voice_presets.get(
                style, "zh-CN-XiaoxiaoNeural"
            )

        result = {"episodes": []}

        for ep in script.get("episodes", []):
            ep_num = ep["episode_number"]
            ep_dir = output_dir / f"episode_{ep_num:02d}"
            ep_dir.mkdir(parents=True, exist_ok=True)

            episode_data = {"episode_number": ep_num, "scenes": []}

            for scene in ep.get("scenes", []):
                scene_num = scene["scene_number"]
                scene_dir = ep_dir / f"scene_{scene_num:02d}"
                scene_dir.mkdir(parents=True, exist_ok=True)

                if progress:
                    progress.update(
                        progress.task_ids[0],
                        description=f"[cyan]生成语音: 第{ep_num}集 场景{scene_num}..."
                    )

                audio_files = self.generate_scene_audio(
                    scene.get("dialogues", []), voice_map, scene_dir
                )
                episode_data["scenes"].append({
                    "scene_number": scene_num,
                    "audio_files": [str(f) for f in audio_files],
                    "scene_dir": str(scene_dir)
                })

            result["episodes"].append(episode_data)

        return result

    def merge_audio_files(self, audio_files: list[Path], output_path: Path,
                          silence_between: float = 0.3):
        """合并多个音频文件"""
        if not audio_files:
            return

        # 使用 ffmpeg 合并
        # 先创建 concat 文件列表
        concat_list = output_path.parent / "concat_list.txt"
        lines = []
        for f in audio_files:
            if f.exists():
                lines.append(f"file '{f.as_posix()}'")
        concat_list.write_text("\n".join(lines), encoding="utf-8")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)

        # 清理
        concat_list.unlink(missing_ok=True)
