# -*- coding: utf-8 -*-
"""정수해 대조: scipy.optimize.milp(HiGHS)로 (1) P0 MCLP 최적 도달 증가(K=32), (2) 단위별 하한 K_min(τ_main)을 구해 탐욕 해와 비교.
모형: x_j∈{0,1} 후보지, y_i∈[0,1] 미도달 격자(인구>0) 도달 여부, y_i ≤ Σ_{j∋i} x_j.
  P0: max Σ pop_i y_i  s.t. Σ x_j = K.
  K_min(π,τ): min Σ x_j  s.t. ∀u: cov_u + Σ_{i∈u} pop_i y_i ≥ τ·pop_u.
사용: python milp_check.py [연도=2020] [시간제한초=600]"""
import sys, time, json
import numpy as np, pandas as pd
from scipy import sparse
from scipy.optimize import milp, LinearConstraint, Bounds
from r1lib import Year, OUT

year = sys.argv[1] if len(sys.argv) > 1 else "2020"; TL = float(sys.argv[2]) if len(sys.argv) > 2 else 600
ONLY = sys.argv[3].split(",") if len(sys.argv) > 3 else None   # 예: 동  → 해당 단위만
K = 32; t0 = time.time()
Yr = Year(year); pop = Yr.pop; r0 = Yr.reach("도서관"); C0 = Yr.cov(r0); cand = Yr.candidates("도서관")
def wmedian(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return x[o][np.searchsorted(cw, cw[-1] / 2)]
Cd, dd = Yr.unit_cov(Yr.units["동"], r0); tau = 0.6 * wmedian(Cd[dd > 0], dd[dd > 0])
# 미도달·인구>0 격자 i, 후보 j 의 피복 행렬 A (i × j)
I = np.where((~r0) & Yr.popped)[0]; iix = {g: k for k, g in enumerate(I)}
rows_, cols_ = [], []
for jj, j in enumerate(cand):
    oo = Yr.cover_of(j); oo = oo[(~r0[oo]) & Yr.popped[oo]]
    rows_.extend(iix[o] for o in oo); cols_.extend([jj] * len(oo))
A = sparse.csr_matrix((np.ones(len(rows_)), (rows_, cols_)), shape=(len(I), len(cand)))
A.data[:] = 1; A.sum_duplicates()
nI, nJ = len(I), len(cand); popI = pop[I]
print(f"grids {nI:,} cand {nJ:,} nnz {A.nnz:,} tau {tau:.3f} ({time.time()-t0:.0f}s)", flush=True)
res_rows = []
def solve(c, cons, integrality, tl):
    r = milp(c, constraints=cons, integrality=integrality, bounds=Bounds(0, 1), options={"time_limit": tl, "disp": False})
    return r
# 변수 순서: x (nJ), y (nI)
integrality = np.r_[np.ones(nJ), np.zeros(nI)]
link = sparse.hstack([-A, sparse.eye(nI)]).tocsr()          # y_i − Σ x_j ≤ 0
# (1) P0 MCLP
if ONLY is None:
  c = np.r_[np.zeros(nJ), -popI]
  budget = sparse.hstack([sparse.csr_matrix(np.ones((1, nJ))), sparse.csr_matrix((1, nI))])
  r = solve(c, [LinearConstraint(link, -np.inf, 0), LinearConstraint(budget, K, K)], integrality, TL)
  p0g, _, _ = Yr.place(r0, None, 0, K, cand); g_greedy = (pop * Yr.cov_after(r0, p0g, K)).sum() - (pop * r0).sum()
  g_milp = -r.fun if r.x is not None else np.nan
  res_rows.append({"year": year, "문제": "P0 MCLP K=32 도달증가", "탐욕": g_greedy, "정수해": g_milp, "status": r.message, "gap": r.mip_gap if hasattr(r, "mip_gap") else None, "초": round(time.time() - t0)})
  print(res_rows[-1], flush=True)
# (2) K_min by level
for lv in (ONLY or ("공식LZ", "Leiden", "구", "동")):
    u = Yr.units[lv]; nU = u.max() + 1; den = np.bincount(u, pop, minlength=nU); cov0 = np.bincount(u, pop * r0, minlength=nU)
    need = np.maximum(0, tau * den - cov0); rowsU = np.where(need > 1e-9)[0]
    M = sparse.csr_matrix((popI, (u[I], np.arange(nI))), shape=(nU, nI))[rowsU]
    floor = sparse.hstack([sparse.csr_matrix((len(rowsU), nJ)), M])
    c = np.r_[np.ones(nJ), np.zeros(nI)]
    t1 = time.time()
    r = solve(c, [LinearConstraint(link, -np.inf, 0), LinearConstraint(floor, need[rowsU], np.inf)], integrality, TL)
    _, kmin_g, _ = Yr.place(r0, u, tau, K, cand, kcap=700)
    kmin_m = int(round(r.fun)) if r.x is not None else np.nan
    res_rows.append({"year": year, "문제": f"K_min {lv} τ={tau:.3f}", "탐욕": kmin_g, "정수해": kmin_m, "status": r.message, "gap": getattr(r, "mip_gap", None), "초": round(time.time() - t1)})
    print(res_rows[-1], flush=True)
R = pd.DataFrame(res_rows); R.to_csv(OUT / (f"정수해대조_{year}.csv" if ONLY is None else f"정수해대조_{year}_{'_'.join(ONLY)}_TL{int(TL)}.csv"), index=False, encoding="utf-8-sig"); print(R.to_string())
