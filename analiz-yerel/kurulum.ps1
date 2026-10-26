# KPSS Tercihi yerel analiz toplayıcısı kurulumu (bir kez çalıştırılır).
# .env dosyasına panel anahtarını gizli girişle yazar ve Windows'ta oturum açılınca otomatik başlayan görev kurar.
$ErrorActionPreference = 'Stop'
$dizin = $PSScriptRoot
$node = (Get-Command node -ErrorAction Stop).Source
$surum = [version](& $node -p "process.versions.node")
if ($surum -lt [version]'22.13') { throw "Node 22.13 veya yenisi gerekli (kurulu: $surum)." }

$env_dosyasi = Join-Path $dizin '.env'
if (-not (Test-Path $env_dosyasi)) {
    $g = Read-Host 'Panel anahtarı (en az 16 karakter; ekranda görünmez)' -AsSecureString
    $anahtar = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($g))
    if ($anahtar.Length -lt 16) { throw 'Anahtar en az 16 karakter olmalı.' }
    Set-Content -Path $env_dosyasi -Value "PANEL_ANAHTARI=$anahtar`nPORT=8787" -Encoding ascii
    Write-Host '.env yazıldı (git dışında tutulur).'
} else { Write-Host '.env zaten var, dokunulmadı.' }

$eylem = New-ScheduledTaskAction -Execute (Join-Path $env:WINDIR 'System32\wscript.exe') -Argument "`"$dizin\gizli-baslat.vbs`"" -WorkingDirectory $dizin   # konsol penceresi açmaz
$tetik = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$ayar = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'KPSS Analiz Toplayici' -Action $eylem -Trigger $tetik -Settings $ayar -Description 'KPSS Tercihi cerezsiz analiz toplayicisi (127.0.0.1:8787)' -Force | Out-Null
Start-ScheduledTask -TaskName 'KPSS Analiz Toplayici'
Start-Sleep -Seconds 3
try { Write-Host ('Yanıt: ' + (Invoke-WebRequest http://127.0.0.1:8787/ -UseBasicParsing).Content) } catch { Write-Host 'Sunucu henüz yanıt vermedi: ' $_.Exception.Message }
