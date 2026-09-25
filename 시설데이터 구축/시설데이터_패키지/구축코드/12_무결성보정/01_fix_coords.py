# -*- coding: utf-8 -*-
"""facility-v1.1 무결성 보정 1 — 좌표 (2026-09-25).
1) 어린이집: 원천(OA-20300) 좌표가 기본값(서울시청 126.977963, 37.566470)이거나 좌표 자치구 ≠ 주소 자치구인 행 → 주소 정확일치 재지오코딩(결과 좌표 구 = 주소 구일 때만 채택).
   실패 시 기본값 행은 unresolved(좌표 제거), 그 밖의 행은 원천 좌표 유지(coord_fix_note에 검토 필요 표시).
   입력 11_신뢰도_승격/어린이집/ (채택 원본) → 출력 ../데이터/시설별/어린이집/
2) 공공체육 SPO00377 2025: 명부 주소 오기(강남구) → OA-21779 주소(양천구 목동동로 87) 정확일치 좌표.
   입력·출력 ../데이터/민감도용/공공체육_핵심종목/ (같은 결과를 내므로 다시 실행해도 됨)
실행 순서: 01_fix_coords.py → 02_fix_suspension.py → 04_fill_geocode.py → ../build_통합.py → ../build_분석용.py
API 키는 mb.keys()로 읽기만 하고 출력·저장하지 않는다."""
import sys, re, json, glob, os, hashlib, shutil
sys.dont_write_bytecode = True
from pathlib import Path
import pandas as pd

ST = Path(__file__).resolve().parent
V1 = ST.parent
DATA = V1.parent / '데이터'   # 시설데이터_패키지/데이터

sys.path.insert(0, str(V1 / '02_명부' / '_lib'))
import mb
CACHE = ST / 'cache'
PH = (126.977963, 37.56647)
GU_RE = r'(종로|중|용산|성동|광진|동대문|중랑|성북|강북|도봉|노원|은평|서대문|마포|양천|강서|구로|금천|영등포|동작|관악|서초|강남|송파|강동)구'
log = []


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()


def gu_codes():
    """SGIS 2025_2Q 시군구 경계에서 서울 자치구명 → 5자리 코드(행정동 코드 앞 5자리와 같은 체계)."""
    import geopandas as gpd
    g = gpd.read_file(mb.BND / '03_행정구역' / '경계_2025_2Q' / 'bnd_sigungu_00_2025_2Q' / 'bnd_sigungu_00_2025_2Q.shp', ignore_geometry=True)
    g = g[g.SIGUNGU_CD.astype(str).str.startswith('11')]
    m = dict(zip(g.SIGUNGU_NM.astype(str), g.SIGUNGU_CD.astype(str)))
    assert len(m) == 25, m
    return m


def save(d, base):
    for c in d.columns:
        if d[c].dtype == object or str(d[c].dtype) == 'str': d[c] = d[c].astype('string')
    Path(base).parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(str(base) + '.parquet', index=False)
    d.to_csv(str(base) + '.csv', index=False, encoding='utf-8-sig')


def put_spatial(d, i, lon, lat):
    s = mb.spatial(pd.DataFrame({'lon': [lon], 'lat': [lat]}))
    d.loc[i, ['lon', 'lat']] = [lon, lat]
    for c in ['x_5179', 'y_5179', 'adm_dong_cd', 'oa_cd', 'grid100_cd', 'inside_seoul']:
        v = s.at[0, c]
        if str(d[c].dtype) in ('str', 'string', 'object'): v = '' if pd.isna(v) else str(v)
        elif pd.isna(v): v = pd.NA
        d.loc[i, c] = v


def fix_childcare(gcode):
    for y in ['2020', '2025']:
        d = pd.read_parquet(V1 / '11_신뢰도_승격' / '어린이집' / f'facilities_어린이집_{y}_01.parquet')
        d['coord_fix_note'] = pd.Series(pd.NA, index=d.index, dtype='string')
        ph = (d.lon.round(6) == PH[0]) & (d.lat.round(6) == PH[1])
        agu = d.address.astype(str).str.extract(GU_RE, expand=False) + '구'
        cgu = d.adm_dong_cd.fillna('').astype(str).str[:5]
        mis = d.lon.notna() & agu.notna() & (cgu != '') & (cgu != agu.map(gcode))   # 좌표 자치구 ≠ 주소 자치구
        hit = d.index[ph | mis]
        for i in hit:
            addr = str(d.at[i, 'address'] or '')
            m = re.search(GU_RE, addr); gu = m.group(0) if m else None
            if not ph[i]:
                lon0, lat0 = d.at[i, 'lon'], d.at[i, 'lat']
            lon, lat, meth, det = mb.geocode(addr, CACHE)
            ok = False
            if lon is not None:
                cd = str(mb.spatial(pd.DataFrame({'lon': [lon], 'lat': [lat]})).at[0, 'adm_dong_cd'] or '')
                ok = gu is not None and cd[:5] == gcode.get(gu)
            why = '원천 좌표가 기본값(서울시청)' if ph[i] else '원천 좌표의 자치구가 주소 자치구와 다름'
            if ok:
                moved = None if ph[i] else round(float(((pd.Series(mb.spatial(pd.DataFrame({'lon': [lon0], 'lat': [lat0]}))[['x_5179', 'y_5179']].iloc[0]).astype(float).values - pd.Series(mb.spatial(pd.DataFrame({'lon': [lon], 'lat': [lat]}))[['x_5179', 'y_5179']].iloc[0]).astype(float).values) ** 2).sum() ** 0.5), 1)
                put_spatial(d, i, lon, lat)
                d.at[i, 'coord_method'] = meth + ('_fix_placeholder' if ph[i] else '_fix_gu_mismatch')
                d.at[i, 'coord_fix_note'] = f'{why} → 주소 재지오코딩({det}), 2026-09-25' + (f', 이동 {moved} m' if moved is not None else '')
                res = 'fixed'
            elif not ph[i]:
                d.at[i, 'coord_fix_note'] = f'{why}, 주소 정확일치 실패({det}) → 원천 좌표 유지(검토 필요), 2026-09-25'
                res = 'kept_review'
            else:
                for c in ['lon', 'lat', 'x_5179', 'y_5179']: d.at[i, c] = pd.NA
                for c in ['adm_dong_cd', 'oa_cd', 'grid100_cd']: d.at[i, c] = ''
                d.at[i, 'inside_seoul'] = pd.NA
                d.at[i, 'coord_method'] = 'unresolved'
                d.at[i, 'coord_fix_note'] = f'원천 좌표가 기본값(서울시청), 주소 정확일치 실패({det}) → 좌표 제거, 2026-09-25'
                res = 'unresolved'
            log.append(dict(target='어린이집', year=y, facility_id=d.at[i, 'facility_id'], name=d.at[i, 'name'], address=addr, result=res,
                            new_lon=d.at[i, 'lon'], new_lat=d.at[i, 'lat'], adm_dong_cd=d.at[i, 'adm_dong_cd'], note=d.at[i, 'coord_fix_note']))
        save(d, DATA / '시설별' / '어린이집' / f'facilities_어린이집_{y}_01')


def fix_spo00377(gcode):
    src = DATA / '민감도용' / '공공체육_핵심종목' / 'facilities_공공체육_핵심종목_2025_01.parquet'
    d = pd.read_parquet(src)
    i = d.index[d.facility_id == 'SPO00377']; assert len(i) == 1; i = i[0]
    lon, lat, meth, det = mb.geocode('서울특별시 양천구 목동동로 87', CACHE); assert lon is not None
    put_spatial(d, i, lon, lat)
    assert str(d.at[i, 'adm_dong_cd'])[:5] == gcode['양천구']
    d.at[i, 'coord_method'] = 'borrowed_official_list_name_gu'
    if 'borrow_source' in d.columns:
        d.at[i, 'borrow_source'] = 'OA-21779 체육시설일련번호=1233 | 양천구민체육센터 수영장 | 수영장 | 서울특별시 양천구 목동동로 87 (명부 주소 오기 교정, 2026-09-25)'
    if 'coord_v2_status' in d.columns: d.at[i, 'coord_v2_status'] = 'fixed_roster_address_error_20260925'
    save(d, DATA / '민감도용' / '공공체육_핵심종목' / 'facilities_공공체육_핵심종목_2025_01')
    log.append(dict(target='공공체육_핵심종목', year='2025', facility_id='SPO00377', name=d.at[i, 'name'], address=d.at[i, 'address'],
                    result='fixed', new_lon=lon, new_lat=lat, adm_dong_cd=d.at[i, 'adm_dong_cd']))


if __name__ == '__main__':
    g = gu_codes()
    fix_childcare(g)
    fix_spo00377(g)
    pd.DataFrame(log).to_csv(ST / 'fix_log_coords.csv', index=False, encoding='utf-8-sig')
    print(pd.DataFrame(log)[['target', 'year', 'facility_id', 'name', 'result', 'adm_dong_cd']].to_string())
