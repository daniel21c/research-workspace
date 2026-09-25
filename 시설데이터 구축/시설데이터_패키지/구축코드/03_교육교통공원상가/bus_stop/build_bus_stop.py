# -*- coding: utf-8 -*-
"""버스정류소 2020_01 / 2025_01
2020: 서울시 연도별 정류장 현황(OA-22193) '2019년 12월 31일 기준' 시트(목록 A, 좌표 없음)
      + 서울시 버스정류소 위치정보(OA-15067) 2019.07.10판 좌표를 ARS-ID로 조인, 없으면 2020.12.31판 좌표.
2025: OA-15067 20241209판(A, 좌표 포함).
정류소유형(중앙차로/가로변/마을버스/가상정류장 등)은 facility_subtype. 2020 유형은 2020.12.31판에서 가져옴(없으면 미상)."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import fac
import pandas as pd, numpy as np

RAW = HERE / 'raw'; TYP = 'bus_stop'
fac.seoul_file('OA-22193', 1, 1, RAW / 'OA-22193_정류소현황_2019_2023.xlsx', ref_date='2019-12-31 등 연말 시트',
               note='서울시 연도별 정류장 현황')
fac.seoul_file('OA-15067', 2, 1, RAW / 'OA-15067_버스정류소위치_20190710.xlsx', ref_date='2019-07-10')
fac.seoul_file('OA-15067', 3, 1, RAW / 'OA-15067_버스정류소위치_20201231.xlsx', ref_date='2020-12-31')
fac.seoul_file('OA-15067', 37, 1, RAW / 'OA-15067_버스정류소위치_20241209.xlsx', ref_date='2024-12-09')

lst = pd.read_excel(RAW / 'OA-22193_정류소현황_2019_2023.xlsx', sheet_name='2019년 12월 31일 기준', dtype=str)
lst['row'] = np.arange(2, len(lst) + 2)
c19 = pd.read_excel(RAW / 'OA-15067_버스정류소위치_20190710.xlsx', dtype=str).drop_duplicates('ARSID')
c20 = pd.read_excel(RAW / 'OA-15067_버스정류소위치_20201231.xlsx', dtype=str).drop_duplicates('ARS-ID')
c24 = pd.read_excel(RAW / 'OA-15067_버스정류소위치_20241209.xlsx', dtype=str)
c24['row'] = np.arange(2, len(c24) + 2)
qa = {'type': TYP, 'notes': [__doc__.strip()]}

def base(o, snap):
    o['category_group'] = '교통'; o['facility_type'] = '버스정류소'; o['year_snapshot'] = snap
    o['source_org'] = '서울특별시'; o['source_url'] = 'https://data.seoul.go.kr/dataList/OA-15067/F/1/datasetView.do'
    return o

# 2020
o = pd.DataFrame(index=lst.index)
o['facility_id'] = 'BUS_' + lst['ARS-ID']; o['name'] = lst['정류소명']; o['address'] = None
m19 = lst[['ARS-ID']].merge(c19, left_on='ARS-ID', right_on='ARSID', how='left'); m19.index = lst.index
m20 = lst[['ARS-ID']].merge(c20, on='ARS-ID', how='left', suffixes=('', '_20')); m20.index = lst.index
o['lon'] = pd.to_numeric(m19['X좌표'], errors='coerce'); o['lat'] = pd.to_numeric(m19['Y좌표'], errors='coerce')
o['coord_file'] = np.where(o['lon'].notna(), 'OA-15067 20190710', None)
f = o['lon'].isna()
o.loc[f, 'lon'] = pd.to_numeric(m20.loc[f, 'X좌표'], errors='coerce'); o.loc[f, 'lat'] = pd.to_numeric(m20.loc[f, 'Y좌표'], errors='coerce')
o.loc[f & o['lon'].notna(), 'coord_file'] = 'OA-15067 20201231'
o['coord_method'] = np.where(o['lon'].notna(), 'source', 'unresolved')
o['facility_subtype'] = m20['정류소유형'].fillna('미상')
o['node_id'] = m19['표준ID'].fillna(m20['NODE_ID'])
o['grade'] = 'A'; o['source_dataset'] = '서울시 연도별 정류장 현황(OA-22193) 2019-12-31 목록 + 버스정류소 위치정보(OA-15067) 좌표'
o['source_file'] = 'raw/OA-22193_정류소현황_2019_2023.xlsx'; o['source_row_id'] = lst['row'].astype(str)
o['source_reference_date'] = '2019-12-31'; o['reference_month_delta'] = 0
o['temporal_reason'] = '목록은 2019-12-31 기준(A). 좌표는 2019-07-10판(-6개월) 우선, 없으면 2020-12-31판(+12개월)'
o['gu_name'] = lst['행정구명']; o['sz_routes'] = pd.to_numeric(lst['노선수'], errors='coerce')
o = base(o, '2020_01'); o = fac.attach_geo(o); o = fac.write_out(o, HERE, TYP, '2020_01')
q = fac.qa_block(o)
q.update(list_rows=len(lst), coord_from=o['coord_file'].value_counts(dropna=False).to_dict(),
         dup_ars_in_list=int(lst['ARS-ID'].duplicated().sum()),
         osm_note='OSM 비교는 transport_base 조사(서울 bbox bus_stop 노드 2020: 8,809) 참고용')
qa['2020_01'] = q
# 2025
o = pd.DataFrame(index=c24.index)
o['facility_id'] = 'BUS_' + c24['ARS_ID']; o['name'] = c24['정류소명']; o['address'] = None
o['lon'] = c24['X좌표']; o['lat'] = c24['Y좌표']; o['coord_method'] = 'source'
o['facility_subtype'] = c24['정류소타입']; o['node_id'] = c24['NODE_ID']
o['grade'] = 'A'; o['source_dataset'] = '서울시 버스정류소 위치정보(OA-15067) 20241209판'
o['source_file'] = 'raw/OA-15067_버스정류소위치_20241209.xlsx'; o['source_row_id'] = c24['row'].astype(str)
o['source_reference_date'] = '2024-12-09'; o['reference_month_delta'] = fac.month_delta('2024-12-09', '2025_01')
o['temporal_reason'] = '2024-12-09 배포본(허용창 내)'; o['sz_routes'] = np.nan
o = base(o, '2025_01'); o = fac.attach_geo(o); o.loc[o['x_5179'].isna(), 'coord_method'] = 'unresolved'
o = fac.write_out(o, HERE, TYP, '2025_01')
q = fac.qa_block(o)
q.update(source_rows=len(c24), virtual_stops=int((c24['정류소타입'] == '가상정류장').sum()),
         official_compare='OA-22193 연말 목록 2023-12-04 시트와 비교 가능(2024 시트 없음)')
try:
    l23 = pd.read_excel(RAW / 'OA-22193_정류소현황_2019_2023.xlsx', sheet_name='2023년 12월 4일 기준', dtype=str)
    q['oa22193_2023_12_04_rows'] = len(l23)
except Exception as e:
    q['oa22193_2023_12_04_rows'] = str(e)
qa['2025_01'] = q
a, b = set(fac.read_csv_any(HERE / 'facilities_bus_stop_2020_01.csv')['facility_id']), set(o['facility_id'])
qa['panel'] = dict(common_ids=len(a & b), only_2020=len(a - b), only_2025=len(b - a))
fac.dump_qa(HERE, TYP, qa)
for s in ['2020_01', '2025_01']:
    print(s, {k: qa[s].get(k) for k in ['rows', 'coord_rate', 'coord_from', 'outside_seoul', 'dup_facility_id', 'subtype']})
print(qa['panel'])
