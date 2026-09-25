"""EPSG:5174 원천 좌표 변환 검증: 여러 업종의 무작위 표본을 도로명주소로 Kakao 지오코딩(건물번호 일치만)해 거리 비교."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from lic_common import LIC_ROOT, address_key, geocode_one, load_keys, tf
secret = load_keys()
rows = []
for T, n in (('의원', 60), ('병원급', 20), ('약국', 30), ('일반음식점', 40), ('체육시설업', 20), ('대규모점포', 10)):
    p = LIC_ROOT / T / f'facilities_{T}_2025_01.parquet'
    if not p.exists():
        continue
    d = pd.read_parquet(p)
    d = d[(d.coord_method == 'source')]
    d = d[d.address.map(lambda a: address_key(a).startswith('road:'))].sample(n, random_state=42)
    for r in d.itertuples():
        k = address_key(r.address)
        g = geocode_one(k, secret, LIC_ROOT / T / 'raw' / 'geocoding')
        if g:
            gx, gy = tf(4326, 5179).transform(g[0], g[1])
            rows.append({'type': T, 'facility_id': r.facility_id, 'address': r.address, 'dist_m': float(np.hypot(gx - r.x_5179, gy - r.y_5179)),
                         'dx_m': gx - r.x_5179, 'dy_m': gy - r.y_5179})
df = pd.DataFrame(rows)
res = {'method': 'pyproj EPSG:5174→5179 (Korean 1985 → WGS84 Molodensky-Badekas, EPSG 기본 변환) 결과와 Kakao 주소검색(도로명+건물번호 정확 일치) 좌표 비교',
       'n': int(len(df)), 'median_m': round(float(df.dist_m.median()), 1), 'p90_m': round(float(df.dist_m.quantile(.9)), 1),
       'share_le_50m': round(float((df.dist_m <= 50).mean()), 3), 'share_100_300m': round(float(df.dist_m.between(100, 300).mean()), 3),
       'mean_dx_m': round(float(df.dx_m.mean()), 1), 'mean_dy_m': round(float(df.dy_m.mean()), 1),
       'median_dx_m': round(float(df.dx_m.median()), 1), 'median_dy_m': round(float(df.dy_m.median()), 1),
       'by_type_median_m': df.groupby('type').dist_m.median().round(1).to_dict(),
       'landmarks_manual': '서울대병원·삼성서울·서울아산·강북삼성·국립중앙의료원·고대구로 변환좌표가 실제 위치와 수십 m 이내(2026-09-24 확인)',
       'verdict': None}
res['verdict'] = ('체계적 편차 없음 — 보정계수 추가 적용 불필요' if res['median_m'] < 50 and abs(res['median_dx_m']) < 30 and abs(res['median_dy_m']) < 30
                  else '체계적 편차 의심 — 검토 필요')
df.to_csv(Path(__file__).parent / 'crs_check_sample.csv', index=False, encoding='utf-8-sig')
(Path(__file__).parent / 'crs_check.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(res, ensure_ascii=False))
