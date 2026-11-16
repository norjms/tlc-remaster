param([int]$Scale = 2, [string]$Keys = '', [string]$Frames = '90', [string]$Out = 'combat', [string]$Race = '4', [string]$Fleet = '3')
$r = "$env:USERPROFILE\Documents\GitHub\tlc-remaster"
$run = "$env:TEMP\sf_run9"
robocopy "$r\bin\data" "$run\data" /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
Copy-Item "$r\build-win\Release\starflighttlc.exe" "$run\" -Force
$g = "$run\data\globals.lua"
(Get-Content $g | Where-Object { $_ -notmatch '^STARTUPMODULE' }) + 'STARTUPMODULE = "ENCOUNTER"' | Set-Content $g
$od = "\\192.168.1.50\ai-workspace\starflight\step9\shots\$Out"; New-Item -ItemType Directory -Force $od | Out-Null; Remove-Item "$od\*" -Force -ErrorAction SilentlyContinue
$env:SDL_VIDEO_DRIVER = 'offscreen'; $env:SDL_AUDIO_DRIVER = 'dummy'
$env:A4_SCALE = "$Scale"; $env:A4_SHOT_DIR = $od; $env:A4_SHOT_FRAMES = $Frames; $env:A4_INPUT = $Keys
$env:TLC_TEST_ALIEN = $Race; $env:TLC_TEST_FLEET = $Fleet
$p = Start-Process -FilePath "$run\starflighttlc.exe" -WorkingDirectory $run -PassThru -Wait -NoNewWindow -RedirectStandardError "$od\stderr.txt"
"exit $($p.ExitCode); shots " + (Get-ChildItem $od -Filter *.bmp).Count
