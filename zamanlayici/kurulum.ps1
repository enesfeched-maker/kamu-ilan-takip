# Zamanlayıcı sır kurulumu. GitHub anahtarı yalnızca bu pencerede, gizli girişle alınır;
# diske, loga veya ekrana yazılmaz. Kullanım (zamanlayici klasöründe):
#   powershell -ExecutionPolicy Bypass -File .\kurulum.ps1
$ErrorActionPreference = 'Stop'
$wrangler = 'C:\Users\Feched\Desktop\codex-ws\node_modules\.bin\wrangler.cmd'
$ayar = Join-Path $PSScriptRoot 'wrangler.toml'
$depo = 'enesfeched-maker/kamu-ilan-takip'

function Duz([Security.SecureString]$s) {
  $p = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
  try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($p) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p) }
}

try {
  Push-Location $PSScriptRoot
  $token = Duz (Read-Host 'GitHub anahtarı (ekranda görünmez)' -AsSecureString)
  if ($token -notmatch '^(github_pat_|ghp_)[A-Za-z0-9_]{20,}$') { throw 'Anahtar biçimi hatalı. GitHub''ın verdiği satırı olduğu gibi yapıştır.' }
  # Anahtarın bu depoda iş akışı başlatabildiğini doğrula (bekçiyi deneme kipinde başlatır, mesaj atmaz).
  try {
    $istek = @{ Method = 'Post'; Uri = "https://api.github.com/repos/$depo/actions/workflows/bekci.yml/dispatches"
                Headers = @{ Authorization = "Bearer $token"; Accept = 'application/vnd.github+json'; 'User-Agent' = 'kpsstercihi-kurulum' }
                ContentType = 'application/json'; Body = '{"ref":"main","inputs":{"deneme":"true"}}' }
    Invoke-RestMethod @istek | Out-Null
  } catch {
    $Error.Clear()
    throw 'Anahtar GitHub''da iş akışı başlatamadı. Depo erişimi (kamu-ilan-takip) ve "Actions: Read and write" yetkisini kontrol et.'
  }
  Write-Host 'Anahtar doğrulandı: GitHub''da iş akışı başlatabiliyor.'
  $token | & $wrangler secret put GH_TOKEN --config $ayar | Out-Null
  if ($LASTEXITCODE) { throw "GH_TOKEN Cloudflare'a kaydedilemedi (wrangler çıkış kodu $LASTEXITCODE)." }
  Write-Host 'Kurulum tamam: zamanlayıcı her 30 dakikada bir taramayı, 7 dakika sonra bekçiyi başlatacak. Pencereyi kapatabilirsin.'
} catch {
  Write-Host "HATA: $($_.Exception.Message)" -ForegroundColor Red
  $Error.Clear()
  exit 1
} finally {
  Pop-Location -ErrorAction SilentlyContinue
  $token = $null
}
