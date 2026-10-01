# -*- coding: utf-8 -*-
"""S5-1 그림 생성: 저장된 결과표(CSV)와 매핑에서 그림 5개를 새로 만든다. 수치는 모두 CSV에서 읽는다.
F1 절차 흐름도 / F2 공식·Leiden·Louvain 지도 / F3 Louvain 대 Leiden(구별 Q, 결과가 다시 나오는 정도) / F4 구별 진단(IoU·G·불일치 D) / F5 IoU와 이동 지표의 관계

2026-10-02 개정(JTG·Elsevier 그림 규정 반영):
- 실제 인쇄 폭(본문 폭 16 cm)으로 그려 글자가 인쇄 크기에서 7 pt 이상이 되게 한다.
- 글꼴은 Arial(영문·숫자), 한글은 맑은 고딕으로 대체 표시한다.
- 해상도: 선 위주 그림 1000 dpi, 색을 채운 지도 500 dpi. 같은 그림을 벡터 PDF로도 저장한다.
- 지도에는 방위표, 축척 막대, 범례를 넣는다. 그림 안에는 제목을 넣지 않고(캡션에 둠), 패널은 (a), (b)로 표시한다.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

PKG = Path(__file__).resolve().parents[1]
RES = PKG / "results"
FIG = RES / "figures"
OLD = RES / "reused_20260929"
INP = PKG / "inputs"
W = 16 / 2.54                      # 본문 폭 16 cm (인치)
plt.rcParams.update({"font.family": ["Arial", "Malgun Gothic"], "axes.unicode_minus": True, "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
                     "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
                     "ytick.major.width": 0.6, "pdf.fonttype": 42, "figure.dpi": 100,
                     "mathtext.fontset": "custom", "mathtext.rm": "Arial", "mathtext.it": "Arial:italic", "mathtext.bf": "Arial:bold"})   # 기호 표기(본문과 같게)
INK, MUTE, BLUE, ORANGE, GREEN, GRAY = "#222222", "#6b6b6b", "#2f5d8a", "#c8641e", "#3b7a57", "#bdbdbd"


def save(fig, name, dpi):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight", facecolor="white")     # 벡터본(글꼴 포함)
    plt.close(fig)


def panel(ax, label):
    ax.text(0.0, 1.02, label, transform=ax.transAxes, ha="left", va="bottom", fontsize=8.5, fontweight="bold")


def lines_text(ax, xc, yc, lines, fs=7.5, lh=2.8):
    """여러 줄 글자를 한 줄씩 그린다. 한글과 수식 표기($..$)를 한 줄에 섞지 않는다."""
    import re
    top = yc + lh * (len(lines) - 1) / 2
    for i, ln in enumerate(lines):
        assert not ("$" in ln and re.search(r"[가-힣]", ln)), ln
        ax.text(xc, top - i * lh, ln, ha="center", va="center", fontsize=fs, color=INK)


def f1_flow():
    fig, ax = plt.subplots(figsize=(W, 2.9)); ax.set_xlim(0, 100); ax.set_ylim(0, 44); ax.axis("off")
    top = [(["OD 자료", "2025년 1월", "(도착 9~20시,", "HW·WH 제외)"], 1), (["구별 연결망", "(점: 동,", "선: 두 동 사이", "통행량)"], 21),
           (["해상도 250가지", "× 3,000번", "실행"], 41), (["합의 권역", "(같은 권역에", "묶인 비율", "0.5 이상)"], 61),
           (["해상도 고르기", "(목표 권역 수,", r"$\max\ Q$)"], 81)]
    for t, x in top:
        ax.add_patch(FancyBboxPatch((x, 24), 17, 16, boxstyle="round,pad=0.3,rounding_size=1.0", fc="#f1f4f8", ec=BLUE, lw=0.8))
        lines_text(ax, x + 8.5, 32, t)
    for i in range(4):
        ax.add_patch(FancyArrowPatch((top[i][1] + 17.5, 32), (top[i + 1][1] - 0.5, 32), arrowstyle="-|>", mutation_scale=8, color=MUTE, lw=0.8))
    ax.add_patch(FancyArrowPatch((89.5, 23.5), (89.5, 15.5), arrowstyle="-|>", mutation_scale=8, color=MUTE, lw=0.8))
    bot = [(["평가 지표", "$Q$, IFR,", "공간 연속성"], 3), (["공식 생활권과의", "겹침(IoU, ARI)"], 28),
           (["IFR 차이와 불일치", r"($G$, $D$)"], 53), (["후속 조사", "후보 고르기"], 79)]
    for t, x in bot:
        ax.add_patch(FancyBboxPatch((x, 2), 19, 12.5, boxstyle="round,pad=0.3,rounding_size=1.0", fc="#fbf3ec", ec=ORANGE, lw=0.8))
        lines_text(ax, x + 9.5, 8.25, t)
    for (_, xa), (_, xb) in zip(bot[:-1], bot[1:]):
        ax.add_patch(FancyArrowPatch((xb - 0.5, 8.25), (xa + 19.5, 8.25), arrowstyle="<|-", mutation_scale=8, color=MUTE, lw=0.8))
    ax.text(0.5, 42.5, "(a) 이동 권역 만들기", fontsize=8, color=BLUE, fontweight="bold"); ax.text(0.5, 17.2, "(b) 공식 생활권 점검", fontsize=8, color=ORANGE, fontweight="bold")
    save(fig, "F1_procedure", 1000)


def comm_polygons(dong, mapping, col):
    m = mapping[["Dong", col]].rename(columns={col: "cid"})
    g = dong.merge(m, on="Dong")
    g["rank"] = g.groupby("Ku")["cid"].transform(lambda s: pd.factorize(s)[0])
    return g.dissolve(by="cid", aggfunc={"Ku": "first", "rank": "first"}).reset_index()


def north_and_scale(ax, gdf, km=5):
    x0, y0, x1, y1 = gdf.total_bounds
    w, h = x1 - x0, y1 - y0
    bx, by = x0 + 0.02 * w, y0 + 0.02 * h                       # 축척 막대(왼쪽 아래, 지도 밖 여백)
    ax.plot([bx, bx + km * 1000], [by, by], color=INK, lw=1.4, solid_capstyle="butt")
    ax.plot([bx, bx], [by - 0.012 * h, by + 0.012 * h], color=INK, lw=0.8); ax.plot([bx + km * 1000] * 2, [by - 0.012 * h, by + 0.012 * h], color=INK, lw=0.8)
    ax.text(bx + km * 500, by + 0.03 * h, f"{km} km", ha="center", va="bottom", fontsize=7)
    nx_, ny_ = x0 + 0.06 * w, y0 + 0.78 * h                     # 방위표(왼쪽 위)
    ax.annotate("", xy=(nx_, ny_ + 0.12 * h), xytext=(nx_, ny_), arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.9, mutation_scale=8))
    ax.text(nx_, ny_ + 0.14 * h, "N", ha="center", va="bottom", fontsize=7.5, fontweight="bold")


def f2_maps():
    dong = gpd.read_file(INP / "seoul_dong_424_dissolved.gpkg", layer="epsg5179")[["Dong", "Ku", "life_zone_id", "geometry"]]
    dong["Dong"] = dong["Dong"].astype(int); dong["Ku"] = dong["Ku"].astype(int)
    leiden = pd.read_csv(INP / "dong_to_leiden_2025_mapping_424.csv", encoding="utf-8-sig")
    louv = pd.read_csv(PKG / "output" / "louvain" / "2025" / "metrics" / "louvain_mapping_2025.csv", encoding="utf-8-sig")
    off = dong.rename(columns={"life_zone_id": "cid"})[["Dong", "cid"]]
    parts = [("(a) 공식 생활권", comm_polygons(dong, off, "cid")), ("(b) Leiden 권역", comm_polygons(dong, leiden, "global_community_id")),
             ("(c) Louvain 권역", comm_polygons(dong, louv, "global_community_id"))]
    gu = dong.dissolve(by="Ku").reset_index()
    cmap = plt.get_cmap("Set3")
    fig, axes = plt.subplots(1, 3, figsize=(W, 2.2))
    for ax, (t, g) in zip(axes, parts):
        g.plot(ax=ax, color=[cmap(int(r) % 12) for r in g["rank"]], edgecolor="#5a5a5a", linewidth=0.3)
        gu.boundary.plot(ax=ax, color="#111111", linewidth=0.8)
        ax.set_axis_off(); panel(ax, t)
    north_and_scale(axes[0], gu)
    handles = [Line2D([0], [0], color="#111111", lw=0.8, label="자치구 경계"), Line2D([0], [0], color="#5a5a5a", lw=0.3, label="권역 경계")]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.0))
    fig.subplots_adjust(wspace=0.03, bottom=0.12, top=0.9)
    save(fig, "F2_maps_2025", 500)


def f3_algorithm():
    L = pd.read_csv(RES / "tables" / "L1_algorithm_comparison_2025.csv").sort_values("leiden_minus_louvain_q").reset_index(drop=True)
    fig, (a, b) = plt.subplots(1, 2, figsize=(W, 4.3), gridspec_kw={"width_ratios": [1.15, 1]})
    y = np.arange(len(L))
    a.hlines(y, L["louvain_q"], L["leiden_q"], color=GRAY, lw=1.0, zorder=1)
    a.scatter(L["official_q"], y, s=12, facecolors="none", edgecolors=MUTE, lw=0.7, zorder=2)
    a.scatter(L["louvain_q"], y, s=16, color=ORANGE, zorder=3)
    a.scatter(L["leiden_q"], y, s=16, color=BLUE, zorder=3)
    a.set_yticks(y); a.set_yticklabels(L["ku_name"]); a.set_xlabel("Modularity, $Q$"); a.grid(axis="x", color="#e6e6e6", lw=0.5); panel(a, "(a)")
    h = 0.38
    b.barh(y + h / 2, L["leiden_modal_share"] * 100, height=h, color=BLUE)
    b.barh(y - h / 2, L["louvain_modal_share"] * 100, height=h, color=ORANGE)
    for i, r in L.iterrows():
        if r["louvain_stability_ari_min"] < 1 - 1e-12:
            b.text(101.5, i - h / 2, f"ARI {r['louvain_stability_ari_min']:.2f}", va="center", fontsize=7, color=ORANGE)
    b.set_yticks(y); b.set_yticklabels([]); b.set_xlim(0, 132); b.set_xticks([0, 25, 50, 75, 100])
    b.set_xlabel("가장 자주 나온 결과의 비율 (%)"); b.grid(axis="x", color="#e6e6e6", lw=0.5); panel(b, "(b)")
    handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor=BLUE, markersize=6, label="Leiden"),
               Line2D([0], [0], marker="o", color="w", markerfacecolor=ORANGE, markersize=6, label="Louvain"),
               Line2D([0], [0], marker="o", color="w", markerfacecolor="white", markeredgecolor=MUTE, markersize=5, label="공식 생활권 (a에만 표시)")]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.subplots_adjust(wspace=0.05, bottom=0.14)
    save(fig, "F3_algorithm_comparison", 1000)


def f4_diagnostics():
    T = pd.read_csv(OLD / "T3_district_2025.csv").sort_values("iou_1to1").reset_index(drop=True)
    fig, axes = plt.subplots(1, 3, figsize=(W, 4.3), sharey=True)
    y = np.arange(len(T))
    axes[0].barh(y, T["iou_1to1"], color=BLUE, height=0.66); axes[0].set_xlim(0, 1.05); axes[0].set_xlabel("IoU")
    axes[1].barh(y, T["g"] * 100, color=[GREEN if v >= 0 else ORANGE for v in T["g"]], height=0.66); axes[1].axvline(0, color=INK, lw=0.6); axes[1].set_xlabel("$G$ (%p)")
    axes[2].barh(y, T["d_flow"] * 100, color="#7a7a7a", height=0.66); axes[2].set_xlabel(r"$D$ (%)")
    axes[0].set_yticks(y); axes[0].set_yticklabels(T["ku_name"])
    for ax, lab in zip(axes, ("(a)", "(b)", "(c)")):
        ax.grid(axis="x", color="#e6e6e6", lw=0.5); ax.set_axisbelow(True); panel(ax, lab)
    fig.subplots_adjust(wspace=0.08)
    save(fig, "F4_district_diagnostics", 1000)


def f5_relations():
    T = pd.read_csv(OLD / "T3_district_2025.csv"); C = pd.read_csv(OLD / "T8_correlations_2025.csv")
    fig, axes = plt.subplots(1, 3, figsize=(W, 2.3))
    for ax, (col, lab, scale), pl in zip(axes, [("g", r"$G$ (%p)", 100), ("delta_q", r"$\Delta Q$", 1), ("d_flow", r"$D$ (%)", 100)], ("(a)", "(b)", "(c)")):
        ax.scatter(T["iou_1to1"], T[col] * scale, s=12, color=BLUE, alpha=0.9, lw=0)
        r = C[(C.x == "iou_1to1") & (C.y == col)].iloc[0]
        mn = lambda v: f"{v:.2f}".replace("-", "−")  # 축 눈금과 같은 마이너스 기호
        ax.text(0.98, 0.97, f"ρ = {mn(r['rho'])}\n[{mn(r['lo'])}, {mn(r['hi'])}]", transform=ax.transAxes, ha="right", va="top", fontsize=7)
        ax.set_xlabel("IoU"); ax.set_ylabel(lab); ax.grid(color="#e6e6e6", lw=0.5); panel(ax, pl)
        if col in ("g", "delta_q"):
            ax.axhline(0, color=INK, lw=0.5)
    fig.subplots_adjust(wspace=0.45)
    save(fig, "F5_iou_relations", 1000)


if __name__ == "__main__":
    for old in FIG.glob("*"):
        old.unlink()
    f1_flow(); f2_maps(); f3_algorithm(); f4_diagnostics(); f5_relations()
    print("그림 생성:", sorted(p.name for p in FIG.glob("*")))
