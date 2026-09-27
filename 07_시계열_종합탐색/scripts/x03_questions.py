# -*- coding: utf-8 -*-
"""x03_questions.py — Q1~Q9 탐색. 판정 기준은 계산 전에 CRITERIA에 고정한다(계산 후 바꾸지 않는다).

입력: output/tables/panel_{ku,lz116,dong424}.csv (x01_load.py)
출력: output/tables/q*.csv, output/tables/q_results.json, output/figures/F*.png
모든 수치는 탐색용(투고 전 재계산·검증 필요).
"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False
sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parents[1]; ROOT = HERE.parent
T = HERE / "output/tables"; F = HERE / "output/figures"; F.mkdir(exist_ok=True)
rc = lambda n: pd.read_csv(T / n, encoding="utf-8-sig")
ku, lz, dg = rc("panel_ku.csv"), rc("panel_lz116.csv"), rc("panel_dong424.csv")
KPA = ROOT / "04_불일치_시간변화_KPA/output/package_20260924/tables"
sel = pd.read_csv(KPA / "t06_selection.csv", encoding="utf-8-sig")
ari = pd.read_csv(KPA / "t09_ari_ld20_ld25.csv", encoding="utf-8-sig")
CATS = ["교육", "보육·복지", "의료", "문화", "체육", "행정·안전", "소매", "생활서비스"]
SENS = {"main": "acc", "T600": "sens_T600", "retail_without": "sens_retail_without", "snap": "sens_snap"}
R = {}

# ---------- 사전 판정 기준 (계산 전 고정) ----------
CRITERIA = {
 "Q1": "발견 = 구·생활권 모두에서 중위 |ΔD| ≥ 2 × 중위 |ΔCOV_lz116(종합)| (둘 다 %p) 이고, 네트워크 고정 뒤(Δ나머지)에도 유지. 하나라도 깨지면 '불확실', 둘 다 깨지면 '없음'.",
 "Q2": "발견 = 동 424에서 Δ인구%와 Δ시설%(보육·복지 또는 어린이집)의 Spearman ρ ≥ 0.3 (p<0.01). 그리고 인구당 시설 수 변화(상쇄 여부)를 함께 보고. ρ<0.15면 '없음'.",
 "Q3": "발견 = 생활권 116에서 COV_lz116 하위 10% 값이 ≥1%p 오르고 (p90−p10) 격차가 ≥1%p 줄어듦(종합 또는 문화). 둘 중 하나만이면 '불확실'.",
 "Q4": "발견 = (가) 서울 경계 비용(COV_none−COV_lz116)이 두 시점 사이 ≥0.5%p 변하거나, (나) 생활권 116 중 ≥20%에서 비용이 ≥1%p 변함. LD<LZ 비용 관계는 두 해 모두 구 25 중 ≥18개면 '유지'.",
 "Q5": "발견 = LD 소속 변화 동(Jaccard<1)과 불변 동 사이에 |Δ인구%|·|Δ시설%|·ΔSR·ΔIFR_lz 중 2개 이상에서 Mann–Whitney p<0.05 이고 중위 차이가 같은 방향.",
 "Q6": "발견 = 생활권 116에서 ΔIFR_lz와 ΔCOV_lz116(종합)의 Spearman |ρ| ≥ 0.3 (p<0.01). 아니면 '없음'이되, '내부통행↑·접근성 정체' 사분면 비율은 기술 통계로 보고.",
 "Q7": "발견 = 돌봄(어린이집 5분) 미충족 인구 증가분의 ≥50%가 생활권 116 중 상위 10개에 집중. 선별 구 8개와의 겹침은 기술 통계.",
 "Q8": "기술 통계(판정 없음). 선별 8개 구의 이동·접근성·인구·시설·경계 변화를 한 표로.",
 "Q9": "발견 = 동 424에서 네트워크 몫(ΔPWATT_none, 2020 시설·인구 고정)이 인구밀도 또는 Δ인구%와 Spearman |ρ| ≥ 0.3 (p<0.01). 아니면 '없음'(자료 한계로만 처리).",
}
(T / "criteria.json").write_text(json.dumps(CRITERIA, ensure_ascii=False, indent=1), encoding="utf-8")

def wide(df, cols):
    """unit×year → unit 행, 열_2020/열_2025/d열"""
    p = df.pivot(index="unit_id", columns="year", values=cols)
    out = pd.DataFrame(index=p.index)
    for c in cols:
        out[f"{c}_2020"] = p[(c, 2020)]; out[f"{c}_2025"] = p[(c, 2025)]; out[f"d_{c}"] = p[(c, 2025)] - p[(c, 2020)]
    return out

def sp(x, y):
    m = x.notna() & y.notna()
    r, p = stats.spearmanr(x[m], y[m]); return float(r), float(p), int(m.sum())

# ---------- Q1 이동 vs 공급의 비대칭 ----------
q1 = {}
for name, df in [("ku", ku), ("lz116", lz)]:
    cols = ["mob_D", "mob_G", "acc_COV_lz116_종합", "acc_MAI_lz116_종합", "acc_COV_none_종합", "sens_net2025_COV_lz116_종합", "sens_T600_COV_lz116_종합", "sens_retail_without_COV_lz116_종합"]
    w = wide(df, cols)
    w["d_COV_rest"] = w["acc_COV_lz116_종합_2025"] - w["sens_net2025_COV_lz116_종합_2020"]  # 네트워크 고정 뒤 나머지
    w["d_COV_net"] = w["sens_net2025_COV_lz116_종합_2020"] - w["acc_COV_lz116_종합_2020"]
    w.to_csv(T / f"q1_{name}.csv", encoding="utf-8-sig")
    med = lambda s: float(np.nanmedian(np.abs(s)) * 100)
    q1[name] = {"n": len(w), "med_abs_dD_pp": med(w.d_mob_D), "med_abs_dG_pp": med(w.d_mob_G), "med_abs_dCOV_lz_pp": med(w["d_acc_COV_lz116_종합"]),
                "med_abs_dCOV_rest_pp": med(w.d_COV_rest), "med_abs_dCOV_none_pp": med(w["d_acc_COV_none_종합"]),
                "med_abs_dMAI_lz": float(np.nanmedian(np.abs(w["d_acc_MAI_lz116_종합"]))),
                "p90_abs_dD_pp": float(np.nanpercentile(np.abs(w.d_mob_D), 90) * 100), "p90_abs_dCOV_lz_pp": float(np.nanpercentile(np.abs(w["d_acc_COV_lz116_종합"]), 90) * 100),
                "ratio_main": med(w.d_mob_D) / med(w["d_acc_COV_lz116_종합"]), "ratio_rest": med(w.d_mob_D) / med(w.d_COV_rest),
                "ratio_T600": med(w.d_mob_D) / med(w["d_sens_T600_COV_lz116_종합"]), "ratio_retail_without": med(w.d_mob_D) / med(w["d_sens_retail_without_COV_lz116_종합"]),
                "rho_dD_dCOV": sp(w.d_mob_D, w["d_acc_COV_lz116_종합"]), "rho_D2025_COV2025": sp(w.mob_D_2025, w["acc_COV_lz116_종합_2025"]),
                "share_units_dD_gt_1pp": float((w.d_mob_D.abs() > 0.01).mean()), "share_units_dCOV_gt_1pp": float((w["d_acc_COV_lz116_종합"].abs() > 0.01).mean())}
ok = all(q1[n]["ratio_main"] >= 2 for n in q1); ok_rest = all(q1[n]["ratio_rest"] >= 2 for n in q1)
q1["판정"] = "발견" if ok and ok_rest else ("불확실" if ok or ok_rest else "없음")
R["Q1"] = q1
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
for ax, (name, df, lab) in zip(axes, [("ku", ku, "구 25"), ("lz116", lz, "공식 생활권 116")]):
    w = pd.read_csv(T / f"q1_{name}.csv", encoding="utf-8-sig")
    ax.scatter(w["d_acc_COV_lz116_종합"] * 100, w.d_mob_D * 100, s=18, alpha=.7)
    lim = max(abs(w.d_mob_D).max(), abs(w["d_acc_COV_lz116_종합"]).max()) * 100 * 1.1
    ax.plot([-lim, lim], [-lim, lim], "k--", lw=.6); ax.plot([-lim, lim], [lim, -lim], "k--", lw=.6)
    ax.axhline(0, c="grey", lw=.5); ax.axvline(0, c="grey", lw=.5)
    ax.set_xlabel("ΔCoverage (공식 생활권 안, 종합, %p)"); ax.set_ylabel("ΔD 이동 불일치 크기 (%p)"); ax.set_title(lab); ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
fig.suptitle("Q1 2020→2025 이동 불일치 변화 vs 권역 내 접근성 변화 (같은 %p 척도) — 탐색용"); fig.tight_layout(); fig.savefig(F / "F1_q1_dD_vs_dCOV.png", dpi=150); plt.close()

# ---------- Q2 인구 변화 vs 시설 변화 (동 424) ----------
cols = ["pop", "hh", "fac_A_total", "fac_보육·복지", "fac_교육", "fac_어린이집", "fac_유치원", "fac_학교", "fac_문화", "fac_공공도서관", "acc_COV_lz116_보육·복지", "acc_COV_lz116_교육", "acc_COV_lz116_문화", "acc_MAI_lz116_교육"]
w = wide(dg, cols)
w["dpop_pct"] = w.d_pop / w.pop_2020 * 100
for c in ["fac_A_total", "fac_보육·복지", "fac_교육", "fac_어린이집", "fac_유치원", "fac_문화"]:
    w[f"d{c}_pct"] = w[f"d_{c}"] / w[f"{c}_2020"].replace(0, np.nan) * 100
    w[f"{c}_per10k_2020"] = w[f"{c}_2020"] / w.pop_2020 * 1e4; w[f"{c}_per10k_2025"] = w[f"{c}_2025"] / w.pop_2025 * 1e4
    w[f"d{c}_per10k"] = w[f"{c}_per10k_2025"] - w[f"{c}_per10k_2020"]
w = w.join(dg[dg.year == 2025].set_index("unit_id")[["ku", "ku_name", "dong_name", "lz116"]])
w.to_csv(T / "q2_dong.csv", encoding="utf-8-sig")
q2 = {"seoul": {"pop_2019": float(w.pop_2020.sum()), "pop_2024": float(w.pop_2025.sum()), "dpop_pct": float(w.d_pop.sum() / w.pop_2020.sum() * 100),
                **{f"{c}": [float(w[f"{c}_2020"].sum()), float(w[f"{c}_2025"].sum()), float(w[f"d_{c}"].sum() / w[f"{c}_2020"].sum() * 100)] for c in ["fac_A_total", "fac_보육·복지", "fac_교육", "fac_어린이집", "fac_유치원", "fac_학교", "fac_문화", "fac_공공도서관"]}},
      "rho_dpop_vs": {c: sp(w.dpop_pct, w[f"d{c}_pct"]) for c in ["fac_A_total", "fac_보육·복지", "fac_어린이집", "fac_유치원", "fac_교육", "fac_문화"]},
      "rho_dpop_vs_dcount": {c: sp(w.dpop_pct, w[f"d_{c}"]) for c in ["fac_보육·복지", "fac_어린이집"]},
      "share_dong_pop_down": float((w.d_pop < 0).mean()), "share_dong_childcare_down": float((w["d_fac_어린이집"] < 0).mean()),
      "share_both_down": float(((w.d_pop < 0) & (w["d_fac_어린이집"] < 0)).mean()),
      "childcare_per10k_seoul": [float(w["fac_어린이집_2020"].sum() / w.pop_2020.sum() * 1e4), float(w["fac_어린이집_2025"].sum() / w.pop_2025.sum() * 1e4)],
      "share_dong_childcare_per10k_down": float((w["dfac_어린이집_per10k"] < 0).mean()),
      "rho_dchildcare_per10k_vs_dpop": sp(w["dfac_어린이집_per10k"], w.dpop_pct),
      "COV_보육_lz_2025_below_0.99_share": float((w["acc_COV_lz116_보육·복지_2025"] < 0.99).mean()),
      "rho_dCOV_보육_vs_dchildcare_pct": sp(w["d_acc_COV_lz116_보육·복지"], w["dfac_어린이집_pct"]),
      "rho_dMAI_교육_vs_dfac_교육_pct": sp(w["d_acc_MAI_lz116_교육"], w["dfac_교육_pct"]),
      "rho_dCOV_문화_vs_dfac_문화": sp(w["d_acc_COV_lz116_문화"], w["d_fac_문화"]),
      "rho_dpop_pct_vs_dCOV_none": sp(w.dpop_pct, wide(dg, ["acc_COV_none_종합"])["d_acc_COV_none_종합"])}
r = q2["rho_dpop_vs"]["fac_보육·복지"][0], q2["rho_dpop_vs"]["fac_어린이집"][0]
q2["판정"] = "발견" if max(r) >= 0.3 and min(q2["rho_dpop_vs"]["fac_보육·복지"][1], q2["rho_dpop_vs"]["fac_어린이집"][1]) < 0.01 else ("없음" if max(r) < 0.15 else "불확실")
R["Q2"] = q2
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
axes[0].scatter(w.dpop_pct, w["dfac_어린이집_pct"], s=12, alpha=.6); axes[0].set_xlabel("Δ인구 2019→2024 (%)"); axes[0].set_ylabel("Δ어린이집 수 (%)"); axes[0].set_title("동 424: 인구 변화 vs 어린이집 변화")
axes[1].scatter(w.dpop_pct, w["dfac_어린이집_per10k"], s=12, alpha=.6); axes[1].axhline(0, c="grey", lw=.5); axes[1].set_xlabel("Δ인구 (%)"); axes[1].set_ylabel("Δ 인구 1만 명당 어린이집 수"); axes[1].set_title("상쇄 여부: 인구당 어린이집")
fig.suptitle("Q2 — 탐색용"); fig.tight_layout(); fig.savefig(F / "F2_q2_pop_vs_childcare.png", dpi=150); plt.close()

# ---------- Q3 형평성 ----------
def dist(s):
    s = s.dropna(); return {"mean": float(s.mean()), "std": float(s.std()), "p10": float(s.quantile(.1)), "p50": float(s.median()), "p90": float(s.quantile(.9)), "gap_p90_p10": float(s.quantile(.9) - s.quantile(.1)), "min": float(s.min())}
q3 = {}
rows = []
for tagname, pre in SENS.items():
    for cat in ["종합"] + CATS:
        col = f"{pre}_COV_lz116_{cat}"
        if col not in lz.columns: continue
        w = wide(lz, [col])
        d20, d25 = dist(w[f"{col}_2020"]), dist(w[f"{col}_2025"])
        rho_catchup = sp(w[f"{col}_2020"], w[f"d_{col}"])
        # 인구가중 변동계수
        pw = lz.pivot(index="unit_id", columns="year", values="pop")
        cv = {}
        for y in (2020, 2025):
            v = w[f"{col}_{y}"]; p = pw[y]; m = v.notna()
            mu = np.average(v[m], weights=p[m]); cv[y] = float(np.sqrt(np.average((v[m] - mu) ** 2, weights=p[m])) / mu)
        rows.append({"tag": tagname, "cat": cat, **{f"{k}_2020": v for k, v in d20.items()}, **{f"{k}_2025": v for k, v in d25.items()},
                     "d_p10_pp": (d25["p10"] - d20["p10"]) * 100, "d_gap_pp": (d25["gap_p90_p10"] - d20["gap_p90_p10"]) * 100, "d_std": d25["std"] - d20["std"],
                     "wcv_2020": cv[2020], "wcv_2025": cv[2025], "rho_level2020_vs_delta": rho_catchup[0], "p_catchup": rho_catchup[1],
                     "n_lz_below_seoul_2020": int((w[f"{col}_2020"] < ku[(ku.year == 2020)][col.replace("lz116", "lz116")].mean()).sum()) if False else None})
q3t = pd.DataFrame(rows); q3t.to_csv(T / "q3_equity_lz116.csv", index=False, encoding="utf-8-sig")
main = q3t[q3t.tag == "main"].set_index("cat")
q3["main"] = main[["p10_2020", "p10_2025", "d_p10_pp", "gap_p90_p10_2020", "gap_p90_p10_2025", "d_gap_pp", "wcv_2020", "wcv_2025", "rho_level2020_vs_delta"]].round(4).to_dict("index")
hit = {c: bool(main.loc[c, "d_p10_pp"] >= 1 and main.loc[c, "d_gap_pp"] <= -1) for c in ["종합", "문화"]}
half = {c: bool(main.loc[c, "d_p10_pp"] >= 1 or main.loc[c, "d_gap_pp"] <= -1) for c in ["종합", "문화"]}
q3["sens"] = {t: q3t[(q3t.tag == t) & q3t.cat.isin(["종합", "문화"])].set_index("cat")[["d_p10_pp", "d_gap_pp"]].round(2).to_dict("index") for t in SENS if t != "main"}
q3["판정"] = "발견" if any(hit.values()) else ("불확실" if any(half.values()) else "없음")
R["Q3"] = q3
w = wide(lz, ["acc_COV_lz116_문화", "acc_COV_lz116_종합"]).join(lz[lz.year == 2025].set_index("unit_id")[["name", "ku_name"]])
w = w.sort_values("acc_COV_lz116_문화_2020")
fig, ax = plt.subplots(figsize=(12, 5))
x = np.arange(len(w)); ax.vlines(x, w["acc_COV_lz116_문화_2020"], w["acc_COV_lz116_문화_2025"], color="grey", lw=1)
ax.scatter(x, w["acc_COV_lz116_문화_2020"], s=10, label="2020"); ax.scatter(x, w["acc_COV_lz116_문화_2025"], s=10, label="2025")
ax.set_xlabel("공식 생활권 116 (2020 값 오름차순)"); ax.set_ylabel("문화 Coverage (생활권 안, 15분)"); ax.legend(); ax.set_title("Q3 문화 접근성의 생활권 간 분포 변화 — 탐색용")
fig.tight_layout(); fig.savefig(F / "F3_q3_culture_dumbbell.png", dpi=150); plt.close()

# ---------- Q4 경계 비용 ----------
q4 = {}
for name, df in [("ku", ku), ("lz116", lz)]:
    for pre_name, pre in SENS.items():
        cn, cl, cd = f"{pre}_COV_none_종합", f"{pre}_COV_lz116_종합", f"{pre}_COV_ld_종합"
        if cn not in df.columns: continue
        w = wide(df, [cn, cl, cd])
        for y in (2020, 2025):
            w[f"cost_lz_{y}"] = w[f"{cn}_{y}"] - w[f"{cl}_{y}"]; w[f"cost_ld_{y}"] = w[f"{cn}_{y}"] - w[f"{cd}_{y}"]
        w["d_cost_lz"] = w.cost_lz_2025 - w.cost_lz_2020; w["d_cost_ld"] = w.cost_ld_2025 - w.cost_ld_2020
        if pre_name == "main":
            w.join(df[df.year == 2025].set_index("unit_id")[["name"]]).to_csv(T / f"q4_cost_{name}.csv", encoding="utf-8-sig")
        q4[f"{name}_{pre_name}"] = {"n": len(w), "med_cost_lz_2020_pp": float(w.cost_lz_2020.median() * 100), "med_cost_lz_2025_pp": float(w.cost_lz_2025.median() * 100),
                                    "med_cost_ld_2020_pp": float(w.cost_ld_2020.median() * 100), "med_cost_ld_2025_pp": float(w.cost_ld_2025.median() * 100),
                                    "n_ld_cost_lt_lz_2020": int((w.cost_ld_2020 < w.cost_lz_2020 - 1e-9).sum()), "n_ld_cost_gt_lz_2020": int((w.cost_ld_2020 > w.cost_lz_2020 + 1e-9).sum()),
                                    "n_ld_cost_lt_lz_2025": int((w.cost_ld_2025 < w.cost_lz_2025 - 1e-9).sum()), "n_ld_cost_gt_lz_2025": int((w.cost_ld_2025 > w.cost_lz_2025 + 1e-9).sum()),
                                    "share_dcost_lz_abs_ge_1pp": float((w.d_cost_lz.abs() >= 0.01).mean()), "share_dcost_lz_up_ge_1pp": float((w.d_cost_lz >= 0.01).mean()), "share_dcost_lz_down_ge_1pp": float((w.d_cost_lz <= -0.01).mean()),
                                    "rho_cost_lz_2025_vs_D_2025": sp(w.cost_lz_2025, wide(df, ["mob_D"]).mob_D_2025) if "mob_D" in df.columns else None}
# 서울 값
s = pd.concat([pd.read_csv(ROOT / f"06_접근성분석/접근성분석_패키지/데이터/결과/main/unit_access_{y}_100.csv", encoding="utf-8-sig").assign(year=y) for y in (2020, 2025)])
s = s[(s.unit_level == "seoul") & (s.cat == "종합")].pivot(index="year", columns="b", values="COV")
q4["seoul"] = {"cost_lz_2020_pp": float((s.loc[2020, "none"] - s.loc[2020, "lz116"]) * 100), "cost_lz_2025_pp": float((s.loc[2025, "none"] - s.loc[2025, "lz116"]) * 100),
               "cost_ld_2020_pp": float((s.loc[2020, "none"] - s.loc[2020, "ld"]) * 100), "cost_ld_2025_pp": float((s.loc[2025, "none"] - s.loc[2025, "ld"]) * 100),
               "cost_dong_2020_pp": float((s.loc[2020, "none"] - s.loc[2020, "dong424"]) * 100), "cost_dong_2025_pp": float((s.loc[2025, "none"] - s.loc[2025, "dong424"]) * 100),
               "cost_ku_2020_pp": float((s.loc[2020, "none"] - s.loc[2020, "ku"]) * 100), "cost_ku_2025_pp": float((s.loc[2025, "none"] - s.loc[2025, "ku"]) * 100)}
dseoul = abs(q4["seoul"]["cost_lz_2025_pp"] - q4["seoul"]["cost_lz_2020_pp"])
q4["판정"] = "발견" if dseoul >= 0.5 or q4["lz116_main"]["share_dcost_lz_abs_ge_1pp"] >= 0.2 else "없음"
q4["LD<LZ_유지"] = bool(q4["ku_main"]["n_ld_cost_lt_lz_2020"] >= 18 and q4["ku_main"]["n_ld_cost_lt_lz_2025"] >= 18)
R["Q4"] = q4
w = pd.read_csv(T / "q4_cost_lz116.csv", encoding="utf-8-sig")
fig, ax = plt.subplots(figsize=(6, 6)); ax.scatter(w.cost_lz_2020 * 100, w.cost_lz_2025 * 100, s=14, alpha=.7)
lim = max(w.cost_lz_2020.max(), w.cost_lz_2025.max()) * 100 * 1.05; ax.plot([0, lim], [0, lim], "k--", lw=.6)
ax.set_xlabel("2020 경계 비용 (COV 없음 − COV 공식 생활권, %p)"); ax.set_ylabel("2025 경계 비용 (%p)"); ax.set_title("Q4 생활권 116의 경계 비용 — 탐색용")
fig.tight_layout(); fig.savefig(F / "F4_q4_boundary_cost_lz116.png", dpi=150); plt.close()

# ---------- Q5 LD 소속 변화 동 ----------
w = wide(dg, ["pop", "fac_A_total", "mob_SR", "mob_IFR_lz", "mob_IFR_ld", "mob_D", "acc_COV_none_종합", "acc_COV_lz116_종합", "acc_MAI_none_종합", "biz", "emp"])
w["dpop_pct"] = w.d_pop / w.pop_2020 * 100; w["dfac_pct"] = w.d_fac_A_total / w.fac_A_total_2020 * 100; w["dbiz_pct"] = w.d_biz / w.biz_2020.replace(0, np.nan) * 100
w = w.join(dg[dg.year == 2025].set_index("unit_id")[["ku", "ku_name", "dong_name", "ld_jaccard", "ld_changed", "lz_ld2025_same"]])
w.to_csv(T / "q5_dong_ldchange.csv", encoding="utf-8-sig")
q5 = {"n_changed": int(w.ld_changed.sum()), "n_unchanged": int((~w.ld_changed).sum()), "n_ku_with_change": int(w[w.ld_changed].ku.nunique()), "tests": {}}
nsig = 0
for v, absv in [("dpop_pct", True), ("dfac_pct", True), ("dbiz_pct", True), ("d_mob_SR", False), ("d_mob_IFR_lz", False), ("d_mob_D", False), ("d_acc_COV_none_종합", True), ("d_acc_COV_lz116_종합", False)]:
    x = w[v].abs() if absv else w[v]
    a, b = x[w.ld_changed].dropna(), x[~w.ld_changed].dropna()
    u = stats.mannwhitneyu(a, b, alternative="two-sided")
    q5["tests"][("abs_" if absv else "") + v] = {"med_changed": float(a.median()), "med_unchanged": float(b.median()), "p": float(u.pvalue)}
    nsig += u.pvalue < 0.05
q5["n_sig"] = int(nsig)
q5["판정"] = "발견" if nsig >= 2 else "없음"
R["Q5"] = q5

# ---------- Q6 자족성 vs 접근성 (생활권) ----------
q6 = {}
for pre_name, pre in SENS.items():
    col = f"{pre}_COV_lz116_종합"
    if col not in lz.columns: continue
    w = wide(lz, ["mob_IFR_lz", "mob_IFR_ld", "mob_SR", col, f"{pre}_MAI_lz116_종합"])
    r = sp(w.d_mob_IFR_lz, w[f"d_{col}"]); r2 = sp(w.d_mob_SR, w[f"d_{col}"]); r3 = sp(w.d_mob_IFR_lz, w[f"d_{pre}_MAI_lz116_종합"])
    q6[pre_name] = {"rho_dIFR_lz_dCOV": r, "rho_dSR_dCOV": r2, "rho_dIFR_lz_dMAI": r3,
                    "quad_IFRup_COVflat(|d|<0.5pp)": float(((w.d_mob_IFR_lz > 0) & (w[f"d_{col}"].abs() < 0.005)).mean()),
                    "quad_IFRup_COVup": float(((w.d_mob_IFR_lz > 0) & (w[f"d_{col}"] >= 0.005)).mean()), "quad_IFRup_COVdown": float(((w.d_mob_IFR_lz > 0) & (w[f"d_{col}"] <= -0.005)).mean()),
                    "share_IFR_up": float((w.d_mob_IFR_lz > 0).mean()), "rho_level_IFR2025_COV2025": sp(w.mob_IFR_lz_2025, w[f"{col}_2025"])}
    if pre_name == "main":
        w.join(lz[lz.year == 2025].set_index("unit_id")[["name", "ku_name"]]).to_csv(T / "q6_lz_ifr_vs_cov.csv", encoding="utf-8-sig")
rr = q6["main"]["rho_dIFR_lz_dCOV"]
q6["판정"] = "발견" if abs(rr[0]) >= 0.3 and rr[1] < 0.01 else "없음"
R["Q6"] = q6
w = pd.read_csv(T / "q6_lz_ifr_vs_cov.csv", encoding="utf-8-sig")
fig, ax = plt.subplots(figsize=(6.5, 5.5)); ax.scatter(w.d_mob_IFR_lz * 100, w["d_acc_COV_lz116_종합"] * 100, s=14, alpha=.7)
ax.axhline(0, c="grey", lw=.5); ax.axvline(0, c="grey", lw=.5); ax.set_xlabel("ΔIFR 공식 생활권 자족률 (%p)"); ax.set_ylabel("ΔCoverage 생활권 안 (종합, %p)"); ax.set_title("Q6 생활권 116: 자족률 변화 vs 접근성 변화 — 탐색용")
fig.tight_layout(); fig.savefig(F / "F6_q6_dIFR_vs_dCOV_lz116.png", dpi=150); plt.close()

# ---------- Q7 국가 최저기준 ----------
w = wide(lz, ["nat_종합", "nat_돌봄", "nat_교육", "nat_교육_유치원_10분", "nat_의료", "nat_체육", "nat_편의", "pop"])
for it in ["nat_종합", "nat_돌봄", "nat_교육_유치원_10분"]:
    for y in (2020, 2025): w[f"unmet_{it}_{y}"] = (1 - w[f"{it}_{y}"]) * w[f"pop_{y}"]
    w[f"d_unmet_{it}"] = w[f"unmet_{it}_2025"] - w[f"unmet_{it}_2020"]
w = w.join(lz[lz.year == 2025].set_index("unit_id")[["name", "ku", "ku_name"]])
w["selected_ku"] = w.ku.isin(sel[sel.selected_B].ku_code)
w.to_csv(T / "q7_natstd_lz116.csv", encoding="utf-8-sig")
inc = w[w["d_unmet_nat_돌봄"] > 0].sort_values("d_unmet_nat_돌봄", ascending=False)
q7 = {"seoul_unmet_돌봄_2020": float(w["unmet_nat_돌봄_2020"].sum()), "seoul_unmet_돌봄_2025": float(w["unmet_nat_돌봄_2025"].sum()),
      "seoul_unmet_종합_2020": float(w["unmet_nat_종합_2020"].sum()), "seoul_unmet_종합_2025": float(w["unmet_nat_종합_2025"].sum()),
      "n_lz_돌봄_down": int((w["d_nat_돌봄"] < -0.01).sum()), "n_lz_돌봄_up": int((w["d_nat_돌봄"] > 0.01).sum()),
      "top10_share_of_increase_돌봄": float(inc["d_unmet_nat_돌봄"].head(10).sum() / inc["d_unmet_nat_돌봄"].sum()),
      "top10_돌봄_increase": inc.head(10)[["name", "ku_name", "nat_돌봄_2020", "nat_돌봄_2025", "d_unmet_nat_돌봄", "selected_ku"]].round(3).to_dict("records"),
      "share_increase_in_selected_ku": float(inc[inc.selected_ku]["d_unmet_nat_돌봄"].sum() / inc["d_unmet_nat_돌봄"].sum()),
      "share_pop_in_selected_ku": float(w[w.selected_ku].pop_2025.sum() / w.pop_2025.sum()),
      "rho_dnat_돌봄_vs_dpop_pct": sp(w["d_nat_돌봄"], w.d_pop / w.pop_2020),
      "worst10_종합_2025": w.sort_values("nat_종합_2025").head(10)[["name", "ku_name", "nat_종합_2020", "nat_종합_2025", "selected_ku"]].round(3).to_dict("records")}
q7["판정"] = "발견" if q7["top10_share_of_increase_돌봄"] >= 0.5 else "없음"
R["Q7"] = q7

# ---------- Q8 선별 구 프로파일 ----------
w = wide(ku, ["mob_IFR_lz", "mob_IFR_ld", "mob_G", "mob_D", "acc_COV_lz116_종합", "acc_MAI_lz116_종합", "acc_COV_none_종합", "pop", "fac_A_total", "fac_어린이집", "fac_문화", "nat_돌봄", "nat_종합"])
w["dpop_pct"] = w.d_pop / w.pop_2020 * 100; w["dfac_pct"] = w.d_fac_A_total / w.fac_A_total_2020 * 100
w["cost_lz_2025_pp"] = (w["acc_COV_none_종합_2025"] - w["acc_COV_lz116_종합_2025"]) * 100
w = w.join(ku[ku.year == 2025].set_index("unit_id")[["name"]])
w = w.join(sel.set_index("ku_code")[["selected_B", "type", "selected_B_minband1.0"]]).join(ari.set_index("ku_code")[["ari_ld20_ld25", "n_dong_changed"]])
lzw = pd.read_csv(T / "q7_natstd_lz116.csv", encoding="utf-8-sig")
lzcov = wide(lz, ["acc_COV_lz116_종합"]).join(lz[lz.year == 2025].set_index("unit_id")[["ku"]])
seoul_cov25 = float(s.loc[2025, "lz116"])
below = lzcov[lzcov["acc_COV_lz116_종합_2025"] < seoul_cov25].groupby("ku").size().rename("n_lz_below_seoulCOV_2025")
down = lzcov[lzcov["d_acc_COV_lz116_종합"] < -0.005].groupby("ku").size().rename("n_lz_COV_down_0.5pp")
w = w.join(below).join(down).fillna({"n_lz_below_seoulCOV_2025": 0, "n_lz_COV_down_0.5pp": 0})
cols8 = ["name", "selected_B", "type", "selected_B_minband1.0", "d_mob_D", "d_mob_G", "mob_D_2025", "mob_G_2025", "ari_ld20_ld25", "n_dong_changed", "d_acc_COV_lz116_종합", "d_acc_MAI_lz116_종합", "acc_COV_lz116_종합_2025", "cost_lz_2025_pp", "dpop_pct", "dfac_pct", "d_fac_어린이집", "d_fac_문화", "d_nat_돌봄", "n_lz_below_seoulCOV_2025", "n_lz_COV_down_0.5pp"]
w[cols8].to_csv(T / "q8_ku_profile.csv", encoding="utf-8-sig")
q8 = {"seoul_COV_lz116_2025": seoul_cov25, "selected": w[w.selected_B][cols8].round(4).to_dict("index"),
      "H7_check": {str(i): {"type": r.type, "n_lz_below": int(r.n_lz_below_seoulCOV_2025), "n_lz_down": int(r["n_lz_COV_down_0.5pp"])} for i, r in w[w.selected_B].iterrows()}}
R["Q8"] = q8

# ---------- Q9 네트워크 몫의 공간 분포 ----------
w = wide(dg, ["acc_PWATT_none_종합", "acc_COV_none_종합", "sens_net2025_PWATT_none_종합", "sens_net2025_COV_none_종합", "pop", "n_grid", "biz"])
w["net_dPWATT_min"] = w["sens_net2025_PWATT_none_종합_2020"] - w["acc_PWATT_none_종합_2020"]
w["net_dCOV"] = w["sens_net2025_COV_none_종합_2020"] - w["acc_COV_none_종합_2020"]
w["rest_dPWATT_min"] = w["acc_PWATT_none_종합_2025"] - w["sens_net2025_PWATT_none_종합_2020"]
w["dens_2020"] = w.pop_2020 / w.n_grid_2020; w["dpop_pct"] = w.d_pop / w.pop_2020 * 100
w = w.join(dg[dg.year == 2025].set_index("unit_id")[["ku", "ku_name", "dong_name"]])
w.to_csv(T / "q9_dong_network.csv", encoding="utf-8-sig")
byku = w.groupby("ku_name").agg(net_dPWATT_med=("net_dPWATT_min", "median"), rest_dPWATT_med=("rest_dPWATT_min", "median"), net_dCOV_med=("net_dCOV", "median")).round(3)
byku.to_csv(T / "q9_ku_network.csv", encoding="utf-8-sig")
q9 = {"seoul_med_net_dPWATT_min": float(w.net_dPWATT_min.median()), "share_dong_net_dPWATT_pos": float((w.net_dPWATT_min > 0).mean()),
      "rho_net_dPWATT_vs_density": sp(w.net_dPWATT_min, w.dens_2020), "rho_net_dPWATT_vs_dpop": sp(w.net_dPWATT_min, w.dpop_pct), "rho_net_dPWATT_vs_biz": sp(w.net_dPWATT_min, w.biz_2020),
      "rho_net_dCOV_vs_density": sp(w.net_dCOV, w.dens_2020), "rho_net_vs_rest_dPWATT": sp(w.net_dPWATT_min, w.rest_dPWATT_min),
      "ku_top5_net_dPWATT": byku.sort_values("net_dPWATT_med", ascending=False).head(5).to_dict("index"), "ku_bottom5": byku.sort_values("net_dPWATT_med").head(5).to_dict("index"),
      "kruskal_ku_p": float(stats.kruskal(*[g.net_dPWATT_min.dropna() for _, g in w.groupby("ku")]).pvalue)}
hit = [q9["rho_net_dPWATT_vs_density"], q9["rho_net_dPWATT_vs_dpop"]]
q9["판정"] = "발견" if any(abs(h[0]) >= 0.3 and h[1] < 0.01 for h in hit) else "없음"
R["Q9"] = q9
# 지도
try:
    import geopandas as gpd
    g = gpd.read_file(ROOT / "00_공통_코어엔진/data/seoul_dong_424_dissolved.gpkg")
    idcol = [c for c in g.columns if c.lower() in ("dong", "dong424", "dong_cd", "adm_cd8", "dong_code")]
    if idcol:
        g["unit_id"] = g[idcol[0]].astype(int); g = g.merge(w[["net_dPWATT_min", "rest_dPWATT_min"]], left_on="unit_id", right_index=True, how="left")
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
        for ax, c, t in zip(axes, ["net_dPWATT_min", "rest_dPWATT_min"], ["보행망 변화 몫 (2020 시설·인구 고정, 분)", "나머지 몫 (시설·인구 변화, 분)"]):
            g.plot(column=c, cmap="RdBu_r", vmin=-0.6, vmax=0.6, legend=True, ax=ax, edgecolor="white", linewidth=.2); ax.set_axis_off(); ax.set_title(t)
        fig.suptitle("Q9 동별 도달시간 변화의 분해 (경계 없음, 종합) — 탐색용"); fig.tight_layout(); fig.savefig(F / "F9_q9_network_map.png", dpi=150); plt.close()
    else:
        R["Q9"]["map"] = f"id 열을 찾지 못함: {list(g.columns)}"
except Exception as e:
    R["Q9"]["map_error"] = str(e)

(T / "q_results.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
for k, v in R.items():
    print(k, "판정:", v.get("판정", "-"))
