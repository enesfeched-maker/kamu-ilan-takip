"""Extract labelled, source-bound excerpts and keep an unchanged public PDF copy."""
import hashlib
import io
import re
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
BASE='https://enesfeched-maker.github.io/kamu-ilan-takip/'
VERSION=4


def summarize(raw,row):
    from ek_kaynaklar import clean,norm
    pages=[]
    for page in PdfReader(io.BytesIO(raw)).pages:
        layout=page.extract_text(extraction_mode='layout') or ''
        plain=page.extract_text() or ''
        pages.append(plain if len(clean(layout))<len(clean(plain))*.6 else layout)
    rawblocks=[b for page in pages for b in re.split(r'\n\s*\n',page) if clean(b)]
    blocks=[clean(b) for b in rawblocks]
    # Keep each PDF table row/paragraph together: a degree or score must never
    # be detached from the job to which the source assigns it.
    conditions=[]
    table_blocks=set()
    for rawblock in rawblocks:
        block=clean(rawblock)
        code=re.search(r'\b((?!19\d{2}\b|20\d{2}\b)\d{4})\b',block)
        if len(block)>1600 or not any(w in norm(block) for w in ('mezun','lisans','doktora','docent')):continue
        # Rightmost text column is read vertically, not interleaved with unit,
        # job title, grade and headcount columns on every physical PDF line.
        rows=[list(re.finditer(r'\S(?:.*?\S)?(?= {3,}|$)',line)) for line in rawblock.splitlines() if line.strip()]
        anchors=[parts[-1].start() for parts in rows if len(parts)>=3 and any(w in norm(parts[-1].group()) for w in ('mezun','lisans','doktora','docent'))]
        if not anchors:continue
        start=min(anchors)
        if start<45:continue
        requirement=clean(' '.join(line[start:] for line in rawblock.splitlines()))
        if not requirement or len(requirement)>1100:continue
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
        if not any(w in n for w in ('mezun','yuksek lisans','doktora','docent','kpss','ales','yabanci dil','yasini')):
            continue
        if any(w in n for w in ('fotokopisi','transkript','istenen belgeler')):
            continue
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
    for sentence in sentences:
        n=norm(sentence)
        if 'basvur' in n and any(w in n for w in ('sahsen','posta yol','elektronik','e devlet','basvuru adresi','online')):
            if 40<len(sentence)<1000 and sentence not in application:application.append(sentence)
        if len(application)==2:break
    summary=[row['kadro'].rstrip('.').replace('ALACAK','alımı')+'.']
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
    return {'ozet':' '.join(summary),'sartlar':conditions,
            'basvuru_notu':' '.join(application[1:]) or '',
            'belge_kopyasi':BASE+relative,'belge_sha256':digest,
            'belge_aciklamasi':'SBB’den alınan ilan belgesinin değiştirilmemiş kopyasıdır. Sonradan yayımlanan düzeltmeleri kurumun duyurularından kontrol edin.',
            'sbb_detay_surumu':VERSION}


def document_url(item):
    value=item.get('belge_kopyasi','')
    return value if re.fullmatch(re.escape(BASE)+r'belgeler/sbb/[a-f0-9]{64}\.pdf',value) else None
