"""Extract labelled, source-bound excerpts and keep an unchanged public PDF copy."""
import hashlib
import io
import re
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
BASE='https://enesfeched-maker.github.io/kamu-ilan-takip/'
VERSION=6

FIIL=re.compile(r'(?:iptal\s+edil(?:miş\s*tir|di)|düzeltil(?:miş\s*tir|di)|değiştiril(?:miş\s*tir|di)|uzatıl(?:mış\s*tır|dı))')


def _katla(s):
    return s.translate(str.maketrans({'İ':'i','I':'ı'})).lower()  # length-preserving Turkish fold


def duyuru_cumlesi_bul(pages):
    """Resmi duyurunun işlem cümlesi ('... kadrosu ilanımız iptal edilmiştir.'); bulunamazsa ''.
    pages: düz extract_text() sayfa metinleri (layout modu 'edilmiş  tir' diye böler)."""
    from ek_kaynaklar import clean
    full=clean(' '.join(pages))
    for s in re.split(r'(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9])',full):
        m=FIIL.search(_katla(s))
        if m:
            s=clean(s[:m.end()])+'.'  # fiilden hemen sonra kes
            if len(s)>600:s='…'+s[-600:].split(' ',1)[-1]
            return s
    return ''


def belge_cumlesi(item):
    """Depodaki PDF kopyasından duyuru cümlesi (geriye dönük doldurma); belge yoksa None."""
    sha=str(item.get('belge_sha256') or '')
    path=ROOT/'docs'/'belgeler'/'sbb'/(sha+'.pdf')
    if not re.fullmatch(r'[a-f0-9]{64}',sha) or not path.exists():return None
    return duyuru_cumlesi_bul([p.extract_text() or '' for p in PdfReader(str(path)).pages])


def summarize(raw,row):
    from ek_kaynaklar import clean,norm
    pages=[]
    plain_pages=[]
    for page in PdfReader(io.BytesIO(raw)).pages:
        layout=page.extract_text(extraction_mode='layout') or ''
        plain=page.extract_text() or ''
        plain_pages.append(plain)
        pages.append(plain if len(clean(layout))<len(clean(plain))*.6 else layout)
    rawblocks=[b for page in pages for b in re.split(r'\n\s*\n',page) if clean(b)]
    blocks=[clean(b) for b in rawblocks]
    # Numbered eligibility lists often have no blank lines between bullets.
    for page in pages:
        bullets=re.split(r'\n\s*(?=(?:[-•]|[a-zçğıöşü]\)|\d{1,2}[)\-])\s)',page)
        if len(bullets)>1:
            blocks.extend(clean(b) for b in bullets[1:] if 40<len(clean(b))<700)
    # Keep each PDF table row/paragraph together: a degree or score must never
    # be detached from the job to which the source assigns it.
    conditions=[]
    table_blocks=set()
    for rawblock in rawblocks:
        block=clean(rawblock)
        code=re.search(r'^\s*((?!19\d{2}\b|20\d{2}\b)\d{4})\s{3,}',rawblock,re.M)
        if not code:continue
        if len(block)>1600 or not any(w in norm(block) for w in ('mezun','lisans','doktora','docent')):continue
        # Rightmost text column is read vertically, not interleaved with unit,
        # job title, grade and headcount columns on every physical PDF line.
        rows=[list(re.finditer(r'\S(?:.*?\S)?(?= {3,}|$)',line)) for line in rawblock.splitlines() if line.strip()]
        anchors=[parts[-1].start() for parts in rows if len(parts)>=3 and any(w in norm(parts[-1].group()) for w in ('mezun','lisans','doktora','docent'))]
        # A wrapped requirement can start on a line above the numbered row.
        # Its indentation identifies the full column even with justified gaps.
        anchors.extend(len(line)-len(line.lstrip()) for line in rawblock.splitlines()
                       if len(line)-len(line.lstrip())>=45 and re.match(r'(?:Doçentli|Lisans|Yüksek|Doktora|Mezun)',line.lstrip(),re.I))
        if not anchors:continue
        start=min(anchors)
        if start<45:continue
        if any(len(line)>start and not line[start-1].isspace() and not line[start].isspace() for line in rawblock.splitlines()):continue
        requirement=clean(' '.join(line[start:] for line in rawblock.splitlines()))
        if not 40<len(requirement)<1100:continue
        left=clean(' '.join(line[:start] for line in rawblock.splitlines()))
        nleft=norm(left)
        role=next((title for needle,title in [('arastirma','Araştırma Görevlisi'),('profesor','Profesör'),('docent','Doçent'),('uyes','Öğretim Üyesi'),('gorevl','Öğretim Görevlisi')] if needle in nleft),'Kadro özel şartları')
        if not code and role=='Kadro özel şartları':continue
        conditions.append({'kadro':('İlan no '+code.group(1)+' · ' if code else '')+role,'metin':requirement})
        table_blocks.add(block)
    candidates=[]
    for block in blocks:
        if block in table_blocks:continue
        n=norm(block)
        if not any(w in n for w in ('mezun','lisans','doktora','docent','kpss','ales','yabanci dil','yasini')):
            continue
        if any(w in n for w in ('fotokopisi','transkript','istenen belgeler','mezuniyet belgelerinde','notunun hesaplanmas','basvuru sonuclari')):
            continue
        if not re.search(r'(?:[.,;:)]|olmak)$',block):continue
        if not any(w in n for w in ('olmak','aran','doldurmamis','puan al','mezun olmayan','basvurabil')):continue
        special=bool(re.search(r'\b(?!19\d{2}\b|20\d{2}\b)\d{4}\b',block) and ('mezun' in n or 'yuksek lisans' in n) and len(block)<1800)
        candidates.append((0 if special else 1,block))
    for _,block in sorted(candidates,key=lambda x:x[0]):
        if len(conditions)>=6:break
        # Avoid publishing a whole page under a misleading "short summary".
        if len(block)>700:continue
        if block in [s['metin'] for s in conditions]:continue
        code=re.search(r'\b((?!19\d{2}\b|20\d{2}\b)\d{4})\b',block)
        label=('İlan no '+code.group(1)+' · kadro ve özel şartlar') if code and len(block)<1000 else 'Belgede belirtilen koşullar'
        conditions.append({'kadro':label,'metin':block})
    application=[]
    full=clean(' '.join(pages))
    # Complete sentences retain exclusions such as "posta kabul edilmez".
    sentences=re.split(r'(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9])',full)
    if not conditions:
        for sentence in sentences:
            n=norm(sentence)
            if 40<len(sentence)<600 and 'mezun' in n and any(w in n for w in ('olmak','aran')) and not any(w in n for w in ('fotokopi','transkript','istenen belgeler')):
                conditions.append({'kadro':'Belgedeki kadro koşullarından alıntı','metin':sentence})
            if len(conditions)==3:break
    for sentence in sentences:
        n=norm(sentence)
        if len(conditions)<6 and len(sentence)<450 and 'en az' in n and any(w in n for w in ('ales','kpss','yabanci dil')):
            conditions.append({'kadro':'Sınav puanı koşulu · kadroya göre muafiyetler için belgeyi inceleyin','metin':sentence})
    # Prefer complete short paragraphs/bullets: initials such as T.C. can split
    # a valid application sentence. Placement and appeals are later procedures.
    application_candidates=[]
    for sentence in blocks+sentences:
        n=norm(sentence)
        if any(w in n for w in ('sinavda basarili','sinav sonuclari','itiraz','ilce) tercihi','yedek aday','atamaya hak','sinava giris belgesi','mezuniyet belgelerinde')):
            continue
        if 'basvur' in n and any(w in n for w in ('sahsen','posta yol','elektronik','basvuru adresi','online','e devlet uzerinden')):
            if 40<len(sentence)<700:
                priority=0 if 'basvurularini' in n or 'basvurmalari' in n else 1
                application_candidates.append((priority,sentence))
    for _,sentence in sorted(application_candidates,key=lambda x:x[0]):
        if not any(sentence in a or a in sentence for a in application):application.append(sentence)
        if len(application)==2:break
    dates=next((b for b in blocks if 40<len(b)<650 and 'basvur' in norm(b) and 'tarihleri arasinda' in norm(b)
                and not any(w in norm(b) for w in ('ucret','sonuc','itiraz','tercih'))),None)
    if dates and application and dates not in application:
        application=application[:1]+[dates]
    # PDF'nin TAM metninden il, gerçek kadro, puan türü, öğrenim, KPSS durumu (güvenilmezse alan hiç yazılmaz).
    try:
        from belge_alanlari import alanlar as belge_alanlari
        turetilen=belge_alanlari(plain_pages,row) if not row.get('duyuru_turu') else {}
    except Exception:
        turetilen={}
    summary=[(turetilen.get('kadro') or row['kadro']).rstrip('.').replace('ALACAK','alımı')+'.']
    if row.get('son_tarih'):summary.append('Son başvuru: '+'.'.join(reversed(row['son_tarih'].split('-')))+'.')
    if application:summary.append(application[0])
    if conditions:
        summary.append('Kadroya göre değişen eğitim ve deneyim koşulları aşağıda ayrı olarak gösterilmiştir.')
    if not conditions:
        # No guessed requirements when a scanned document or table is unreadable.
        summary.append('Özel şartlar aşağıdaki ilan belgesinde yer alıyor.')
    digest=hashlib.sha256(raw).hexdigest()
    relative='belgeler/sbb/'+digest+'.pdf'
    target=ROOT/'docs'/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():target.write_bytes(raw)
    result={'ozet':' '.join(summary),'sartlar':conditions,
            'basvuru_notu':' '.join(application[1:]) or '',
            'belge_kopyasi':BASE+relative,'belge_sha256':digest,
            'belge_aciklamasi':'SBB’den alınan ilan belgesinin değiştirilmemiş kopyasıdır. Sonradan yayımlanan düzeltmeleri kurumun duyurularından kontrol edin.',
            'sbb_detay_surumu':VERSION}
    result.update(turetilen)
    if row.get('duyuru_turu'):
        result['duyuru_cumlesi']=duyuru_cumlesi_bul(plain_pages)
        if result['duyuru_cumlesi']:result['ozet']=result['duyuru_cumlesi']
    return result


def belge_sayfalari(item, en_buyuk=4_000_000):
    """Depodaki PDF kopyasının düz sayfa metinleri; kopya yoksa/çok büyükse None."""
    sha=str(item.get('belge_sha256') or '')
    path=ROOT/'docs'/'belgeler'/'sbb'/(sha+'.pdf')
    if not re.fullmatch(r'[a-f0-9]{64}',sha) or not path.exists() or path.stat().st_size>en_buyuk:return None
    return [p.extract_text() or '' for p in PdfReader(str(path)).pages]


def document_url(item):
    value=item.get('belge_kopyasi','')
    return value if re.fullmatch(re.escape(BASE)+r'belgeler/sbb/[a-f0-9]{64}\.pdf',value) else None
