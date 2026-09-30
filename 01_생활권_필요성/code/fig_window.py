# -*- coding: utf-8 -*-
"""그림 4.1-D: 시설별 보장 가능 창 [k_bind, k_afford] 과 공식 생활권 116 선. 입력 output/표4.1-9_시설별_창_{연도}.csv"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager
import sys
from r1lib import OUT, PLACE_SETS
SUF = sys.argv[1] if len(sys.argv) > 1 else ""   # 예: _평균60%
for f in ("Malgun Gothic", "NanumGothic"):
    if any(f == x.name for x in font_manager.fontManager.ttflist): plt.rcParams["font.family"] = f; break
plt.rcParams["axes.unicode_minus"] = False
KS = [25, 50, 80, 116, 160, 250, 424]; TAGS = {25: "구", 50: "rand50", 80: "rand80", 116: "rand116", 160: "rand160", 250: "rand250", 424: "동"}
fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
for ax, year in zip(axes, ("2020", "2025")):
    W = pd.read_csv(OUT / f"표4.1-9_시설별_창_{year}{SUF}.csv")
    labels = []
    for i, fac in enumerate(PLACE_SETS):
        d = W[W.시설 == fac]; K = int(d.K.iloc[0]); C = float(d.서울C.iloc[0])
        kmin = np.array([d[d.tag == TAGS[k]]["K_min"].astype(float).median() for k in KS]); bind = np.array([d[d.tag == TAGS[k]]["FGT0_P0후"].astype(float).median() for k in KS])
        afford = [k for k, v in zip(KS, kmin) if not np.isnan(v) and v <= K]; binds = [k for k, v in zip(KS, bind) if v >= 0.01]
        y = len(PLACE_SETS) - 1 - i
        if afford and binds and min(binds) <= max(afford):
            lo, hi = min(binds), max(afford); col = "#2a78d6" if lo <= 116 <= hi else "#eb6834"
            ax.plot([lo, hi], [y, y], color=col, linewidth=9, solid_capstyle="butt", alpha=0.85)
            ax.text(hi * 1.08, y, f"[{lo}, {hi}]", va="center", fontsize=8.5, color="#52514e")
        elif afford and not binds:
            ax.plot([25, 424], [y, y], color="#c3c2b7", linewidth=9, alpha=0.6, solid_capstyle="butt"); ax.text(440, y, "하한 무구속(어느 단위든 P0와 같음)", va="center", fontsize=8.5, color="#52514e")
        else:
            ax.plot([25, 424], [y, y], color="#e6e6e3", linewidth=9, alpha=0.9, solid_capstyle="butt"); ax.text(440, y, "창 없음(예산 부족)", va="center", fontsize=8.5, color="#52514e")
        # 무작위 구획 K_min ≤ K 점 표시
        ax.scatter([k for k, v in zip(KS, kmin) if not np.isnan(v) and v <= K], [y] * len(afford), s=14, color="white", zorder=5, edgecolor="#52514e", linewidth=0.6)
        labels.append(f"{fac}\n(C={C:.2f}, K={K})")
    ax.axvline(116, color="#0b0b0b", linewidth=1.2, linestyle="--"); ax.text(116, -0.9, "공식 생활권 116", ha="center", fontsize=9)
    ax.set_xscale("log"); ax.set_xticks(KS); ax.set_xticklabels(["구 25", "50", "80", "116", "160", "250", "동 424"], fontsize=8.5); ax.set_xlim(20, 1500)
    ax.set_yticks(range(len(PLACE_SETS))); ax.set_yticklabels(labels[::-1], fontsize=8.5); ax.set_title(f"{year}  (τ 규칙: {SUF.strip('_') or '중위 60%'})", fontsize=11); ax.set_ylim(-1.3, len(PLACE_SETS) - 0.4)
    ax.grid(axis="x", color="#e6e6e3", linewidth=0.6); ax.spines[["top", "right"]].set_visible(False)
fig.suptitle("그림 4.1-D  시설별 '보장 가능 창' — 하한이 구속력을 갖는 최소 단위 수(k_bind)부터 실제 5년 예산으로 지킬 수 있는 최대 단위 수(k_afford)까지\n"
             "파랑 = 창이 116을 품음, 주황 = 창이 있으나 116 밖, 회색 = 하한이 어느 단위에서도 구속하지 않음(시설이 이미 충분), 연회색 = 예산으로는 어느 단위도 못 지킴", fontsize=9.5)
fig.tight_layout(rect=(0, 0, 1, 0.9)); fig.savefig(OUT / f"그림4.1-D_시설별_보장가능창{SUF}.png", dpi=200); print("done")
