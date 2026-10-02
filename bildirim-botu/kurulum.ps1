# Bildirim botu sır kurulumu. Token yalnızca bu pencerede, gizli girişle alınır;
# diske, loga veya ekrana yazılmaz. Kullanım (bildirim-botu klasöründe):
#   powershell -ExecutionPolicy Bypass -File .\kurulum.ps1 -WorkerUrl https://kamu-ilan-bildirim.<alt-alan>.workers.dev
param([Parameter(Mandatory = $true)][string]$WorkerUrl)
$ErrorActionPreference = 'Stop'
$wrangler = 'C:\Users\Feched\Desktop\codex-ws\node_modules\.bin\wrangler.cmd'
# Üst klasördeki .wrangler/deploy/config.json ile karışmaması için yapılandırma her çağrıda açıkça verilir.
$ayar = Join-Path $PSScriptRoot 'wrangler.toml'

function Duz([Security.SecureString]$s) {
  $p = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
  try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($p) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p) }
}

# Hata kayıtları istek adresini (dolayısıyla token'ı) tutabildiği için ayrıntı gösterilmez, kayıt temizlenir.
function Telegram([string]$yontem, $govde) {
  try {
  # Wrangler geçici dosyalarını çalışma klasörüne yazar; System32 gibi korumalı bir yerden çalıştırılsa da betik klasörüne geç.
  Push-Location $PSScriptRoot
    $istek = @{ Method = 'Post'; Uri = ($script:api + $yontem) }
    if ($govde) { $istek.ContentType = 'application/json; charset=utf-8'; $istek.Body = [Text.Encoding]::UTF8.GetBytes(($govde | ConvertTo-Json -Depth 5)) }
    return Invoke-RestMethod @istek
  } catch {
    $Error.Clear()
    throw "Telegram '$yontem' çağrısı başarısız oldu (token geçersiz ya da iptal edilmiş olabilir)."
  }
}

function Sir([string]$ad, [string]$deger) {
  $deger | & $wrangler secret put $ad --config $ayar | Out-Null
  if ($LASTEXITCODE) { throw "$ad Cloudflare'a kaydedilemedi (wrangler çıkış kodu $LASTEXITCODE)." }
}

try {
  # Wrangler geçici dosyalarını çalışma klasörüne yazar; System32 gibi korumalı bir yerden çalıştırılsa da betik klasörüne geç.
  Push-Location $PSScriptRoot
  $token = Duz (Read-Host 'BotFather token (ekranda görünmez)' -AsSecureString)
  if ($token -notmatch '^\d+:[A-Za-z0-9_-]{30,}$') { throw 'Token biçimi hatalı. BotFather''ın verdiği satırı olduğu gibi yapıştır.' }
  $script:api = "https://api.telegram.org/bot$token/"
  $ben = Telegram 'getMe'
  Write-Host "Bot doğrulandı: @$($ben.result.username)"

  $bayt = New-Object byte[] 32
  [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bayt)
  $gizli = -join ($bayt | ForEach-Object { $_.ToString('x2') })

  Sir 'BOT_TOKEN' $token
  Sir 'WEBHOOK_SECRET' $gizli
  Write-Host 'Sırlar Cloudflare''a kaydedildi.'

  $null = Telegram 'setWebhook' @{ url = ($WorkerUrl.TrimEnd('/') + '/webhook'); secret_token = $gizli
                                   drop_pending_updates = $true; allowed_updates = @('message', 'callback_query') }
  $null = Telegram 'setMyCommands' @{ commands = @(
    @{ command = 'start'; description = 'Başla / onay' }, @{ command = 'ayarlar'; description = 'Tercihlerim' },
    @{ command = 'kelime'; description = 'Anahtar kelimeler' }, @{ command = 'durdur'; description = 'Bildirimleri durdur' },
    @{ command = 'devam'; description = 'Bildirimleri aç' }, @{ command = 'sil'; description = 'Verilerimi sil' },
    @{ command = 'yardim'; description = 'Yardım' }) }
  $durum = Telegram 'getWebhookInfo'
  Write-Host "Webhook bağlandı: $($durum.result.url)"
  Write-Host 'Kurulum tamam. Pencereyi kapatabilirsin.'
} catch {
  Write-Host "HATA: $($_.Exception.Message)" -ForegroundColor Red
  $Error.Clear()
  exit 1
} finally {
  Pop-Location -ErrorAction SilentlyContinue
  $token = $null; $gizli = $null; $script:api = $null; $bayt = $null
}
