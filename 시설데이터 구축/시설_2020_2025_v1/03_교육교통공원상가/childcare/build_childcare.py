# -*- coding: utf-8 -*-
"""어린이집 2020_01 / 2025_01 — 서울시 어린이집 정보(OA-20300, 폐지 포함 전체 이력) 역산(B)
규칙: 인가일자 ≤ D 그리고 (폐지일자 없음 또는 > D). 운영현황=폐지인데 폐지일자 없으면 행의 데이터기준일자(최종 갱신일)를
폐지일로 대체(temporal_reason 표시). 인가일자 결측·1900-01-01 등 더미는 unknown → 제외.
휴지는 시작·종료일이 모두 있고 시작 ≤ D ≤ 종료일 때만 제외.
정원·현원은 현재값(폐지 시설은 폐지 직전값) → sz_capacity_current, sz_enrolled_current (시점값 아님).
대조: 서울시 보육통계 OA-15457 (연말 자치구×유형 시설수)."""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import fac
import pandas as pd, numpy as np

RAW = HERE / 'raw'; TYP = 'childcare'; GC = RAW / 'geocoding'
fac.seoul_sheet('OA-20300', RAW / 'OA-20300_어린이집정보.csv', ref_date='다운로드 시점 현재(폐지 이력 포함)',
                note='서울시 어린이집 정보(표준 데이터) 시트 CSV')
fac.seoul_sheet('OA-15457', RAW / 'OA-15457_보육통계_자치구유형별.csv', ref_date='연도별 12월말',
                note='서울시 보육통계 어린이집 현황(자치구,유형별)')
d = fac.read_csv_any(RAW / 'OA-20300_어린이집정보.csv')
d['row'] = np.arange(2, len(d) + 2)
st = fac.read_csv_any(RAW / 'OA-15457_보육통계_자치구유형별.csv')
TYPEMAP = {'법인?단체등': '법인·단체등'}
d['어린이집유형'] = d['어린이집유형'].replace(TYPEMAP)

def dt(s):
    x = pd.to_datetime(s, errors='coerce')
    return x.where(x > pd.Timestamp('1901-01-01'))

d['_auth'] = dt(d['인가일자']); d['_close'] = dt(d['폐지일자'])
d['_close_sub'] = False
m = (d['운영현황'] == '폐지') & d['_close'].isna()
d.loc[m, '_close'] = dt(d.loc[m, '데이터기준일자']); d.loc[m, '_close_sub'] = True
d['_hs'] = dt(d['휴지시작일자']); d['_he'] = dt(d['휴지종료일자'])
qa = {'type': TYP, 'notes': [__doc__.strip()], 'source_rows': len(d),
      'source_status': d['운영현황'].value_counts().to_dict(),
      'auth_date_unknown': int(d['_auth'].isna().sum()), 'closed_without_date_substituted': int(m.sum())}
outs = {}
for snap in ['2020_01', '2025_01']:
    D = pd.Timestamp(fac.SNAP[snap]['ref'])
    alive = d['_auth'].notna() & (d['_auth'] <= D) & (d['_close'].isna() | (d['_close'] > D))
    susp = d['_hs'].notna() & d['_he'].notna() & (d['_hs'] <= D) & (d['_he'] >= D)
    s = d[alive & ~susp].copy()
    o = pd.DataFrame(index=s.index)
    o['facility_id'] = 'CC_' + s['어린이집코드']; o['category_group'] = '교육보육'; o['facility_type'] = '어린이집'
    o['facility_subtype'] = s['어린이집유형']; o['year_snapshot'] = snap; o['name'] = s['어린이집명']
    o['address'] = s['상세주소']; o['lon'] = pd.to_numeric(s['시설 경도(좌표값)'], errors='coerce')
    o['lat'] = pd.to_numeric(s['시설 위도(좌표값)'], errors='coerce')
    o.loc[~o['lon'].between(120, 135), ['lon', 'lat']] = np.nan
    o['coord_method'] = np.where(o['lon'].notna(), 'source', None)
    o = fac.geocode_df(o, 'address', GC)
    o['grade'] = 'B'; o['source_org'] = '서울특별시(원천 보건복지부 어린이집정보공개포털)'
    o['source_dataset'] = '서울시 어린이집 정보(표준 데이터) OA-20300'
    o['source_url'] = 'https://data.seoul.go.kr/dataList/OA-20300/S/1/datasetView.do'
    o['source_file'] = 'raw/OA-20300_어린이집정보.csv'; o['source_row_id'] = s['row'].astype(str)
    o['source_reference_date'] = fac.SNAP[snap]['ref']; o['reference_month_delta'] = 0
    o['temporal_reason'] = np.where(s['_close_sub'], '역산: 인가일≤D, 폐지(날짜 없음→데이터기준일자로 대체)>D',
                                    np.where(s['_close'].notna(), '역산: 인가일≤D, 폐지일>D', '역산: 인가일≤D, 폐지 없음'))
    o['auth_date'] = s['인가일자']; o['close_date'] = s['폐지일자']; o['status_current'] = s['운영현황']
    o['gu_name'] = s['시군구명']
    o['sz_capacity_current'] = pd.to_numeric(s['정원'], errors='coerce')
    o['sz_enrolled_current'] = pd.to_numeric(s['현원'], errors='coerce')
    o['sz_rooms_current'] = pd.to_numeric(s['보육실수'], errors='coerce')
    o = fac.attach_geo(o); o.loc[o['x_5179'].isna(), 'coord_method'] = 'unresolved'
    o = fac.write_out(o, HERE, TYP, snap); outs[snap] = o
    q = fac.qa_block(o)
    yr = '2019' if snap == '2020_01' else '2024'
    t = st[(st['통계연도'] == yr)].copy()
    tot = t[t['자치구명'] == '계'].iloc[0]
    cols = {'국공립': '어린이집수_국공립', '사회복지법인': '어린이집수_사회복지법인', '법인·단체등': '어린이집수_법인단체등',
            '민간': '어린이집수_민간', '가정': '어린이집수_가정', '협동': '어린이집수_부모협동', '직장': '어린이집수_직장'}
    cmp = {k: dict(built=int((o['facility_subtype'] == k).sum()), official=int(tot[v])) for k, v in cols.items()}
    for k in cmp: cmp[k]['diff_pct'] = round(100 * (cmp[k]['built'] / cmp[k]['official'] - 1), 1) if cmp[k]['official'] else None
    g = t[t['자치구명'] != '계'][['자치구명', '시설수합계']].copy(); g['gu'] = g['자치구명'].map(lambda x: x if x.endswith('구') else x + '구')
    bg = o['gu_name'].value_counts()
    g['built'] = g['gu'].map(bg).fillna(0).astype(int); g['official'] = g['시설수합계'].astype(int)
    q.update(excluded_suspended=int((alive & susp).sum()), alive_candidates=int(alive.sum()),
             official_total=int(tot['시설수합계']), diff_total_pct=round(100 * (len(o) / int(tot['시설수합계']) - 1), 2),
             by_type_vs_official=cmp, by_gu_vs_official=g[['gu', 'built', 'official']].to_dict('records'),
             official_source=f'OA-15457 통계연도 {yr} (12월말)', closed_sub_included=int(s['_close_sub'].sum()),
             sum_capacity_current=int(o['sz_capacity_current'].sum()))
    qa[snap] = q
c = set(outs['2020_01']['facility_id']) & set(outs['2025_01']['facility_id'])
qa['panel'] = dict(common_ids=len(c), only_2020=len(outs['2020_01']) - len(c), only_2025=len(outs['2025_01']) - len(c))
fac.dump_qa(HERE, TYP, qa)
for s in ['2020_01', '2025_01']:
    print(s, {k: qa[s][k] for k in ['rows', 'coord_rate', 'coord_method', 'official_total', 'diff_total_pct', 'outside_seoul']})
    print({k: v for k, v in qa[s]['by_type_vs_official'].items()})
