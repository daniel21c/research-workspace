# -*- coding: utf-8 -*-
"""실험 16 (C2): 묶음 완결 정수계획 — 탐욕 결과(exp14)의 상한·하한.
정식화(묶음 MCLP): max Σ_i p_i z_i
   z_i ≤ Σ_{s∈S(k)} Σ_j A^s_{ij} x_{sj}   (격자 i 에서 기존에 안 닿는 범주 k 마다)
   Σ_j x_{sj} ≤ K_s (배치 유형 s),  x ∈ {0,1}, z ∈ [0,1]
   i 는 고정 범주가 모두 닿고, 빠진 배치 범주마다 닿는 후보가 있는 인구 격자만(나머지는 z_i = 0 이 자명).
보고: LP 완화 상한, 시간 제한 MIP 현재해·갭, exp14 COL·IND 탐욕값 대비.
IND 정확해: 유형별 MCLP(자기 범주 미도달 인구 최대화)를 각각 정수계획으로 풀고 완결률로 평가.
사용: python exp16_bundle_milp.py <seoul|logan7> <연도> [MIP 시간제한초=3600]"""
import sys, time, json
import numpy as np, pandas as pd
from scipy import sparse
from scipy.optimize import milp, linprog, LinearConstraint, Bounds
from r1lib import Year, OUT

bundle = sys.argv[1]; year = sys.argv[2]; TL = float(sys.argv[3]) if len(sys.argv) > 3 else 3600; t0 = time.time()
Yr = Year(year); Y20 = Year("2020") if year == "2025" else Yr; Y25 = Year("2025") if year == "2020" else Yr
pop = Yr.pop; n = len(Yr.M); popped = Yr.popped
def gidx(sel): return np.unique(Yr.gix.reindex(Yr.F[sel(Yr.F)].grid100_cd.dropna().unique()).dropna().astype(int).to_numpy())
def growth(name):
    k = len(Y25.fac[name][0]) - len(Y20.fac[name][0]); return k if k >= 3 else max(3, int(round(0.1 * len(Y20.fac[name][0]))))
if bundle == "seoul":
    T = 600
    CATS = [("공원", Yr.fac["공원"][0], []), ("도서관", Yr.fac["도서관"][0], [("도서관", growth("도서관"))]),
            ("노인여가", Yr.fac["노인이용시설"][0], [("노인이용시설", growth("노인이용시설"))]),
            ("청소년아동", np.union1d(Yr.fac["청소년수련시설"][0], Yr.fac["지역아동센터"][0]), [("청소년수련시설", growth("청소년수련시설"))]),
            ("보육", gidx(lambda f: f["시설"] == "어린이집"), [("국공립어린이집5분", growth("국공립어린이집5분"))]),
            ("공공체육", Yr.fac["공공체육"][0], [("공공체육", growth("공공체육"))])]
else:
    T = 900
    CATS = [(c, gidx(lambda f, c=c: f.cat_A == c), []) for c in ["교육", "보육·복지", "생활서비스", "소매", "의료"]]
    CATS += [("문화", gidx(lambda f: f.cat_A == "문화"), [("도서관", growth("도서관")), ("공공문화시설", growth("공공문화시설"))]),
             ("행정·안전", gidx(lambda f: f.cat_A == "행정·안전"), [("주민센터", growth("주민센터"))])]
NC = len(CATS)
m = Yr._t_all <= T; Eo, Ed = Yr._o_all[m], Yr._d_all[m]
R0 = np.zeros((NC, n), bool)
for k, (_, idx, _) in enumerate(CATS):
    isf = np.zeros(n, bool); isf[idx] = True; R0[k, Eo[isf[Ed]]] = True
cnt0 = R0.sum(0); comp0 = (cnt0 == NC) & popped; base = (pop * comp0).sum()
Yr.use_T(T); endsT = np.searchsorted(Ed, np.arange(n), side="right") > np.searchsorted(Ed, np.arange(n))
SUBS = []   # (유형, 범주, K, 후보 배열)
for k, (_, idx, subs) in enumerate(CATS):
    for s, K in subs:
        have = set(Yr.fac[s][0].tolist()) | set(idx.tolist())
        c = np.where(((Yr.M["pop"] > 0) | (Yr.M["biz"] > 0)).to_numpy() & endsT)[0]; SUBS.append((s, k, K, np.array([j for j in c if j not in have])))
fixed = [k for k, (_, _, subs) in enumerate(CATS) if not subs]
# 완결 가능 격자
reachable = R0.copy()
for s, k, K, cand in SUBS:
    isc = np.zeros(n, bool); isc[cand] = True; reachable[k, Eo[isc[Ed]]] = True
I = np.where(popped & ~comp0 & np.all(R0[fixed], axis=0) & np.all(reachable, axis=0))[0] if fixed else np.where(popped & ~comp0 & np.all(reachable, axis=0))[0]
iix = -np.ones(n, int); iix[I] = np.arange(len(I))
print(f"{bundle} {year}: 기준 완결 인구 {base:,.0f}, 완결 가능 격자 {len(I):,} (인구 {pop[I].sum():,.0f})", flush=True)
# 변수: x_(s,j) 블록들, 그 다음 z_i
xcols = []; blocks = []; off = 0
for s, k, K, cand in SUBS:
    isc = np.zeros(n, bool); isc[cand] = True
    sel = isc[Ed] & (iix[Eo] >= 0) & ~R0[k, Eo]
    jj = np.unique(Ed[sel]); col = -np.ones(n, int); col[jj] = off + np.arange(len(jj))
    blocks.append((s, k, K, jj, off, col, Eo[sel], Ed[sel])); off += len(jj)
nX = off; nZ = len(I); nV = nX + nZ
rows_i, rows_c, rows_v = [], [], []; r = 0; rowmap = {}
# 제약: 격자 i 의 빠진 범주 k 마다 z_i − Σ x ≤ 0
for k in range(NC):
    need = I[~R0[k, I]]
    if len(need) == 0: continue
    if k in fixed: continue
    rid = -np.ones(n, int); rid[need] = r + np.arange(len(need)); r += len(need)
    rows_i += list(rid[need]); rows_c += list(nX + iix[need]); rows_v += [1.0] * len(need)
    for s, kk, K, jj, o_, col, eo, ed in blocks:
        if kk != k: continue
        mm = rid[eo] >= 0; rows_i += list(rid[eo[mm]]); rows_c += list(col[ed[mm]]); rows_v += [-1.0] * int(mm.sum())
A1 = sparse.csr_matrix((rows_v, (rows_i, rows_c)), shape=(r, nV)); A1.sum_duplicates(); A1.data = np.where(A1.data > 0, 1.0, -1.0)
bud = sparse.lil_matrix((len(blocks), nV))
for b, (s, k, K, jj, o_, col, eo, ed) in enumerate(blocks): bud[b, o_:o_ + len(jj)] = 1
bud = bud.tocsr(); Kv = np.array([b[2] for b in blocks], float)
c = np.r_[np.zeros(nX), -pop[I]]
print(f"변수 x {nX:,} z {nZ:,}, 연결 제약 {r:,}, nnz {A1.nnz:,} ({time.time()-t0:.0f}s)", flush=True)
cons = [LinearConstraint(A1, -np.inf, 0), LinearConstraint(bud, 0, Kv)]
SKIP_LP = len(sys.argv) > 4 and sys.argv[4] == "nolp"
t1 = time.time(); lp = milp(c, constraints=cons, integrality=np.zeros(nV), bounds=Bounds(0, 1), options={"time_limit": min(TL, 1800), "disp": False}) if not SKIP_LP else type("R", (), {"x": None, "fun": np.nan, "message": "skipped"})()
ub_lp = base + (-lp.fun if lp.x is not None else np.nan); print(f"LP 상한 완결 인구 {ub_lp:,.0f} ({time.time()-t1:.0f}s) {lp.message[:40]}", flush=True)
t1 = time.time(); mip = milp(c, constraints=cons, integrality=np.r_[np.ones(nX), np.zeros(nZ)], bounds=Bounds(0, 1), options={"time_limit": TL, "disp": False, "mip_rel_gap": 0.01})
inc = base + (-mip.fun if mip.x is not None else np.nan); gap = getattr(mip, "mip_gap", None); dual = getattr(mip, "mip_dual_bound", None)
print(f"MIP 현재해 {inc:,.0f} 갭 {gap} 상계 {base + (-dual if dual is not None else np.nan):,.0f} ({time.time()-t1:.0f}s) {mip.message[:40]}", flush=True)
# IND 정확해: 유형별 MCLP
indcov = R0.copy()
for s, k, K, jj, o_, col, eo, ed in blocks:
    U = np.where(popped & ~R0[k])[0]; uix = -np.ones(n, int); uix[U] = np.arange(len(U))
    isc = np.zeros(n, bool); isc[jj] = True; mm = isc[Ed] & (uix[Eo] >= 0) & ~R0[k, Eo]
    cj = -np.ones(n, int); cj[jj] = np.arange(len(jj)); nx = len(jj); nu = len(U)
    Aa = sparse.csr_matrix((np.r_[-np.ones(int(mm.sum())), np.ones(nu)], (np.r_[uix[Eo[mm]], np.arange(nu)], np.r_[cj[Ed[mm]], nx + np.arange(nu)])), shape=(nu, nx + nu)); Aa.sum_duplicates(); Aa.data = np.where(Aa.data > 0, 1.0, -1.0)
    Bb = sparse.csr_matrix((np.ones(nx), (np.zeros(nx, int), np.arange(nx))), shape=(1, nx + nu))
    rr = milp(np.r_[np.zeros(nx), -pop[U]], constraints=[LinearConstraint(Aa, -np.inf, 0), LinearConstraint(Bb, 0, K)], integrality=np.r_[np.ones(nx), np.zeros(nu)], bounds=Bounds(0, 1), options={"time_limit": 900, "disp": False})
    pick = jj[np.round(rr.x[:nx]) > 0.5] if rr.x is not None else []
    for j in pick: indcov[k, Eo[Ed == j]] = True
    print(f"IND MCLP {s}: {len(pick)}개, {rr.message[:30]}", flush=True)
ind_exact = (pop * ((indcov.sum(0) == NC) & popped)).sum()
tot = pop.sum()
g = pd.read_csv(OUT / f"표4.1-18_묶음배치_{bundle}_{year}.csv"); col_g = g[g.방식 == "COL_조정_무경계"].완결률.iloc[0] * tot; ind_g = g[g.방식 == "IND_유형별독립"].완결률.iloc[0] * tot
res = {"bundle": bundle, "year": year, "기준_완결": base / tot, "IND_탐욕": ind_g / tot, "IND_정확(유형별MCLP)": ind_exact / tot, "COL_탐욕": col_g / tot,
       "MIP_현재해": inc / tot, "MIP_상계": (base + (-dual if dual is not None else np.nan)) / tot, "MIP_갭": gap, "LP_상한": ub_lp / tot,
       "조정이득_하한(MIP현재해/IND정확-1)": inc / ind_exact - 1, "조정이득_탐욕(COL/IND탐욕-1)": col_g / ind_g - 1, "초": round(time.time() - t0)}
pd.DataFrame([res]).to_csv(OUT / f"표4.1-19_묶음정수계획_{bundle}_{year}.csv", index=False, encoding="utf-8-sig")
print(json.dumps(res, ensure_ascii=False, indent=1, default=float)); print("done")
