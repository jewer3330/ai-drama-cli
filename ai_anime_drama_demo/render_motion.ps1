param(
  [string]$Output = "midnight_confession_motion.mp4"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root
try {
  ffmpeg.exe -y `
    -loop 1 -t 4 -i scene01.png `
    -loop 1 -t 4 -i scene02.png `
    -loop 1 -t 4 -i scene03.png `
    -filter_complex "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='1+0.0008*on':x='iw/2-(iw/zoom/2)+12*sin(on/16)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=25,eq=contrast=1.06:saturation=1.08[v0];[1:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='1.04-0.0005*on':x='iw/2-(iw/zoom/2)-10*sin(on/14)':y='ih/2-(ih/zoom/2)+8*sin(on/20)':d=1:s=1080x1920:fps=25,eq=contrast=1.12:saturation=1.12[v1];[2:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='1+0.0007*on':x='iw/2-(iw/zoom/2)+18*sin(on/18)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=25,eq=contrast=1.08:saturation=1.1[v2];[v0][v1]xfade=transition=fade:duration=0.35:offset=3.65[x1];[x1][v2]xfade=transition=smoothleft:duration=0.35:offset=7.30,format=yuv420p,subtitles=subtitles.srt:force_style='FontName=Microsoft YaHei,Fontsize=13,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=120'[v]" `
    -map "[v]" -r 25 -movflags +faststart $Output
}
finally {
  Pop-Location
}

Write-Host "Rendered $Output"
