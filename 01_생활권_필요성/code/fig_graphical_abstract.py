# -*- coding: utf-8 -*-
"""Graphical abstract for the Cities submission (2026-10-02). Uses saved solutions only (no new analysis):
exp16 MIP picks (grid bundle maximisation, 2025) and exp20 living-zone 5% picks (4 h run, 2025); gu/dong counts from 표4.1-23.
Output: manuscript/figures/GraphicalAbstract.png (≥ 1328 × 531 px; here 2656 × 1062) and .pdf"""
import json
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt, geopandas as gpd
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
from bundlelib import Ctx, State
from r1lib import OUT, X
plt.rcParams.update({"font.family": "Arial", "axes.unicode_minus": False, "font.size": 10})
DST = Path(__file__).parent.parent / "manuscript" / "figures"; DST.mkdir(parents=True, exist_ok=True)
GR, BL, OR = "#52514e", "#2a78d6", "#eb6834"
c = Ctx("seoul", "2025")
dong = X.load_dong(); gu = dong.dissolve(by="Ku").reset_index()
lz = gpd.read_file(X.C.DATA_DIR / "seoul_official_livingzone_116.gpkg", layer="epsg5179")

def lz_share(picks):
    st = State(c); st.B = {s: 10 ** 6 for s in c.SUB}
    for s, js in (picks or {}).items():
        for j in js: st.apply(int(j), [s])
    comp = (st.cnt == c.NC) & c.popped
    df = pd.DataFrame({"lz": c.Yr.M.lz.to_numpy(), "p": c.pop, "c": c.pop * comp}).groupby("lz").sum(); return (df.c / df.p).rename("share")

mip = json.load(open(OUT / "exp16_milp_picks_seoul_2025.json", encoding="utf-8"))["MIP"]["picks"]
flo = json.load(open(OUT / "exp20_picks_2025_공식LZ_long_0.05.json", encoding="utf-8"))["picks"]
T = pd.read_csv(OUT / "표4.1-23_권역최저선_2025.csv")
def z(u): return int(T[(T.단위 == u) & (T.τ == 0.05)]["공식LZ_0%권역"].iloc[0])
cmap = ListedColormap(["#7a1f12", "#f0a080", "#f6d7c3", "#cfe0f5", BL]); norm = BoundaryNorm([-1e-9, 1e-9, 0.05, 0.10, 0.25, 1.0], cmap.N)

fig = plt.figure(figsize=(13.28, 5.31))
fig.text(0.012, 0.93, "Why plan by living zones? Grids fill people, not places", fontsize=17, fontweight="bold", color=GR)
fig.text(0.012, 0.865, "Seoul, 116 living zones: residents who can walk to all six planned public services (park, library, senior leisure, youth & children, childcare, public sports) within 10 min, 2025",
         fontsize=10.5, color=GR)
panels = [("Before placement", None, "5.3% of residents complete"), ("Grid-optimised placement", mip, "24.2% complete"), ("Living-zone minimum standard", flo, "22.1% complete")]
for k, (title, picks, sub) in enumerate(panels):
    ax = fig.add_axes([0.005 + k * 0.2, 0.15, 0.19, 0.6])
    sh = lz_share(picks); g = lz.merge(sh, left_on="life_zone_id", right_index=True, how="left")
    g.plot(column="share", cmap=cmap, norm=norm, ax=ax, edgecolor="white", linewidth=0.3); gu.boundary.plot(ax=ax, color=GR, linewidth=0.4); ax.set_axis_off()
    n0 = int((sh <= 0).sum())
    ax.set_title(f"{title}\n{sub}", fontsize=11, color=GR, loc="center")
    ax.text(0.5, -0.07, f"{n0} empty living zones", transform=ax.transAxes, ha="center", fontsize=12, fontweight="bold", color="#7a1f12" if n0 > 5 else BL)
fig.legend(handles=[Patch(color=cmap(i), label=l) for i, l in enumerate(["0%", "0–5%", "5–10%", "10–25%", "≥25%"])], loc="lower left", bbox_to_anchor=(0.1, 0.0), ncol=5, frameon=False, fontsize=9.5,
           title="Share of residents completing the bundle", title_fontsize=9.5)
ax = fig.add_axes([0.765, 0.3, 0.215, 0.47])
rows = [("Grid-optimised", 14, GR), ("Gu minimum", z("구"), OR), ("Dong minimum", z("동"), OR), ("Living-zone minimum", z("공식LZ_long"), BL)]
ys = np.arange(len(rows)); ax.barh(ys, [r[1] for r in rows], color=[r[2] for r in rows], height=0.62)
for yy, (_, v, _c) in zip(ys, rows): ax.text(v + 0.4, yy, f"{v}", va="center", fontsize=12, fontweight="bold", color=GR)
ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows], fontsize=11); ax.invert_yaxis(); ax.set_xlim(0, 20)
ax.spines[["top", "right"]].set_visible(False); ax.set_xlabel("Empty living zones (no resident completes), 2025", fontsize=10)
ax.set_title("Same 381 facilities,\nminimum set by different units", fontsize=11.5, color=GR, loc="left")
fig.text(0.635, 0.025, "Gu minimum: met, yet its living zones stay empty.\nDong minimum: cannot be met with the facilities added.\nOnly a minimum at the living-zone scale fills places.", fontsize=10, color=GR)
for ext in ("png", "pdf"): fig.savefig(DST / f"GraphicalAbstract.{ext}", dpi=200)
print("done", [int(x) for x in fig.get_size_inches() * 200])
