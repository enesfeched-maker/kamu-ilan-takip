# Instagram paylaşım kurulumu. Erişim anahtarı yalnızca bu pencerede, gizli girişle alınır;
# diske, loga veya ekrana yazılmaz. Kullanım (herhangi bir klasörden):
#   powershell -ExecutionPolicy Bypass -File "...\bildirim-botu\kurulum-instagram.ps1"
$ErrorActionPreference = 'Stop'
$wrangler = 'C:\Users\Feched\Desktop\codex-ws\node_modules\.bin\wrangler.cmd'
# Üst klasördeki .wrangler/deploy/config.json ile karışmaması için yapılandırma her çağrıda açıkça verilir.
$ayar = Join-Path $PSScriptRoot 'wrangler.toml'
$api = 'https://graph.instagram.com/v25.0'

function Duz([Security.SecureString]$s) {
  $p = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
  try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($p) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p) }
}

function Sir([string]$ad, [string]$deger) {
  $deger | & $wrangler secret put $ad --config $ayar | Out-Null
  if ($LASTEXITCODE) { throw "$ad Cloudflare'a kaydedilemedi (wrangler çıkış kodu $LASTEXITCODE)." }
}

try {
  $token = Duz (Read-Host 'Instagram erişim anahtarı (ekranda görünmez)' -AsSecureString)
  if ($token.Length -lt 50 -or $token -match '\s') { throw 'Anahtar biçimi hatalı. Meta panelindeki "Generate token" ile alınan anahtarı olduğu gibi yapıştır.' }

  # Hata kayıtları istek adresini (dolayısıyla anahtarı) tutabildiği için ayrıntı gösterilmez, kayıt temizlenir.
  try { $ben = Invoke-RestMethod -Method Get -Uri "$api/me?fields=user_id,username&access_token=$token" }
  catch { $Error.Clear(); throw 'Instagram anahtarı kabul etmedi (geçersiz, süresi dolmuş ya da yetkisi eksik).' }
  if (-not $ben.user_id) { throw 'Instagram hesap kimliği alınamadı.' }
  Write-Host "Instagram hesabı doğrulandı: @$($ben.username)"

  Sir 'IG_TOKEN' $token
  Sir 'IG_USER_ID' ([string]$ben.user_id)
  # Eski bir kurulumdan kalan, botun yenileyip sakladığı anahtar yeni anahtarın önüne geçmesin.
  & $wrangler d1 execute kamu-ilan-bildirim --remote --config $ayar -y --command "DELETE FROM meta WHERE anahtar IN ('ig_token','ig_token_tarih','ig_son_hata')" | Out-Null
  if ($LASTEXITCODE) { throw "Eski Instagram kaydı temizlenemedi (wrangler çıkış kodu $LASTEXITCODE)." }
  Write-Host 'Instagram bilgileri Cloudflare''a kaydedildi. Bot her sabah 10:15''ten sonra paylaşım yapacak.'
} catch {
  Write-Host "HATA: $($_.Exception.Message)" -ForegroundColor Red
  $Error.Clear()
  exit 1
} finally {
  $token = $null; $ben = $null
}
