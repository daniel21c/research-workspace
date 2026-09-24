# -*- coding: utf-8 -*-
"""유치원 2020_01 / 2025_01 — 유치원알리미 공시 기본현황(gongsiListCode=05)
주: 2019년 2차 공시(timingListCode=20192) / 2024년 2차(20242). 민감도용으로 20201·20251도 저장.
위경도 원자료 포함(coord_method=source). 동작구 사랑유치원 1행은 홈페이지 URL의 쉼표 때문에 열이 밀려 있어 병합 수정.
대조: 서울교육통계 일람표 유치원 수(폐원 제외) — school/raw 의 일람표 사용."""
import sys, csv, io, json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import fac
import pandas as pd, numpy as np

RAW = HERE / 'raw'; TYP = 'kindergarten'
URL = 'https://e-childschoolinfo.moe.go.kr/download/getOpenData.do'
T = {'20192': '2019-10-01', '20201': '2020-04-01', '20242': '2024-10-01', '20251': '2025-04-01'}
for t, ref in T.items():
    fac.fetch(URL, RAW / f'kinder_basic_{t}.csv', params=dict(combineSidoCode=11, timingListCode=t, gongsiListCode='05',
                                                              ExcelCsv=2), ref_date=ref,
              note=f'유치원알리미 기본현황 {t[:4]}년 {t[4]}차 공시(기준일은 공시 지침상 4.1/10.1 추정)')

def load(t):
    txt = open(RAW / f'kinder_basic_{t}.csv', encoding='utf-8-sig').read()
    rows = list(csv.reader(io.StringIO(txt))); h = rows[0]; fixed = 0; out = []
    hi = h.index('홈페이지')
    for i, r in enumerate(rows[1:], start=2):
        if len(r) == len(h) + 1:
            r = r[:hi] + [r[hi] + ',' + r[hi + 1]] + r[hi + 2:]; fixed += 1
        if len(r) != len(h):
            continue
        out.append(r + [i])
    d = pd.DataFrame(out, columns=h + ['row']); return d, fixed

qa = {'type': TYP, 'notes': [
    '유치원알리미 기본현황 공시 2019-2차(20192)·2024-2차(20242)를 주 자료로 사용(A). 기준일은 공시지침상 10.1 추정(원문 미확인) → source_reference_date 2019-10-01/2024-10-01.',
    'sz_capacity=인가총정원수, sz_children=연령별 원아수 합, sz_classes=연령별 학급수 합(특수 포함).',
    'facility_id = KG_ + 유치원명 + 설립일(yyyymmdd): 두 시점 같은 시설 연결용(원천 고유코드 없음).']}
sen = {}
try:
    sys.path.insert(0, str(HERE.parent / 'school'))
    s19 = pd.read_excel(HERE.parent / 'school' / 'raw' / 'sen_2019하_학교현황.xlsx', sheet_name='05_학교별주요통계', header=None, dtype=str)
    sen['2020_01'] = int(((s19[2] == '유치원') & (~s19[7].astype(str).str.contains('폐'))).sum())
    s24 = pd.read_excel(HERE.parent / 'school' / 'raw' / 'sen_2024하_학교별일람표.xlsx', sheet_name=0, header=None, dtype=str)
    sen['2025_01'] = int(((s24[4] == '유치원') & (~s24.iloc[:, 14].astype(str).str.contains('폐'))).sum())
except Exception as e:
    sen['error'] = str(e)
outs = {}
for snap, t, alt in [('2020_01', '20192', '20201'), ('2025_01', '20242', '20251')]:
    d, fixed = load(t)
    o = pd.DataFrame(index=d.index)
    o['facility_id'] = 'KG_' + d['유치원명'].str.replace(r'\s', '', regex=True) + '_' + d['설립일']
    o['category_group'] = '교육보육'; o['facility_type'] = '유치원'
    o['facility_subtype'] = d['설립유형']; o['year_snapshot'] = snap; o['name'] = d['유치원명']; o['address'] = d['주소']
    o['lon'] = d['경도']; o['lat'] = d['위도']; o['coord_method'] = 'source'; o['grade'] = 'A'
    o['source_org'] = '교육부(유치원알리미)'; o['source_dataset'] = f'유치원 기본현황 공시 {t[:4]}-{t[4]}차'
    o['source_url'] = f'{URL}?combineSidoCode=11&timingListCode={t}&gongsiListCode=05&ExcelCsv=2'
    o['source_file'] = f'raw/kinder_basic_{t}.csv'; o['source_row_id'] = d['row'].astype(str)
    o['source_reference_date'] = T[t]; o['reference_month_delta'] = fac.month_delta(T[t], snap)
    o['temporal_reason'] = f'{t[:4]}년 {t[4]}차 공시(기준일 {T[t]} 추정, 허용창 내)'
    num = lambda cols: sum(pd.to_numeric(d[c], errors='coerce').fillna(0) for c in cols)
    o['sz_capacity'] = pd.to_numeric(d['인가총정원수'], errors='coerce')
    o['sz_children'] = num(['만3세원아수', '만4세원아수', '만5세원아수', '혼합원아수', '특수원아수'])
    o['sz_classes'] = num(['만3세학급수', '만4세학급수', '만5세학급수', '혼합학급수', '특수학급수'])
    o['establish_date'] = d['설립일']; o['open_date'] = d['개원일']; o['edu_office'] = d['교육지원청명']
    o.loc[pd.to_numeric(o['lon'], errors='coerce').isna(), 'coord_method'] = 'unresolved'
    o = fac.attach_geo(o); o.loc[o['x_5179'].isna(), 'coord_method'] = 'unresolved'
    o = fac.write_out(o, HERE, TYP, snap); outs[snap] = o
    q = fac.qa_block(o)
    a, _ = load(alt)
    q.update(source_rows=len(d), fixed_shifted_rows=fixed, official_sen_kindergartens_excl_closed=sen.get(snap),
             diff_vs_sen=(len(o) - sen[snap]) if snap in sen else None,
             sensitivity_alt_release={alt: len(a)}, sum_capacity=int(o['sz_capacity'].sum()),
             sum_children=int(o['sz_children'].sum()))
    qa[snap] = q
c = set(outs['2020_01']['facility_id']) & set(outs['2025_01']['facility_id'])
qa['panel'] = dict(common_ids=len(c), only_2020=len(outs['2020_01']) - len(c), only_2025=len(outs['2025_01']) - len(c))
fac.dump_qa(HERE, TYP, qa)
print({k: {kk: v[kk] for kk in ['rows', 'coord_rate', 'outside_seoul', 'dup_facility_id', 'official_sen_kindergartens_excl_closed', 'fixed_shifted_rows', 'subtype']} for k, v in qa.items() if k in ('2020_01', '2025_01')}, qa['panel'])
