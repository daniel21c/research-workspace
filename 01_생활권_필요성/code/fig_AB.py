# -*- coding: utf-8 -*-
"""그림 A(단위 크기 축 k 곡선)와 그림 B(효율–형평 평면). 입력: output/표4.1-3_크기축_구획별.csv, 표4.1-1_4단위비교행렬_*.csv, 표4.1-4_형평정의_*.csv.
축은 패널마다 하나(이중축 없음), 범주 색은 고정 순서(파랑=공식, 주황=Leiden, 청록=무작위 중앙값, 회색=구·동 끝점).
출력: output/그림4.1-A_크기축_{연도}.png, 그림4.1-B_효율형평평면_{연도}.png"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager
from r1lib import OUT
for f in ("Malgun Gothic", "NanumGothic", "Apple SD Gothic Neo"):
    if any(f == x.name for x in font_manager.fontManager.ttflist): plt.rcParams["font.family"] = f; break
plt.rcParams["axes.unicode_minus"] = False
C = {"공식": "#2a78d6", "Leiden": "#eb6834", "무작위": "#1baf7a", "끝점": "#52514e", "grid": "#e6e6e3"}
A = pd.read_csv(OUT / "표4.1-3_크기축_구획별.csv"); A["year"] = A.year.astype(str)
KS = [25, 50, 80, 116, 160, 250, 424]; TAGS = {25: "구", 50: "rand50", 80: "rand80", 116: "rand116", 160: "rand160", 250: "rand250", 424: "동"}
PANELS = [("IFR", "통행 내부율 IFR", "↑"), ("loss_도서관", "경계 제한 손실 (도서관 Coverage)", "↓"), ("Hauc_도서관", "은폐 H (τ 곡선 AUC, 도서관)", "↓"),
          ("Kmin", "보장에 필요한 도서관 수 K_min (τ=중위 60%)", "↓"), ("Reff", "효율 유지율 @K=32", "↑"), ("span_lib", "도서관 1개 도달권이 걸치는 단위 수", "↓")]
for y in ("2020", "2025"):
    d = A[A.year == y]; fig, axes = plt.subplots(2, 3, figsize=(13, 7.6)); axes = axes.ravel()
    for ax, (m, title, arrow) in zip(axes, PANELS):
        med, lo, hi = [], [], []
        for k in KS:
            v = d[d.tag == TAGS[k]][m].astype(float).dropna(); med.append(v.median()); lo.append(v.quantile(.05)); hi.append(v.quantile(.95))
        ax.fill_between(KS, lo, hi, color=C["무작위"], alpha=0.15, linewidth=0)
        ax.plot(KS, med, color=C["무작위"], linewidth=2, marker="o", markersize=4, label="무작위 연접 구획 중앙값 (5~95%)")
        for tag, col, mk, lab in (("공식LZ", C["공식"], "s", "공식 생활권 116"), (f"Leiden{y}", C["Leiden"], "D", f"Leiden {y} 116")):
            g = d[d.tag == tag]
            if not g.empty and not np.isnan(float(g[m].iloc[0])): ax.plot([116], [float(g[m].iloc[0])], marker=mk, markersize=9, color=col, linestyle="none", label=lab, zorder=5)
        ax.set_xscale("log"); ax.set_xticks(KS); ax.set_xticklabels(["구 25", "50", "80", "116", "160", "250", "동 424"], fontsize=8)
        ax.set_title(f"{title} {arrow}", fontsize=10); ax.grid(color=C["grid"], linewidth=0.6); ax.spines[["top", "right"]].set_visible(False)
        if m == "Kmin": ax.axhline(32, color=C["끝점"], linewidth=1, linestyle="--"); ax.text(26, 33, "예산 32", fontsize=8, color=C["끝점"])
    h, l = axes[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=3, frameon=False, fontsize=9)
    fig.suptitle(f"그림 4.1-A  단위 크기 축에서 본 지표 ({y}, 공공도서관, 예산 32)  — 가로축: 단위 수 k (로그)", fontsize=11)
    fig.tight_layout(rect=(0, 0.05, 1, 0.96)); fig.savefig(OUT / f"그림4.1-A_크기축_{y}.png", dpi=200); plt.close(fig)
    # 그림 B: 효율(유지율) × 형평(권역 FGT0 / 동 FGT1)
    E = pd.read_csv(OUT / f"표4.1-1_4단위비교행렬_{y}_도서관.csv"); E = E[E["τ규칙"].isin(["-", "중위60%"])]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    mk = {"P0 도시전체효율(격자)": ("격자 P0", "o", C["끝점"]), "P1 동 최소보장": ("동", "^", C["끝점"]), "P1 공식LZ 최소보장": ("공식 생활권", "s", C["공식"]),
          "P1 Leiden 최소보장": ("Leiden", "D", C["Leiden"]), "P1 구 최소보장": ("구", "v", C["끝점"]), "실제 2020→2025": ("실제 배치(K=42)", "*", "#e34948")}
    for ax, (ycol, ylab) in zip(axes, (("공식LZ_FGT0", "소외 생활권 거주 인구 비율 FGT0 (↓)"), ("동_FGT1", "동 수준 부족분 FGT1 (↓)"))):
        for _, r in E.iterrows():
            if r["규칙"] not in mk or r["규칙"].startswith("P0 ("): continue
            lab, m_, col = mk[r["규칙"]]; ax.plot(r["효율유지율"], r[ycol], marker=m_, markersize=10 if m_ != "*" else 14, color=col, linestyle="none", markeredgecolor="white", markeredgewidth=1)
            off = {"격자 P0": (8, 8), "구": (8, -14), "공식 생활권": (8, -14), "Leiden": (-46, 8), "동": (8, 4), "실제 배치(K=42)": (10, -4)}[lab]
            ax.annotate(lab, (r["효율유지율"], r[ycol]), textcoords="offset points", xytext=off, fontsize=9, arrowprops=dict(arrowstyle="-", color="#9a9a96", lw=0.6) if lab in ("구", "공식 생활권", "Leiden") else None)
        ax.margins(x=0.12, y=0.15); ax.set_xlabel("효율 유지율 (P0 도달 증가 = 1) →"); ax.set_ylabel(ylab); ax.grid(color=C["grid"], linewidth=0.6); ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"그림 4.1-B  효율–형평 평면 ({y}, 공공도서관, 규칙 K=32; 실제 배치는 K=42이며 효율 유지율은 K=32 P0 대비)", fontsize=11); fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT / f"그림4.1-B_효율형평평면_{y}.png", dpi=200); plt.close(fig)
print("done")
