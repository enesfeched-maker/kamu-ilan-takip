#!/data/data/com.termux/files/usr/bin/bash
# Telefonu uyanık tutarak (wake lock) 30 dakikada bir tarama yapar. Tek kopya çalışır.
# Gövde bir fonksiyonda: tarama kodu güncellerken (git reset) bu dosya değişse de çalışan döngü bozulmaz.
ana() {
  termux-wake-lock 2>/dev/null
  local kilit="$HOME/.kamu-dongu.pid"
  if [ -f "$kilit" ] && kill -0 "$(cat "$kilit")" 2>/dev/null; then
    echo "Döngü zaten çalışıyor (pid $(cat "$kilit"))."
    return 0
  fi
  echo $$ > "$kilit"
  while true; do
    bash "$HOME/kamu-ilan-takip/telefon/calistir.sh"
    sleep 1800
  done
}
ana
exit