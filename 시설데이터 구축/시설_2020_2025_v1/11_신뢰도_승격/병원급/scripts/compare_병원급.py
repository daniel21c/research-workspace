# -*- coding: utf-8 -*-
"""병원급 역산(01_인허가/병원급) vs 공식 통계.
(1) 서울 합계·종별: 보건복지부 병원 및 의원 수_의료기관 종류별_시도별(data.go.kr 15127855, 2019·2024 연말; 심평원 요양기관 수)
(2) 구별 2025: 심평원 요양기관개설현황 2024.12판(data.go.kr 15051057) 시군구명
(3) 구별 2020(정의 맞춤): 우리 2020_01 중 2021-12-31까지 살아남은 기관 vs 심평원 2021.12판 중 개설일자≤2019-12-31"""
import json
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; OUT = HERE.parent
V1 = OUT.parent.parent
LIC = V1 / '01_인허가'
H = {2024: LIC / '의원/raw/hira_establishments_20241231.csv', 2021: LIC / '의원/raw/hira_establishments_20211231.csv'}
KINDS = ['종합병원', '병원', '요양병원', '정신병원', '치과병원', '한방병원']
HMAP = {'상급종합병원': '종합병원'}

ours = {y: pd.read_parquet(LIC / f'병원급/facilities_병원급_{y}_01.parquet') for y in ('2020', '2025')}
for d in ours.values():
    d['gu'] = d.address.fillna('').str.extract(r'서울특별시\s*([가-힣]+구)')[0]

off = pd.read_csv(OUT / 'raw/datagokr_15127855_병의원수_종류별_시도별_20241231.csv', encoding='cp949')
off = off[off['시도'].str.contains('서울')].set_index('연도')
def offk(yr):
    r = off.loc[yr]
    return {'종합병원': r['병의원_종합병원'], '병원': r['병의원_일반병원'] + r['특수병원_결핵'] + r['특수병원_한센'],
            '요양병원': r['병의원_요양병원'], '정신병원': r['특수병원_정신'], '치과병원': r['치과병 의원_치과병원'], '한방병원': r['한방병 의원_한방병원']}
rows = []
for y, yr in (('2020', 2019), ('2025', 2024)):
    o = ours[y].facility_subtype.value_counts(); k = offk(yr)
    for kk in KINDS + ['요양+정신', '합계']:
        if kk == '요양+정신':
            a = o.get('요양병원', 0) + o.get('정신병원', 0); b = k['요양병원'] + k['정신병원']
        elif kk == '합계':
            a = int(o[o.index.isin(KINDS)].sum()); b = int(sum(k.values()))
        else:
            a = int(o.get(kk, 0)); b = int(k[kk])
        rows.append(dict(level='서울', snapshot=y + '_01', official_date=f'{yr}-12-31', kind=kk, ours=int(a), official=int(b),
                         diff=int(a - b), diff_pct=round((a - b) / b * 100, 2) if b else None,
                         source='보건복지부_병원 및 의원 수_의료기관 종류별_시도별_20241231 (data.go.kr 15127855)'))

def hira(yr):
    d = pd.read_csv(H[yr], encoding='cp949', dtype=str); d = d[d['시도명'] == '서울특별시'].copy()
    if '암호화된요양기호' in d: d = d.drop_duplicates('암호화된요양기호')
    d['kind'] = d['요양종별'].map(lambda v: HMAP.get(v, v)); d = d[d.kind.isin(KINDS)]
    d['gu'] = d['시군구명'].str.replace('서울', '').str.strip(); d['open'] = pd.to_datetime(d['개설일자'], errors='coerce')
    return d
def gu_cmp(a, b, label, snap, src):
    g = pd.DataFrame({'ours': a.value_counts(), 'official': b.value_counts()}).fillna(0).astype(int)
    g['diff'] = g.ours - g.official; g['diff_pct'] = (g['diff'] / g.official * 100).round(1)
    st = dict(r=round(float(np.corrcoef(g.ours, g.official)[0, 1]), 4), max_abs_diff=int(g['diff'].abs().max()),
              max_abs_pct=float(g.diff_pct.abs().max()), n_gu=len(g), total_ours=int(g.ours.sum()), total_off=int(g.official.sum()),
              gu_within5pct=int((g.diff_pct.abs() <= 5).sum()), gu_within_2=int((g['diff'].abs() <= 2).sum()))
    for gu, r in g.iterrows():
        rows.append(dict(level='구:' + label, snapshot=snap, official_date=src[1], kind='병원급 전체', gu=gu, ours=int(r.ours),
                         official=int(r.official), diff=int(r['diff']), diff_pct=r.diff_pct, source=src[0]))
    return st, g
h24 = hira(2024)
s25, g25 = gu_cmp(ours['2025'].gu, h24.gu, '직접', '2025_01', ('심평원 요양기관개설현황 2024.12판 (data.go.kr 15051057)', '2024-12-31'))
h21 = hira(2021); h21 = h21[h21.open <= '2019-12-31']
o20 = ours['2020']; end = pd.to_datetime(o20.end_date, errors='coerce')
surv = o20[end.isna() | (end > '2021-12-31')]
s20, g20 = gu_cmp(surv.gu, h21.gu, '생존맞춤', '2020_01', ('심평원 요양기관개설현황 2021.12판 개설일자≤2019-12-31 (data.go.kr 15051057)', '2021-12-31'))
res = pd.DataFrame(rows)
res.to_csv(OUT / 'official_compare_병원급.csv', index=False, encoding='utf-8-sig')
cov = {y: dict(coord_rate=float(d.lon.notna().mean()), inside=float(d.inside_seoul.mean()),
               min_gu_coord_rate=float(d.groupby('gu').lon.apply(lambda s: s.notna().mean()).min())) for y, d in ours.items()}
# 민감도: 2020 정의맞춤 생존 비교의 종별
kind20 = pd.DataFrame({'ours_surv': surv.facility_subtype.value_counts(), 'hira21_open_le2019': h21.kind.value_counts()}).fillna(0).astype(int)
summ = dict(gu_2025=s25, gu_2020_survivor=s20, coverage=cov, n_surv_2020=len(surv),
            kind_2020_survivor=kind20.to_dict(), flag_admin_end={y: int(d.flag_admin_end.sum()) for y, d in ours.items()})
(OUT / 'summary_병원급.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
print(res[res.level == '서울'].to_string()); print(json.dumps(summ, ensure_ascii=False, default=str))
print(g25[g25['diff'].abs() >= 2]); print(g20[g20['diff'].abs() >= 2])
