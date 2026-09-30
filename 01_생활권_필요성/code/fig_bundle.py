# -*- coding: utf-8 -*-
"""묶음 스토리 그림 4장 (2026-10-01). 색: 파랑 #2a78d6, 주황 #eb6834, 청록 #1baf7a, 노랑 #eda100, 회색 #52514e.
F1 정의별 완결률 누적곡선(2020·2025) + 미완결자의 결손 범주 수 분포
F2 배치 방식 비교(완결률·하위 20% 완결률, 두 해; 2025 정수계획 현재해 표시)
F3 조정 배치(COL)가 산출한 다유형 공동입지 지도 2025 + 공식 생활권 경계 + 결손 2개 이상 격자
F4 서비스별 권역 vs 공통 권역(관행 시나리오·요인 비교·판정 단위 수)"""
import json
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt, geopandas as gpd
from matplotlib import font_manager
from r1lib import OUT, X
for f in ("Malgun Gothic", "NanumGothic"):
    if any(f == x.name for x in font_manager.fontManager.ttflist): plt.rcParams["font.family"] = f; break
plt.rcParams["axes.unicode_minus"] = False
BL, OR, AQ, YE, GR, LG = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#52514e", "#e6e6e3"
def clean(ax): ax.grid(color=LG, linewidth=0.6); ax.spines[["top", "right"]].set_visible(False)

# F1
fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
DEF = [("logan4_원정의(약국·슈퍼·공원·초등)", "Logan 원정의 4종", AQ), ("logan7_최댓값(cat_A 7)", "일상 7범주(최댓값)", BL),
       ("seoul_FULL_6분야(공원·도서관·노인여가·청소년아동·보육·공공체육)", "서울 계획 생활서비스 6분야", OR)]
for ax, y in zip(axes[:2], ("2020", "2025")):
    C = pd.read_csv(OUT / f"표4.1-16_묶음정의별_곡선_{y}.csv")
    for key, lab, col in DEF:
        d = C[C.정의 == key]; ax.plot(d.분, d.완결률, color=col, linewidth=2.2, label=lab)
    ax.axvline(10, color=GR, linestyle=":", linewidth=1); ax.axvline(15, color=GR, linestyle="--", linewidth=1)
    ax.text(10.2, 0.02, "10분(서울 계획)", fontsize=8, color=GR); ax.text(15.2, 0.02, "15분", fontsize=8, color=GR)
    ax.set_xlim(0, 20); ax.set_ylim(0, 1); ax.set_xlabel("보행 시간(분) — 묶음의 모든 범주가 이 시간 안에 닿는 인구"); ax.set_ylabel("인구 비율"); ax.set_title(y); clean(ax)
axes[0].legend(frameon=False, fontsize=9, loc="upper left")
ax = axes[2]; y = "2025"; M = pd.read_csv(OUT / f"표4.1-16_결손수분포_{y}.csv")
a = M[(M.정의 == "logan7_최댓값(cat_A 7)") & (M["임계(분)"] == 15)].iloc[0]; b = M[(M.정의 == "seoul_FULL_6분야") & (M["임계(분)"] == 10)].iloc[0]
ks = [1, 2, 3, 4]; w = 0.38; xs = np.arange(len(ks))
va = [a[f"결손{k}개"] for k in ks[:-1]] + [sum(a.get(f"결손{k}개", 0) or 0 for k in range(4, 8))]
vb = [b[f"결손{k}개"] for k in ks[:-1]] + [sum((b.get(f"결손{k}개", 0) if pd.notna(b.get(f"결손{k}개", np.nan)) else 0) for k in range(4, 7))]
ax.bar(xs - w / 2, va, w, color=BL, label="일상 7범주 · 15분"); ax.bar(xs + w / 2, vb, w, color=OR, label="서울 계획 6분야 · 10분")
ax.set_xticks(xs); ax.set_xticklabels(["1개", "2개", "3개", "4개 이상"]); ax.set_ylabel("미완결 인구 중 비율"); ax.set_title(f"미완결자의 결손 범주 수 ({y})"); ax.legend(frameon=False, fontsize=9); clean(ax)
fig.suptitle("그림 1  하루 묶음 완결률: 일상 기능은 거의 닫혀 있고, 공공 생활서비스 묶음은 여러 개가 동시에 빠져 있다", fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.93)); fig.savefig(OUT / "그림_묶음1_완결곡선_결손수.png", dpi=200); plt.close(fig)

# F2
order = [("IND_유형별독립", "시설별 독립 배치"), ("COL_조정_무경계", "묶음 조정(경계 없음)"), ("FLOOR_공식", "생활권 하한 + 조정"), ("FLOOR_무작위116", "무작위 116 하한 + 조정"),
         ("FLOOR_동", "동 하한 + 조정"), ("ZONE_공식", "생활권마다 중심 하나"), ("ZONE_무작위116", "무작위 116마다 하나"), ("ZONE_동", "동마다 하나")]
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
for ax, met, title in zip(axes, ("완결률", "하위20_완결률"), ("묶음 완결 인구 비율", "배치 전 하위 20%(도달 범주 수, 동률 분수 가중)의 완결 비율")):
    for i, y in enumerate(("2020", "2025")):
        D = pd.read_csv(OUT / f"표4.1-18_묶음배치_seoul_{y}.csv").groupby("방식")[met].median()
        v = [D.get(k, np.nan) for k, _ in order]; ys = np.arange(len(order)) + (0.2 if i == 0 else -0.2)
        ax.barh(ys, v, height=0.38, color=[GR if k.startswith("IND") else (BL if k.startswith(("COL", "FLOOR")) else OR) for k, _ in order], alpha=0.55 if i == 0 else 1.0, label=y)
    if met == "완결률":
        mi = pd.read_csv(OUT / "표4.1-19_묶음정수계획_seoul_2025.csv").iloc[0]
        lab_m = "최적" if (pd.notna(mi["MIP_갭"]) and mi["MIP_갭"] <= 1e-9) else "현재해(근최적)"
        ax.axvline(mi["MIP_현재해"], color=GR, linestyle="--", linewidth=1); ax.text(mi["MIP_현재해"], len(order) - 0.4, f" 정수계획 {lab_m} 2025 ({mi['MIP_현재해']:.3f}, 상계 {mi['MIP_상계']:.3f})", fontsize=8, color=GR)
    ax.set_yticks(range(len(order))); ax.set_yticklabels([l for _, l in order]); ax.invert_yaxis(); ax.set_title(title + ("  (옅은 2020, 진한 2025)" if met == "완결률" else ""), fontsize=10); clean(ax)
fig.suptitle("그림 2  같은 유형별 추가량(381 유형–입지, 점유 격자 순증)으로 서울 계획 생활서비스 묶음을 채우는 방식 비교 — 보행 600초", fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.93)); fig.savefig(OUT / "그림_묶음2_배치방식비교.png", dpi=200); plt.close(fig)

# F3
from bundlelib import Ctx
ctx = Ctx("seoul", "2025"); Yr = ctx.Yr; M = Yr.M
PL = json.load(open(OUT / "exp14_placements_seoul_2025.json", encoding="utf-8"))["COL_조정_무경계#0"]
pts = pd.DataFrame([(j, s) for s, js in PL.items() for j in js], columns=["j", "s"]); g = pts.groupby("j").s.nunique()
multi = g[g >= 2].index.to_numpy(); single = g[g == 1].index.to_numpy()
lz = gpd.read_file(X.C.DATA_DIR / "seoul_official_livingzone_116.gpkg", layer="epsg5179")
fig, ax = plt.subplots(figsize=(10, 8.4))
miss2 = ctx.popped & ((ctx.NC - ctx.cnt0) >= 2)
ax.scatter(M.x_c[miss2], M.y_c[miss2], s=0.6, c="#f3c9b5", label="배치 전 2개 이상 결손 격자", rasterized=True)
lz.boundary.plot(ax=ax, color=GR, linewidth=0.5)
ax.scatter(M.x_c.to_numpy()[single], M.y_c.to_numpy()[single], s=10, c=BL, alpha=0.7, label=f"단일 유형 입지 ({len(single)})")
ax.scatter(M.x_c.to_numpy()[multi], M.y_c.to_numpy()[multi], s=40, c=OR, edgecolor="white", linewidth=0.6, label=f"다유형 공동입지 ({len(multi)})")
ax.set_axis_off(); ax.legend(frameon=False, loc="lower left", fontsize=9)
c20 = pd.read_csv(OUT / "표4.1-20_중심구조_seoul.csv"); c20 = c20[(c20.year.astype(str) == "2025") & (c20.반경m == 0)].iloc[0]
ax.set_title("그림 3  묶음 조정 배치가 산출한 다유형 공동입지(2025) — 결손이 겹친 곳에 몰리며 생활권마다 생기지 않는다(알고리즘의 공동입지 액션 결과)" + chr(10) +
             f"(공식 생활권 116 경계; 공동입지 간 최근린 중앙 {c20['중심NN중앙m']/1000:.1f} km, Clark–Evans R {c20['ClarkEvansR']:.2f}, 생활권의 {c20['생활권_중심0비율']:.0%}에 공동입지 없음)", fontsize=10)
fig.tight_layout(); fig.savefig(OUT / "그림_묶음3_중심지도_2025.png", dpi=200); plt.close(fig)

# F4
fig, axes = plt.subplots(1, 3, figsize=(18, 4.8))
lab = {"S0_무경계서비스별(IND)": "시설별 독립(경계 없음)", "S1_서비스별권역(관행k)+서비스별하한+독립": "서비스별 권역(관행 k) + 서비스별 하한 + 독립", "S2_공통116+서비스별하한+독립": "공통 116 + 서비스별 하한 + 독립",
       "S3_공통116+묶음하한+조정": "공통 116 + 묶음 하한 + 조정", "S4_무경계조정(COL)": "묶음 조정(경계 없음)"}
cols = {"S0_무경계서비스별(IND)": GR, "S1_서비스별권역(관행k)+서비스별하한+독립": OR, "S2_공통116+서비스별하한+독립": YE, "S3_공통116+묶음하한+조정": BL, "S4_무경계조정(COL)": AQ}
DD = {y: pd.read_csv(OUT / f"표4.1-21_서비스별vs공통권역_seoul_{y}.csv").groupby("방식").median(numeric_only=True) for y in ("2020", "2025")}
keys = list(lab)
for i, y in enumerate(("2020", "2025")):
    ys = np.arange(len(keys)) + (0.2 if i == 0 else -0.2)
    axes[0].barh(ys, [DD[y].loc[k, "완결률"] for k in keys], height=0.38, color=[cols[k] for k in keys], alpha=0.55 if i == 0 else 1.0)
axes[0].set_yticks(range(len(keys))); axes[0].set_yticklabels([lab[k] for k in keys]); axes[0].invert_yaxis(); axes[0].set_title("A 관행 시나리오(권역 수·목적·하한이 함께 다름) — 완결률 (옅은 2020 · 진한 2025)", fontsize=9); clean(axes[0])
fk = [("F1_서비스별116+서비스별하한+독립", "서비스별 116 · 독립", OR), ("F2_공통116+서비스별하한+독립", "공통 116 · 독립", YE), ("F3_서비스별116+서비스별하한+조정", "서비스별 116 · 조정", "#f0a080"), ("F4_공통116+서비스별하한+조정", "공통 116 · 조정", BL)]
for i, y in enumerate(("2020", "2025")):
    ys = np.arange(len(fk)) + (0.2 if i == 0 else -0.2)
    axes[1].barh(ys, [DD[y].loc[k, "완결률"] for k, _, _ in fk], height=0.38, color=[c for _, _, c in fk], alpha=0.55 if i == 0 else 1.0)
axes[1].set_yticks(range(len(fk))); axes[1].set_yticklabels([l for _, l, _ in fk]); axes[1].invert_yaxis(); axes[1].set_title("B 요인 비교(권역 수 116·하한 규칙 고정): 경계 × 목적 — 완결률", fontsize=9); clean(axes[1])
D = DD["2025"]; k1 = "S1_서비스별권역(관행k)+서비스별하한+독립"; f1 = "F1_서비스별116+서비스별하한+독립"
vals = [D.loc[k1, "판정단위수"], D.loc[f1, "판정단위수"], 116]
axes[2].bar([0, 1, 2], vals, color=[OR, "#f0a080", BL])
for x_, v in zip([0, 1, 2], vals): axes[2].text(x_, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=9)
axes[2].set_xticks([0, 1, 2]); axes[2].set_xticklabels(["서비스별 권역(관행 k)", "서비스별 116", "공통 116"], fontsize=8); axes[2].set_xlabel("관행 k 의 값은 설계값(보육 424)에 좌우", fontsize=8)
axes[2].set_title("'하루가 완결되는가' 판정 단위 수 (2025; 유형별 권역의 중첩 개수)", fontsize=9); clean(axes[2])
fig.suptitle("그림 4  차이를 가르는 것은 경계의 모양이 아니라 약속의 내용이다 — 관행 비교(A)는 복합 차이 12%p, 요인 비교(B)에서 경계 종류의 차이는 1%p 안, 조정 +3%p, 묶음 하한 +5%p", fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.92)); fig.savefig(OUT / "그림_묶음4_서비스별vs공통권역.png", dpi=200); plt.close(fig)
print("done")
