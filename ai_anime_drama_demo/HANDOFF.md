# AI Anime Drama Handoff

This folder is a portable test package for the local ComfyUI anime short-drama demo.

## Current Result

- Story: `story.json`
- Keyframes: `scene01.png`, `scene02.png`, `scene03.png`
- Dynamic sample: `midnight_confession_motion.mp4`
- ComfyUI workflows: `comfy_scene_01.json`, `comfy_scene_02.json`, `comfy_scene_03.json`

## Local Model Layout

The current machine uses this layout:

```powershell
D:\AI\ComfyUI\app
D:\AI\ComfyUI\models\checkpoints\Counterfeit-V3.0_fix_fp16.safetensors
D:\AI\ComfyUI\models\checkpoints\animagine-xl-4.0-opt.safetensors
```

`Counterfeit-V3.0_fix_fp16.safetensors` is the practical low-VRAM test model.
`animagine-xl-4.0-opt.safetensors` is higher quality but wants a much stronger GPU.

## Run On This Machine

Start ComfyUI CPU mode:

```powershell
D:\AI\ComfyUI\start_cpu.bat
```

Queue the three ComfyUI scenes:

```powershell
powershell -ExecutionPolicy Bypass -File .\queue_scenes.ps1
```

Render the dynamic vertical video:

```powershell
powershell -ExecutionPolicy Bypass -File .\render_motion.ps1
```

## Run On A Stronger GPU Machine

1. Copy this folder and the model files.
2. Install ComfyUI.
3. Put models under `ComfyUI\models\checkpoints`, or update `extra_model_paths.yaml`.
4. Install CUDA PyTorch for the target GPU.
5. Start with:

```powershell
python main.py --normalvram --listen 127.0.0.1 --port 8188 --extra-model-paths-config extra_model_paths.yaml
```

For 8GB VRAM or more, try `animagine-xl-4.0-opt.safetensors` and 768x1152 or 832x1216 keyframes.

## Next Quality Upgrade

- Add IPAdapter or a character LoRA to lock `星野澪` and `神代莲`.
- Add AnimateDiff or WanVideoWrapper on a stronger GPU for real motion.
- Generate 9-12 keyframes per episode, then render with this lightweight motion pass.
