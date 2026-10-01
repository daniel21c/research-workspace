# -*- coding: utf-8 -*-
"""설계 4판 보고용 그림 2장 (2026-10-02).
그림 A  6분야 묶음 완결 비율의 생활권 지도(2025): 배치 전 / 격자 총량 최대(정수계획) / 생활권 최저선 5%(exp20). 0명 생활권은 진한 색.
그림 B  같은 추가량에서 규칙별로 남는 생활권 — (왼) 시설 7종 최저선 미달 생활권 수(표4.1-10), (오) 6분야 묶음 0명 생활권 수(저장 해 + exp20).
색: 파랑 #2a78d6, 주황 #eb6834, 청록 #1baf7a, 노랑 #eda100, 회색 #52514e."""
import json
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt, geopandas as gpd
from matplotlib import font_manager
from matplotlib.colors import ListedColormap, BoundaryNorm
from bundlelib import Ctx, State
from r1lib import OUT, X
for f in ("Malgun Gothic", "NanumGothic"):
    if any(f == x.name for x in font_manager.fontManager.ttflist): plt.rcParams["font.family"] = f; break
plt.rcParams["axes.unicode_minus"] = False
BL, OR, AQ, YE, GR, LG = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#52514e", "#e6e6e3"
def clean(ax): ax.grid(color=LG, linewidth=0.6, axis="x"); ax.spines[["top", "right"]].set_visible(False)

Ys = {}; ctx = {}
for y in ("2020", "2025"):
    ctx[y] = Ctx("seoul", y, years=Ys); Ys = ctx[y].Y
def lz_share(c, picks):
    st = State(c); st.B = {s: 10 ** 6 for s in c.SUB}
    for s, js in (picks or {}).items():
        for j in js: st.apply(int(j), [s])
    comp = (st.cnt == c.NC) & c.popped
    lz = c.Yr.M.lz.to_numpy(); df = pd.DataFrame({"lz": lz, "p": c.pop, "c": c.pop * comp}).groupby("lz").sum()
    return (df.c / df.p).rename("share")

# 그림 A
y = "2025"; c = ctx[y]
mip = json.load(open(OUT / f"exp16_milp_picks_seoul_{y}.json", encoding="utf-8"))["MIP"]["picks"]
flo = json.load(open(OUT / f"exp20_picks_{y}_공식LZ_long_0.05.json", encoding="utf-8"))["picks"]
panels = [("배치 전", None), ("격자 총량 최대(정수계획)", mip), ("생활권 최저선 5%(정수계획)", flo)]
lzg = gpd.read_file(X.C.DATA_DIR / "seoul_official_livingzone_116.gpkg", layer="epsg5179")
cmap = ListedColormap(["#7a1f12", "#f0a080", "#f6d7c3", "#cfe0f5", "#2a78d6"]); norm = BoundaryNorm([-1e-9, 1e-9, 0.05, 0.10, 0.25, 1.0], cmap.N)
fig, axes = plt.subplots(1, 3, figsize=(16, 6.2))
for ax, (title, picks) in zip(axes, panels):
    sh = lz_share(c, picks); g = lzg.merge(sh, left_on="life_zone_id", right_index=True, how="left")
    g.plot(column="share", cmap=cmap, norm=norm, ax=ax, edgecolor="white", linewidth=0.4)
    tot = (c.pop * 0).sum()
    ax.set_axis_off(); ax.set_title(f"{title}\n0명 생활권 {int((sh <= 0).sum())}개 · 5% 미만 {int((sh < 0.05).sum())}개", fontsize=11)
from matplotlib.patches import Patch
fig.legend(handles=[Patch(color=cmap(i), label=l) for i, l in enumerate(["0명", "0~5%", "5~10%", "10~25%", "25% 이상"])], loc="lower center", ncol=5, frameon=False, fontsize=10, title="6분야를 모두 걸어서 10분 안에 쓰는 주민 비율")
fig.suptitle("그림 A  격자로 가장 잘 놓아도 빈 생활권이 남고, 생활권 최저선을 걸어야 사라진다 (2025, 같은 추가량)", fontsize=12)
fig.tight_layout(rect=(0, 0.08, 1, 0.93)); fig.savefig(OUT / "그림_필요성A_생활권지도_2025.png", dpi=200); plt.close(fig)

# 그림 B
fig, axes = plt.subplots(1, 2, figsize=(15, 5.4))
pol = [("P0", "격자 효율", GR), ("PG1", "격자 취약 가중", YE), ("PL_구", "자치구 최저선", OR), ("PL_공식", "생활권 최저선", BL)]
fac = ["도서관", "국공립유치원10분", "공공문화시설", "국공립어린이집5분", "주민센터", "청소년수련시설"]
fl = {"도서관": "도서관", "국공립유치원10분": "유치원", "공공문화시설": "공공문화", "국공립어린이집5분": "어린이집", "주민센터": "주민센터", "청소년수련시설": "청소년수련"}
D = pd.read_csv(OUT / "표4.1-10_정책비교_2025.csv").groupby(["시설", "정책"])["공식_미달수"].median()
ax = axes[0]; w = 0.2; xs = np.arange(len(fac))
for i, (k, lab, col) in enumerate(pol):
    v = [D.get((f, k), np.nan) for f in fac]; ax.bar(xs + (i - 1.5) * w, v, w, color=col, label=lab)
    for xx, vv in zip(xs + (i - 1.5) * w, v):
        if vv == 0: ax.text(xx, 0.25, "0", ha="center", va="bottom", fontsize=9, color=col, fontweight="bold")
ax.set_xticks(xs); ax.set_xticklabels([fl[f] for f in fac]); ax.set_ylabel("최저선 미달 생활권 수 (116개 중)"); ax.legend(frameon=False, fontsize=9); clean(ax)
ax.set_title("시설 하나씩 (2025): 생활권 최저선만 미달을 0으로 만든다", fontsize=10)
T = pd.read_csv(OUT / "표4.1-23_권역최저선_2025.csv"); T.loc[T.단위 == "공식LZ_long", "단위"] = "공식LZ*"
def z(u, t): r = T[(T.단위 == u) & (T.τ == t)]; return float(r["공식LZ_0%권역"].median()) if len(r) else np.nan
rnd = T[T.단위.str.startswith("rand116") & (T.τ == 0.05)]["공식LZ_0%권역"]
rows = [("배치 전", 38, GR), ("격자 총량 최대", 14, GR), ("격자 취약 가중(P=2)", 19, YE), ("자치구 최저선 5%", z("구", 0.05), OR), ("행정동 최저선 5%", z("동", 0.05), OR),
        ("무작위 116 최저선 5%", float(rnd.median()), AQ), ("Leiden 116 최저선 5%", z("Leiden", 0.05), AQ), ("생활권 최저선 5%", z("공식LZ*", 0.05), BL)]
ax = axes[1]; ys = np.arange(len(rows))
ax.barh(ys, [r[1] for r in rows], color=[r[2] for r in rows])
for yy, r in zip(ys, rows): ax.text(r[1] + 0.4, yy, f"{r[1]:.0f}", va="center", fontsize=9)
ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows]); ax.invert_yaxis(); ax.set_xlabel("6분야를 모두 쓰는 주민이 0명인 생활권 수 (116개 중)"); clean(ax)
ax.set_title("6분야 묶음 (2025): 생활권 규모에 걸어야 빈 생활권이 준다", fontsize=10)
fig.suptitle("그림 B  격자는 사람을 채우지만 지역을 채우지 못한다: 같은 추가량에서 규칙별로 남는 빈 생활권", fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.92)); fig.savefig(OUT / "그림_필요성B_규칙별빈생활권_2025.png", dpi=200); plt.close(fig)
print("done")
