# -*- coding: utf-8 -*-
"""실험 14 (C1): 묶음 배치 실험 — 묶음 정의를 선행연구·제도로 (2026-10-01).
묶음(bundle):
  seoul  — 서울 2030 생활권계획 지역생활권 생활서비스 6분야(주차장 제외), 계획 기준 보행 10분(600초).
           공원(고정) · 도서관(배치: 공공도서관) · 노인여가(배치: 노인 이용시설) · 청소년아동(도달 = 청소년수련∪지역아동센터, 배치: 청소년수련시설)
           · 보육(도달 = 어린이집 전체, 배치: 국공립어린이집) · 공공체육(배치: 공공체육, 부가 층 신뢰도 중).
  logan7 — Logan형 최댓값 정의, cat_A 7범주 15분. 공공이 놓는 것만 배치: 문화(공공도서관·공공문화시설), 행정·안전(주민센터). 나머지 고정.
각 배치 유형의 추가 수 K = 실제 2020→2025 격자 순증(3 미만이면 2020 수의 10%). 고정 범주는 기존 도달만.
방식: IND(유형별 독립 도달 최대화, 격자 논리) / COL(경계 없는 묶음 조정) / FLOOR_u(단위 평균 도달 범주 수 하한 → 조정) / ZONE_u(단위마다 중심 하나씩 순환 배분).
평가: 완결률, 평균 도달 범주 수, 배치 전 취약 20%(도달 범주 수 하위) 완결률, 평가권역(Leiden·공식·동·구) 최저·미달·FGT0·Gini, 중심 구조.
목적함수: f(c) = (c/NC)^P (P=4 본; 환경변수 P_EXP). 배치는 exp14_placements_{묶음}_{연도}.json 에 저장(C2·C3 입력).
사용: python exp14_bundle_place.py <seoul|logan7> <연도> [무작위반복=10]"""
import sys, time, heapq, os, json
import numpy as np, pandas as pd
from r1lib import Year, OUT, md

bundle = sys.argv[1]; year = sys.argv[2]; R = int(sys.argv[3]) if len(sys.argv) > 3 else 10
P_EXP = float(os.environ.get("P_EXP", "4")); t0 = time.time(); rng = np.random.default_rng(20261001)
Yr = Year(year); Y20 = Year("2020") if year == "2025" else Yr; Y25 = Year("2025") if year == "2020" else Yr
pop = Yr.pop; n = len(Yr.M); popped = Yr.popped
def gidx(sel):
    return np.unique(Yr.gix.reindex(Yr.F[sel(Yr.F)].grid100_cd.dropna().unique()).dropna().astype(int).to_numpy())
def growth(name):
    k = len(Y25.fac[name][0]) - len(Y20.fac[name][0]); return k if k >= 3 else max(3, int(round(0.1 * len(Y20.fac[name][0]))))

# 범주: (이름, 임계초, 기존 도달 시설 격자, [(배치 유형 이름, K)])
if bundle == "seoul":
    T = 600
    CATS = [("공원", T, Yr.fac["공원"][0], []),
            ("도서관", T, Yr.fac["도서관"][0], [("도서관", growth("도서관"))]),
            ("노인여가", T, Yr.fac["노인이용시설"][0], [("노인이용시설", growth("노인이용시설"))]),
            ("청소년아동", T, np.union1d(Yr.fac["청소년수련시설"][0], Yr.fac["지역아동센터"][0]), [("청소년수련시설", growth("청소년수련시설"))]),
            ("보육", T, gidx(lambda f: f["시설"] == "어린이집"), [("국공립어린이집5분", growth("국공립어린이집5분"))]),
            ("공공체육", T, Yr.fac["공공체육"][0], [("공공체육", growth("공공체육"))])]
elif bundle == "logan7":
    T = 900
    CATS = [(c, T, gidx(lambda f, c=c: f.cat_A == c), []) for c in ["교육", "보육·복지", "생활서비스", "소매", "의료"]]
    CATS += [("문화", T, gidx(lambda f: f.cat_A == "문화"), [("도서관", growth("도서관")), ("공공문화시설", growth("공공문화시설"))]),
             ("행정·안전", T, gidx(lambda f: f.cat_A == "행정·안전"), [("주민센터", growth("주민센터"))])]
NC = len(CATS); cat_names = [c[0] for c in CATS]
def f(c): return (c / NC) ** P_EXP
m = Yr._t_all <= T; Eo, Ed = Yr._o_all[m], Yr._d_all[m]; Es = np.searchsorted(Ed, np.arange(n)); Ee = np.searchsorted(Ed, np.arange(n), side="right")
def cover(j): return Eo[Es[j]:Ee[j]]
R0 = np.zeros((NC, n), bool)
for k, (_, _, idx, _) in enumerate(CATS):
    isf = np.zeros(n, bool); isf[idx] = True; R0[k, Eo[isf[Ed]]] = True
SUB = {}   # 배치 유형 → (범주 번호, K, 후보 집합)
Yr.use_T(T)
for k, (_, _, idx, subs) in enumerate(CATS):
    for s, K in subs:
        have = set(Yr.fac[s][0].tolist()) | set(idx.tolist())
        c = np.where(((Yr.M["pop"] > 0) | (Yr.M["biz"] > 0)).to_numpy() & (Ee > Es))[0]
        SUB[s] = (k, K, np.array([j for j in c if j not in have]))
Yr.use_T(900)
candALL = np.unique(np.concatenate([v[2] for v in SUB.values()])); candset = {s: set(v[2].tolist()) for s, v in SUB.items()}
cnt0 = R0.sum(0); comp0 = (cnt0 == NC) & popped
o = np.argsort(cnt0 + (~popped) * 99, kind="stable"); cw = np.cumsum(pop[o]); cut = cnt0[o][min(np.searchsorted(cw, 0.2 * cw[-1]), n - 1)]; POOR = (cnt0 <= cut) & popped
Ktot = sum(v[1] for v in SUB.values())
print(f"{bundle} {year} T={T}s 범주 {cat_names} 배치 {[(s, v[1]) for s, v in SUB.items()]} 합 {Ktot}; 기준 완결률 {Yr.cov(comp0):.4f} 평균범주 {(pop*cnt0).sum()/pop.sum():.3f}", flush=True)
EVAL = {"Leiden": Yr.units["Leiden"], "공식": Yr.units["공식LZ"], "동": Yr.units["동"], "구": Yr.units["구"]}
def gini_w(x, w):
    o_ = np.argsort(x); x, w = x[o_], w[o_]; cw_ = np.cumsum(w); cx = np.cumsum(x * w)
    return 1 - 2 * np.sum(w * (cx - x * w / 2)) / (cw_[-1] * cx[-1]) if cx[-1] > 0 else np.nan

class State:
    def __init__(self): self.R = R0.copy(); self.cnt = cnt0.copy(); self.B = {s: v[1] for s, v in SUB.items()}; self.placed = {s: [] for s in SUB}
    def center_set(self, j):
        out, used = [], set()
        for s, (k, K, _) in SUB.items():
            if k in used or self.B[s] <= 0 or j not in candset[s]: continue
            idx = cover(j)
            if np.any(~self.R[k, idx] & popped[idx]): out.append(s); used.add(k)
        return out
    def gain(self, j, S):
        parts = [cover(j)[~self.R[SUB[s][0], cover(j)]] for s in S]
        g = np.concatenate(parts) if parts else np.array([], int)
        if len(g) == 0: return 0.0
        u, c = np.unique(g, return_counts=True); old = self.cnt[u]; return float((pop[u] * (f(old + c) - f(old))).sum())
    def apply(self, j, S):
        for s in S:
            k = SUB[s][0]; idx = cover(j); new = idx[~self.R[k, idx]]; self.R[k, new] = True; self.cnt[new] += 1; self.B[s] -= 1; self.placed[s].append(int(j))

PLACED = {}
def evaluate(st, name, rep=0):
    PLACED[f"{name}#{rep}"] = st.placed
    comp = (st.cnt == NC) & popped; tau_b = 0.5 * Yr.cov(comp)
    row = {"bundle": bundle, "year": year, "방식": name, "rep": rep, "완결률": Yr.cov(comp), "완결률_기준": Yr.cov(comp0), "평균범주수": (pop * st.cnt).sum() / pop.sum(),
           "완결-1이상": pop[popped & (st.cnt >= NC - 1)].sum() / pop.sum(), "취약20_완결률": pop[POOR & comp].sum() / pop[POOR].sum(),
           "취약20_평균범주수": (pop * st.cnt)[POOR].sum() / pop[POOR].sum(), "사용": sum(SUB[s][1] - st.B[s] for s in SUB)}
    allj = sum(st.placed.values(), []); uj, cj = np.unique(allj, return_counts=True)
    row["중심수"] = len(uj); row["중심당_시설"] = float(cj.mean()) if len(cj) else 0.0; row["다유형_중심수"] = int((cj >= 2).sum())
    for en, eu in EVAL.items():
        num = np.bincount(eu, pop * comp); den = np.bincount(eu, pop); v = den > 0; sh = np.divide(num, den, out=np.zeros_like(num), where=v)
        row[f"{en}_최저"] = sh[v].min(); row[f"{en}_미달수"] = int((v & (sh < tau_b)).sum()); row[f"{en}_FGT0"] = den[v & (sh < tau_b)].sum() / den[v].sum(); row[f"{en}_Gini"] = gini_w(sh[v], den[v])
    return row

def greedy_free(st):
    heap = [(-st.gain(j, S), int(j)) for j in candALL for S in [st.center_set(j)] if S]; heapq.heapify(heap); moves = 0
    while heap and any(st.B[s] > 0 for s in SUB):
        _, j = heapq.heappop(heap); S = st.center_set(j)
        if not S: continue
        g = st.gain(j, S)
        if heap and g < -heap[0][0] - 1e-9: heapq.heappush(heap, (-g, j)); continue
        if g <= 0: break
        st.apply(j, S); moves += 1
        if moves % 25 == 0: heap = [(-st.gain(jj, SS), int(jj)) for jj in candALL for SS in [st.center_set(jj)] if SS]; heapq.heapify(heap)
    return st

def run_IND():
    st = State()
    for s, (k, K, cand) in SUB.items():
        Yr.use_T(T); Yr.fac["_tmp"] = (np.where(st.R[k])[0][:0], T)   # dummy
        # 범주 k 의 현재 도달 위에서 유형 s 도달 최대화(MCLP 탐욕)
        cov = st.R[k].copy(); heap = [(-(pop[cover(j)[~cov[cover(j)]]].sum()), int(j)) for j in cand]; heapq.heapify(heap); placed = 0
        while heap and placed < K:
            _, j = heapq.heappop(heap); idx = cover(j); g = pop[idx[~cov[idx]]].sum()
            if heap and g < -heap[0][0] - 1e-9: heapq.heappush(heap, (-g, j)); continue
            if g <= 0: break
            st.apply(j, [s]); cov = st.R[k]; placed += 1
    Yr.use_T(900); return st

def run_FLOOR(u, tau_c):
    st = State(); den = np.bincount(u, pop); v = den > 0; nz = u.max() + 1; members = {z: candALL[u[candALL] == z] for z in range(nz)}; stuck = set()
    while any(st.B[s] > 0 for s in SUB):
        mc = np.divide(np.bincount(u, pop * st.cnt, minlength=nz), den, out=np.full(nz, 99.0), where=v)
        below = [z for z in np.argsort(mc) if v[z] and mc[z] < tau_c - 1e-9 and z not in stuck]
        if not below: break
        z = below[0]; best, bg, bS = None, 0.0, None
        for j in members[z]:
            S = st.center_set(j)
            if not S: continue
            add = sum(pop[(nw := cover(j)[~st.R[SUB[s][0], cover(j)]])[u[nw] == z]].sum() for s in S); g = min(add / den[z], tau_c - mc[z])
            if g > bg: best, bg, bS = j, g, S
        if best is None: stuck.add(z); continue
        st.apply(best, bS)
    return greedy_free(st)

def run_ZONE(u):
    st = State(); nz = u.max() + 1; members = {z: candALL[u[candALL] == z] for z in range(nz)}; den = np.bincount(u, pop); v = den > 0
    order = list(np.argsort(np.divide(np.bincount(u, pop * cnt0, minlength=nz), den, out=np.full(nz, 99.0), where=v))); stuck = set()
    while any(st.B[s] > 0 for s in SUB):
        prog = False
        for z in order:
            if z in stuck or not v[z] or len(members[z]) == 0: continue
            best, bg, bS = None, 0.0, None
            for j in members[z]:
                S = st.center_set(j)
                if S:
                    g = st.gain(j, S)
                    if g > bg: best, bg, bS = j, g, S
            if best is None: stuck.add(z); continue
            st.apply(best, bS); prog = True
            if not any(st.B[s] > 0 for s in SUB): break
        if not prog: break
    return st

def wmedian(x, w):
    o_ = np.argsort(x); cw_ = np.cumsum(w[o_]); return x[o_][np.searchsorted(cw_, cw_[-1] / 2)]
ud = Yr.units["동"]; dd = np.bincount(ud, pop); mcd = np.bincount(ud, pop * cnt0) / np.maximum(dd, 1); tau_c = 0.6 * wmedian(mcd[dd > 0], dd[dd > 0])
rows = []
rows.append(evaluate(run_IND(), "IND_유형별독립")); print("IND", round(rows[-1]["완결률"], 4), f"{time.time()-t0:.0f}s", flush=True)
rows.append(evaluate(greedy_free(State()), "COL_조정_무경계")); print("COL", round(rows[-1]["완결률"], 4), f"{time.time()-t0:.0f}s", flush=True)
for lv, tag in (("공식LZ", "공식"), ("Leiden", "Leiden"), ("동", "동"), ("구", "구")):
    rows.append(evaluate(run_FLOOR(Yr.units[lv], tau_c), f"FLOOR_{tag}")); print("FLOOR", tag, round(rows[-1]["완결률"], 4), f"{time.time()-t0:.0f}s", flush=True)
    rows.append(evaluate(run_ZONE(Yr.units[lv]), f"ZONE_{tag}")); print("ZONE", tag, round(rows[-1]["완결률"], 4), f"{time.time()-t0:.0f}s", flush=True)
for i in range(R):
    up = Yr.dong_series_to_units(Yr.random_partition(116, rng))
    rows.append(evaluate(run_FLOOR(up, tau_c), "FLOOR_무작위116", i)); rows.append(evaluate(run_ZONE(up), "ZONE_무작위116", i))
    print("rand", i, round(rows[-2]["완결률"], 4), round(rows[-1]["완결률"], 4), f"{time.time()-t0:.0f}s", flush=True)
D = pd.DataFrame(rows); D["tau_c"] = tau_c; D["P_EXP"] = P_EXP
suf = "" if P_EXP == 4 else f"_p{int(P_EXP)}"
D.to_csv(OUT / f"표4.1-18_묶음배치_{bundle}_{year}{suf}.csv", index=False, encoding="utf-8-sig")
json.dump({k: {s: v for s, v in d.items()} for k, d in PLACED.items()}, open(OUT / f"exp14_placements_{bundle}_{year}{suf}.json", "w", encoding="utf-8"), ensure_ascii=False)
S = D.groupby("방식").median(numeric_only=True)
cols = ["완결률", "평균범주수", "완결-1이상", "취약20_완결률", "취약20_평균범주수", "중심수", "중심당_시설", "다유형_중심수", "Leiden_최저", "Leiden_미달수", "Leiden_FGT0", "Leiden_Gini", "동_FGT0"]
open(OUT / f"표4.1-18_묶음배치_{bundle}_{year}{suf}.md", "w", encoding="utf-8").write(
    f"# 표 4.1-18 묶음 배치 ({bundle}, {year}, T={T}s, 추가 {Ktot}; 기준 완결률 {Yr.cov(comp0):.4f}; 무작위 116 {R}회 중앙값)\n\n" + md(S[cols].round(4).reset_index(), "{}"))
print(S[cols].round(4).to_string()); print("done", f"{time.time()-t0:.0f}s")
