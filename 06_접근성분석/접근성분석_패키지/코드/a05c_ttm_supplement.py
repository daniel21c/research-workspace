# -*- coding: utf-8 -*-
"""P4 보충: 다른 시점 네트워크로 계산할 때 빠지는 출발 격자의 소요시간표 (네트워크 고정 민감도용).

왜 필요한가: ttm{grid}_{net} 의 출발 셀은 그 시점(net) 인구·사업체 기준(pop_or_biz)이다.
  2020 시설·인구를 2025 네트워크로 계산하면(sens_net2025) 2019 인구>0 인데 2025 표에 출발로 없는 셀이 생긴다.
  엔진은 표에 없는 출발을 r=0(미도달)으로 채우므로, 이 셀들을 같은 코드로 따로 계산해 둔다.
확정본(ttm{grid}_{net}/)은 건드리지 않는다. 결과는 별도 폴더 ttm{grid}_{net}_for{year}/ 에 쓴다.
계산 경로는 a05_ttm.py 와 같다(같은 스냅 파일·run_chunk·dijkstra). --check N 이면 확정본에 이미 있는 출발 N개를
다시 계산해 저장된 행과 완전히 같은지 먼저 확인한다(재현성 점검, 결과는 scratch 에만 씀).

실행: python a05c_ttm_supplement.py --net 2025 --for-year 2020 --grid 100 [--check 40]
"""
import argparse, datetime as dt, json, shutil, sys, tempfile, time
from pathlib import Path

import numpy as np, pandas as pd
import pyarrow.dataset as pads
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a00_config as C  # noqa: E402
import a05_ttm as T      # noqa: E402
import a99_manifest as M  # noqa: E402


def main_origins(net, grid):
    d = pads.dataset(str(T.TTM / f'ttm{grid}_{net}'), format='parquet', partitioning='hive')
    return set(pd.unique(d.to_table(columns=['o_grid']).column('o_grid').to_numpy()))


def make_tasks(sub, out_dir, chunk):
    tasks = []
    for ku, g in sub.sort_values('grid_cd').groupby('ku'):
        d = Path(out_dir) / f'ku={ku}'; d.mkdir(parents=True, exist_ok=True)
        for i in range(0, len(g), chunk):
            s = g.iloc[i:i + chunk]
            tasks.append((str(d / f'chunk_{i // chunk:03d}.parquet'), s.grid_cd.tolist(), s.node.tolist()))
    return tasks


def reproduce_check(m, snap, net, grid, n, batch):
    """확정본에 있는 출발 n개를 다시 계산해 저장값과 비교. 반환: dict."""
    d = pads.dataset(str(T.TTM / f'ttm{grid}_{net}'), format='parquet', partitioning='hive')
    have = np.array(sorted(main_origins(net, grid)))
    pick = set(np.random.default_rng(0).choice(have, size=n, replace=False))
    sub = m[m.grid_cd.isin(pick)].copy(); sub['node'] = snap.set_index('grid_cd').loc[sub.grid_cd, 'node_idx'].values
    tmp = Path(tempfile.mkdtemp(prefix='a05c_check_'))
    try:
        for t in make_tasks(sub, tmp / 'x', 10 ** 6):
            T.run_chunk(t)
        new = pd.concat([pd.read_parquet(f) for f in (tmp / 'x').glob('ku=*/chunk_*.parquet')], ignore_index=True)
        old = d.to_table(filter=pads.field('o_grid').isin(list(pick)), columns=['o_grid', 'd_grid', 't_sec']).to_pandas()
        k = ['o_grid', 'd_grid']
        new = new.sort_values(k).reset_index(drop=True); old = old.sort_values(k).reset_index(drop=True)
        same = len(new) == len(old) and (new[k].values == old[k].values).all() and (new.t_sec.values == old.t_sec.values).all()
        return {'n_origins': int(len(sub)), 'n_pairs_new': int(len(new)), 'n_pairs_stored': int(len(old)), 'identical': bool(same)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--net', type=int, required=True, choices=list(C.YEARS), help='네트워크 시점')
    ap.add_argument('--for-year', type=int, required=True, choices=list(C.YEARS), help='시설·인구 시점(엔진 --year)')
    ap.add_argument('--grid', type=int, default=100, choices=[100, 250])
    ap.add_argument('--chunk', type=int, default=200)
    ap.add_argument('--batch', type=int, default=32)
    ap.add_argument('--check', type=int, default=40, help='재현성 점검 출발 수(0=생략)')
    a = ap.parse_args()
    if a.net == a.for_year:
        sys.exit('--net 과 --for-year 가 같으면 보충할 것이 없음')
    t0 = time.time()
    py = C.YEARS[a.for_year]['pop_year']
    m = T.load_master(a.grid, a.net)                      # 격자 순서·좌표 (인구 열은 net 시점 → 아래에서 for-year 인구로 교체)
    popf = pd.read_parquet(C.DATA / 'grid' / f'grid{a.grid}_master.parquet', columns=['grid_cd', f'pop_{py}'])
    assert (popf.grid_cd.values == m.grid_cd.values).all()
    m['pop_for'] = popf[f'pop_{py}'].values
    csr, node_id, xy = T.load_graph(a.net)
    snap = T.snap_cells(m, xy, node_id, a.grid, a.net)    # 확정 스냅 파일을 그대로 읽음(격자 순서 대조)
    del csr
    have = main_origins(a.net, a.grid)
    need = m[(m.pop_for > 0) & ~m.grid_cd.isin(have)].copy()
    need['node'] = snap.node_idx.values[need.index.values]
    T.log(f'{a.net} 네트워크 표 출발 {len(have):,}셀, {py} 인구>0 중 표에 없는 셀 {len(need):,} (인구 {need.pop_for.sum():,.0f})')

    chk = None
    dest_nodes = snap.node_idx.values; dest_cd = m.grid_cd.values.astype(str)
    T._init(a.net, dest_nodes, dest_cd, a.batch)
    if a.check:
        chk = reproduce_check(m, snap, a.net, a.grid, a.check, a.batch)
        T.log('재현성 점검', chk)
        if not chk['identical']:
            sys.exit('재현성 점검 실패: 확정본과 같은 값을 내지 못함 → 중단')

    out_dir = T.TTM / f'ttm{a.grid}_{a.net}_for{a.for_year}'
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {'net_year': a.net, 'for_year': a.for_year, 'grid_m': a.grid, 'chunk': a.chunk,
            'origins_rule': f'pop_{py}>0 이고 ttm{a.grid}_{a.net} 출발에 없는 셀'}
    (out_dir / '_meta.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
    tasks = make_tasks(need, out_dir, a.chunk)
    n_pairs = 0
    for j, t in enumerate(tasks):
        p, n, s = T.run_chunk(t); n_pairs += max(n, 0)
        T.log(f'  [{j + 1}/{len(tasks)}] {Path(p).parent.name}/{Path(p).name} 출발 {len(t[1])} 쌍 {n:,} {s:.1f}s')
    files = sorted(out_dir.glob('ku=*/chunk_*.parquet'))
    total = sum(pq.read_metadata(f).num_rows for f in files)
    got = set(pd.concat([pd.read_parquet(f, columns=['o_grid']) for f in files]).o_grid.unique()) if files else set()
    st = pd.concat([pd.read_parquet(T.stats_path(t[0])) for t in tasks], ignore_index=True)
    summary = {**meta, 'n_origins': int(len(need)), 'pop_origins': float(need.pop_for.sum()),
               'n_origins_with_pairs': int(len(got)), 'n_origins_no_pair_within_30min': int(len(need) - len(got)),
               'n_pairs': int(total), 'reach_15min_cells_median': float(st.n_reach_15.median()) if len(st) else None,
               'snap_gt_max_origins': int(snap.set_index('grid_cd').loc[need.grid_cd, 'snap_gt_max'].sum()),
               'reproduce_check': chk, 'seconds': round(time.time() - t0, 1),
               'created': dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    sp = T.TTM / f'ttm{a.grid}_{a.net}_for{a.for_year}_summary.json'
    sp.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')
    h, b = T.combined_hash(files)
    now = summary['created']
    M.update([M.row(sp, 'a05c_ttm_supplement.py', 1, now),
              {'file': f'{T.rel(out_dir)}/ku=*/chunk_*.parquet ({len(files)} files, combined)', 'sha256': h,
               'bytes': str(b), 'created': now, 'script': 'a05c_ttm_supplement.py', 'rows': str(int(total))}])
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
