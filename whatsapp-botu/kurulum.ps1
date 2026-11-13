$ErrorActionPreference = 'Stop'
$waRuntime = Join-Path $env:LOCALAPPDATA 'KpssTercihi\whatsapp-botu'
$waNode = (Get-Command node -ErrorAction Stop).Source
New-Item -ItemType Directory -Path $waRuntime -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'package.json'),(Join-Path $PSScriptRoot 'package-lock.json') -Destination $waRuntime -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'src') -Destination $waRuntime -Recurse -Force
$env:PUPPETEER_SKIP_DOWNLOAD = 'true'
Push-Location $waRuntime
try {
    npm ci --omit=dev
    if ($LASTEXITCODE -ne 0) { throw 'WhatsApp bağımlılıkları kurulamadı' }
} finally { Pop-Location }
$waEntry = Join-Path $waRuntime 'src\bot.js'
$waVbs = Join-Path $waRuntime 'baslat.vbs'
$waQuotedNode = $waNode.Replace('"','""')
$waQuotedEntry = $waEntry.Replace('"','""')
$waQuotedRoot = $waRuntime.Replace('"','""')
$waLauncher = @"
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "$waQuotedRoot"
WScript.Quit sh.Run("""$waQuotedNode"" ""$waQuotedEntry""", 0, True)
"@
Set-Content -LiteralPath $waVbs -Value $waLauncher -Encoding Unicode
$waAction = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument ('"' + $waVbs + '"') -WorkingDirectory $waRuntime
$waTrigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$waSettings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'KPSS WhatsApp Kanal Botu' -Action $waAction -Trigger $waTrigger -Settings $waSettings -Description 'KPSS Tercihi sosyal paylaşımlarını WhatsApp kanalına aktarır' -Force | Out-Null
Write-Host 'Kuruldu. Başlatmak için: Start-ScheduledTask -TaskName "KPSS WhatsApp Kanal Botu"'
Write-Host 'Bağlantı durumu: http://127.0.0.1:8789/'
