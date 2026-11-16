param([int]$Scale = 1, [string]$Keys = '', [string]$Frames = '200', [string]$Out = 'sm', [string]$Module = 'INTERPLANETARY', [int]$Timeout = 120)
$r = "$env:USERPROFILE\Documents\GitHub\tlc-remaster"
$run = "$env:TEMP\sf_run10b"
robocopy "$r\bin\data" "$run\data" /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
Copy-Item "$r\build-win\Release\starflighttlc.exe" "$run\" -Force
$g = "$run\data\globals.lua"
(Get-Content $g | Where-Object { $_ -notmatch '^STARTUPMODULE' }) + "STARTUPMODULE = `"$Module`"" | Set-Content $g
$od = "\\192.168.1.50\ai-workspace\starflight\step10b\shots\$Out"; New-Item -ItemType Directory -Force $od | Out-Null; Remove-Item "$od\*" -Force -ErrorAction SilentlyContinue
$env:SDL_VIDEO_DRIVER = 'offscreen'; $env:SDL_AUDIO_DRIVER = 'dummy'
$env:A4_SCALE = "$Scale"; $env:A4_SHOT_DIR = $od; $env:A4_SHOT_FRAMES = $Frames; $env:A4_INPUT = $Keys
$p = Start-Process -FilePath "$run\starflighttlc.exe" -WorkingDirectory $run -PassThru -NoNewWindow -RedirectStandardError "$od\stderr.txt"
if (-not $p.WaitForExit($Timeout * 1000)) { Stop-Process -Id $p.Id -Force; "timeout (killed $($p.Id))" }
"exit $($p.ExitCode); shots " + (Get-ChildItem $od -Filter *.bmp).Count
