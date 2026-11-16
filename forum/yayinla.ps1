# Forum API yayin yardimcisi (idempotent): D1, gocler, sirlar, dagitim ve duman testi.
# Her calistirmada yalniz eksik olani yapar; tekrar calistirmak guvenlidir. forum/ klasorunden calistir:
#   powershell -ExecutionPolicy Bypass -File .\yayinla.ps1 -Kuru     # yalniz ne yapacagini yazar (uzakta degisiklik yok)
#   powershell -ExecutionPolicy Bypass -File .\yayinla.ps1           # gercek yayin
# Ayrintilar ve elle adimlar: KURULUM.md.
#
# Sirlar:
#   OTURUM_SIRRI, YONETICI_ANAHTARI, SIFRE_BIBERI: eksikse bu betik guclu rastgele deger uretir, wrangler'a yazar ve
#     YALNIZ yerel dosyaya ($env:USERPROFILE\.kpss-forum-sirlari.txt, depo disi) kaydeder. Bu dosyayi YEDEKLE.
#     SIFRE_BIBERI hicbir zaman degismemeli: degisirse tum sifreler ve kurtarma kodlari gecersiz olur.
#   TELEGRAM_BOT_TOKEN: sahibinden gelir (gizli giris, diske yazilmaz). Bildirim botuyla (@kamuilanibot) ayni belirectir;
#     bildirim-botu/ Worker'indaki BOT_TOKEN sirri Cloudflare'dan geri okunamaz, BotFather > /mybots > @kamuilanibot > API Token'dan alinir.
# Sir degerleri ekrana, loga ya da depoya YAZILMAZ.
param(
  [switch]$Kuru,        # kuru calisma: yalniz yapilacaklari yazar; okuma amacli (whoami, list) komutlar disinda uzaga dokunmaz
  [switch]$TestAtla     # yayindan once calisan forum testlerini atla (onerilmez)
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$ayar = 'wrangler.toml'
$dbAd = 'kpss-forum'
$adres = 'https://forum-api.kpsstercihi.com'
$sirDosyasi = Join-Path $env:USERPROFILE '.kpss-forum-sirlari.txt'
$uyarilar = New-Object System.Collections.ArrayList

function Bilgi([string]$m) { Write-Host $m }
function Adim([string]$m) { Write-Host ''; Write-Host ('== ' + $m) -ForegroundColor Cyan }
function Kuru([string]$m) { Write-Host ('[KURU] ' + $m) -ForegroundColor Yellow }
function Uyari([string]$m) { [void]$uyarilar.Add($m); Write-Host ('UYARI: ' + $m) -ForegroundColor Yellow }

# ---------- wrangler cagrisi (stderr sorunu olmadan; kod + cikti doner) ----------
function WranglerBul {
  $d = $PSScriptRoot
  while ($d) {
    $c = Join-Path $d 'node_modules\.bin\wrangler.cmd'
    if (Test-Path $c) { return $c }
    $p = Split-Path $d -Parent
    if (-not $p -or $p -eq $d) { break }
    $d = $p
  }
  return $null
}
$script:wr = WranglerBul
function Wr([string[]]$Arg, [string]$Girdi = $null) {
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  if ($script:wr) { $psi.FileName = $script:wr; $a = $Arg } else { $psi.FileName = 'npx.cmd'; $a = @('wrangler') + $Arg }
  $psi.Arguments = (($a | ForEach-Object { if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ } }) -join ' ')
  $psi.UseShellExecute = $false
  # stdin her zaman yonlendirilip kapatilir: wrangler hicbir komutta gorunmez bir soruda takili kalmaz
  $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true; $psi.RedirectStandardInput = $true
  $psi.StandardOutputEncoding = [Text.Encoding]::UTF8; $psi.StandardErrorEncoding = [Text.Encoding]::UTF8
  $psi.WorkingDirectory = $PSScriptRoot
  $p = [System.Diagnostics.Process]::Start($psi)
  $o = $p.StandardOutput.ReadToEndAsync(); $e = $p.StandardError.ReadToEndAsync()
  if ($null -ne $Girdi -and $Girdi -ne '') { $p.StandardInput.Write($Girdi) }
  $p.StandardInput.Close()
  $p.WaitForExit()
  return [pscustomobject]@{ Kod = $p.ExitCode; Cikti = $o.Result; Hata = $e.Result }
}
function JsonCoz([string]$s) {
  if (-not $s) { return $null }
  $i = $s.IndexOfAny([char[]]@('[', '{'))
  if ($i -lt 0) { return $null }
  try { return ($s.Substring($i) | ConvertFrom-Json) } catch { return $null }
}
function WrHata([string]$ne, $r) {
  # Sir degeri hicbir wrangler ciktisinda yer almaz; yine de yalniz ilk satirlari goster.
  $m = (($r.Hata + "`n" + $r.Cikti) -split "`n" | Where-Object { $_.Trim() } | Select-Object -First 6) -join "`n"
  throw "$ne basarisiz (cikis kodu $($r.Kod)).`n$m"
}
function D1Calistir([string]$bayrak, [string]$deger) {   # yazma: --file ya da --command
  $r = Wr @('d1', 'execute', $dbAd, '--remote', '--config', $ayar, '--yes', '--json', $bayrak, $deger)
  if ($r.Kod -ne 0) { WrHata "D1 komutu ($bayrak)" $r }
  return $r
}
function D1Oku([string]$sql) {   # salt okunur sorgu; satir listesi doner
  $r = Wr @('d1', 'execute', $dbAd, '--remote', '--config', $ayar, '--json', '--command', $sql)
  if ($r.Kod -ne 0) { WrHata 'D1 sorgusu' $r }
  $j = @(JsonCoz $r.Cikti)
  if ($j.Count -eq 0 -or $null -eq $j[0].results) { return @() }
  return @($j[0].results)
}
function DosyaCalistir([string]$yol, [string]$aciklama) {
  if ($Kuru) { Kuru "$aciklama ($yol) uygulanacak"; return }
  Bilgi "  $aciklama ..."
  [void](D1Calistir '--file' $yol)
}

# ---------- sir dosyasi (yalniz yerel, depo disi) ----------
function SirDosyasiOku {
  $h = @{}
  if (Test-Path $sirDosyasi) {
    foreach ($s in [IO.File]::ReadAllLines($sirDosyasi)) {
      # -cmatch sart: tr-TR kulturunde -match [A-Z] ile "I" eslesmez, yedek hic okunmazdi
      if ($s -cmatch '^\s*([A-Z_]+)=(.+)$') { $h[$Matches[1]] = $Matches[2].Trim() }
    }
  }
  return $h
}
function SirDosyasinaYaz([string]$ad, [string]$deger) {
  if (-not (Test-Path $sirDosyasi)) {
    [IO.File]::WriteAllText($sirDosyasi, "# KPSS Tercihi forum sirlari. BU DOSYAYI YEDEKLE, kimseyle paylasma, depoya koyma.`r`n# SIFRE_BIBERI asla degismemeli (degisirse tum sifreler ve kurtarma kodlari gecersiz olur).`r`n", (New-Object Text.UTF8Encoding $false))
    try { & icacls.exe $sirDosyasi /inheritance:r /grant:r ("{0}:(R,W)" -f $env:USERNAME) | Out-Null } catch { }
  }
  [IO.File]::AppendAllText($sirDosyasi, "$ad=$deger`r`n", (New-Object Text.UTF8Encoding $false))
}
function Rastgele([int]$bayt = 48) {
  $b = New-Object byte[] $bayt
  $g = [Security.Cryptography.RandomNumberGenerator]::Create()
  $g.GetBytes($b); $g.Dispose()
  return ([Convert]::ToBase64String($b)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}
function DuzMetin([Security.SecureString]$s) {
  $p = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($p) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p) }
}

if ($Kuru) { Write-Host 'KURU CALISMA: uzakta hicbir sey degismeyecek; yalniz okuma komutlari (whoami, d1 list, secret list, salt okunur sorgular) calisir.' -ForegroundColor Yellow }

# ---------- 1. Cloudflare oturumu ----------
Adim '1/7 Cloudflare oturumu'
$r = Wr @('whoami')
if ($r.Kod -ne 0 -or ($r.Cikti + $r.Hata) -match '(?i)not authenticated|not logged in|You are not') {
  throw "Cloudflare'a giris yapilmamis. Once calistir: npx wrangler login  (sonra bu betigi yeniden calistir)"
}
Bilgi 'Cloudflare oturumu acik.'

# ---------- 2. Testler ----------
Adim '2/7 Forum testleri'
if ($TestAtla) { Uyari 'Testler atlandi (-TestAtla).' }
elseif ($Kuru) { Kuru 'node --test "test/*.test.js" calistirilacak (kirik test yayini durdurur)' }
else {
  & node --test 'test/*.test.js' | Out-Null
  if ($LASTEXITCODE -ne 0) { throw 'Forum testleri basarisiz; yayin durduruldu. Duzeltip yeniden calistir.' }
  Bilgi 'Testler gecti.'
}

# ---------- 3. D1 veritabani ----------
Adim "3/7 D1 veritabani ($dbAd)"
function DbBul {
  $r = Wr @('d1', 'list', '--json', '--config', $ayar)
  if ($r.Kod -ne 0) { WrHata 'd1 list' $r }
  foreach ($d in @(JsonCoz $r.Cikti)) { if ($d.name -eq $dbAd) { return $d } }
  return $null
}
$db = DbBul
if ($db) { Bilgi "Veritabani var (id ...$($db.uuid.Substring($db.uuid.Length - 6)))." }
elseif ($Kuru) { Kuru "$dbAd olusturulacak ve kimligi wrangler.toml icine yazilacak (BURAYA-ID yerine)" }
else {
  Bilgi "$dbAd olusturuluyor ..."
  $c = Wr @('d1', 'create', $dbAd, '--config', $ayar)
  if ($c.Kod -ne 0) { WrHata 'd1 create' $c }
  $db = DbBul
  if (-not $db) { throw 'Veritabani olusturuldu ama list ciktisinda bulunamadi; yeniden calistir.' }
}
$tomlYol = Join-Path $PSScriptRoot $ayar
$toml = [IO.File]::ReadAllText($tomlYol)
if ($db) {
  if ($toml -match 'database_id\s*=\s*"BURAYA-ID"') {   # kuru calismada da yazilir (yalniz yerel dosya; okuma sorgulari dogru kimlige ihtiyac duyar)
    [IO.File]::WriteAllText($tomlYol, ($toml -replace 'database_id\s*=\s*"BURAYA-ID"', ('database_id = "' + $db.uuid + '"')), (New-Object Text.UTF8Encoding $false))
    Bilgi 'wrangler.toml icine database_id yazildi.'
  } elseif ($toml -match 'database_id\s*=\s*"([^"]+)"' -and $Matches[1] -ne $db.uuid) {
    throw "wrangler.toml icindeki database_id ($($Matches[1])) Cloudflare'daki '$dbAd' ($($db.uuid)) ile ayni degil. Elle duzelt."
  } else { Bilgi 'wrangler.toml database_id dogru.' }
} elseif ($Kuru -and $toml -match 'BURAYA-ID') { Kuru 'wrangler.toml: BURAYA-ID duzeltilecek' }

# ---------- 4. Sema ve goc (probe tabanli: sutun/indeks varsa atlanir) ----------
Adim '4/7 Sema ve gocler'
$schema = Join-Path $PSScriptRoot 'schema.sql'
$goc = @{ '0002' = 'migrations\0002_ozellikler.sql'; '0003' = 'migrations\0003_odalar.sql'; '0004' = 'migrations\0004_ozel_takip.sql'; '0005' = 'migrations\0005_kayit.sql' }
$tablolar = @()
if ($db) {
  $tablolar = @(D1Oku "SELECT name FROM sqlite_master WHERE type='table'" | ForEach-Object { $_.name })
}
$uyelerVar = $tablolar -contains 'uyeler'
function Sutunlar([string]$tablo) { if ($tablolar -contains $tablo) { return @(D1Oku "PRAGMA table_info($tablo)" | ForEach-Object { $_.name }) } else { return @() } }
function IndeksVar([string]$ad) { return (@(D1Oku "SELECT name FROM sqlite_master WHERE type='index' AND name='$ad'")).Count -gt 0 }

if (-not $db) {
  Kuru 'Veritabani olusunca: bos ise schema.sql + odalar.sql uygulanir (gocler yeni semada gerekmez)'
} elseif (-not $uyelerVar) {
  Bilgi 'Bos veritabani: schema.sql guncel semayi kurar; gocler (0002-0005) gerekmez, zaten icindedir.'
  DosyaCalistir $schema 'schema.sql'
} else {
  $uyeS = Sutunlar 'uyeler'; $basS = Sutunlar 'basliklar'
  $bekleyen = @()
  if ($basS -notcontains 'duzey') { $bekleyen += '0002' }
  if ($tablolar -contains 'yanitlar' -and -not (IndeksVar 'yanitlar_ust')) { $bekleyen += '0003' }
  if ($uyeS -notcontains 'dm_acik') { $bekleyen += '0004' }
  if ($uyeS -notcontains 'sifre_ozet') { $bekleyen += '0005' }
  if ($bekleyen.Count -eq 0) { Bilgi 'Gocler zaten uygulanmis.' }
  if ($bekleyen -contains '0005') {
    # 0005 oncesi kontrol: rumuz_kat cakismasi benzersiz indeksi kurdurmaz.
    $metin = [IO.File]::ReadAllText((Join-Path $PSScriptRoot $goc['0005']))
    if ($metin -notmatch '(?m)^-- ONCE KONTROL:\s*(?<q>SELECT .+?HAVING COUNT\(\*\) > 1\))') { throw '0005 on kontrol sorgusu dosyada bulunamadi.' }
    # --remote --file ice aktarma API'sini kullanir ve SELECT sonucunu DONDURMEZ (yalniz "Total queries executed" ozeti);
    # bu yuzden sorgu --command ile calisir. Komut satirinda Turkce harf bozulmasin diye 'C' gibi tek harfli metinler char(kod) olur.
    $q = [regex]::Replace($Matches['q'], "'([^\x00-\x7F])'", [Text.RegularExpressions.MatchEvaluator]{ param($m) 'char(' + [int][char]$m.Groups[1].Value + ')' })
    # -cmatch: tr-TR kulturunde buyuk/kucuk harf duyarsiz eslemede "I" bile ASCII disi sayilir
    if ($q -cmatch '[^\x00-\x7F]') { throw '0005 on kontrol sorgusu ASCII yapilamadi.' }
    $kr = @(D1Oku $q)
    if ($kr.Count -eq 0) { throw '0005 on kontrol sorgusu sonuc dondurmedi; yayin durduruldu.' }
    $cakisma = [int](@($kr[0].PSObject.Properties)[0].Value)
    if ($cakisma -gt 0) { throw "0005 durduruldu: $cakisma rumuz grubu Turkce harf/buyuk-kucuk harf/nokta/alt cizgi farkiyla cakisiyor. Cakisan hesaplardan birinin rumuzunu elle degistirip yeniden calistir." }
    Bilgi '0005 on kontrolu temiz (cakisan rumuz yok).'
  }
  foreach ($k in ($bekleyen | Sort-Object)) { DosyaCalistir (Join-Path $PSScriptRoot $goc[$k]) "goc $k" }
  if ($bekleyen.Count -gt 0 -or $uyeS -notcontains 'kayitli') {
    if (-not $Kuru -and (Sutunlar 'uyeler') -notcontains 'kayitli') {
      Bilgi '  uyeler.kayitli sutunu ekleniyor (0005 daha once kayitli sutunsuz uygulanmis olabilir) ...'
      [void](D1Calistir '--command' 'ALTER TABLE uyeler ADD COLUMN kayitli TEXT')
    } elseif ($Kuru -and $uyeS -notcontains 'kayitli' -and $bekleyen -notcontains '0005') { Kuru 'uyeler.kayitli sutunu eklenecek' }
  }
  # e-posta ile giris sutunlari: 0005 e-postasiz haliyle daha once uygulanmissa (sifre_ozet var, eposta yok) yalniz eksik sutunlar eklenir
  $sutunEklendi = $false
  foreach ($ek in @(@('eposta', 'TEXT'), @('eposta_dogrulandi', 'INTEGER'), @('silindi', 'INTEGER'))) {
    if ($bekleyen -contains '0005') { break }   # 0005 dosyasi zaten ekler
    if ($uyeS -notcontains $ek[0]) {
      if ($Kuru) { Kuru ("uyeler." + $ek[0] + " sutunu eklenecek") }
      else { Bilgi ("  uyeler." + $ek[0] + " sutunu ekleniyor ..."); [void](D1Calistir '--command' ("ALTER TABLE uyeler ADD COLUMN " + $ek[0] + " " + $ek[1])); $sutunEklendi = $true }
    }
  }
  # eksik tablo/indeksler icin (idempotent) guncel sema
  $beklenen =[regex]::Matches([IO.File]::ReadAllText($schema), 'CREATE TABLE IF NOT EXISTS (\w+)') | ForEach-Object { $_.Groups[1].Value }
  $eksik = @($beklenen | Where-Object { (@(D1Oku "SELECT name FROM sqlite_master WHERE type='table' AND name='$_'")).Count -eq 0 })
  if ($eksik.Count -gt 0 -or $bekleyen.Count -gt 0 -or $sutunEklendi) { DosyaCalistir $schema 'schema.sql (eksik tablo/indeksler)' } else { Bilgi 'Sema guncel.' }
}
# sabit sohbet odalari (dosya zaten "yoksa ekle" mantigiyla yazilmis; yine de gereksiz calistirma)
$odaDosya = Join-Path $PSScriptRoot 'odalar.sql'
$odaSayisi = ([regex]::Matches([IO.File]::ReadAllText($odaDosya), '(?m)^INSERT INTO basliklar')).Count
$mevcutOda = 0
if ($db -and (($tablolar -contains 'basliklar') -or ((-not $uyelerVar) -and (-not $Kuru)))) {
  try { $mevcutOda = [int](@(D1Oku "SELECT COUNT(*) AS n FROM basliklar WHERE kategori='oda'")[0].n) } catch { $mevcutOda = 0 }
}
if ($db -and $mevcutOda -ge $odaSayisi) { Bilgi "Sohbet odalari var ($mevcutOda)." }
else { DosyaCalistir $odaDosya 'odalar.sql' }

# ---------- 5. Sirlar ----------
Adim '5/7 Sirlar'
$gerekli = @('OTURUM_SIRRI', 'YONETICI_ANAHTARI', 'SIFRE_BIBERI', 'TELEGRAM_BOT_TOKEN')
function SirListesi {   # tanimli sir adlari; Worker yoksa $null. Baska her hata yayini DURDURUR: liste okunamazken
  # "sir yok" sanip SIFRE_BIBERI'ni yeni degerle ezmek tum sifreleri gecersiz kilar.
  $r = Wr @('secret', 'list', '--format', 'json', '--config', $ayar)
  if ($r.Kod -ne 0) {
    if (($r.Hata + "`n" + $r.Cikti) -match '(?i)Worker "[^"]+".* not found|workers\.api\.error\.script_not_found|\[code: 10007\]') { return $null }
    WrHata 'secret list' $r
  }
  if ($r.Cikti -notmatch '\[') { throw "secret list ciktisi JSON degil; sirlara dokunulmadan durduruldu." }
  return ,@(@(JsonCoz $r.Cikti) | ForEach-Object { $_.name } | Where-Object { $_ })
}
$sl = SirListesi
$isciVar = ($null -ne $sl)
$varOlan = @()
if ($isciVar) { $varOlan = @($sl) }
if ($isciVar) { Bilgi ('Worker mevcut; tanimli sirlar: ' + $(if ($varOlan.Count) { $varOlan -join ', ' } else { '(yok)' })) }
else { Bilgi 'Worker henuz yok: sirlar ilk dagitimdan hemen sonra yazilacak.' }
# BREVO_ANAHTARI (e-posta ile giris): bu betik URETMEZ ve SORMAZ; sahibi kendisi ekler. Yalnizca tanimli mi diye raporlanir.
$brevoVar = $varOlan -contains 'BREVO_ANAHTARI'
if ($brevoVar) { Bilgi 'E-posta ile giris: BREVO_ANAHTARI tanimli.' }
else { Bilgi 'E-posta ile giris KAPALI: BREVO_ANAHTARI tanimli degil (istege bagli; sahibi kendisi ekler, bkz. Sonraki adimlar).' }
$dosyadaki = SirDosyasiOku
$yazilacak = @{}      # ad -> deger (bellekte; ekrana basilmaz)
foreach ($ad in @('OTURUM_SIRRI', 'YONETICI_ANAHTARI', 'SIFRE_BIBERI')) {
  if ($varOlan -contains $ad) { continue }
  if ($dosyadaki.ContainsKey($ad)) { $yazilacak[$ad] = $dosyadaki[$ad]; Bilgi "  $ad : yerel dosyadaki deger kullanilacak"; continue }
  if ($Kuru) { Kuru "$ad rastgele uretilecek, wrangler'a yazilacak ve $sirDosyasi dosyasina kaydedilecek"; continue }
  $v = Rastgele 48
  SirDosyasinaYaz $ad $v      # once yedek, sonra Cloudflare: yazma yarida kalirsa deger kaybolmaz
  $yazilacak[$ad] = $v
  Bilgi "  $ad : uretildi ve yerel dosyaya kaydedildi"
}
if ($varOlan -notcontains 'TELEGRAM_BOT_TOKEN') {
  $botAdi = 'kamuilanibot'
  if ($toml -match 'TELEGRAM_BOT_ADI\s*=\s*"([^"]+)"') { $botAdi = $Matches[1] }
  if ($Kuru) { Kuru "TELEGRAM_BOT_TOKEN sahibinden istenecek: @$botAdi belirteci (bildirim botuyla ayni; BotFather > /mybots > @$botAdi > API Token). Belirteci ekrana yazma, depoya koyma." }
  else {
    Bilgi "TELEGRAM_BOT_TOKEN gerekli: @$botAdi belirteci (bildirim botuyla AYNI; bildirim-botu Worker'indaki BOT_TOKEN geri okunamaz, BotFather > /mybots > @$botAdi > API Token'dan al)."
    $tg = DuzMetin (Read-Host 'Bot belirteci (ekranda gorunmez; bos birakirsan Telegram girisi/bildirimi simdilik kapali kalir)' -AsSecureString)
    if ($tg) {
      # -cnotmatch: tr-TR kulturunde "I"/"i" iceren gecerli belirtec reddedilirdi
      if ($tg -cnotmatch '^\d+:[A-Za-z0-9_-]{30,}$') { throw 'Belirtec bicimi hatali. BotFather satirini oldugu gibi yapistir.' }
      try { $ben = Invoke-RestMethod -Uri ("https://api.telegram.org/bot$tg/getMe") -Method Get }
      catch { $Error.Clear(); throw "Telegram getMe basarisiz (belirtec gecersiz ya da iptal edilmis olabilir)." }
      if ($ben.result.username -ne $botAdi) { throw "Belirtec @$($ben.result.username) botuna ait; beklenen @$botAdi (wrangler.toml TELEGRAM_BOT_ADI)." }
      Bilgi "  Telegram botu dogrulandi: @$($ben.result.username)"
      $yazilacak['TELEGRAM_BOT_TOKEN'] = $tg
    } else { Uyari 'TELEGRAM_BOT_TOKEN verilmedi: Telegram girisi ve bildirimi kapali. Betigi sonra yeniden calistirip ekleyebilirsin.' }
  }
}
function SirlariYaz {
  # yazmadan hemen once yeniden oku: o arada tanimlanmis bir sir (ozellikle SIFRE_BIBERI) asla ezilmez
  $simdiki = @()
  if (-not $Kuru) { $l = SirListesi; if ($null -ne $l) { $simdiki = @($l) } }
  foreach ($ad in @($yazilacak.Keys)) {
    if ($simdiki -contains $ad) { Bilgi "  $ad Cloudflare'da zaten tanimli; degistirilmedi"; continue }
    if ($Kuru) { Kuru "wrangler secret put $ad"; continue }
    $p = Wr @('secret', 'put', $ad, '--config', $ayar) $yazilacak[$ad]
    if ($p.Kod -ne 0) { WrHata "secret put $ad" $p }
    Bilgi "  $ad Cloudflare'a yazildi"
  }
  $yazilacak.Clear()
}
if ($isciVar -or $Kuru) { SirlariYaz }

# ---------- 6. Dagitim ----------
Adim '6/7 Dagitim'
if ($Kuru) { Kuru 'wrangler deploy --config wrangler.toml' }
else {
  $d = Wr @('deploy', '--config', $ayar)
  if ($d.Kod -ne 0) { WrHata 'wrangler deploy' $d }
  Bilgi 'Dagitildi.'
  if (-not $isciVar) { Bilgi 'Ilk dagitim: sirlar simdi yaziliyor ...'; SirlariYaz }
}

# ---------- 7. Duman testi ----------
Adim '7/7 Duman testi'
if ($Kuru) { Kuru "GET $adres/durum (ve /giris/ayar) denenecek" }
else {
  $tamam = $false
  for ($i = 1; $i -le 8 -and -not $tamam; $i++) {
    try {
      $y = Invoke-RestMethod -Uri "$adres/durum" -Method Get -TimeoutSec 20
      $tamam = $true
      Bilgi "  /durum yanit verdi: $((($y | Get-Member -MemberType NoteProperty | Select-Object -ExpandProperty Name) -join ', '))"
    } catch { $Error.Clear(); Bilgi "  /durum henuz yanit vermiyor (deneme $i/8; yeni alan adi birkac dakika surebilir) ..."; Start-Sleep -Seconds 15 }
  }
  if (-not $tamam) { Uyari "$adres/durum yanit vermedi. Cloudflare panelinde Workers > kpss-forum > Domains bolumune ve DNS'e bak." }
  else {
    try {
      $g = Invoke-RestMethod -Uri "$adres/giris/ayar" -Method Get -TimeoutSec 20
      if (-not $g.sifre) { Uyari 'giris/ayar sifre:false: SIFRE_BIBERI tanimli degil gorunuyor.' } else { Bilgi '  /giris/ayar: rumuz+sifre uyeligi acik.' }
      if ($g.eposta) { Bilgi '  /giris/ayar: e-posta ile giris acik.' } else { Bilgi '  /giris/ayar: e-posta ile giris kapali (BREVO_ANAHTARI yok); Google ve rumuz+sifre calisir.' }
    } catch { $Error.Clear(); Uyari '/giris/ayar okunamadi.' }
  }
}

# ---------- sonraki adimlar ----------
Adim 'Sonraki adimlar'
Bilgi "1) Sir yedegi: $sirDosyasi dosyasini guvenli bir yere YEDEKLE (SIFRE_BIBERI kaybolursa tum sifreler gecersiz olur; asla degistirme)."
Bilgi '2) Analiz Worker''i (forum paneli): ayni YONETICI_ANAHTARI degerini FORUM_YONETICI_ANAHTARI olarak ver ve analizi dagit:'
Bilgi '     cd ..\analiz'
Bilgi '     npx wrangler secret put FORUM_YONETICI_ANAHTARI --config wrangler.toml     (deger: yukaridaki dosyadaki YONETICI_ANAHTARI satiri)'
Bilgi '     npx wrangler deploy --config wrangler.toml'
Bilgi '3) BotFather''da Telegram giris araci icin: /setdomain -> @kamuilanibot -> kpsstercihi.com (bir kez).'
if (-not $brevoVar) {
  Bilgi '   E-posta ile giris (istege bagli; Brevo ucretsiz plan, gunde 300 e-posta, biz 280''de dururuz): Brevo hesabinda gonderen adresi dogrula, API anahtari olustur, sonra KENDIN:'
  Bilgi '     npx wrangler secret put BREVO_ANAHTARI --config wrangler.toml     (istege bagli gonderen: wrangler.toml [vars] EPOSTA_GONDEREN, varsayilan bildirim@kpsstercihi.com)'
}
Bilgi '4) Siteyi (docs/, forum.js ?v= surumleriyle) yayina al; forum ve hesap girisi ancak o zaman sitede gorunur.'
if ($uyarilar.Count -gt 0) { Write-Host ''; Write-Host 'Uyarilar:' -ForegroundColor Yellow; $uyarilar | ForEach-Object { Write-Host (' - ' + $_) -ForegroundColor Yellow } }
if ($Kuru) { Write-Host ''; Write-Host 'Kuru calisma bitti; uzakta hicbir sey degismedi.' -ForegroundColor Yellow }
