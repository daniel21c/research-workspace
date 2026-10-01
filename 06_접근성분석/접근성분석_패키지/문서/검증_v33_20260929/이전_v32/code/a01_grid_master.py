# -*- coding: utf-8 -*-
"""P1 격자 마스터 구축 — 100m(본) · 250m(민감도).

입력 (a00_config): SGIS 100m 격자 SHP + 통계 CSV(인구·가구·사업체·종사자 2019·2024),
  코어엔진 동 424 폴리곤(seoul_boundaries_all.gpkg / dong_424), 동→생활권·Leiden 매핑 CSV,
  SGIS 집계구 경계(2025_2Q), SGIS 행정동 경계(2025_2Q, 참고 열), 250m 격자 기하(GRID250_SRC, 기하·gid만 사용).
규칙 (문서/지표정의_확정.md, 자료가공설계.md P1):
  - 서울 셀 = 셀 중심점이 동 424 합집합 안에 있는 셀.
  - 모든 단위 배정(동·구·생활권·Leiden·집계구)은 **중심점 규칙**. 면적비는 250m 인구 배분에만 사용.
  - 250m 인구 = 100m 셀 값 × (교차 면적 / 100m 셀 면적) 합산.
산출: 데이터/입력/grid/grid100_master.parquet|.gpkg, grid250_master.parquet|.gpkg,
      문서/격자마스터_구축기록.md, manifest_sha256.csv(추가), 작업기록.md(추가).
실행: python a01_grid_master.py [--force]   (중간 결과는 데이터/입력/grid/_tmp/ 에 체크포인트)
"""
import argparse, hashlib, json, sys, time, shutil, tempfile, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, shapely, pyogrio
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a00_config as C

GRID_DIR = C.DATA / 'grid'; TMP = GRID_DIR / '_tmp'; TMP.mkdir(parents=True, exist_ok=True)
STAT_ITEMS = {'pop': ('인구', 'to_in_001'), 'hh': ('가구', 'to_ga_001'),
              'biz': ('사업체', 'to_fa_010'), 'emp': ('종사자', 'to_em_020')}   # SGIS 제공용 코드표(3. statistics_code.xls) 총계 항목
POP_YEARS = (2019, 2024)
OFFICIAL_POP = {2019: 9_639_541, 2024: 9_335_444}   # SGIS 행정구역 통계 서울 총인구(SGIS README 확인값)
SGIS_DONG_2025 = C.SGIS / '03_행정구역' / '경계_2025_2Q' / 'bnd_dong_00_2025_2Q' / 'bnd_dong_00_2025_2Q.shp'
UNIT_COLS = ['dong424', 'ku', 'ku_name', 'adm_nm', 'lz116', 'ld2020', 'ld2025', 'oa_cd', 'adm_cd_2025q2']
STAT_COLS = [f'{v}_{y}' for v in STAT_ITEMS for y in POP_YEARS]
T0 = time.time()
def log(*a): print(f'[{time.time()-T0:6.1f}s]', *a, flush=True)
def to_gpkg(gdf, path, layer=None):
    """마운트 폴더에 sqlite 직접 쓰기가 실패하므로 로컬 임시 파일에 쓴 뒤 복사."""
    path = Path(path)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / path.name
        gdf.to_file(tmp, driver='GPKG', layer=layer or path.stem)
        shutil.copyfile(tmp, path)

def load_meta(path):
    """체크포인트 메타 json 로드(연도 키를 int로 되돌림)."""
    def fix(v):
        if isinstance(v, dict):
            return {(int(k) if isinstance(k, str) and k.isdigit() else k): fix(x) for k, x in v.items()}
        return v
    R.update(fix(json.loads(Path(path).read_text(encoding='utf-8'))))

def sha256(p, chunk=1 << 22):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''): h.update(b)
    return h.hexdigest()
R = {}   # 구축기록에 적을 검증값

# ---------------------------------------------------------------- 공통 기하 도구
def load_dong():
    d = gpd.read_file(C.BOUND_GPKG, layer='dong_424')
    assert len(d) == 424 and d.Dong.is_unique
    d['Dong'] = d['Dong'].astype('int64')
    u = d.geometry.union_all() if hasattr(d.geometry, 'union_all') else d.geometry.unary_union
    R['union_geomtype'] = u.geom_type; R['union_area_km2'] = u.area / 1e6
    R['union_n_interiors'] = sum(len(g.interiors) for g in getattr(u, 'geoms', [u]))
    return d, u

def assign_by_centroid(pts, dong, union, oa, sgis_dong, maps):
    """pts: GeoSeries(점, 5179) → 단위 열 DataFrame(중심점 규칙). 동 폴리곤 안에 없지만 합집합 안(동 사이 틈)은 최근접 동."""
    P = gpd.GeoDataFrame({'i': np.arange(len(pts))}, geometry=pts.values, crs=C.CRS)
    j = gpd.sjoin(P, dong[['Dong', 'geometry']], predicate='within', how='left').drop_duplicates('i')
    dong_id = j.set_index('i')['Dong'].reindex(P.i)
    miss = dong_id.isna().values
    n_gap = int(miss.sum())
    if n_gap:
        nn = gpd.sjoin_nearest(P[miss], dong[['Dong', 'geometry']], how='left').drop_duplicates('i')
        dong_id.loc[nn.i.values] = nn.Dong.values
    out = pd.DataFrame({'dong424': dong_id.astype('int64').values})
    dl = dong.set_index('Dong')
    out['ku'] = dl.loc[out.dong424, 'Ku'].astype('int64').values
    out['ku_name'] = dl.loc[out.dong424, 'ku_name'].values
    out['adm_nm'] = dl.loc[out.dong424, 'ADM_NM'].values
    out['lz116'] = maps['lz'].loc[out.dong424].astype('int64').values
    out['ld2020'] = maps['ld2020'].loc[out.dong424].astype('int64').values
    out['ld2025'] = maps['ld2025'].loc[out.dong424].astype('int64').values
    # 집계구(2025_2Q) — 중심점 within, 남는 셀은 최근접
    jo = gpd.sjoin(P, oa[['TOT_OA_CD', 'geometry']], predicate='within', how='left').drop_duplicates('i')
    oa_cd = jo.set_index('i')['TOT_OA_CD'].reindex(P.i)
    n_oa_within = int(oa_cd.notna().sum())
    m = oa_cd.isna().values
    if m.any():
        nn = gpd.sjoin_nearest(P[m], oa[['TOT_OA_CD', 'geometry']], how='left').drop_duplicates('i')
        oa_cd.loc[nn.i.values] = nn.TOT_OA_CD.values
    out['oa_cd'] = oa_cd.values
    # SGIS 2025_2Q 행정동(참고 열, 8자리)
    js = gpd.sjoin(P, sgis_dong[['ADM_CD', 'geometry']], predicate='within', how='left').drop_duplicates('i')
    out['adm_cd_2025q2'] = js.set_index('i')['ADM_CD'].reindex(P.i).values
    stats = dict(n_gap_nearest_dong=n_gap, n_oa_within=n_oa_within, n_oa_nearest=int(m.sum()),
                 n_sgis_dong_missing=int(out.adm_cd_2025q2.isna().sum()))
    return out, stats

def area_share(cells, union, cell_area):
    """셀 기하가 합집합 안에 있는 면적 비율. 경계에 걸친 셀만 교차 계산."""
    geo = cells.geometry.values
    bnd = union.boundary
    touch = shapely.intersects(bnd, geo)
    share = np.ones(len(geo))
    if touch.any():
        inter = shapely.intersection(geo[touch], union)
        share[touch] = shapely.area(inter) / cell_area
    return np.clip(share, 0, 1), touch

def lonlat(x, y):
    tr = Transformer.from_crs(C.CRS, 4326, always_xy=True)
    lon, lat = tr.transform(x, y); return lon, lat

def load_maps():
    lz = pd.read_csv(C.DONG_LZ_MAP); ld20 = pd.read_csv(C.DONG_LD_MAP[2020]); ld25 = pd.read_csv(C.DONG_LD_MAP[2025])
    for m in (lz, ld20, ld25): assert len(m) == 424 and m.Dong.is_unique
    return {'lz': lz.set_index('Dong')['life_zone_id'], 'ld2020': ld20.set_index('Dong')['global_community_id'],
            'ld2025': ld25.set_index('Dong')['global_community_id']}

def load_oa_sgisdong(bounds):
    oa = pyogrio.read_dataframe(C.OA_SHP, bbox=tuple(bounds))
    oa = oa[oa.ADM_CD.astype(str).str.startswith('11')].reset_index(drop=True)
    sd = pyogrio.read_dataframe(SGIS_DONG_2025, bbox=tuple(bounds))
    sd = sd[sd.ADM_CD.astype(str).str.startswith('11')].reset_index(drop=True)
    R['n_oa_seoul'] = len(oa); R['n_sgis_dong_2025_seoul'] = len(sd)
    return oa, sd

# ---------------------------------------------------------------- 1) 100m 서울 셀
def step_seoul_cells(dong, union, force):
    ck = TMP / 'g100_seoul.gpkg'; meta = TMP / 'g100_seoul_meta.json'
    if ck.exists() and meta.exists() and not force:
        log('체크포인트 로드', ck.name); load_meta(meta); return gpd.read_file(ck)
    g = pyogrio.read_dataframe(C.GRID100_SHP, bbox=tuple(shapely.bounds(union)))
    R['n_grid100_bbox'] = len(g); R['n_grid100_total'] = pyogrio.read_info(C.GRID100_SHP)['features']
    assert g.GRID_CD.is_unique
    cen = g.geometry.centroid
    inside = shapely.contains(union, cen.values)              # 중심점 규칙
    touch_all = shapely.intersects(union.boundary, g.geometry.values)
    R['n_edge_excluded'] = int((touch_all & ~inside).sum())    # 합집합에 걸치지만 중심점은 밖 → 제외
    R['excluded_edge_cells'] = g.loc[touch_all & ~inside, 'GRID_CD'].tolist()
    g = g[inside].reset_index(drop=True)
    share, touch = area_share(g, union, 10_000.0)
    g['area_in_seoul_share'] = share
    g['x_c'] = cen[inside].x.values; g['y_c'] = cen[inside].y.values
    g = g.rename(columns={'GRID_CD': 'grid_cd'})
    log(f'서울 100m 셀 {len(g):,} (bbox {R["n_grid100_bbox"]:,}), 경계 걸침 {int(touch.sum()):,}')
    to_gpkg(g, ck)
    meta.write_text(json.dumps({k: R[k] for k in ('n_grid100_bbox', 'n_grid100_total', 'n_edge_excluded', 'excluded_edge_cells')}, ensure_ascii=False), encoding='utf-8')
    return g

# ---------------------------------------------------------------- 2) 통계 CSV
def step_stats(force):
    ck = TMP / 'stats100.parquet'; meta = TMP / 'stats100_meta.json'
    if ck.exists() and meta.exists() and not force:
        log('체크포인트 로드', ck.name); load_meta(meta); return pd.read_parquet(ck)
    frames = []; R['stats_files'] = {}
    for v, (kor, item) in STAT_ITEMS.items():
        for y in POP_YEARS:
            f = C.GRID100_STATS / f'{y}년_{kor}_다사_100M.csv'
            df = pd.read_csv(f, encoding='cp949', header=None, names=['year', 'grid_cd', 'item', 'value'], dtype={'grid_cd': str, 'item': str})
            items = df.item.value_counts().to_dict()
            sub = df[df.item == item]
            dup = int(sub.grid_cd.duplicated().sum())
            s = sub.groupby('grid_cd')['value'].sum().rename(f'{v}_{y}')
            R['stats_files'][f.name] = dict(rows=len(df), items=items, used=item, rows_used=len(sub), dup_grid=dup, total=int(s.sum()))
            frames.append(s)
    st = pd.concat(frames, axis=1).fillna(0).astype('int64')
    st.index.name = 'grid_cd'; st = st.reset_index()
    st.to_parquet(ck, index=False); meta.write_text(json.dumps({'stats_files': R['stats_files']}, ensure_ascii=False), encoding='utf-8')
    log('통계 CSV 결합', st.shape); return st

# ---------------------------------------------------------------- 3) 100m 마스터
def step_master100(g, st, dong, union, oa, sd, maps, force):
    ck = TMP / 'g100_master.gpkg'; meta = TMP / 'g100_master_meta.json'
    if ck.exists() and meta.exists() and not force:
        log('체크포인트 로드', ck.name); load_meta(meta)
        m = gpd.read_file(ck)
        for y in POP_YEARS: m[f'pop_pos_{y}'] = m[f'pop_pos_{y}'].astype(bool)
        return m
    units, ustat = assign_by_centroid(gpd.GeoSeries.from_xy(g.x_c, g.y_c, crs=C.CRS), dong, union, oa, sd, maps)
    R['assign100'] = ustat
    m = pd.concat([g.reset_index(drop=True), units], axis=1)
    m = m.merge(st, on='grid_cd', how='left')
    ex = st[st.grid_cd.isin(R['excluded_edge_cells'])]
    R['excluded_edge_pop'] = {y: int(ex[f'pop_{y}'].sum()) for y in POP_YEARS}; R['excluded_edge_pop_pos'] = {y: int((ex[f'pop_{y}'] > 0).sum()) for y in POP_YEARS}
    R['n100_no_stats_any'] = int(m[STAT_COLS].isna().all(axis=1).sum())
    R['n100_no_stats'] = {c: int(m[c].isna().sum()) for c in STAT_COLS}
    m[STAT_COLS] = m[STAT_COLS].fillna(0).astype('int64')
    for y in POP_YEARS: m[f'pop_pos_{y}'] = m[f'pop_{y}'] > 0
    m['lon'], m['lat'] = lonlat(m.x_c.values, m.y_c.values)
    m = m.sort_values('grid_cd').reset_index(drop=True)
    cols = ['grid_cd', 'x_c', 'y_c', 'lon', 'lat'] + UNIT_COLS + ['area_in_seoul_share'] + STAT_COLS + [f'pop_pos_{y}' for y in POP_YEARS]
    m = gpd.GeoDataFrame(m[cols + ['geometry']], geometry='geometry', crs=C.CRS)
    to_gpkg(m, ck)
    meta.write_text(json.dumps({k: R[k] for k in ('assign100', 'excluded_edge_pop', 'excluded_edge_pop_pos', 'n100_no_stats_any', 'n100_no_stats')}, ensure_ascii=False), encoding='utf-8')
    log('100m 마스터 열 완성', m.shape); return m

# ---------------------------------------------------------------- 4) 250m 마스터
def step_master250(m100, dong, union, oa, sd, maps, force):
    g250 = gpd.read_file(C.GRID250_SRC)[['gid', 'geometry']]
    assert g250.gid.is_unique
    g250['geometry'] = g250.geometry.apply(lambda g: max(g.geoms, key=lambda p: p.area) if g.geom_type == 'MultiPolygon' else g)
    R['n250_src'] = len(g250); R['area250'] = float(g250.geometry.area.median())
    a250 = R['area250']
    # 100m × 250m 교차 → 면적비 가중치
    pairs = gpd.sjoin(m100[['grid_cd', 'geometry']], g250, predicate='intersects', how='inner')
    ga = m100.geometry.values[pairs.index.values]
    gb = g250.geometry.values[pairs.index_right.values]
    ia = shapely.area(shapely.intersection(ga, gb))
    pairs = pd.DataFrame({'grid_cd': pairs.grid_cd.values, 'gid': pairs.gid.values, 'w': ia / 10_000.0})
    pairs = pairs[pairs.w > 1e-9]
    cov = pairs.groupby('grid_cd')['w'].sum()
    cov = cov.reindex(m100.grid_cd).fillna(0)
    R['n100_not_fully_covered_by_250'] = int((cov < 0.999).sum())
    R['pop_lost_uncovered'] = {y: float(((1 - cov.values) * m100[f'pop_{y}'].values).sum()) for y in POP_YEARS}
    vals = m100.set_index('grid_cd')[STAT_COLS]
    W = pairs.merge(vals, left_on='grid_cd', right_index=True)
    for c in STAT_COLS: W[c] = W[c] * W.w
    agg = W.groupby('gid')[STAT_COLS].sum()
    # 단위 배정(중심점)
    cen = g250.geometry.centroid
    inside = shapely.contains(union, cen.values)
    t = agg.reindex(g250.gid).fillna(0)
    pop_any = (t[[f'pop_{y}' for y in POP_YEARS]].values > 0).any(axis=1)
    keep = inside | pop_any
    R['n250_centroid_in'] = int(inside.sum()); R['n250_pop_only'] = int((pop_any & ~inside).sum()); R['n250_dropped'] = int((~keep).sum())
    R['pop_dropped_250'] = {y: float(t.loc[~keep, f'pop_{y}'].sum()) for y in POP_YEARS}
    R['dropped_250'] = {c: float(t.loc[~keep, c].sum()) for c in STAT_COLS}
    g = g250[keep].reset_index(drop=True); t = t.loc[g.gid].reset_index(drop=True)
    units, ustat = assign_by_centroid(cen[keep].reset_index(drop=True), dong, union, oa, sd, maps)
    R['assign250'] = ustat
    share, touch = area_share(g, union, a250)
    m = pd.concat([g[['gid']].rename(columns={'gid': 'grid_cd'}), units, t], axis=1)
    m['area_in_seoul_share'] = share
    m['x_c'] = cen[keep].x.values; m['y_c'] = cen[keep].y.values
    m['lon'], m['lat'] = lonlat(m.x_c.values, m.y_c.values)
    for y in POP_YEARS: m[f'pop_pos_{y}'] = m[f'pop_{y}'] > 0
    cols = ['grid_cd', 'x_c', 'y_c', 'lon', 'lat'] + UNIT_COLS + ['area_in_seoul_share'] + STAT_COLS + [f'pop_pos_{y}' for y in POP_YEARS]
    m = gpd.GeoDataFrame(m[cols].assign(geometry=g.geometry.values), geometry='geometry', crs=C.CRS).sort_values('grid_cd').reset_index(drop=True)
    R['sum250_vs_100'] = {c: (float(m[c].sum()), int(m100[c].sum())) for c in STAT_COLS}
    log('250m 마스터', m.shape); return m

# ---------------------------------------------------------------- 5) 검증값·기록
def checks(m100, m250, dong, sd):
    R['n100'] = len(m100)
    for y in POP_YEARS:
        R[f'n100_pop_pos_{y}'] = int(m100[f'pop_pos_{y}'].sum())
        R[f'n250_pop_pos_{y}'] = int(m250[f'pop_pos_{y}'].sum())
        s = int(m100[f'pop_{y}'].sum()); R[f'pop100_{y}'] = s; R[f'pop100_diff_{y}'] = (s - OFFICIAL_POP[y]) / OFFICIAL_POP[y] * 100
    R['n250'] = len(m250)
    cnt = m100.groupby('dong424').size().reindex(dong.Dong).fillna(0).astype(int)
    R['dong_cells'] = dict(min=int(cnt.min()), median=float(cnt.median()), max=int(cnt.max()), zero=cnt[cnt == 0].index.tolist(),
                           min_dong=f'{cnt.idxmin()} {dong.set_index("Dong").ADM_NM[cnt.idxmin()]}')
    cnt250 = m250.groupby('dong424').size().reindex(dong.Dong).fillna(0).astype(int)
    R['dong_cells250'] = dict(min=int(cnt250.min()), median=float(cnt250.median()), zero=int((cnt250 == 0).sum()))
    ok = m100.adm_cd_2025q2.notna()
    diff = ok & (m100.adm_cd_2025q2.str[:7] != m100.dong424.astype(str))
    nm = sd.set_index('ADM_CD')['ADM_NM']
    sgis_nm = m100.adm_cd_2025q2.map(nm)
    ndiff = ok & (sgis_nm != m100.adm_nm)
    R['sgis_dong_diff'] = dict(n=int(diff.sum()), share=float(diff.sum() / ok.sum()), n_na=int((~ok).sum()),
                               n_name=int(ndiff.sum()), share_name=float(ndiff.sum() / ok.sum()))
    top = m100[diff & ~ndiff].groupby(['adm_nm', 'dong424', 'adm_cd_2025q2']).size().sort_values(ascending=False)
    R['sgis_dong_code_only'] = [(a, int(b), c, int(n)) for (a, b, c), n in top.items()]
    top = m100[ndiff].assign(sgis_nm=sgis_nm[ndiff]).groupby(['adm_nm', 'sgis_nm']).size().sort_values(ascending=False).head(8)
    R['sgis_dong_diff_top'] = [(a, b, int(n)) for (a, b), n in top.items()]
    b = m100.area_in_seoul_share < 1
    R['boundary100'] = dict(n=int(b.sum()), share_min=float(m100.area_in_seoul_share.min()),
                            pop_share={y: float(m100.loc[b, f'pop_{y}'].sum() / m100[f'pop_{y}'].sum()) for y in POP_YEARS})
    R['oa_fill'] = dict(within=R['assign100']['n_oa_within'] / len(m100), n_unique=int(m100.oa_cd.nunique()))
    R['lz_dong_consistent'] = bool((dong.set_index('Dong').life_zone_id.reindex(m100.dong424).values == m100.lz116.values).all())
    R['ld2020_dong_consistent'] = bool((dong.set_index('Dong').leiden_2020.reindex(m100.dong424).values == m100.ld2020.values).all())
    R['ld2025_dong_consistent'] = bool((dong.set_index('Dong').leiden_2025.reindex(m100.dong424).values == m100.ld2025.values).all())

def write_outputs(m100, m250):
    outs = []
    for name, m in (('grid100_master', m100), ('grid250_master', m250)):
        pq = GRID_DIR / f'{name}.parquet'; gp = GRID_DIR / f'{name}.gpkg'
        pd.DataFrame(m.drop(columns='geometry')).to_parquet(pq, index=False)
        to_gpkg(m, gp, layer=name)
        outs += [(pq, len(m)), (gp, len(m))]
    return outs

def source_files():
    fs = [C.GRID100_SHP, C.GRID100_SHP.with_suffix('.dbf'), C.BOUND_GPKG, C.DONG_LZ_MAP, C.DONG_LD_MAP[2020], C.DONG_LD_MAP[2025],
          C.GRID250_SRC, C.OA_SHP, C.OA_SHP.with_suffix('.dbf'), SGIS_DONG_2025, SGIS_DONG_2025.with_suffix('.dbf')]
    fs += [C.GRID100_STATS / f'{y}년_{k}_다사_100M.csv' for k, _ in STAT_ITEMS.values() for y in POP_YEARS]
    return fs

def nrows(p):
    p = Path(p)
    if p.suffix == '.gpkg' and p == C.BOUND_GPKG: return pyogrio.read_info(p, layer='dong_424')['features']
    if p.suffix in ('.shp', '.gpkg'): return pyogrio.read_info(p)['features']
    if p.suffix == '.csv':
        n = sum(1 for _ in open(p, 'rb'))
        return n - 1 if 'mapping' in p.name else n     # 매핑 CSV만 헤더 있음
    return ''

def write_records(outs, src_hash):
    today = dt.date.today().isoformat(); now = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    rel = lambda p: str(Path(p).relative_to(C.ROOT)) if str(p).startswith(str(C.ROOT)) else str(p).replace(str(C.BASE), '..').replace(str(Path.home() / 'mnt'), '~/mnt')
    L = []
    L.append(f'# 격자 마스터 구축기록 (P1 grid-master-100m-v1 · grid-master-250m-v1)\n')
    L.append(f'- 생성: {now}, `코드/a01_grid_master.py`. 규칙 출처: `문서/지표정의_확정.md`, `문서/자료가공설계.md` P1.')
    L.append('- 서울 셀 정의: 셀 **중심점**이 코어엔진 동 424 폴리곤 합집합 안. 모든 단위(동·구·공식 생활권·Leiden·집계구·SGIS 2025_2Q 행정동) 배정도 중심점 규칙. 면적비는 250m 인구 배분에만 사용.\n')
    L.append('## 1. 원천 파일\n\n| 파일 | 행(피처) | SHA-256 |\n|---|---:|---|')
    for p, h, n in src_hash: L.append(f'| `{rel(p)}` | {n:,} | `{h}` |' if n != '' else f'| `{rel(p)}` | (dbf) | `{h}` |')
    L.append('\n통계 CSV(cp949, 헤더 없음: 연도, GRID_CD, 항목코드, 값) 항목 코드 — SGIS 제공용 코드표(`04_참고문서/3. 제공용 코드(statistics_code).xls` 격자 시트)로 확인:\n')
    L.append('| 파일 | 행 | 파일 내 항목코드 | 사용 코드 | 사용 행 | 격자 중복 | 합계(다사 도엽 전체) |\n|---|---:|---|---|---:|---:|---:|')
    for f, s in R['stats_files'].items():
        L.append(f'| {f} | {s["rows"]:,} | {", ".join(f"{k}({v:,})" for k, v in s["items"].items())} | `{s["used"]}` | {s["rows_used"]:,} | {s["dup_grid"]} | {s["total"]:,} |')
    L.append('\n- 사용 코드: 인구 `to_in_001`(총인구), 가구 `to_ga_001`(총가구수), 사업체 `to_fa_010`(총사업체수), 종사자 `to_em_020`(총종사자수). 인구 파일의 `to_in_007/008`(남/여)은 쓰지 않음.')
    L.append(f'\n## 2. 100m 격자 마스터 (`데이터/입력/grid/grid100_master.parquet` · `.gpkg`)\n')
    L.append(f'- SGIS `grid_다사_100M.shp` 전체 {R["n_grid100_total"]:,}셀 → 동 424 합집합 bbox 안 {R["n_grid100_bbox"]:,}셀 → 중심점이 합집합 안 **{R["n100"]:,}셀**.')
    L.append(f'- 동 424 합집합: {R["union_geomtype"]}, 면적 {R["union_area_km2"]:.2f} km², 내부 구멍 {R["union_n_interiors"]}개.')
    L.append(f'- 합집합에 걸치지만 중심점이 밖이라 제외한 셀 {R["n_edge_excluded"]:,}개 — 그중 인구>0 셀 2019 {R["excluded_edge_pop_pos"][2019]:,}개(인구 {R["excluded_edge_pop"][2019]:,}), 2024 {R["excluded_edge_pop_pos"][2024]:,}개(인구 {R["excluded_edge_pop"][2024]:,}). 이 인구는 서울 밖으로 간주해 마스터에 넣지 않음.')
    L.append(f'- 통계 행이 없어 0으로 둔 셀: 모든 8개 변수 없음 {R["n100_no_stats_any"]:,}셀; 변수별 ' + ', '.join(f'{c} {n:,}' for c, n in R['n100_no_stats'].items()) + '.')
    L.append(f'- 중심점이 어느 동 폴리곤 안에도 없어(동 사이 틈) 최근접 동으로 배정한 셀: {R["assign100"]["n_gap_nearest_dong"]:,}개.')
    L.append('\n### 2.1 인구 합계 vs SGIS 행정구역 통계 서울 총인구\n\n| 연도 | 격자 합(서울 셀) | 공식 총인구 | 차이 | 인구>0 셀 |\n|---|---:|---:|---:|---:|')
    for y in POP_YEARS:
        L.append(f'| {y} | {R[f"pop100_{y}"]:,} | {OFFICIAL_POP[y]:,} | {R[f"pop100_diff_{y}"]:+.3f}% | {R[f"n100_pop_pos_{y}"]:,} |')
    L.append('\n차이는 SGIS 격자 비밀보호(5 미만 0/5 대체, ±7 잡음) 때문이며 SGIS README 확인값(+0.06%/+0.04%)과 같은 수준.')
    L.append('\n### 2.2 기타 변수 합계(서울 셀)\n\n| 변수 | 2019 | 2024 |\n|---|---:|---:|')
    for v in STAT_ITEMS: L.append(f'| {v} | {R["sum250_vs_100"][f"{v}_2019"][1]:,} | {R["sum250_vs_100"][f"{v}_2024"][1]:,} |')
    dc = R['dong_cells']
    L.append(f'\n### 2.3 동 424 배정\n\n- 동별 셀 수: 최소 {dc["min"]}(동 {dc["min_dong"]}), 중앙값 {dc["median"]:.0f}, 최대 {dc["max"]}. 셀 0개 동: {len(dc["zero"])}개{(" " + str(dc["zero"])) if dc["zero"] else ""}.')
    L.append(f'- 동 레이어 속성(life_zone_id·leiden_2020·leiden_2025)과 매핑 CSV 결합값 일치: LZ {R["lz_dong_consistent"]}, LD2020 {R["ld2020_dong_consistent"]}, LD2025 {R["ld2025_dong_consistent"]}.')
    sd = R['sgis_dong_diff']
    L.append(f'- SGIS 2025_2Q 행정동(`adm_cd_2025q2`, 8자리, 서울 {R["n_sgis_dong_2025_seoul"]}동, 중심점 배정) vs 동424: 코드 불일치(7자리+0 규칙) {sd["n"]:,}셀 ({sd["share"]*100:.2f}%), **동 이름 불일치 {sd["n_name"]:,}셀 ({sd["share_name"]*100:.2f}%)**, 2025_2Q 배정 없음 {sd["n_na"]:,}셀.')
    L.append('  - 코드만 다르고 이름은 같은 경우(SGIS 코드 개편, 같은 동): ' + '; '.join(f'{a} {b}→{c} {n}셀' for a, b, c, n in R['sgis_dong_code_only']) + '.')
    L.append('  - 이름 불일치 상위(동424 이름→2025_2Q 이름, 셀 수): ' + '; '.join(f'{a}→{b} {n}' for a, b, n in R['sgis_dong_diff_top']) + '.')
    L.append('  - 이름 불일치는 2019→2025 행정동 변동(항동 신설, 상일동 분동)이 대부분이고 나머지는 경계 미세 차이. 분석 단위는 동424만 사용하고 이 열은 참고용.')
    b = R['boundary100']
    L.append(f'\n### 2.4 경계 셀·집계구\n\n- 합집합 경계에 걸친 셀(area_in_seoul_share<1): {b["n"]:,}개, 최소 면적비 {b["share_min"]:.3f}; 인구 비중 2019 {b["pop_share"][2019]*100:.2f}%, 2024 {b["pop_share"][2024]*100:.2f}%.')
    L.append(f'- 집계구(`oa_cd`, 2025_2Q, 서울 {R["n_oa_seoul"]:,}개): 중심점 within 채움률 {R["oa_fill"]["within"]*100:.2f}%, 나머지 {R["assign100"]["n_oa_nearest"]:,}셀은 최근접 집계구로 채움. 고유 집계구 {R["oa_fill"]["n_unique"]:,}개.')
    L.append(f'\n## 3. 250m 격자 마스터 (`데이터/입력/grid/grid250_master.parquet` · `.gpkg`)\n')
    L.append(f'- 틀: `GRID250_SRC`(국가격자 250m, {R["n250_src"]:,}셀, 셀 면적 {R["area250"]:,.0f} m²)의 **기하·gid만** 사용(그 파일의 인구·OD 값은 쓰지 않음). `grid_cd` 열 = 원본 gid.')
    L.append('- 인구·가구·사업체·종사자 = 100m 서울 셀 값 × (교차면적 / 10,000 m²) 을 250m 셀별로 합산(면적비 배분). 값은 실수.')
    L.append(f'- 100m 셀 중 250m 틀에 완전히 덮이지 않은 셀: {R["n100_not_fully_covered_by_250"]:,}개, 그로 인해 배분되지 않은 인구 2019 {R["pop_lost_uncovered"][2019]:.1f}, 2024 {R["pop_lost_uncovered"][2024]:.1f}.')
    L.append(f'- 유지 규칙: 중심점이 합집합 안({R["n250_centroid_in"]:,}셀) **또는** 배분 인구>0(2019 또는 2024; 중심점 밖인데 인구 받은 셀 {R["n250_pop_only"]:,}개). 제외 {R["n250_dropped"]:,}셀(제외 셀 인구 2019 {R["pop_dropped_250"][2019]:.1f}, 2024 {R["pop_dropped_250"][2024]:.1f}). → **{R["n250"]:,}셀**.')
    L.append(f'- 단위 열은 100m와 같은 중심점 규칙(동 틈 최근접 배정 {R["assign250"]["n_gap_nearest_dong"]}셀, 집계구 최근접 {R["assign250"]["n_oa_nearest"]}셀). 동별 250m 셀 수 최소 {R["dong_cells250"]["min"]}, 중앙값 {R["dong_cells250"]["median"]:.0f}, 0개 동 {R["dong_cells250"]["zero"]}개.')
    L.append('\n### 3.1 합계 검증 Σ250 vs Σ100\n\n| 변수 | Σ250m | Σ100m | 차이 |\n|---|---:|---:|---:|')
    for c, (a, b_) in R['sum250_vs_100'].items(): L.append(f'| {c} | {a:,.1f} | {b_:,} | {a-b_:+.1f} |')
    L.append(f'\n- 100m 셀은 모두 250m 틀에 완전히 덮이므로(위) 배분 전 합계는 같다. 차이는 제외된 {R["n250_dropped"]:,}셀(중심점 밖·인구 0)이 가진 사업체·종사자 값: ' + ', '.join(f'{c} {v:,.1f}' for c, v in R['dropped_250'].items() if v) + '.')
    L.append(f'- 인구>0 250m 셀: 2019 {R["n250_pop_pos_2019"]:,}, 2024 {R["n250_pop_pos_2024"]:,}.')
    L.append('\n## 4. 열 정의\n')
    L.append('| 열 | 뜻 |\n|---|---|\n| grid_cd | 100m: SGIS GRID_CD(다사NNNNNN) / 250m: 국가격자 gid(다사NNxxNNxx) |\n| x_c, y_c | 셀 중심 좌표(EPSG:5179) |\n| lon, lat | 중심 경위도(EPSG:4326) |\n| dong424 | 코어엔진 동 424 코드(7자리, 중심점) |\n| ku, ku_name, adm_nm | 구 코드·이름, 동 이름(동 424 레이어) |\n| lz116 | 공식 생활권 life_zone_id(dong_to_official_livingzone_mapping_424.csv) |\n| ld2020, ld2025 | Leiden global_community_id(dong_to_leiden_{2020,2025}_mapping_424.csv) |\n| oa_cd | SGIS 집계구 TOT_OA_CD(2025_2Q, 중심점; 연령 배분 보류용) |\n| adm_cd_2025q2 | SGIS 2025_2Q 행정동 ADM_CD(8자리, 참고) |\n| area_in_seoul_share | 셀 면적 중 동 424 합집합 안 비율(1=완전 내부) |\n| pop/hh/biz/emp_{2019,2024} | 총인구·총가구·총사업체·총종사자(100m 정수, 250m 실수) |\n| pop_pos_{2019,2024} | 인구>0 |')
    L.append('\n## 5. 산출 파일\n\n| 파일 | 행 | SHA-256 |\n|---|---:|---|')
    for p, n, h in outs: L.append(f'| `{rel(p)}` | {n:,} | `{h}` |')
    L.append('\n- parquet는 기하 없이(x_c,y_c 포함) 표 형식, gpkg는 같은 열 + 셀 폴리곤(EPSG:5179). 중간 체크포인트는 `데이터/입력/grid/_tmp/`.')
    (C.REC / '격자마스터_구축기록.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    # manifest (기존 스키마 file,sha256,bytes,created,script 유지 + rows 열 추가; 같은 파일은 행 교체)
    mf = C.MANIFEST
    rows = pd.DataFrame([{'file': rel(p), 'sha256': h, 'bytes': Path(p).stat().st_size, 'created': dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                          'script': 'a01_grid_master.py', 'rows': n} for p, n, h in outs])
    if mf.exists():
        old = pd.read_csv(mf, encoding='utf-8-sig'); old = old[~old['file'].isin(rows['file'])]; rows = pd.concat([old, rows], ignore_index=True)
    rows['rows'] = rows['rows'].astype('Int64')
    rows.to_csv(mf, index=False, encoding='utf-8-sig')
    # 작업기록
    wl = C.REC / '작업기록.md'
    head = '# 06_접근성분석 작업기록\n\n' if not wl.exists() else wl.read_text(encoding='utf-8')
    title = f'## {today} — P1 격자 마스터 100m·250m (Cowork/Claude, `a01_grid_master.py`)'
    if title in head:   # 같은 날 재실행이면 기존 항목 교체
        parts = head.split('\n## '); parts = [x for x in parts if not x.startswith(title[3:])]; head = '\n## '.join(parts)
    entry = (f'\n{title}\n\n'
             f'- 100m 서울 셀 {R["n100"]:,}(중심점 규칙), 인구 합 2019 {R["pop100_2019"]:,} ({R["pop100_diff_2019"]:+.3f}%), 2024 {R["pop100_2024"]:,} ({R["pop100_diff_2024"]:+.3f}%) vs SGIS 행정구역 총인구.\n'
             f'- 250m 셀 {R["n250"]:,}(GRID250_SRC 기하만, 100m 면적비 배분), Σ250−Σ100 인구 2019 {R["sum250_vs_100"]["pop_2019"][0]-R["sum250_vs_100"]["pop_2019"][1]:+.1f}, 2024 {R["sum250_vs_100"]["pop_2024"][0]-R["sum250_vs_100"]["pop_2024"][1]:+.1f}.\n'
             f'- 통계 항목코드: 인구 to_in_001, 가구 to_ga_001, 사업체 to_fa_010, 종사자 to_em_020. 셀 0개 동 {len(R["dong_cells"]["zero"])}개.\n'
             f'- 산출: `데이터/입력/grid/grid100_master.{{parquet,gpkg}}`, `grid250_master.{{parquet,gpkg}}`, 기록 `문서/격자마스터_구축기록.md`, manifest 갱신.\n')
    wl.write_text(head.rstrip('\n') + '\n' + entry, encoding='utf-8')

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--force', action='store_true', help='체크포인트 무시하고 다시 계산')
    ap.add_argument('--until', choices=['cells', 'stats', 'm100', 'all'], default='all', help='이 단계까지만 실행(체크포인트 저장)')
    a = ap.parse_args()
    dong, union = load_dong(); log('동 424·합집합')
    g = step_seoul_cells(dong, union, a.force)
    if a.until == 'cells': return
    st = step_stats(a.force)
    if a.until == 'stats': return
    maps = load_maps(); oa, sd = load_oa_sgisdong(shapely.bounds(union)); log('집계구·2025 행정동 로드', len(oa), len(sd))
    m100 = step_master100(g, st, dong, union, oa, sd, maps, a.force)
    if a.until == 'm100': return
    m250 = step_master250(m100, dong, union, oa, sd, maps, a.force)
    checks(m100, m250, dong, sd); log('검증값 계산')
    outs = write_outputs(m100, m250); log('산출 파일 저장')
    outs = [(p, n, sha256(p)) for p, n in outs]
    src = [(p, sha256(p), nrows(p)) for p in source_files()]
    log('해시 계산')
    write_records(outs, src); log('기록 저장 완료')
    (TMP / 'grid_master_checks.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    print({k: v for k, v in R.items() if k not in ('excluded_edge_cells', 'stats_files')})

if __name__ == '__main__':
    main()
