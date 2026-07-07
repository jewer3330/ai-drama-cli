"""配置管理模块"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


CONFIG_DIR = Path.home() / ".drama-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class DramaConfig:
    """全局配置"""
    # AI 配置
    ai_provider: str = "openai"  # openai / deepseek / custom
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o"

    # TTS 配置
    tts_engine: str = "edge"  # edge / openai / azure
    tts_voice: str = "zh-CN-XiaoxiaoNeural"  # 默认中文女声
    tts_speed: float = 1.0

    # 视频配置
    video_width: int = 1080
    video_height: int = 1920  # 竖屏短剧
    video_fps: int = 24
    bg_color: str = "#1a1a2e"

    # 默认模板
    default_genre: str = "都市"
    default_episodes: int = 3
    default_scenes_per_episode: int = 5

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    @classmethod
    def load(cls) -> "DramaConfig":
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return cls()

    @classmethod
    def get_or_create(cls) -> "DramaConfig":
        cfg = cls.load()
        cfg.save()
        return cfg