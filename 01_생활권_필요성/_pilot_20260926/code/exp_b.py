# -*- coding: utf-8 -*-
"""실험 B: 도서관 배치 — τ 연속 곡선의 K_min, K 곡선의 효율·형평, 실제 배치 대조. 두 해."""
import time, json
import numpy as np, pandas as pd
from r1lib import Year, OUT

Y = {y: Year(y) for y in ("2020", "2025")}
TAUS = np.round(np.arange(0.5, 1.31, 0.1), 2)
KS = list(range(1, 65))
LEVELS = ["격자", "동", "공식LZ", "Leiden", "구"]
rows_tau, rows_k, rows_act = [], [], []
t0 = time.time()
for y, Yr in Y.items():
    r0 = Yr.reach("도서관"); C0 = Yr.cov(r0); cand = Yr.candidates("도서관")
    units = dict(Yr.units); units["격자"] = np.where(Yr.popped, np.arange(len(Yr.M)), len(Yr.M))
    p0, _, _ = Yr.place(r0, None, 0, 64, cand)
    def evalK(picks, K, base_pick=p0):
        c = Yr.cov_after(r0, picks, K); cb = Yr.cov_after(r0, base_pick, K)
        g = (Yr.pop * c).sum() - (Yr.pop * r0).sum(); gb = (Yr.pop * cb).sum() - (Yr.pop * r0).sum()
        Cd, dd = Yr.unit_cov(Yr.units["동"], c); Cd0, _ = Yr.unit_cov(Yr.units["동"], r0)
        newg = c & ~r0
        return {"gain": g, "Reff": g / gb if gb > 0 else np.nan,
                "dong_below": int(((Cd < C0) & (dd > 0)).sum()), "dong_min": Cd[dd > 0].min(),
                "dong_p10": np.quantile(Cd[dd > 0], .1),
                "vuln_share": (Yr.pop[newg] * (Cd0[Yr.units["동"]][newg] < C0)).sum() / max(Yr.pop[newg].sum(), 1)}
    for K in KS: rows_k.append({"year": y, "rule": "P0", "tau": "-", "K": K, **evalK(p0, K)})
    for lv in LEVELS:
        u = units[lv]
        for m in TAUS:
            tau = 1.0 if lv == "격자" else min(C0 * m, 0.9999)
            pk, kmin, sf = Yr.place(r0, u, tau, 64, cand, kcap=700)
            rows_tau.append({"year": y, "level": lv, "tau_mult": m, "tau": tau, "Kmin": kmin, "shortfall_left": sf,
                             **{f"{k}@32": v for k, v in evalK(pk, 32).items()}})
            if m in (0.8, 1.0):
                for K in KS: rows_k.append({"year": y, "rule": f"P1 {lv}", "tau": m, "K": K, **evalK(pk, K)})
            if lv == "격자": break
        print(y, lv, f"{time.time()-t0:.0f}s", flush=True)
    # 실제 배치 (2020→2025 신규 도서관 격자)
    if y == "2020":
        new = np.setdiff1d(Y["2025"].fac["도서관"][0], Yr.fac["도서관"][0])
        new = [j for j in new if Yr.ends[j] > Yr.starts[j]]
        rows_act.append({"year": y, "rule": "actual", "K": len(new), **evalK(list(new), len(new))})
        rows_act.append({"year": y, "rule": "P0@same", "K": len(new), **evalK(p0, len(new))})
        # 실제 신규 도서관이 놓인 동의 2020 기준 Coverage 분위
        Cd0, _ = Yr.unit_cov(Yr.units["동"], r0)
        rows_act.append({"year": y, "rule": "actual_site_dongC_mean", "K": len(new),
                         "gain": float(np.mean(Cd0[Yr.units["동"][new]]))})
        rows_act.append({"year": y, "rule": "P0_site_dongC_mean", "K": len(new),
                         "gain": float(np.mean(Cd0[Yr.units["동"][p0[:len(new)]]]))})
pd.DataFrame(rows_tau).to_csv(OUT / "exp_b_tau.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(rows_k).to_csv(OUT / "exp_b_kcurve.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(rows_act).to_csv(OUT / "exp_b_actual.csv", index=False, encoding="utf-8-sig")
print("done", time.time() - t0)
