"""재지오코딩 결과(캐시)를 원 빌드 파일에 반영해 11_신뢰도_승격/<시설>/facilities_<시설>_20XX_01.parquet/.csv 작성.
- 원본(01_인허가/<시설>/) 은 읽기만 한다.
- 좌표 없는 행: 도로명주소 key → address key → 지번주소 key 순으로, 캐시 응답 중 건물번호/번지 정확 일치만 채택(lic_common.geocode_one; 네트워크 호출 없음).
- 채운 행: lon/lat → EPSG:5179, inside_seoul·adm_dong_cd·oa_cd·grid100_cd 를 lic_common.spatial_attach(원 빌드와 동일)로 부여.
- 추가 컬럼: coord_stage(source / geocode_11 / unresolved), gu_org, gu_addr, gu, gu_coord.
사용: python apply_geocode.py <시설>
"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; V1 = next(p for p in Path(__file__).resolve().parents if (p / '01_인허가').exists())
sys.path.insert(0, str(V1 / '01_인허가/_common')); sys.path.insert(0, str(HERE))
from lic_common import geocode_one, tf, spatial_attach
from gu import add_gu
FAC = sys.argv[1]
OUT = V1 / '11_신뢰도_승격' / FAC; LIC = V1 / '01_인허가' / FAC; CACHE = OUT / 'raw/geocoding'
cand = pd.read_parquet(OUT / 'raw/geocode_candidates.parquet')
if 'key_parcel2' not in cand: cand['key_parcel2'] = ''
idx_ = pd.read_parquet(OUT / 'raw/geocode_index.parquet')
hitmap = {k: (lo, la, m) for k, lo, la, m in zip(idx_.key, idx_.lon, idx_.lat, idx_.method) if m}
res = {}
for fid, *ks in zip(cand.facility_id, cand.key_road, cand.key_addr, cand.key_parcel, cand.key_parcel2):
    hit = None
    for c, k in zip(('key_road', 'key_addr', 'key_parcel', 'key_parcel2'), ks):
        if k and k in hitmap:
            hit = (*hitmap[k], c, k); break
    res[fid] = hit
qa = {'facility': FAC, 'candidates_unique_facilities': int(len(cand)),
      'accepted_unique_facilities': int(sum(1 for v in res.values() if v)),
      'by_key_type': pd.Series([v[3] for v in res.values() if v]).value_counts().to_dict(),
      'by_method': pd.Series([v[2] for v in res.values() if v]).value_counts().to_dict(),
      'no_parsable_key': int(((cand.key_road == '') & (cand.key_addr == '') & (cand.key_parcel == '') & (cand.key_parcel2 == '')).sum())}
for k in ('2020_01', '2025_01'):
    d = pd.read_parquet(LIC / f'facilities_{FAC}_{k}.parquet')
    d['coord_stage'] = np.where(d.coord_method == 'unresolved', 'unresolved', 'source')
    d.loc[d.coord_method.str.startswith('geocode'), 'coord_stage'] = 'geocode_build'   # 원 빌드에서 이미 지오코딩된 행
    m = (d.coord_method == 'unresolved') & d.facility_id.map(lambda f: bool(res.get(f)))
    idx = d.index[m]
    if len(idx):
        lo = np.array([res[f][0] for f in d.loc[idx, 'facility_id']]); la = np.array([res[f][1] for f in d.loc[idx, 'facility_id']])
        X, Y = tf(4326, 5179).transform(lo, la)
        d.loc[idx, 'lon'] = lo; d.loc[idx, 'lat'] = la; d.loc[idx, 'x_5179'] = X; d.loc[idx, 'y_5179'] = Y
        d.loc[idx, 'coord_method'] = [res[f][2] for f in d.loc[idx, 'facility_id']]
        d.loc[idx, 'coord_stage'] = 'geocode_11'
        sub = spatial_attach(d.loc[idx, ['x_5179', 'y_5179']].copy())
        for c in ('inside_seoul', 'adm_dong_cd', 'oa_cd', 'grid100_cd'):
            d[c] = d[c].astype(object); d.loc[idx, c] = sub[c].values
    d = add_gu(d)
    ok = d.coord_method != 'unresolved'
    ins = ok & (d.inside_seoul == True)
    qa[k] = {'n': int(len(d)), 'coord_rate_before': round(float(d.coord_stage.isin(['source', 'geocode_build']).mean()), 4),
             'coord_rate_after': round(float(ok.mean()), 4), 'inside_seoul_coord_rate_after': round(float(ins.mean()), 4),
             'filled_rows': int(len(idx)), 'unresolved_after': int((~ok).sum()), 'outside_seoul': int((ok & (d.inside_seoul == False)).sum()),
             'gu_coord_mismatch_among_filled': int(((d.coord_stage == 'geocode_11') & d.gu_coord.notna() & (d.gu_coord != d.gu)).sum())}
    d.to_parquet(OUT / f'facilities_{FAC}_{k}.parquet', index=False)
    d.to_csv(OUT / f'facilities_{FAC}_{k}.csv', index=False, encoding='utf-8-sig')
(OUT / f'qa_geocode_{FAC}.json').write_text(json.dumps(qa, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(qa, ensure_ascii=False, indent=1))
