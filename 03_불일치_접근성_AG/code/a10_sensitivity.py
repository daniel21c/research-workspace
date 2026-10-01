# -*- coding: utf-8 -*-
"""Q1·Q2 범주 의존과 시설 시점 민감도(2026-10-02 데이터 사용 정합 감사 S2-1 대응).

a01과 똑같은 통행 기준 경로·무작위 100경로(같은 시드·같은 코드)를 다시 만들고, 매 상태를 세 가지 L로 센다.
  all7 : 원고의 L(7범주). a01_states.csv의 ΔL과 전 상태 일치를 assert한다(재현 확인).
  five : 문화·행정·안전을 뺀 5범주로 센 고유 주민 L(같은 보행 도달 행렬의 열 부분집합).
  noC  : 시점 등급 C 세 유형(공공도서관·주민센터·소방서·119안전센터)을 시설 목록에서 빼고 다시 센 L.
         행정·안전은 두 유형이 모두 C라 범주 전체가 빠지고, 문화는 공공도서관만 빠진다(시설 패키지 표 A.4 등급).
또 범주별 단독 누락(그 범주에서 누락된 주민)의 경로 끝 변화, 대안 지도 1000장(a02 저장 표본)에 대한 five·noC의 Q2 결과를 낸다.
실행: python code/a10_sensitivity.py 2025   (2020도 같음)
출력: results/{연도}/a10_sensitivity.json, a10_states_subsets.csv
"""
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent; AG = HERE.parent; ROOT = AG.parent
sys.path.insert(0, str(HERE)); import study as S  # noqa: E402
import a01_flow_random as A1  # noqa: E402
from a02_ensemble import SEEDS  # noqa: E402

NREP = 100
C_TYPES = ['공공도서관', '주민센터', '소방서·119안전센터']  # 시점 등급 C(표 A.4)
CI = {c: j for j, c in enumerate(S.CATS)}
FIVE = [CI[c] for c in S.CATS if c not in ('문화', '행정·안전')]


class ReachNoC:
    """study.Accessibility와 같은 규칙(15분, 인구 있는 출발 격자, 출발 격자→도착 격자의 동)으로, C 유형을 뺀 시설의 범주별 도달 여부만 계산."""

    def __init__(self, D, paths, ev):
        gm = D['gm']; ng = len(gm); code = pd.Series(np.arange(ng), index=gm.grid_cd)
        f = pd.read_parquet(paths['units'], columns=['year', '시설', '분석가능', 'role', 'cat_A', 'grid100_cd'])
        f = f[(f.year == D['year']) & f['분석가능'].astype(bool) & f['role'].ne('control') & f.cat_A.isin(S.CATS) & ~f['시설'].isin(C_TYPES)]
        gi = f.grid100_cd.map(code); ok = gi.notna()
        mask = np.zeros(ng, np.uint8)
        np.bitwise_or.at(mask, gi[ok].to_numpy(int), np.left_shift(1, f.loc[ok, 'cat_A'].map(CI).to_numpy()).astype(np.uint8))
        mapper = np.full(ng, -1, int); mapper[ev.pos] = np.arange(ev.n); es = []
        for pth in sorted(paths['ttm'].glob('ku=*/*.parquet')):
            x = pq.read_table(pth, columns=['o_grid', 'd_grid', 't_sec']).to_pandas()
            o = x.o_grid.map(code).to_numpy(int); d = x.d_grid.map(code).to_numpy(int)
            sel = (x.t_sec.to_numpy() <= 900) & (D['pop'][o] > 0) & (mask[d] > 0); o = mapper[o[sel]]; d = d[sel]
            if not len(o):
                continue
            ids, inv = np.unique(o.astype(np.int64) * 424 + D['gd'][d], return_inverse=True); vals = np.zeros((len(ids), 7), np.uint8)
            for j in range(7):
                np.maximum.at(vals[:, j], inv, ((mask[d] >> j) & 1).astype(np.uint8))
            es.append((ids, vals))
        ids = np.concatenate([e[0] for e in es]); vals = np.concatenate([e[1] for e in es]); keys, inv = np.unique(ids, return_inverse=True)
        em = np.zeros((len(keys), 7), np.uint8)
        for j in range(7):
            np.maximum.at(em[:, j], inv, vals[:, j])
        self.eo = keys // 424; self.ed = keys % 424; self.em = em; self.gd = ev.gd; self.n = ev.n; self.p = ev.p
        self.rn = self.matrix(None) > 0; self.x0 = (self.rn & ~(self.matrix(D['LZ']) > 0)).any(1)
        self.n_cells_by_category = {c: int(((mask >> j) & 1).sum()) for j, c in enumerate(S.CATS)}; self.n_records = int(len(f))

    def matrix(self, lab):
        mat = np.zeros((self.n, 7), np.uint8); ok = np.ones(len(self.eo), bool) if lab is None else lab[self.gd[self.eo]] == lab[self.ed]
        for j in range(7):
            np.maximum.at(mat[:, j], self.eo[ok], self.em[ok, j])
        return mat


def paths_like_a01(D):
    """a01.main과 같은 코드·같은 시드로 통행 기준 경로와 무작위 100경로의 상태(라벨, 옮긴 동)를 만든다."""
    z = D['z']; name2id = dict(zip(z.life_zone_name, z.life_zone_id)); di = {int(d): i for i, d in enumerate(z.Dong)}
    LZ = D['LZ']; ku = D['ku']; G = D['G']; nD = D['nD']
    mv, _ = A1.flow_moves(D)
    queues = {k: list(g.itertuples()) for k, g in mv.sort_values(['ku_name', 'step']).groupby('ku_name')}; seqQ = []
    while any(queues.values()):
        k = max((k for k in queues if queues[k]), key=lambda k: queues[k][0].dQ); r = queues[k].pop(0); seqQ.append((di[int(r.dong)], name2id[r.to_zone]))

    def valid(lab, v, zt):
        rest = np.flatnonzero(lab == lab[v]); rest = rest[rest != v]
        return len(rest) > 0 and nx.is_connected(G.subgraph(rest.tolist())) and zt != lab[v]

    def states(seq):
        lab = LZ.copy(); moved = np.zeros(nD, bool); res = {0: (lab.copy(), moved.copy())}
        for i, (v, zt) in enumerate(seq, 1):
            lab[v] = zt; moved[v] = True; res[i] = (lab.copy(), moved.copy())
        return res

    rng = np.random.default_rng(20260930 + D['year']); ku_seq = [ku[v] for v, _ in seqQ]

    def rand_seq():
        lab = LZ.copy(); moved = np.zeros(nD, bool); seq = []
        for k in ku_seq:
            nodes = np.flatnonzero((ku == k) & ~moved)
            for _ in range(300 if len(nodes) else 0):
                v = nodes[rng.integers(len(nodes))]; zs = sorted({lab[u] for u in G[v] if lab[u] != lab[v]})
                if not zs:
                    continue
                zt = zs[rng.integers(len(zs))]
                if valid(lab, v, zt):
                    lab[v] = zt; moved[v] = True; seq.append((v, zt)); break
            else:
                seq.append(seq[-1] if seq else None)
        return [s for s in seq if s is not None]

    PL = {('FLOW', kk, -1): v for kk, v in states(seqQ).items()}
    for r in range(NREP):
        for kk, v in states(rand_seq()).items():
            PL[('RAND', kk, r)] = v
    return PL, len(seqQ)


def path_summary(SR, col, K):
    fl = SR[SR.strategy == 'FLOW'].set_index('k')[col]; rd = SR[SR.strategy == 'RAND']; end = rd[rd.k == K][col]
    below = [k for k in range(1, K + 1) if (rd[rd.k == k][col] > fl[k]).all()]
    first = next((k for k in range(1, K + 1) if all(j in below for j in range(k, K + 1))), None)
    return {'flow_end': float(fl[K]), 'flow_min': float(fl.min()), 'flow_argmin_k': int(fl.idxmin()), 'first_k_flow_below_all_random': first,
            'rand_end_median': float(end.median()), 'rand_end_p2.5': float(end.quantile(.025)), 'rand_end_p97.5': float(end.quantile(.975)),
            'rand_end_share_above_0': float((end > 0).mean()), 'rand_end_share_below_flow': float((end < fl[K]).mean())}


def main(year):
    out = AG / 'results' / str(year); cache = AG / 'results' / '_cache' / str(year); cache.mkdir(parents=True, exist_ok=True)
    paths = S.input_paths(ROOT, year); D = S.load(ROOT, year, paths); ev = S.Accessibility(D, paths, cache); evC = ReachNoC(D, paths, ev)
    PL, K = paths_like_a01(D)
    xc0 = ev.rn & ~(ev.base > 0); L0 = float(ev.p[ev.x0].sum()); x5_0 = xc0[:, FIVE].any(1); L5_0 = float(ev.p[x5_0].sum()); LC_0 = float(evC.p[evC.x0].sum())
    rows = []; cat_end = {}
    for (s, kk, r), (lab, moved) in PL.items():
        mat = ev.matrix(lab); xc = ev.rn & ~(mat > 0); x = xc.any(1); matC = evC.matrix(lab); xC = (evC.rn & ~(matC > 0)).any(1)
        rows.append({'strategy': s, 'k': kk, 'rep': r, 'dL_all7': float(ev.p[x].sum()) - L0, 'dL_five': float(ev.p[xc[:, FIVE].any(1)].sum()) - L5_0, 'dL_noC': float(evC.p[xC].sum()) - LC_0})
        if kk == K:
            cat_end[(s, r)] = [float(ev.p[xc[:, j]].sum() - ev.p[xc0[:, j]].sum()) for j in range(7)]
    SR = pd.DataFrame(rows)
    saved = pd.read_csv(out / 'a01_states.csv'); m = saved.merge(SR, on=['strategy', 'k', 'rep'])
    assert len(m) == len(saved) == len(SR) and np.allclose(m.dL, m.dL_all7, rtol=0, atol=1e-6), 'a01 재현 실패'
    SR.to_csv(out / 'a10_states_subsets.csv', index=False, encoding='utf-8-sig', float_format='%.12g')
    flow_cat = cat_end[('FLOW', -1)]; rand_cat = np.median(np.array([v for (s, r), v in cat_end.items() if s == 'RAND']), 0)
    res = {'year': year, 'reproduces_a01_states': True, 'n_states': len(SR), 'K': K,
           'official_L': {'all7': L0, 'five': L5_0, 'noC': LC_0},
           'official_excluded_by_category': {c: float(ev.p[xc0[:, j]].sum()) for j, c in enumerate(S.CATS)},
           'flow_end_minus_official_by_category': dict(zip(S.CATS, flow_cat)), 'random_end_minus_official_median_by_category': dict(zip(S.CATS, map(float, rand_cat))),
           'paths': {nm: path_summary(SR, f'dL_{nm}', K) for nm in ('all7', 'five', 'noC')},
           'noC_facility': {'excluded_types': C_TYPES, 'records_kept': evC.n_records, 'cells_by_category': evC.n_cells_by_category}}
    # Q2: 대안 지도 1000장
    ens = {'five': [], 'noC': []}; offi = {}
    for sd in SEEDS[year]:
        Lb = np.load(out / f'a02_ensemble_{sd}_labels.npz'); assert np.array_equal(Lb['dongs'], D['dongs'])
        for key in ['LZ'] + [f'E{i:03d}' for i in range(500)]:
            lab = Lb[key].astype(np.int64); mat = ev.matrix(lab); v5 = float(ev.p[(ev.rn[:, FIVE] & ~(mat[:, FIVE] > 0)).any(1)].sum())
            vC = float(evC.p[(evC.rn & ~(evC.matrix(lab) > 0)).any(1)].sum())
            if key == 'LZ':
                offi = {'five': v5, 'noC': vC}
            else:
                ens['five'].append(v5); ens['noC'].append(vC)
    res['ensemble'] = {nm: {'official': offi[nm], 'n_maps': len(v), 'n_greater': int((np.array(v) > offi[nm] + .5).sum()), 'median_minus_official': float(np.median(v) - offi[nm])} for nm, v in ens.items()}
    (out / 'a10_sensitivity.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('official_L', 'paths', 'ensemble', 'flow_end_minus_official_by_category')}, ensure_ascii=False, default=float))


if __name__ == '__main__':
    main(int(sys.argv[1]))
