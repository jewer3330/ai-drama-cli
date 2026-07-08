# DramaCLI

Professional AI short-drama CLI for script generation, TTS, vertical video assembly,
Douyin-style packaging, and ComfyUI visual production.

## Quick Start

```powershell
pip install -e .
drama --help
```

Configure an AI provider:

```powershell
drama config set-ai --key YOUR_API_KEY --model gpt-4o
```

Generate a short drama:

```powershell
drama play "contract marriage revenge drama" --genre "urban" --episodes 3
```

## ComfyUI Pro Stack

The `comfyui` command group adds a curated plugin stack for AI short-drama
production: character consistency, pose/depth control, keyframe generation,
image-to-video, interpolation, assembly, and finishing.

## Anime Drama Styles

The `anime` command group builds local ComfyUI anime short-drama packages with
style presets. It writes story metadata, three ComfyUI workflows, generated
keyframes, subtitles, and an optional vertical motion cut.

List styles:

```powershell
drama anime styles
```

Generate a cyberpunk package:

```powershell
drama anime make --style cyberpunk --output anime_cyberpunk
```

Generate a true image-to-video production package:

```powershell
drama anime make --style rainy --output anime_i2v_wan --motion i2v --video-model wan --width 512 --height 768
```

Use `--video-model ltx` for a lighter LTX-Video-style pass. The I2V mode writes
scene keyframes plus `i2v_plan_*.json`, per-scene I2V blueprints, and a shotlist.
Install the matching ComfyUI video nodes/models before queueing the I2V pass.

Only write workflow files for another machine:

```powershell
drama anime make --style xianxia --output anime_xianxia --dry-run --motion i2v --video-model wan
```

Available styles:

- `rainy`: rainy Tokyo suspense romance.
- `cyberpunk`: neon sci-fi anime.
- `xianxia`: Chinese fantasy anime.
- `shoujo`: soft romance anime.
- `dark`: gothic mystery anime.

Motion modes:

- `fake`: fast ffmpeg push/zoom cut from three generated keyframes.
- `i2v`: true video-model production package for Wan/LTX-style image-to-video.
- `none`: keyframes and metadata only.

List the recommended stack:

```powershell
drama comfyui list --profile pro
```

Check a local ComfyUI install:

```powershell
drama comfyui doctor --path C:\ComfyUI --profile pro
```

Install the profile into `ComfyUI/custom_nodes`:

```powershell
drama comfyui install --path C:\ComfyUI --profile pro --yes
```

Preview install commands without touching the filesystem:

```powershell
drama comfyui install --path C:\ComfyUI --profile pro --dry-run
```

Write reusable production files:

```powershell
drama comfyui manifest --output comfyui_short_drama_plugins.json
drama comfyui blueprint --output comfyui_short_drama_blueprint.json
```

## Profiles

- `core`: Manager, Impact Pack, ControlNet preprocessors, IPAdapter.
- `image`: still-image, cover, poster, and character reference production.
- `video`: animation, Wan video, frame interpolation, and video assembly.
- `pro`: full short-drama production stack.
- `all`: every curated plugin.

## Safety Notes

ComfyUI custom nodes are third-party code. Review repositories before installing,
pin versions for production machines, and prefer ComfyUI Manager for updates and
maintenance. Install dependencies with the same Python runtime that launches
ComfyUI.

## Main Plugin Sources

- [ComfyUI Manager](https://github.com/Comfy-Org/ComfyUI-Manager)
- [ComfyUI Impact Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack)
- [ControlNet Auxiliary Preprocessors](https://github.com/Fannovel16/comfyui_controlnet_aux)
- [ComfyUI IPAdapter Plus](https://github.com/cubiq/ComfyUI_IPAdapter_plus)
- [Video Helper Suite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)
- [AnimateDiff Evolved](https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved)
- [WanVideoWrapper](https://github.com/kijai/ComfyUI-WanVideoWrapper)
- [Frame Interpolation](https://github.com/Fannovel16/ComfyUI-Frame-Interpolation)
- [Ultimate SD Upscale](https://github.com/ssitu/ComfyUI_UltimateSDUpscale)
