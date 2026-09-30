# -*- coding: utf-8 -*-
"""실험 E: 목적함수를 '도달 여부'가 아니라 '도달시간(30분 상한)'으로 바꾸면 효율–형평 충돌이 생기는가.
P0-time: Σ pop·min(t,1800) 최소화(탐욕). 단위 규칙: maximin-time(가장 나쁜 단위의 인구가중 시간을 가장 많이 줄이는 후보)."""
import time, sys
import numpy as np, pandas as pd, pyarrow.dataset as ds
from r1lib import Year, OUT, md, PKG, X

CAP = 1800; K = 32
rows, prof = [], []
t0 = time.time()
dong_gdf = X.load_dong(); dong_gdf["area_km2"] = dong_gdf.geometry.area / 1e6; area = dong_gdf.set_index("Dong")["area_km2"]
for y in ("2020", "2025"):
    Yr = Year(y); pop = Yr.pop; n = len(Yr.M)
    tt = ds.dataset(PKG / f"입력/ttm/ttm100_{y}", format="parquet", partitioning="hive").to_table(columns=["o_grid", "d_grid", "t_sec"]).to_pandas()
    o = Yr.gix.reindex(tt.o_grid).to_numpy(); d = Yr.gix.reindex(tt.d_grid).to_numpy(); ok = ~(np.isnan(o) | np.isnan(d))
    o = o[ok].astype(np.int64); d = d[ok].astype(np.int64); t = tt.t_sec.to_numpy()[ok].astype(np.int32); del tt
    order = np.argsort(d, kind="stable"); o, d, t = o[order], d[order], t[order]
    st = np.searchsorted(d, np.arange(n)); en = np.searchsorted(d, np.arange(n), side="right")
    lib = Yr.fac["도서관"][0]
    cur = np.full(n, CAP, np.int32)
    for j in lib:
        oo, ttj = o[st[j]:en[j]], t[st[j]:en[j]]; np.minimum.at(cur, oo, ttj)
    cur0 = cur.copy()
    cand = Yr.candidates("도서관")
    ud = Yr.units["동"]
    def dong_time(c):
        num = np.bincount(ud, pop * c); den = np.bincount(ud, pop); return np.divide(num, den, out=np.zeros_like(num), where=den > 0) / 60, den
    def evalc(c):
        base = (pop * cur0).sum(); now = (pop * c).sum()
        dt, den = dong_time(c); dt0, _ = dong_time(cur0); v = den > 0
        newr = (c <= 900) & (cur0 > 900)
        return {"time_reduction_min": (base - now) / 60 / pop.sum() * 1, "cov15_gain": (pop * newr).sum(),
                "dong_time_p90": np.quantile(dt[v], .9), "dong_time_max": dt[v].max(), "dong_over20": int(((dt > 20) & v).sum()),
                "benef_dens_med": float(np.median((np.bincount(ud, pop * (c < cur0)) / area.reindex(pd.factorize(Yr.M.dong)[1]).to_numpy())[np.bincount(ud, pop * (c < cur0)) > 0])) if (c < cur0).any() else np.nan}
    def gain_time(j, c):
        oo, ttj = o[st[j]:en[j]], t[st[j]:en[j]]; red = c[oo] - ttj; m = red > 0
        return (pop[oo[m]] * red[m]).sum(), oo[m], ttj[m]
    # P0-time
    c = cur0.copy(); picks = []
    for step in range(K):
        best, bg = None, 0
        for j in cand:
            g, _, _ = gain_time(j, c)
            if g > bg: best, bg = j, g
        _, oo, ttj = gain_time(best, c); c[oo] = ttj; picks.append(best)
    e0 = evalc(c); rows.append({"year": y, "rule": "P0-time", "level": "-", **e0, "Reff": 1.0})
    # 누가 이득을 봤나: 이득 인구의 동 밀도 분포
    print(y, "P0-time", f"{time.time()-t0:.0f}s", flush=True)
    # P0-cov (도달 여부 목적) 을 시간으로 평가
    p0c, _, _ = Yr.place(Yr.reach("도서관"), None, 0, K, cand); c = cur0.copy()
    for j in p0c:
        _, oo, ttj = gain_time(j, c); c[oo] = ttj
    e = evalc(c); rows.append({"year": y, "rule": "P0-cov(평가:시간)", "level": "-", **e, "Reff": e["time_reduction_min"] / e0["time_reduction_min"]})
    # maximin-time by level
    for lv in ("동", "공식LZ", "Leiden", "구"):
        u = Yr.units[lv]; den = np.bincount(u, pop); valid = den > 0
        c = cur0.copy(); picks = []
        for step in range(K):
            ut = np.divide(np.bincount(u, pop * c, minlength=len(den)), den, out=np.full(len(den), -1.0), where=valid)
            worst = np.argmax(ut); best, bkey = None, (-1.0, -1.0)
            for j in cand:
                g, oo, ttj = gain_time(j, c)
                if g <= 0: continue
                m = u[oo] == worst; gw = (pop[oo[m]] * (c[oo[m]] - ttj[m])).sum()
                if (gw, g) > bkey: best, bkey = j, (gw, g)
            if bkey[0] <= 0: valid[worst] = False; continue
            _, oo, ttj = gain_time(best, c); c[oo] = ttj; picks.append(best)
        e = evalc(c); rows.append({"year": y, "rule": "maximin-time", "level": lv, **e, "Reff": e["time_reduction_min"] / e0["time_reduction_min"]})
        print(y, lv, f"{time.time()-t0:.0f}s", flush=True)
R = pd.DataFrame(rows).round(3); R.to_csv(OUT / "exp_e_time.csv", index=False, encoding="utf-8-sig")
s = md(R, "{}"); print(s); open(OUT / "exp_e_summary.md", "w", encoding="utf-8").write(s)
