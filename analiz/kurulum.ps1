# KPSS Tercihi site analizi kurulumu. Panel anahtarı yalnızca bu pencerede, gizli girişle alınır;
# diske, loga veya ekrana yazılmaz. Kullanım (analiz klasöründe):
#   powershell -ExecutionPolicy Bypass -File .\kurulum.ps1
# Adımlar: D1 oluştur (yoksa) -> kimliği wrangler.toml'a yaz -> tabloları kur -> PANEL_ANAHTARI -> dağıt.
# Her adım yeniden çalıştırılabilir (tablolar IF NOT EXISTS; var olan veritabanı yeniden oluşturulmaz).
$ErrorActionPreference = 'Stop'
$wrangler = 'C:\Users\Feched\Desktop\codex-ws\node_modules\.bin\wrangler.cmd'
# Üst klasördeki .wrangler/deploy/config.json ile karışmaması için yapılandırma her çağrıda açıkça verilir.
$ayar = Join-Path $PSScriptRoot 'wrangler.toml'
$yer = 'BURAYA-D1-ID-YAZ'

function Duz([Security.SecureString]$s) {
  $p = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
  try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($p) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p) }
}

function Wr([string[]]$argumanlar) {
  & $wrangler @argumanlar --config $ayar
  if ($LASTEXITCODE) { throw "wrangler $($argumanlar[0]) başarısız oldu (çıkış kodu $LASTEXITCODE)." }
}

try {
  Push-Location $PSScriptRoot
  $toml = [IO.File]::ReadAllText($ayar)

  # 1) D1 veritabanı
  if ($toml.Contains($yer)) {
    Write-Host '1/4  D1 veritabanı oluşturuluyor (kpss-analiz)...'
    $cikti = (& $wrangler d1 create kpss-analiz --config $ayar 2>&1 | Out-String)
    if ($cikti -notmatch 'database_id"?\s*[=:]\s*"([0-9a-fA-F-]{36})"') { Write-Host $cikti; throw 'Veritabanı kimliği çıktıdan okunamadı. Aynı adda veritabanı varsa: wrangler d1 list ile kimliği bulup wrangler.toml içine elle yaz.' }
    $toml = $toml.Replace($yer, $Matches[1])
    [IO.File]::WriteAllText($ayar, $toml, (New-Object Text.UTF8Encoding $false))
    Write-Host "     Kimlik wrangler.toml dosyasına yazıldı: $($Matches[1])"
  } else { Write-Host '1/4  D1 kimliği wrangler.toml içinde zaten var, atlandı.' }

  # 2) Tablolar
  Write-Host '2/4  Tablolar kuruluyor...'
  Wr @('d1', 'execute', 'kpss-analiz', '--remote', '--file=schema.sql', '--yes')

  # 3) Panel anahtarı
  $anahtar = Duz (Read-Host 'Panel anahtarı (en az 16 karakter, ekranda görünmez)' -AsSecureString)
  if ($anahtar.Length -lt 16) { throw 'Anahtar en az 16 karakter olmalı.' }
  Write-Host '3/4  PANEL_ANAHTARI Cloudflare''a kaydediliyor...'
  $anahtar | & $wrangler secret put PANEL_ANAHTARI --config $ayar | Out-Null
  if ($LASTEXITCODE) { throw "PANEL_ANAHTARI kaydedilemedi (çıkış kodu $LASTEXITCODE)." }

  # 4) Dağıtım (api.kpsstercihi.com özel alan adını da oluşturur)
  Write-Host '4/4  Dağıtılıyor...'
  Wr @('deploy')
  Write-Host 'Kurulum tamam. Panel: https://api.kpsstercihi.com/panel'
} catch {
  Write-Host "HATA: $($_.Exception.Message)" -ForegroundColor Red
  $Error.Clear()
  exit 1
} finally {
  Pop-Location -ErrorAction SilentlyContinue
  $anahtar = $null
}