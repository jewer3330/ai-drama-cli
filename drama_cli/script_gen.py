"""剧本生成引擎 - AI 驱动的短剧剧本创作"""

import json
import re
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .ai_client import AIClient
from .config import DramaConfig

console = Console()

SYSTEM_PROMPT = """你是一位顶尖的短剧编剧，擅长创作引人入胜的短剧剧本。
你需要根据用户提供的主题和设定，创作出结构完整、节奏紧凑的短剧剧本。

## 输出格式要求
你必须严格按照以下 JSON 格式输出剧本，不要输出任何其他内容：

```json
{
  "title": "剧名",
  "genre": "类型",
  "description": "一句话简介",
  "characters": [
    {
      "name": "角色名",
      "role": "主角/配角/反派等",
      "gender": "男/女",
      "age": 25,
      "personality": "性格描述",
      "voice_style": "温柔/霸气/活泼/冷淡等",
      "description": "角色背景简介"
    }
  ],
  "episodes": [
    {
      "episode_number": 1,
      "title": "第X集标题",
      "scenes": [
        {
          "scene_number": 1,
          "location": "场景地点",
          "time": "时间（白天/夜晚/清晨等）",
          "visual_description": "画面描述（用于视频生成）",
          "dialogues": [
            {
              "character": "角色名",
              "line": "台词内容",
              "emotion": "情绪（开心/愤怒/悲伤/紧张等）",
              "action": "动作描述"
            }
          ]
        }
      ]
    }
  ]
}
```

## 创作要求
1. 每集包含 3-6 个场景，节奏紧凑
2. 对话要自然，符合角色性格
3. 每集结尾要有悬念或钩子
4. 画面描述要具体，方便后续视频生成
5. 台词要短小精悍，适合短视频平台
"""


class ScriptGenerator:
    """剧本生成器"""

    def __init__(self, config: DramaConfig):
        self.config = config
        self.ai = AIClient(config)

    def generate(
        self,
        topic: str,
        genre: str = "",
        episodes: int = 0,
        scenes_per_episode: int = 0,
        style: str = "爽文",
        stream: bool = True,
    ) -> dict:
        """生成完整剧本"""
        genre = genre or self.config.default_genre
        episodes = episodes or self.config.default_episodes
        scenes_per_episode = scenes_per_episode or self.config.default_scenes_per_episode

        user_prompt = f"""请创作一部短剧剧本：

【主题】{topic}
【类型】{genre}
【集数】{episodes} 集
【每集场景数】约 {scenes_per_episode} 个场景
【风格】{style}

请严格按照 JSON 格式输出完整剧本。"""

        console.print(Panel.fit(
            f"[bold cyan]🎬 正在生成短剧剧本[/bold cyan]\n"
            f"主题: {topic}\n类型: {genre}\n集数: {episodes} 集",
            border_style="cyan"
        ))

        if stream:
            return self._generate_stream(user_prompt)
        else:
            return self._generate_sync(user_prompt)

    def _generate_sync(self, user_prompt: str) -> dict:
        """同步生成"""
        with console.status("[bold green]AI 正在创作剧本...[/bold green]", spinner="dots"):
            raw = self.ai.chat(SYSTEM_PROMPT, user_prompt, temperature=0.85)
        return self._parse_script(raw)

    def _generate_stream(self, user_prompt: str) -> dict:
        """流式生成"""
        console.print("\n[bold yellow]📝 AI 创作中...[/bold yellow]\n")
        full_text = ""
        try:
            for chunk in self.ai.chat_stream(SYSTEM_PROMPT, user_prompt, temperature=0.85):
                console.print(chunk, end="", style="dim")
                full_text += chunk
        except RuntimeError:
            console.print("\n[yellow]⚠ 流式失败，切换到同步模式...[/yellow]")
            return self._generate_sync(user_prompt)

        console.print("\n")
        return self._parse_script(full_text)

    def _parse_script(self, raw: str) -> dict:
        """解析 AI 返回的 JSON 剧本"""
        # 尝试提取 JSON
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', raw)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接找 JSON 对象
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = raw

        try:
            script = json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试修复常见问题
            cleaned = self._fix_json(json_str)
            try:
                script = json.loads(cleaned)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"剧本解析失败: {e}\n原始内容: {raw[:500]}...")

        self._validate_script(script)
        return script

    def _fix_json(self, text: str) -> str:
        """尝试修复损坏的 JSON"""
        text = text.strip()
        if not text.startswith('{'):
            text = '{' + text
        if not text.endswith('}'):
            text = text + '}'
        return text

    def _validate_script(self, script: dict):
        """验证剧本结构"""
        required = ["title", "characters", "episodes"]
        for key in required:
            if key not in script:
                raise ValueError(f"剧本缺少必要字段: {key}")
        if not script["episodes"]:
            raise ValueError("剧本至少需要 1 集")
        if not script["characters"]:
            raise ValueError("剧本至少需要 1 个角色")

    def save(self, script: dict, output_dir: Path):
        """保存剧本到文件"""
        output_dir.mkdir(parents=True, exist_ok=True)
        script_path = output_dir / "script.json"
        script_path.write_text(
            json.dumps(script, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        # 同时生成可读的 Markdown 版本
        md = self._to_markdown(script)
        md_path = output_dir / "script.md"
        md_path.write_text(md, encoding="utf-8")

        console.print(f"\n[green]✅ 剧本已保存:[/green] {script_path}")
        console.print(f"[green]✅ Markdown 版本:[/green] {md_path}")

    def _to_markdown(self, script: dict) -> str:
        """将剧本转为 Markdown 格式"""
        lines = [
            f"# {script.get('title', '未命名短剧')}",
            "",
            f"> **类型:** {script.get('genre', '')}",
            f"> **简介:** {script.get('description', '')}",
            "",
            "---",
            "",
            "## 👥 角色列表",
            ""
        ]

        for char in script.get("characters", []):
            lines.extend([
                f"### {char['name']} ({char.get('role', '')})",
                f"- **性别:** {char.get('gender', '')}",
                f"- **年龄:** {char.get('age', '')}",
                f"- **性格:** {char.get('personality', '')}",
                f"- **配音风格:** {char.get('voice_style', '')}",
                f"- **简介:** {char.get('description', '')}",
                ""
            ])

        lines.extend(["---", ""])

        for ep in script.get("episodes", []):
            lines.extend([
                f"## 第 {ep['episode_number']} 集: {ep.get('title', '')}",
                ""
            ])

            for scene in ep.get("scenes", []):
                lines.extend([
                    f"### 场景 {scene['scene_number']}: {scene.get('location', '')}",
                    f"**时间:** {scene.get('time', '')}",
                    "",
                    f"*{scene.get('visual_description', '')}*",
                    ""
                ])

                for d in scene.get("dialogues", []):
                    emotion = d.get('emotion', '')
                    action = d.get('action', '')
                    line = f"**{d['character']}**"
                    if emotion:
                        line += f" ({emotion})"
                    line += f": {d['line']}"
                    if action:
                        line += f" *[{action}]*"
                    lines.append(line)
                    lines.append("")

                lines.append("---")
                lines.append("")

        return "\n".join(lines)