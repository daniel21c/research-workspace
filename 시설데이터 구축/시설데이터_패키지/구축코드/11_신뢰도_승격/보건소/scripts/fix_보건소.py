# -*- coding: utf-8 -*-
"""보건소 2025_01(원 빌드 = 2025-12-31판 명부)를 2024-12-31 상태로 맞춤.
(1) 수: 2024년말 시도별 수(data.go.kr 15127903: 보건소 25·보건지소 38·건강생활지원센터 0) = 2025-12판 서울 63행(보건소 25·일반보건지소 38) → 2025년 중 신설·폐지 순변화 0.
    2022-12판(33지소) 대비 2025-12판에만 있는 5곳(송정·삼각산·수유·불광·독산)은 공식 수 2023=36, 2024=38 과 합치(2023+3, 2024+2).
(2) 위치: 2025년 중 이전한 3곳은 2024-12-31 당시 주소(=2022-12판·2020_01 빌드와 같은 주소)의 좌표로 되돌림.
    광진구보건소(자양로 117 → 아차산로 400, 2025-04 통합청사 이전), 동작구보건소(장승배기로10길 42 → 만양로3길 80, 2025-01-31 이전),
    창동보건지소(덕릉로59길 73-3 → 덕릉로63길 53, 2025-05 이전). 좌표·행정코드는 2020_01 빌드의 같은 기관 행에서 복사(같은 주소, Kakao exact)."""
import json, re, sys
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent; OUT = HERE.parent; V1 = HERE.parents[2]
SRC = V1 / '02_명부/보건소'
a20 = pd.read_parquet(SRC / 'facilities_보건소_2020_01.parquet'); a25 = pd.read_parquet(SRC / 'facilities_보건소_2025_01.parquet')
def rk(a):
    m = re.search(r'([가-힣A-Za-z0-9]+(?:로|길))\s*(\d+(?:-\d+)?)', a or ''); return f'{m.group(1)} {m.group(2)}' if m else ''
e22 = pd.read_csv(SRC / 'raw/datagokr_3072692_지역보건의료기관_20221231.csv', encoding='cp949', dtype=str)
e22 = e22[e22['시도'].str.contains('서울')].copy(); e22['nm'] = e22['보건기관명'].str.replace(r'\s', '', regex=True); e22['rk'] = e22['주소'].map(rk)
a25['nm'] = a25.name.str.replace(r'\s', '', regex=True); a25['rk'] = a25.address.map(rk)
m = a25.merge(e22[['nm', 'rk']], on='nm', how='left', suffixes=('', '_2022'))
moved = m[m.rk_2022.notna() & (m.rk != m.rk_2022)][['name', 'rk', 'rk_2022']]
MOVE = {'광진구보건소': ('자양로 117', '2025-04 광진구 통합청사(아차산로 400) 이전', 'https://mbiz.heraldcorp.com/article/10504431'),
        '동작구보건소': ('장승배기로10길 42', '2025-01-31 신청사(만양로3길 80) 이전', 'https://www.asiae.co.kr/article/2025011007401732773'),
        '창동보건지소': ('덕릉로59길 73-3', '2025-05 덕릉로63길 53 이전', 'https://www.job-post.co.kr/news/articleView.html?idxno=162083')}
assert set(moved.name) == set(MOVE), moved
out = a25.drop(columns=['nm', 'rk']).copy(); out['coord_stage'] = 'original_2025-12판'; out['scope_flag'] = ''
out['address_2024_12'] = out.address
cols = ['lon', 'lat', 'x_5179', 'y_5179', 'coord_method', 'inside_seoul', 'adm_dong_cd', 'oa_cd', 'grid100_cd', 'geocode_detail']
a20['rk'] = a20.address.map(rk)
for nm, (old, why, url) in MOVE.items():
    src = a20[a20.rk == old]; assert len(src) == 1, (nm, old)
    i = out.index[out.name == nm][0]
    for c in cols: out.at[i, c] = src.iloc[0][c]
    out.at[i, 'address_2024_12'] = src.iloc[0].address
    out.at[i, 'coord_stage'] = f'2024-12 위치로 환원({why}; 좌표=2020_01 빌드 동일주소 행)'
    out.at[i, 'coord_method'] = str(src.iloc[0].coord_method) + '_reuse2020'
out['temporal_reason'] = out.temporal_reason.astype(str) + ';11승격: 2024말 시도별 수 일치(63=63), 2025 이전 3곳 2024-12 위치로 환원'
out.to_parquet(OUT / 'facilities_보건소_2025_01.parquet', index=False); out.to_csv(OUT / 'facilities_보건소_2025_01.csv', index=False, encoding='utf-8-sig')
off = pd.read_csv(OUT / 'raw/datagokr_15127903_보건소등수_시도별_20241231.csv', encoding='cp949')
off = off[off['시도'].str.startswith('서울')].set_index('년도')
rows = []
for snap, yr, d in (('2020_01', 2019, a20), ('2025_01', 2024, out)):
    vc = d.facility_subtype.value_counts()
    for k_ours, k_off in (('보건소', '보건소'), ('일반보건지소', '보건지소')):
        rows.append(dict(snapshot=snap, official_year=yr, kind=k_off, ours=int(vc.get(k_ours, 0)), official=int(off.loc[yr, k_off])))
    rows.append(dict(snapshot=snap, official_year=yr, kind='건강생활지원센터', ours=int(vc.get('건강생활지원센터', 0)), official=int(off.loc[yr, '건강생활지원센터'])))
    rows.append(dict(snapshot=snap, official_year=yr, kind='보건진료소', ours=int(vc.get('보건진료소', 0)), official=int(off.loc[yr, '보건진료소'])))
r = pd.DataFrame(rows); r['diff'] = r.ours - r.official
tot = r.groupby(['snapshot', 'official_year'])[['ours', 'official', 'diff']].sum().reset_index().assign(kind='합계'); r = pd.concat([r, tot])
r['source'] = '보건복지부 보건소·보건지소·보건진료소·건강생활지원센터 수_시도별_20241231 (data.go.kr 15127903)'
r.to_csv(OUT / 'official_compare_보건소.csv', index=False, encoding='utf-8-sig')
gu = pd.DataFrame({'2020_01': a20.gu.value_counts(), '2025_01': out.gu.value_counts()}).fillna(0).astype(int)
summ = dict(moved_2025=moved.to_dict('records'), yearly_official_seoul=off[['보건소', '보건지소', '보건진료소', '건강생활지원센터']].to_dict('index'),
            new_since_2022=a25.loc[~a25.in_2022_edition.astype(bool), 'name'].tolist(), coord_rate={'2020': float(a20.lon.notna().mean()), '2025': float(out.lon.notna().mean())},
            gu_counts=gu.to_dict())
(OUT / 'summary_보건소.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
print(r.to_string()); print(json.dumps({k: summ[k] for k in ('moved_2025', 'new_since_2022', 'coord_rate')}, ensure_ascii=False))
