# -*- coding: utf-8 -*-
"""실험 D: (1) 최소단위 우선(maximin) 규칙 — 매 단계 가장 낮은 단위의 Coverage 를 가장 많이 올리는 후보 선택.
(2) P0 가 남기는 동의 성격(인구밀도·인구) — '효율은 밀집지부터'가 서울 도서관에서 실제로 나타나는가."""
import time
import numpy as np, pandas as pd
from r1lib import Year, OUT, md, X

Y = {y: Year(y) for y in ("2020", "2025")}
K = 32; rows = []; prof = []; t0 = time.time()
dong_gdf = X.load_dong(); dong_gdf["area_km2"] = dong_gdf.geometry.area / 1e6; area = dong_gdf.set_index("Dong")["area_km2"]

for y, Yr in Y.items():
    r0 = Yr.reach("도서관"); C0 = Yr.cov(r0); cand = Yr.candidates("도서관"); pop = Yr.pop
    ud = Yr.units["동"]
    def evalc(c):
        g = (pop * c).sum() - (pop * r0).sum()
        Cd, dd = Yr.unit_cov(ud, c); Cd0, _ = Yr.unit_cov(ud, r0); newg = c & ~r0
        return {"gain": g, "dong_below": int(((Cd < C0) & (dd > 0)).sum()), "dong_p10": np.quantile(Cd[dd > 0], .1),
                "dong_p25": np.quantile(Cd[dd > 0], .25), "vuln_share": (pop[newg] * (Cd0[ud][newg] < C0)).sum() / max(pop[newg].sum(), 1)}
    p0, _, _ = Yr.place(r0, None, 0, K, cand); c0 = Yr.cov_after(r0, p0, K)
    base = evalc(c0); rows.append({"year": y, "rule": "P0", "level": "-", **base, "Reff": 1.0})
    # (2) P0 이 남기는 동의 성격
    Cd0, dd = Yr.unit_cov(ud, r0); Cd1, _ = Yr.unit_cov(ud, c0)
    dong_codes = pd.factorize(Yr.M.dong)[1]
    D = pd.DataFrame({"Dong": dong_codes, "pop": dd, "C0": Cd0, "C_P0": Cd1})
    D["dens"] = D["pop"] / area.reindex(D.Dong).to_numpy()
    below0 = D[(D.C0 < C0) & (D["pop"] > 0)]
    lifted = below0[below0.C_P0 >= C0]; left = below0[below0.C_P0 < C0]
    improved = below0[below0.C_P0 - below0.C0 > 0.05]; untouched = below0[below0.C_P0 - below0.C0 <= 0.001]
    for nm, g in (("기준 미달 동 전체", below0), ("P0 후 충족", lifted), ("P0 후 미달 잔존", left), ("P0 로 5%p 이상 개선", improved), ("P0 가 손대지 않음", untouched)):
        prof.append({"year": y, "집단": nm, "n": len(g), "인구중위": g["pop"].median(), "밀도중위(명/km2)": g.dens.median(), "C0중위": g.C0.median(),
                     "인구합": g["pop"].sum()})
    # (1) maximin
    for lv in ("동", "공식LZ", "Leiden", "구"):
        u = Yr.units[lv]; den = np.bincount(u, pop); valid = den > 0
        cnum = np.bincount(u, pop * r0, minlength=len(den)); cov = r0.copy(); picks = []
        for step in range(K):
            Cu = np.divide(cnum, den, out=np.full_like(cnum, np.inf), where=valid)
            worst = np.argmin(Cu); best, bkey = None, (-1, -1)
            for j in cand:
                idx = Yr.cover_of(j); new = idx[~cov[idx]]
                if len(new) == 0: continue
                gw = pop[new[u[new] == worst]].sum(); g = pop[new].sum()
                key = (gw, g)
                if key > bkey: best, bkey = j, key
            if bkey[0] <= 0:   # 최악 단위를 올릴 후보가 없으면(후보 없음) 그 단위 제외하고 계속
                valid[worst] = False; den_tmp = None
                Cu = np.divide(cnum, den, out=np.full_like(cnum, np.inf), where=valid)
                continue
            idx = Yr.cover_of(best); new = idx[~cov[idx]]; cov[new] = True
            cnum += np.bincount(u[new], pop[new], minlength=len(den)); picks.append(best)
        e = evalc(cov); rows.append({"year": y, "rule": "maximin", "level": lv, **e, "Reff": e["gain"] / base["gain"]})
        print(y, lv, f"{time.time()-t0:.0f}s", flush=True)
R = pd.DataFrame(rows).round(3); R.to_csv(OUT / "exp_d_maximin.csv", index=False, encoding="utf-8-sig")
PF = pd.DataFrame(prof).round(3); PF.to_csv(OUT / "exp_d_profile.csv", index=False, encoding="utf-8-sig")
s = "## maximin\n" + md(R, "{}") + "\n\n## P0 가 남기는 동\n" + md(PF, "{}")
print(s); open(OUT / "exp_d_summary.md", "w", encoding="utf-8").write(s)
