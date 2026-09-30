# -*- coding: utf-8 -*-
"""실험 11: "걸어서 완결되는 하루"(묶음 접근성). 2026-09-30.
T1 묶음 완결률: 일상 기능 7범주(cat_A, 15분, 모든 시설)가 모두 닿는 인구 비율. 개별 범주 포화 vs 묶음.
T2 결손의 공간 구조: 미완결 인구가 단위(동·공식·Leiden·구)에 얼마나 뭉쳐 있는가 — 완결 지표의 단위 간 분산 비율, 하위 10% 단위에 몰린 미완결 인구 비율, 결정적 결손 범주.
T3 계획 방식 비교(공공 배치 시설 7종, 시설별 임계, 시설별 K = 실제 2020→2025 격자 순증):
   IND  시설별 독립 최적화(격자 논리, 시설 하나씩 도달 최대화)
   COL  중심 조정 배치(묶음 논리, 경계 없음): 한 격자에 부족한 시설들을 함께 놓아 "완결" 인구 증가를 최대화
   ZONE_u  단위마다 중심 하나(가장 낮은 단위부터 순환): u = 공식·Leiden·동·구·무작위116(R회)
   평가: 완결 인구 비율, 평균 완결 기능 수, 배치 전 취약(완결 수 하위 20%) 인구의 완결 비율,
         평가권역(Leiden·공식·동·구)별 완결 비율의 최저·미달(서울 완결 비율의 50% 미만) 수·FGT0·Gini.
목적함수(COL·ZONE): Σ pop·[f(c′)−f(c)], f(c)=(c/7)^4 (완결에 가까울수록 큰 보상; 완결 인구 증가를 근사). 탐욕 + 지연 갱신, 25수마다 전량 재계산(비부분모듈이므로 발견적 해).
사용: python exp11_bundle.py <task: diag|place> <연도> [무작위반복=10]"""
import sys, time, heapq
import numpy as np, pandas as pd
from r1lib import Year, OUT, md, PLACE_SETS

task = sys.argv[1]; year = sys.argv[2] if len(sys.argv) > 2 else "2020"; R = int(sys.argv[3]) if len(sys.argv) > 3 else 10
t0 = time.time(); rng = np.random.default_rng(20260930)
Yr = Year(year); pop = Yr.pop; n = len(Yr.M); popped = Yr.popped
import os
NT = 7; P_EXP = float(os.environ.get("P_EXP", "4")); ONLY_COL = os.environ.get("ONLY_COL") == "1"
def f(c): return (c / NT) ** P_EXP

def gini_w(x, w):
    o = np.argsort(x); x, w = x[o], w[o]; cw = np.cumsum(w); cx = np.cumsum(x * w)
    return 1 - 2 * np.sum(w * (cx - x * w / 2)) / (cw[-1] * cx[-1]) if cx[-1] > 0 else np.nan

def unit_stats(u, complete, tau_b):
    num = np.bincount(u, pop * complete); den = np.bincount(u, pop); v = den > 0
    s = np.divide(num, den, out=np.zeros_like(num), where=v)
    return {"최저": s[v].min(), "미달수": int((v & (s < tau_b)).sum()), "FGT0": den[v & (s < tau_b)].sum() / den[v].sum(),
            "Gini": gini_w(s[v], den[v]), "단위간분산비": (pop * (s[u] - Yr.cov(complete)) ** 2).sum() / max((pop * (complete - Yr.cov(complete)) ** 2).sum(), 1e-9)}

EVAL = {"Leiden": Yr.units["Leiden"], "공식": Yr.units["공식LZ"], "동": Yr.units["동"], "구": Yr.units["구"]}

# ─────────────────────────── T1·T2 진단 ───────────────────────────
if task == "diag":
    Yr.use_T(900)
    cats = ["교육", "문화", "보육·복지", "생활서비스", "소매", "의료", "행정·안전"]
    RA = np.zeros((NT, n), bool)
    for k, c in enumerate(cats):
        g = Yr.F[Yr.F.cat_A == c].grid100_cd.dropna().unique(); idx = Yr.gix.reindex(g).dropna().astype(int).to_numpy()
        Yr.fac["_cat"] = (np.unique(idx), 900); RA[k] = Yr.reach("_cat")
    rows = []
    for name, RM, labels in (("A7_15분_모든시설", RA, cats), ):
        cnt = RM.sum(0); comp = (cnt == NT) & popped
        row = {"year": year, "묶음": name, "인구": pop.sum()}
        for k, c in enumerate(labels): row[f"단일_{c}"] = Yr.cov(RM[k])
        row["묶음완결률"] = Yr.cov(comp); row["평균완결수"] = (pop * cnt).sum() / pop.sum()
        for m in range(NT + 1): row[f"완결{m}개_인구비율"] = pop[popped & (cnt == m)].sum() / pop.sum()
        inc = popped & ~comp
        for k, c in enumerate(labels): row[f"미완결중_{c}결손비율"] = pop[inc & ~RM[k]].sum() / max(pop[inc].sum(), 1)
        tau_b = 0.5 * Yr.cov(comp)
        for en, eu in EVAL.items():
            st = unit_stats(eu, comp, tau_b)
            for kk, vv in st.items(): row[f"{en}_{kk}"] = vv
            # 미완결 인구가 하위 10% 단위에 몰린 비율
            num = np.bincount(eu, pop * comp); den = np.bincount(eu, pop); v = den > 0; s = np.divide(num, den, out=np.zeros_like(num), where=v)
            order = np.argsort(s + (~v) * 9); k10 = max(1, int(v.sum() * 0.1)); worst = set(order[:k10].tolist())
            row[f"{en}_하위10%단위_미완결인구비율"] = pop[inc & np.isin(eu, list(worst))].sum() / max(pop[inc].sum(), 1)
        rows.append(row)
    # 공공 배치 시설 7종 묶음(시설별 임계) 기준 상태
    RP = np.zeros((NT, n), bool)
    for k, t in enumerate(PLACE_SETS):
        Yr.use_T(Yr.fac[t][1]); RP[k] = Yr.reach(t)
    Yr.use_T(900); cnt = RP.sum(0); comp = (cnt == NT) & popped
    row = {"year": year, "묶음": "P7_공공배치시설_제도임계", "인구": pop.sum(), "묶음완결률": Yr.cov(comp), "평균완결수": (pop * cnt).sum() / pop.sum()}
    for k, t in enumerate(PLACE_SETS): row[f"단일_{t}"] = Yr.cov(RP[k])
    for m in range(NT + 1): row[f"완결{m}개_인구비율"] = pop[popped & (cnt == m)].sum() / pop.sum()
    tau_b = 0.5 * Yr.cov(comp)
    for en, eu in EVAL.items():
        for kk, vv in unit_stats(eu, comp, tau_b).items(): row[f"{en}_{kk}"] = vv
    rows.append(row)
    D = pd.DataFrame(rows); D.to_csv(OUT / f"표4.1-14_묶음완결_진단_{year}.csv", index=False, encoding="utf-8-sig")
    print(D.T.to_string()); print("done", f"{time.time()-t0:.0f}s"); sys.exit()

# ─────────────────────────── T3 배치 ───────────────────────────
Y25 = Year("2025") if year == "2020" else Yr; Y20 = Year("2020") if year == "2025" else Yr
types = PLACE_SETS; T_of = {t: Yr.fac[t][1] for t in types}
E = {}
for T in sorted(set(T_of.values())):
    m = Yr._t_all <= T; o, d = Yr._o_all[m], Yr._d_all[m]
    E[T] = (o, np.searchsorted(d, np.arange(n)), np.searchsorted(d, np.arange(n), side="right"))
def cover(t, j): o, s, e = E[T_of[t]]; return o[s[j]:e[j]]
R0 = np.zeros((NT, n), bool); CAND = {}; HAS = {}; K = {}
for k, t in enumerate(types):
    Yr.use_T(T_of[t]); R0[k] = Yr.reach(t); CAND[t] = Yr.candidates(t); HAS[t] = set(Yr.fac[t][0].tolist())
    n20, n25 = len(Y20.fac[t][0]), len(Y25.fac[t][0]); kk = n25 - n20; K[t] = kk if kk >= 3 else max(3, int(round(0.1 * n20)))
Yr.use_T(900)
candALL = np.unique(np.concatenate(list(CAND.values()))); candset = {t: set(CAND[t].tolist()) for t in types}
cnt0 = R0.sum(0); comp0 = (cnt0 == NT) & popped
o = np.argsort(cnt0 + (~popped) * 99, kind="stable"); cw = np.cumsum(pop[o]); cut = cnt0[o][min(np.searchsorted(cw, 0.2 * cw[-1]), n - 1)]
POOR = (cnt0 <= cut) & popped
print(f"{year} 기준 완결률 {Yr.cov(comp0):.4f} 평균완결수 {(pop*cnt0).sum()/pop.sum():.3f} 취약(완결수≤{cut}) 인구비율 {pop[POOR].sum()/pop.sum():.3f} K={K}", flush=True)

class State:
    def __init__(self): self.R = R0.copy(); self.cnt = cnt0.copy(); self.B = dict(K); self.placed = {t: [] for t in types}
    def need(self, t, j):
        if self.B[t] <= 0 or j in HAS[t] or j not in candset[t]: return False
        idx = cover(t, j); return bool(np.any(~self.R[types.index(t), idx] & popped[idx]))
    def gain(self, j, S):
        parts = []
        for t in S:
            k = types.index(t); idx = cover(t, j); parts.append(idx[~self.R[k, idx]])
        if not parts: return 0.0
        g = np.concatenate(parts)
        if len(g) == 0: return 0.0
        u, c = np.unique(g, return_counts=True); old = self.cnt[u]; return float((pop[u] * (f(old + c) - f(old))).sum())
    def apply(self, j, S):
        for t in S:
            k = types.index(t); idx = cover(t, j); new = idx[~self.R[k, idx]]; self.R[k, new] = True; self.cnt[new] += 1
            self.B[t] -= 1; self.placed[t].append(int(j)); HAS_local[t].add(int(j))
    def center_set(self, j): return [t for t in types if self.need(t, j)]

PLACED = {}
def evaluate(st, name, rep=0):
    comp = (st.cnt == NT) & popped; tau_b = 0.5 * Yr.cov(comp)
    PLACED[f"{name}#{rep}"] = {t: list(map(int, v)) for t, v in st.placed.items()}
    row = {"year": year, "방식": name, "rep": rep, "완결률": Yr.cov(comp), "완결률_기준": Yr.cov(comp0), "평균완결수": (pop * st.cnt).sum() / pop.sum(),
           "완결6이상": pop[popped & (st.cnt >= 6)].sum() / pop.sum(), "취약20_완결률": pop[POOR & comp].sum() / pop[POOR].sum(),
           "취약20_평균완결수": (pop * st.cnt)[POOR].sum() / pop[POOR].sum(), "사용예산": sum(K[t] - st.B[t] for t in types), "중심수": len(set(sum(st.placed.values(), [])))}
    for t in types: row[f"배치_{t}"] = K[t] - st.B[t]
    allj = sum(st.placed.values(), []); uj, cj = np.unique(allj, return_counts=True)
    row["중심당_시설수_평균"] = float(cj.mean()) if len(cj) else 0.0; row["시설3종이상_중심수"] = int((cj >= 3).sum())
    for en in ("공식", "Leiden"):
        eu = EVAL[en]; z = eu[uj]; nz = np.bincount(z, minlength=eu.max() + 1); den = np.bincount(eu, pop); v = den > 0
        row[f"{en}_중심있는단위비율"] = float((nz[v] > 0).mean()); row[f"{en}_중심수Gini"] = gini_w(nz[v].astype(float), np.ones(int(v.sum())))
    for en, eu in EVAL.items():
        for kk, vv in unit_stats(eu, comp, tau_b).items(): row[f"{en}_{kk}"] = vv
    return row

def run_IND():
    st = State()
    for t in types:
        Yr.use_T(T_of[t]); pk, _, _ = Yr.place(R0[types.index(t)], None, 0, K[t], CAND[t])
        for j in pk[:K[t]]:
            st.B[t] = max(st.B[t], 1); st.apply(j, [t])
        st.B[t] = 0
    Yr.use_T(900); return st

def run_COL(zone=None, zone_order=None):
    """zone=None: 경계 없는 중심 조정. zone 주면 단위 순환(가장 낮은 단위부터, 단위마다 중심 하나씩)."""
    st = State(); moves = 0
    def best_in(cands):
        best, bg, bS = None, 0.0, None
        for j in cands:
            S = st.center_set(j)
            if not S: continue
            g = st.gain(j, S)
            if g > bg: best, bg, bS = j, g, S
        return best, bg, bS
    if zone is None:
        heap = []
        def full():
            heap.clear()
            for j in candALL:
                S = st.center_set(j)
                if S: heap.append((-st.gain(j, S), int(j)))
            heapq.heapify(heap)
        full()
        while heap and any(st.B[t] > 0 for t in types):
            negg, j = heapq.heappop(heap); S = st.center_set(j)
            if not S: continue
            g = st.gain(j, S)
            if heap and g < -heap[0][0] - 1e-9: heapq.heappush(heap, (-g, j)); continue
            if g <= 0: break
            st.apply(j, S); moves += 1
            if moves % 25 == 0: full()
        return st
    # 단위 순환
    nz = zone.max() + 1; members = {z: candALL[zone[candALL] == z] for z in range(nz)}
    stuck = set()
    while any(st.B[t] > 0 for t in types):
        progressed = False
        for z in zone_order:
            if z in stuck or len(members[z]) == 0: continue
            j, g, S = best_in(members[z])
            if j is None or g <= 0: stuck.add(z); continue
            st.apply(j, S); progressed = True; moves += 1
            if not any(st.B[t] > 0 for t in types): break
        if not progressed: break
    return st

def run_FLOOR(u, tau_c):
    """1단계: 평균 완결 수가 tau_c 미만인 단위 중 가장 낮은 단위 안에 중심을 놓아 부족분 합을 줄인다(부족분 감소 최대). 2단계: 남은 예산은 경계 없는 조정(COL)."""
    st = State(); den = np.bincount(u, pop); v = den > 0; nz = u.max() + 1
    members = {z: candALL[u[candALL] == z] for z in range(nz)}
    def mean_cnt(): return np.divide(np.bincount(u, pop * st.cnt, minlength=nz), den, out=np.full(nz, 99.0), where=v)
    def shortfall(mc): return np.maximum(0, tau_c - mc)[v].sum()
    stuck = set()
    while any(st.B[t] > 0 for t in types):
        mc = mean_cnt(); below = [z for z in np.argsort(mc) if v[z] and mc[z] < tau_c - 1e-9 and z not in stuck]
        if not below: break
        z = below[0]; best, bg, bS = None, 0.0, None
        for j in members[z]:
            S = st.center_set(j)
            if not S: continue
            # 부족분 감소 = 이 단위 평균 완결 수 증가 (단위 안 인구만)
            add = 0.0
            for t in S:
                k = types.index(t); idx = cover(t, j); new = idx[~st.R[k, idx]]; add += pop[new[u[new] == z]].sum()
            g = min(add / den[z], tau_c - mc[z])
            if g > bg: best, bg, bS = j, g, S
        if best is None: stuck.add(z); continue
        st.apply(best, bS)
    # 2단계 자유 조정
    heap = []
    for j in candALL:
        S = st.center_set(j)
        if S: heap.append((-st.gain(j, S), int(j)))
    heapq.heapify(heap); moves = 0
    while heap and any(st.B[t] > 0 for t in types):
        negg, j = heapq.heappop(heap); S = st.center_set(j)
        if not S: continue
        g = st.gain(j, S)
        if heap and g < -heap[0][0] - 1e-9: heapq.heappush(heap, (-g, j)); continue
        if g <= 0: break
        st.apply(j, S); moves += 1
        if moves % 25 == 0:
            heap = [(-st.gain(jj, st.center_set(jj)), int(jj)) for jj in candALL if st.center_set(jj)]; heapq.heapify(heap)
    return st

rows = []
HAS_local = {t: set(HAS[t]) for t in types}
st = run_IND(); rows.append(evaluate(st, "IND_시설별독립")); print("IND", f"{rows[-1]['완결률']:.4f}", f"{time.time()-t0:.0f}s", flush=True)
HAS_local = {t: set(HAS[t]) for t in types}
st = run_COL(); rows.append(evaluate(st, "COL_중심조정_무경계")); print("COL", f"{rows[-1]['완결률']:.4f}", f"{time.time()-t0:.0f}s", flush=True)
if ONLY_COL:
    D = pd.DataFrame(rows); D["P_EXP"] = P_EXP; D.to_csv(OUT / f"표4.1-15_묶음배치_민감도_{year}_p{int(P_EXP)}.csv", index=False, encoding="utf-8-sig"); print(D[["방식","완결률","취약20_완결률","평균완결수","중심수"]].round(4).to_string()); sys.exit()
def zone_order_of(u):
    num = np.bincount(u, pop * comp0); den = np.bincount(u, pop); v = den > 0
    s = np.divide(num, den, out=np.full_like(num, 9.0), where=v); mean_cnt = np.divide(np.bincount(u, pop * cnt0), den, out=np.full_like(num, 99.0), where=v)
    return list(np.lexsort((mean_cnt, s)))   # 완결률 낮은 순, 동률이면 평균 완결 수 낮은 순
for lv, tag in (("공식LZ", "공식"), ("Leiden", "Leiden"), ("동", "동"), ("구", "구")):
    HAS_local = {t: set(HAS[t]) for t in types}; u = Yr.units[lv]
    st = run_COL(u, zone_order_of(u)); rows.append(evaluate(st, f"ZONE_{tag}")); print("ZONE", tag, f"{rows[-1]['완결률']:.4f}", f"{time.time()-t0:.0f}s", flush=True)
RANDS = [Yr.dong_series_to_units(Yr.random_partition(116, rng)) for _ in range(R)]
for i, u in enumerate(RANDS):
    HAS_local = {t: set(HAS[t]) for t in types}
    st = run_COL(u, zone_order_of(u)); rows.append(evaluate(st, "ZONE_무작위116", i)); print("ZONE rand", i, f"{rows[-1]['완결률']:.4f}", f"{time.time()-t0:.0f}s", flush=True)
    pd.DataFrame(rows).to_csv(OUT / f"표4.1-15_묶음배치_{year}.csv", index=False, encoding="utf-8-sig")
# 하한형(단위 평균 완결 수 ≥ τ_c = 동 인구가중 중위 × 0.6) 후 자유 조정
def wmedian(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return x[o][np.searchsorted(cw, cw[-1] / 2)]
ud = Yr.units["동"]; mcd = np.divide(np.bincount(ud, pop * cnt0), np.bincount(ud, pop), out=np.zeros(ud.max() + 1), where=np.bincount(ud, pop) > 0)
tau_c = 0.6 * wmedian(mcd[np.bincount(ud, pop) > 0], np.bincount(ud, pop)[np.bincount(ud, pop) > 0]); print("tau_c", round(tau_c, 3), flush=True)
for lv, tag in (("공식LZ", "공식"), ("Leiden", "Leiden"), ("동", "동"), ("구", "구")):
    HAS_local = {t: set(HAS[t]) for t in types}
    st = run_FLOOR(Yr.units[lv], tau_c); rows.append(evaluate(st, f"FLOOR_{tag}")); rows[-1]["tau_c"] = tau_c; print("FLOOR", tag, f"{rows[-1]['완결률']:.4f}", f"{time.time()-t0:.0f}s", flush=True)
for i, u in enumerate(RANDS):
    HAS_local = {t: set(HAS[t]) for t in types}
    st = run_FLOOR(u, tau_c); rows.append(evaluate(st, "FLOOR_무작위116", i)); rows[-1]["tau_c"] = tau_c; print("FLOOR rand", i, f"{rows[-1]['완결률']:.4f}", f"{time.time()-t0:.0f}s", flush=True)
    pd.DataFrame(rows).to_csv(OUT / f"표4.1-15_묶음배치_{year}.csv", index=False, encoding="utf-8-sig")
import json; json.dump(PLACED, open(OUT / f"exp11_placements_{year}.json", "w", encoding="utf-8"), ensure_ascii=False)
D = pd.DataFrame(rows); D.to_csv(OUT / f"표4.1-15_묶음배치_{year}.csv", index=False, encoding="utf-8-sig")
S = D.groupby("방식").median(numeric_only=True)
cols = ["완결률", "평균완결수", "완결6이상", "취약20_완결률", "취약20_평균완결수", "중심수", "중심당_시설수_평균", "시설3종이상_중심수", "공식_중심있는단위비율", "Leiden_중심있는단위비율", "Leiden_최저", "Leiden_미달수", "Leiden_FGT0", "Leiden_Gini", "동_FGT0"]
open(OUT / f"표4.1-15_묶음배치_{year}.md", "w", encoding="utf-8").write(f"# 표 4.1-15 묶음 배치 방식 비교 ({year}; 기준 완결률 {Yr.cov(comp0):.4f}; 무작위 116은 {R}회 중앙값)\n\n" + md(S[cols].round(4).reset_index(), "{}"))
print(S[cols].round(4).to_string()); print("done", f"{time.time()-t0:.0f}s")
