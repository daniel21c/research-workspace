# -*- coding: utf-8 -*-
"""실험 8: 자치구 사례 지도(중간발표용). 서울 전체 배치 결과 가운데 두 구를 골라
기준 상태(도서관 미도달 격자·기존 도서관), P0(도시 전체 효율)와 P1 공식 생활권 보장이 고른 신규 입지, 생활권 경계를 한 장에 그린다.
구 선택 규칙(사전 고정): (1) 기준 상태에서 소외 생활권(τ_main 미만)이 가장 많은 구, (2) P0와 P1 공식의 입지가 가장 많이 다른 구. 두 구가 같으면 다음 순위.
사용: python exp8_case_gu.py [연도=2020]"""
import sys, json
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt, geopandas as gpd
from matplotlib import font_manager
from r1lib import Year, OUT, X, md
for f in ("Malgun Gothic", "NanumGothic"):
    if any(f == x.name for x in font_manager.fontManager.ttflist): plt.rcParams["font.family"] = f; break
plt.rcParams["axes.unicode_minus"] = False
year = sys.argv[1] if len(sys.argv) > 1 else "2020"; K = 32
Yr = Year(year); pop = Yr.pop; r0 = Yr.reach("도서관"); cand = Yr.candidates("도서관")
def wmedian(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return x[o][np.searchsorted(cw, cw[-1] / 2)]
Cd, dd = Yr.unit_cov(Yr.units["동"], r0); tau = 0.6 * wmedian(Cd[dd > 0], dd[dd > 0])
def _load_json(pth):
    for enc in ("utf-8", "cp949"):
        try: return json.load(open(pth, encoding=enc))
        except UnicodeDecodeError: pass
    raise
picks = _load_json(OUT / "exp5_picks.json")[year]
p0, p1 = picks["P0"], picks["P1 공식LZ"]
ulz = Yr.units["공식LZ"]; uku = Yr.units["구"]; ku_codes = pd.factorize(Yr.M.ku)[1]; lz_codes = pd.factorize(Yr.M.lz)[1]
Cl, dl = Yr.unit_cov(ulz, r0); below = (dl > 0) & (Cl < tau)
lz_ku = pd.Series(Yr.M.ku.to_numpy(), index=ulz).groupby(level=0).first()   # 생활권 → 구
n_below_ku = pd.Series(below).groupby(lz_ku.reindex(range(len(Cl))).to_numpy()).sum()
p0a, p1a = np.asarray(p0), np.asarray(p1)
diff_ku = pd.Series({kc: len(set(p0a[uku[p0a] == i].tolist()) ^ set(p1a[uku[p1a] == i].tolist())) for i, kc in enumerate(ku_codes)})   # 감사 F7-3 교정: 격자 ID 대칭차
ku_name = Yr.M.groupby("ku").size().index  # placeholder
names = X.load_dong().groupby("Ku")["ku_name"].first() if "ku_name" in X.load_dong().columns else None
sel = [int(n_below_ku.sort_values(ascending=False).index[0])]
for kc in diff_ku.sort_values(ascending=False).index:
    if int(kc) not in sel: sel.append(int(kc)); break
dong = X.load_dong(); lz = gpd.read_file(X.C.DATA_DIR / "seoul_official_livingzone_116.gpkg")
rows = []
fig, axes = plt.subplots(1, 2, figsize=(14, 6.5))
for ax, kc in zip(axes, sel):
    g = dong[dong.Ku == kc]; kname = g.ku_name.iloc[0] if "ku_name" in g else str(kc)
    minx, miny, maxx, maxy = g.total_bounds
    g.boundary.plot(ax=ax, color="#bdbdb8", linewidth=0.4)
    lzk = lz[lz.intersects(g.union_all())] if hasattr(g, "union_all") else lz[lz.intersects(g.unary_union)]
    lzk.boundary.plot(ax=ax, color="#2a78d6", linewidth=1.2)
    inku = (Yr.M.ku.to_numpy() == kc)
    m = inku & (~r0) & Yr.popped; ax.scatter(Yr.M.x_c[m], Yr.M.y_c[m], s=1.2, c="#e34948", label="도서관 15분 미도달 격자(인구>0)")
    lib = Yr.fac["도서관"][0]; lib = lib[inku[lib]]; ax.scatter(Yr.M.x_c[lib], Yr.M.y_c[lib], s=40, marker="s", c="#52514e", label="기존 도서관")
    j0 = [j for j in p0 if inku[j]]; j1 = [j for j in p1 if inku[j]]
    ax.scatter(Yr.M.x_c[j0], Yr.M.y_c[j0], s=140, marker="o", facecolors="none", edgecolors="#1baf7a", linewidths=2, label=f"P0 도시전체효율 신규({len(j0)})")
    ax.scatter(Yr.M.x_c[j1], Yr.M.y_c[j1], s=140, marker="^", facecolors="none", edgecolors="#eb6834", linewidths=2, label=f"P1 생활권 보장 신규({len(j1)})")
    # 소외 생활권 음영
    for i in np.where(below)[0]:
        if lz_ku.get(i) == kc:
            z = lz[lz.life_zone_id == lz_codes[i]] if "life_zone_id" in lz else None
            if z is not None and not z.empty: z.plot(ax=ax, color="#eb6834", alpha=0.12, edgecolor="none")
    ax.set_xlim(minx - 300, maxx + 300); ax.set_ylim(miny - 300, maxy + 300); ax.set_axis_off()
    ax.set_title(f"{kname} ({year}) — 소외 생활권 {int(n_below_ku.get(kc, 0))}개 음영, τ={tau:.2f}", fontsize=11)
    rows.append({"구": kname, "코드": kc, "소외생활권수(기준)": int(n_below_ku.get(kc, 0)), "P0신규": len(j0), "P1공식신규": len(j1),
                 "미도달인구": float(pop[m].sum()), "구인구": float(pop[inku].sum())})
h, l = axes[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=4, frameon=False, fontsize=9)
fig.suptitle("그림 4.1-C  자치구 사례: 도시 전체 효율(P0) vs 생활권 보장(P1)의 신규 도서관 입지", fontsize=12)
fig.tight_layout(rect=(0, 0.06, 1, 0.95)); fig.savefig(OUT / f"그림4.1-C_자치구사례_{year}.png", dpi=200); plt.close(fig)
R = pd.DataFrame(rows); R.to_csv(OUT / f"표4.1-8_자치구사례_{year}.csv", index=False, encoding="utf-8-sig"); print(md(R.round(0), "{}"))
