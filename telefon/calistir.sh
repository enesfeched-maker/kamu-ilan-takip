#!/data/data/com.termux/files/usr/bin/bash
# Tek tarama: kodu GitHub main ile eşitler, yerel tarayıcıyı çalıştırır, günlüğe yazar (son 2000 satır tutulur).
KLASOR="$HOME/kamu-ilan-takip"
GUNLUK="$HOME/kamu-ilan-tarama.log"
export KAMU_GITHUB_TOKEN="$(cat "$HOME/.kamu-github-token" 2>/dev/null)"
export PATH="/data/data/com.termux/files/usr/bin:$PATH"
cd "$KLASOR" || exit 1
{
  echo "=== $(date -Iseconds) telefon"
  timeout 1500 python bot/yerel_baslat.py
  echo "çıkış: $?"
} >> "$GUNLUK" 2>&1
tail -n 2000 "$GUNLUK" > "$GUNLUK.tmp" && mv "$GUNLUK.tmp" "$GUNLUK"
