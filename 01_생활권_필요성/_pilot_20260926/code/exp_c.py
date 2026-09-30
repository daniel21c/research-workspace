# -*- coding: utf-8 -*-
"""실험 C: P2 단위별 예산 배분(부족 인구 비례 정수 배분 → 단위 안 후보에서 도달 최대화). 두 해, τ 0.8/1.0/미도달비례."""
import time
import numpy as np, pandas as pd
from r1lib import Year, OUT, md

Y = {y: Year(y) for y in ("2020", "2025")}
K = 32; rows = []; t0 = time.time()
rng = np.random.default_rng(7)

def largest_remainder(w, K):
    w = np.asarray(w, float); w = w / w.sum() if w.sum() > 0 else np.ones_like(w) / len(w)
    raw = w * K; a = np.floor(raw).astype(int); rem = K - a.sum()
    for i in np.argsort(-(raw - a))[:rem]: a[i] += 1
    return a

for y, Yr in Y.items():
    r0 = Yr.reach("도서관"); C0 = Yr.cov(r0); cand = Yr.candidates("도서관"); pop = Yr.pop
    p0, _, _ = Yr.place(r0, None, 0, K, cand)
    def evalc(c):
        g = (pop * c).sum() - (pop * r0).sum()
        Cd, dd = Yr.unit_cov(Yr.units["동"], c); Cd0, _ = Yr.unit_cov(Yr.units["동"], r0); newg = c & ~r0
        return {"gain": g, "dong_below": int(((Cd < C0) & (dd > 0)).sum()), "dong_p10": np.quantile(Cd[dd > 0], .1),
                "dong_min": Cd[dd > 0].min(), "vuln_share": (pop[newg] * (Cd0[Yr.units["동"]][newg] < C0)).sum() / max(pop[newg].sum(), 1)}
    base = evalc(Yr.cov_after(r0, p0, K)); rows.append({"year": y, "rule": "P0", "alloc": "-", "level": "-", **base, "Reff": 1.0})
    partitions = dict(Yr.units)
    for rep in range(5):
        partitions[f"rand116_{rep}"] = Yr.dong_series_to_units(Yr.random_partition(116, rng))
    for lv, u in partitions.items():
        Cu, den = Yr.unit_cov(u, r0); nU = len(den)
        cand_u = u[cand]
        for alloc in ("미도달비례", "τ0.8부족", "τ1.0부족"):
            if alloc == "미도달비례": w = den - Cu * den
            else:
                tau = C0 * float(alloc[1:4]); w = np.maximum(0, tau * den - Cu * den)
            if w.sum() <= 0: continue
            Ku = largest_remainder(w, K)
            cov = r0.copy()
            for uu in np.nonzero(Ku)[0]:
                cj = cand[cand_u == uu]
                if len(cj) == 0: continue
                for _ in range(Ku[uu]):
                    best, bg = None, 0
                    for j in cj:
                        idx = Yr.cover_of(j); g = pop[idx[~cov[idx]]].sum()
                        if g > bg: best, bg = j, g
                    if best is None: break
                    cov[Yr.cover_of(best)] = True
            e = evalc(cov); rows.append({"year": y, "rule": "P2", "alloc": alloc, "level": lv, **e, "Reff": e["gain"] / base["gain"],
                                         "units_funded": int((Ku > 0).sum()), "n_units": nU})
        print(y, lv, f"{time.time()-t0:.0f}s", flush=True)
D = pd.DataFrame(rows); D.to_csv(OUT / "exp_c_p2.csv", index=False, encoding="utf-8-sig")
D["level2"] = D.level.str.replace(r"rand116_\d", "rand116", regex=True)
S = D.groupby(["year", "rule", "alloc", "level2"])[["Reff", "dong_below", "dong_p10", "vuln_share", "units_funded"]].median().round(3).reset_index()
print(md(S, "{}")); open(OUT / "exp_c_summary.md", "w", encoding="utf-8").write(md(S, "{}"))
