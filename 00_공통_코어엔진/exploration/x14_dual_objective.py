# -*- coding: utf-8 -*-
"""
x14_dual_objective.py — 이중 목표 제안 경계 (이동 자족성 + 인구 균형) — PC 에서 약 5~15분
===========================================================================================
설계: exploration/이중목표_제안경계_설계.md. 정본은 읽기만 하고 결과는 output/proposal/ 에 쓴다.

문제 (구 g 마다)
  max Q(ℓ)                               (정본 modularity_q 와 같은 정의, 자기 루프 포함)
  s.t. 권역 수 = 공식 생활권 수 k_g, 권역마다 공간 연속, 권역마다 인구 ≥ P_min
시나리오: P5 (P_min 2만 = 공식 생활권 최소 권역 인구 수준), P5_30k, P5_50k (민감도)

알고리즘: 제약 국소 탐색(담금질).
  - 이동 = 경계 동 하나를 인접 권역으로 옮김. 원래 권역이 비거나 끊기는 이동은 금지(개수·연속성 유지).
  - 점수 = Q − λ·(인구 하한 부족분 합), λ = 2 / P_min (부족분이 P_min 만큼이면 벌점 2 > Q 범위) → 사실상 하드 제약.
    최종 해는 "부족분 0 인 해 중 Q 최대"; 부족분 0 이 불가능하면(구 인구 < k·P_min) 부족분 최소 해를 쓰고 표시.
  - 재시작: 정본 분할에서 1번 + 인구 균형 무작위 연결 분할에서 (R−1)번. 온도 T0→T1 기하 감소.
  - 시드 고정: 20260924 + 구 코드 + 연도 + P_min.
출력: output/proposal/p5_partitions.csv  (year, Dong, Ku, scenario, label)
      output/proposal/p5_cost_of_balance.csv / .md  (정본 대비 ΔQ, ΔIFR, 최소 권역 인구, 바뀐 동, 재시작 안정성)
실행: python x14_dual_objective.py [--restarts 40] [--steps 8000] [--workers 8] [--ku 11020 11240] [--pmin 20000 30000 50000]
"""
import argparse, math, time
from concurrent.futures import ProcessPoolExecutor
import pandas as pd
from xcommon import *

PROP = C.OUTPUT_DIR / "proposal"
SCEN = {20000: "P5", 30000: "P5_30k", 50000: "P5_50k"}


def _connected_without(lab, a, i, adj):
    nodes = [j for j in range(len(lab)) if lab[j] == a and j != i]
    if not nodes:
        return False
    seen, stack = {nodes[0]}, [nodes[0]]
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if v != i and lab[v] == a and v not in seen:
                seen.add(v); stack.append(v)
    return len(seen) == len(nodes)


def _stats(A, deg, pop, lab, k):
    L, D, P = np.zeros(k), np.zeros(k), np.zeros(k)
    np.add.at(D, lab, deg); np.add.at(P, lab, pop)
    same = lab[:, None] == lab[None, :]
    iu = np.triu_indices(len(lab))
    Lm = np.where(same, A, 0.0)[iu]
    np.add.at(L, lab[iu[0]], Lm)
    return L, D, P


def anneal(A, adj, pop, k, lab0, pmin, rng, steps, T0=0.02, T1=1e-4):
    n = len(pop)
    m = A[np.triu_indices(n)].sum()
    deg = A.sum(1) + np.diag(A)
    lam = 2.0 / pmin
    lab = lab0.copy()
    L, D, P = _stats(A, deg, pop, lab, k)
    q = float((L / m - (D / (2 * m)) ** 2).sum())
    dfc = float(np.maximum(0, pmin - P).sum())
    size = np.bincount(lab, minlength=k)
    best_feas = (lab.copy(), q) if dfc == 0 else (None, -np.inf)
    best_any = (lab.copy(), q, dfc)
    for t in range(steps):
        T = T0 * (T1 / T0) ** (t / steps)
        i = int(rng.integers(n)); a = lab[i]
        if size[a] == 1:
            continue
        nb = list({lab[j] for j in adj[i] if lab[j] != a})
        if not nb:
            continue
        b = nb[int(rng.integers(len(nb)))]
        if not _connected_without(lab, a, i, adj):
            continue
        wia = A[i, lab == a].sum() - A[i, i]
        wib = A[i, lab == b].sum()
        La, Lb = L[a] - wia - A[i, i], L[b] + wib + A[i, i]
        Da, Db = D[a] - deg[i], D[b] + deg[i]
        dq = ((La - L[a]) + (Lb - L[b])) / m - ((Da ** 2 - D[a] ** 2) + (Db ** 2 - D[b] ** 2)) / (4 * m * m)
        Pa, Pb = P[a] - pop[i], P[b] + pop[i]
        ddf = max(0, pmin - Pa) + max(0, pmin - Pb) - max(0, pmin - P[a]) - max(0, pmin - P[b])
        ds = dq - lam * ddf
        if ds >= 0 or rng.random() < math.exp(ds / T):
            lab[i] = b; size[a] -= 1; size[b] += 1
            L[a], L[b], D[a], D[b], P[a], P[b] = La, Lb, Da, Db, Pa, Pb
            q += dq; dfc += ddf
            if dfc <= 1e-9 and q > best_feas[1]:
                best_feas = (lab.copy(), q)
            if (dfc, -q) < (best_any[2], -best_any[1]):
                best_any = (lab.copy(), q, dfc)
    return best_feas, best_any


def solve_ku(task):
    A, adj, pop, k, lab_c, pmins, seed, steps, restarts = (task[x] for x in ("A", "adj", "pop", "k", "lab_c", "pmins", "seed", "steps", "restarts"))
    out = {}
    t0 = time.time()
    for pmin in pmins:
        rng = np.random.default_rng(seed + pmin)
        starts = [lab_c.copy()]
        while len(starts) < restarts:
            x = random_balanced_partition(adj, k, rng, pop)
            if x is None:
                x = random_connected_partition(adj, k, rng)
            if x is None:
                break
            starts.append(np.asarray(x))
        finals = []
        for s in starts:
            (lf, qf), (la, qa, da) = anneal(A, adj, pop, k, s, pmin, rng, steps)
            finals.append((lf, qf, True) if lf is not None else (la, qa - 10 * da, False))
        feas = [f for f in finals if f[2]]
        pool = feas if feas else finals
        bl, bq, _ = max(pool, key=lambda f: f[1])
        hits = sum(1 for f in pool if abs(f[1] - bq) < 1e-7)
        aris = [ari(bl, f[0]) for f in pool]
        out[pmin] = {"labels": bl, "feasible": bool(feas), "n_feasible_restarts": len(feas), "n_restarts": len(finals),
                     "n_hit_best": hits, "ari_restarts_mean": float(np.mean(aris)), "canon_start_q": finals[0][1]}
    out["_sec"] = time.time() - t0
    return task["ku"], out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--restarts", type=int, default=40)
    ap.add_argument("--steps", type=int, default=8000)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--ku", nargs="*", type=int, default=None, help="일부 구만 (점검용)")
    ap.add_argument("--pmin", nargs="*", type=int, default=list(SCEN))
    ap.add_argument("--seed", type=int, default=20260924)
    a = ap.parse_args()
    PROP.mkdir(parents=True, exist_ok=True)
    lz = load_lz()
    rows, cost = [], []
    for year in YEARS:
        G = all_ku_graphs(year, with_pop=True)
        m, _ = load_leiden(year)
        tasks = []
        for ku in KU_ORDER:
            if a.ku and ku not in a.ku:
                continue
            g = G[ku]
            n = g.n
            A = np.zeros((n, n))
            for (i, j), w in zip(g.edges, g.weights):
                A[i, j] += w
                if i != j:
                    A[j, i] += w
            lab_c = g.labels_from_mapping(m["global_community_id"])
            k = int(lab_c.max()) + 1
            tasks.append({"ku": ku, "A": A, "adj": g.adj, "pop": g.pop, "k": k, "lab_c": lab_c, "pmins": a.pmin,
                          "seed": a.seed + ku + int(year), "steps": a.steps, "restarts": a.restarts})
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            res = dict(ex.map(solve_ku, tasks))
        print(f"[{year}] {len(tasks)}개 구 × P_min {a.pmin}: {time.time() - t0:.0f}s")
        for tk in tasks:
            ku = tk["ku"]; g = G[ku]; lab_c = tk["lab_c"]; lab_o = g.labels_from_mapping(lz["life_zone_id"])
            popc = np.bincount(lab_c, weights=g.pop)
            for pmin in a.pmin:
                r = res[ku][pmin]; l = np.asarray(r["labels"])
                pops = np.bincount(l, weights=g.pop)
                sa, sb = lab_c[:, None] == lab_c[None, :], l[:, None] == l[None, :]
                mv = [g.names[i] for i in np.where((sa != sb).any(axis=1))[0]]
                rows += [{"year": year, "Dong": int(d), "Ku": int(ku), "scenario": SCEN.get(pmin, f"P5_{pmin // 1000}k"), "label": int(x)}
                         for d, x in zip(g.nodes, l)]
                cost.append({"year": year, "구": C.KU_NAME[ku], "P_min": pmin, "k": tk["k"], "구인구": float(g.pop.sum()),
                             "가능": r["feasible"], "정본_최소권역인구": popc.min(), "정본_제약충족": bool(popc.min() >= pmin),
                             "P5_최소권역인구": pops.min(), "Q_정본": g.q(lab_c), "Q_P5": g.q(l), "ΔQ": g.q(l) - g.q(lab_c),
                             "IFR_정본": g.ifr(lab_c), "IFR_P5": g.ifr(l), "IFR_공식": g.ifr(lab_o),
                             "popCV_정본": float(popc.std() / popc.mean()), "popCV_P5": float(pops.std() / pops.mean()),
                             "ARI_정본": ari(lab_c, l), "ARI_공식": ari(lab_o, l), "바뀐동수": len(mv), "바뀐동": ", ".join(mv),
                             "재시작_가능해": r["n_feasible_restarts"], "재시작": r["n_restarts"], "최고해_도달": r["n_hit_best"],
                             "재시작_ARI평균": r["ari_restarts_mean"]})
    P = pd.DataFrame(rows); K = pd.DataFrame(cost)
    P.to_csv(PROP / "p5_partitions.csv", index=False, encoding="utf-8-sig")
    K.to_csv(PROP / "p5_cost_of_balance.csv", index=False, encoding="utf-8-sig")
    L = ["# 이중 목표 제안 경계 — 균형의 비용", "",
         "개수 = 공식 생활권 수, 목적 = Q 최대, 제약 = 권역 인구 ≥ P_min · 공간 연속. 정본(제약 없는 Leiden 합의) 대비 무엇을 포기했는가.", "",
         f"탐색: 재시작 {a.restarts}회(정본 시작 1 + 인구 균형 무작위 시작), 단계 {a.steps}, 시드 {a.seed}.", ""]
    for year in YEARS:
        for pmin in a.pmin:
            x = K[(K.year == year) & (K.P_min == pmin)]
            if not len(x):
                continue
            ch = x[x.바뀐동수 > 0]
            L += [f"## {year} · P_min {pmin:,}", "",
                  f"- 정본이 이미 제약을 충족하는 구 {int(x.정본_제약충족.sum())}/{len(x)} (이 구들은 P5 = 정본이면 비용 0)",
                  f"- 제약을 만족하는 해가 없는 구(구 인구 < k·P_min): {', '.join(x[~x.가능].구) or '없음'}",
                  f"- 정본에서 바뀐 구 {len(ch)}개, 평균 ΔQ {ch.ΔQ.mean() if len(ch) else 0:+.4f}, 최대 손실 {x.ΔQ.min():+.4f}"
                  + (f" ({x.loc[x.ΔQ.idxmin(), '구']})" if len(x) else ""),
                  f"- 서울 IFR(구별 IFR 의 구 인구 가중 평균 — 분자합/분모합 정확값은 scorecard.md): 정본 {x.IFR_정본.mul(x.구인구).sum() / x.구인구.sum():.4f} → P5 {x.IFR_P5.mul(x.구인구).sum() / x.구인구.sum():.4f} (인구 가중 근사)",
                  f"- 권역 인구 CV 평균: 정본 {x.popCV_정본.mean():.2f} → P5 {x.popCV_P5.mean():.2f}; 최소 권역 인구: 정본 {x.정본_최소권역인구.min():,.0f} → P5 {x.P5_최소권역인구.min():,.0f}", "",
                  md_table(x[["구", "k", "가능", "정본_최소권역인구", "P5_최소권역인구", "Q_정본", "Q_P5", "ΔQ", "IFR_공식", "IFR_정본", "IFR_P5",
                              "popCV_정본", "popCV_P5", "ARI_정본", "바뀐동수", "최고해_도달", "재시작_ARI평균"]]), ""]
            if len(ch):
                L += ["바뀐 동:", ""] + [f"- {r.구}: {r.바뀐동}" for r in ch.itertuples()] + [""]
    (PROP / "p5_cost_of_balance.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(l for l in L if l.startswith("## ") or l.startswith("- ")))
    print(f"→ {PROP / 'p5_partitions.csv'}, p5_cost_of_balance.md")


if __name__ == "__main__":
    main()
