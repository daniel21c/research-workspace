# -*- coding: utf-8 -*-
"""P4 격자→격자 보행 소요시간표 (ttm-walk-{100|250}m-v1), 2020 · 2025.

입력 : 데이터/입력/grid/grid{100|250}_master.parquet (a01), 데이터/입력/network/walk_{year}_graph.npz (a04).
출발 : --origins pop_or_biz(기본) = 해당 시점 인구>0 또는 사업체>0 셀(연구1 후보지 포함) / pop = 인구>0 셀.
       --ku 로 구를 지정하면 출발 셀만 그 구로 제한(시험 계산). 도착은 항상 서울 전체 셀.
스냅 : 셀 중심 → 가장 가까운 그래프 노드(cKDTree, EPSG:5179). 스냅 거리는 snap 파일에 기록하고 시간에는 더하지 않는다
       (SNAP_MAX_M 초과 셀은 flag). 같은 노드에 스냅된 셀 사이 시간은 0 이 될 수 있다.
계산 : scipy.sparse.csgraph.dijkstra(무향, limit=TTM_MAX_SEC) 를 출발 노드 묶음(--batch)으로 실행,
       도착 노드 시간을 도착 셀에 대응. t ≤ TTM_MAX_SEC(1,800 s) 인 쌍만 저장. t_sec 는 반올림 uint16.
저장 : 데이터/입력/ttm/ttm{grid}_{year}/ku={ku}/chunk_{i:03d}.parquet  (o_grid, d_grid, t_sec) — Hive 분할, pyarrow.dataset 으로 읽음.
       청크(--chunk 출발 셀 수)마다 파일이 생기며 이미 있으면 건너뜀(재시작 가능). 청크별 출발셀 통계 _stats/ku=…_chunk_….parquet.
       데이터/입력/ttm/snap{grid}_{year}.parquet (grid_cd, node_idx, node_id, snap_m, snap_gt_max)
       데이터/입력/ttm/ttm{grid}_{year}_summary[_ku…].json, ttm{grid}_{year}_origin_stats[_ku…].parquet, *_detour[_ku…].json
실행 : python a05_ttm.py --year 2025 --grid 100 [--ku 11010 ...] [--origins pop_or_biz|pop] [--workers 4] [--chunk 200] [--batch 32] [--validate 200]
"""
import argparse, hashlib, json, os, sys, time, datetime as dt
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
import pyarrow as pa, pyarrow.parquet as pq
import scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a00_config as C

TTM = C.DATA / 'ttm'
WALK_MPS = C.WALK_KMH * 1000.0 / 3600.0
T15 = C.T_SEC


def log(*a):
    print(dt.datetime.now().strftime('%H:%M:%S'), *a, flush=True)


# ---------------------------------------------------------------- 입력
def load_graph(year):
    z = np.load(C.DATA / 'network' / f'walk_{year}_graph.npz')
    n = len(z['node_id'])
    csr = sp.csr_matrix((z['time_s'].astype(np.float64), z['indices'], z['indptr']), shape=(n, n))
    return csr, z['node_id'], np.column_stack([z['x'], z['y']])


def load_master(grid, year):
    py = C.YEARS[year]['pop_year']
    m = pd.read_parquet(C.DATA / 'grid' / f'grid{grid}_master.parquet',
                        columns=['grid_cd', 'x_c', 'y_c', 'ku', f'pop_{py}', f'biz_{py}'])
    return m.rename(columns={f'pop_{py}': 'pop', f'biz_{py}': 'biz'}).reset_index(drop=True)


def snap_cells(m, xy, node_id, grid, year):
    p = TTM / f'snap{grid}_{year}.parquet'
    if p.exists():
        s = pd.read_parquet(p)
        if len(s) == len(m) and (s.grid_cd.values == m.grid_cd.values).all():
            return s
    tree = cKDTree(xy)
    d, i = tree.query(np.column_stack([m.x_c.values, m.y_c.values]), k=1)
    s = pd.DataFrame({'grid_cd': m.grid_cd.values, 'node_idx': i.astype(np.int64), 'node_id': node_id[i],
                      'snap_m': d.astype(np.float32), 'snap_gt_max': d > C.SNAP_MAX_M})
    s.to_parquet(p, index=False); return s


# ---------------------------------------------------------------- 워커
G = {}


def _init(year, dest_nodes, dest_cd, batch):
    csr, node_id, xy = load_graph(year)
    G.update(csr=csr, dest_nodes=dest_nodes, dest_cd=dest_cd, batch=batch)


def stats_path(out):
    """청크 통계 파일: <out_dir>/_stats/ku=XXXXX_chunk_NNN.parquet (pyarrow.dataset 은 '_' 폴더를 무시)."""
    out = Path(out); d = out.parent.parent / '_stats'; d.mkdir(exist_ok=True)
    return d / f'{out.parent.name}_{out.stem}.parquet'


def run_chunk(task):
    """task: (out_path, o_cd(list), o_node(list)) → 청크 parquet + stats parquet 저장, (path, n_pairs, sec) 반환."""
    out, o_cd, o_node = task
    out = Path(out); stats_p = stats_path(out)
    if out.exists() and stats_p.exists():
        return str(out), -1, 0.0
    t0 = time.time()
    csr, dest_nodes, dest_cd, B = G['csr'], G['dest_nodes'], G['dest_cd'], G['batch']
    o_node = np.asarray(o_node); o_cd = np.asarray(o_cd)
    uniq, inv = np.unique(o_node, return_inverse=True)
    parts = []; n15 = np.zeros(len(o_cd), np.int32); n30 = np.zeros(len(o_cd), np.int32)
    for s in range(0, len(uniq), B):
        src = uniq[s:s + B]
        D = dijkstra(csr, directed=False, indices=src, limit=C.TTM_MAX_SEC)[:, dest_nodes]   # (b, n_dest)
        for k in range(len(src)):
            row = D[k]; ok = row <= C.TTM_MAX_SEC
            if not ok.any():
                continue
            t = np.rint(row[ok]).astype(np.uint16); dcd = dest_cd[ok]
            for oi in np.flatnonzero(inv == s + k):
                parts.append(pd.DataFrame({'o_grid': o_cd[oi], 'd_grid': dcd, 't_sec': t}))
                n30[oi] = ok.sum(); n15[oi] = int((row[ok] <= T15).sum())
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame({'o_grid': pd.Series([], dtype=str), 'd_grid': pd.Series([], dtype=str), 't_sec': pd.Series([], dtype=np.uint16)})
    tbl = pa.Table.from_pandas(df, preserve_index=False).cast(pa.schema([('o_grid', pa.string()), ('d_grid', pa.string()), ('t_sec', pa.uint16())]))
    tmp = out.with_suffix('.tmp'); pq.write_table(tbl, tmp, compression='zstd'); os.replace(tmp, out)
    sec = time.time() - t0
    pd.DataFrame({'o_grid': o_cd, 'n_reach_15': n15, 'n_reach_30': n30,
                  'chunk_sec': np.float32(sec), 'chunk_n': np.int32(len(o_cd))}).to_parquet(stats_p, index=False)
    return str(out), len(df), sec


# ---------------------------------------------------------------- 검증 (우회율)
def detour_check(out_dir, m, n_pairs, seed=0):
    rng = np.random.default_rng(seed)
    files = sorted(out_dir.glob('ku=*/chunk_*.parquet'))
    if not files:
        return None
    pick = [files[i] for i in rng.choice(len(files), size=min(len(files), 20), replace=False)]
    df = pd.concat([pd.read_parquet(f) for f in pick], ignore_index=True)
    df = df[df.o_grid != df.d_grid]
    df = df.iloc[rng.choice(len(df), size=min(n_pairs, len(df)), replace=False)].reset_index(drop=True)
    xy = m.set_index('grid_cd')[['x_c', 'y_c']]
    o = xy.loc[df.o_grid].values; d = xy.loc[df.d_grid].values
    line_m = np.hypot(o[:, 0] - d[:, 0], o[:, 1] - d[:, 1]); t_line = line_m / WALK_MPS
    ratio = df.t_sec.values / t_line
    q = lambda a: {f'p{int(p)}': round(float(np.percentile(a, p)), 3) for p in (5, 10, 25, 50, 75, 90, 95)}
    far = line_m >= 500
    return {'n_pairs': int(len(df)), 'ratio_quantiles_all': q(ratio), 'share_ratio_lt1_all': round(float((ratio < 1).mean()), 4),
            'share_ratio_in_1.2_1.6_all': round(float(((ratio >= 1.2) & (ratio <= 1.6)).mean()), 4),
            'n_pairs_line_ge500m': int(far.sum()), 'ratio_quantiles_line_ge500m': q(ratio[far]) if far.any() else None,
            'share_ratio_lt1_line_ge500m': round(float((ratio[far] < 1).mean()), 4) if far.any() else None,
            'mean_ratio_line_ge500m': round(float(ratio[far].mean()), 3) if far.any() else None,
            'note': '스냅 거리(셀 중심→노드)를 시간에 더하지 않아 가까운 쌍(같은 노드에 스냅 등)은 비율<1 또는 0 이 나올 수 있음. 직선 500 m 이상 쌍의 분포가 우회율의 본 값.'}


# ---------------------------------------------------------------- 기록
def rel(p):
    return str(Path(p).resolve().relative_to(C.ROOT.resolve())).replace('\\', '/')


def sha256_file(p, buf=1 << 24):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(buf), b''):
            h.update(b)
    return h.hexdigest()


def combined_hash(files):
    """청크 파일 집합의 결합 해시: 파일별 sha256 을 상대경로 순으로 이어 붙여 다시 sha256."""
    h = hashlib.sha256(); total = 0
    for f in sorted(files, key=lambda f: rel(f)):
        h.update(rel(f).encode()); h.update(sha256_file(f).encode()); total += Path(f).stat().st_size
    return h.hexdigest(), total


def update_manifest(paths, now, script='a05_ttm.py', extra_rows=()):
    """paths: [(path, rows)]. manifest 열: file,sha256,bytes,created,script,rows"""
    mf = C.MANIFEST
    rows = pd.DataFrame([{'file': rel(p), 'sha256': sha256_file(p), 'bytes': Path(p).stat().st_size, 'created': now, 'script': script, 'rows': n}
                         for p, n in paths] + list(extra_rows))
    if mf.exists():
        old = pd.read_csv(mf, encoding='utf-8-sig')
        if 'file' not in old.columns and 'path' in old.columns:
            old = old.rename(columns={'path': 'file'})
        old = old[~old['file'].isin(rows['file'])]; rows = pd.concat([old, rows], ignore_index=True)
    rows.to_csv(mf, index=False, encoding='utf-8-sig')


def append_worklog(text):
    wl = C.REC / '작업기록.md'
    head = '# 06_접근성분석 작업기록\n\n' if not wl.exists() else wl.read_text(encoding='utf-8')
    wl.write_text(head + text, encoding='utf-8')


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', type=int, required=True, choices=list(C.YEARS))
    ap.add_argument('--grid', type=int, required=True, choices=[100, 250])
    ap.add_argument('--ku', type=int, nargs='*', default=None, help='출발 셀을 이 구(들)로 제한 (예: 11010 종로구)')
    ap.add_argument('--origins', default='pop_or_biz', choices=['pop_or_biz', 'pop'])
    ap.add_argument('--workers', type=int, default=1)
    ap.add_argument('--chunk', type=int, default=200, help='청크당 출발 셀 수 (같은 출력 폴더에서는 바꿀 수 없음: _meta.json 대조)')
    ap.add_argument('--batch', type=int, default=32, help='dijkstra 한 번에 넣는 출발 노드 수 (메모리 = batch × 노드수 × 8B)')
    ap.add_argument('--validate', type=int, default=200, help='우회율 검증 표본 쌍 수 (0=생략)')
    ap.add_argument('--out', default=None, help='출력 폴더(기본 데이터/입력/ttm/ttm{grid}_{year})')
    ap.add_argument('--max-seconds', type=float, default=0, help='이 시간이 지나면 새 청크를 시작하지 않고 종료(코드 3). 다시 실행하면 이어서 계산')
    a = ap.parse_args()
    t0 = time.time(); TTM.mkdir(parents=True, exist_ok=True)
    out_dir = Path(a.out) if a.out else TTM / f'ttm{a.grid}_{a.year}'; out_dir.mkdir(parents=True, exist_ok=True)
    tag = ('_ku' + '_'.join(map(str, a.ku))) if a.ku else ''
    # 출력 폴더 메타: 청크 크기·출발 규칙이 다르면 청크 파일이 어긋나므로 거부
    meta_p = out_dir / '_meta.json'
    meta = {'year': a.year, 'grid_m': a.grid, 'chunk': a.chunk, 'origins_rule': a.origins}
    if meta_p.exists():
        old = json.loads(meta_p.read_text(encoding='utf-8'))
        if any(old.get(k) != v for k, v in meta.items()):
            sys.exit(f'출력 폴더 {out_dir} 는 {old} 로 만들어졌음. 같은 --chunk/--origins 를 쓰거나 --out 으로 다른 폴더를 지정하세요.')
    else:
        meta_p.write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')

    m = load_master(a.grid, a.year)
    csr, node_id, xy = load_graph(a.year)
    log(f'격자 {a.grid}m {len(m):,}셀, 네트워크 {a.year} 노드 {csr.shape[0]:,}')
    snap = snap_cells(m, xy, node_id, a.grid, a.year)
    del csr
    log(f'스냅 거리 중위 {np.median(snap.snap_m):.1f} m, 평균 {snap.snap_m.mean():.1f} m, >{C.SNAP_MAX_M} m {int(snap.snap_gt_max.sum()):,}셀')

    orig = (m['pop'] > 0) if a.origins == 'pop' else ((m['pop'] > 0) | (m['biz'] > 0))
    if a.ku:
        orig &= m.ku.isin(a.ku)
    om = m[orig.values].copy(); om['node'] = snap.node_idx.values[orig.values]
    dest_nodes = snap.node_idx.values; dest_cd = m.grid_cd.values.astype(str)
    log(f'출발 셀 {len(om):,} ({a.origins}{" ku=" + str(a.ku) if a.ku else ""}), 도착 셀 {len(dest_cd):,}')

    # 청크 작업 목록 (구별 폴더, 구 안에서 grid_cd 순)
    tasks = []
    for ku, g in om.sort_values('grid_cd').groupby('ku'):
        d = out_dir / f'ku={ku}'; d.mkdir(exist_ok=True)
        for i in range(0, len(g), a.chunk):
            sub = g.iloc[i:i + a.chunk]
            tasks.append((str(d / f'chunk_{i // a.chunk:03d}.parquet'), sub.grid_cd.tolist(), sub.node.tolist()))
    todo = [t for t in tasks if not (Path(t[0]).exists() and stats_path(t[0]).exists())]
    log(f'청크 {len(tasks)}개 (남은 것 {len(todo)}개), workers={a.workers}, batch={a.batch}')

    n_pairs = 0; sec_sum = 0.0; n_done_orig = 0; t1 = time.time(); stopped = False
    deadline = (t0 + a.max_seconds) if a.max_seconds > 0 else None
    if a.workers <= 1:
        _init(a.year, dest_nodes, dest_cd, a.batch)
        for j, t in enumerate(todo):
            if deadline and time.time() > deadline:
                stopped = True; break
            p, n, s = run_chunk(t); n_pairs += max(n, 0); sec_sum += s; n_done_orig += len(t[1])
            log(f'  [{j + 1}/{len(todo)}] {Path(p).parent.name}/{Path(p).name} 쌍 {n:,} {s:.1f}s ({s / len(t[1]) * 1000:.0f} ms/출발셀)')
    else:
        with ProcessPoolExecutor(max_workers=a.workers, initializer=_init, initargs=(a.year, dest_nodes, dest_cd, a.batch)) as ex:
            pending = {}; it = iter(enumerate(todo)); j_done = 0
            while True:
                while len(pending) < a.workers * 2:
                    if deadline and time.time() > deadline:
                        break
                    try:
                        j, t = next(it)
                    except StopIteration:
                        break
                    pending[ex.submit(run_chunk, t)] = t
                if not pending:
                    break
                from concurrent.futures import wait, FIRST_COMPLETED
                done, _ = wait(list(pending), return_when=FIRST_COMPLETED)
                for f in done:
                    t = pending.pop(f); p, n, s = f.result(); j_done += 1
                    n_pairs += max(n, 0); sec_sum += s; n_done_orig += len(t[1])
                    log(f'  [{j_done}/{len(todo)}] {Path(p).parent.name}/{Path(p).name} 쌍 {n:,} {s:.1f}s')
            stopped = j_done < len(todo)
    if stopped:
        log(f'--max-seconds {a.max_seconds:.0f}s 도달: {n_done_orig:,}셀 계산 후 중단. 남은 청크는 다시 실행하면 이어서 계산됩니다 (종료 코드 3).')
        sys.exit(3)
    wall = time.time() - t1

    # 출발셀 통계 (모든 청크의 stats 합침)
    st = pd.concat([pd.read_parquet(stats_path(t[0])).assign(chunk_id=i) for i, t in enumerate(tasks)], ignore_index=True)
    st = st.merge(snap[['grid_cd', 'snap_m', 'snap_gt_max']], left_on='o_grid', right_on='grid_cd', how='left').drop(columns='grid_cd')
    st_p = TTM / f'ttm{a.grid}_{a.year}_origin_stats{tag}.parquet'; st.to_parquet(st_p, index=False)
    files = list(out_dir.glob('ku=*/chunk_*.parquet'))
    total_pairs = sum(pq.read_metadata(f).num_rows for f in files)
    summary = {
        'year': a.year, 'grid_m': a.grid, 'origins_rule': a.origins, 'ku_filter': a.ku, 'walk_kmh': C.WALK_KMH,
        'ttm_max_sec': C.TTM_MAX_SEC, 'snap_max_m': C.SNAP_MAX_M, 'snap_added_to_time': False,
        'n_cells_all': int(len(m)), 'n_origins': int(len(om)), 'n_destinations': int(len(dest_cd)),
        'n_chunks': len(tasks), 'n_chunks_computed_now': len(todo), 'n_pairs_total_in_dir': int(total_pairs),
        'reach_15min_cells': {'mean': round(float(st.n_reach_15.mean()), 1), 'median': float(st.n_reach_15.median()),
                              'p10': float(st.n_reach_15.quantile(.1)), 'p90': float(st.n_reach_15.quantile(.9)), 'zero': int((st.n_reach_15 == 0).sum())},
        'reach_30min_cells': {'mean': round(float(st.n_reach_30.mean()), 1), 'median': float(st.n_reach_30.median()),
                              'p10': float(st.n_reach_30.quantile(.1)), 'p90': float(st.n_reach_30.quantile(.9)), 'zero': int((st.n_reach_30 == 0).sum())},
        'snap_m_origins': {'mean': round(float(st.snap_m.mean()), 1), 'median': round(float(st.snap_m.median()), 1),
                           'p95': round(float(st.snap_m.quantile(.95)), 1), 'max': round(float(st.snap_m.max()), 1), 'n_gt_max': int(st.snap_gt_max.sum())},
        'snap_m_all_cells': {'mean': round(float(snap.snap_m.mean()), 1), 'median': round(float(snap.snap_m.median()), 1),
                             'p95': round(float(snap.snap_m.quantile(.95)), 1), 'n_gt_max': int(snap.snap_gt_max.sum())},
        'timing': {'wall_sec': round(wall, 1), 'cpu_sec_chunks': round(sec_sum, 1), 'origins_computed_now': int(n_done_orig),
                   'ms_per_origin_cpu': round(sec_sum / n_done_orig * 1000, 1) if n_done_orig else None, 'workers': a.workers, 'batch': a.batch},
        'out_dir': rel(out_dir), 'created_utc': dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    }
    ch = st.drop_duplicates('chunk_id').dropna(subset=['chunk_sec']) if 'chunk_sec' in st.columns else None
    if ch is not None and len(ch) and ch.chunk_n.sum() > 0:
        summary['timing']['ms_per_origin_cpu_all_chunks'] = round(float(ch.chunk_sec.sum() / ch.chunk_n.sum() * 1000), 1)
        summary['timing']['cpu_sec_all_chunks'] = round(float(ch.chunk_sec.sum()), 1)
    if a.validate:
        summary['detour_check'] = detour_check(out_dir, m, a.validate)
        log('우회율(직선≥500m) 분위:', summary['detour_check'] and summary['detour_check']['ratio_quantiles_line_ge500m'])
    sum_p = TTM / f'ttm{a.grid}_{a.year}_summary{tag}.json'
    sum_p.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')
    now = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ch_hash, ch_bytes = combined_hash(files)
    update_manifest([(sum_p, 1), (st_p, len(st)), (TTM / f'snap{a.grid}_{a.year}.parquet', len(snap))], now,
                    extra_rows=[{'file': f'{rel(out_dir)}/ku=*/chunk_*.parquet ({len(files)} files, combined)', 'sha256': ch_hash,
                                 'bytes': ch_bytes, 'created': now, 'script': 'a05_ttm.py', 'rows': int(total_pairs)}])
    if n_done_orig:  # 새로 계산한 것이 없으면(요약·manifest 갱신만) 작업기록은 남기지 않음
      append_worklog(f'\n## {now[:10]} — P4 소요시간표 {a.grid}m {a.year}{tag} (`a05_ttm.py --year {a.year} --grid {a.grid}{" --ku " + " ".join(map(str, a.ku)) if a.ku else ""}`)\n\n'
                   f'- 출발 {len(om):,}셀({a.origins}), 도착 {len(dest_cd):,}셀, 저장 쌍 {total_pairs:,}(≤{C.TTM_MAX_SEC}s). 15분 도달 셀 중위 {summary["reach_15min_cells"]["median"]:.0f}, 30분 {summary["reach_30min_cells"]["median"]:.0f}.\n'
                   f'- 스냅 거리 중위 {summary["snap_m_all_cells"]["median"]} m, >{C.SNAP_MAX_M} m {summary["snap_m_all_cells"]["n_gt_max"]:,}셀(전체). 계산 {n_done_orig:,}셀 {wall:.0f}s (workers {a.workers}).\n'
                   f'- 산출: `{rel(out_dir)}/ku=*/chunk_*.parquet`, `{rel(sum_p)}`, `{rel(st_p)}`.\n')
    log('완료', round(time.time() - t0, 1), 's; 요약', sum_p)


if __name__ == '__main__':
    main()
