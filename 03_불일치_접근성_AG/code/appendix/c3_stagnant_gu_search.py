# -*- coding: utf-8 -*-
"""부록 'Chain diagnostics'와 3.3절 끝 문장(네 구는 유효 분할 1~8개, 사슬이 하나 빼고 모두 방문)의 원 산출을 다시 만든다.
원 코드: 보관 `explore/v3/e13b_stagnant_gu_search.py`(2026-09-28)와 `common_v3.py`·`config_v3_run2A.json`. 결과 지표(누락·접근성·IFR)는 보지 않는다.
옛 모듈 대신 a02_ensemble.py(같은 생성 규칙: 인접표 공유 길이 PP, 정렬 인구 ±20%, 구 평균 PP ≥ 0.95×공식)의 Cons·pp_csv·comp_key를 쓴다.
설정은 원 config 그대로: 경보(저장 고유 상태 < 10 또는 공식과 다른 비율 < 0.5)가 난 구만, 동 18개 이하면 완전 열거(시간 상한 900초, 개수 상한 100만).
실행: python code/appendix/c3_stagnant_gu_search.py 2025 20261101   (2025: 20261101·20261102, 2020: 20261201·20261202)
출력: results/_cache/appendix_regen/e13b_{연도}_SIZE20_{시드}_stagnant_search.csv (seconds 열은 실행 시간이라 대조에서 뺀다)
"""
import sys
import time
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; AG = HERE.parents[1]; ROOT = AG.parent; RES = AG / 'results'
sys.path.insert(0, str(AG / 'code')); import study as S  # noqa: E402
from a02_ensemble import Cons, SIZE_TOL, pp_csv  # noqa: E402

CFG = {'exhaustive_max_dong': 18, 'exhaustive_time_cap_s': 900, 'exhaustive_count_cap': 1000000, 'alarm_unique_lt': 10, 'alarm_differs_lt': 0.5}


def enumerate_partitions(D, cons, Scsv, k, nodes, t_cap, n_cap):
    G = D['G'].subgraph(nodes); nz = cons.nz[k]; ref = cons.ref[k]; popd = D['popd']
    lo_any, hi_any = (1 - SIZE_TOL) * ref.min(), (1 + SIZE_TOL) * ref.max()

    def ok_pop(p):
        return any((1 - SIZE_TOL) * r <= p <= (1 + SIZE_TOL) * r for r in ref)
    t0 = time.time(); found = []; state = {'timeout': False, 'n': 0}

    def subsets(R, r):
        out = []

        def ext(Sset, frontier, excl, pop):
            if time.time() - t0 > t_cap:
                state['timeout'] = True; return
            if pop >= lo_any:
                out.append(frozenset(Sset))
            frontier = list(frontier)
            for i, v in enumerate(frontier):
                np_ = pop + popd[v]
                if np_ > hi_any:
                    continue
                newf = set(frontier[i + 1:]) | {u for u in G[v] if u in R and u not in Sset and u not in excl and u not in frontier[:i + 1]}
                ext(Sset | {v}, newf, excl | set(frontier[:i]), np_)
        ext({r}, {u for u in G[r] if u in R}, set(), popd[r])
        return out

    def rec(R, parts):
        if state['timeout'] or state['n'] >= n_cap:
            return
        if len(parts) == nz - 1:
            if nx.is_connected(G.subgraph(R)) and ok_pop(popd[list(R)].sum()):
                allp = parts + [frozenset(R)]
                if cons.pops_ok(k, [popd[list(p)].sum() for p in allp]) and cons.pp_ok(k, [pp_csv(D, Scsv, sorted(p)) for p in allp]):
                    found.append(tuple(sorted(tuple(sorted(p)) for p in allp))); state['n'] += 1
            return
        r = min(R)
        for Sset in subsets(R, r):
            if not ok_pop(popd[list(Sset)].sum()) or len(Sset) == len(R):
                continue
            rest = R - Sset
            if all(ok_pop(popd[list(c)].sum()) or len(c) > 1 for c in nx.connected_components(G.subgraph(rest))):
                rec(rest, parts + [Sset])
    rec(frozenset(nodes.tolist()), [])
    return len(set(found)), state['timeout'], time.time() - t0


def main(year, seed):
    paths = S.input_paths(ROOT, year); D = S.load(ROOT, year, paths)
    adj = pd.read_csv(paths['adjacency']); Scsv = np.zeros((424, 424))
    for a, b, l in zip(adj.i, adj.j, adj.shared_len_m):
        i, j = D['di'][a], D['di'][b]
        if D['ku'][i] == D['ku'][j]:
            Scsv[i, j] += l
    cons = Cons(D, Scsv)
    dg = pd.read_csv(RES / str(year) / f'a02_ensemble_{seed}_chain_diag.csv')
    tgt = dg[(dg.saved_unique_states < CFG['alarm_unique_lt']) | (dg.saved_share_differs_from_LZ < CFG['alarm_differs_lt'])]; rows = []
    for r in tgt.itertuples():
        nodes = np.flatnonzero(D['ku'] == r.ku)
        assert len(nodes) <= CFG['exhaustive_max_dong'], '원 산출의 네 구는 모두 완전 열거 대상'
        n, to, sec = enumerate_partitions(D, cons, Scsv, r.ku, nodes, CFG['exhaustive_time_cap_s'], CFG['exhaustive_count_cap'])
        rows.append({'ku': r.ku, 'ku_name': r.ku_name, 'n_dong': len(nodes), 'method': 'exhaustive', 'legal_partitions_found(incl LZ)': n, 'timeout': to, 'seconds': round(sec, 1),
                     'chain_saved_unique': r.saved_unique_states, 'verdict': ('구조적으로 LZ만 합법' if (n == 1 and not to) else ('비자명 대안 존재 → 사슬 탐색 부족' if n > r.saved_unique_states else ('탐색 미완(시간 상한)' if to else '사슬이 열거된 상태를 모두 방문')))})
    out = RES / '_cache' / 'appendix_regen'; out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / f'e13b_{year}_SIZE20_{seed}_stagnant_search.csv', index=False, encoding='utf-8-sig'); print(pd.DataFrame(rows).to_string(index=False))


if __name__ == '__main__':
    main(int(sys.argv[1]), int(sys.argv[2]))
