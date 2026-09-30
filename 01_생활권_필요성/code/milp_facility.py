# -*- coding: utf-8 -*-
"""시설별 K_min 정수해 대조(공식 생활권·Leiden·구; 동은 시간이 길어 제외). 창 경계(k_afford)의 근거가 되는 K_min ≤ K 판정을 정수해로 확인.
사용: python milp_facility.py [연도=2020] [시간제한초=600] [τ규칙=중위60%|평균60%]"""
import sys, time
import numpy as np, pandas as pd
from scipy import sparse
from scipy.optimize import milp, LinearConstraint, Bounds
from r1lib import Year, OUT, PLACE_SETS

year = sys.argv[1] if len(sys.argv) > 1 else "2020"; TL = float(sys.argv[2]) if len(sys.argv) > 2 else 600
TAU_RULE = sys.argv[3] if len(sys.argv) > 3 else "중위60%"; t0 = time.time()
Y = {"2020": Year("2020"), "2025": Year("2025")}; Yr = Y[year]; pop = Yr.pop
def wmedian(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return x[o][np.searchsorted(cw, cw[-1] / 2)]
rows = []
for fac in PLACE_SETS:
    n20, n25 = len(Y["2020"].fac[fac][0]), len(Y["2025"].fac[fac][0]); K = n25 - n20
    if K < 3: K = max(3, int(round(0.1 * n20)))
    Yr.use_T(Yr.fac[fac][1])
    r0 = Yr.reach(fac); C0 = Yr.cov(r0); cand = Yr.candidates(fac)
    Cd, dd = Yr.unit_cov(Yr.units["동"], r0); tau = {"중위60%": 0.6 * wmedian(Cd[dd > 0], dd[dd > 0]), "평균60%": 0.6 * C0}[TAU_RULE]
    I = np.where((~r0) & Yr.popped)[0]; iix = {g: k for k, g in enumerate(I)}
    rr, cc = [], []
    for jj, j in enumerate(cand):
        oo = Yr.cover_of(j); oo = oo[(~r0[oo]) & Yr.popped[oo]]; rr.extend(iix[o] for o in oo); cc.extend([jj] * len(oo))
    A = sparse.csr_matrix((np.ones(len(rr)), (rr, cc)), shape=(len(I), len(cand))); A.data[:] = 1; A.sum_duplicates()
    nI, nJ = len(I), len(cand); popI = pop[I]; integrality = np.r_[np.ones(nJ), np.zeros(nI)]
    link = sparse.hstack([-A, sparse.eye(nI)]).tocsr()
    for lv in ("공식LZ", "Leiden", "구"):
        u = Yr.units[lv]; nU = u.max() + 1; den = np.bincount(u, pop, minlength=nU); cov0 = np.bincount(u, pop * r0, minlength=nU)
        need = np.maximum(0, tau * den - cov0); rowsU = np.where(need > 1e-9)[0]
        _, kg, _ = Yr.place(r0, u, tau, K, cand, kcap=max(700, 4 * K))
        if len(rowsU) == 0:
            rows.append({"year": year, "시설": fac, "K": K, "τ": tau, "단위": lv, "탐욕": kg, "정수해": 0, "status": "미달 단위 없음", "초": 0}); continue
        M = sparse.csr_matrix((popI, (u[I], np.arange(nI))), shape=(nU, nI))[rowsU]
        floor = sparse.hstack([sparse.csr_matrix((len(rowsU), nJ)), M]); t1 = time.time()
        r = milp(np.r_[np.ones(nJ), np.zeros(nI)], constraints=[LinearConstraint(link, -np.inf, 0), LinearConstraint(floor, need[rowsU], np.inf)],
                 integrality=integrality, bounds=Bounds(0, 1), options={"time_limit": TL, "disp": False})
        km = int(round(r.fun)) if r.x is not None else np.nan
        rows.append({"year": year, "시설": fac, "K": K, "τ": tau, "단위": lv, "탐욕": kg, "정수해": km, "status": r.message[:40], "gap": getattr(r, "mip_gap", None), "초": round(time.time() - t1)})
        print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(OUT / f"정수해대조_시설별_{year}_{TAU_RULE}.csv", index=False, encoding="utf-8-sig")
print(pd.DataFrame(rows).to_string()); print("done", f"{time.time()-t0:.0f}s")
