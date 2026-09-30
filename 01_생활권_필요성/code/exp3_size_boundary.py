# -*- coding: utf-8 -*-
"""실험 3: 크기 효과와 경계 효과의 분리.
(A) 무작위 연접 구획 k=50,80,116,160,250 (구 안 연접 병합, 인구 균형) + 구 25 + 동 424 + 공식·Leiden: 지표를 k 곡선으로.
(B) 116개에서 귀무 3종(인구균형·동수균형·자유)에 대한 치환 분위와 25개 구 부호검정.
지표: IFR, 경계 제한 손실(진단 시설), 도서관 도달권이 걸치는 단위 수, 은폐 H_AUC·FGT0(τ_main), K_min(τ_main, 탐욕), 효율 유지율@32, 안정성(2020↔2025 ρ·Jaccard).
사용: python exp3_size_boundary.py [반복116=150] [반복기타=40] [귀무반복=100]"""
import sys, time, json
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from r1lib import Year, OUT, md, DIAG_SETS

R116 = int(sys.argv[1]) if len(sys.argv) > 1 else 150
ROTH = int(sys.argv[2]) if len(sys.argv) > 2 else 40
RNULL = int(sys.argv[3]) if len(sys.argv) > 3 else 100
K = 32; rng = np.random.default_rng(20260927); t0 = time.time()
Y = {y: Year(y) for y in ("2020", "2025")}
LOSS_SETS = ["도서관", "문화", "행정안전", "유치원10분", "어린이집5분", "초등학교15분", "의원10분", "생활체육10분"]
def wmedian(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return x[o][np.searchsorted(cw, cw[-1] / 2)]
r_none, C_none, tau_main, cand, base_gain = {}, {}, {}, {}, {}
for y, Yr in Y.items():
    r_none[y] = {f: Yr.reach(f) for f in LOSS_SETS}; C_none[y] = {f: Yr.cov(r_none[y][f]) for f in LOSS_SETS}
    Cd, dd = Yr.unit_cov(Yr.units["동"], r_none[y]["도서관"]); tau_main[y] = 0.6 * wmedian(Cd[dd > 0], dd[dd > 0])
    cand[y] = Yr.candidates("도서관"); p0, _, _ = Yr.place(r_none[y]["도서관"], None, 0, K, cand[y])
    base_gain[y] = (Yr.pop * Yr.cov_after(r_none[y]["도서관"], p0, K)).sum() - (Yr.pop * r_none[y]["도서관"]).sum()
print("loaded", {y: round(v, 3) for y, v in tau_main.items()}, f"{time.time()-t0:.0f}s", flush=True)

def metrics(s, tag, k, rep, full=True):
    out = {}; ucov = {}
    for y, Yr in Y.items():
        u = Yr.dong_series_to_units(s); pop = Yr.pop
        row = {"tag": tag, "k": k, "rep": rep, "year": y, "n_units": int(u.max() + 1), "IFR": Yr.ifr(s)}
        den = np.bincount(u, pop); row["pop_cv"] = den[den > 0].std() / den[den > 0].mean()
        for f in LOSS_SETS:
            row[f"loss_{f}"] = C_none[y][f] - Yr.cov(Yr.reach(f, u))
        r = r_none[y]["도서관"]; row["Hauc_도서관"] = Yr.H_curve(u, r, C_none[y]["도서관"]).mean()
        Cu, dn = Yr.unit_cov(u, r); v = dn > 0; below = v & (Cu < tau_main[y])
        row["FGT0_도서관"] = dn[below].sum() / dn[v].sum(); row["소외단위수"] = int(below.sum())
        row["span_lib"] = Yr.catchment_spans(u, "도서관")
        if full:
            pk, kmin, sf = Yr.place(r, u, tau_main[y], K, cand[y], kcap=700)
            c = Yr.cov_after(r, pk, K); row["Kmin"] = kmin if kmin is not None else np.nan
            row["Reff"] = ((pop * c).sum() - (pop * r).sum()) / base_gain[y]
        ucov[y] = (Cu, dn); out[y] = row
    a, da = ucov["2020"]; b, db = ucov["2025"]; ok = (da > 0) & (db > 0)
    rho = spearmanr(a[ok], b[ok]).correlation; na = max(1, int(ok.sum() * 0.1))
    ia = set(np.argsort(a[ok])[:na]); ib = set(np.argsort(b[ok])[:na]); jac = len(ia & ib) / len(ia | ib)
    for y in out: out[y]["stab_rho"] = rho; out[y]["stab_jac10"] = jac
    return list(out.values())

Y20 = Y["2020"]
rows = []
rows += metrics(pd.Series(Y20.dong_gdf.index, index=Y20.dong_gdf.index), "동", 424, 0)
rows += metrics(Y20.dong_gdf["Ku"], "구", 25, 0)
rows += metrics(Y20.lz_map, "공식LZ", 116, 0); rows += metrics(Y20.ld_map, "Leiden2020", 116, 0); rows += metrics(Y["2025"].ld_map, "Leiden2025", 116, 0)
for k in (50, 80, 116, 160, 250):
    R = R116 if k == 116 else ROTH
    for rep in range(R):
        rows += metrics(Y20.random_partition(k, rng, balance="pop"), f"rand{k}", k, rep)
        if rep % 10 == 0:
            print(f"k={k} rep={rep} {time.time()-t0:.0f}s", flush=True); pd.DataFrame(rows).to_csv(OUT / "표4.1-3_크기축_구획별.csv", index=False, encoding="utf-8-sig")
# 귀무 3종 (116, 배치 없이)
for rep in range(RNULL):
    for null in ("dong", "free"):
        rows += metrics(Y20.random_partition(116, rng, balance=null), f"null116_{null}", 116, rep, full=False)
    if rep % 20 == 0: print(f"null rep={rep} {time.time()-t0:.0f}s", flush=True)
D = pd.DataFrame(rows); D.to_csv(OUT / "표4.1-3_크기축_구획별.csv", index=False, encoding="utf-8-sig")
# 요약
def summarize(D):
    out = "# 표 4.1-3 크기 축 (무작위 구획 중앙값 [5~95 분위]) 과 116개 치환 검정\n\n"
    cols = ["IFR", "loss_도서관", "loss_문화", "loss_유치원10분", "loss_어린이집5분", "Hauc_도서관", "FGT0_도서관", "소외단위수", "Kmin", "Reff", "span_lib", "stab_rho", "pop_cv"]
    for y in ("2020", "2025"):
        d = D[D.year == y]; out += f"\n## {y} 크기 축\n\n"; tab = []
        for tag in ("구", "rand50", "rand80", "rand116", "공식LZ", "Leiden2020", "Leiden2025", "rand160", "rand250", "동"):
            g = d[d.tag == tag]
            if g.empty: continue
            row = {"구획": tag, "k": int(g.k.iloc[0]), "n": len(g)}
            for c in cols:
                v = g[c].astype(float).dropna()
                if v.empty: row[c] = ""; continue
                row[c] = f"{v.median():.3f}" if len(v) == 1 else f"{v.median():.3f} [{v.quantile(.05):.3f}~{v.quantile(.95):.3f}]"
            tab.append(row)
        out += md(pd.DataFrame(tab), "{}")
        out += f"\n\n## {y} 116개 치환 검정 (분위 = 귀무 중 값이 더 작은 비율; 손실·FGT0·K_min·span 은 작을수록, IFR·Reff 는 클수록 좋음)\n\n"; tab = []
        for tag in ("공식LZ", "Leiden2020", "Leiden2025"):
            x = d[d.tag == tag].iloc[0]
            for null, ntag in (("인구균형", "rand116"), ("동수균형", "null116_dong"), ("자유", "null116_free")):
                r = d[d.tag == ntag]; row = {"구획": tag, "귀무": null, "n": len(r)}
                for c in cols:
                    if np.isnan(x[c]) or r[c].dropna().empty: row[c] = ""; continue
                    row[c] = f"p{(r[c].astype(float) < x[c]).mean():.2f}"
                tab.append(row)
        out += md(pd.DataFrame(tab), "{}") + "\n"
    return out
S = summarize(D); open(OUT / "표4.1-3_크기축_요약.md", "w", encoding="utf-8").write(S); print(S); print("done", f"{time.time()-t0:.0f}s")
