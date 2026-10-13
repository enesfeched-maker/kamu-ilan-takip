#!/data/data/com.termux/files/usr/bin/bash
# KPSS Tercihi — Android (Termux) yerel tarayıcı kurulumu.
# SBB, ÇŞB ve Kariyer Kapısı ayrıntıları yalnız Türkiye'den okunabildiği için bu tarama telefondan yapılır.
# Kullanım (Termux'ta):  curl -fsSL https://raw.githubusercontent.com/enesfeched-maker/kamu-ilan-takip/main/telefon/kurulum.sh | bash
set -e
KLASOR="$HOME/kamu-ilan-takip"
JETON="$HOME/.kamu-github-token"

echo "1/5 Paketler kuruluyor (birkaç dakika sürebilir)..."
yes | pkg update -y >/dev/null 2>&1 || true
pkg install -y python git python-pillow python-cryptography cronie termux-services >/dev/null
# cryptography telefonda derlenemez (Rust ister): hazır Termux paketinden gelir, pip yeniden kurmaya çalışmasın.

echo "2/5 Python kütüphaneleri kuruluyor..."
pip install -q beautifulsoup4==4.13.5 pypdf==6.0.0
# PDF tablo okuyucu isteğe bağlı: kurulamazsa tarama tablosuz devam eder.
pip install -q charset-normalizer pdfminer.six 2>/dev/null || true
pip install -q --no-deps pdfplumber==0.11.7 2>/dev/null || true

echo "3/5 Kod indiriliyor..."
if [ -d "$KLASOR/.git" ]; then
  git -C "$KLASOR" fetch -q origin main && git -C "$KLASOR" reset -q --hard origin/main
else
  git clone -q --depth 1 https://github.com/enesfeched-maker/kamu-ilan-takip.git "$KLASOR"
fi

if [ ! -s "$JETON" ]; then
  echo "4/5 GitHub anahtarını yapıştır (ekranda görünmez), sonra Enter:"
  read -rs ANAHTAR </dev/tty
  echo
  [ -n "$ANAHTAR" ] || { echo "Anahtar boş; kurulum durdu."; exit 1; }
  umask 077
  printf '%s' "$ANAHTAR" > "$JETON"
  chmod 600 "$JETON"
else
  echo "4/5 GitHub anahtarı zaten kayıtlı."
fi

echo "5/5 30 dakikada bir çalışma ayarlanıyor..."
chmod +x "$KLASOR/telefon/calistir.sh"
( crontab -l 2>/dev/null | grep -v 'telefon/calistir.sh' ; echo "6,36 * * * * $KLASOR/telefon/calistir.sh" ) | crontab -
sv-enable crond >/dev/null 2>&1 || true
mkdir -p "$HOME/.termux/boot"
cat > "$HOME/.termux/boot/kamu-ilan.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
. $PREFIX/etc/profile
sv-enable crond
EOF
chmod +x "$HOME/.termux/boot/kamu-ilan.sh"
termux-wake-lock || true

echo "İlk tarama deneniyor..."
"$KLASOR/telefon/calistir.sh" && tail -n 6 "$HOME/kamu-ilan-tarama.log"
echo "Kurulum tamam. Termux'u kapatabilirsin; bildirimde 'wake lock' yazısı kalmalı."
