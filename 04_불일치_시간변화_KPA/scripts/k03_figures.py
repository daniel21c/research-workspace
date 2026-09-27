# -*- coding: utf-8 -*-
"""
k03 — 그림 (연구설계 11.2 F4.4-1 ~ F4.4-6)

입력: output/tables/ (k01, k02 결과), 코어엔진 동 경계 gpkg
출력: output/figures/*.png (300dpi) + *.pdf

색 규칙 (두 경계는 언제나 같은 색): 공식 생활권 LZ = 청색 계열, 이동 기반 경계 LD = 주황 계열.
변화량(ΔD)은 파랑–회색–빨강의 양방향 척도, 0이 회색.
글자는 검정/회색만 쓰고 계열 색을 글자에 쓰지 않는다. 구 이름은 그림에서는 영문(폰트 호환), 표에서는 한글.
"""
from __future__ import annotations

import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager
import numpy as np
import pandas as pd

import config as C

# 한글 폰트가 있으면 쓴다(없으면 영문 라벨만 나온다)
for cand in ("Noto Sans CJK KR", "Noto Sans CJK JP", "NanumGothic", "Malgun Gothic", "Noto Serif CJK KR"):
    if any(f.name == cand for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": "#e5e5e5", "grid.linewidth": 0.6, "axes.edgecolor": "#888",
                     "axes.unicode_minus": False, "font.size": 9, "pdf.fonttype": 42})

COL_LZ, COL_LD = "#3B6EA8", "#D9782D"     # 두 계열 고정 색
COL_MUTED, COL_INK = "#9a9a9a", "#222222"
Y0, Y1 = C.Y0, C.Y1


def save(fig, name):
    fig.savefig(C.FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(C.FIG / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def load():
    ch = pd.read_csv(C.TAB / "t03_gu_change.csv", encoding="utf-8-sig")
    seoul = ch[ch.ku_code == "SEOUL"].iloc[0]
    ch = ch[ch.ku_code != "SEOUL"].copy(); ch["ku_code"] = ch.ku_code.astype(int)
    sel = pd.read_csv(C.TAB / "t06_selection.csv", encoding="utf-8-sig")
    nul = pd.read_csv(C.TAB / "t05_null_summary.csv", encoding="utf-8-sig")
    return ch.set_index("ku_code"), seoul, sel.set_index("ku_code"), nul.set_index("ku_code")


# F4.4-1 두 경계의 IFR, 2020→2025 (덤벨)
def fig1(ch, seoul):
    d = ch.sort_values(f"IFR_lz_{Y0}")
    y = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(6.5, 7.5))
    for i, (k, r) in enumerate(d.iterrows()):
        ax.plot([r[f"IFR_lz_{Y0}"], r[f"IFR_lz_{Y1}"]], [i + 0.15, i + 0.15], color=COL_LZ, lw=1.6, alpha=0.8)
        ax.plot([r[f"IFR_ld_{Y0}"], r[f"IFR_ld_{Y1}"]], [i - 0.15, i - 0.15], color=COL_LD, lw=1.6, alpha=0.8)
    ax.scatter(d[f"IFR_lz_{Y0}"], y + 0.15, s=18, facecolor="white", edgecolor=COL_LZ, zorder=3)
    ax.scatter(d[f"IFR_lz_{Y1}"], y + 0.15, s=22, color=COL_LZ, zorder=3)
    ax.scatter(d[f"IFR_ld_{Y0}"], y - 0.15, s=18, facecolor="white", edgecolor=COL_LD, zorder=3)
    ax.scatter(d[f"IFR_ld_{Y1}"], y - 0.15, s=22, color=COL_LD, zorder=3)
    ax.set_yticks(y); ax.set_yticklabels(d["ku_name"]); ax.set_xlabel("IFR (내부통행비율)")
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    h = [mpatches.Patch(color=COL_LZ, label="공식 생활권 LZ"), mpatches.Patch(color=COL_LD, label="이동 기반 경계 LD"),
         plt.Line2D([], [], marker="o", ls="", mfc="white", mec=COL_INK, label=Y0),
         plt.Line2D([], [], marker="o", ls="", color=COL_INK, label=Y1)]
    ax.legend(handles=h, loc="lower right", frameon=False, fontsize=8)
    ax.set_title(f"구별 IFR: {Y0}(빈 점) → {Y1}(찬 점). 서울 전체 LZ {seoul[f'IFR_lz_{Y0}']:.1%}→{seoul[f'IFR_lz_{Y1}']:.1%}, "
                 f"LD {seoul[f'IFR_ld_{Y0}']:.1%}→{seoul[f'IFR_ld_{Y1}']:.1%}", fontsize=8.5, loc="left")
    save(fig, "F4-4-1_ifr_dumbbell")


# F4.4-2 LD vs LZ IFR 산점도 (두 해)
def fig2(ch):
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.4), sharex=True, sharey=True)
    lo = min(ch[[f"IFR_lz_{Y0}", f"IFR_ld_{Y0}"]].min().min(), ch[[f"IFR_lz_{Y1}", f"IFR_ld_{Y1}"]].min().min()) - 0.02
    hi = max(ch[[f"IFR_lz_{Y1}", f"IFR_ld_{Y1}"]].max().max(), 0.5) + 0.02
    for ax, y in zip(axes, (Y0, Y1)):
        ax.plot([lo, hi], [lo, hi], color=COL_MUTED, lw=1, ls="--", zorder=1)
        ax.scatter(ch[f"IFR_lz_{y}"], ch[f"IFR_ld_{y}"], s=28, color=COL_INK, zorder=3)
        big = ch[(ch[f"G_{y}"].abs() >= 0.02)]
        for k, r in big.iterrows():
            ax.annotate(r.ku_name, (r[f"IFR_lz_{y}"], r[f"IFR_ld_{y}"]), fontsize=7, xytext=(4, 3),
                        textcoords="offset points", color="#444")
        ax.set_title(f"{y}", loc="left"); ax.set_xlabel("IFR (LZ)"); ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
        ax.set_aspect("equal")
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    axes[0].set_ylabel("IFR (LD)")
    fig.suptitle("구별 IFR: 이동 기반 경계(LD) vs 공식 생활권(LZ). 대각선 위 = G > 0 (|G| ≥ 2%p 구만 표기)", fontsize=8.5, x=0.02, ha="left")
    save(fig, "F4-4-2_scatter_ld_vs_lz")


# F4.4-3 사분면도: G_2020 vs G_2025, 점 크기 = D_2025, 색 = ΔD
def fig3(ch, sel):
    fig, ax = plt.subplots(figsize=(6.4, 6))
    lim = max(ch[[f"G_{Y0}", f"G_{Y1}"]].abs().max().max(), 0.06) + 0.01
    ax.axhline(0, color=COL_MUTED, lw=0.8); ax.axvline(0, color=COL_MUTED, lw=0.8)
    ax.plot([-lim, lim], [-lim, lim], color=COL_MUTED, lw=0.8, ls="--")
    dD = ch["dD"]; vmax = max(abs(dD.min()), abs(dD.max()))
    sc = ax.scatter(ch[f"G_{Y0}"], ch[f"G_{Y1}"], s=40 + 3000 * ch[f"D_{Y1}"], c=dD, cmap="RdBu_r", vmin=-vmax, vmax=vmax,
                    edgecolor=COL_INK, linewidth=0.6, zorder=3)
    zero = []
    for k, r in ch.iterrows():
        if abs(r[f"G_{Y0}"]) < 1e-9 and abs(r[f"G_{Y1}"]) < 1e-9 and abs(r["dD"]) < 1e-9:
            zero.append(r.ku_name); continue          # 두 해 모두 LD = LZ 인 구는 한 점에 겹치므로 각주로
        if not (sel.loc[k, "selected_B"] or abs(r[f"G_{Y1}"]) >= 0.01 or abs(r["dD"]) >= 0.02):
            continue
        mark = "*" if sel.loc[k, "selected_B"] else ""
        ax.annotate(f"{r.ku_name}{mark}", (r[f"G_{Y0}"], r[f"G_{Y1}"]), fontsize=6.5, xytext=(5, 4),
                    textcoords="offset points", color="#333")
    if zero:
        ax.text(0.01, 0.01, "원점(G=D=0, 두 해 모두 LD=LZ): " + ", ".join(zero) + "\n표기: 선별 구, |G 2025| ≥ 1%p 또는 |ΔD| ≥ 2%p",
                transform=ax.transAxes, fontsize=6.5, color="#444", va="bottom")
    cb = fig.colorbar(sc, ax=ax, shrink=0.7, pad=0.02); cb.set_label("ΔD = D(2025) - D(2020) (총 판정차 변화)")
    cb.ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=1))
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect("equal")
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel(f"G {Y0} = IFR(LD) - IFR(LZ)"); ax.set_ylabel(f"G {Y1}")
    ax.set_title("격차의 방향(G, 축)과 크기(D, 점 크기), 변화(ΔD, 색). * = 선별된 구", loc="left", fontsize=8.5)
    save(fig, "F4-4-3_quadrant_G")


def gu_polygons():
    import geopandas as gpd
    g = gpd.read_file(C.DONG_GPKG, layer="epsg5179")
    g["Ku"] = g["Ku"].astype(int); g["Dong"] = g["Dong"].astype(int)
    ku = g.dissolve(by="Ku")[["geometry"]]
    return g, ku


# F4.4-4 지도: ΔD 와 선별 구
def fig4(ch, sel, g, ku):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
    m = ku.join(ch[["dD", f"D_{Y1}", "ku_name"]]).join(sel[["selected_B", "type"]])
    vmax = m["dD"].abs().max()
    m.plot(column="dD", cmap="RdBu_r", vmin=-vmax, vmax=vmax, edgecolor="white", linewidth=0.6, ax=axes[0],
           legend=True, legend_kwds={"shrink": 0.6, "label": "ΔD", "format": matplotlib.ticker.PercentFormatter(1.0, decimals=0)})
    axes[0].set_title("(a) 총 판정차 변화 ΔD = D(2025) - D(2020)", loc="left", fontsize=9)
    m.plot(column=f"D_{Y1}", cmap="Oranges", edgecolor="white", linewidth=0.6, ax=axes[1], legend=True,
           legend_kwds={"shrink": 0.6, "label": f"D {Y1}"})
    typ_col = {"경계 재검토": COL_LD, "접근성·운영 검토": COL_LZ}
    for k, r in m[m["selected_B"] == True].iterrows():
        c = r.geometry.representative_point()
        axes[1].plot(c.x, c.y, marker="o" if r["type"] == "경계 재검토" else "s", ms=8, mfc="white",
                     mec=typ_col[r["type"]], mew=2)
        axes[1].annotate(r.ku_name, (c.x, c.y), fontsize=6.5, xytext=(5, 4), textcoords="offset points")
    h = [plt.Line2D([], [], marker="o", ls="", mfc="white", mec=COL_LD, mew=2, label="선별: 경계 재검토"),
         plt.Line2D([], [], marker="s", ls="", mfc="white", mec=COL_LZ, mew=2, label="선별: 권역 내 운영 검토")]
    axes[1].legend(handles=h, loc="lower left", frameon=False, fontsize=7.5)
    axes[1].set_title(f"(b) {Y1}년 총 판정차 D 와 선별된 구 (규칙 {C.SELECTION_RULE})", loc="left", fontsize=9)
    for ax in axes:
        ax.set_axis_off()
    save(fig, "F4-4-4_map_dD_selection")


# F4.4-5 선별 구의 LD 2020 vs 2025 경계 (동 단위), 바뀐 동 강조
def fig5(sel, g):
    lz = pd.read_csv(C.LZ_MAP, encoding="utf-8-sig").set_index("Dong")
    ld = {y: pd.read_csv(C.ld_map(y), encoding="utf-8-sig").set_index("Dong")["community"] for y in C.YEARS}
    ari = pd.read_csv(C.TAB / "t09_ari_ld20_ld25.csv", encoding="utf-8-sig").set_index("ku_code")
    picks = sel[sel["selected_B"] == True].index.tolist()
    if not picks:
        return
    n = len(picks)
    fig, axes = plt.subplots(n, 3, figsize=(9.5, 2.9 * n))
    axes = np.atleast_2d(axes)
    cmap = plt.get_cmap("Set2")
    for i, k in enumerate(picks):
        gk = g[g["Ku"] == k].set_index("Dong")
        # 소속이 바뀐 동: 이름으로 저장되어 있으므로 다시 계산한다
        a, b = ld[Y0].loc[gk.index], ld[Y1].loc[gk.index]
        peers20 = {d: frozenset(a.index[a == a[d]]) for d in gk.index}
        peers25 = {d: frozenset(b.index[b == b[d]]) for d in gk.index}
        chg = [d for d in gk.index if peers20[d] != peers25[d]]
        for j, (lab, col) in enumerate((("LZ (공식)", lz.loc[gk.index, "life_zone_id"]), (f"LD {Y0}", a), (f"LD {Y1}", b))):
            ax = axes[i, j]
            codes = pd.factorize(col)[0]
            gk.assign(c=codes).plot(column="c", cmap=cmap, categorical=True, edgecolor="white", linewidth=0.5, ax=ax)
            gk.dissolve(by=col.values).boundary.plot(ax=ax, color=COL_INK, linewidth=1.0)
            if j > 0 and chg:
                gk.loc[chg].boundary.plot(ax=ax, color="#C0392B", linewidth=1.8, linestyle="--")
            ax.set_axis_off()
            ax.set_title(f"{C.KU_NAME_EN[k]} — {lab}", fontsize=8, loc="left")
        axes[i, 2].set_title(f"{C.KU_NAME_EN[k]} — LD {Y1}   (ARI vs LD {Y0} = {ari.loc[k,'ari_ld20_ld25']:.2f}, "
                             f"소속 변경 동 {len(chg)}개: 붉은 점선)", fontsize=7.5, loc="left")
    save(fig, "F4-4-5_selected_gu_boundaries")


# F4.4-6 H4: 두 경계의 ΔIFR vs 귀무 분할(무작위 인접 분할) ΔIFR 90% 구간
def fig6(ch, nul):
    d = nul.sort_values("null_dIFR_med")
    y = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(6.5, 7.5))
    ax.hlines(y, d["null_dIFR_p05"], d["null_dIFR_p95"], color="#cfcfcf", lw=6, label="귀무 분할 ΔIFR 5~95% (구별 1,000개)")
    ax.scatter(d["null_dIFR_med"], y, marker="|", s=120, color="#666", label="귀무 분할 중앙값", zorder=3)
    ax.scatter(d["dIFR_lz"], y, s=26, color=COL_LZ, zorder=4, label="ΔIFR 공식 생활권 LZ")
    ax.scatter(d["dIFR_ld"], y, s=26, color=COL_LD, zorder=4, label="ΔIFR 이동 기반 경계 LD")
    ax.set_yticks(y); ax.set_yticklabels(d["ku_name"]); ax.axvline(0, color=COL_MUTED, lw=0.8)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel(f"ΔIFR = IFR {Y1} - IFR {Y0}"); ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    ax.set_title("경계와 무관한 IFR 상승 점검: 같은 구·같은 개수의 무작위 인접 분할과 비교", loc="left", fontsize=8.5)
    save(fig, "F4-4-6_null_partition_dIFR")


# F4.4-7 IoU(경계 모양 일치도) vs D(통행 판정 불일치), 색 = G. D가 크기, G가 방향임을 보이는 그림
def fig7():
    iou = pd.read_csv(C.TAB / "t10_iou_vs_gap.csv", encoding="utf-8-sig").set_index("ku_code")
    tst = json.loads((C.TAB / "t06_tests.json").read_text(encoding="utf-8"))["iou_corr"]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.4), sharey=True)
    vmax = max(abs(iou[[f"G_{Y0}", f"G_{Y1}"]].min().min()), iou[[f"G_{Y0}", f"G_{Y1}"]].max().max())
    for ax, y in zip(axes, (Y0, Y1)):
        sc = ax.scatter(iou[f"IoU_{y}"], iou[f"D_{y}"], c=iou[f"G_{y}"], cmap="RdBu_r", vmin=-vmax, vmax=vmax,
                        s=34, edgecolor=COL_INK, linewidth=0.5, zorder=3)
        for k, r in iou.iterrows():
            if r[f"D_{y}"] >= 0.12 or r[f"IoU_{y}"] <= 0.45:
                ax.annotate(C.KU_NAME_EN[k], (r[f"IoU_{y}"], r[f"D_{y}"]), fontsize=6.5, xytext=(4, 3),
                            textcoords="offset points", color="#444")
        rD = tst[f"IoU_vs_D_{y}"]["spearman"]; rG = tst[f"IoU_vs_G_{y}"]["spearman"]
        ax.set_title(f"{y}   ρ(IoU, D) = {rD:+.2f},  ρ(IoU, G) = {rG:+.2f}", loc="left", fontsize=8.5)
        ax.set_xlabel("IoU (공식 생활권 vs 이동 기반 경계, 동 기준 1:1)"); ax.set_xlim(0.3, 1.03)
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    axes[0].set_ylabel("D (총 판정차)")
    cb = fig.colorbar(sc, ax=axes, shrink=0.8, pad=0.02); cb.set_label("G = IFR(LD) - IFR(LZ)")
    cb.ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    fig.suptitle("경계 모양의 어긋남(IoU)은 판정 불일치의 크기(D)와 맞고, 방향(G)과는 무관하다", fontsize=8.5, x=0.02, ha="left")
    save(fig, "F4-4-7_iou_vs_D")


def main():
    ch, seoul, sel, nul = load()
    fig1(ch, seoul); fig2(ch); fig3(ch, sel); fig6(ch, nul); fig7()
    g, ku = gu_polygons()
    fig4(ch, sel, g, ku); fig5(sel, g)
    print("그림 저장:", sorted(p.name for p in C.FIG.glob("*.png")))


if __name__ == "__main__":
    main()
