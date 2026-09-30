# -*- coding: utf-8 -*-
"""실험 17 (C3): 조정 배치가 만드는 "중심"의 구조 검정.
입력: exp14_placements_{묶음}_{연도}.json 의 COL(무경계 조정)·IND(유형별 독립) 배치.
중심 정의: 배치된 격자를 반경 r(0·300·500 m) 안에서 단일연결로 묶은 군집 중 서로 다른 배치 유형이 2개 이상인 것.
검정:
  (1) 공존: 다유형 중심 수, 다유형 중심에 속한 시설 비율 — 귀무 A: 유형별 개수를 그대로 두고 각 유형 후보지에 무작위 재배치(1,000회), 귀무 B: IND 배치.
  (2) 간격: 다유형 중심 간 최근린 거리 중앙값, Clark–Evans R(=관측 평균 NN / 무작위 기대) — 귀무: 같은 수의 중심을 후보 격자(균등)·인구 비례로 무작위 배치(1,000회).
      비교 기준: 동·공식 생활권·구의 등가 반경 √(평균 면적/π)와 등가 간격 √(평균 면적).
  (3) 단위와의 대응: 공식 생활권·동별 중심 수 분포(0개·1개·2개 이상 권역 비율) vs 귀무.
  (4) 시점 반복: 2020·2025 COL 다유형 중심의 1 km 안 매칭 비율 vs 무작위 점 매칭.
사용: python exp17_centers.py <seoul|logan7> [반복=1000]"""
import sys, json, time
import numpy as np, pandas as pd
from scipy.spatial import cKDTree
from scipy.sparse.csgraph import connected_components
from scipy.sparse import coo_matrix
from bundlelib import Ctx
from r1lib import OUT, X, md

bundle = sys.argv[1]; NR = int(sys.argv[2]) if len(sys.argv) > 2 else 1000; t0 = time.time(); rng = np.random.default_rng(20261002)
ctxs = {}; Ys = {}
for y in ("2020", "2025"):
    ctxs[y] = Ctx(bundle, y, years=Ys); Ys = ctxs[y].Y
M = ctxs["2020"].Yr.M; XY = M[["x_c", "y_c"]].to_numpy()
dong = X.load_dong(); area_dong = dong.geometry.area.mean(); lz = dong.dissolve(by=dong.Dong.map(ctxs["2020"].Yr.lz_map)) if hasattr(dong, "dissolve") else None
area_lz = dong.geometry.area.sum() / 116; area_gu = dong.geometry.area.sum() / 25
EQ = {"동": (np.sqrt(area_dong / np.pi), np.sqrt(area_dong)), "생활권": (np.sqrt(area_lz / np.pi), np.sqrt(area_lz)), "구": (np.sqrt(area_gu / np.pi), np.sqrt(area_gu))}

def centers(placed, r):
    pts, typ = [], []
    for s, js in placed.items():
        for j in js: pts.append(j); typ.append(s)
    if not pts: return np.zeros((0, 2)), 0, 0
    P = XY[np.array(pts)]; typ = np.array(typ)
    if r > 0:
        pairs = cKDTree(P).query_pairs(r, output_type="ndarray")
        G = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(P), len(P))) if len(pairs) else coo_matrix((len(P), len(P)))
        _, lab = connected_components(G, directed=False)
    else:
        _, lab = np.unique(np.array(pts), return_inverse=True)
    df = pd.DataFrame({"lab": lab, "typ": typ, "x": P[:, 0], "y": P[:, 1]})
    g = df.groupby("lab").agg(nt=("typ", "nunique"), n=("typ", "size"), x=("x", "mean"), y=("y", "mean"))
    multi = g[g.nt >= 2]
    return multi[["x", "y"]].to_numpy(), len(multi), int(multi.n.sum())

def nn_stats(C):
    if len(C) < 3: return np.nan, np.nan
    d, _ = cKDTree(C).query(C, k=2); nn = d[:, 1]
    A = dong.geometry.area.sum(); exp = 0.5 * np.sqrt(A / len(C)); return float(np.median(nn)), float(nn.mean() / exp)

rows = []; null_rows = []
for y, ctx in ctxs.items():
    PL = json.load(open(OUT / f"exp14_placements_{bundle}_{y}.json", encoding="utf-8"))
    col = PL["COL_조정_무경계#0"]; ind = PL["IND_유형별독립#0"]
    cand_all = ctx.candALL; popw = ctx.pop[cand_all] / ctx.pop[cand_all].sum() if ctx.pop[cand_all].sum() > 0 else None
    ulz = ctx.Yr.units["공식LZ"]; udong = ctx.Yr.units["동"]
    for r in (0, 300, 500):
        Cc, nc, fc = centers(col, r); Ci, ni, fi = centers(ind, r)
        tot = sum(len(v) for v in col.values())
        med, ce = nn_stats(Cc)
        # 귀무 A: 유형별 무작위 재배치
        nA, fA = [], []
        for _ in range(NR):
            rp = {s: list(rng.choice(ctx.SUB[s][2], len(js), replace=False)) if len(js) else [] for s, js in col.items()}
            _, a, b = centers(rp, r); nA.append(a); fA.append(b)
        # 귀무: 같은 수의 중심을 무작위 점으로 (균등·인구 비례)
        medU, ceU, medP, ceP = [], [], [], []
        for _ in range(min(NR, 300)):
            if nc >= 3:
                U = XY[rng.choice(cand_all, nc, replace=False)]; a, b = nn_stats(U); medU.append(a); ceU.append(b)
                if popw is not None:
                    Pp = XY[rng.choice(cand_all, nc, replace=False, p=popw)]; a, b = nn_stats(Pp); medP.append(a); ceP.append(b)
        # 단위별 중심 수
        def per_unit(Cpts, u):
            if len(Cpts) == 0: return (np.nan, np.nan, np.nan)
            _, gi = cKDTree(XY).query(Cpts); z = u[gi]; cnt = np.bincount(z, minlength=u.max() + 1); valid = np.bincount(u, ctx.pop, minlength=u.max() + 1) > 0
            cv = cnt[valid]; return (float((cv == 0).mean()), float((cv == 1).mean()), float((cv >= 2).mean()))
        lz0, lz1, lz2 = per_unit(Cc, ulz); dg0, dg1, dg2 = per_unit(Cc, udong)
        rows.append({"bundle": bundle, "year": y, "반경m": r, "배치시설": tot, "COL_다유형중심": nc, "COL_중심소속시설비율": fc / max(tot, 1), "IND_다유형중심": ni, "IND_중심소속시설비율": fi / max(tot, 1),
                     "귀무A_다유형중심_중앙": float(np.median(nA)), "귀무A_95분위": float(np.quantile(nA, 0.95)), "p_공존(귀무A≥관측)": float(np.mean(np.array(nA) >= nc)),
                     "중심NN중앙m": med, "ClarkEvansR": ce, "귀무균등_NN중앙m": float(np.nanmedian(medU)) if medU else np.nan, "귀무균등_R": float(np.nanmedian(ceU)) if ceU else np.nan,
                     "p_규칙(균등R≥관측)": float(np.mean(np.array(ceU) >= ce)) if ceU else np.nan, "귀무인구_NN중앙m": float(np.nanmedian(medP)) if medP else np.nan, "귀무인구_R": float(np.nanmedian(ceP)) if ceP else np.nan,
                     "p_규칙(인구R≥관측)": float(np.mean(np.array(ceP) >= ce)) if ceP else np.nan,
                     "생활권_중심0비율": lz0, "생활권_중심1비율": lz1, "생활권_중심2+비율": lz2, "동_중심0비율": dg0, "동_중심1비율": dg1, "동_중심2+비율": dg2})
        print(y, r, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items() if k not in ("bundle",)}, f"{time.time()-t0:.0f}s", flush=True)
# 시점 반복
PL20 = json.load(open(OUT / f"exp14_placements_{bundle}_2020.json", encoding="utf-8"))["COL_조정_무경계#0"]; PL25 = json.load(open(OUT / f"exp14_placements_{bundle}_2025.json", encoding="utf-8"))["COL_조정_무경계#0"]
rep = []
for r in (0, 300, 500):
    C20, n20, _ = centers(PL20, r); C25, n25, _ = centers(PL25, r)
    if len(C20) and len(C25):
        d, _ = cKDTree(C25).query(C20); obs = float((d <= 1000).mean())
        nul = [float((cKDTree(XY[rng.choice(ctxs["2025"].candALL, len(C25), replace=False)]).query(C20)[0] <= 1000).mean()) for _ in range(300)]
        rep.append({"bundle": bundle, "반경m": r, "중심2020": n20, "중심2025": n25, "1km매칭": obs, "귀무_중앙": float(np.median(nul)), "p(귀무≥관측)": float(np.mean(np.array(nul) >= obs))})
D = pd.DataFrame(rows); Rp = pd.DataFrame(rep)
D.to_csv(OUT / f"표4.1-20_중심구조_{bundle}.csv", index=False, encoding="utf-8-sig"); Rp.to_csv(OUT / f"표4.1-20_중심시점반복_{bundle}.csv", index=False, encoding="utf-8-sig")
eq = pd.DataFrame([{"단위": k, "등가반경m": round(v[0]), "등가간격m": round(v[1])} for k, v in EQ.items()])
open(OUT / f"표4.1-20_중심구조_{bundle}.md", "w", encoding="utf-8").write(f"# 표 4.1-20 조정 배치의 중심 구조 ({bundle}; 귀무 {NR}회)\n\n" + md(D.round(3), "{}") + "\n\n## 시점 반복\n\n" + md(Rp.round(3), "{}") + "\n\n## 단위 등가 크기\n\n" + md(eq, "{}"))
print(eq.to_string(index=False)); print(Rp.round(3).to_string(index=False)); print("done", f"{time.time()-t0:.0f}s")
