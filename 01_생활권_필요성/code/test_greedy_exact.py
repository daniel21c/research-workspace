# -*- coding: utf-8 -*-
"""greedy_free 정확성 시험 (2026-10-02, 검토 F02).
(1) 검토자의 가상 반례: 범주 2, 유형별 1개, 격자 6(인구 10·2·3·0·0·0), 후보 3·4·5. 예전 지연 갱신은 목적 5.625(완결 1/3), 정확 탐욕은 13.125(완결 13/15).
(2) 무작위 소형 사례 200개: 증분 재계산 greedy_free 와 매 단계 전체 후보 재계산(참조 구현)의 선택 순서·목적값 일치.
사용: python test_greedy_exact.py"""
import numpy as np, heapq
from bundlelib import State, greedy_free

class Toy:
    """Ctx 와 같은 인터페이스의 가상 자료. covers[j] = 후보 j 가 닿는 출발 격자."""
    def __init__(self, pop, R0, covers, subs, P=4.0):
        self.pop = np.asarray(pop, float); self.popped = self.pop > 0; self.n = len(self.pop); self.P = P
        self.R0 = np.asarray(R0, bool); self.NC = self.R0.shape[0]
        self.covers = {int(j): np.asarray(v, int) for j, v in covers.items()}
        self.SUB = {s: (k, K, np.array(sorted(cs))) for s, (k, K, cs) in subs.items()}
        self.candALL = np.unique(np.concatenate([v[2] for v in self.SUB.values()])); self.candset = {s: set(v[2].tolist()) for s, v in self.SUB.items()}
        self.candpos = -np.ones(self.n, int); self.candpos[self.candALL] = np.arange(len(self.candALL))
        self.cnt0 = self.R0.sum(0)
    def f(self, c): return (c / self.NC) ** self.P
    def cover(self, j): return self.covers.get(int(j), np.array([], int))
    def dests_of(self, grids):
        d = np.array(sorted({j for j, v in self.covers.items() if np.isin(v, grids).any()}), int); return d[self.candpos[d] >= 0] if len(d) else d

def greedy_lazy_old(st):
    """예전 구현(지연 갱신 heap, 25회마다 재계산) — 대조용."""
    c = st.c; heap = [(-st.gain(j, S), int(j)) for j in c.candALL for S in [st.center_set(j)] if S]; heapq.heapify(heap); moves = 0
    while heap and any(st.B[s] > 0 for s in c.SUB):
        _, j = heapq.heappop(heap); S = st.center_set(j)
        if not S: continue
        g = st.gain(j, S)
        if heap and g < -heap[0][0] - 1e-9: heapq.heappush(heap, (-g, j)); continue
        if g <= 0: break
        st.apply(j, S); moves += 1
        if moves % 25 == 0: heap = [(-st.gain(jj, SS), int(jj)) for jj in c.candALL for SS in [st.center_set(jj)] if SS]; heapq.heapify(heap)
    return st

def greedy_full_rescore(st):
    """참조 구현: 매 단계 모든 후보의 한계이득을 다시 계산. 동률은 후보 번호가 작은 쪽(np.argmax 와 같은 규칙)."""
    c = st.c
    while any(st.B[s] > 0 for s in c.SUB):
        best, bg, bS = None, 0.0, None
        for j in c.candALL:
            S = st.center_set(j)
            if not S: continue
            g = st.gain(j, S)
            if g > bg + 1e-12: best, bg, bS = int(j), g, S
        if best is None: break
        st.apply(best, bS)
    return st

def objective(st): return float((st.c.pop * st.c.f(st.cnt)).sum())
def completion(st): c = st.c; comp = (st.cnt == c.NC) & c.popped; return (c.pop * comp).sum() / c.pop.sum()

# (1) 검토자 반례
toy = Toy(pop=[10, 2, 3, 0, 0, 0], R0=[[0, 1, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0]], covers={3: [0, 2], 4: [0], 5: [1]},
          subs={"A": (0, 1, [3]), "B": (1, 1, [4, 5])})
old = greedy_lazy_old(State(toy)); new = greedy_free(State(toy)); ref = greedy_full_rescore(State(toy))
print("반례 | 예전:", old.placed, round(objective(old), 4), round(completion(old), 4), "| 정확:", new.placed, round(objective(new), 4), round(completion(new), 4), "| 참조:", ref.placed, round(objective(ref), 4))
assert objective(old) < objective(new) - 1e-9 and abs(objective(new) - objective(ref)) < 1e-9 and new.placed == ref.placed

# (2) 무작위 사례
rng = np.random.default_rng(7); n_ok = 0; n_old_diff = 0; n_run = 0
for t in range(200):
    n = int(rng.integers(20, 60)); NC = int(rng.integers(2, 5)); pop = rng.integers(0, 20, n).astype(float); pop[rng.random(n) < 0.2] = 0
    R0 = rng.random((NC, n)) < 0.35
    cands = rng.choice(n, size=int(rng.integers(8, 20)), replace=False)
    covers = {int(j): np.unique(np.r_[j, rng.choice(n, size=int(rng.integers(1, 6)), replace=False)]) for j in cands}
    subs = {}
    for k in range(NC):
        if rng.random() < 0.75:
            cs = rng.choice(cands, size=int(rng.integers(3, len(cands) + 1)), replace=False); subs[f"s{k}"] = (k, int(rng.integers(1, 4)), cs.tolist())
    if not subs: continue
    n_run += 1; toy = Toy(pop, R0, covers, subs, P=float(rng.choice([2, 4, 8])))
    a = greedy_free(State(toy)); b = greedy_full_rescore(State(toy)); o = greedy_lazy_old(State(toy))
    same = {k: sorted(v) for k, v in a.placed.items()} == {k: sorted(v) for k, v in b.placed.items()} and abs(objective(a) - objective(b)) < 1e-9   # 동률은 순서만 다를 수 있음
    if not same: print("불일치", t, a.placed, b.placed, objective(a), objective(b))
    n_ok += same; n_old_diff += objective(o) < objective(a) - 1e-9; n_old_better = globals().get("n_old_better", 0) + (objective(o) > objective(a) + 1e-9); globals()["n_old_better"] = n_old_better
print(f"무작위 사례: 증분 = 전체 재계산 {n_ok}/{n_run} 일치; 예전 지연 갱신의 최종 목적값이 더 낮은 사례 {n_old_diff}/{n_run}, 더 높은 사례 {globals().get('n_old_better', 0)}/{n_run} (탐욕은 근사해라 단계별 최대 선택이 최종값 우위를 보장하지는 않음)")
assert n_ok == n_run
print("OK")
