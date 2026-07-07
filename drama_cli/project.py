"""项目管理模块"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

PROJECTS_DIR = Path.home() / ".drama-cli" / "projects"


class Project:
    """短剧项目"""

    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.meta_path = path / "project.json"
        self.script_path = path / "script.json"
        self.audio_dir = path / "audio"
        self.video_dir = path / "video"

    @property
    def meta(self) -> dict:
        if self.meta_path.exists():
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        return {}

    @meta.setter
    def meta(self, data: dict):
        self.meta_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    @property
    def script(self) -> Optional[dict]:
        if self.script_path.exists():
            return json.loads(self.script_path.read_text(encoding="utf-8"))
        return None

    @property
    def exists(self) -> bool:
        return self.path.exists() and self.meta_path.exists()

    def create(self, genre: str = "", topic: str = ""):
        """创建新项目"""
        self.path.mkdir(parents=True, exist_ok=True)
        self.meta = {
            "name": self.name,
            "genre": genre,
            "topic": topic,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "created",
            "episodes": 0,
            "scenes": 0
        }

    def update_status(self, status: str, **kwargs):
        """更新项目状态"""
        data = self.meta
        data["status"] = status
        data["updated_at"] = datetime.now().isoformat()
        data.update(kwargs)
        self.meta = data

    def info(self) -> str:
        """获取项目信息"""
        m = self.meta
        title = m.get("title", self.name)
        return (
            f"[bold cyan]{title}[/bold cyan]\n"
            f"  类型: {m.get('genre', 'N/A')}\n"
            f"  主题: {m.get('topic', 'N/A')}\n"
            f"  集数: {m.get('episodes', 0)}\n"
            f"  状态: {m.get('status', 'unknown')}\n"
            f"  创建: {m.get('created_at', '')[:19]}\n"
            f"  更新: {m.get('updated_at', '')[:19]}"
        )


class ProjectManager:
    """项目管理器"""

    @staticmethod
    def list_projects() -> list[Project]:
        """列出所有项目"""
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        projects = []
        for d in sorted(PROJECTS_DIR.iterdir(), reverse=True):
            if d.is_dir() and (d / "project.json").exists():
                projects.append(Project(d.name, d))
        return projects

    @staticmethod
    def get_project(name: str) -> Optional[Project]:
        """获取项目"""
        path = PROJECTS_DIR / name
        if path.exists():
            return Project(name, path)
        return None

    @staticmethod
    def create_project(name: str, genre: str = "", topic: str = "") -> Project:
        """创建项目"""
        path = PROJECTS_DIR / name
        if path.exists():
            raise ValueError(f"项目 '{name}' 已存在")
        project = Project(name, path)
        project.create(genre, topic)
        return project

    @staticmethod
    def show_projects():
        """显示项目列表"""
        projects = ProjectManager.list_projects()
        if not projects:
            console.print(Panel(
                "[yellow]📭 还没有项目，使用 [bold]drama init <名称>[/bold] 创建第一个短剧项目！[/yellow]",
                border_style="yellow"
            ))
            return

        table = Table(title="🎬 短剧项目列表", border_style="cyan")
        table.add_column("项目名", style="cyan", no_wrap=True)
        table.add_column("类型", style="green")
        table.add_column("主题", style="yellow")
        table.add_column("集数", justify="center")
        table.add_column("状态", justify="center")
        table.add_column("更新时间", style="dim")

        for p in projects:
            m = p.meta
            status_map = {
                "created": "📝 已创建",
                "scripted": "📜 已生成剧本",
                "audio_done": "🔊 已合成语音",
                "video_done": "🎥 视频完成",
                "error": "❌ 错误"
            }
            status_text = status_map.get(m.get("status", ""), m.get("status", ""))

            table.add_row(
                m.get("name", p.name),
                m.get("genre", "-"),
                m.get("topic", "-")[:20],
                str(m.get("episodes", 0)),
                status_text,
                m.get("updated_at", "")[:19] if m.get("updated_at") else ""
            )

        console.print(table)