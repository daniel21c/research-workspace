# -*- coding: utf-8 -*-
"""실험 A: 단위 크기 연속축 + 116개 치환 검정. 두 해, 시설 6집합. 결과 r1_out/exp_a_*.csv"""
import sys, time, json
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from r1lib import Year, OUT, FACSETS

KS = [25, 50, 80, 116, 160, 250, 424]
REPS = {25: 1, 424: 1, 116: int(sys.argv[1]) if len(sys.argv) > 1 else 150}
R_OTHER = int(sys.argv[2]) if len(sys.argv) > 2 else 40
K_BUDGET = 32
rng = np.random.default_rng(20260926)
Y = {y: Year(y) for y in ("2020", "2025")}
print("loaded", flush=True)
r_none = {y: {f: Y[y].reach(f) for f in FACSETS} for y in Y}
C_none = {y: {f: Y[y].cov(r_none[y][f]) for f in FACSETS} for y in Y}
cand = {y: Y[y].candidates("도서관") for y in Y}
A_lib = {y: Y[y].sfca_grid("공공도서관") for y in Y}
A_seoul = {y: (Y[y].pop * A_lib[y]).sum() / Y[y].pop.sum() for y in Y}
base_gain = {}
for y in Y:
    p0, _, _ = Y[y].place(r_none[y]["도서관"], None, 0, K_BUDGET, cand[y])
    c = Y[y].cov_after(r_none[y]["도서관"], p0, K_BUDGET)
    base_gain[y] = (Y[y].pop * c).sum() - (Y[y].pop * r_none[y]["도서관"]).sum()
print("P0 gain", base_gain, "C_none", {y: {f: round(v, 3) for f, v in C_none[y].items()} for y in Y}, flush=True)


def metrics(s, tag, k, rep):
    rows = {}
    ucov = {}
    for y, Yr in Y.items():
        u = Yr.dong_series_to_units(s)
        row = {"tag": tag, "k": k, "rep": rep, "year": y, "n_units": int(u.max() + 1), "IFR": Yr.ifr(s)}
        for f in FACSETS:
            r = r_none[y][f]
            row[f"Hauc_{f}"] = Yr.H_curve(u, r, C_none[y][f]).mean()
            row[f"H10_{f}"] = Yr.H(u, r, C_none[y][f])
            rb = Yr.reach(f, u); row[f"loss_{f}"] = C_none[y][f] - Yr.cov(rb)
            row[f"within_{f}"] = Yr.within_share(u, r)
        # 도서관 배치
        for m in (0.8, 1.0):
            pk, kmin, sf = Yr.place(r_none[y]["도서관"], u, C_none[y]["도서관"] * m, K_BUDGET, cand[y])
            c = Yr.cov_after(r_none[y]["도서관"], pk, K_BUDGET)
            row[f"Kmin_{m}"] = kmin if kmin is not None else np.nan
            row[f"Reff_{m}"] = ((Yr.pop * c).sum() - (Yr.pop * r_none[y]["도서관"]).sum()) / base_gain[y]
            Cd, dend = Yr.unit_cov(Y[y].units["동"], c); row[f"dongmin_{m}"] = Cd[dend > 0].min()
            row[f"dong_below_{m}"] = int(((Cd < C_none[y]["도서관"]) & (dend > 0)).sum())
        # 나눠 쓰기: 단위 2SFCA 값, 0인 격자 인구 중 "충족 단위" 안 몫
        Au, den = Yr.unit_mean(u, A_lib[y]); zero = (A_lib[y] <= 0) & Yr.popped
        row["sfca_H"] = (Yr.pop[zero] * (Au[u][zero] >= A_seoul[y])).sum() / max(Yr.pop[zero].sum(), 1)
        row["sfca_unit_p10"] = np.quantile(Au[den > 0], 0.1)
        row["sfca_units_zero"] = int(((Au <= 1e-9) & (den > 0)).sum()) / int((den > 0).sum())
        # 행정 대리
        row["span_lib"] = Yr.catchment_spans(u, "도서관")
        Cu, dd = Yr.unit_cov(u, r_none[y]["도서관"]); ucov[y] = (Cu, dd)
        rows[y] = row
    # 안정성(두 해 동일 구획)
    a, da = ucov["2020"]; b, db = ucov["2025"]; ok = (da > 0) & (db > 0)
    rho = spearmanr(a[ok], b[ok]).correlation
    q = 0.1; na = max(1, int(ok.sum() * q))
    ia = set(np.argsort(a[ok])[:na]); ib = set(np.argsort(b[ok])[:na])
    jac = len(ia & ib) / len(ia | ib)
    for y in rows: rows[y]["stab_rho"] = rho; rows[y]["stab_jac10"] = jac
    return list(rows.values())


out = []
t0 = time.time()
dong_s = pd.Series(Y["2020"].dong_gdf.index, index=Y["2020"].dong_gdf.index)
out += metrics(dong_s, "동", 424, 0)
out += metrics(Y["2020"].dong_gdf["Ku"], "구", 25, 0)
out += metrics(Y["2020"].lz_map, "공식LZ", 116, 0)
out += metrics(Y["2020"].ld_map, "Leiden2020", 116, 0)
out += metrics(Y["2025"].ld_map, "Leiden2025", 116, 0)
print("named done", time.time() - t0, flush=True)
for k in KS:
    if k in (25, 424): continue
    R = REPS.get(k, R_OTHER)
    for rep in range(R):
        s = Y["2020"].random_partition(k, rng)
        out += metrics(s, f"rand{k}", k, rep)
        if rep % 10 == 0:
            print(f"k={k} rep={rep} {time.time()-t0:.0f}s", flush=True)
            pd.DataFrame(out).to_csv(OUT / "exp_a_partitions.csv", index=False, encoding="utf-8-sig")
df = pd.DataFrame(out); df.to_csv(OUT / "exp_a_partitions.csv", index=False, encoding="utf-8-sig")
json.dump({"base_gain": base_gain, "C_none": C_none, "A_seoul": A_seoul}, open(OUT / "exp_a_meta.json", "w"), ensure_ascii=False, indent=1)
print("done", time.time() - t0)
