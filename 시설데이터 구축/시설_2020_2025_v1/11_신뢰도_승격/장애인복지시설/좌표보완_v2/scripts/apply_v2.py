# -*- coding: utf-8 -*-
"""좌표보완_v2 적용: 시설별 SPEC(수작업 조사 결과)을 읽어 좌표를 채우고, 원 빌드와 같은 함수로 공간 열을 재계산,
구별 좌표율·fill_log·parquet/csv를 좌표보완_v2/에 쓴다. 원본 폴더는 읽기만.
사용: python3 apply_v2.py <시설>"""
import sys, re, json
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v2lib
from specs_v2 import SPECS
import pandas as pd, numpy as np

FAC = sys.argv[1]
FD = HERE.parents[2] / FAC            # 11_신뢰도_승격/<시설>
OUT = FD / '좌표보완_v2'
sys.path.insert(0, str(FD / '_lib'))
import u11  # noqa  (mb, fac 읽기 전용 import)

def _num(s):
    try: return int(s or 0)
    except Exception: return -1

def resolve(q, kind):
    """Kakao 주소검색(캐시) → (lon, lat, matched_text). road: 도로명+본번+부번 일치, parcel: 지번 일치만."""
    docs = v2lib.kakao_addr(q).get('documents', [])
    if kind == 'road':
        m = re.search(r'([가-힣0-9]+(?:로|길))\s+(\d+)(?:-(\d+))?$', q)
        for d in docs:
            ra = d.get('road_address') or {}
            if ra and (ra.get('road_name') or '').replace(' ', '') == m.group(1) and _num(ra.get('main_building_no')) == int(m.group(2)) \
                    and _num(ra.get('sub_building_no')) == int(m.group(3) or 0):
                return float(ra['x']), float(ra['y']), 'road:' + ra['address_name']
    else:
        m = re.search(r'([가-힣0-9]+(?:동|가|리))\s+(산\s*)?(\d+)(?:-(\d+))?$', q)
        for d in docs:
            ja = d.get('address') or {}
            if ja and m.group(1) in (ja.get('address_name') or '') and _num(ja.get('main_address_no')) == int(m.group(3)) \
                    and _num(ja.get('sub_address_no')) == int(m.group(4) or 0) and (ja.get('mountain_yn') == 'Y') == bool(m.group(2)):
                return float(ja['x']), float(ja['y']), 'jibun:' + ja['address_name']
    # VWorld 보조
    r = v2lib.vw_coord(q, 'road' if kind == 'road' else 'parcel').get('response', {})
    if r.get('status') == 'OK':
        pt = r['result']['point']; return float(pt['x']), float(pt['y']), 'vworld:' + (r.get('refined') or {}).get('text', '')
    raise RuntimeError(f'resolve failed: {q}')

cfg = SPECS[FAC]
gu_col = cfg['gu_col']
summary = {}
logs = []
cb_rows = []
for snap in ['2020_01', '2025_01']:
    d = pd.read_parquet(FD / f'facilities_{FAC}_{snap}.parquet')
    d0 = d.copy()
    for c in ['coord_evidence_url', 'coord_second_source', 'coord_v2_how', 'coord_v2_addr_used', 'coord_confidence', 'coord_v2_note']:
        d[c] = pd.Series([''] * len(d), index=d.index, dtype='string')
    idx = {fid: i for i, fid in zip(d.index, d.facility_id)}
    for s in [s for s in cfg['fills'] if s['snap'] == snap]:
        i = idx[s['id']]
        assert pd.isna(d.at[i, 'x_5179']), (snap, s['id'], 'already has coord')
        lon, lat, matched = resolve(s['q'], s['kind'])
        d.at[i, 'lon'] = lon; d.at[i, 'lat'] = lat
        d.at[i, 'coord_method'] = s.get('method', 'search_verified')
        d.at[i, 'coord_stage'] = 'filled_v2'
        d.at[i, 'geocode_detail2'] = f"v2:{matched}"
        for k, c in [('url', 'coord_evidence_url'), ('second', 'coord_second_source'), ('how', 'coord_v2_how'), ('conf', 'coord_confidence'), ('note', 'coord_v2_note')]:
            d.at[i, c] = s.get(k, '')
        d.at[i, 'coord_v2_addr_used'] = s['q']
    # 공간 열 재계산(filled_v2 행만, 원 빌드와 같은 함수)
    m = d.coord_stage == 'filled_v2'
    if m.any():
        sub = d.loc[m, ['lon', 'lat']].reset_index(drop=True)
        r = u11.mb.spatial(sub) if cfg['lib'] == 'mb' else u11.fac.attach_geo(sub)
        for c in ['x_5179', 'y_5179', 'inside_seoul', 'adm_dong_cd', 'oa_cd', 'grid100_cd']:
            vals = r[c].values
            if c in ('x_5179', 'y_5179'):
                d.loc[m, c] = pd.to_numeric(pd.Series(vals), errors='coerce').values
            elif c == 'inside_seoul':
                was_bool = str(d0[c].dtype) == 'boolean'
                d[c] = d[c].astype(object)
                d.loc[m, c] = [None if (v is None or v is pd.NA or (isinstance(v, float) and v != v)) else bool(v) for v in vals]
                if was_bool:
                    d[c] = d[c].map(lambda v: pd.NA if (v is None or v is pd.NA) else bool(v)).astype('boolean')
                elif d0[c].map(lambda v: isinstance(v, str)).any():      # 원 빌드가 'True'/'False' 문자열로 저장
                    d.loc[m, c] = [None if v is None else str(v) for v in d.loc[m, c]]
            else:
                d[c] = d[c].astype(object); d.loc[m, c] = vals
        for c in ['x_5179', 'y_5179']:
            d.loc[m, c] = d.loc[m, c].astype(float).round(2)
        for c in ['adm_dong_cd', 'oa_cd', 'grid100_cd', 'gu_point']:
            if c in d0 and str(d0[c].dtype) == 'string':
                d[c] = d[c].astype('string')
        if 'location_outside_seoul' in d:
            d.loc[m, 'location_outside_seoul'] = d.loc[m, 'location_outside_seoul'].astype(bool) | (d.loc[m, 'inside_seoul'].astype(str) == 'False')
        if 'gu_point' in d:
            dn = u11.sgis_dongs('2025_2Q'); cd2gu = dict(zip(dn.CD.astype(str).str[:5], dn.gu))
            d.loc[m, 'gu_point'] = d.loc[m, 'adm_dong_cd'].fillna('').astype(str).str[:5].map(cd2gu)
    # 로그
    for i in d.index[m]:
        logs.append(dict(snap=snap, facility_id=d.at[i, 'facility_id'], scope_flag=d.at[i, 'scope_flag'] if 'scope_flag' in d else '',
                         gu=d.at[i, gu_col], name=d.at[i, 'name'], address_명부=d.at[i, 'address'],
                         old_coord_method=d0.at[i, 'coord_method'], old_lon=d0.at[i, 'lon'], old_lat=d0.at[i, 'lat'],
                         new_lon=round(d.at[i, 'lon'], 7), new_lat=round(d.at[i, 'lat'], 7), new_coord_method=d.at[i, 'coord_method'],
                         addr_used=d.at[i, 'coord_v2_addr_used'], matched=d.at[i, 'geocode_detail2'], how=d.at[i, 'coord_v2_how'],
                         evidence_url=d.at[i, 'coord_evidence_url'], second_source=d.at[i, 'coord_second_source'],
                         confidence=d.at[i, 'coord_confidence'], note=d.at[i, 'coord_v2_note'],
                         adm_dong_cd=d.at[i, 'adm_dong_cd'], inside_seoul=d.at[i, 'inside_seoul'], gu_point=d.at[i, 'gu_point'] if 'gu_point' in d else ''))
    # 구별 좌표율(범위별)
    summ = {}
    rows = []
    for sc in cfg['scopes']:
        x = d if sc == 'all' else d[d.scope_flag == sc]; x0 = d0 if sc == 'all' else d0[d0.scope_flag == sc]
        xin = x[~x.location_outside_seoul.astype(bool)] if 'location_outside_seoul' in x else x
        xin0 = x0[~x0.location_outside_seoul.astype(bool)] if 'location_outside_seoul' in x0 else x0
        cov = u11.gu_coverage(xin, gu_col, xin['x_5179'].notna()); cov0 = u11.gu_coverage(xin0, gu_col, xin0['x_5179'].notna())
        for g in cov.index:
            rows.append(dict(snap=snap, scope_flag=sc, gu=g, n=int(cov.loc[g, 'n']), coord_before=int(cov0.loc[g, 'coord']), coord_after=int(cov.loc[g, 'coord']),
                             rate_before=cov0.loc[g, 'rate'], rate_after=cov.loc[g, 'rate']))
        c2 = cov[cov.n > 0]
        if len(x) == 0:
            continue
        summ[sc] = dict(n=len(x), coord_before=int(x0.x_5179.notna().sum()), coord_after=int(x.x_5179.notna().sum()),
                        rate_before=round(float(x0.x_5179.notna().mean()), 4), rate_after=round(float(x.x_5179.notna().mean()), 4),
                        n_seoul_located=len(xin), rate_after_seoul_located=round(float(xin.x_5179.notna().mean()), 4),
                        rate_before_seoul_located=round(float(xin0.x_5179.notna().mean()), 4),
                        min_gu=str(c2.rate.idxmin()) if len(c2) else None, min_gu_rate=float(c2.rate.min()) if len(c2) else None, gu_below_85=c2.index[c2.rate < 0.85].tolist(),
                        filled_v2=int((x.coord_stage == 'filled_v2').sum()), still_missing=int(x.x_5179.isna().sum()),
                        still_missing_ids=x.loc[x.x_5179.isna(), 'facility_id'].tolist())
    summary[snap] = summ
    cb_rows += rows
    # 저장(모든 행 유지)
    assert len(d) == len(d0) and (d.facility_id.values == d0.facility_id.values).all()
    d.to_parquet(OUT / f'facilities_{FAC}_{snap}.parquet', index=False)
    d.to_csv(OUT / f'facilities_{FAC}_{snap}.csv', index=False, encoding='utf-8-sig')
pd.DataFrame(cb_rows).to_csv(OUT / f'coord_by_gu_{FAC}_v2.csv', index=False, encoding='utf-8-sig')
pd.DataFrame(logs).to_csv(OUT / f'fill_log_{FAC}.csv', index=False, encoding='utf-8-sig')
json.dump(summary, open(OUT / f'summary_{FAC}_v2.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(summary, ensure_ascii=False, indent=1, default=str))
