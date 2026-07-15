"""DramaCLI - AI 短剧自动生成工具 🎬

用法:
  drama init <名称>             创建新短剧项目
  drama generate [主题]         生成短剧剧本
  drama tts                     合成语音
  drama video                   生成视频
  drama play [主题]             一键生成完整短剧
  drama list                    列出所有项目
  drama info [名称]             查看项目详情
  drama config                  管理配置
"""

import os
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.syntax import Syntax
from rich import print as rprint
from typing import Optional

from .config import DramaConfig
from .script_gen import ScriptGenerator
from .tts_engine import TTSEngine
from .video_gen import VideoGenerator
from .project import Project, ProjectManager
from .comfyui import comfyui_app
from .anime import anime_app
from . import __version__

app = typer.Typer(
    name="drama",
    help="🎬 AI 短剧自动生成 CLI 工具",
    add_completion=True,
    rich_markup_mode="rich",
)

console = Console()

# ============================================================
# 子命令
# ============================================================

config_app = typer.Typer(help="配置管理")
app.add_typer(config_app, name="config")
app.add_typer(comfyui_app, name="comfyui")
app.add_typer(anime_app, name="anime")


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """主入口 - 显示帮助"""
    if ctx.invoked_subcommand is None:
        _show_banner()
        _show_quickstart()


# ============================================================
# init - 初始化项目
# ============================================================

@app.command()
def init(
    name: str = typer.Argument(..., help="项目名称"),
    genre: str = typer.Option("都市", "--genre", "-g", help="短剧类型"),
    topic: str = typer.Option("", "--topic", "-t", help="短剧主题"),
):
    """✨ 初始化一个新的短剧项目"""
    try:
        project = ProjectManager.create_project(name, genre, topic)

        console.print(Panel.fit(
            f"[bold green]✨ 项目创建成功！[/bold green]\n\n"
            f"[cyan]项目名:[/cyan] {name}\n"
            f"[cyan]类型:[/cyan] {genre}\n"
            f"[cyan]路径:[/cyan] {project.path}\n\n"
            f"[dim]下一步: drama generate \"你的主题\" -p {name}[/dim]",
            border_style="green",
            title="🎬 新项目"
        ))
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)


# ============================================================
# generate - 生成剧本
# ============================================================

@app.command()
def generate(
    topic: str = typer.Argument("", help="短剧主题/一句话梗概"),
    project: str = typer.Option("", "--project", "-p", help="指定项目名"),
    genre: str = typer.Option("", "--genre", "-g", help="短剧类型"),
    episodes: int = typer.Option(0, "--episodes", "-e", help="集数"),
    style: str = typer.Option("爽文", "--style", "-s", help="创作风格"),
    no_stream: bool = typer.Option(False, "--no-stream", help="禁用流式输出"),
):
    """📝 AI 生成短剧剧本"""
    cfg = DramaConfig.get_or_create()

    if not cfg.ai_api_key:
        console.print(
            "[red]✗ 请先配置 AI API Key:[/red]\n"
            "  [cyan]drama config set-ai --key YOUR_API_KEY[/cyan]\n"
            "  [dim]支持 OpenAI / DeepSeek / 自定义 API[/dim]"
        )
        raise typer.Exit(1)

    # 如果指定了项目，加载项目信息
    proj = None
    if project:
        proj = ProjectManager.get_project(project)
        if not proj:
            console.print(f"[red]✗ 项目 '{project}' 不存在[/red]")
            raise typer.Exit(1)
        if not topic:
            topic = proj.meta.get("topic", "")
        if not genre:
            genre = proj.meta.get("genre", "")
        if not topic:
            topic = typer.prompt("请输入短剧主题")

    if not topic:
        topic = typer.prompt("请输入短剧主题")

    generator = ScriptGenerator(cfg)
    script = generator.generate(
        topic=topic,
        genre=genre,
        episodes=episodes,
        style=style,
        stream=not no_stream
    )

    # 保存剧本
    if proj:
        output_dir = proj.path
        proj.update_status(
            "scripted",
            title=script.get("title", ""),
            episodes=len(script.get("episodes", [])),
            genre=script.get("genre", "")
        )
    else:
        output_dir = Path.cwd() / "drama_output"
        output_dir.mkdir(parents=True, exist_ok=True)

    generator.save(script, output_dir)

    # 显示剧本摘要
    _show_script_summary(script)


# ============================================================
# tts - 语音合成
# ============================================================

@app.command()
def tts(
    project: str = typer.Option("", "--project", "-p", help="项目名"),
    script_file: str = typer.Option("", "--script", "-s", help="剧本 JSON 文件路径"),
):
    """🔊 将剧本台词合成为语音"""
    cfg = DramaConfig.get_or_create()

    # 加载剧本
    script = _load_script_from_project_or_file(project, script_file)
    if not script:
        raise typer.Exit(1)

    # 确定输出目录
    if project:
        proj = ProjectManager.get_project(project)
        output_dir = proj.audio_dir
    else:
        output_dir = Path(script_file).parent / "audio" if script_file else Path.cwd() / "drama_output" / "audio"

    console.print(Panel.fit(
        f"[bold cyan]🔊 开始语音合成[/bold cyan]\n"
        f"剧名: {script.get('title', '未知')}\n"
        f"角色数: {len(script.get('characters', []))}\n"
        f"集数: {len(script.get('episodes', []))}",
        border_style="cyan"
    ))

    try:
        engine = TTSEngine(cfg)
        audio_data = engine.generate_full_audio(script, output_dir)

        if project:
            proj = ProjectManager.get_project(project)
            proj.update_status("audio_done")

        console.print(f"\n[green]✅ 语音合成完成！输出目录: {output_dir}[/green]")
    except RuntimeError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)


# ============================================================
# video - 视频生成
# ============================================================

@app.command()
def video(
    project: str = typer.Option("", "--project", "-p", help="项目名"),
    script_file: str = typer.Option("", "--script", "-s", help="剧本 JSON 文件路径"),
    audio_dir: str = typer.Option("", "--audio", "-a", help="音频目录"),
    merge: bool = typer.Option(False, "--merge", "-m", help="合并所有场景为完整视频"),
):
    """🎥 将剧本和语音合成视频"""
    cfg = DramaConfig.get_or_create()

    # 加载剧本
    script = _load_script_from_project_or_file(project, script_file)
    if not script:
        raise typer.Exit(1)

    # 确定路径
    if project:
        proj = ProjectManager.get_project(project)
        base_dir = proj.path
        video_dir = proj.video_dir
        audio_dir = proj.audio_dir if not audio_dir else Path(audio_dir)
    else:
        base_dir = Path(script_file).parent if script_file else Path.cwd() / "drama_output"
        video_dir = base_dir / "video"
        audio_dir = base_dir / "audio" if not audio_dir else Path(audio_dir)

    if not audio_dir.exists():
        console.print(f"[red]✗ 音频目录不存在: {audio_dir}[/red]")
        console.print("[dim]请先运行: drama tts[/dim]")
        raise typer.Exit(1)

    console.print(Panel.fit(
        f"[bold cyan]🎥 开始视频生成[/bold cyan]\n"
        f"分辨率: {cfg.video_width}x{cfg.video_height}\n"
        f"帧率: {cfg.video_fps} fps",
        border_style="cyan"
    ))

    # 构建 audio_data 结构
    audio_data = _build_audio_data(audio_dir, script)

    try:
        gen = VideoGenerator(cfg)
        video_files = gen.generate_full_video(script, audio_data, video_dir)

        # 合并
        if merge and video_files:
            final_path = video_dir / "final_drama.mp4"
            gen.merge_episodes(video_files, final_path)
            console.print(f"\n[bold green]🎉 完整视频已生成: {final_path}[/bold green]")

        if project:
            proj = ProjectManager.get_project(project)
            proj.update_status("video_done")

        console.print(f"\n[green]✅ 视频生成完成！共 {len(video_files)} 个场景[/green]")
        console.print(f"[dim]输出目录: {video_dir}[/dim]")

    except RuntimeError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)


# ============================================================
# play - 一键生成
# ============================================================

@app.command()
def play(
    topic: str = typer.Argument("", help="短剧主题"),
    genre: str = typer.Option("", "--genre", "-g", help="短剧类型"),
    episodes: int = typer.Option(0, "--episodes", "-e", help="集数"),
    style: str = typer.Option("爽文", "--style", "-s", help="创作风格"),
    skip_tts: bool = typer.Option(False, "--skip-tts", help="跳过语音合成"),
    skip_video: bool = typer.Option(False, "--skip-video", help="跳过视频生成"),
):
    """🚀 一键生成完整短剧（剧本 + 语音 + 视频）"""
    cfg = DramaConfig.get_or_create()

    if not cfg.ai_api_key:
        console.print(
            "[red]✗ 请先配置 AI API Key:[/red]\n"
            "  [cyan]drama config set-ai --key YOUR_API_KEY[/cyan]"
        )
        raise typer.Exit(1)

    if not topic:
        topic = typer.prompt("请输入短剧主题")

    project_name = topic.replace(" ", "_")[:20]

    console.print(Panel.fit(
        f"[bold magenta]🚀 一键生成短剧[/bold magenta]\n\n"
        f"主题: {topic}\n"
        f"类型: {genre or cfg.default_genre}\n"
        f"集数: {episodes or cfg.default_episodes}\n"
        f"风格: {style}\n"
        f"跳过语音: {skip_tts}\n"
        f"跳过视频: {skip_video}",
        border_style="magenta",
        title="🎬 DramaCLI"
    ))

    # Step 1: 创建项目 + 生成剧本
    console.print("\n[bold cyan]━━━ Step 1/3: 生成剧本 ━━━[/bold cyan]\n")

    try:
        project = ProjectManager.create_project(project_name, genre, topic)
    except ValueError:
        # 项目已存在，使用现有项目
        project = ProjectManager.get_project(project_name)

    generator = ScriptGenerator(cfg)
    script = generator.generate(
        topic=topic, genre=genre, episodes=episodes, style=style
    )
    generator.save(script, project.path)
    project.update_status(
        "scripted",
        title=script.get("title", ""),
        episodes=len(script.get("episodes", [])),
        genre=script.get("genre", "")
    )

    _show_script_summary(script)

    if skip_tts and skip_video:
        console.print("\n[green]✅ 剧本生成完成！[/green]")
        return

    # Step 2: 语音合成
    if not skip_tts:
        console.print("\n[bold cyan]━━━ Step 2/3: 语音合成 ━━━[/bold cyan]\n")
        try:
            engine = TTSEngine(cfg)
            audio_data = engine.generate_full_audio(script, project.audio_dir)
            project.update_status("audio_done")
            console.print(f"[green]✅ 语音合成完成！[/green]")
        except RuntimeError as e:
            console.print(f"[yellow]⚠ 语音合成失败 (非致命): {e}[/yellow]")
            console.print("[dim]继续生成视频...[/dim]")
            skip_video = True  # 无音频无法生成视频

    if skip_video:
        return

    # Step 3: 视频生成
    console.print("\n[bold cyan]━━━ Step 3/3: 视频生成 ━━━[/bold cyan]\n")
    try:
        audio_data = _build_audio_data(project.audio_dir, script)
        gen = VideoGenerator(cfg)
        video_files = gen.generate_full_video(script, audio_data, project.video_dir)

        final_path = project.video_dir / "final_drama.mp4"
        gen.merge_episodes(video_files, final_path)
        project.update_status("video_done")

        console.print(Panel.fit(
            f"[bold green]🎉 短剧生成完成！[/bold green]\n\n"
            f"[cyan]剧名:[/cyan] {script.get('title', '')}\n"
            f"[cyan]集数:[/cyan] {len(script.get('episodes', []))}\n"
            f"[cyan]视频:[/cyan] {final_path}\n"
            f"[cyan]项目:[/cyan] {project.path}\n\n"
            f"[dim]播放: 用视频播放器打开 {final_path}[/dim]",
            border_style="green",
            title="🎬 完成"
        ))
    except RuntimeError as e:
        console.print(f"[red]✗ 视频生成失败: {e}[/red]")


# ============================================================
# list - 列出项目
# ============================================================

@app.command("list")
def list_projects():
    """📋 列出所有短剧项目"""
    ProjectManager.show_projects()


# ============================================================
# info - 查看项目详情
# ============================================================

@app.command()
def info(
    name: str = typer.Argument("", help="项目名"),
):
    """📊 查看项目详情"""
    if not name:
        projects = ProjectManager.list_projects()
        if not projects:
            console.print("[yellow]没有项目[/yellow]")
            return
        name = projects[0].name

    project = ProjectManager.get_project(name)
    if not project:
        console.print(f"[red]✗ 项目 '{name}' 不存在[/red]")
        raise typer.Exit(1)

    console.print(Panel(project.info(), title=f"📊 项目: {name}", border_style="cyan"))

    # 显示剧本信息
    script = project.script
    if script:
        _show_script_summary(script)


# ============================================================
# config 子命令
# ============================================================

@config_app.command("show")
def config_show():
    """查看当前配置"""
    cfg = DramaConfig.get_or_create()
    table = Table(title="⚙ 当前配置", border_style="blue")
    table.add_column("配置项", style="cyan")
    table.add_column("值", style="green")

    table.add_row("AI 提供商", cfg.ai_provider)
    table.add_row("AI 模型", cfg.ai_model)
    table.add_row("API Base URL", cfg.ai_base_url)
    table.add_row("API Key", "***" + cfg.ai_api_key[-4:] if cfg.ai_api_key else "未设置")
    table.add_row("TTS 引擎", cfg.tts_engine)
    table.add_row("TTS 语音", cfg.tts_voice)
    table.add_row("视频分辨率", f"{cfg.video_width}x{cfg.video_height}")
    table.add_row("默认类型", cfg.default_genre)
    table.add_row("默认集数", str(cfg.default_episodes))

    console.print(table)


@config_app.command("set-ai")
def config_set_ai(
    key: str = typer.Option("", "--key", "-k", help="API Key"),
    base_url: str = typer.Option("", "--base-url", "-b", help="API Base URL"),
    model: str = typer.Option("", "--model", "-m", help="模型名称"),
    provider: str = typer.Option("", "--provider", "-p", help="提供商"),
):
    """配置 AI 参数"""
    cfg = DramaConfig.get_or_create()

    changes = []
    if key:
        cfg.ai_api_key = key
        changes.append("API Key")
    if base_url:
        cfg.ai_base_url = base_url
        changes.append("Base URL")
    if model:
        cfg.ai_model = model
        changes.append("模型")
    if provider:
        cfg.ai_provider = provider
        changes.append("提供商")

    if not changes:
        console.print("[yellow]未指定任何配置项[/yellow]")
        return

    cfg.save()
    console.print(f"[green]✅ 已更新: {', '.join(changes)}[/green]")


@config_app.command("set-tts")
def config_set_tts(
    voice: str = typer.Option("", "--voice", "-v", help="TTS 语音"),
    engine: str = typer.Option("", "--engine", "-e", help="TTS 引擎"),
):
    """配置 TTS 参数"""
    cfg = DramaConfig.get_or_create()

    changes = []
    if voice:
        cfg.tts_voice = voice
        changes.append("语音")
    if engine:
        cfg.tts_engine = engine
        changes.append("引擎")

    if not changes:
        console.print("[yellow]未指定任何配置项[/yellow]")
        return

    cfg.save()
    console.print(f"[green]✅ 已更新: {', '.join(changes)}[/green]")


# ============================================================
# 辅助函数
# ============================================================

def _show_banner():
    """显示 Banner"""
    banner = r"""
    [bold cyan]
    ╔══════════════════════════════════════════╗
    ║  🎬  DramaCLI - AI 短剧自动生成工具    ║
    ║        v{version}                          ║
    ╚══════════════════════════════════════════╝
    [/bold cyan]
    """.format(version=__version__)
    console.print(banner)


def _show_quickstart():
    """显示快速开始"""
    quickstart = """
[bold]🚀 快速开始:[/bold]

  [cyan]1.[/cyan] 配置 API Key:
     [bold]drama config set-ai --key YOUR_OPENAI_KEY[/bold]

  [cyan]2.[/cyan] 一键生成短剧:
     [bold]drama play "霸道总裁爱上我"[/bold]

  [cyan]3.[/cyan] 分步操作:
     [bold]drama init my_drama[/bold]
     [bold]drama generate "主题" -p my_drama[/bold]
     [bold]drama tts -p my_drama[/bold]
     [bold]drama video -p my_drama --merge[/bold]

[bold]📖 更多命令: drama --help[/bold]
"""
    console.print(quickstart)


def _show_script_summary(script: dict):
    """显示剧本摘要"""
    console.print(Panel.fit(
        f"[bold yellow]📜 {script.get('title', '未命名')}[/bold yellow]\n\n"
        f"类型: {script.get('genre', '')}\n"
        f"简介: {script.get('description', '')}\n"
        f"角色: {len(script.get('characters', []))} 人\n"
        f"集数: {len(script.get('episodes', []))} 集",
        border_style="yellow"
    ))

    # 角色列表
    table = Table(title="👥 角色列表", border_style="dim")
    table.add_column("角色", style="cyan")
    table.add_column("身份", style="green")
    table.add_column("性格", style="yellow")
    table.add_column("配音风格", style="magenta")

    for char in script.get("characters", []):
        table.add_row(
            char.get("name", ""),
            char.get("role", ""),
            char.get("personality", ""),
            char.get("voice_style", "")
        )
    console.print(table)


def _load_script_from_project_or_file(project: str, script_file: str) -> dict:
    """从项目或文件加载剧本"""
    import json

    if project:
        proj = ProjectManager.get_project(project)
        if not proj:
            console.print(f"[red]✗ 项目 '{project}' 不存在[/red]")
            return None
        script = proj.script
        if not script:
            console.print(f"[red]✗ 项目 '{project}' 中没有剧本，请先运行 drama generate[/red]")
            return None
        return script

    if script_file:
        path = Path(script_file)
        if not path.exists():
            console.print(f"[red]✗ 剧本文件不存在: {script_file}[/red]")
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    console.print("[red]✗ 请指定项目名 (--project) 或剧本文件 (--script)[/red]")
    return None


def _build_audio_data(audio_dir: Path, script: dict) -> dict:
    """从音频目录构建 audio_data 结构"""
    import json
    result = {"episodes": []}

    for ep in script.get("episodes", []):
        ep_num = ep["episode_number"]
        ep_dir = audio_dir / f"episode_{ep_num:02d}"
        episode_data = {"episode_number": ep_num, "scenes": []}

        for scene in ep.get("scenes", []):
            scene_num = scene["scene_number"]
            scene_dir = ep_dir / f"scene_{scene_num:02d}"

            audio_files = []
            if scene_dir.exists():
                for f in sorted(scene_dir.glob("line_*.mp3")):
                    audio_files.append(str(f))

            episode_data["scenes"].append({
                "scene_number": scene_num,
                "audio_files": audio_files,
                "scene_dir": str(scene_dir)
            })

        result["episodes"].append(episode_data)

    return result


# ============================================================
# douyin - 抖音专业版命令
# ============================================================

douyin_app = typer.Typer(help="🎬 抖音短剧专业版", rich_markup_mode="rich")
app.add_typer(douyin_app, name="douyin")


@douyin_app.command("web")
def douyin_web(
    port: int = typer.Option(8888, "--port", "-p", help="Web服务端口"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="绑定地址"),
):
    """🌐 启动Web管理后台"""
    from .douyin.web_server import start_server
    start_server(host=host, port=port)


@douyin_app.command("templates")
def douyin_templates():
    """📋 列出所有抖音短剧模板"""
    from .douyin.templates import list_templates, get_template
    from rich.table import Table

    table = Table(title="🎭 抖音短剧模板", border_style="cyan")
    table.add_column("模板名", style="gold1")
    table.add_column("类型", style="green")
    table.add_column("风格", style="yellow")
    table.add_column("视觉", style="magenta")
    table.add_column("BGM", style="blue")
    table.add_column("简介", style="dim")

    for name in list_templates():
        t = get_template(name)
        table.add_row(t.name, t.genre, t.style, t.visual_style, t.bgm_mood, t.description[:30])

    console.print(table)


@douyin_app.command("produce")
def douyin_produce(
    script_file: str = typer.Argument("demo_script.json", help="剧本 JSON 文件"),
    output: str = typer.Option("douyin_output", "--output", "-o", help="输出目录"),
    mode: str = typer.Option("pro", "--mode", help="pro/fast，Pro 优先使用高质量 AI"),
    video_engine: str = typer.Option("auto", "--video-engine", help="auto/sora/ken-burns"),
    video_model: str = typer.Option("sora-2-pro", "--video-model", help="云端视频模型"),
):
    """🎬 一键生成抖音短剧 - 零参数，智能全自动"""
    import json
    from pathlib import Path
    from .douyin.pipeline import DouyinPipeline, PipelineConfig
    from .douyin.templates import get_template, list_templates

    mode = mode.lower()
    video_engine = video_engine.lower()
    if mode not in {"pro", "fast"}:
        console.print("[red]--mode 仅支持 pro 或 fast[/red]")
        raise typer.Exit(2)
    if video_engine not in {"auto", "sora", "ken-burns"}:
        console.print("[red]--video-engine 仅支持 auto、sora 或 ken-burns[/red]")
        raise typer.Exit(2)

    script_path = Path(script_file)
    if not script_path.exists():
        console.print(f"[red]✗ 剧本不存在: {script_file}[/red]")
        raise typer.Exit(1)

    script = json.loads(script_path.read_text(encoding="utf-8"))
    genre = script.get("genre", "")

    # 智能匹配模板
    template_name = "霸道总裁"
    template_map = {
        "都市": "霸道总裁", "古装": "穿越王妃", "穿越": "穿越王妃",
        "复仇": "重生复仇", "重生": "重生复仇", "豪门": "豪门千金",
        "悬疑": "悬疑惊悚", "推理": "悬疑惊悚", "校园": "校园甜宠",
        "战神": "战神归来", "娱乐圈": "娱乐圈", "末日": "末日求生",
        "修仙": "玄幻修仙", "玄幻": "玄幻修仙",
    }
    for key, val in template_map.items():
        if key in genre:
            template_name = val
            break

    global_cfg = DramaConfig.load()
    api_key = os.getenv("OPENAI_API_KEY", global_cfg.ai_api_key)
    selected_video = video_model if mode == "pro" and api_key and video_engine != "ken-burns" else "电影感本地运镜"

    console.print(Panel.fit(
        f"[bold magenta]🎬 DramaCLI Pro[/bold magenta]\n"
        f"剧名: {script.get('title', '')}\n"
        f"类型: {genre} → 模板: {template_name}\n"
        f"集数: {len(script.get('episodes', []))}\n"
        f"模式: {mode} | 视频: {selected_video}\n"
        f"特效: 爆款钩子/BGM/调色/片头片尾/转场",
        border_style="magenta"
    ))

    cfg = PipelineConfig(
        project_name=script.get("title", "短剧")[:20],
        template_name=template_name,
        topic=script.get("title", ""),
        episodes=len(script.get("episodes", [])),
        mode=mode,
        ai_api_key=api_key,
        ai_base_url=global_cfg.ai_base_url,
        ai_model=global_cfg.ai_model,
        video_engine=video_engine,
        video_model=video_model,
        tts_engine=global_cfg.tts_engine,
        tts_model=global_cfg.tts_model,
        tts_voice=global_cfg.tts_voice,
        tts_speed=global_cfg.tts_speed,
        output_dir=Path(output) / script.get("title", "drama")[:20],
    )

    pipeline = DouyinPipeline(cfg)
    pipeline.set_script(script)

    final_path = pipeline.run()
    pkg = pipeline.export_douyin_package()

    console.print(Panel.fit(
        f"[bold green]🎉 完成![/bold green]\n"
        f"视频: {final_path}\n"
        f"封面: {cfg.output_dir / 'cover.png'}\n"
        f"标签: {' '.join(pkg.get('tags', []))}",
        border_style="green"
    ))


def main():
    app()


if __name__ == "__main__":
    main()
