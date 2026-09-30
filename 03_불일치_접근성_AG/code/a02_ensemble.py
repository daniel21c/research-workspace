# -*- coding: utf-8 -*-
"""결과 3 표본 생성: 공식 생활권과 크기·모양을 맞춘 대안 생활권 지도(ReCom 앙상블; DeFord et al., 2021).

구마다 따로 사슬을 돌린다(생활권은 구를 넘지 않음). 한 번의 제안:
 인접한 두 생활권을 합침 → 합친 영역의 균등 신장트리 → 끊었을 때 제약을 만족하는 간선 중 하나를 균등 선택해 다시 둘로 나눔.
제약(SIZE20, 제안마다 그 구 전체 검사): 생활권 수 = 공식, 구 안, 연속, 비공집합,
 구별 정렬 생활권 인구가 공식의 같은 순위 인구와 ±20% 이내, 구 평균 Polsby–Popper ≥ 0.95 × 공식 구 평균.
Metropolis 보정은 하지 않는다(균등 표본이 아님). 버림 500, 간격 20 제안, 사슬당 500 표본, 연도별 두 사슬.
PP의 공유 경계 길이는 인접표의 shared_len_m을 쓴다(생성 당시 규칙). 저장 표본은 study.py의 기하 기반 제약으로도 다시 검사한다.
이 파일은 2026-09-28 생성 코드(explore/v3/e13_matched_ensemble.py + common_v3.py)를 입력 적재만 study.load로 바꿔 옮긴 것이다. 같은 시드면 같은 표본이 나와야 한다.
실행: python code/a02_ensemble.py 2025 20261101   (2025: 20261101·20261102, 2020: 20261201·20261202)
출력: results/{연도}/a02_ensemble_{시드}_labels.npz, a02_ensemble_{시드}_chain_diag.csv
"""
import json
import sys
import time
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; AG = HERE.parent; ROOT = AG.parent
sys.path.insert(0, str(HERE)); import study as S  # noqa: E402
SEEDS = {2025: (20261101, 20261102), 2020: (20261201, 20261202)}
BURN, THIN, N, SIZE_TOL, PP_FACTOR = 500, 20, 500, 0.20, 0.95


def comp_key(lab, nodes):
    g = {}
    for i in nodes:
        g.setdefault(lab[i], []).append(int(i))
    return tuple(sorted(tuple(v) for v in g.values()))


def pp_csv(D, Scsv, members):
    s = np.asarray(members); A = D['area'][s].sum(); P = D['per'][s].sum() - Scsv[np.ix_(s, s)].sum(); return 4 * np.pi * A / P ** 2


class Cons:
    def __init__(self, D, Scsv):
        self.D, self.S = D, Scsv; self.ref, self.thr, self.nz = {}, {}, {}
        for k in D['kus']:
            nodes = np.flatnonzero(D['ku'] == k); zs = np.unique(D['LZ'][nodes])
            self.ref[k] = np.sort([D['popd'][nodes][D['LZ'][nodes] == c].sum() for c in zs]); self.nz[k] = len(zs)
            self.thr[k] = PP_FACTOR * float(np.mean([pp_csv(D, Scsv, nodes[D['LZ'][nodes] == c]) for c in zs]))

    def pops_ok(self, k, pops):
        pops = np.sort(np.asarray(pops, float))
        return len(pops) == self.nz[k] and not np.any(pops <= 0) and bool(np.all(np.abs(pops / self.ref[k] - 1) <= SIZE_TOL))

    def pp_ok(self, k, v):
        return float(np.mean(v)) >= self.thr[k]

    def check_gu(self, lab, k):
        D = self.D; nodes = np.flatnonzero(D['ku'] == k); zs = np.unique(lab[nodes])
        return {'n_zone': len(zs) == self.nz[k], 'inside_gu': all(set(np.flatnonzero(lab == c)) <= set(nodes) for c in zs),
                'connected': all(nx.is_connected(D['G'].subgraph(list(nodes[lab[nodes] == c]))) for c in zs),
                'pop': self.pops_ok(k, [D['popd'][nodes][lab[nodes] == c].sum() for c in zs]), 'pp': self.pp_ok(k, [pp_csv(D, self.S, nodes[lab[nodes] == c]) for c in zs])}


def main(year, seed):
    assert seed in SEEDS[year]
    out = AG / 'results' / str(year); out.mkdir(parents=True, exist_ok=True); t0 = time.time(); rng = np.random.default_rng(seed)
    paths = S.input_paths(ROOT, year); D = S.load(ROOT, year, paths)
    adj = pd.read_csv(paths['adjacency']); Scsv = np.zeros((424, 424))
    for a, b, l in zip(adj.i, adj.j, adj.shared_len_m):
        i, j = D['di'][a], D['di'][b]
        if D['ku'][i] == D['ku'][j]:
            Scsv[i, j] += l
    cons = Cons(D, Scsv); G, popd = D['G'], D['popd']
    assert all(all(cons.check_gu(D['LZ'], k).values()) for k in D['kus'])
    plans = np.zeros((N, D['nD']), np.int64); diag = []
    for k in D['kus']:
        nodes = np.flatnonzero(D['ku'] == k); lab = D['LZ'].copy(); key_prev = comp_key(lab, nodes)
        cnt = dict(rej_disconnected=0, rej_no_candidate=0, rej_no_cut=0, acc_changed=0, acc_same=0, acc_relabel=0); runs = []; run = 0; saved = []
        for s in range(1, BURN + THIN * N + 1):
            H = G.subgraph(nodes); cut = [(a, b) for a, b in H.edges() if lab[a] != lab[b]]
            if not cut:
                cnt['rej_no_cut'] += 1; run += 1
            else:
                a, b = cut[rng.integers(len(cut))]; za, zb = lab[a], lab[b]
                merged = [n for n in nodes if lab[n] in (za, zb)]; Hm = G.subgraph(merged)
                if not nx.is_connected(Hm):
                    cnt['rej_disconnected'] += 1; run += 1
                else:
                    T = nx.random_spanning_tree(Hm, seed=int(rng.integers(1 << 31))); tot = popd[merged].sum()
                    oc = [c for c in np.unique(lab[nodes]) if c not in (za, zb)]; opop = [popd[nodes][lab[nodes] == c].sum() for c in oc]; opp = [pp_csv(D, Scsv, nodes[lab[nodes] == c]) for c in oc]
                    cands = []
                    for e in T.edges():
                        T.remove_edge(*e); comp = nx.node_connected_component(T, e[0]); T.add_edge(*e)
                        c1 = sorted(comp); c2 = [n for n in merged if n not in comp]; p1 = popd[c1].sum()
                        if cons.pops_ok(k, opop + [p1, tot - p1]) and cons.pp_ok(k, opp + [pp_csv(D, Scsv, c1), pp_csv(D, Scsv, c2)]):
                            cands.append(c1)
                    if not cands:
                        cnt['rej_no_candidate'] += 1; run += 1
                    else:
                        cs = set(cands[rng.integers(len(cands))]); old = lab.copy()
                        for n in merged:
                            lab[n] = za if n in cs else zb
                        key_new = comp_key(lab, nodes)
                        if key_new != key_prev:
                            cnt['acc_changed'] += 1; runs.append(run); run = 0; key_prev = key_new
                        elif np.array_equal(old[nodes], lab[nodes]):
                            cnt['acc_same'] += 1; run += 1
                        else:
                            cnt['acc_relabel'] += 1; run += 1
            if s > BURN and (s - BURN) % THIN == 0:
                chk = cons.check_gu(lab, k)
                if not all(chk.values()):
                    raise RuntimeError(f'제약 위반: 구 {k}, 제안 {s}, {chk}')
                plans[(s - BURN) // THIN - 1, nodes] = lab[nodes]; saved.append(comp_key(lab, nodes))
        runs.append(run); lzk = comp_key(D['LZ'], nodes); P = BURN + THIN * N
        diag.append({'ku': int(k), 'ku_name': D['z'].loc[D['z'].Ku == k, 'ku_name'].iloc[0], 'n_dong': len(nodes), 'n_zone': cons.nz[k], 'proposals': P,
                     **{f'{kk}_rate': v / P for kk, v in cnt.items()}, 'accept_rate': (cnt['acc_changed'] + cnt['acc_same'] + cnt['acc_relabel']) / P,
                     'stagnation_max': int(max(runs)), 'saved_unique_states': len(set(saved)), 'saved_share_differs_from_LZ': float(np.mean([x != lzk for x in saved]))})
    pd.DataFrame(diag).to_csv(out / f'a02_ensemble_{seed}_chain_diag.csv', index=False, encoding='utf-8-sig')
    np.savez_compressed(out / f'a02_ensemble_{seed}_labels.npz', LZ=D['LZ'], dongs=D['dongs'], **{f'E{i:03d}': plans[i] for i in range(N)})
    print(json.dumps({'year': year, 'seed': seed, 'seconds': round(time.time() - t0), 'unique_city_plans': len({tuple(p) for p in plans})}))


if __name__ == '__main__':
    main(int(sys.argv[1]), int(sys.argv[2]))
