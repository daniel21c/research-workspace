# -*- coding: utf-8 -*-
"""
x4_null_model_q.py — B3 귀무모형 대비 Modularity 유의성으로 개수 고르기
=========================================================================
"Q 가 높다"는 것이 구조가 있어서인지, 그 구의 동별 통행 규모(차수) 때문인지 구분하려고, 동별 통행 총량은 거의 그대로
두고 누가 누구와 통행하는지만 뒤섞은 무작위 그래프(귀무)에서도 같은 절차로 Q 를 구해 비교한다.

귀무 그래프 (가중 구성모형 계열)
  - 동 내부 통행(자기 루프)은 그대로 둔다.
  - 동 쌍 i≠j 의 가중치를 평균이 s_i·s_j/(2m) 인 지수분포에서 새로 뽑는다 (s = 동 간 통행 총량, m = 총합).
  - 대칭 IPF 로 각 동의 동 간 통행 총량 s_i 를 원래 값에 정확히 맞춘다.
  → 차수(통행 규모)는 같고 구조는 없는 그래프.

절차 (실제 그래프와 귀무 그래프에 똑같이 적용)
  - 해상도 γ = 0.05~2.50 (0.05 간격, 50개) 마다 Leiden 을 n_iter 번(기본 20) 돌려 Q 가 가장 높은 분할을 취한다 (반복별 시드).
  - 커뮤니티 수 k 별 최대 Q: Q_obs(k), Q_null(k).
  - z(k) = (Q_obs(k) − 평균 Q_null(k)) / sd Q_null(k).  z 가 가장 큰 k = "우연 대비 구조가 가장 뚜렷한 개수".
  정본 합의(3,000회)가 아니라 빠른 절차라, 실제·귀무에 같은 절차를 쓰는 것이 핵심이다.

출력: output/exploration/x4/null_q_curves.csv, null_q_kstar.csv, x4_report.md
실행: python x4_null_model_q.py --workers 8 [--nulls 30] [--n-iter 20] [--seed 20260924]
      (8코어 약 5분)
"""
import argparse, time
import concurrent.futures as cf
from xcommon import *


def sym_matrix(g):
    M = np.zeros((g.n, g.n))
    for (i, j), w in zip(g.edges, g.weights):
        M[i, j] = w; M[j, i] = w
    return M


def to_edges(M):
    n = len(M); E, W = [], []
    for i in range(n):
        if M[i, i] > 0:
            E.append((i, i)); W.append(M[i, i])
        for j in range(i + 1, n):
            if M[i, j] > 0:
                E.append((i, j)); W.append(M[i, j])
    return np.asarray(E, dtype=np.int64).reshape(-1, 2), np.asarray(W)


def null_matrix(M, rng, iters=200):
    diag = np.diag(M).copy()
    O = M.copy(); np.fill_diagonal(O, 0)
    s = O.sum(1); m2 = s.sum()
    mean = np.outer(s, s) / m2
    R = rng.exponential(1.0, size=M.shape) * mean
    R = np.triu(R, 1); R = R + R.T
    for _ in range(iters):                       # 대칭 IPF: 행 합을 s 에 맞춤
        f = np.sqrt(s / np.maximum(R.sum(1), 1e-12))
        R = R * f[:, None] * f[None, :]
    np.fill_diagonal(R, diag)
    return R


def scan_best_q(edges, weights, n, res_grid, n_iter, seed0):
    import igraph as ig, leidenalg
    G = ig.Graph(n=n, edges=edges.tolist()); G.es["weight"] = list(map(float, weights))
    best = {}
    sd = seed0
    for res in res_grid:
        top_q, top_k = -1, None
        for _ in range(n_iter):
            p = leidenalg.find_partition(G, leidenalg.RBConfigurationVertexPartition, resolution_parameter=float(res),
                                         weights="weight", seed=int(sd) % (2**31 - 1)); sd += 1
            lab = np.asarray(p.membership)
            q = modularity_q(edges, weights, lab)
            if q > top_q:
                top_q, top_k = q, int(lab.max()) + 1
        if top_k >= 2:
            best[top_k] = max(best.get(top_k, -1), top_q)
    return best


def job(args):
    year, ku, nulls, n_iter, seed = args
    t0 = time.time()
    dong, od = load_dong(), load_od(year)
    g = KuGraph(ku, dong, od)
    res_grid = np.round(np.arange(0.05, 2.5001, 0.05), 4)
    rng = np.random.default_rng(seed + ku * 7 + int(year))
    obs = scan_best_q(g.edges, g.weights, g.n, res_grid, n_iter, seed + ku * 1_000_003)
    M = sym_matrix(g)
    null = []
    for t in range(nulls):
        E, W = to_edges(null_matrix(M, rng))
        null.append(scan_best_q(E, W, g.n, res_grid, n_iter, seed + ku * 1_000_003 + (t + 1) * 100_000))
    rows = []
    for k in sorted(set(obs) | {k for d in null for k in d}):
        nv = np.array([d[k] for d in null if k in d])
        rows.append({"year": year, "ku": ku, "구": C.KU_NAME[ku], "k": k, "Q_obs": obs.get(k, np.nan),
                     "Q_null_mean": nv.mean() if len(nv) else np.nan, "Q_null_sd": nv.std() if len(nv) > 1 else np.nan,
                     "n_null": len(nv)})
    return rows, round(time.time() - t0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=C.N_WORKERS)
    ap.add_argument("--nulls", type=int, default=30)
    ap.add_argument("--n-iter", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20260924)
    ap.add_argument("--ku", nargs="*", type=int, default=None)
    a = ap.parse_args()
    kus = a.ku or KU_ORDER
    tasks = [(y, ku, a.nulls, a.n_iter, a.seed) for y in YEARS for ku in kus]
    rows = []
    with cf.ProcessPoolExecutor(max_workers=a.workers) as ex:
        for i, f in enumerate(cf.as_completed([ex.submit(job, t) for t in tasks]), 1):
            r, sec = f.result(); rows += r
            print(f"[{i}/{len(tasks)}] {r[0]['year']} {r[0]['구']} {sec}s", flush=True)
    d = pd.DataFrame(rows)
    d["z"] = (d["Q_obs"] - d["Q_null_mean"]) / d["Q_null_sd"]
    save(d, "null_q_curves", "x4")
    ks = []
    for (y, ku), x in d.groupby(["year", "ku"]):
        x = x[(x["n_null"] >= max(2, a.nulls // 2)) & x["z"].notna() & (x["k"] >= 2)]
        k0 = C.TARGET_COMMUNITIES[ku]
        if x.empty:
            continue
        b = x.loc[x["z"].idxmax()]
        z0 = x.set_index("k")["z"].get(k0, np.nan)
        ks.append({"year": y, "구": C.KU_NAME[ku], "공식k": k0, "k_z최대": int(b["k"]), "z_max": b["z"], "z_공식k": z0,
                   "Q_obs_공식k": x.set_index("k")["Q_obs"].get(k0, np.nan), "Q_null_공식k": x.set_index("k")["Q_null_mean"].get(k0, np.nan)})
    kd = pd.DataFrame(ks, columns=["year", "구", "공식k", "k_z최대", "z_max", "z_공식k", "Q_obs_공식k", "Q_null_공식k"])
    save(kd, "null_q_kstar", "x4")
    L = ["# x4 — B3 귀무모형 대비 Q 유의성", "",
         f"귀무 그래프 {a.nulls}개/구(동 간 통행 총량 보존, 구조 제거). 해상도 50개 × Leiden {a.n_iter}회로 k별 최대 Q 를 실제·귀무에 같은 절차로 구함.", ""]
    for y in YEARS:
        x = kd[kd.year == y]
        L += [f"## {y}", "",
              f"- z 최대 개수 합계 {x['k_z최대'].sum()} (공식 116). z 최대 개수 = 공식 개수인 구 {int((x['k_z최대'] == x['공식k']).sum())}/{len(x)}",
              f"- 공식 개수에서의 z 중앙값 {x['z_공식k'].median():.1f} (z>3 인 구 {int((x['z_공식k'] > 3).sum())}/{len(x)})", "",
              md_table(x.drop(columns="year")), ""]
    (out_dir("x4") / "x4_report.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join([l for l in L if l.startswith("- ") or l.startswith("## ")]))


if __name__ == "__main__":
    main()
