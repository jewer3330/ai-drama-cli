"""Anime short-drama commands backed by local ComfyUI."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console(safe_box=True)
anime_app = typer.Typer(
    help="Generate local ComfyUI anime short-drama keyframes and motion cuts",
    rich_markup_mode="rich",
)


@dataclass(frozen=True)
class AnimeStyle:
    slug: str
    title: str
    prompt_tags: str
    color_grade: str
    story_hook: str


STYLES: dict[str, AnimeStyle] = {
    "rainy": AnimeStyle(
        slug="rainy",
        title="Rainy Tokyo Drama",
        prompt_tags=(
            "japanese anime drama, rainy tokyo night, wet asphalt reflections, "
            "cinematic lighting, emotional suspense, clean line art"
        ),
        color_grade="eq=contrast=1.08:saturation=1.10",
        story_hook="A future message arrives before midnight.",
    ),
    "cyberpunk": AnimeStyle(
        slug="cyberpunk",
        title="Cyberpunk Neon",
        prompt_tags=(
            "cyberpunk anime, neon tokyo, holograms, rain, high contrast, "
            "glowing signs, futuristic street, cinematic sci-fi mood"
        ),
        color_grade="eq=contrast=1.18:saturation=1.28",
        story_hook="A stolen memory chip predicts the heroine's disappearance.",
    ),
    "xianxia": AnimeStyle(
        slug="xianxia",
        title="Xianxia Anime",
        prompt_tags=(
            "chinese anime style, xianxia, hanfu, moonlit mountains, floating petals, "
            "ink wash atmosphere, spiritual light, elegant fantasy"
        ),
        color_grade="eq=contrast=1.06:saturation=1.18",
        story_hook="A forbidden vow awakens an ancient sword spirit.",
    ),
    "shoujo": AnimeStyle(
        slug="shoujo",
        title="Shoujo Romance",
        prompt_tags=(
            "shoujo anime, pastel colors, soft lighting, cherry blossoms, gentle romance, "
            "sparkling highlights, delicate expression"
        ),
        color_grade="eq=contrast=1.03:saturation=1.16",
        story_hook="A confession letter appears every day, always signed tomorrow.",
    ),
    "dark": AnimeStyle(
        slug="dark",
        title="Dark Mystery",
        prompt_tags=(
            "dark fantasy anime, gothic school, candlelight, mist, dramatic shadows, "
            "supernatural mystery, ominous atmosphere"
        ),
        color_grade="eq=contrast=1.20:saturation=0.95",
        story_hook="At midnight, every mirror shows a different ending.",
    ),
}


NEGATIVE_PROMPT = (
    "low quality, worst quality, blurry, bad anatomy, bad hands, extra fingers, "
    "missing fingers, watermark, logo, text, jpeg artifacts, deformed face, "
    "cropped head, poorly drawn eyes"
)


DEFAULT_SCENES = (
    {
        "prefix": "anime_drama_ep01_sc01",
        "title": "Signal",
        "subtitle": "雨夜，澪收到一封来自未来的短信。",
        "action": (
            "Hoshino Mio, black long hair, blue eyes, black sailor uniform, red ribbon, "
            "standing alone, holding a glowing smartphone, worried expression"
        ),
    },
    {
        "prefix": "anime_drama_ep01_sc02",
        "title": "Countdown",
        "subtitle": "零点倒计时开始，世界的记忆正在褪色。",
        "action": (
            "Hoshino Mio, black long hair, blue eyes, black sailor uniform, red ribbon, "
            "dramatic close-up, supernatural countdown light, memory fragments dissolving"
        ),
    },
    {
        "prefix": "anime_drama_ep01_sc03",
        "title": "Choice",
        "subtitle": "最后十秒，她握住那只手，改写结局。",
        "action": (
            "Hoshino Mio, black long hair, blue eyes, black sailor uniform, red ribbon, "
            "holding hands with mysterious silver hair boy in school blazer, emotional climax"
        ),
    },
)


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _workflow(
    *,
    scene: dict[str, str],
    style: AnimeStyle,
    checkpoint: str,
    width: int,
    height: int,
    steps: int,
    seed: int,
) -> dict[str, Any]:
    positive = (
        "masterpiece, best quality, vertical composition, anime short drama key visual, "
        f"{scene['action']}, {style.prompt_tags}, detailed background"
    )
    return {
        "client_id": "drama-cli-anime",
        "prompt": {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": 6.5,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": checkpoint},
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1},
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": positive, "clip": ["4", 1]},
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": NEGATIVE_PROMPT, "clip": ["4", 1]},
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": scene["prefix"], "images": ["8", 0]},
            },
        },
    }


def _write_subtitles(path: Path, scenes: tuple[dict[str, str], ...]) -> None:
    blocks = []
    for index, scene in enumerate(scenes, start=1):
        start = (index - 1) * 4
        end = index * 4
        blocks.append(
            f"{index}\n"
            f"00:00:{start:02d},000 --> 00:00:{end:02d},000\n"
            f"{scene['subtitle']}\n"
        )
    path.write_text("\n".join(blocks), encoding="utf-8")


def _render_motion(output_dir: Path, output_name: str, style: AnimeStyle) -> Path:
    if not shutil.which("ffmpeg.exe") and not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required to render the motion video.")

    output = output_dir / output_name
    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "zoompan=z='1+0.0008*on':x='iw/2-(iw/zoom/2)+12*sin(on/16)':"
        f"y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=25,{style.color_grade}[v0];"
        "[1:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "zoompan=z='1.04-0.0005*on':x='iw/2-(iw/zoom/2)-10*sin(on/14)':"
        f"y='ih/2-(ih/zoom/2)+8*sin(on/20)':d=1:s=1080x1920:fps=25,{style.color_grade}[v1];"
        "[2:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "zoompan=z='1+0.0007*on':x='iw/2-(iw/zoom/2)+18*sin(on/18)':"
        f"y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=25,{style.color_grade}[v2];"
        "[v0][v1]xfade=transition=fade:duration=0.35:offset=3.65[x1];"
        "[x1][v2]xfade=transition=smoothleft:duration=0.35:offset=7.30,"
        "format=yuv420p,subtitles=subtitles.srt:"
        "force_style='FontName=Microsoft YaHei,Fontsize=13,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=120'[v]"
    )
    cmd = [
        "ffmpeg.exe" if shutil.which("ffmpeg.exe") else "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-t",
        "4",
        "-i",
        "scene01.png",
        "-loop",
        "1",
        "-t",
        "4",
        "-i",
        "scene02.png",
        "-loop",
        "1",
        "-t",
        "4",
        "-i",
        "scene03.png",
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-r",
        "25",
        "-movflags",
        "+faststart",
        output.name,
    ]
    result = subprocess.run(cmd, cwd=output_dir, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return output


@anime_app.command("styles")
def list_styles():
    """List available anime short-drama styles."""
    table = Table(title="Anime styles", border_style="cyan", expand=True)
    table.add_column("Style", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Story hook")
    for style in STYLES.values():
        table.add_row(style.slug, style.title, style.story_hook)
    console.print(table)


@anime_app.command("make")
def make_anime_drama(
    style_name: str = typer.Option("rainy", "--style", "-s", help="rainy/cyberpunk/xianxia/shoujo/dark"),
    output: Path = typer.Option(Path("anime_drama_output"), "--output", "-o", help="Output folder"),
    server: str = typer.Option("http://127.0.0.1:8188", "--server", help="ComfyUI server URL"),
    comfy_output: Path = typer.Option(Path("D:/AI/ComfyUI/app/output"), "--comfy-output", help="ComfyUI output folder"),
    checkpoint: str = typer.Option("Counterfeit-V3.0_fix_fp16.safetensors", "--checkpoint", help="ComfyUI checkpoint"),
    width: int = typer.Option(384, "--width", help="Latent width"),
    height: int = typer.Option(640, "--height", help="Latent height"),
    steps: int = typer.Option(6, "--steps", help="Sampler steps"),
    seed: int = typer.Option(26070700, "--seed", help="Base seed"),
    render: bool = typer.Option(True, "--render/--no-render", help="Render motion MP4 after keyframes"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Only write story/workflow files"),
):
    """Generate three local ComfyUI anime keyframes and an optional motion cut."""
    style = STYLES.get(style_name)
    if not style:
        console.print(f"[red]Unknown style:[/red] {style_name}")
        console.print("Run [cyan]drama anime styles[/cyan] to see options.")
        raise typer.Exit(1)

    output.mkdir(parents=True, exist_ok=True)
    scenes = tuple(DEFAULT_SCENES)
    _write_subtitles(output / "subtitles.srt", scenes)
    story = {
        "title": f"{style.title} - Midnight Confession",
        "style": style.slug,
        "hook": style.story_hook,
        "checkpoint": checkpoint,
        "scenes": scenes,
    }
    (output / "story.json").write_text(json.dumps(story, indent=2, ensure_ascii=False), encoding="utf-8")

    console.print(
        Panel.fit(
            f"Style: {style.title}\nCheckpoint: {checkpoint}\nOutput: {output}",
            title="Anime drama plan",
            border_style="magenta",
        )
    )

    workflows = []
    for index, scene in enumerate(scenes, start=1):
        workflow = _workflow(
            scene=scene,
            style=style,
            checkpoint=checkpoint,
            width=width,
            height=height,
            steps=steps,
            seed=seed + index,
        )
        workflow_path = output / f"comfy_scene_{index:02d}.json"
        workflow_path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False), encoding="utf-8")
        workflows.append(workflow_path)

    if dry_run:
        console.print("[green]Wrote story and ComfyUI workflow files:[/green]")
        for workflow_path in workflows:
            console.print(f"  {workflow_path}")
        return

    try:
        _get_json(f"{server}/system_stats")
    except (URLError, TimeoutError, OSError) as exc:
        console.print(f"[red]Cannot reach ComfyUI:[/red] {server}")
        console.print(str(exc))
        raise typer.Exit(1)

    for index, scene in enumerate(scenes, start=1):
        workflow = json.loads((output / f"comfy_scene_{index:02d}.json").read_text(encoding="utf-8"))
        response = _post_json(f"{server}/prompt", workflow)
        prompt_id = response.get("prompt_id")
        if not prompt_id:
            console.print(f"[red]Failed to queue scene {index}[/red]")
            raise typer.Exit(1)
        console.print(f"[cyan]Queued scene {index}:[/cyan] {prompt_id}")

        while True:
            history = _get_json(f"{server}/history/{prompt_id}")
            if history:
                entry = next(iter(history.values()))
                images = entry.get("outputs", {}).get("9", {}).get("images", [])
                if images:
                    image = images[0]
                    source = comfy_output / image["filename"]
                    if not source.exists():
                        console.print(f"[red]Cannot find ComfyUI output:[/red] {source}")
                        raise typer.Exit(1)
                    dest = output / f"scene{index:02d}.png"
                    shutil.copy2(source, dest)
                    console.print(f"[green]Scene {index} ready:[/green] {dest}")
                    break
            time.sleep(5)

    if render:
        try:
            video = _render_motion(output, f"{style.slug}_anime_drama_motion.mp4", style)
            console.print(f"[bold green]Motion cut rendered:[/bold green] {video}")
        except RuntimeError as exc:
            console.print(f"[red]Render failed:[/red] {exc}")
            raise typer.Exit(1)

    console.print("[green]Anime drama package ready.[/green]")
