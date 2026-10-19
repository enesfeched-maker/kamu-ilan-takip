"""İlan sayfasına "Bu ilan için bilmen gerekenler" bölümü (19 Ekim 2026).

ÖSYM taban puanı eşleşmeyen (kurumun kendi sınavıyla alım yapan) ilanlarda da sayfaya özgü bilgi olsun diye:
ilanın kendi verisinden başvuru süresi, kapanış saati, puan türü ve öğrenim düzeyi; ilanın türüne göre kısa bir
açıklama ve ilgili rehber yazısına bağlantı. Açıklamalar "genellikle" diye yazılır; kesin usul her zaman ilan metnidir."""
import re
from datetime import datetime
from html import escape as esc

from siniflandir import kucuk

AYLAR = ('Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık')
DUZEY = {'lisans': 'Lisans', 'onlisans': 'Önlisans', 'ortaogretim': 'Ortaöğretim (lise)'}
REHBER_ADI = {
    'sozlesmeli-bilisim-personeli': 'Sözleşmeli bilişim personeli alımları',
    'ekpss-engelli-memur-alimi': 'EKPSS ve engelli kadroları',
    'kamu-isci-alimi': 'Kamu işçi alımları',
    'belediye-memur-alimi': 'Belediye memur alımları',
    'merkezi-yerlestirme-ve-kurum-ilanlari': 'Merkezi yerleştirme ve kurum ilanları',
    'sozlesmeli-personel-4b': 'Sözleşmeli personel (4/B)',
    'kariyer-kapisi-basvuru': 'Kariyer Kapısı\'ndan başvuru',
    'basvuru-belgeleri-ve-hatalar': 'Başvuru belgeleri ve sık yapılan hatalar',
}


def _zaman(deger):
    try:
        return datetime.fromisoformat(deger) if deger else None
    except ValueError:
        return None


def _tarih(z):
    return f'{z.day} {AYLAR[z.month - 1]} {z.year}'


def tur_bilgisi(item):
    """(açıklama, rehber slug) ya da (None, None)."""
    metin = kucuk(' '.join(str(item.get(a) or '') for a in ('baslik', 'kadro', 'ilan_turu', 'kurum')))
    kat = item.get('kategori')
    if kat == 'bilisim' or 'bilişim personeli' in metin:
        return ('Sözleşmeli bilişim personeli alımlarında sözlü sınava çağrı sıralaması genellikle KPSS P3 puanının %70\'i '
                'ile yabancı dil puanının %30\'u toplanarak yapılır; mesleki tecrübe süresi ücret tavanını (2, 3 ya da 4 kat) belirler.',
                'sozlesmeli-bilisim-personeli')
    if 'engelli' in metin:
        return ('Engelli kadrolarında en az %40 engelli olduğunu gösteren sağlık kurulu raporu istenir; memur kadrolarında '
                'EKPSS puanı, işçi kadrolarında İŞKUR üzerinden başvuru ve kura yaygındır.', 'ekpss-engelli-memur-alimi')
    if kat == 'isci' or 'işçi' in metin:
        return ('Kamu işçi alımlarında başvuru genellikle İŞKUR üzerinden yapılır; çoğu ilanda KPSS aranmaz, adaylar noter '
                'kurası ya da sözlü sınavla belirlenir. Kuruma doğrudan yapılan başvurular çoğu zaman geçersiz sayılır.',
                'kamu-isci-alimi')
    if kat == 'belediye':
        ek = ''
        if 'itfaiye' in metin:
            ek = ' İtfaiye eri kadrolarında boy-kilo ölçüleri, yaş sınırı ve sürücü belgesi şartı sık aranır.'
        elif 'zabıta' in metin:
            ek = ' Zabıta memuru kadrolarında boy-kilo ölçüleri ve yaş sınırı sık görülür.'
        return ('Belediye ilanlarında başvuru çoğunlukla şahsen, posta ya da e-posta ile yapılır; adaylar KPSS puan sırasına '
                'göre sözlü ya da uygulamalı sınava çağrılır.' + ek, 'belediye-memur-alimi')
    if any(k in metin for k in ('uzman yardımcısı', 'müfettiş yardımcısı', 'denetçi yardımcısı', 'murakıp yardımcısı',
                                'kariyer meslek')):
        return ('Uzman ve müfettiş yardımcılığı ilanlarında KPSS A grubu puanına göre sınırlı sayıda aday giriş sınavına '
                'çağrılır; yazılı ve sözlü sınavın ardından genellikle üç yıllık yetişme dönemi ve yeterlik sınavı gelir.',
                'merkezi-yerlestirme-ve-kurum-ilanlari')
    if any(k in metin for k in ('subay', 'astsubay', 'askeri personel', 'uzman erbaş', 'sözleşmeli er')):
        return ('Askerî personel temininde başvurular genellikle ilgili kuvvetin ya da MSB\'nin personel temin sayfasından '
                'yapılır; ön değerlendirme, sağlık, fiziki yeterlilik ve mülakat aşamaları bulunur.', None)
    if 'sözleşmeli' in metin:
        return ('Sözleşmeli (4/B) personel alımlarında yerleştirme genellikle KPSS puan sırasıyla ya da sözlü sınavla yapılır; '
                'hizmet sözleşmesinin koşulları ilan metninde yer alır.', 'sozlesmeli-personel-4b')
    return None, None


def maddeler(item):
    sonuc = []
    bas, son = _zaman(item.get('baslangic_zaman')), _zaman(item.get('son_zaman'))
    if bas and son and son >= bas:
        gun = (son.date() - bas.date()).days + 1
        aralik = (f'{bas.day} – {_tarih(son)}' if (bas.year, bas.month) == (son.year, son.month)
                  else f'{_tarih(bas)} – {_tarih(son)}')
        sonuc.append(f'Başvuru dönemi: {aralik} ({gun} gün).')
    if son and (son.hour, son.minute) not in ((23, 59), (0, 0)):
        sonuc.append(f'Son gün başvurular saat {son:%H.%M}\'de kapanıyor; son saate bırakmamak iyi olur.')
    if item.get('kpss') == 'kpsssiz':
        sonuc.append('Bu ilanda KPSS şartı aranmıyor.')
    elif item.get('kpss') == 'kpss' and item.get('puan_turleri'):
        sonuc.append(f'İstenen KPSS puan türü: {", ".join(item["puan_turleri"])}.')
    duzeyler = [DUZEY[d] for d in item.get('ogrenim') or [] if d in DUZEY]
    if duzeyler:
        sonuc.append(f'Başvurabilecek öğrenim düzeyi: {", ".join(duzeyler)}.')
    kanal = basvuru_kanali(item)
    if kanal == 'iskur':
        sonuc.append('Başvuru İŞKUR üzerinden yapılır (İŞKUR hesabı ya da hizmet merkezleri).')
    elif kanal == 'kariyer':
        sonuc.append('Başvuru e-Devlet şifresiyle Kariyer Kapısı üzerinden yapılır.')
    return sonuc


def basvuru_kanali(item):
    """İlan metni açıkça söylüyorsa: 'iskur' ya da 'kariyer'; emin değilsek None (yanlış yönlendirmemek için)."""
    metin = kucuk(' '.join(str(item.get(a) or '') for a in ('ozet', 'basvuru_notu', 'duyuru_cumlesi')))
    # Kaynağın iskur.gov.tr olması yetmez: İŞKUR memur/belediye ilanlarının belgesini de yayımlar (20 Ekim 2026).
    if re.search(r'işkur[^.]{0,60}(?:başvur|müracaat)|(?:başvur|müracaat)[^.]{0,60}(?:işkur|iş kurumu)', metin):
        return 'iskur'
    if 'kariyer kapısı' in metin or 'kariyerkapisi' in metin:
        return 'kariyer'
    return None


def bolum_html(item, kok='../../'):
    if item.get('duyuru_turu') or item.get('iptal_edildi'):
        return ''
    satirlar = maddeler(item)
    aciklama, slug = tur_bilgisi(item)
    if len(satirlar) < 2 and not aciklama:
        return ''
    rehberler = [s for s in (slug, 'kariyer-kapisi-basvuru' if basvuru_kanali(item) == 'kariyer' else None,
                             'basvuru-belgeleri-ve-hatalar') if s]
    baglantilar = ' · '.join(f'<a class="yazi-link" href="{kok}rehber/{s}/">{esc(REHBER_ADI[s])}</a>'
                             for s in dict.fromkeys(rehberler))
    return ('<section class="ilan-rehber"><h2>Başvuru hakkında ayrıntılar</h2>'
            + (f'<ul>{"".join(f"<li>{esc(m)}</li>" for m in satirlar)}</ul>' if satirlar else '')
            + (f'<p>{esc(aciklama)}</p>' if aciklama else '')
            + '<p class="muted">Kesin şartlar ve değerlendirme usulü resmî ilan metnindedir.</p>'
            + f'<p>İlgili rehber: {baglantilar}</p></section>')
