# -*- coding: utf-8 -*-
"""실험 2: 은폐 — 어느 단위로 보면 취약지가 보이지 않는가.
H(τ) = 하한 τ를 충족한 단위 안에 사는 미도달 인구 / 전체 미도달 인구. τ 곡선(서울 평균 × 0.5~1.5, 11점)과 AUC,
τ_main(행정동 중위 60%)에서의 H와 FGT0, 도달 여부 분산의 단위 내 몫(인구가중 분산 분해 = Theil 대신 이진변수용).
시설: 설정근거 3절 진단 목록(DIAG_SETS). 두 해. 지도: 도서관, 구 충족(τ_main) vs 격자 미도달.
사용: python exp2_concealment.py"""
import time, json
import numpy as np, pandas as pd
from r1lib import Year, OUT, md, DIAG_SETS, X

MS = np.linspace(0.5, 1.5, 11)
LEV = ["동", "공식LZ", "Leiden", "구"]
rows, curves = [], []; t0 = time.time()
def wmedian(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return x[o][np.searchsorted(cw, cw[-1] / 2)]
for year in ("2020", "2025"):
    Yr = Year(year); pop = Yr.pop
    for f in DIAG_SETS:
        r = Yr.reach(f); C = Yr.cov(r)
        if (~r & Yr.popped).sum() == 0: continue
        Cd, dd = Yr.unit_cov(Yr.units["동"], r); tau_main = 0.6 * wmedian(Cd[dd > 0], dd[dd > 0])
        for lv in LEV:
            u = Yr.units[lv]
            hc = Yr.H_curve(u, r, C, MS)
            Cu, den = Yr.unit_cov(u, r); v = den > 0; below = v & (Cu < tau_main)
            row = {"year": year, "시설": f, "서울C": C, "τ_main": tau_main, "단위": lv,
                   "H_AUC(τ0.5~1.5×평균)": hc.mean(), "H(τ_main)": Yr.H(u, r, tau_main), "H(τ=평균)": hc[5],
                   "FGT0(τ_main)": den[below].sum() / den[v].sum(), "소외단위수": int(below.sum()), "단위수": int(v.sum()),
                   "도달분산_단위내몫": Yr.within_share(u, r)}
            rows.append(row)
            for m, h in zip(MS, hc): curves.append({"year": year, "시설": f, "단위": lv, "τ배수": round(m, 2), "H": h})
        print(year, f, f"{time.time()-t0:.0f}s", flush=True)
    # 지도 (도서관, τ_main): 구 충족 여부 + 격자 미도달
    if year == "2020":
        try:
            import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, geopandas as gpd
            r = Yr.reach("도서관"); Cd, dd = Yr.unit_cov(Yr.units["동"], r); tau_main = 0.6 * wmedian(Cd[dd > 0], dd[dd > 0])
            ku_gdf = X.load_dong().dissolve(by="Ku").reset_index()
            Cu, den = Yr.unit_cov(Yr.units["구"], r); ku_codes = pd.factorize(Yr.M.ku)[1]
            kc = pd.Series(Cu, index=ku_codes); ku_gdf["C"] = ku_gdf.Ku.map(kc); ku_gdf["ok"] = ku_gdf.C >= tau_main
            lz_gdf = gpd.read_file(X.C.DATA_DIR / "seoul_official_livingzone_116.gpkg")
            fig, ax = plt.subplots(figsize=(9, 8)); ku_gdf.plot(ax=ax, color=np.where(ku_gdf.ok, "#dfe8dc", "#f3d4d4"), edgecolor="k", linewidth=0.8)
            lz_gdf.boundary.plot(ax=ax, color="gray", linewidth=0.3)
            m = (~r) & Yr.popped; ax.scatter(Yr.M.x_c[m], Yr.M.y_c[m], s=0.3, c="#b00020")
            ax.set_axis_off(); ax.set_title(f"library 15min: uncovered grids (red) vs gu >= tau {tau_main:.2f} (green)")
            fig.savefig(OUT / "그림4.1-2_은폐지도_2020_도서관.png", dpi=200, bbox_inches="tight"); plt.close(fig)
        except Exception as e:
            print("map skipped:", repr(e))
D = pd.DataFrame(rows).round(4); D.to_csv(OUT / "표4.1-2_은폐_H.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(curves).round(4).to_csv(OUT / "표4.1-2_은폐_H곡선.csv", index=False, encoding="utf-8-sig")
piv = D.pivot_table(index=["year", "시설"], columns="단위", values=["H_AUC(τ0.5~1.5×평균)", "H(τ_main)", "FGT0(τ_main)", "도달분산_단위내몫"])
out = "# 표 4.1-2 은폐(H)와 FGT0 — 단위별\n\n"
for m in ["H_AUC(τ0.5~1.5×평균)", "H(τ_main)", "FGT0(τ_main)", "도달분산_단위내몫"]:
    out += f"\n## {m}\n\n" + md(piv[m][LEV].round(3).reset_index(), "{}") + "\n"
open(OUT / "표4.1-2_은폐_H.md", "w", encoding="utf-8").write(out); print(out); print("done", f"{time.time()-t0:.0f}s")
