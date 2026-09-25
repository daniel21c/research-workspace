# -*- coding: utf-8 -*-
"""장애인복지시설(보건복지부 「장애인복지시설 일람표」 PDF) 2020_01(2020년판)·2025_01(2025년판=2024.12월말 기준). 연간 명부 → grade C.
PDF 글자 좌표(pdfplumber)로 표를 복원한다: 머리글 낱말 위치로 열을 정하고, 일련번호 줄을 기준으로 위아래 ±11pt 안 낱말을 한 행으로 묶는다.
2020년판은 기준일이 표지에 없다(2020.7 발간). 수록 시설의 설치신고일 최댓값으로 기준 시점을 추정해 qa에 남긴다."""
import sys, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import mb
import pandas as pd
import pdfplumber

RAW = HERE / 'raw'
TYP = '장애인복지시설'
B = 'https://www.mohw.go.kr/boardDownload.es'
SRC = {
    '2020_01': dict(file='mohw_장애인복지시설일람표_2020.pdf', bid='0021', list_no='359053', seq='1', ref='2019-12-31',
                    ds='2020년 장애인 복지시설 일람표(2020.7 발간, 기준일 미표기)'),
    '2025_01': dict(file='mohw_장애인복지시설일람표_2025_202412말.pdf', bid='0021', list_no='1485440', seq='1', ref='2024-12-31',
                    ds='2025년 장애인복지시설 일람표(2024.12월말 기준)'),
}
SIDO = ['서울특별시', '부산광역시', '대구광역시', '인천광역시', '광주광역시', '대전광역시', '울산광역시', '세종특별자치시', '경기도', '강원도',
        '강원특별자치도', '충청북도', '충청남도', '전라북도', '전북특별자치도', '전라남도', '경상북도', '경상남도', '제주특별자치도']
SECTION_RE = re.compile(r'^([2-5])\s*\.?\s*장애인\s*(거주시설|지역사회\s*재활시설|직업재활시설|의료재활시설)')
SECTION = {'2': '장애인 거주시설', '3': '장애인 지역사회재활시설', '4': '장애인 직업재활시설', '5': '장애인 의료재활시설'}
HEAD_RE = re.compile(r'^(∙|❚|▮)?\s*(\d\)\s*)?([가-힣·･ ()]+?(?:시설|센터|복지관|가정|도서관|작업장|사업장))\s*$')
PHONE_RE = re.compile(r'^\(?0\d{1,3}\)?[-.)]?\s?\d{3,4}[-.]\d{4}(~\d+)?$')
DATE_RE = re.compile(r'^\d{4}[-.]\d{1,2}[-.]\d{1,2}\.?$')
NUM_RE = re.compile(r'^[\d,]+$')


def download():
    for s in SRC.values():
        mb.fetch(B, RAW / s['file'], params=dict(bid=s['bid'], list_no=s['list_no'], seq=s['seq']), ref_date=s['ref'], note=s['ds'])


def lines_of(words):
    L = []
    for w in sorted(words, key=lambda w: (w['top'], w['x0'])):
        if L and abs(L[-1]['top'] - w['top']) <= 2:
            L[-1]['words'].append(w)
        else:
            L.append(dict(top=w['top'], words=[w]))
    for l in L:
        l['words'].sort(key=lambda w: w['x0'])
        l['text'] = ' '.join(w['text'] for w in l['words'])
        l['x0'] = l['words'][0]['x0']
    return L


def header_cols(L, hi):
    """머리글 블록(시설명 줄 ±15pt)에서 열 중심 좌표."""
    t0 = L[hi]['top']
    ws = [w for l in L if t0 - 15 <= l['top'] <= t0 + 17 for w in l['words']]
    cen = lambda w: (w['x0'] + w['x1']) / 2
    cols = {}
    labels = []
    nums = []
    for w in ws:
        t = w['text']
        key = {'일련': 'no', '시군구': 'gu', '관할': 'gu', '법인명': 'corp', '시설명': 'name', '시설장': 'head', '주소': 'addr', '소재지': 'addr',
               '시설소재지': 'addr', '전화번호': 'phone', '설치신고일': 'date', '설치일': 'date'}.get(t)
        if key and key not in cols:
            cols[key] = cen(w)
        if t in ('정원', '현원'):
            nums.append(w)
        if t in ('입소자', '종사자', '장애인', '근로'):
            labels.append(w)
    numcols = []
    for w in sorted(nums, key=lambda w: w['x0']):
        above = [l for l in labels if l['top'] < w['top'] and l['x0'] - 25 <= cen(w) <= l['x1'] + 25]
        grp = min(above, key=lambda l: abs((l['x0'] + l['x1']) / 2 - cen(w)))['text'] if above else ''
        numcols.append((cen(w), grp, w['text']))
    bottom = max(w['bottom'] for w in ws)
    return cols, numcols, bottom


def assign(words, cols, numcols):
    cen = lambda w: (w['x0'] + w['x1']) / 2
    textcols = {k: v for k, v in cols.items() if k in ('gu', 'corp', 'name', 'head', 'addr')}
    nzone = (min(c for c, _, _ in numcols) - 14, max(c for c, _, _ in numcols) + 14) if numcols else None
    out = {k: [] for k in list(textcols) + ['date', 'phone']}
    nums = {}
    for w in words:
        t = w['text']; c = cen(w)
        if 'no' in cols and abs(c - cols['no']) < 10 and re.fullmatch(r'\d+', t):
            continue
        if PHONE_RE.match(t) or re.fullmatch(r'\(?FAX\)?', t):
            out['phone'].append(w); continue
        if DATE_RE.match(t):
            out['date'].append(w); continue
        if NUM_RE.match(t) and nzone and nzone[0] <= c <= nzone[1]:
            j = min(range(len(numcols)), key=lambda j: abs(numcols[j][0] - c))
            nums.setdefault(j, []).append(t); continue
        if not textcols:
            continue
        k = min(textcols, key=lambda k: abs(textcols[k] - c))
        out[k].append(w)
    txt = {k: ' '.join(w['text'] for w in sorted(v, key=lambda w: (round(w['top']), w['x0']))) for k, v in out.items()}
    return txt, nums


def parse(snap):
    s = SRC[snap]
    pdf = pdfplumber.open(RAW / s['file'])
    st = dict(sido=None, section=None, major=None, minor=None)
    cols = None; numcols = []
    recs = []; subtot = []
    for pn, page in enumerate(pdf.pages):
        words = [w for w in page.extract_words(x_tolerance=1.5) if not (w['x0'] > 505 and len(w['text']) <= 2)]
        L = lines_of(words)
        anchors = []; barriers = []
        for i, l in enumerate(L):
            t = l['text'].strip()
            tt = t.replace('【', '').replace('】', '').strip()
            if tt in SIDO:
                st['sido'] = tt; barriers.append((l['top'], l['top'] + 8)); continue
            m = SECTION_RE.match(t)
            if m and l['top'] < 140:
                if st['section'] != SECTION[m.group(1)]:
                    st['major'] = None; st['minor'] = None  # 새 장(章)에서는 소제목 초기화
                st['section'] = SECTION[m.group(1)]; continue
            if '시설명' in [w['text'] for w in l['words']]:
                cols, numcols, hb = header_cols(L, i)
                barriers.append((l['top'] - 16, hb)); continue
            if l['x0'] < 200 and not re.search(r'\d{2,}', t):
                mh = HEAD_RE.match(t)
                if mh and len(mh.group(3)) <= 24 and not t.startswith(('시설', '일련', '번호', '(')):
                    if mh.group(1) == '∙':
                        st['minor'] = mh.group(3).strip()
                    else:
                        st['major'] = mh.group(3).strip(); st['minor'] = None
                    barriers.append((l['top'], l['top'] + 8)); continue
            if t.startswith('소계'):
                if st['sido'] == '서울특별시':
                    subtot.append(dict(st, text=t))
                barriers.append((l['top'], l['top'] + 8)); continue
            w0 = l['words'][0]
            if cols and 'no' in cols and re.fullmatch(r'\d+', w0['text']) and abs((w0['x0'] + w0['x1']) / 2 - cols['no']) < 12 \
                    and len(l['words']) > 1 and l['top'] < page.height - 45:  # 쪽번호 줄 제외
                anchors.append(dict(top=l['top'], st=dict(st), cols=cols, numcols=numcols, line=i))
        for k, a in enumerate(anchors):
            if a['st']['sido'] != '서울특별시':
                continue
            up = a['top'] - 11.5; lo = a['top'] + 11.5
            if k > 0:
                up = max(up, (anchors[k - 1]['top'] + a['top']) / 2)
            if k + 1 < len(anchors):
                lo = min(lo, (anchors[k + 1]['top'] + a['top']) / 2)
            for bt, bb in barriers:
                if bb <= a['top'] + 1:
                    up = max(up, bb + 0.5)
                elif bt >= a['top'] + 1:
                    lo = min(lo, bt - 0.5)
            ws = [w for w in words if up <= w['top'] <= lo]
            txt, nums = assign(ws, a['cols'], a['numcols'])
            rec = dict(section=a['st']['section'], major=a['st']['major'], minor=a['st']['minor'], page=pn + 1,
                       serial=int(L[a['line']]['words'][0]['text']), **{f'raw_{k}': v for k, v in txt.items()})
            for j, (c, grp, lab) in enumerate(a['numcols']):
                v = nums.get(j)
                rec[f'num_{grp or "시설"}_{lab}'] = float(v[0].replace(',', '')) if v else None
            recs.append(rec)
    return pd.DataFrame(recs), subtot


def official(snap):
    """앞쪽 총괄표(가로 회전 쪽)의 서울 행. pdfplumber는 회전 쪽 글자 순서가 뒤집혀 pdftotext -layout 사용(없으면 생략)."""
    import subprocess
    out = {}
    for pn in range(1, 13):
        try:
            tx = subprocess.run(['pdftotext', '-layout', '-f', str(pn), '-l', str(pn), str(RAW / SRC[snap]['file']), '-'],
                                capture_output=True, text=True, timeout=60).stdout
        except Exception as e:
            return dict(error='pdftotext 없음: ' + str(e)[:80])
        title = next((l.strip() for l in tx.split('\n') if '총괄표' in l), '')
        for l in tx.split('\n'):
            if l.strip().startswith('서울'):
                nums = [float(x.replace(',', '')) for x in re.findall(r'\d[\d,]*', l)]
                if nums:
                    out[title or f'page{pn}'] = dict(first_number_total=nums[0], numbers=nums[:40])
    return out


def build():
    download()
    qa = dict(type=TYP, grade='C', note_grade='연간 공식 명부(보건복지부 장애인복지시설 일람표)', snapshots={})
    fr = {}
    for snap in ['2020_01', '2025_01']:
        sp = SRC[snap]
        d, subtot = parse(snap)
        d = d[(d.raw_name.fillna('') != '') | (d.raw_addr.fillna('') != '') | (d.raw_gu.fillna('') != '')].copy()
        d['facility_subtype'] = [f"{sec.replace('장애인 ', '')}" + (f"/{mj}" if mj else '') + (f"/{mn}" if mn else '') for sec, mj, mn in zip(d.section, d.major, d.minor)]
        d['name'] = d['raw_name'].map(mb.clean)
        d['gu'] = d['raw_gu'].map(lambda x: re.sub(r'\s+', '', x or ''))
        def comp(a, g):
            a = mb.clean(a)
            if not a:
                return ''
            if a.startswith('서울') or mb.OTHER_SIDO.match(a):
                return a
            return mb.seoulize(a, g if g in mb.GU else '')
        d['address'] = [comp(a, g) for a, g in zip(d.raw_addr, d.gu)]
        d['sz_open_date'] = d['raw_date']
        d['sz_corp'] = d.get('raw_corp', '').map(mb.clean) if 'raw_corp' in d else ''
        ren = {}
        for c in d.columns:
            if c.startswith('num_'):
                g, lab = c[4:].split('_')
                base = {'입소자': 'capacity', '장애인': 'capacity', '근로': 'capacity', '종사자': 'staff', '시설': 'capacity'}.get(g, 'capacity')
                nm = f"sz_{base}" if lab == '정원' else f"sz_{'current' if base == 'capacity' else base + '_current'}"
                if base == 'staff' and lab == '정원':
                    nm = 'sz_staff_quota'
                if base == 'staff' and lab == '현원':
                    nm = 'sz_staff'
                ren[c] = nm
        for c, nm in ren.items():
            d[nm] = d[nm].fillna(d[c]) if nm in d else d[c]
        d = d.drop(columns=list(ren))
        d['source_row_id'] = 'p' + d['page'].astype(str) + '_no' + d['serial'].astype(str)
        dates = pd.to_datetime(d['raw_date'].str.replace('.', '-', regex=False).str.rstrip('-'), errors='coerce')
        d = mb.geocode_df(d, RAW / 'geocoding')
        fr[snap] = d
        qa['snapshots'][snap] = dict(source_file=sp['file'], source_rows_seoul=len(d), rows_without_address=int((d.address == '').sum()),
                                     rows_without_name=int((d.name == '').sum()),
                                     max_install_date=str(dates.max().date()) if dates.notna().any() else None,
                                     n_install_date_after_2019=int((dates > '2019-12-31').sum()),
                                     subtotal_lines=subtot)
    a, b, st = mb.assign_ids(fr['2020_01'], fr['2025_01'], 'DIS')
    qa['facility_id_rule'] = 'mb.assign_ids(0 명칭+주소키+subtype, 1 명칭+주소키, 2 명칭 유일, 3 주소키+subtype 유일, 4 좌표 50m+명칭 앞4자). 명칭 없는 공동생활가정은 주소로만 매칭'
    qa['id_matching'] = st
    for snap, d in [('2020_01', a), ('2025_01', b)]:
        sp = SRC[snap]
        d = mb.spatial(d)
        d['category_group'] = '복지행정안전'; d['facility_type'] = TYP; d['grade'] = 'C'
        d['source_org'] = '보건복지부'; d['source_dataset'] = sp['ds']
        d['source_url'] = f"{B}?bid={sp['bid']}&list_no={sp['list_no']}&seq={sp['seq']}"
        d['source_file'] = 'raw/' + sp['file']; d['source_reference_date'] = sp['ref']
        d['reference_month_delta'] = mb.month_delta(sp['ref'], snap)
        d['temporal_reason'] = ('2020년판(2020.7 발간)은 기준일 미표기 → 2019.12말 기준으로 추정(qa max_install_date 참고)' if snap == '2020_01'
                                else '2024.12월말 기준 일람표')
        keep_raw = [c for c in d.columns if c.startswith('raw_')]
        d = mb.finalize(d.drop(columns=keep_raw + ['serial', 'page']), snap, HERE, TYP)
        q = qa['snapshots'][snap]
        q['final_rows'] = len(d); q['subtype_counts'] = d.facility_subtype.value_counts().to_dict()
        q['section_counts'] = d.section.value_counts().to_dict()
        q['geocoding'] = mb.geo_qa(d); q['duplicates'] = mb.dup_qa(d)
    qa['official_check'] = dict(
        총괄표_2020=official('2020_01'), 총괄표_2025=official('2025_01'),
        note='2025판 총괄표 서울 행 첫 수(시설 수)와 section_counts 비교: 거주시설 총괄=거주, 지역사회재활·의료재활 총괄=지역사회+의료, 직업재활 총괄=직업재활. '
             '2020판 PDF 앞쪽 총괄표는 글자 추출이 안 돼 대조 불가.')
    cmp = {}
    for snap in qa['snapshots']:
        sc = qa['snapshots'][snap]['section_counts']; sub = qa['snapshots'][snap]['subtype_counts']
        o = qa['official_check'][f'총괄표_{snap[:4]}']
        for title, v in (o.items() if isinstance(o, dict) else []):
            if '거주' in title:
                cmp[f'{snap} 거주시설'] = dict(official=v['first_number_total'], parsed=sc.get('장애인 거주시설', 0))
            elif '지역사회' in title:
                cmp[f'{snap} 지역사회재활+의료재활'] = dict(official=v['first_number_total'],
                                                     parsed=sc.get('장애인 지역사회재활시설', 0) + sc.get('장애인 의료재활시설', 0))
            elif '직업재활' in title:
                sale = sum(n for k, n in sub.items() if '판매시설' in k)
                cmp[f'{snap} 직업재활(판매시설 제외)'] = dict(official=v['first_number_total'], parsed=sc.get('장애인 직업재활시설', 0) - sale)
    for v in cmp.values():
        v['diff'] = v['parsed'] - v['official']
    qa['official_check']['comparison'] = cmp
    mb.write_json(HERE / f'qa_{TYP}.json', qa)
    return qa


if __name__ == '__main__':
    import json
    q = build()
    for s, v in q['snapshots'].items():
        print(s, v['final_rows'], v['rows_without_address'], v['rows_without_name'], v['max_install_date'], v['n_install_date_after_2019'], v['section_counts'], v['geocoding']['coord_rate'])
        print('  ', v['subtype_counts'])
    print(json.dumps(q['official_check'], ensure_ascii=False)[:1500])
    print(q['id_matching'])
