"""Eski telefon uyumluluğu: docs/ altındaki kendi yazdığımız .js dosyaları ES2017 söz diziminde kalmalı.

Eski tarayıcılarda (Chrome 61+, Safari 11) `?.`, `??`, `catch {`, nesne yayılımı gibi söz dizimleri tüm dosyayı
çalıştırmaz (portal.js / puanlar.js bir kez bu yüzden hiç açılmadı). Bu test düzenli ifade tabanlı kaba bir
denetimdir: dize ve yorumları atar, kalanda yasak kalıpları arar. Kesin denetim için:
    npx acorn@8 --ecma2017 --silent docs/portal.js
"""
import re
import unittest
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / 'docs'

# Üçüncü taraf / sıkıştırılmış dosyalar denetlenmez.
def _ucuncu_taraf(p):
    return p.name.endswith('.min.js')

KOD_YASAK = [
    (re.compile(r'\?\.(?!\d)'), 'isteğe bağlı zincir (?.)'),
    (re.compile(r'\?\?'), 'null birleştirme (??, ??=)'),
    (re.compile(r'\|\|=|&&='), 'mantıksal atama (||=, &&=)'),
    (re.compile(r'\b\d[\d_]*\d_\d|\b\d_\d'), 'sayı ayırıcı (1_000)'),
    (re.compile(r'\bcatch\s*\{'), 'isteğe bağlı catch bağı (catch {)'),
    (re.compile(r'\.at\('), '.at()'),
    (re.compile(r'\breplaceAll\s*\('), 'replaceAll'),
    (re.compile(r'\bObject\.hasOwn\s*\('), 'Object.hasOwn'),
    (re.compile(r'\bstructuredClone\s*\('), 'structuredClone'),
    (re.compile(r'\{\s*\.\.\.'), 'nesne yayılımı ({...x}); Object.assign kullan'),
    (re.compile(r'\bclass\b[^{;]*\{[^{}]*?\n\s*#\w'), 'sınıf özel alanı (#x)'),
]
REGEX_YASAK = [
    (re.compile(r'\(\?<[=!]'), 'regex lookbehind'),
    (re.compile(r'\(\?<\w+>'), 'regex adlandırılmış grup'),
    (re.compile(r'\\[pP]\{'), 'regex \\p{...} özellik kaçışı'),
]
# Bu simgelerden sonra gelen "/" bir bölme değil regex başlangıcıdır.
REGEX_ONCESI = set('(,=:[!&|?{};+-*%<>~^') | {''}


def temizle(kaynak):
    """(dize/yorum/regex atılmış kod, regex gövdeleri). Kaba bir tarayıcıdır; yeterlidir."""
    kod, regexler = [], []
    i, n, son = 0, len(kaynak), ''
    while i < n:
        c = kaynak[i]
        iki = kaynak[i:i + 2]
        if iki == '//':
            j = kaynak.find('\n', i)
            i = n if j < 0 else j
            continue
        if iki == '/*':
            j = kaynak.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in '\'"`':
            j = i + 1
            while j < n and kaynak[j] != c:
                j += 2 if kaynak[j] == '\\' else 1
            kod.append(' ')
            i, son = j + 1, 'x'
            continue
        if c == '/' and son in REGEX_ONCESI | set('return'):
            j, sinif = i + 1, False
            while j < n and (kaynak[j] != '/' or sinif) and kaynak[j] != '\n':
                if kaynak[j] == '\\':
                    j += 1
                elif kaynak[j] == '[':
                    sinif = True
                elif kaynak[j] == ']':
                    sinif = False
                j += 1
            regexler.append(kaynak[i + 1:j])
            kod.append(' ')
            i, son = j + 1, 'x'
            continue
        kod.append(c)
        if not c.isspace():
            son = c
        i += 1
    return ''.join(kod), regexler


def ihlaller(kaynak):
    kod, regexler = temizle(kaynak)
    bulunan = []
    for desen, ad in KOD_YASAK:
        for m in desen.finditer(kod):
            bulunan.append((kod.count('\n', 0, m.start()) + 1, ad))
    for r in regexler:
        for desen, ad in REGEX_YASAK:
            if desen.search(r):
                bulunan.append((0, ad + ' /' + r[:40] + '/'))
    return bulunan


class JsUyumlulukTest(unittest.TestCase):
    def test_denetim_yasak_kaliplari_yakalar(self):
        for parca in ('a?.b', 'a ?? b', 'a ||= 1', 'x = 1_000', 'try{}catch{}', 'x.at(-1)', "s.replaceAll('a','b')",
                      'Object.hasOwn(o,k)', 'structuredClone(o)', 'f({...o})', 'var r=/(?<=a)b/', 'var r=/(?<ad>a)/',
                      'var r=/\\p{L}/u'):
            with self.subTest(parca=parca):
                self.assertTrue(ihlaller(parca), parca)

    def test_denetim_zararsiz_kodu_gecirir(self):
        parca = ("var s='a?.b ?? c'; // x ?? y\n/* catch { */ var r=/\\?.*$/; var q = a ? .5 : 1;\n"
                 "try{}catch(e){} var t=`${a}??`; var u=b/2/3;")
        self.assertEqual(ihlaller(parca), [])

    def test_site_js_dosyalari_es2017(self):
        dosyalar = [p for p in sorted(DOCS.rglob('*.js')) if not _ucuncu_taraf(p)]
        self.assertTrue(dosyalar, 'docs/ altında .js bulunamadı')
        sorunlar = []
        for p in dosyalar:
            for satir, ad in ihlaller(p.read_text(encoding='utf-8')):
                sorunlar.append(f'{p.relative_to(DOCS.parent).as_posix()}:{satir}: {ad}')
        self.assertEqual(sorunlar, [], 'ES2017 sonrası söz dizimi eski telefonlarda dosyayı çalıştırmaz:\n' + '\n'.join(sorunlar[:30]))


if __name__ == '__main__':
    unittest.main()
