# -*- coding: utf-8 -*-
"""facility 배포본 무결성 검증 (읽기 전용, 2026-09-25). 결과: 검증결과.json, 좌표구_주소구_불일치.csv (이 폴더).
검사: 33종 × 2시점, 중복 키(허용 BUS_15143 2020 1건), lon/lat ↔ x/y 일관, grid100_cd, 행정동·inside_seoul 일관,
시설×시점×자치구 분석가능 비율 ≥85%, 기본값 좌표(같은 좌표가 3개 이상 자치구 주소에 쓰임), 좌표 자치구 ≠ 주소 자치구(주소 구 경계까지 거리),
통합본(10_신뢰도_상) 행 수 대조, 두 빌드 스크립트 재실행 재현(임시 폴더, 해시·내용 비교).
실행: python 03_verify_package.py"""
import os, sys, re, json, hashlib, subprocess, tempfile
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; V1 = HERE.parent
sys.path.insert(0, str(V1 / '02_명부' / '_lib'))
import mb
F = V1 / '20_분석용' / '서울시설_2020_2025_분석용.parquet'
GU_RE = r'((?:종로|중|용산|성동|광진|동대문|중랑|성북|강북|도봉|노원|은평|서대문|마포|양천|강서|구로|금천|영등포|동작|관악|서초|강남|송파|강동)구)'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()


def main():
    import geopandas as gpd
    from pyproj import Transformer
    o = {'file': F.relative_to(V1).as_posix(), 'sha256': sha(F)}
    a = pd.read_parquet(F)
    o['rows'] = len(a); o['n_facility'] = int(a['시설'].nunique())
    per = a.groupby(['시설', 'year']).size().unstack()
    o['all_33_both_years'] = bool(o['n_facility'] == 33 and per.notna().all().all() and set(per.columns) == {2020, 2025})
    dup = a[a.duplicated(['시설', 'facility_id', 'year'], keep=False)][['시설', 'facility_id', 'year']].drop_duplicates()
    o['dup_keys'] = dup.astype(str).values.tolist()
    o['dup_ok'] = set(map(tuple, dup.values.tolist())) <= {('버스정류장', 'BUS_15143', 2020)}
    ok = a.lon.notna() & a.x_5179.notna()
    xs, ys = Transformer.from_crs(4326, 5179, always_xy=True).transform(a.loc[ok, 'lon'].values, a.loc[ok, 'lat'].values)
    o['xy_lonlat_max_m'] = round(float(np.nanmax(np.hypot(xs - a.loc[ok, 'x_5179'], ys - a.loc[ok, 'y_5179']))), 3)
    gc = pd.Series([mb.grid100(x, y) for x, y in zip(a.loc[ok, 'x_5179'], a.loc[ok, 'y_5179'])], index=a.index[ok])
    o['grid_mismatch_on_100m_line'] = int((gc != a.loc[ok, 'grid100_cd']).sum())
    dong = a.adm_dong_cd.fillna('').astype(str)
    o['inside_dong_inconsistent'] = int((a.inside_seoul & (dong == '')).sum() + (~a.inside_seoul & (dong != '')).sum())
    o['unresolved_with_coord'] = int(((a.coord_method == 'unresolved') & a.lon.notna()).sum())
    o['분석가능_pct'] = round(a['분석가능'].mean() * 100, 2)
    a['gu_addr'] = a.address.str.extract(GU_RE, expand=False)
    low = []
    for (f, y), g in a[a.gu_addr.notna()].groupby(['시설', 'year']):
        r = g.groupby('gu_addr')['분석가능'].mean()
        low += [[f, int(y), gu, round(v * 100, 1)] for gu, v in r.items() if v < 0.85]
    o['gu_below_85pct'] = low
    sg = gpd.read_file(mb.BND / '03_행정구역' / '경계_2025_2Q' / 'bnd_sigungu_00_2025_2Q' / 'bnd_sigungu_00_2025_2Q.shp')
    sg = sg[sg.SIGUNGU_CD.astype(str).str.startswith('11')].to_crs(5179)
    code = dict(zip(sg.SIGUNGU_NM, sg.SIGUNGU_CD.astype(str))); poly = dict(zip(sg.SIGUNGU_CD.astype(str), sg.geometry))
    ph = []
    for f, g in a[a.lon.notna()].groupby('시설'):
        k = g.groupby([g.lon.round(6), g.lat.round(6)]).gu_addr.nunique()
        ph += [[f, float(lo), float(la), int(n)] for (lo, la), n in k[k >= 3].items()]
    o['placeholder_coords'] = ph
    mm = a[(dong != '') & a.gu_addr.notna()].copy()
    mm = mm[mm.adm_dong_cd.str[:5] != mm.gu_addr.map(code)]
    pts = gpd.points_from_xy(mm.x_5179, mm.y_5179, crs=5179)
    mm['dist_to_addr_gu_m'] = [round(poly[code[g]].distance(p), 1) for g, p in zip(mm.gu_addr, pts)]
    mm[['시설', 'year', 'facility_id', 'name', 'address', 'coord_method', 'adm_dong_cd', 'dist_to_addr_gu_m']].to_csv(HERE / '좌표구_주소구_불일치.csv', index=False, encoding='utf-8-sig')
    o['gu_mismatch_rows'] = len(mm); o['gu_mismatch_over_200m'] = mm[mm.dist_to_addr_gu_m > 200][['시설', 'year', 'facility_id', 'name', 'dist_to_addr_gu_m']].astype(str).values.tolist()
    t = pd.read_parquet(V1 / '10_신뢰도_상' / '통합_신뢰도상_2020_2025.parquet', columns=['시설'])
    o['integrated_rows_vs_analysis_excl_retail'] = [len(t), int((a['시설'] != '일상소매').sum())]
    # 재현: 빌드 스크립트를 임시 폴더로 다시 실행
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, OUT_DIR=td, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
        r1 = subprocess.run([sys.executable, '-X', 'utf8', str(V1 / '10_신뢰도_상' / 'build_통합.py')], env=env, capture_output=True, text=True, encoding='utf-8')
        r2 = subprocess.run([sys.executable, '-X', 'utf8', str(V1 / '20_분석용' / 'build_분석용.py')], env=env, capture_output=True, text=True, encoding='utf-8')
        o['rebuild_returncodes'] = [r1.returncode, r2.returncode]
        if r1.returncode == 0: o['rebuild_integrated_sha_equal'] = sha(Path(td) / '통합_신뢰도상_2020_2025.parquet') == sha(V1 / '10_신뢰도_상' / '통합_신뢰도상_2020_2025.parquet')
        if r2.returncode == 0: o['rebuild_analysis_sha_equal'] = sha(Path(td) / '서울시설_2020_2025_분석용.parquet') == o['sha256']
    o['PASS'] = bool(o['all_33_both_years'] and o['dup_ok'] and o['xy_lonlat_max_m'] < 1 and o['inside_dong_inconsistent'] == 0
                     and o['unresolved_with_coord'] == 0 and not low and not ph and o['integrated_rows_vs_analysis_excl_retail'][0] == o['integrated_rows_vs_analysis_excl_retail'][1]
                     and o.get('rebuild_integrated_sha_equal') and o.get('rebuild_analysis_sha_equal'))
    (HERE / '검증결과.json').write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in o.items() if k not in ('gu_below_85pct',)}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
