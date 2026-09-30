# -*- coding: utf-8 -*-
"""결과 1·2: 경계 동을 통행 기준(모듈성)으로 재배정한 경로와 무작위 재배정 100경로의 경계 내 시설 누락 비교.

재배정 규칙(두 경로 공통): 같은 구 안, Queen 인접한 다른 생활권으로 한 동을 옮김, 원 생활권은 비지 않고 연속, 생활권 수 유지.
 - 통행 기준: 구마다 무방향 통행망 w_ij = f_ij + f_ji, 자기 고리 f_ii, 해상도 1 모듈성 Q. 매 단계 ΔQ 최대 이동 하나, 최대 ΔQ ≤ 1e-15이면 그 구 종료.
   같은 동의 재이동 허용. 구별 경로를 남은 첫 이동의 ΔQ가 큰 구부터 꺼내 도시 경로로 합침.
 - 무작위: 통행 기준 도시 경로의 구 순서를 그대로 따르며, 그 구에서 아직 옮기지 않은 동 하나와 인접한 다른 생활권 하나를 균등 추출(최대 300회 시도).
   시드 default_rng(20260930 + 연도), 100경로.
평가: study.Accessibility(7범주 27유형, 100 m 격자, 15분 보행). L = 무경계로는 닿지만 자기 생활권 안에서는 닿지 않는 범주가 하나라도 있는 주민 수.
실행: python code/a01_flow_random.py 2025   (2020도 같음)
출력: results/{연도}/a01_flow_moves.csv, a01_states.csv, a01_summary.json
"""
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; AG = HERE.parent; ROOT = AG.parent
sys.path.insert(0, str(HERE)); import study as S  # noqa: E402
NREP = 100; TOL = 1e-15


def modularity(Wk, lab):
    deg = Wk.sum(1) + np.diag(Wk); m = (Wk.sum() + np.trace(Wk)) / 2; Q = 0.0
    for c in np.unique(lab):
        s = lab == c; L = (Wk[np.ix_(s, s)].sum() + np.trace(Wk[np.ix_(s, s)])) / 2; Q += L / m - (deg[s].sum() / (2 * m)) ** 2
    return Q


def flow_moves(D):
    """구별 모듈성 탐욕 재배정. 반환: 이동 표(구, 단계, 동, 출발·도착 생활권, ΔQ)와 구별 Q 검산."""
    z = D['z']; LZ = D['LZ']; ku = D['ku']; G = D['G']; F = D['F']; dongs = D['dongs']
    id2name = dict(zip(z.life_zone_id, z.life_zone_name)); kuname = dict(zip(z.Dong, z.ku_name)); rows, chk = [], []
    for k in np.unique(ku):
        nodes = np.flatnonzero(ku == k); pos = {n: i for i, n in enumerate(nodes)}
        Fk = F[np.ix_(nodes, nodes)]; Wk = Fk + Fk.T; np.fill_diagonal(Wk, np.diag(Fk))
        deg = Wk.sum(1) + np.diag(Wk); m = (Wk.sum() + np.trace(Wk)) / 2
        lab = LZ[nodes].copy(); Q0 = modularity(Wk, lab); step = 0; gsum = 0.0
        while True:
            dsum = {c: deg[lab == c].sum() for c in np.unique(lab)}; best = (0.0, None)
            for v in range(len(nodes)):
                a = lab[v]; nb = {lab[pos[u]] for u in G[nodes[v]] if lab[pos[u]] != a}
                if not nb:
                    continue
                kva = Wk[v, lab == a].sum() - Wk[v, v]
                for b in nb:
                    kvb = Wk[v, lab == b].sum()
                    dq = (kvb - kva) / m - ((dsum[a] - deg[v]) ** 2 + (dsum[b] + deg[v]) ** 2 - dsum[a] ** 2 - dsum[b] ** 2) / (4 * m * m)
                    if dq > best[0] + TOL:
                        rest = [nodes[u] for u in np.flatnonzero(lab == a) if u != v]
                        if rest and nx.is_connected(G.subgraph(rest)):
                            best = (dq, (v, a, b))
            if best[1] is None:
                break
            v, a, b = best[1]; lab[v] = b; step += 1; gsum += best[0]
            rows.append({'ku_name': kuname[dongs[nodes[v]]], 'step': step, 'dong': int(dongs[nodes[v]]), 'from_zone': id2name[a], 'to_zone': id2name[b], 'dQ': best[0]})
        Q1 = modularity(Wk, lab); nxQ = nx.community.modularity(nx.from_numpy_array(Wk), [set(np.flatnonzero(lab == c)) for c in np.unique(lab)], weight='weight')
        chk.append({'ku': int(k), 'Q0': Q0, 'Q1': Q1, 'sum_dQ': gsum, 'nx_Q1': float(nxQ)})
    return pd.DataFrame(rows), pd.DataFrame(chk)


def main(year):
    out = AG / 'results' / str(year); out.mkdir(parents=True, exist_ok=True); cache = AG / 'results' / '_cache' / str(year); cache.mkdir(parents=True, exist_ok=True)
    paths = S.input_paths(ROOT, year); D = S.load(ROOT, year, paths); ev = S.Accessibility(D, paths, cache)
    z = D['z']; name2id = dict(zip(z.life_zone_name, z.life_zone_id)); di = {int(d): i for i, d in enumerate(z.Dong)}
    LZ = D['LZ']; ku = D['ku']; G = D['G']; nD = D['nD']
    mv, chk = flow_moves(D); mv.to_csv(out / 'a01_flow_moves.csv', index=False, encoding='utf-8-sig')
    queues = {k: list(g.itertuples()) for k, g in mv.sort_values(['ku_name', 'step']).groupby('ku_name')}; seqQ = []
    while any(queues.values()):
        k = max((k for k in queues if queues[k]), key=lambda k: queues[k][0].dQ); r = queues[k].pop(0); seqQ.append((di[int(r.dong)], name2id[r.to_zone]))
    NMOVE = len(seqQ)

    def valid(lab, v, zt):
        rest = np.flatnonzero(lab == lab[v]); rest = rest[rest != v]
        return len(rest) > 0 and nx.is_connected(G.subgraph(rest.tolist())) and zt != lab[v]

    def states(seq):
        lab = LZ.copy(); moved = np.zeros(nD, bool); res = {0: (lab.copy(), moved.copy())}
        for i, (v, zt) in enumerate(seq, 1):
            lab[v] = zt; moved[v] = True; res[i] = (lab.copy(), moved.copy())
        return res

    rng = np.random.default_rng(20260930 + year); ku_seq = [ku[v] for v, _ in seqQ]

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
    L0 = float(ev.p[ev.x0].sum()); rows = []
    for (s, kk, r), (lab, moved) in PL.items():
        mat = ev.matrix(lab); x = (ev.rn & ~(mat > 0)).any(1); new = x & ~ev.x0; res = ~x & ev.x0; met = ev.metrics(mat)
        rows.append({'strategy': s, 'k': kk, 'rep': r, 'L': float(ev.p[x].sum()), 'dL': float(ev.p[x].sum()) - L0, 'new': float(ev.p[new].sum()), 'resolved': float(ev.p[res].sum()),
                     'IFR': S.ifr(D, lab), 'COV15': met['COV15'], 'MAI15': met['MAI15'], 'n_moved': int(moved.sum()), 'moved_pop': float(D['popd'][moved].sum())})
    R = pd.DataFrame(rows); R.to_csv(out / 'a01_states.csv', index=False, encoding='utf-8-sig', float_format='%.12g')
    assert np.allclose(R.new - R.resolved, R.dL), 'N - R = ΔL 항등식 위반'
    curve = []
    for kk in range(1, NMOVE + 1):
        rd = R[(R.strategy == 'RAND') & (R.k == kk)]; f = R[(R.strategy == 'FLOW') & (R.k == kk)].iloc[0]
        curve.append({'k': kk, 'flow_dL': f.dL, 'flow_new': f.new, 'flow_resolved': f.resolved, 'flow_IFR': f.IFR, 'rand_n': int(len(rd)), 'rand_median': float(rd.dL.median()),
                      'rand_p2.5': float(rd.dL.quantile(.025)), 'rand_p97.5': float(rd.dL.quantile(.975)), 'rand_min': float(rd.dL.min()), 'rand_IFR_median': float(rd.IFR.median()),
                      'share_rand_below_flow': float((rd.dL < f.dL).mean())})
    C = pd.DataFrame(curve); allbelow = C[C.share_rand_below_flow == 0].k
    first_k_all = int(next(k for k in C.k if (C[C.k >= k].share_rand_below_flow == 0).all()))
    summ = {'year': year, 'population': float(ev.p.sum()), 'L_LZ': L0, 'L_LZ_share': L0 / float(ev.p.sum()), 'IFR_LZ': S.ifr(D, LZ), 'n_flow_moves': NMOVE,
            'n_flow_moved_dongs': int(PL[('FLOW', NMOVE, -1)][1].sum()), 'n_gu_with_moves': int(mv.ku_name.nunique()),
            'first_k_from_which_flow_below_all_random': first_k_all, 'k_where_flow_below_all_random': allbelow.tolist(),
            'end': C.iloc[-1].to_dict(), 'curve': curve,
            'check_Q': {'max_abs(Q1-Q0-sum_dQ)': float((chk.Q1 - chk.Q0 - chk.sum_dQ).abs().max()), 'max_abs(Q1-networkx)': float((chk.Q1 - chk.nx_Q1).abs().max())},
            'category_omission_LZ': {c: float(ev.p[ev.rn[:, j] & ~(ev.base[:, j] > 0)].sum()) for j, c in enumerate(S.CATS)},
            'no_boundary_reach_share': {c: float(ev.p[ev.rn[:, j]].sum() / ev.p.sum()) for j, c in enumerate(S.CATS)},
            'facility_info': {k: (v if not isinstance(v, (np.integer, np.floating)) else v.item()) for k, v in ev.info.items()}}
    (out / 'a01_summary.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps({k: v for k, v in summ.items() if k != 'curve'}, ensure_ascii=False, default=float))


if __name__ == '__main__':
    main(int(sys.argv[1]))
