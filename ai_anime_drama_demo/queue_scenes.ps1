param(
  [string]$Server = "http://127.0.0.1:8188",
  [string]$ComfyOutput = "D:\AI\ComfyUI\app\output",
  [int]$PollSeconds = 5
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$scenes = @(
  @{ Json = "comfy_scene_01.json"; Prefix = "anime_drama_ep01_sc01"; Output = "scene01.png" },
  @{ Json = "comfy_scene_02.json"; Prefix = "anime_drama_ep01_sc02"; Output = "scene02.png" },
  @{ Json = "comfy_scene_03.json"; Prefix = "anime_drama_ep01_sc03"; Output = "scene03.png" }
)

$promptIds = @()
foreach ($scene in $scenes) {
  $jsonPath = Join-Path $root $scene.Json
  $response = curl.exe -s -H "Content-Type: application/json" --data-binary "@$jsonPath" "$Server/prompt" | ConvertFrom-Json
  if (-not $response.prompt_id) {
    throw "Failed to queue $($scene.Json): $response"
  }
  $promptIds += [pscustomobject]@{
    Prefix = $scene.Prefix
    Output = $scene.Output
    PromptId = $response.prompt_id
  }
  Write-Host "Queued $($scene.Json) -> $($response.prompt_id)"
}

$promptIds | ForEach-Object { $_.PromptId } | Set-Content -Encoding UTF8 (Join-Path $root "prompt_ids.txt")

foreach ($item in $promptIds) {
  Write-Host "Waiting for $($item.Prefix) ..."
  while ($true) {
    $historyText = curl.exe -s "$Server/history/$($item.PromptId)"
    if ($historyText -and $historyText -ne "{}") {
      $history = $historyText | ConvertFrom-Json
      $entry = $history.PSObject.Properties.Value | Select-Object -First 1
      if ($entry.outputs.'9'.images.Count -gt 0) {
        break
      }
    }
    Start-Sleep -Seconds $PollSeconds
  }

  $latest = Get-ChildItem -LiteralPath $ComfyOutput -Filter "$($item.Prefix)*.png" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if (-not $latest) {
    throw "No output image found for $($item.Prefix)"
  }
  Copy-Item -LiteralPath $latest.FullName -Destination (Join-Path $root $item.Output) -Force
  Write-Host "Copied $($latest.Name) -> $($item.Output)"
}

Write-Host "All keyframes are ready."
