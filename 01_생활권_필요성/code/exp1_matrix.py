# -*- coding: utf-8 -*-
"""실험 1: 4단위 × 4항목 기본 행렬 — 같은 시설·후보지·예산에서 배치 규칙만 바꾸고 모든 단위에서 교차 평가.
사용: python exp1_matrix.py [연도=2020] [시설=도서관] [K=32]

규칙: P0 도시 전체 효율(=격자 기준, MCLP 탐욕), P1 단위별 최소 보장(동/공식LZ/Leiden/구), 실제 배치(2020→2025).
소외 정의(설정근거_20260927.md 1절): 단위 Coverage < τ 인 단위. 지표 FGT0(소외 단위 거주 인구 비율)·FGT1(평균 부족분)·소외 단위 수,
  보조 = 인구가중 Gini, 최저값, 하위 10%.
τ(설정근거 2절): 본 = 행정동(424) Coverage 인구가중 중위의 60% (상대 문턱, 모든 단위에 같은 값). 민감도 = 서울 평균 × 0.8, 1.0.
배치 해법은 탐욕법(K_min은 정수해의 상한). 출력: output/표4.1-1_4단위비교행렬_{연도}_{시설}.csv/.md"""
import sys, time, json
import numpy as np, pandas as pd
from r1lib import Year, OUT, md, X

year = sys.argv[1] if len(sys.argv) > 1 else "2020"
fac = sys.argv[2] if len(sys.argv) > 2 else "도서관"
K = int(sys.argv[3]) if len(sys.argv) > 3 else 32
t0 = time.time()
Yr = Year(year); pop = Yr.pop; popped = Yr.popped
r0 = Yr.reach(fac); C0 = Yr.cov(r0); cand = Yr.candidates(fac)
dong_gdf = X.load_dong(); area = (dong_gdf.geometry.area / 1e6).set_axis(dong_gdf.Dong)
dong_codes = pd.factorize(Yr.M.dong)[1]
ud = Yr.units["동"]; den_d = np.bincount(ud, pop); dens = den_d / area.reindex(dong_codes).to_numpy()
lowdens = dens < np.median(dens[den_d > 0])
units = dict(Yr.units); units["격자"] = np.where(popped, np.arange(len(Yr.M)), len(Yr.M))
uncovered0 = pop * (~r0)

def wmedian(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return x[o][np.searchsorted(cw, cw[-1] / 2)]
def gini_w(x, w):
    o = np.argsort(x); x, w = x[o], w[o]; cw = np.cumsum(w); cx = np.cumsum(x * w)
    return 1 - 2 * np.sum(w * (cx - x * w / 2)) / (cw[-1] * cx[-1]) if cx[-1] > 0 else np.nan

Cd0, _ = Yr.unit_cov(ud, r0)
TAU = {"중위60%": 0.6 * wmedian(Cd0[den_d > 0], den_d[den_d > 0]), "평균×0.8": 0.8 * C0, "평균×1.0": C0}
tau_main = TAU["중위60%"]

def fgt(u, cov, tau):
    Cu, den = Yr.unit_cov(u, cov); v = den > 0; below = v & (Cu < tau)
    fgt0 = den[below].sum() / den[v].sum()
    fgt1 = (den[below] * (tau - Cu[below]) / tau).sum() / den[v].sum()
    return fgt0, fgt1, int(below.sum()), Cu[v].min(), np.quantile(Cu[v], .1), gini_w(Cu[v], den[v])

def evaluate(picks, Kp, label, tau_rule, tau_val, kmin=None, shortfall=None):
    cov = Yr.cov_after(r0, picks, Kp); newg = cov & ~r0; gain = (pop * newg).sum()
    row = {"규칙": label, "τ규칙": tau_rule, "τ": tau_val, "K": Kp, "K_min": kmin, "잔여부족": shortfall,
           "서울_도달증가(명)": gain, "서울_Coverage후": Yr.cov(cov),
           "격자_취약인구도달률": gain / uncovered0.sum(), "격자_FGT0(미도달인구비율)": (pop * ~cov).sum() / pop.sum()}
    for lv in ("동", "공식LZ", "Leiden", "구"):
        f0, f1, nb, mn, p10, g = fgt(units[lv], cov, tau_main)
        row[f"{lv}_FGT0"] = f0; row[f"{lv}_FGT1"] = f1; row[f"{lv}_소외단위수"] = nb
        row[f"{lv}_최저"] = mn; row[f"{lv}_하위10%"] = p10; row[f"{lv}_Gini"] = g
    row["저밀동_수혜비중"] = (pop[newg] * lowdens[ud[newg]]).sum() / max(gain, 1)
    row["신규입지동_기존Coverage평균"] = float(np.mean(Cd0[ud[picks[:Kp]]])) if len(picks) else np.nan
    row["신규입지_저밀동비율"] = float(np.mean(lowdens[ud[picks[:Kp]]])) if len(picks) else np.nan
    return row

rows = []
p0, _, _ = Yr.place(r0, None, 0, K, cand)
rows.append(evaluate(p0, K, "P0 도시전체효율(격자)", "-", None)); base = rows[0]["서울_도달증가(명)"]
for rule, tv in TAU.items():
    for lv in ("동", "공식LZ", "Leiden", "구"):
        pk, kmin, sf = Yr.place(r0, units[lv], min(tv, 0.9999), K, cand, kcap=700)
        rows.append(evaluate(pk, K, f"P1 {lv} 최소보장", rule, tv, kmin, round(sf, 4) if sf is not None else None))
    print(rule, f"{time.time()-t0:.0f}s", flush=True)
if year == "2020":
    Y25 = Year("2025"); new = np.setdiff1d(Y25.fac[fac][0], Yr.fac[fac][0]); new = [j for j in new if Yr.ends[j] > Yr.starts[j]]
    rows.append(evaluate(list(new), len(new), "실제 2020→2025", "-", None))
    p0b, _, _ = Yr.place(r0, None, 0, len(new), cand); rows.append(evaluate(p0b, len(new), "P0 (실제와 같은 K)", "-", None))
E = pd.DataFrame(rows); E["효율유지율"] = E["서울_도달증가(명)"] / base
front = ["규칙", "τ규칙", "τ", "K", "K_min", "효율유지율", "서울_도달증가(명)", "격자_FGT0(미도달인구비율)",
         "동_FGT0", "동_FGT1", "동_소외단위수", "공식LZ_FGT0", "공식LZ_FGT1", "공식LZ_소외단위수", "Leiden_FGT0", "Leiden_소외단위수",
         "구_FGT0", "구_FGT1", "구_소외단위수", "동_최저", "동_하위10%", "동_Gini", "공식LZ_최저", "구_최저",
         "저밀동_수혜비중", "신규입지동_기존Coverage평균", "신규입지_저밀동비율"]
E = E[front + [c for c in E.columns if c not in front]]
meta = {"year": year, "facility": fac, "K": K, "pop_year": {"2020": "2019", "2025": "2024"}[year], "C0_seoul": C0,
        "dong_wmedian": float(wmedian(Cd0[den_d > 0], den_d[den_d > 0])), "tau": {k: float(v) for k, v in TAU.items()}, "tau_main": "중위60%",
        "n_candidates": int(len(cand)), "uncovered0": float(uncovered0.sum()), "solver": "greedy (K_min = 정수해 상한)",
        "소외정의": "단위 Coverage < τ. FGT0 = 소외 단위 거주 인구 비율, FGT1 = Σ pop_u (τ−C_u)/τ / Σ pop (Foster–Greer–Thorbecke). 모든 단위에 같은 τ.",
        "note": "설계 검토용. 설정 근거는 설정근거_20260927.md."}
name = f"표4.1-1_4단위비교행렬_{year}_{fac}"
E.round(4).to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8-sig")
json.dump(meta, open(OUT / f"{name}_meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(OUT / f"{name}.md", "w", encoding="utf-8").write(f"# {name}\n\n" + json.dumps(meta, ensure_ascii=False) + "\n\n" + md(E.round(3), "{}"))
print(json.dumps(meta, ensure_ascii=False)); print(md(E[front].round(3), "{}")); print("done", f"{time.time()-t0:.0f}s")
