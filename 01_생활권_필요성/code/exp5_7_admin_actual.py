# -*- coding: utf-8 -*-
"""실험 5(행정 배분·협의 대리지표)와 실험 7(실제 배치 대조). 도서관, K=32, τ_main. 두 해(실제 배치는 2020 기준만).
실험 5: 규칙별 (i) 신규 시설이 들어가는 단위 수(동/생활권/구), (ii) 규칙이 지목하는 소외 단위 목록 길이(기준 상태, 각 단위), (iii) 시설 1개 도달권이 걸치는 단위 수,
        (iv) 단위별 취약 순위 안정성 2020↔2025(스피어만, 하위 10% Jaccard). 주 논증은 문헌, 대리지표는 탐색적(설정근거·확정안 4.4).
실험 7: 실제 2020→2025 신규 도서관(격자 42)이 (i) 기준 상태 소외 생활권/동에 들어간 비율, (ii) P1 공식 생활권 규칙이 고른 생활권과 겹치는 비율, (iii) 효율–형평 평면 좌표.
사용: python exp5_7_admin_actual.py"""
import time, json
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from r1lib import Year, OUT, md

K = 32; t0 = time.time()
def wmedian(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return x[o][np.searchsorted(cw, cw[-1] / 2)]
Y = {y: Year(y) for y in ("2020", "2025")}
LEV = ("동", "공식LZ", "Leiden", "구")
rows5, picks_all = [], {}
for y, Yr in Y.items():
    pop = Yr.pop; r0 = Yr.reach("도서관"); cand = Yr.candidates("도서관")
    Cd0, dd = Yr.unit_cov(Yr.units["동"], r0); tau = 0.6 * wmedian(Cd0[dd > 0], dd[dd > 0])
    rules = {"P0": Yr.place(r0, None, 0, K, cand)[0]}
    for lv in LEV: rules[f"P1 {lv}"] = Yr.place(r0, Yr.units[lv], tau, K, cand, kcap=700)[0][:K]
    picks_all[y] = {k: [int(j) for j in v] for k, v in rules.items()}
    for rule, pk in rules.items():
        row = {"year": y, "규칙": rule, "τ": tau, "시설수": len(pk)}
        for lv in LEV:
            u = Yr.units[lv]; row[f"{lv}_투입단위수"] = int(len(np.unique(u[pk])))
            Cu, den = Yr.unit_cov(u, r0); v = den > 0; row[f"{lv}_소외목록길이(기준)"] = int((v & (Cu < tau)).sum())
            cov = Yr.cov_after(r0, pk, K); Cu1, _ = Yr.unit_cov(u, cov); row[f"{lv}_소외목록길이(후)"] = int((v & (Cu1 < tau)).sum())
        rows5.append(row)
    # 도달권 걸침·안정성 (구획 자체의 성질)
    for lv in LEV:
        u = Yr.units[lv]; Cu, den = Yr.unit_cov(u, r0)
        rows5.append({"year": y, "규칙": f"[구획] {lv}", "도달권_걸치는단위수": Yr.catchment_spans(u, "도서관"), "단위수": int((den > 0).sum())})
    print(y, f"{time.time()-t0:.0f}s", flush=True)
# 안정성 2020↔2025 (같은 구획, 기준 상태 단위 Coverage 순위)
stab = []
for lv in LEV:
    a, da = Y["2020"].unit_cov(Y["2020"].units[lv], Y["2020"].reach("도서관")); b, db = Y["2025"].unit_cov(Y["2025"].units[lv], Y["2025"].reach("도서관"))
    if lv == "Leiden":  # 연도별 경계가 다르므로 2020 경계 고정으로 두 해 비교
        b, db = Y["2025"].unit_cov(Y["2025"].dong_series_to_units(Y["2020"].ld_map), Y["2025"].reach("도서관"))
    ok = (da > 0) & (db > 0); rho = spearmanr(a[ok], b[ok]).correlation; na = max(1, int(ok.sum() * 0.1))
    ia = set(np.argsort(a[ok])[:na]); ib = set(np.argsort(b[ok])[:na])
    stab.append({"단위": lv, "n": int(ok.sum()), "순위상관ρ": rho, "하위10%_Jaccard": len(ia & ib) / len(ia | ib)})
S5 = pd.DataFrame(rows5); S5.to_csv(OUT / "표4.1-5_행정대리지표.csv", index=False, encoding="utf-8-sig")
ST = pd.DataFrame(stab); ST.to_csv(OUT / "표4.1-5_안정성.csv", index=False, encoding="utf-8-sig")
json.dump(picks_all, open(OUT / "exp5_picks.json", "w"), ensure_ascii=False)
# 실험 7 — 실제 배치 (2020 기준)
Yr = Y["2020"]; pop = Yr.pop; r0 = Yr.reach("도서관"); Cd0, dd = Yr.unit_cov(Yr.units["동"], r0); tau = 0.6 * wmedian(Cd0[dd > 0], dd[dd > 0])
new = np.setdiff1d(Y["2025"].fac["도서관"][0], Yr.fac["도서관"][0]); new = [int(j) for j in new if Yr.ends[j] > Yr.starts[j]]
rows7 = []
def site_profile(pk, label):
    row = {"규칙": label, "시설수": len(pk)}
    for lv in LEV:
        u = Yr.units[lv]; Cu, den = Yr.unit_cov(u, r0); below = (den > 0) & (Cu < tau)
        row[f"{lv}_소외단위에_입지한_비율"] = float(np.mean(below[u[pk]])) if len(pk) else np.nan
    p1 = set(Yr.units["공식LZ"][picks_all["2020"]["P1 공식LZ"]]); p0 = set(Yr.units["공식LZ"][picks_all["2020"]["P0"]])
    z = Yr.units["공식LZ"][pk]
    row["P1공식이_고른_생활권과_겹침"] = float(np.mean([zz in p1 for zz in z])) if len(pk) else np.nan
    row["P0가_고른_생활권과_겹침"] = float(np.mean([zz in p0 for zz in z])) if len(pk) else np.nan
    cov = Yr.cov_after(r0, pk, len(pk)); newg = cov & ~r0
    row["도달증가"] = (pop * newg).sum(); row["입지동_기존Coverage평균"] = float(np.mean(Cd0[Yr.units["동"][pk]])) if len(pk) else np.nan
    Cd, _ = Yr.unit_cov(Yr.units["동"], cov); v = dd > 0; below = v & (Cd < tau)
    row["동_FGT1(후)"] = (dd[below] * (tau - Cd[below]) / tau).sum() / dd[v].sum()
    Cl, dl = Yr.unit_cov(Yr.units["공식LZ"], cov); vl = dl > 0; row["공식LZ_FGT0(후)"] = dl[vl & (Cl < tau)].sum() / dl[vl].sum()
    return row
rows7.append(site_profile(new, "실제 2020→2025 (42)"))
rows7.append(site_profile(Yr.place(r0, None, 0, len(new), Yr.candidates("도서관"))[0], "P0 (K=42)"))
rows7.append(site_profile(Yr.place(r0, Yr.units["공식LZ"], tau, len(new), Yr.candidates("도서관"), kcap=700)[0][:len(new)], "P1 공식LZ (K=42)"))
for rule, pk in picks_all["2020"].items(): rows7.append(site_profile(pk, f"{rule} (K=32)"))
S7 = pd.DataFrame(rows7); S7.to_csv(OUT / "표4.1-7_실제배치대조.csv", index=False, encoding="utf-8-sig")
out = "# 표 4.1-5 행정 배분·협의 대리지표 (탐색적)\n\n" + md(S5.round(3).fillna(""), "{}") + "\n\n## 안정성 2020↔2025 (기준 상태 단위 Coverage 순위)\n\n" + md(ST.round(3), "{}") \
      + "\n\n# 표 4.1-7 실제 배치 대조 (2020 기준, τ={:.3f})\n\n".format(tau) + md(S7.round(3), "{}")
open(OUT / "표4.1-5_7_요약.md", "w", encoding="utf-8").write(out); print(out); print("done", f"{time.time()-t0:.0f}s")
