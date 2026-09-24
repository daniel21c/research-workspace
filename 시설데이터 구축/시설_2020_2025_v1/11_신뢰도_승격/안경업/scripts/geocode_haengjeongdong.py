# -*- coding: utf-8 -*-
"""안경업 좌표 결측(주로 강동구 '성내3동 429번지 3호'처럼 행정동명+지번 주소) 보완.
행정동명(성내3동·길2동 등)을 법정동명(성내동·길동)으로 바꾼 지번 키를 만들어 lic_common.geocode_one(Kakao exact → VWorld)으로 조회,
번지까지 일치한 결과만 채택. 좌표 채운 행은 lic_common.spatial_attach 로 inside_seoul·adm_dong_cd·oa_cd·grid100_cd 산출(원 빌드와 동일).
원본 01_인허가는 읽기만, 결과는 11_신뢰도_승격/안경업/ 에 저장."""
import re, sys, json
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent; OUT = HERE.parent
V1 = HERE.parents[2]; sys.path.insert(0, str(V1 / '01_인허가/_common'))
import lic_common as L
CACHE = OUT / 'raw/geocoding'
def hkey(addr):
    a = re.sub(r'^서울(?:특별시|시)\s*', '', str(addr)).strip()
    m = re.match(r'([가-힣]+구)\s+([가-힣]+?)(\d+)?동\s+(?:산\s*)?(\d+)(?:번지)?\s*(?:(\d+)호)?', a)
    if not m: return ''
    gu, dong, _, b1, b2 = m.groups()
    return f'parcel:{gu}|{dong}동|{b1}' + (f'-{b2}' if b2 else '')
sec = L.load_keys(); log = {}
for y in ('2020', '2025'):
    d = pd.read_parquet(V1 / f'01_인허가/안경업/facilities_안경업_{y}_01.parquet')
    d['coord_stage'] = d.lon.notna().map({True: 'original', False: 'missing'})
    miss = d.index[d.lon.isna()]; res = []
    for i in miss:
        k = L.address_key(d.at[i, 'address']); k2 = hkey(d.at[i, 'address'])
        g = L.geocode_one(k, sec, CACHE) if k else None
        if g is None and k2 and k2 != k: g = L.geocode_one(k2, sec, CACHE); used = k2
        else: used = k
        res.append(dict(idx=int(i), name=d.at[i, 'name'], address=d.at[i, 'address'], key=k, key_hjd=k2, ok=g is not None, method=g[2] if g else None))
        if g:
            lon, lat, meth = g; x, yv = L.tf('EPSG:4326', 'EPSG:5179').transform(lon, lat)
            d.loc[i, ['lon', 'lat', 'x_5179', 'y_5179']] = [lon, lat, x, yv]
            d.at[i, 'coord_method'] = meth + ('_hjd2bjd' if used == k2 and k2 != k else '')
            d.at[i, 'coord_stage'] = 'regeocode_11'
    fix = d.coord_stage == 'regeocode_11'
    if fix.any():
        sa = L.spatial_attach(d.loc[fix, ['x_5179', 'y_5179']].assign(inside_seoul=None, adm_dong_cd=None, oa_cd=None, grid100_cd=None))
        for c in ('inside_seoul', 'adm_dong_cd', 'oa_cd', 'grid100_cd'): d.loc[fix, c] = sa[c].values
    d['scope_flag'] = ''
    d.to_parquet(OUT / f'facilities_안경업_{y}_01.parquet', index=False); d.to_csv(OUT / f'facilities_안경업_{y}_01.csv', index=False, encoding='utf-8-sig')
    log[y] = dict(missing_before=len(miss), filled=int(fix.sum()), coord_rate_before=round(1 - len(miss) / len(d), 4),
                  coord_rate_after=round(float(d.lon.notna().mean()), 4), rows=res)
(OUT / 'geocode_log_안경업.json').write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')
print({y: {k: v for k, v in l.items() if k != 'rows'} for y, l in log.items()})
print(pd.DataFrame(log['2020']['rows'])[['address', 'key_hjd', 'ok', 'method']].to_string())
