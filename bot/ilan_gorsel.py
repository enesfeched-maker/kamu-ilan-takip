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
    from meslek_gorseli import meslekler, kutu_gorseli
    try:
        from ilan_bot import okunakli_baslik
    except ImportError:
        okunakli_baslik = lambda metin: metin
    import math
    roles = [okunakli_baslik(r) for r in meslekler(kadro)] or ['İlan ayrıntıları']
    ozet = len(roles) - 5 if len(roles) > 6 else 0
    if ozet:
        roles = roles[:5] + [f'+{ozet} kadro türü daha']
    columns = min(3, len(roles))
    rows = math.ceil(len(roles)/columns)
    rowheight = 268
    footer = 346 + rows*rowheight
    height = footer + 206
    im = Image.new('RGB', (1200, height), '#102b35')
    d = ImageDraw.Draw(im)
    accent = '#ffd0be' if rozet else '#d9f59a'
    d.rectangle((0, 0, 13, height), fill=accent)
    if logo:
        with Image.open(BytesIO(logo)) as mark:
            mark = mark.convert('RGBA')
            from PIL import ImageChops
            white=Image.new('RGBA',mark.size,'white');white.alpha_composite(mark)
            box=ImageChops.difference(white.convert('RGB'),Image.new('RGB',mark.size,'white')).getbbox()
            if box:
                mark=mark.crop(box)
            # Do not enlarge tiny directory logos: interpolation cannot restore
            # missing lettering. Verified originals can fill the full logo area.
            scale=min(1.0,228/max(mark.size))
            mark=mark.resize((max(1,round(mark.width*scale)),max(1,round(mark.height*scale))),Image.Resampling.LANCZOS)
            d.rounded_rectangle((882,36,1152,306),radius=24,fill='white')
            im.paste(mark,(1017-mark.width//2,171-mark.height//2),mark)
    titlefont=font(44,True)
    for n,line in enumerate(lines(d,kurum,titlefont,780,3)):
        d.text((52,46+n*55),line,font=titlefont,fill='white')
    if yer:
        cityfont=font(32,True)
        for n,line in enumerate(lines(d,yer,cityfont,780,2)):
            d.text((52,218+n*38),line,font=cityfont,fill='#d9f59a')
    d.text((52,309),'ALIM YAPILACAK KADROLAR',font=font(20,True),fill=accent)
    gap=16
    cellw=(1100-gap*(columns-1))//columns
    for index,role in enumerate(roles):
        x=52+(index%columns)*(cellw+gap); y=350+(index//columns)*rowheight
        d.rounded_rectangle((x,y,x+cellw,y+rowheight-16),radius=19,fill='#f3f6f1')
        art = None if ozet and index == 5 else kutu_gorseli(role, 206)
        if art is None:
            sade = font(64, True)
            d.text((x + cellw / 2, y + 85), role.split(' ')[0], font=sade, fill='#173e48', anchor='mm')
            role = role.split(' ', 1)[1]
        else:
            im.paste(art, (x + (cellw - art.width) // 2, y + (6 if art.height < art.width * 0.9 else 8)), art)
        face=font(25,True)
        for n,line in enumerate(lines(d,role,face,cellw-24,3)):
            d.text((x+(cellw-d.textlength(line,font=face))/2,y+167+n*27),line,font=face,fill='#173e48')
    d.line((52,footer+12,1152,footer+12),fill='#35515a',width=2)
    d.text((52,footer+34),'SON BAŞVURU',font=font(20,True),fill='#b6cbcc')
    for n,line in enumerate(lines(d,tarih,font(31,True),780 if rozet else 1090,2)):
        d.text((52,footer+65+n*36),line,font=font(31,True),fill='white')
    if rozet:
        d.rounded_rectangle((874,footer+40,1152,footer+107),radius=14,fill='#b93429')
        face=font(25,True);label=lines(d,rozet,face,250,1)[0]
        d.text((1013-d.textlength(label,font=face)/2,footer+60),label,font=face,fill='white')
    d.text((52,footer+151),'KPSS Tercihi',font=font(22,True),fill=accent)
    channel='kpsstercihi.com'
    channel_face=font(22,True)
    d.text((1152-d.textlength(channel,font=channel_face),footer+151),channel,font=channel_face,fill='white')
    out=BytesIO();im.save(out,format='PNG',optimize=True)
    return out.getvalue()
