# -*- coding: utf-8 -*-
"""소방서·119안전센터·구조대 2020_01 / 2025_01 — 서울시 소방서 안전센터 구조대 위치정보(OA-21072) 연도판(C)
2020_01: _2020판, 2025_01: _2024판(민감도: _2025판 행수 qa 기록). 연도판은 기준월 미표기(변경 시 업로드) → reference_month_delta 미상.
좌표 X/Y는 EPSG:5186(GRS80 중부원점, 가산 600000) — 서울 경계 포함 여부로 검증.
facility_subtype: 이름으로 분류(…소방서 / …119안전센터 / …구조대 / 기타)."""
import sys, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import fac
import pandas as pd, numpy as np
from pyproj import Transformer

RAW = HERE / 'raw'; TYP = 'fire_station'
for seq, y in [(2, 2020), (4, 2024), (5, 2025)]:
    fac.seoul_file('OA-21072', seq, 3, RAW / f'OA-21072_소방위치_{y}.xlsx', ref_date=f'{y}년판(월 미표기)')

def sub(n):
    n = str(n)
    if n.endswith('소방서'): return '소방서'
    if '안전센터' in n: return '119안전센터'
    if '구조대' in n: return '구조대'
    return '기타(본부·현장대응단 등)'

qa = {'type': TYP, 'notes': [__doc__.strip()]}
t = Transformer.from_crs(5186, 4326, always_xy=True)
for snap, y in [('2020_01', 2020), ('2025_01', 2024)]:
    d = pd.read_excel(RAW / f'OA-21072_소방위치_{y}.xlsx', dtype=str); d['row'] = np.arange(2, len(d) + 2)
    o = pd.DataFrame(index=d.index)
    o['facility_id'] = 'FIRE_' + d['서ㆍ센터ID']; o['category_group'] = '복지행정안전'; o['facility_type'] = '소방관서'
    o['facility_subtype'] = d['서ㆍ센터명'].map(sub); o['year_snapshot'] = snap; o['name'] = d['서ㆍ센터명']; o['address'] = None
    x = pd.to_numeric(d['X좌표'], errors='coerce'); yy = pd.to_numeric(d['Y좌표'], errors='coerce')
    lo, la = t.transform(x.values, yy.values); o['lon'] = lo; o['lat'] = la
    o['coord_method'] = 'source'; o['grade'] = 'C'; o['source_org'] = '서울특별시 소방재난본부'
    o['source_dataset'] = f'서울시 소방서 안전센터 구조대 위치정보 OA-21072 _{y}판'
    o['source_url'] = 'https://data.seoul.go.kr/dataList/OA-21072/S/1/datasetView.do'
    o['source_file'] = f'raw/OA-21072_소방위치_{y}.xlsx'; o['source_row_id'] = d['row'].astype(str)
    o['source_reference_date'] = str(y); o['reference_month_delta'] = None
    o['temporal_reason'] = f'연도판 {y}(기준월 미표기) — T{snap[:4]} 대응 연도판'
    o['type_label_source'] = d['유형구분명']; o['parent_id'] = d['상위서ㆍ센터ID']
    o['src_x_5186'] = x; o['src_y_5186'] = yy
    o = fac.attach_geo(o); o.loc[o['x_5179'].isna(), 'coord_method'] = 'unresolved'
    o = fac.write_out(o, HERE, TYP, snap)
    q = fac.qa_block(o); q['source_rows'] = len(d)
    qa[snap] = q
qa['sensitivity_2025_release_rows'] = len(pd.read_excel(RAW / 'OA-21072_소방위치_2025.xlsx', dtype=str))
a = set(fac.read_csv_any(HERE / 'facilities_fire_station_2020_01.csv')['facility_id']); b = set(o['facility_id'])
qa['panel'] = dict(common_ids=len(a & b), only_2020=sorted(a - b), only_2025=sorted(b - a))
qa['official_compare'] = '서울 경찰·소방관서 통계(data.go.kr 15046592) 대조 미실시(보류)'
fac.dump_qa(HERE, TYP, qa)
print({k: {kk: qa[k][kk] for kk in ['rows', 'coord_rate', 'outside_seoul', 'subtype']} for k in ['2020_01', '2025_01']}, qa['panel'], qa['sensitivity_2025_release_rows'])
