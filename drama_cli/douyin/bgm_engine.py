"""BGM背景音乐引擎 - 情绪驱动的音乐匹配系统"""

import subprocess
from pathlib import Path
from typing import Optional
import json

# ============================================================
# BGM 情绪映射表
# ============================================================

BGM_MOOD_MAP = {
    "romantic_intense": {
        "description": "浪漫紧张",
        "genres": ["love", "drama"],
        "tempo": "medium",
        "instruments": ["piano", "strings"],
    },
    "ancient_epic": {
        "description": "古风史诗",
        "genres": ["epic", "traditional"],
        "tempo": "slow",
        "instruments": ["guqin", "erhu", "flute"],
    },
    "dark_intense": {
        "description": "暗黑紧张",
        "genres": ["dark", "suspense"],
        "tempo": "slow",
        "instruments": ["cello", "bass"],
    },
    "elegant_dramatic": {
        "description": "优雅戏剧",
        "genres": ["classical", "drama"],
        "tempo": "medium",
        "instruments": ["piano", "violin"],
    },
    "suspense": {
        "description": "悬疑",
        "genres": ["suspense", "thriller"],
        "tempo": "slow",
        "instruments": ["synth", "bass"],
    },
    "sweet_light": {
        "description": "甜蜜轻快",
        "genres": ["pop", "acoustic"],
        "tempo": "fast",
        "instruments": ["guitar", "ukulele"],
    },
    "epic_intense": {
        "description": "史诗激昂",
        "genres": ["epic", "orchestral"],
        "tempo": "medium",
        "instruments": ["orchestra", "choir", "brass"],
    },
    "glamorous": {
        "description": "华丽璀璨",
        "genres": ["electronic", "pop"],
        "tempo": "medium",
        "instruments": ["synth", "piano"],
    },
    "dark_tension": {
        "description": "末日紧张",
        "genres": ["dark", "industrial"],
        "tempo": "slow",
        "instruments": ["synth", "drone"],
    },
    "epic_fantasy": {
        "description": "仙侠奇幻",
        "genres": ["epic", "world"],
        "tempo": "medium",
        "instruments": ["orchestra", "choir", "flute"],
    },
}

# 场景情绪映射
SCENE_EMOTION_MAP = {
    "紧张": "suspense",
    "悲伤": "dark_intense",
    "开心": "sweet_light",
    "愤怒": "epic_intense",
    "浪漫": "romantic_intense",
    "恐惧": "dark_tension",
    "感动": "elegant_dramatic",
    "霸气": "epic_intense",
    "甜蜜": "sweet_light",
    "悬疑": "suspense",
}


class BGMEngine:
    """BGM背景音乐引擎"""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg = ffmpeg_path
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        try:
            subprocess.run([self.ffmpeg, "-version"], capture_output=True, check=True)
        except Exception:
            self.ffmpeg = "ffmpeg"

    def generate_bgm(self, mood: str, duration: float, output_path: Path,
                     volume: float = 0.3) -> Optional[Path]:
        """根据情绪生成背景音乐"""
        import random

        mood_config = BGM_MOOD_MAP.get(mood, BGM_MOOD_MAP["romantic_intense"])

        # 使用 FFmpeg 生成合成音乐
        # 通过正弦波 + 包络生成简单但有效的背景音乐
        freq_map = {
            "slow": (110, 220),
            "medium": (220, 440),
            "fast": (330, 660),
        }
        freq_range = freq_map.get(mood_config["tempo"], (220, 440))
        base_freq = random.uniform(*freq_range)

        # 生成多层音频轨道
        tracks = []

        # 1. 基础低频 (氛围)
        bass_path = output_path.parent / f"bgm_bass_{output_path.stem}.wav"
        self._generate_wave(bass_path, base_freq / 2, duration, "sine", 0.3 * volume)

        # 2. 中频旋律 (主旋律)
        melody_path = output_path.parent / f"bgm_melody_{output_path.stem}.wav"
        self._generate_wave(melody_path, base_freq, duration, "sine", 0.5 * volume)

        # 3. 高频泛音 (亮度)
        harmonic_path = output_path.parent / f"bgm_harmonic_{output_path.stem}.wav"
        self._generate_wave(harmonic_path, base_freq * 2, duration, "triangle", 0.2 * volume)

        # 混合
        self._mix_audio([bass_path, melody_path, harmonic_path], output_path, volume)

        # 清理
        for p in [bass_path, melody_path, harmonic_path]:
            p.unlink(missing_ok=True)

        return output_path

    def _generate_wave(self, output_path: Path, freq: float, duration: float,
                       waveform: str = "sine", volume: float = 0.5):
        """生成单频波形"""
        # 使用 FFmpeg 的 sine 音频源
        cmd = [
            self.ffmpeg, "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency={freq}:duration={duration}",
            "-af", f"volume={volume},afade=t=in:d=0.5,afade=t=out:st={duration-0.5}:d=0.5",
            "-c:a", "pcm_s16le",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)

    def _mix_audio(self, input_paths: list[Path], output_path: Path,
                   volume: float = 0.5):
        """混合多个音频轨道"""
        if not input_paths:
            return

        # 构建 filter_complex
        inputs = []
        for p in input_paths:
            inputs.extend(["-i", str(p)])

        # 混合滤镜
        n = len(input_paths)
        mix_filter = f"amix=inputs={n}:duration=longest:dropout_transition=0"

        cmd = [
            self.ffmpeg, "-y", *inputs,
            "-filter_complex", mix_filter,
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)

    def mix_bgm_with_dialogue(self, dialogue_audio: Path, bgm_path: Path,
                              output_path: Path, bgm_volume: float = 0.25):
        """将BGM混入对话音频"""
        cmd = [
            self.ffmpeg, "-y",
            "-i", str(dialogue_audio),
            "-i", str(bgm_path),
            "-filter_complex",
            f"[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0",
            "-c:a", "libmp3lame", "-b:a", "192k",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)
        return output_path

    def get_mood_for_scene(self, scene: dict) -> str:
        """根据场景情绪确定BGM情绪"""
        dialogues = scene.get("dialogues", [])
        if not dialogues:
            return "romantic_intense"

        # 统计场景中最多出现的情绪
        emotion_counts = {}
        for d in dialogues:
            emotion = d.get("emotion", "")
            if emotion in SCENE_EMOTION_MAP:
                mood = SCENE_EMOTION_MAP[emotion]
                emotion_counts[mood] = emotion_counts.get(mood, 0) + 1

        if emotion_counts:
            return max(emotion_counts, key=emotion_counts.get)
        return "romantic_intense"

    def add_sound_effects(self, scene: dict, audio_path: Path, output_path: Path):
        """添加音效 (转场、提示音等)"""
        dialogues = scene.get("dialogues", [])

        # 生成提示音
        ding_path = output_path.parent / "ding.wav"
        self._generate_wave(ding_path, 880, 0.15, "sine", 0.3)

        # 在对话之间插入提示音
        # 简化版：直接返回原音频
        if not dialogues or len(dialogues) <= 1:
            return audio_path

        # 合并音效
        temp_path = output_path.parent / "with_sfx.mp3"

        concat_parts = []
        for i, d in enumerate(dialogues):
            concat_parts.append(str(audio_path))
            if i < len(dialogues) - 1:
                concat_parts.append(str(ding_path))

        # 简化处理：直接返回
        return audio_path