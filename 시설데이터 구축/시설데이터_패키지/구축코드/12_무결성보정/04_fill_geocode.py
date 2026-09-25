# -*- coding: utf-8 -*-
"""facility 보정 3 — 원천 좌표가 없는 행의 주소 지오코딩 (2026-09-25).
대상: ../데이터/시설별/휴게음식점, 미용업 (원 빌드가 원천 좌표만 쓰고 결측을 지오코딩하지 않은 유형)의 coord_method='unresolved' 행.
규칙: 원 빌드와 같은 mb.geocode(Kakao → VWorld, 도로명+건물번호 또는 지번 번지 정확 일치만), 주소 표기 정리 변형(coord_fill.normalize_variants)
      순서대로 시도. 결과 좌표의 자치구가 주소 자치구와 같을 때만 채택 → coord_method = geocode_*_exact_fill. 실패하면 unresolved 유지.
출력: 같은 파일 덮어씀(이미 채운 행은 다시 건드리지 않음), 로그 fix_log_fill_geocode.csv. API 키는 읽기만 하고 출력·저장하지 않는다.
실행: python 04_fill_geocode.py"""
import sys, re
sys.dont_write_bytecode = True
from pathlib import Path
import pandas as pd
ST = Path(__file__).resolve().parent; V1 = ST.parent
DATA = V1.parent / '데이터'   # 시설데이터_패키지/데이터
sys.path.insert(0, str(V1 / '02_명부' / '_lib')); sys.path.insert(0, str(V1 / '02_명부' / '공공체육시설'))
import mb
import coord_fill as CF
CACHE = ST / 'cache'
TARGETS = ['휴게음식점', '미용업']
GU_RE = r'((?:종로|중|용산|성동|광진|동대문|중랑|성북|강북|도봉|노원|은평|서대문|마포|양천|강서|구로|금천|영등포|동작|관악|서초|강남|송파|강동)구)'


def gu_codes():
    import geopandas as gpd
    g = gpd.read_file(mb.BND / '03_행정구역' / '경계_2025_2Q' / 'bnd_sigungu_00_2025_2Q' / 'bnd_sigungu_00_2025_2Q.shp', ignore_geometry=True)
    g = g[g.SIGUNGU_CD.astype(str).str.startswith('11')]
    return dict(zip(g.SIGUNGU_NM.astype(str), g.SIGUNGU_CD.astype(str)))


def try_addr(addr):
    for v in dict.fromkeys([mb.clean(addr)] + CF.normalize_variants(addr)):
        lon, lat, meth, det = mb.geocode(v, CACHE)
        if lon is not None: return lon, lat, meth, det, v
    return None


def main():
    gcode = gu_codes(); log = []
    for fac in TARGETS:
        for y in ['2020', '2025']:
            f = DATA / '시설별' / fac / f'facilities_{fac}_{y}_01.parquet'
            d = pd.read_parquet(f)
            if 'coord_fix_note' not in d.columns: d['coord_fix_note'] = pd.Series(pd.NA, index=d.index, dtype='string')
            idx = d.index[(d.coord_method == 'unresolved') & d.address.fillna('').str.strip().ne('')]
            addrs = list(dict.fromkeys(d.loc[idx, 'address'].tolist()))
            res = {a_: try_addr(a_) for a_ in addrs}   # 순차 실행(Windows에서 캐시 파일 동시 쓰기 충돌 방지)
            ok_rows = []
            for i in idx:
                addr = d.at[i, 'address']; r = res.get(addr); m = re.search(GU_RE, addr); gu = m.group(1) if m else None
                if r is None: log.append(dict(시설=fac, year=y, facility_id=d.at[i, 'facility_id'], address=addr, result='no_exact_match')); continue
                ok_rows.append((i, r, gu))
            if ok_rows:
                sp = mb.spatial(pd.DataFrame({'lon': [r[0] for _, r, _ in ok_rows], 'lat': [r[1] for _, r, _ in ok_rows]}))
                for k, (i, r, gu) in enumerate(ok_rows):
                    cd = str(sp.at[k, 'adm_dong_cd'] or '')
                    if gu is None or cd[:5] != gcode.get(gu):
                        log.append(dict(시설=fac, year=y, facility_id=d.at[i, 'facility_id'], address=d.at[i, 'address'], result='gu_mismatch_rejected', detail=r[3])); continue
                    d.loc[i, ['lon', 'lat']] = [r[0], r[1]]
                    for c in ['x_5179', 'y_5179', 'adm_dong_cd', 'oa_cd', 'grid100_cd', 'inside_seoul']:
                        v = sp.at[k, c]
                        if str(d[c].dtype) in ('str', 'string', 'object'): v = '' if pd.isna(v) else str(v)
                        d.loc[i, c] = v
                    d.at[i, 'coord_method'] = r[2] + '_fill'
                    d.at[i, 'coord_fix_note'] = f'원천 좌표 없음 → 주소 정확일치 지오코딩({r[3]}), 2026-09-25'
                    log.append(dict(시설=fac, year=y, facility_id=d.at[i, 'facility_id'], address=d.at[i, 'address'], result='filled', detail=r[3]))
            for c in d.columns:
                if d[c].dtype == object or str(d[c].dtype) == 'str': d[c] = d[c].astype('string')
            d.to_parquet(f, index=False); d.to_csv(str(f).replace('.parquet', '.csv'), index=False, encoding='utf-8-sig')
            print(fac, y, 'target', len(idx), 'filled', sum(1 for x in log if x['시설'] == fac and x['year'] == y and x['result'] == 'filled'), flush=True)
    L = pd.DataFrame(log); L.to_csv(ST / 'fix_log_fill_geocode.csv', index=False, encoding='utf-8-sig')
    print(L.groupby(['시설', 'year', 'result']).size().to_string())


if __name__ == '__main__':
    main()
