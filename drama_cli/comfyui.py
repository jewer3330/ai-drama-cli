"""ComfyUI integration commands for AI short-drama production."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console(safe_box=True)
comfyui_app = typer.Typer(
    help="ComfyUI plugin stack for professional AI short-drama pipelines",
    rich_markup_mode="rich",
)


@dataclass(frozen=True)
class ComfyPlugin:
    slug: str
    name: str
    repo: str
    category: str
    profile: tuple[str, ...]
    why: str
    notes: str = ""
    models: tuple[str, ...] = field(default_factory=tuple)


PLUGIN_STACK: tuple[ComfyPlugin, ...] = (
    ComfyPlugin(
        slug="manager",
        name="ComfyUI Manager",
        repo="https://github.com/Comfy-Org/ComfyUI-Manager",
        category="ops",
        profile=("core", "pro", "all"),
        why="Install, update, disable, and repair custom nodes from inside ComfyUI.",
        notes="Install this first. It is the safest long-term plugin management path.",
    ),
    ComfyPlugin(
        slug="impact-pack",
        name="ComfyUI Impact Pack",
        repo="https://github.com/ltdrdata/ComfyUI-Impact-Pack",
        category="image",
        profile=("core", "image", "pro", "all"),
        why="Detector, detailer, upscaler, pipe helpers, and face/detail polish.",
        notes="Great for poster covers, close-ups, and fixing key character shots.",
    ),
    ComfyPlugin(
        slug="controlnet-aux",
        name="ControlNet Auxiliary Preprocessors",
        repo="https://github.com/Fannovel16/comfyui_controlnet_aux",
        category="image",
        profile=("core", "image", "pro", "all"),
        why="Pose, depth, lineart, and edge preprocessors for directed scenes.",
        notes="Use for shot blocking, actor pose control, and repeatable scene layouts.",
    ),
    ComfyPlugin(
        slug="ipadapter-plus",
        name="ComfyUI IPAdapter Plus",
        repo="https://github.com/cubiq/ComfyUI_IPAdapter_plus",
        category="identity",
        profile=("core", "image", "pro", "all"),
        why="Reference-image conditioning for character identity and visual style.",
        notes="Repository is maintenance-only, but still valuable for SDXL identity workflows.",
        models=(
            "models/clip_vision",
            "models/ipadapter",
        ),
    ),
    ComfyPlugin(
        slug="video-helper-suite",
        name="Video Helper Suite",
        repo="https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite",
        category="video",
        profile=("video", "pro", "all"),
        why="Load, batch, combine, preview, and export image sequences as video.",
        notes="The backbone for image-sequence based drama rendering.",
    ),
    ComfyPlugin(
        slug="animatediff-evolved",
        name="AnimateDiff Evolved",
        repo="https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved",
        category="video",
        profile=("video", "pro", "all"),
        why="Advanced AnimateDiff motion workflows and sampling support.",
        notes="Use for stylized short motion, teaser loops, and low-cost scene movement.",
    ),
    ComfyPlugin(
        slug="wan-video-wrapper",
        name="WanVideoWrapper",
        repo="https://github.com/kijai/ComfyUI-WanVideoWrapper",
        category="video",
        profile=("video", "pro", "all"),
        why="Wan video generation wrapper for higher-end image/video-to-video scenes.",
        notes="GPU and model requirements are heavier; keep it in the pro profile.",
    ),
    ComfyPlugin(
        slug="frame-interpolation",
        name="Frame Interpolation",
        repo="https://github.com/Fannovel16/ComfyUI-Frame-Interpolation",
        category="video",
        profile=("video", "pro", "all"),
        why="RIFE, FILM, AMT, and related VFI nodes for smoother final shots.",
        notes="Useful after AnimateDiff or Wan output, especially for vertical drama exports.",
    ),
    ComfyPlugin(
        slug="ultimate-sd-upscale",
        name="Ultimate SD Upscale",
        repo="https://github.com/ssitu/ComfyUI_UltimateSDUpscale",
        category="finish",
        profile=("image", "pro", "all"),
        why="Tile-based upscale for posters, covers, and hero frames.",
        notes="Pair with Impact Pack detailers for final delivery frames.",
    ),
    ComfyPlugin(
        slug="custom-scripts",
        name="ComfyUI Custom Scripts",
        repo="https://github.com/pythongosssss/ComfyUI-Custom-Scripts",
        category="ux",
        profile=("pro", "all"),
        why="Workflow UI improvements for faster daily production.",
        notes="Quality-of-life plugin, not required for render correctness.",
    ),
    ComfyPlugin(
        slug="was-node-suite",
        name="WAS Node Suite",
        repo="https://github.com/WASasquatch/was-node-suite-comfyui",
        category="utility",
        profile=("pro", "all"),
        why="Large utility node set for text, image, mask, and file operations.",
        notes="Powerful but broad; install after the core stack is stable.",
    ),
)


BLUEPRINT = {
    "name": "ai_short_drama_comfyui_pro_pipeline",
    "version": "1.0",
    "target": "9:16 short drama production",
    "stages": [
        {
            "stage": "character_bible",
            "goal": "Lock hero, heroine, antagonist, and supporting-role identity.",
            "plugins": ["ComfyUI IPAdapter Plus", "ComfyUI Impact Pack"],
            "outputs": ["character reference portraits", "face detail pass"],
        },
        {
            "stage": "shot_design",
            "goal": "Convert script scenes into controlled vertical compositions.",
            "plugins": ["ControlNet Auxiliary Preprocessors"],
            "outputs": ["pose/depth/lineart controls", "scene prompt pack"],
        },
        {
            "stage": "scene_generation",
            "goal": "Generate consistent keyframes for every episode scene.",
            "plugins": ["ComfyUI Impact Pack", "Ultimate SD Upscale"],
            "outputs": ["cover frame", "scene keyframes", "detail/upscale variants"],
        },
        {
            "stage": "motion",
            "goal": "Animate keyframes into short scene clips.",
            "plugins": ["AnimateDiff Evolved", "WanVideoWrapper", "Video Helper Suite"],
            "outputs": ["raw video clips", "image sequences"],
        },
        {
            "stage": "finishing",
            "goal": "Smooth, assemble, upscale, and export platform-ready vertical video.",
            "plugins": ["Frame Interpolation", "Video Helper Suite"],
            "outputs": ["24/30/60 fps scene clips", "final mp4 assets"],
        },
    ],
    "negative_prompt": (
        "low quality, bad anatomy, inconsistent face, extra fingers, distorted hands, "
        "watermark, text artifacts, logo, blurry, overexposed, underexposed"
    ),
    "prompt_template": (
        "{character}, {scene_action}, vertical 9:16 cinematic short drama frame, "
        "{genre} tone, consistent face, expressive acting, realistic lighting, "
        "film still, high detail, commercial drama poster quality"
    ),
}


def _plugins_for_profile(profile: str) -> list[ComfyPlugin]:
    return [plugin for plugin in PLUGIN_STACK if profile in plugin.profile]


def _repo_dir_name(repo: str) -> str:
    return repo.rstrip("/").split("/")[-1].replace(".git", "")


def _custom_nodes_dir(comfyui_path: Path) -> Path:
    if comfyui_path.name == "custom_nodes":
        return comfyui_path
    app_custom_nodes = comfyui_path / "app" / "custom_nodes"
    if app_custom_nodes.exists():
        return app_custom_nodes
    nested = comfyui_path / "ComfyUI" / "custom_nodes"
    if nested.exists():
        return nested
    return comfyui_path / "custom_nodes"


def _comfyui_root(comfyui_path: Path) -> Path:
    if comfyui_path.name == "custom_nodes":
        return comfyui_path.parent
    if (comfyui_path / "main.py").exists() and (comfyui_path / "comfy").exists():
        return comfyui_path
    if (comfyui_path / "app" / "main.py").exists():
        return comfyui_path / "app"
    if (comfyui_path / "ComfyUI" / "main.py").exists():
        return comfyui_path / "ComfyUI"
    return comfyui_path


def _model_root(comfyui_path: Path) -> Path:
    shared = comfyui_path / "models"
    if shared.exists():
        return shared
    parent_shared = comfyui_path.parent / "models"
    if comfyui_path.name == "app" and parent_shared.exists():
        return parent_shared
    return _comfyui_root(comfyui_path) / "models"


def _iter_target_plugins(profile: str, only: Optional[str]) -> Iterable[ComfyPlugin]:
    plugins = PLUGIN_STACK if profile == "all" else _plugins_for_profile(profile)
    if only:
        wanted = {item.strip() for item in only.split(",") if item.strip()}
        plugins = [plugin for plugin in plugins if plugin.slug in wanted or plugin.name in wanted]
    return plugins


def _model_files(comfyui_path: Path) -> dict[str, list[Path]]:
    model_root = _model_root(comfyui_path)
    buckets = {
        "checkpoints": [],
        "loras": [],
        "vae": [],
        "controlnet": [],
        "clip_vision": [],
        "ipadapter": [],
        "animatediff_models": [],
        "diffusion_models": [],
    }
    suffixes = {".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf"}

    for name in buckets:
        folder = model_root / name
        if folder.exists():
            buckets[name] = [
                item
                for item in folder.rglob("*")
                if item.is_file() and item.suffix.lower() in suffixes
            ]
    return buckets


@comfyui_app.command("list")
def list_plugins(
    profile: str = typer.Option("pro", "--profile", "-p", help="core/image/video/pro/all"),
):
    """Show the curated ComfyUI plugin stack."""
    plugins = list(_iter_target_plugins(profile, None))
    if not plugins:
        console.print(f"[red]Unknown profile:[/red] {profile}")
        raise typer.Exit(1)

    table = Table(
        title=f"ComfyUI short-drama plugin stack: {profile}",
        border_style="cyan",
        expand=True,
    )
    table.add_column("Slug", style="cyan", no_wrap=True)
    table.add_column("Type", style="green", no_wrap=True)
    table.add_column("Plugin", style="bold", overflow="fold")
    table.add_column("Production role", overflow="fold")

    for plugin in plugins:
        table.add_row(plugin.slug, plugin.category, plugin.name, plugin.why)

    console.print(table)
    console.print(
        Panel.fit(
            "Recommended path: install Manager first, then install the profile through "
            "Manager or run `drama comfyui install --path <ComfyUI>`.",
            title="Production advice",
            border_style="green",
        )
    )


@comfyui_app.command("manifest")
def write_manifest(
    output: Path = typer.Option("comfyui_short_drama_plugins.json", "--output", "-o"),
):
    """Write the curated plugin manifest to JSON."""
    payload = {
        "name": "DramaCLI ComfyUI Short-Drama Plugin Stack",
        "profiles": ["core", "image", "video", "pro", "all"],
        "plugins": [asdict(plugin) for plugin in PLUGIN_STACK],
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"[green]Manifest written:[/green] {output}")


@comfyui_app.command("doctor")
def doctor(
    path: Path = typer.Option(..., "--path", "-p", help="ComfyUI root or custom_nodes path"),
    profile: str = typer.Option("pro", "--profile", help="core/image/video/pro/all"),
):
    """Check ComfyUI custom node installation status."""
    custom_nodes = _custom_nodes_dir(path)
    table = Table(title="ComfyUI doctor", border_style="blue")
    table.add_column("Check", style="cyan")
    table.add_column("Result")

    git_path = shutil.which("git")
    table.add_row("Git", git_path or "[red]missing[/red]")
    table.add_row("custom_nodes", str(custom_nodes) if custom_nodes.exists() else "[red]missing[/red]")
    model_counts = _model_files(path)
    local_model_count = sum(len(items) for items in model_counts.values())
    table.add_row("local models", f"{local_model_count} files detected")

    for plugin in _iter_target_plugins(profile, None):
        target = custom_nodes / _repo_dir_name(plugin.repo)
        alt_target = custom_nodes / plugin.slug
        installed = target.exists() or alt_target.exists()
        table.add_row(plugin.slug, "[green]installed[/green]" if installed else "[yellow]not installed[/yellow]")

    console.print(table)
    if not custom_nodes.exists():
        console.print("[yellow]Tip:[/yellow] pass the ComfyUI root folder, not this DramaCLI project folder.")


@comfyui_app.command("models")
def models(
    path: Path = typer.Option(..., "--path", "-p", help="ComfyUI root path"),
    limit: int = typer.Option(5, "--limit", "-n", help="Files to show per model folder"),
):
    """Inspect local ComfyUI model folders."""
    buckets = _model_files(path)
    table = Table(title="ComfyUI local model inventory", border_style="magenta", expand=True)
    table.add_column("Folder", style="cyan", no_wrap=True)
    table.add_column("Count", style="green", justify="right")
    table.add_column("Examples", overflow="fold")

    for folder, files in buckets.items():
        examples = "\n".join(file.name for file in files[:limit]) if files else "-"
        table.add_row(folder, str(len(files)), examples)

    console.print(table)
    total = sum(len(files) for files in buckets.values())
    if total:
        console.print("[green]Local ComfyUI models detected.[/green]")
    else:
        console.print(
            "[yellow]No local model files found in this ComfyUI path.[/yellow] "
            "Put checkpoints, LoRAs, ControlNet, IPAdapter, and video models under ComfyUI/models."
        )


@comfyui_app.command("install")
def install_plugins(
    path: Path = typer.Option(..., "--path", "-p", help="ComfyUI root or custom_nodes path"),
    profile: str = typer.Option("pro", "--profile", help="core/image/video/pro/all"),
    only: Optional[str] = typer.Option(None, "--only", help="Comma-separated plugin slugs"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print git commands without running them"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clone selected plugins into ComfyUI/custom_nodes."""
    custom_nodes = _custom_nodes_dir(path)
    plugins = list(_iter_target_plugins(profile, only))

    if not plugins:
        console.print("[red]No plugins selected.[/red]")
        raise typer.Exit(1)
    if not dry_run and not shutil.which("git"):
        console.print("[red]Git is required to install ComfyUI plugins.[/red]")
        raise typer.Exit(1)
    if not dry_run:
        custom_nodes.mkdir(parents=True, exist_ok=True)

    console.print(
        Panel.fit(
            f"Target: {custom_nodes}\nProfile: {profile}\nPlugins: {len(plugins)}",
            title="ComfyUI install plan",
            border_style="cyan",
        )
    )

    if not yes and not dry_run:
        typer.confirm("Clone these third-party repositories into ComfyUI?", abort=True)

    for plugin in plugins:
        target = custom_nodes / _repo_dir_name(plugin.repo)
        if target.exists():
            console.print(f"[green]Already installed:[/green] {plugin.name} -> {target}")
            continue

        cmd = ["git", "clone", "--depth", "1", "--single-branch", plugin.repo, str(target)]
        if dry_run:
            console.print("[cyan]DRY RUN[/cyan] " + " ".join(cmd))
            continue

        console.print(f"[cyan]Installing[/cyan] {plugin.name}")
        result = subprocess.run(cmd, cwd=str(custom_nodes), text=True, capture_output=True)
        if result.returncode != 0:
            console.print(f"[red]Failed:[/red] {plugin.name}")
            console.print(result.stderr.strip() or result.stdout.strip())
        else:
            console.print(f"[green]Installed:[/green] {target}")

    console.print(
        Panel.fit(
            "Restart ComfyUI after install. For dependency issues, use ComfyUI Manager "
            "or install each plugin's requirements with the Python runtime that runs ComfyUI.",
            title="Next step",
            border_style="green",
        )
    )


@comfyui_app.command("blueprint")
def write_blueprint(
    output: Path = typer.Option("comfyui_short_drama_blueprint.json", "--output", "-o"),
):
    """Write a production blueprint for a ComfyUI short-drama workflow."""
    output.write_text(json.dumps(BLUEPRINT, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"[green]Blueprint written:[/green] {output}")
    console.print(
        Panel.fit(
            "Use this as the shot-design contract between DramaCLI script generation "
            "and ComfyUI visual production.",
            title="Short-drama workflow",
            border_style="magenta",
        )
    )
