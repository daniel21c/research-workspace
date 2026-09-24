"""재지오코딩 좌표 위치 검증: 같은 address_key(도로명+건물번호)를 가진 '원천 좌표' 행들의 중앙 좌표와의 거리(EPSG:5179, m)."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
V1 = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(V1 / '01_인허가/_common'))
from lic_common import address_key
d = pd.concat([pd.read_parquet(f'facilities_일반음식점_{k}.parquet') for k in ('2020_01', '2025_01')]).drop_duplicates('facility_id')
d['k'] = d.address.map(address_key)
src = d[(d.coord_stage == 'source') & d.k.str.startswith('road')].groupby('k')[['x_5179', 'y_5179']].median()
g = d[(d.coord_stage == 'geocode_11')].join(src, on='k', rsuffix='_src').dropna(subset=['x_5179_src'])
dist = np.hypot(g.x_5179 - g.x_5179_src, g.y_5179 - g.y_5179_src)
res = {'n_geocoded_unique': int((d.coord_stage == 'geocode_11').sum()), 'n_with_same_address_source_rows': int(len(g)),
       'median_m': round(float(dist.median()), 1), 'p90_m': round(float(dist.quantile(.9)), 1), 'share_within_50m': round(float((dist <= 50).mean()), 4),
       'share_within_100m': round(float((dist <= 100).mean()), 4)}
json.dump(res, open('qa_geocode_position_일반음식점.json', 'w'), ensure_ascii=False, indent=1); print(res)
# 기준선: 원천 좌표끼리의 같은 주소 내 산포(각 원천 행 ↔ 같은 key 원천 중앙값)
s = d[(d.coord_stage == 'source') & d.k.str.startswith('road')]
cntk = s.k.value_counts(); s = s[s.k.isin(cntk[cntk >= 2].index)].join(src, on='k', rsuffix='_src')
ds = np.hypot(s.x_5179 - s.x_5179_src, s.y_5179 - s.y_5179_src)
res['baseline_source_vs_source'] = {'n': int(len(s)), 'median_m': round(float(ds.median()), 1), 'p90_m': round(float(ds.quantile(.9)), 1),
                                    'share_within_50m': round(float((ds <= 50).mean()), 4)}
# 참고: 원 빌드 CRS 검증(Kakao 건물번호 일치 vs 원천) 중앙값 3.4 m, 90% 19.5 m (01_인허가/_common/crs_check.json)
json.dump(res, open('qa_geocode_position_일반음식점.json', 'w'), ensure_ascii=False, indent=1); print(res['baseline_source_vs_source'])
