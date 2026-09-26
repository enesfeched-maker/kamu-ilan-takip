"""Deterministic information cards; only verified listing fields, no external images."""
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def font(size, bold=False):
    names = [
        'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    raise RuntimeError('Türkçe destekli Arial veya DejaVu Sans yazı tipi bulunamadı.')


def lines(draw, text, face, width, maximum):
    result, current = [], ''
    # Character wrapping also handles a malformed source with no spaces.
    for word in text.split():
        candidate = (current + ' ' + word).strip()
        if draw.textlength(candidate, font=face) <= width:
            current = candidate
        else:
            if current:
                result.append(current)
            current = word
            while draw.textlength(current, font=face) > width:
                low, high = 1, len(current)
                while low < high:
                    middle = (low + high + 1) // 2
                    if draw.textlength(current[:middle], font=face) <= width:
                        low = middle
                    else:
                        high = middle - 1
                cut = low
                result.append(current[:cut])
                current = current[cut:]
    if current:
        result.append(current)
    if len(result) > maximum:
        result = result[:maximum]
        while result[-1] and draw.textlength(result[-1] + '…', font=face) > width:
            result[-1] = result[-1][:-1]
        result[-1] += '…'
    return result


def gorsel_olustur(kurum, kadro, yer, tarih, rozet='', kaynak='Kariyer Kapısı', logo=None):
    im = Image.new('RGB', (1200, 760), '#102b35')
    d = ImageDraw.Draw(im)
    accent = '#ffd0be' if rozet else '#d9f59a'
    d.rectangle((0, 0, 16, 760), fill=accent)
    if logo:
        with Image.open(BytesIO(logo)) as mark:
            mark=mark.convert('RGBA')
            mark.thumbnail((136,136),Image.Resampling.LANCZOS)
            d.rounded_rectangle((956,62,1136,242),radius=20,fill='white')
            im.paste(mark,(1046-mark.width//2,152-mark.height//2),mark)
    titlefont = font(49, True)
    y = 66
    for line in lines(d, kurum, titlefont, 830, 3):
        d.text((64, y), line, font=titlefont, fill='#ffffff')
        y += 60
    d.line((64, 284, 1136, 284), fill='#35515a', width=2)
    bodyfont = font(38, True)
    for n, line in enumerate(lines(d, kadro, bodyfont, 1060, 2)):
        d.text((64, 313 + n*48), line, font=bodyfont, fill=accent)
    if yer:
        d.text((64, 431), lines(d, yer, font(30), 1050, 1)[0], font=font(30), fill='#c9dadc')
    d.rounded_rectangle((64, 514, 1136, 665), radius=20, fill='#f2f6f0')
    d.text((92, 534), 'SON BAŞVURU', font=font(22, True), fill='#526463')
    for n, line in enumerate(lines(d, tarih, font(35, True), 660, 2)):
        d.text((92, 571+n*39), line, font=font(35, True), fill='#163b40')
    if rozet:
        d.rounded_rectangle((836, 553, 1108, 624), radius=14, fill='#b93429')
        face = font(26, True)
        label = lines(d, rozet, face, 244, 1)[0]
        d.text((972-d.textlength(label, font=face)/2, 574), label, font=face, fill='white')
    d.text((64, 704), 'Kamu İlan Takip · Bağımsız ilan rehberi', font=font(21), fill='#adc5c7')
    out = BytesIO()
    im.save(out, format='PNG', optimize=True)
    return out.getvalue()
