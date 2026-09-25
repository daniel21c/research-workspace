# -*- coding: utf-8 -*-
"""P3 보행 네트워크 구축 (network-walk-v1) — OSM 스냅샷 2020-01-01 · 2025-01-01.

입력 : Geofabrik south-korea-{200101|250101}.osm.pbf (a00_config.YEARS / OSM_URL).
       원본 pbf는 06 폴더에 두지 않는다(용량). --pbf 로 지정하거나, 아래 순서로 찾고 없으면 스크래치에 내려받는다:
         $OSM_PBF_DIR → ~/work/pk → <tempdir>/osm_pbf (다운로드 위치)
       SHA-256은 시설 구축 때 기록한 metadata.json(park/raw/*.osm.pbf.metadata.json)과 대조한다.
범위 : 코어엔진 동 424 합집합 + SEOUL_BUFFER_M(2 km) 버퍼(EPSG:5179). 추출은 그 bbox(EPSG:4326)로, 이후 버퍼 폴리곤으로 정밀 절단.
규칙 : WALK_RULES (아래 표). 보행 가능 highway 만 유지, foot/access/sidewalk 태그로 보정.
가중 : 변 길이 = EPSG:5179 평면 거리(m), 시간 = 길이 / (WALK_KMH km/h).
연결 : 가장 큰 연결성분(LCC)만 유지. 성분 분포는 summary 에 기록.
산출 : 01_data/network/walk_{year}_nodes.parquet (node_id, x, y)
       01_data/network/walk_{year}_edges.parquet (u, v, length_m, time_s, highway)
       01_data/network/walk_{year}_graph.npz   (CSR: node_id, x, y, indptr, indices, time_s — a05 가 바로 읽음)
       01_data/network/walk_{year}_summary.json, walk_compare_2020_2025.json(두 해가 모두 있을 때)
       04_구축기록/manifest_sha256.csv(추가), 작업기록.md(추가)
실행 : python a04_network.py --year 2020 [--pbf PATH] [--force]
"""
import argparse, hashlib, json, os, sys, time, tempfile, datetime as dt, urllib.request
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, shapely
from pyproj import Transformer
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a00_config as C

NET = C.DATA / 'network'
META_DIR = C.FACDIR / '03_교육교통공원상가' / 'park' / 'raw'
WALK_MPS = C.WALK_KMH * 1000.0 / 3600.0

# ---------------------------------------------------------------- 보행 규칙표 (구축기록에 그대로 실림)
FOOT_YES = {'yes', 'designated', 'permissive', 'official'}
FOOT_NO = {'no', 'private', 'use_sidepath', 'discouraged'}
ACCESS_NO = {'no', 'private', 'military', 'agricultural', 'forestry'}
SIDEWALK_YES = {'both', 'left', 'right', 'yes'}
HW_KEEP = {'footway', 'path', 'pedestrian', 'steps', 'living_street', 'residential', 'service',
           'tertiary', 'tertiary_link', 'secondary', 'secondary_link', 'primary', 'primary_link',
           'unclassified', 'track', 'road', 'corridor', 'crossing'}
HW_COND = {'trunk', 'trunk_link', 'cycleway', 'bridleway'}     # 조건부: foot 허용(또는 trunk 는 sidewalk) 일 때만
HW_DROP = {'motorway', 'motorway_link', 'raceway', 'bus_guideway', 'busway', 'construction', 'proposed',
           'abandoned', 'razed', 'planned', 'platform', 'services', 'rest_area', 'escape', 'elevator',
           'emergency_bay', 'bus_stop', 'traffic_signals', 'street_lamp', 'no'}
WALK_RULES = [
    ('1', 'highway 태그가 없는 way', '제외'),
    ('2', 'highway ∈ {' + ', '.join(sorted(HW_DROP)) + '}', '제외 (자동차 전용·공사·제안·비도로)'),
    ('3', 'foot ∈ {' + ', '.join(sorted(FOOT_NO)) + '}', '제외'),
    ('4', 'access ∈ {' + ', '.join(sorted(ACCESS_NO)) + '} 이고 foot ∉ {' + ', '.join(sorted(FOOT_YES)) + '}', '제외'),
    ('5', 'highway ∈ {trunk, trunk_link}', 'foot ∈ FOOT_YES 또는 sidewalk ∈ {' + ', '.join(sorted(SIDEWALK_YES)) + '} 일 때만 유지'),
    ('6', 'highway ∈ {cycleway, bridleway}', 'foot ∈ FOOT_YES 일 때만 유지'),
    ('7', 'highway ∈ {' + ', '.join(sorted(HW_KEEP)) + '}', '유지'),
    ('8', '그 밖의 highway 값', '제외'),
    ('9', 'area=yes(광장 등) 인 way', '외곽선을 변으로 유지 (OSMnx 관행)'),
    ('10', 'tunnel/bridge/indoor/sac_scale', '별도 제한 없음 (지하보도·산길 포함)'),
]


def walkable(tags):
    hw = tags.get('highway')
    if hw is None or hw in HW_DROP:
        return None
    foot = tags.get('foot'); access = tags.get('access')
    if foot in FOOT_NO:
        return None
    if access in ACCESS_NO and foot not in FOOT_YES:
        return None
    if hw in ('trunk', 'trunk_link'):
        return hw if (foot in FOOT_YES or tags.get('sidewalk') in SIDEWALK_YES) else None
    if hw in ('cycleway', 'bridleway'):
        return hw if foot in FOOT_YES else None
    return hw if hw in HW_KEEP else None


# ---------------------------------------------------------------- 유틸
def log(*a):
    print(dt.datetime.now().strftime('%H:%M:%S'), *a, flush=True)


def sha256_file(p, buf=1 << 24):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(buf), b''):
            h.update(b)
    return h.hexdigest()


def find_or_download_pbf(year, pbf_arg):
    fn = C.YEARS[year]['osm']
    cands = []
    if pbf_arg:
        cands.append(Path(pbf_arg))
    if os.environ.get('OSM_PBF_DIR'):
        cands.append(Path(os.environ['OSM_PBF_DIR']) / fn)
    cands += [Path.home() / 'work' / 'pk' / fn, Path(tempfile.gettempdir()) / 'osm_pbf' / fn]
    for p in cands:
        if p.exists() and p.stat().st_size > 0:
            log('pbf 사용:', p); return p, False
    dst = Path(tempfile.gettempdir()) / 'osm_pbf' / fn; dst.parent.mkdir(parents=True, exist_ok=True)
    url = C.OSM_URL.format(file=fn); log('다운로드:', url, '->', dst)
    tmp = dst.with_suffix('.part')

    def hook(n, bs, total):
        if n % 200 == 0:
            print(f'\r  {n * bs / 1e6:8.1f} MB / {total / 1e6:.1f} MB', end='', flush=True)
    urllib.request.urlretrieve(url, tmp, hook); print()
    tmp.rename(dst); return dst, True


def verify_pbf(year, pbf):
    fn = C.YEARS[year]['osm']; meta = META_DIR / f'{fn}.metadata.json'
    h = sha256_file(pbf); rec = {'pbf': fn, 'sha256': h, 'bytes': pbf.stat().st_size, 'metadata_json': str(meta)}
    if meta.exists():
        m = json.loads(meta.read_text(encoding='utf-8'))
        rec.update(expected_sha256=m.get('sha256'), expected_bytes=m.get('bytes'), match=(m.get('sha256') == h))
    else:
        rec.update(expected_sha256=None, match=None)
    log('SHA-256', h, 'match =', rec['match']); return rec


def seoul_clip_geom():
    dong = gpd.read_file(C.BOUND_GPKG, layer='dong_424')
    assert dong.crs.to_epsg() == C.CRS
    union = shapely.union_all(dong.geometry.values)
    buf = union.buffer(C.SEOUL_BUFFER_M)
    tr = Transformer.from_crs(C.CRS, 4326, always_xy=True)
    minx, miny, maxx, maxy = buf.bounds
    xs, ys = tr.transform([minx, maxx, minx, maxx], [miny, miny, maxy, maxy])
    bbox = (min(xs), min(ys), max(xs), max(ys))
    return union, buf, bbox


# ---------------------------------------------------------------- OSM 추출
def extract(pbf, bbox):
    import osmium
    W, S, E, N = bbox
    fp = (osmium.FileProcessor(str(pbf), osmium.osm.NODE | osmium.osm.WAY)
          .with_locations()
          .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
          .with_filter(osmium.filter.KeyFilter('highway')))
    ids, lons, lats = [], [], []
    eu, ev, ehw, eway = [], [], [], []
    n_hw = n_walk = n_box = 0
    for w in fp:
        n_hw += 1
        hw = walkable(w.tags)
        if hw is None:
            continue
        n_walk += 1
        refs = []; lo = []; la = []; inside = False
        for nd in w.nodes:
            loc = nd.location
            if not loc.valid():
                continue
            x, y = loc.lon, loc.lat
            if not inside and W <= x <= E and S <= y <= N:
                inside = True
            refs.append(nd.ref); lo.append(x); la.append(y)
        if not inside or len(refs) < 2:
            continue
        n_box += 1
        ids.extend(refs); lons.extend(lo); lats.extend(la)
        eu.extend(refs[:-1]); ev.extend(refs[1:]); ehw.extend([hw] * (len(refs) - 1)); eway.extend([w.id] * (len(refs) - 1))
    log(f'highway way {n_hw:,} → 보행 규칙 통과 {n_walk:,} → bbox 안 {n_box:,}')
    nodes = pd.DataFrame({'node_id': np.asarray(ids, np.int64), 'lon': np.asarray(lons), 'lat': np.asarray(lats)}).drop_duplicates('node_id')
    edges = pd.DataFrame({'u': np.asarray(eu, np.int64), 'v': np.asarray(ev, np.int64),
                          'highway': pd.Categorical(ehw), 'way_id': np.asarray(eway, np.int64)})
    return nodes, edges, {'ways_highway_all': n_hw, 'ways_walk_rule': n_walk, 'ways_in_bbox': n_box}


# ---------------------------------------------------------------- 그래프 정리
def build_graph(nodes, edges, buf):
    tr = Transformer.from_crs(4326, C.CRS, always_xy=True)
    x, y = tr.transform(nodes.lon.values, nodes.lat.values)
    nodes = nodes.assign(x=x, y=y).reset_index(drop=True)
    idx = pd.Series(np.arange(len(nodes)), index=nodes.node_id.values)
    ui = idx.loc[edges.u.values].values; vi = idx.loc[edges.v.values].values
    L = np.hypot(nodes.x.values[ui] - nodes.x.values[vi], nodes.y.values[ui] - nodes.y.values[vi])
    ok = (ui != vi) & (L > 0)
    edges = edges.assign(ui=ui, vi=vi, length_m=L)[ok]
    # 버퍼 폴리곤 정밀 절단: 양 끝점 중 하나라도 안에 있으면 유지
    inside = shapely.contains_xy(buf, nodes.x.values, nodes.y.values)
    edges = edges[inside[edges.ui.values] | inside[edges.vi.values]]
    # 중복 변(같은 노드쌍) → 최소 길이 하나
    a = np.minimum(edges.ui.values, edges.vi.values); b = np.maximum(edges.ui.values, edges.vi.values)
    edges = edges.assign(ui=a, vi=b).sort_values('length_m').drop_duplicates(['ui', 'vi']).reset_index(drop=True)
    n = len(nodes)
    A = sp.coo_matrix((np.ones(len(edges)), (edges.ui.values, edges.vi.values)), shape=(n, n)).tocsr()
    ncomp, lab = connected_components(A, directed=False)
    used = np.zeros(n, bool); used[edges.ui.values] = True; used[edges.vi.values] = True
    sizes = np.bincount(lab[used], minlength=ncomp)
    big = int(np.argmax(sizes))
    keep_e = (lab[edges.ui.values] == big)
    comp = {'n_components': int((sizes > 0).sum()), 'lcc_nodes': int(sizes[big]), 'used_nodes': int(used.sum()),
            'lcc_node_share': float(sizes[big] / used.sum()),
            'lcc_edge_share': float(keep_e.sum() / len(edges)),
            'lcc_km_share': float(edges.length_m.values[keep_e].sum() / edges.length_m.values.sum()),
            'components_ge100_nodes': int((sizes >= 100).sum()), 'components_ge1000_nodes': int((sizes >= 1000).sum()),
            'second_largest_nodes': int(np.sort(sizes)[-2]) if (sizes > 0).sum() > 1 else 0}
    edges = edges[keep_e].reset_index(drop=True)
    # LCC 노드만, 연속 인덱스로 재번호
    keep_n = np.zeros(n, bool); keep_n[edges.ui.values] = True; keep_n[edges.vi.values] = True
    newid = -np.ones(n, np.int64); newid[keep_n] = np.arange(keep_n.sum())
    nodes = nodes[keep_n].reset_index(drop=True)
    edges = edges.assign(ui=newid[edges.ui.values], vi=newid[edges.vi.values],
                         time_s=edges.length_m.values / WALK_MPS)
    return nodes, edges, comp


def to_csr(nodes, edges):
    n = len(nodes)
    r = np.concatenate([edges.ui.values, edges.vi.values]); c = np.concatenate([edges.vi.values, edges.ui.values])
    t = np.concatenate([edges.time_s.values, edges.time_s.values]).astype(np.float32)
    return sp.coo_matrix((t, (r, c)), shape=(n, n)).tocsr()


# ---------------------------------------------------------------- 기록
def rel(p):
    return str(Path(p).resolve().relative_to(C.ROOT.resolve())).replace('\\', '/')


def update_manifest(outs, now, script='a04_network.py'):
    """manifest_sha256.csv 열: file,sha256,bytes,created,script (같은 file 은 교체)."""
    mf = C.REC / 'manifest_sha256.csv'
    rows = pd.DataFrame([{'file': rel(p), 'sha256': sha256_file(p), 'bytes': Path(p).stat().st_size,
                          'created': now, 'script': script, 'rows': n} for p, n in outs])
    if mf.exists():
        old = pd.read_csv(mf, encoding='utf-8-sig')
        if 'file' not in old.columns and 'path' in old.columns:
            old = old.rename(columns={'path': 'file'})
        old = old[~old['file'].isin(rows['file'])]
        rows = pd.concat([old, rows], ignore_index=True)
    rows.to_csv(mf, index=False, encoding='utf-8-sig')


def append_worklog(text):
    wl = C.REC / '작업기록.md'
    head = '# 06_접근성분석 작업기록\n\n' if not wl.exists() else wl.read_text(encoding='utf-8')
    wl.write_text(head + text, encoding='utf-8')


def compare_years():
    s = {}
    for y in C.YEARS:
        p = NET / f'walk_{y}_summary.json'
        if p.exists():
            s[y] = json.loads(p.read_text(encoding='utf-8'))
    if len(s) < 2:
        return None
    a, b = s[2020], s[2025]
    cmp = {'years': [2020, 2025]}
    for k in ['nodes', 'edges', 'total_km']:
        cmp[k] = {'2020': a[k], '2025': b[k], 'pct_change': (b[k] - a[k]) / a[k] * 100 if a[k] else None}
    hw = sorted(set(a['by_highway_km']) | set(b['by_highway_km']))
    cmp['by_highway_km'] = {h: {'2020': a['by_highway_km'].get(h, 0), '2025': b['by_highway_km'].get(h, 0)} for h in hw}
    (NET / 'walk_compare_2020_2025.json').write_text(json.dumps(cmp, ensure_ascii=False, indent=1), encoding='utf-8')
    return cmp


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', type=int, required=True, choices=list(C.YEARS))
    ap.add_argument('--pbf', default=None, help='pbf 경로(없으면 탐색/다운로드)')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--allow-hash-mismatch', action='store_true')
    a = ap.parse_args()
    y = a.year; NET.mkdir(parents=True, exist_ok=True)
    out_nodes = NET / f'walk_{y}_nodes.parquet'; out_edges = NET / f'walk_{y}_edges.parquet'
    out_npz = NET / f'walk_{y}_graph.npz'; out_sum = NET / f'walk_{y}_summary.json'
    if out_sum.exists() and not a.force:
        log('이미 있음 (--force 로 재생성):', out_sum); compare_years(); return
    t0 = time.time()
    pbf, downloaded = find_or_download_pbf(y, a.pbf)
    hrec = verify_pbf(y, pbf)
    if hrec['match'] is False and not a.allow_hash_mismatch:
        sys.exit(f'SHA-256 불일치: {hrec}  (--allow-hash-mismatch 로 강행 가능)')
    union, buf, bbox = seoul_clip_geom(); log('bbox(4326)', [round(v, 4) for v in bbox])
    nodes, edges, cnt = extract(pbf, bbox)
    log(f'추출 노드 {len(nodes):,}, 변(세그먼트) {len(edges):,}')
    nodes, edges, comp = build_graph(nodes, edges, buf)
    log(f'LCC 노드 {len(nodes):,}, 변 {len(edges):,}, 총 {edges.length_m.sum() / 1000:,.1f} km; 성분 {comp}')
    # 산출
    nodes_out = nodes[['node_id', 'x', 'y']].copy()
    edges_out = pd.DataFrame({'u': nodes.node_id.values[edges.ui.values], 'v': nodes.node_id.values[edges.vi.values],
                              'length_m': edges.length_m.values.astype(np.float32), 'time_s': edges.time_s.values.astype(np.float32),
                              'highway': edges.highway.astype(str).values, 'way_id': edges.way_id.values})
    nodes_out.to_parquet(out_nodes, index=False); edges_out.to_parquet(out_edges, index=False)
    csr = to_csr(nodes, edges)
    np.savez_compressed(out_npz, node_id=nodes.node_id.values, x=nodes.x.values, y=nodes.y.values,
                        indptr=csr.indptr, indices=csr.indices, time_s=csr.data)
    by_hw_km = edges.groupby(edges.highway.astype(str))['length_m'].sum().div(1000).round(2).to_dict()
    by_hw_n = edges.groupby(edges.highway.astype(str)).size().to_dict()
    summary = {
        'year': y, 'osm_date': C.YEARS[y]['osm_date'], 'source_url': C.OSM_URL.format(file=C.YEARS[y]['osm']),
        'pbf': hrec, 'pbf_downloaded_now': downloaded,
        'clip': {'basis': 'dong_424 union + buffer', 'buffer_m': C.SEOUL_BUFFER_M, 'crs': C.CRS, 'bbox_4326': bbox,
                 'union_area_km2': round(union.area / 1e6, 2), 'buffer_area_km2': round(buf.area / 1e6, 2)},
        'walk_kmh': C.WALK_KMH, 'counts': cnt,
        'nodes': int(len(nodes)), 'edges': int(len(edges)), 'total_km': round(float(edges.length_m.sum() / 1000), 3),
        'mean_edge_m': round(float(edges.length_m.mean()), 2), 'median_edge_m': round(float(edges.length_m.median()), 2),
        'components': comp, 'lcc_only': True,
        'by_highway_km': by_hw_km, 'by_highway_edges': {k: int(v) for k, v in by_hw_n.items()},
        'rules': WALK_RULES, 'elapsed_s': round(time.time() - t0, 1), 'created_utc': dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'files': [out_nodes.name, out_edges.name, out_npz.name],
    }
    out_sum.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')
    now = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    update_manifest([(out_nodes, len(nodes_out)), (out_edges, len(edges_out)), (out_npz, len(nodes_out)), (out_sum, 1)], now)
    append_worklog(f'\n## {now[:10]} — P3 보행 네트워크 {y} (`a04_network.py --year {y}`)\n\n'
                   f'- 원천 {C.YEARS[y]["osm"]} SHA-256 {hrec["sha256"][:16]}… (metadata 대조 {hrec["match"]}). 범위 동424 합집합+{C.SEOUL_BUFFER_M} m.\n'
                   f'- highway way {cnt["ways_highway_all"]:,} → 보행 규칙 {cnt["ways_walk_rule"]:,} → bbox {cnt["ways_in_bbox"]:,}. '
                   f'LCC 노드 {len(nodes):,}, 변 {len(edges):,}, {edges.length_m.sum() / 1000:,.1f} km (LCC 변 비율 {comp["lcc_edge_share"] * 100:.2f}%, 성분 {comp["n_components"]:,}개).\n'
                   f'- 산출: `01_data/network/walk_{y}_{{nodes,edges}}.parquet`, `walk_{y}_graph.npz`, `walk_{y}_summary.json`. {summary["elapsed_s"]} s.\n')
    cmp = compare_years()
    if cmp:
        log('2020→2025 비교:', {k: cmp[k] for k in ['edges', 'total_km']})
    log('완료', round(time.time() - t0, 1), 's')


if __name__ == '__main__':
    main()
