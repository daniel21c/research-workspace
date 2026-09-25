# -*- coding: utf-8 -*-
"""P6. 경계 기하 지표: 코어엔진 정본 사본(해시 대조), 단위별 면적·둘레·Polsby–Popper 컴팩트성, 동424 Queen 인접행렬, 동→단위 표(연구3용 Δ면적·Δ컴팩트).
입력: a00_config.BOUND_GPKG(dong_424, official_livingzone_116_dongbased, leiden_2020_116, leiden_2025_116), DONG_LZ_MAP, DONG_LD_MAP, CORE/data/manifest.json
출력: 데이터/입력/boundary/{seoul_boundaries_all.gpkg, dong_to_*_mapping_424.csv(사본), zone_metrics.csv, dong424_queen_adjacency.csv, dong424_queen_W.npz, dong424_units.csv}
      문서/경계기하지표_구축기록.md, manifest_sha256.csv 추가
정의: compact_pp = 4πA/P² (Polsby & Popper 1991; 1 km 정사각형 → π/4 = 0.785). Queen 인접 = 경계선 또는 점을 공유(shapely touches/intersects, 면적 겹침 없음).
"""
import sys, json, shutil, hashlib, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
from scipy import sparse
sys.path.insert(0, str(Path(__file__).resolve().parent))
import a00_config as C

BDIR = C.DATA / 'boundary'
REC_MD = C.REC / '경계기하지표_구축기록.md'
MANIFEST = C.MANIFEST
LAYERS = {  # layer -> (id 열, 이름 열, n_dongs 열 또는 None)
    'official_livingzone_116_dongbased': ('life_zone_id', 'life_zone_name', 'n_dongs'),
    'leiden_2020_116': ('global_community_id', 'community_name', 'n_dongs'),
    'leiden_2025_116': ('global_community_id', 'community_name', 'n_dongs'),
    'dong_424': ('Dong', 'ADM_NM', None),
}

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def append_manifest(paths, script):
    now = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    rows = [dict(file=str(Path(p).relative_to(C.ROOT)).replace('\\', '/'), sha256=sha256(p), bytes=Path(p).stat().st_size, created=now, script=script) for p in paths]
    new = pd.DataFrame(rows)
    if MANIFEST.exists():
        old = pd.read_csv(MANIFEST); old = old[~old['file'].isin(new['file'])]
        new = pd.concat([old, new], ignore_index=True)
    new.to_csv(MANIFEST, index=False, encoding='utf-8-sig')
    return rows

def polsby_popper(geom):
    """Polsby–Popper 컴팩트성 4πA/P². GeoSeries 또는 단일 geometry."""
    A = geom.area; P = geom.length
    return 4 * np.pi * A / (P ** 2)

def zone_metrics(gdf, id_col, name_col, ndong_col=None, dong_counts=None):
    g = gdf.copy()
    out = pd.DataFrame({'id': g[id_col].values, 'name': g[name_col].values})
    out['n_dongs'] = g[ndong_col].values if ndong_col else (dong_counts.reindex(out['id']).values if dong_counts is not None else 1)
    out['area_km2'] = g.geometry.area.values / 1e6
    out['perimeter_km'] = g.geometry.length.values / 1e3
    out['compact_pp'] = polsby_popper(g.geometry).values
    out['n_parts'] = g.geometry.apply(lambda x: len(x.geoms) if hasattr(x, 'geoms') else 1).values
    return out

def queen_adjacency(dong):
    """Queen 인접: 경계 공유(선 또는 점). intersects이면서 서로 다른 폴리곤. 반환: (pairs DataFrame, W csr, islands list)."""
    from shapely.strtree import STRtree
    geoms = dong.geometry.values; ids = dong['Dong'].values
    tree = STRtree(geoms)
    i, j = tree.query(geoms, predicate='intersects')
    m = i != j; i, j = i[m], j[m]
    # 공유 형태: 선(길이>0) 또는 점
    shared = [geoms[a].intersection(geoms[b]) for a, b in zip(i, j)]
    kind = np.array(['edge' if s.length > 0 else 'vertex' for s in shared])
    length_m = np.array([s.length for s in shared])
    pairs = pd.DataFrame({'i': ids[i], 'j': ids[j], 'kind': kind, 'shared_len_m': length_m.round(2)})
    n = len(dong); W = sparse.csr_matrix((np.ones(len(i)), (i, j)), shape=(n, n))
    W.data[:] = 1
    deg = np.asarray(W.sum(1)).ravel()
    islands = list(ids[deg == 0])
    return pairs, W, islands, deg

def main():
    t0 = dt.datetime.now(); log = []
    P = lambda s: (print(s), log.append(s))
    P(f'# 경계 기하 지표 구축기록 (P6)\n\n- 실행: {t0:%Y-%m-%d %H:%M} · 스크립트 `코드/a03_boundary_metrics.py`')
    BDIR.mkdir(parents=True, exist_ok=True)

    # ---------- 1. 정본 사본 + 해시 대조 ----------
    man = json.load(open(C.CORE / 'data' / 'manifest.json', encoding='utf-8'))['files']
    srcs = [C.BOUND_GPKG, C.DONG_LZ_MAP, C.DONG_LD_MAP[2020], C.DONG_LD_MAP[2025]]
    P('\n## 1. 코어엔진 정본 사본 (복사, 원본 유지)\n| 파일 | 원본 sha256 | manifest.json 일치 | 사본 sha256 일치 |\n|---|---|---|---|')
    copied = []
    for s in srcs:
        d = BDIR / s.name
        shutil.copy2(s, d)
        hs, hd = sha256(s), sha256(d)
        ok_m = man.get(s.name, {}).get('sha256') == hs
        P(f'| `{s.name}` | {hs} | {"일치" if ok_m else "**불일치**"} | {"일치" if hs == hd else "**불일치**"} |')
        assert ok_m and hs == hd, s
        copied.append(d)

    # ---------- 2. 단위별 기하 지표 ----------
    dong = gpd.read_file(C.BOUND_GPKG, layer='dong_424'); assert dong.crs.to_epsg() == C.CRS and len(dong) == 424
    lz = pd.read_csv(C.DONG_LZ_MAP); l20 = pd.read_csv(C.DONG_LD_MAP[2020]); l25 = pd.read_csv(C.DONG_LD_MAP[2025])
    parts = []
    for layer, (idc, nmc, ndc) in LAYERS.items():
        g = gpd.read_file(C.BOUND_GPKG, layer=layer); assert g.crs.to_epsg() == C.CRS
        z = zone_metrics(g, idc, nmc, ndc); z.insert(0, 'layer', layer); parts.append(z)
    ku = dong.dissolve(by='Ku', aggfunc={'ku_name': 'first', 'Dong': 'count'}).reset_index()
    z = zone_metrics(ku, 'Ku', 'ku_name', 'Dong'); z.insert(0, 'layer', 'ku'); parts.append(z)
    zm = pd.concat(parts, ignore_index=True)
    # 검증: 매핑 CSV로 동을 합친 폴리곤과 레이어 폴리곤의 면적 대조 (LZ dongbased, LD 2020/2025)
    P('\n## 2. 단위별 기하 지표 `zone_metrics.csv`\n- 열: layer, id, name, n_dongs, area_km2, perimeter_km, compact_pp(=4πA/P²), n_parts(다중폴리곤 부분 수)')
    chk = []
    for layer, mp, col in [('official_livingzone_116_dongbased', lz, 'life_zone_id'), ('leiden_2020_116', l20, 'global_community_id'), ('leiden_2025_116', l25, 'global_community_id')]:
        dm = dong.merge(mp[['Dong', col]], on='Dong', suffixes=('', '_m'))
        dis = dm.dissolve(by=col if col not in dong.columns else col + '_m')
        a_dis = dis.geometry.area / 1e6
        a_lay = zm[zm.layer == layer].set_index('id')['area_km2']
        diff = (a_dis - a_lay.reindex(a_dis.index)).abs().max()
        n_multi = int((zm[zm.layer == layer].n_parts > 1).sum())
        chk.append(dict(layer=layer, n=len(a_lay), 면적합_km2=round(a_lay.sum(), 3), 동합집합_면적차_최대_km2=round(diff, 6), 다중폴리곤_수=n_multi))
    P('- 레이어 폴리곤 vs 매핑 CSV로 동424를 합친 폴리곤 면적 대조:\n' + pd.DataFrame(chk).to_markdown(index=False))
    summ = zm.groupby('layer').agg(n=('id', 'count'), n_dongs_sum=('n_dongs', 'sum'), area_sum_km2=('area_km2', 'sum'), area_mean=('area_km2', 'mean'), area_min=('area_km2', 'min'), area_max=('area_km2', 'max'),
                                  compact_mean=('compact_pp', 'mean'), compact_min=('compact_pp', 'min'), compact_max=('compact_pp', 'max'), n_multi=('n_parts', lambda s: int((s > 1).sum()))).round(4)
    P('- 요약:\n' + summ.to_markdown())
    zm.to_csv(BDIR / 'zone_metrics.csv', index=False, encoding='utf-8-sig')

    # ---------- 3. Queen 인접 ----------
    pairs, W, islands, deg = queen_adjacency(dong)
    P(f'\n## 3. 동424 Queen 인접 `dong424_queen_adjacency.csv`, `dong424_queen_W.npz`\n- 규칙: 두 동 폴리곤이 교차(intersects)하면 인접(선 공유 edge / 점 공유 vertex). 면적 겹침 없음(사전 확인 overlaps 0쌍).')
    P(f'- 유향 쌍 {len(pairs):,} (무향 {len(pairs)//2:,}), edge {int((pairs.kind=="edge").sum()):,}, vertex {int((pairs.kind=="vertex").sum()):,}; 이웃 수 평균 {deg.mean():.3f}, 최소 {deg.min()}, 최대 {deg.max()}')
    P(f'- 섬(이웃 0) {len(islands)}개: {islands if islands else "없음"}')
    pairs['island_link'] = False
    if islands:
        # 최근접 이웃 연결(표시)
        from shapely.strtree import STRtree
        geoms = dong.geometry.values; ids = list(dong['Dong'].values)
        tree = STRtree(geoms)
        add = []
        for isl in islands:
            k = ids.index(isl); others = [x for x in range(len(ids)) if x != k]
            dists = np.array([geoms[k].distance(geoms[o]) for o in others]); o = others[int(dists.argmin())]
            add += [dict(i=ids[k], j=ids[o], kind='island_nearest', shared_len_m=0.0, island_link=True, dist_m=round(dists.min(), 2)),
                    dict(i=ids[o], j=ids[k], kind='island_nearest', shared_len_m=0.0, island_link=True, dist_m=round(dists.min(), 2))]
            W[k, o] = 1; W[o, k] = 1
            P(f'  - {isl} → 최근접 {ids[o]} ({dists.min():.1f} m) 연결, island_link=True 표시')
        pairs = pd.concat([pairs, pd.DataFrame(add)], ignore_index=True)
    W = sparse.csr_matrix(W); W.eliminate_zeros()
    assert (W != W.T).nnz == 0, '비대칭'
    pairs = pairs.sort_values(['i', 'j']).reset_index(drop=True)
    pairs.to_csv(BDIR / 'dong424_queen_adjacency.csv', index=False, encoding='utf-8-sig')
    sparse.save_npz(BDIR / 'dong424_queen_W.npz', W)
    pd.DataFrame({'idx': range(len(dong)), 'Dong': dong['Dong'].values}).to_csv(BDIR / 'dong424_queen_W_index.csv', index=False)
    # 연결성
    ncomp, _ = sparse.csgraph.connected_components(W, directed=False)
    P(f'- W: {W.shape}, 0/1 대칭, nnz {W.nnz:,}; 행 순서 = `dong424_queen_W_index.csv`(dong_424 레이어 순). 연결성분 {ncomp}개')
    # 레이어 내 LD/LZ 폴리곤이 인접행렬상 연결되는지(비연속 커뮤니티 확인)
    for name, mp, col in [('LZ116', lz, 'life_zone_id'), ('LD2020', l20, 'global_community_id'), ('LD2025', l25, 'global_community_id')]:
        lab = dong[['Dong']].merge(mp[['Dong', col]], on='Dong')[col].values
        bad = 0
        for u in np.unique(lab):
            idx = np.where(lab == u)[0]
            if len(idx) > 1:
                sub = W[idx][:, idx]; nc, _ = sparse.csgraph.connected_components(sub, directed=False); bad += nc > 1
        P(f'- {name}: 인접행렬 기준 비연속 단위 {bad}개')

    # ---------- 4. 동→단위 표 ----------
    u = dong[['Dong', 'Ku', 'ku_name', 'ADM_NM']].rename(columns={'Dong': 'dong424', 'Ku': 'ku', 'ADM_NM': 'dong_name'})
    u = u.merge(lz[['Dong', 'life_zone_id', 'life_zone_name']].rename(columns={'Dong': 'dong424', 'life_zone_id': 'lz116', 'life_zone_name': 'lz_name'}), on='dong424')
    u = u.merge(l20[['Dong', 'global_community_id']].rename(columns={'Dong': 'dong424', 'global_community_id': 'ld2020'}), on='dong424')
    u = u.merge(l25[['Dong', 'global_community_id']].rename(columns={'Dong': 'dong424', 'global_community_id': 'ld2025'}), on='dong424')
    dz = zm[zm.layer == 'dong_424'].set_index('id')
    u['dong_area_km2'] = dz['area_km2'].reindex(u.dong424).values; u['dong_compact'] = dz['compact_pp'].reindex(u.dong424).values
    u['dong_n_neighbors'] = pd.Series(deg, index=dong['Dong'].values).reindex(u.dong424).values.astype(int)
    lzm = zm[zm.layer == 'official_livingzone_116_dongbased'].set_index('id'); ldm = zm[zm.layer == 'leiden_2025_116'].set_index('id'); ld20m = zm[zm.layer == 'leiden_2020_116'].set_index('id')
    u['area_lz'] = lzm['area_km2'].reindex(u.lz116).values; u['compact_lz'] = lzm['compact_pp'].reindex(u.lz116).values; u['n_dongs_lz'] = lzm['n_dongs'].reindex(u.lz116).values
    u['area_ld2025'] = ldm['area_km2'].reindex(u.ld2025).values; u['compact_ld2025'] = ldm['compact_pp'].reindex(u.ld2025).values; u['n_dongs_ld2025'] = ldm['n_dongs'].reindex(u.ld2025).values
    u['area_ld2020'] = ld20m['area_km2'].reindex(u.ld2020).values; u['compact_ld2020'] = ld20m['compact_pp'].reindex(u.ld2020).values
    u['d_area'] = u.area_ld2025 - u.area_lz; u['d_compact'] = u.compact_ld2025 - u.compact_lz
    u['d_n_dongs'] = u.n_dongs_ld2025 - u.n_dongs_lz
    assert len(u) == 424 and u.isna().sum().sum() == 0
    u.to_csv(BDIR / 'dong424_units.csv', index=False, encoding='utf-8-sig')
    P('\n## 4. 동→단위 표 `dong424_units.csv` (424행)\n- 열: dong424, ku, ku_name, dong_name, lz116, lz_name, ld2020, ld2025, dong_area_km2, dong_compact, dong_n_neighbors, area_lz, compact_lz, n_dongs_lz, area_ld2025, compact_ld2025, n_dongs_ld2025, area_ld2020, compact_ld2020, d_area(=ld2025−lz, km²), d_compact(=ld2025−lz), d_n_dongs')
    P('- 연구3 Δ(LD2025 − LZ) 분포(동 단위):\n' + u[['d_area', 'd_compact', 'd_n_dongs']].describe().round(4).to_markdown())
    same = (u.groupby('lz116').ld2025.nunique() == 1) & (u.groupby('lz116').ld2025.first().map(u.groupby('ld2025').lz116.nunique()) == 1)
    P(f'- 공식 생활권과 Leiden 2025가 완전히 같은 동 집합인 단위: {int(same.sum())} / 116')

    # ---------- 5. 저장·해시 ----------
    outs = copied + [BDIR / f for f in ['zone_metrics.csv', 'dong424_queen_adjacency.csv', 'dong424_queen_W.npz', 'dong424_queen_W_index.csv', 'dong424_units.csv']]
    rows = append_manifest(outs, 'a03_boundary_metrics.py')
    P('\n## 5. 해시 (manifest_sha256.csv)\n' + pd.DataFrame(rows).to_markdown(index=False))
    P(f'\n소요 {(dt.datetime.now() - t0).total_seconds():.0f}초')
    REC_MD.write_text('\n'.join(log) + '\n', encoding='utf-8')
    print('기록:', REC_MD)

if __name__ == '__main__':
    main()
