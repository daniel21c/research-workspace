# -*- coding: utf-8 -*-
"""공공자전거(따릉이) 대여소 2020_01 / 2025_01 — 서울시 공공자전거 대여소 정보(OA-13252)
2020: 가장 이른 공개판(21.01.31 기준)에서 설치시기 ≤ 2019-12-31 행을 역산(B). 2020년 중 철거·이전된 대여소는 누락되고,
      재설치로 설치시기가 갱신된 대여소(예: 304 광화문역 2번출구 앞 2021-01-26)도 누락될 수 있음.
2025: 24.12월 기준판(A, 허용창 내).
sz_racks = LCD+QR 거치대수(판 시점 값)."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import fac
import pandas as pd, numpy as np

RAW = HERE / 'raw'; TYP = 'bike_station'
fac.seoul_file('OA-13252', 11, 2, RAW / 'OA-13252_대여소정보_210131.csv', ref_date='2021-01-31')
fac.seoul_file('OA-13252', 21, 2, RAW / 'OA-13252_대여소정보_2412.xlsx', ref_date='2024-12월 기준(2025-01-16 게시)')

def parse(d):
    d = d.copy(); d.columns = range(d.shape[1]); d['row'] = d.index + 2
    d = d[pd.to_numeric(d[0], errors='coerce').notna()].copy()
    o = pd.DataFrame({'sid': d[0].astype(str).str.replace(r'\.0$', '', regex=True).str.strip(), 'name': d[1], 'gu': d[2],
                      'addr': d[3], 'lat': d[4], 'lon': d[5], 'inst': pd.to_datetime(d[6], errors='coerce'),
                      'lcd': pd.to_numeric(d[7], errors='coerce'), 'qr': pd.to_numeric(d[8], errors='coerce'),
                      'op': d[9], 'row': d['row']})
    return o

a = parse(fac.read_csv_any(RAW / 'OA-13252_대여소정보_210131.csv', header=None))
b = parse(pd.read_excel(RAW / 'OA-13252_대여소정보_2412.xlsx', header=None, dtype=str))
qa = {'type': TYP, 'notes': [__doc__.strip()]}
for snap, s, grade, f, ref in [('2020_01', a[a['inst'] <= '2019-12-31'], 'B', 'OA-13252_대여소정보_210131.csv', '2019-12-31'),
                               ('2025_01', b, 'A', 'OA-13252_대여소정보_2412.xlsx', '2024-12-31')]:
    o = pd.DataFrame(index=s.index)
    o['facility_id'] = 'BIKE_' + s['sid']; o['category_group'] = '교통'; o['facility_type'] = '공공자전거대여소'
    o['facility_subtype'] = s['op'].fillna('미상'); o['year_snapshot'] = snap; o['name'] = s['name']; o['address'] = s['addr']
    o['lon'] = s['lon']; o['lat'] = s['lat']; o['coord_method'] = 'source'; o['grade'] = grade
    o['source_org'] = '서울특별시(서울시설공단)'; o['source_dataset'] = '서울시 공공자전거 대여소 정보 OA-13252 ' + ('21.01.31 기준판(설치시기 역산)' if grade == 'B' else '24.12월 기준판')
    o['source_url'] = 'https://data.seoul.go.kr/dataList/OA-13252/F/1/datasetView.do'; o['source_file'] = 'raw/' + f
    o['source_row_id'] = s['row'].astype(str); o['source_reference_date'] = ref if grade == 'B' else '2024-12-31'
    o['reference_month_delta'] = 0
    o['temporal_reason'] = '2021-01-31판에서 설치시기≤2019-12-31(철거·재설치 대여소 누락 가능)' if grade == 'B' else '2024년 12월 기준 배포본'
    o['install_date'] = s['inst'].dt.strftime('%Y-%m-%d'); o['gu_name'] = s['gu']
    o['sz_racks'] = s['lcd'].fillna(0) + s['qr'].fillna(0)
    o = fac.attach_geo(o); o.loc[o['x_5179'].isna(), 'coord_method'] = 'unresolved'
    o = fac.write_out(o, HERE, TYP, snap)
    q = fac.qa_block(o); q['source_rows'] = len(a) if grade == 'B' else len(b)
    if grade == 'B':
        q['installed_after_ref_excluded'] = int((a['inst'] > '2019-12-31').sum()); q['install_date_missing'] = int(a['inst'].isna().sum())
        q['install_year_dist'] = a['inst'].dt.year.value_counts().sort_index().to_dict()
    qa[snap] = q
o20 = set(fac.read_csv_any(HERE / 'facilities_bike_station_2020_01.csv')['facility_id']); o25 = set(o['facility_id'])
qa['panel'] = dict(common_ids=len(o20 & o25), only_2020=len(o20 - o25), only_2025=len(o25 - o20))
qa['official_compare'] = '공식 연말 대여소 수 대조 미실시(보류) — 2019-12 대여이력(OA-15182 등)의 대여소 ID로 검증 권장'
fac.dump_qa(HERE, TYP, qa)
print({k: {kk: qa[k].get(kk) for kk in ['rows', 'source_rows', 'coord_rate', 'outside_seoul', 'dup_facility_id', 'installed_after_ref_excluded', 'install_date_missing']} for k in ['2020_01', '2025_01']}, qa['panel'])
