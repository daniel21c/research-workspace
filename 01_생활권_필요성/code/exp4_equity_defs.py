# -*- coding: utf-8 -*-
"""실험 4: 형평의 정의를 바꿔도 결론이 유지되는가.
(a) 목적함수: 도달 여부(Coverage, 15분) / 도달시간(30분 상한, Σ pop·min(t,1800) 최소화)
(b) 규칙: P0 도시 전체 / P1 하한 τ_main / maximin(가장 나쁜 단위 우선) / P2 예산 배분(미도달 인구 비례 정수 배분 → 단위 안 후보에서 최대화)
(c) 형평 지표(동 424 기준 = 개인 수준 대리): FGT0·FGT1(τ_main), 최저, 하위 10%, 인구가중 Gini, 취약 인구 도달률, 도달시간 p90·최대, 2SFCA(도서관, 1만 명당) 하위 10%
    + 규칙이 적용된 단위 자체의 FGT0.
2SFCA 목적함수는 신규 시설 1개당 Σ pop·ΔA = 1 로 상수라 배치 목적으로는 퇴화 → 평가 지표로만 쓴다.
사용: python exp4_equity_defs.py [연도=2020]  (탐욕법; 도서관; K=32)"""
import sys, time, json
import numpy as np, pandas as pd, pyarrow.dataset as ds
from r1lib import Year, OUT, md, PKG

year = sys.argv[1] if len(sys.argv) > 1 else "2020"
K = 32; CAP = 1800; t0 = time.time()
Yr = Year(year); pop = Yr.pop; n = len(Yr.M); popped = Yr.popped
r0 = Yr.reach("도서관"); C0 = Yr.cov(r0); cand = Yr.candidates("도서관"); ud = Yr.units["동"]
def wmedian(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return x[o][np.searchsorted(cw, cw[-1] / 2)]
def gini_w(x, w):
    o = np.argsort(x); x, w = x[o], w[o]; cw = np.cumsum(w); cx = np.cumsum(x * w)
    return 1 - 2 * np.sum(w * (cx - x * w / 2)) / (cw[-1] * cx[-1]) if cx[-1] > 0 else np.nan
Cd0, dd = Yr.unit_cov(ud, r0); tau = 0.6 * wmedian(Cd0[dd > 0], dd[dd > 0])
# 30분 소요시간(시간 목적용)
tt = ds.dataset(PKG / f"입력/ttm/ttm100_{year}", format="parquet", partitioning="hive").to_table(columns=["o_grid", "d_grid", "t_sec"]).to_pandas()
o = Yr.gix.reindex(tt.o_grid).to_numpy(); d = Yr.gix.reindex(tt.d_grid).to_numpy(); ok = ~(np.isnan(o) | np.isnan(d))
o = o[ok].astype(np.int64); d = d[ok].astype(np.int64); t = tt.t_sec.to_numpy()[ok].astype(np.int32); del tt
order = np.argsort(d, kind="stable"); o, d, t = o[order], d[order], t[order]
st = np.searchsorted(d, np.arange(n)); en = np.searchsorted(d, np.arange(n), side="right")
cur0 = np.full(n, CAP, np.int32)
for j in Yr.fac["도서관"][0]: np.minimum.at(cur0, o[st[j]:en[j]], t[st[j]:en[j]])
# 2SFCA(도서관, 15분): P_j = j 도달권 인구, A_i = Σ_{j∋i} 1/P_j
def sfca_grid(lib_idx):
    A = np.zeros(n)
    for j in lib_idx:
        oo = Yr.cover_of(j); P = pop[oo].sum()
        if P > 0: A[oo] += 1.0 / P
    return A * 1e4
A0 = sfca_grid(Yr.fac["도서관"][0])
print(f"loaded tau {tau:.3f} ({time.time()-t0:.0f}s)", flush=True)

def gain_cov(j, cov):
    idx = Yr.cover_of(j); new = idx[~cov[idx]]; return pop[new].sum(), new
def gain_time(j, c):
    oo, tj = o[st[j]:en[j]], t[st[j]:en[j]]; red = c[oo] - tj; m = red > 0
    return (pop[oo[m]] * red[m]).sum(), oo[m], tj[m]

def evaluate(picks, label, objective, rule, level):
    cov = Yr.cov_after(r0, picks, K); c = cur0.copy()
    for j in picks[:K]:
        _, oo, tj = gain_time(j, c); c[oo] = tj
    A = A0 + sfca_grid(picks[:K])
    Cd, den = Yr.unit_cov(ud, cov); v = den > 0; below = v & (Cd < tau)
    dt = np.divide(np.bincount(ud, pop * c), den, out=np.zeros_like(den), where=v) / 60
    As, _ = Yr.unit_mean(ud, A)
    newg = cov & ~r0
    row = {"year": year, "목적함수": objective, "규칙": rule, "단위": level, "K": K,
           "서울_도달증가": (pop * newg).sum(), "서울_시간감소(분/인)": ((pop * cur0).sum() - (pop * c).sum()) / 60 / pop.sum(),
           "동_FGT0": den[below].sum() / den[v].sum(), "동_FGT1": (den[below] * (tau - Cd[below]) / tau).sum() / den[v].sum(),
           "동_소외수": int(below.sum()), "동_최저": Cd[v].min(), "동_하위10%": np.quantile(Cd[v], .1), "동_Gini": gini_w(Cd[v], den[v]),
           "취약인구도달률": (pop * newg).sum() / (pop * ~r0).sum(),
           "동_시간p90(분)": np.quantile(dt[v], .9), "동_시간최대(분)": dt[v].max(),
           "동_2SFCA하위10%": np.quantile(As[v], .1), "동_2SFCA최저": As[v].min()}
    if level != "-":
        u = Yr.units[level]; Cu, du_ = Yr.unit_cov(u, cov); vv = du_ > 0; b2 = vv & (Cu < tau)
        row["자기단위_FGT0"] = du_[b2].sum() / du_[vv].sum(); row["자기단위_소외수"] = int(b2.sum())
    return row

def largest_remainder(w, K):
    w = np.asarray(w, float); w = w / w.sum() if w.sum() > 0 else np.ones_like(w) / len(w)
    raw = w * K; a = np.floor(raw).astype(int); rem = K - a.sum()
    for i in np.argsort(-(raw - a))[:rem]: a[i] += 1
    return a

rows = []
LEVELS = ("동", "공식LZ", "Leiden", "구")
for objective in ("도달여부", "도달시간"):
    # P0
    if objective == "도달여부":
        p0, _, _ = Yr.place(r0, None, 0, K, cand)
    else:
        c = cur0.copy(); p0 = []
        for _ in range(K):
            best, bg = None, 0
            for j in cand:
                g, _, _ = gain_time(j, c)
                if g > bg: best, bg = j, g
            _, oo, tj = gain_time(best, c); c[oo] = tj; p0.append(best)
    rows.append(evaluate(p0, "P0", objective, "P0", "-")); print(objective, "P0", f"{time.time()-t0:.0f}s", flush=True)
    for lv in LEVELS:
        u = Yr.units[lv]; den = np.bincount(u, pop); valid = den > 0
        # P1 하한 (도달여부만 정의; 시간 목적에서는 단위 평균시간 하한 대신 maximin 사용)
        if objective == "도달여부":
            pk, kmin, _ = Yr.place(r0, u, tau, K, cand, kcap=700); rows.append(evaluate(pk, "P1", objective, "P1 하한τ", lv))
        # maximin
        picks = []
        if objective == "도달여부":
            cov = r0.copy(); cnum = np.bincount(u, pop * cov, minlength=len(den)); vld = valid.copy()
            for _ in range(K):
                Cu = np.divide(cnum, den, out=np.full_like(cnum, np.inf), where=vld); worst = np.argmin(Cu); best, bk = None, (-1.0, -1.0)
                for j in cand:
                    g, new = gain_cov(j, cov)
                    if g <= 0: continue
                    gw = pop[new[u[new] == worst]].sum()
                    if (gw, g) > bk: best, bk = j, (gw, g)
                if bk[0] <= 0: vld[worst] = False; continue
                _, new = gain_cov(best, cov); cov[new] = True; cnum += np.bincount(u[new], pop[new], minlength=len(den)); picks.append(best)
        else:
            c = cur0.copy(); vld = valid.copy()
            for _ in range(K):
                ut = np.divide(np.bincount(u, pop * c, minlength=len(den)), den, out=np.full(len(den), -1.0), where=vld); worst = np.argmax(ut); best, bk = None, (-1.0, -1.0)
                for j in cand:
                    g, oo, tj = gain_time(j, c)
                    if g <= 0: continue
                    m = u[oo] == worst; gw = (pop[oo[m]] * (c[oo[m]] - tj[m])).sum()
                    if (gw, g) > bk: best, bk = j, (gw, g)
                if bk[0] <= 0: vld[worst] = False; continue
                _, oo, tj = gain_time(best, c); c[oo] = tj; picks.append(best)
        rows.append(evaluate(picks, "maximin", objective, "maximin", lv))
        # P2 예산 배분 (미도달 인구 비례 / 시간 목적은 초과시간 인구 비례)
        if objective == "도달여부": w = den - np.bincount(u, pop * r0, minlength=len(den))
        else: w = np.bincount(u, pop * (cur0 - 0) / CAP, minlength=len(den))
        Ku = largest_remainder(w, K); cand_u = u[cand]; picks = []
        zs = float(np.mean(Ku[valid] == 0))   # 설계 M5: 배분 0 인 단위 비율
        cov = r0.copy(); c = cur0.copy()
        for uu in np.nonzero(Ku)[0]:
            cj = cand[cand_u == uu]
            for _ in range(Ku[uu]):
                best, bg = None, 0
                for j in cj:
                    g = gain_cov(j, cov)[0] if objective == "도달여부" else gain_time(j, c)[0]
                    if g > bg: best, bg = j, g
                if best is None: break
                if objective == "도달여부": _, new = gain_cov(best, cov); cov[new] = True
                else: _, oo, tj = gain_time(best, c); c[oo] = tj
                picks.append(best)
        rows.append(evaluate(picks, "P2", objective, "P2 배분", lv)); rows[-1]["배분0단위비율"] = zs; print(objective, lv, f"{time.time()-t0:.0f}s", flush=True)
D = pd.DataFrame(rows); D.to_csv(OUT / f"표4.1-4_형평정의_{year}.csv", index=False, encoding="utf-8-sig")
# 요약: P0 대비 나아진 칸 표시
met = ["동_FGT0", "동_FGT1", "동_최저", "동_하위10%", "동_Gini", "취약인구도달률", "동_시간p90(분)", "동_시간최대(분)", "동_2SFCA하위10%", "자기단위_FGT0"]
better_dir = {"동_FGT0": -1, "동_FGT1": -1, "동_최저": 1, "동_하위10%": 1, "동_Gini": -1, "취약인구도달률": 1, "동_시간p90(분)": -1, "동_시간최대(분)": -1, "동_2SFCA하위10%": 1, "자기단위_FGT0": -1}
out = f"# 표 4.1-4 형평 정의별 비교 ({year}, 도서관, K=32, τ={tau:.3f}) — 값(P0 대비 ↑나아짐/↓나빠짐/=)\n"
for objective in ("도달여부", "도달시간"):
    d = D[D.목적함수 == objective]; p0 = d[d.규칙 == "P0"].iloc[0]; tab = []
    for _, r in d.iterrows():
        row = {"규칙": r.규칙, "단위": r.단위, "효율(도달증가/시간감소)": f"{r.서울_도달증가:,.0f} / {r['서울_시간감소(분/인)']:.3f}"}
        for m in met:
            if pd.isna(r[m]): row[m] = ""; continue
            if r.규칙 == "P0": row[m] = f"{r[m]:.3f}"; continue
            diff = (r[m] - p0[m]) * better_dir[m]; mark = "↑" if diff > 1e-6 else ("↓" if diff < -1e-6 else "=")
            row[m] = f"{r[m]:.3f}{mark}"
        tab.append(row)
    out += f"\n## 목적함수 = {objective}\n\n" + md(pd.DataFrame(tab), "{}") + "\n"
open(OUT / f"표4.1-4_형평정의_{year}.md", "w", encoding="utf-8").write(out); print(out); print("done", f"{time.time()-t0:.0f}s")
