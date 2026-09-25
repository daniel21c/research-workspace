# -*- coding: utf-8 -*-
"""
x7_maxp_regions.py — C2 max-p-regions: 인구 하한만 주고 개수는 최대로 (Duque et al. 2012)
================================================================================================
생활권을 "최소 인구 규모를 갖춘 계획단위"로 본다면, 개수는 인구 하한에서 결정된다.
max-p 는 (1) 모든 권역이 연결되어 있고 (2) 각 권역 인구 ≥ 하한 이라는 조건에서 권역 수 p 를 최대로 하고,
그다음 권역 안 이질성을 최소로 한다.

이질성 속성 = 동의 "이동 프로파일": 구 안 각 동과 주고받는 통행(f_ij+f_ji) 비율 벡터를 주성분 5개로 줄여 표준화.
  → 같은 곳과 주로 오가는 동끼리 묶이게 한다. (max-p 는 "서로 오가는가"가 아니라 "비슷한가"를 본다는 점이 Leiden 과 다름)
인구 하한 = 4만~12만 (구 인구가 하한의 두 배 미만이면 1개로 기록).

풀이: Duque et al.(2012) 의 구성 단계를 그대로 직접 구현 (spopt MaxPHeuristic 은 구에 따라 한 번에 수 분~멈춤 → 대체).
  1. 배정 안 된 동 하나를 무작위로 골라 권역 시작 → 붙어 있는 미배정 동 중 속성이 가장 가까운 동을 더해 인구 ≥ 하한이 될 때까지 키움.
     못 채우면 그 동들은 "남는 동"으로 둠.  2. 남는 동은 붙어 있는 권역 중 속성이 가장 가까운 곳에 붙임.
  3. 이를 --restarts 번(기본 500) 반복해 p 최대 → 권역 안 이질성(SSD) 최소 해를 택한다. (담금질 개선 단계는 생략)

출력: output/exploration/x7/maxp_sweep.csv, maxp_labels.csv, x7_report.md
실행: python x7_maxp_regions.py --workers 8 [--restarts 500] [--seed 20260924]   (8코어 1~3분)      
"""
import argparse, warnings
import concurrent.futures as cf
from xcommon import *

FLOORS = (40_000, 50_000, 60_000, 70_000, 80_000, 100_000, 120_000)


def profile(g, dims=5):
    S = g.W + g.W.T
    R = S / S.sum(1, keepdims=True)
    R = R - R.mean(0)
    U, s, _ = np.linalg.svd(R, full_matrices=False)
    k = min(dims, g.n - 1)
    X = U[:, :k] * s[:k]
    return (X - X.mean(0)) / np.where(X.std(0) > 0, X.std(0), 1)


def ssd(X, lab):
    return float(sum(((X[lab == c] - X[lab == c].mean(0)) ** 2).sum() for c in np.unique(lab)))


def maxp(adj, pop, X, floor, restarts, rng):
    n = len(adj)
    best = None
    for _ in range(restarts):
        lab = -np.ones(n, dtype=int); p = 0
        for s in rng.permutation(n):
            if lab[s] >= 0:
                continue
            members, tot = [s], pop[s]; lab[s] = p
            while tot < floor:
                cand = {u for v in members for u in adj[v] if lab[u] < 0}
                if not cand:
                    break
                cen = X[members].mean(0)
                u = min(cand, key=lambda c: ((X[c] - cen) ** 2).sum() + rng.random() * 1e-9)
                lab[u] = p; members.append(u); tot += pop[u]
            if tot >= floor:
                p += 1
            else:
                lab[members] = -2                          # 남는 동
        if p == 0:
            continue
        left = list(np.where(lab == -2)[0])
        while left:                                        # 남는 동을 이웃 권역에 붙임
            moved = False
            for v in list(left):
                nb = {lab[u] for u in adj[v] if lab[u] >= 0}
                if nb:
                    lab[v] = min(nb, key=lambda r: ((X[v] - X[lab == r].mean(0)) ** 2).sum()); left.remove(v); moved = True
            if not moved:
                break
        if left:
            continue
        key = (p, -ssd(X, lab))
        if best is None or key > best[0]:
            best = (key, lab.copy())
    return None if best is None else best[1]


def job(args):
    """구 하나: 인구 하한별 max-p. 구 인구가 하한의 두 배 미만이면 p=1(구 전체 한 권역)로 기록."""
    year, ku, restarts, seed = args
    import time
    t0 = time.time()
    g = KuGraph(ku, load_dong(), load_od(year), load_pop(year))
    lz = load_lz(); m, _ = load_leiden(year)
    X = profile(g)
    off = g.labels_from_mapping(lz["life_zone_id"]); lei = g.labels_from_mapping(m["global_community_id"])
    rows, labs = [], []
    for fl in FLOORS:
        rng = np.random.default_rng(seed + ku + int(year) + fl)
        lab = np.zeros(g.n, dtype=int) if g.pop.sum() < 2 * fl else maxp(g.adj, g.pop, X, fl, restarts, rng)
        if lab is None:
            lab = np.zeros(g.n, dtype=int)
        lab = np.asarray(pd.factorize(lab)[0])
        zp = np.bincount(lab, weights=g.pop)
        rows.append({"year": year, "구": C.KU_NAME[ku], "공식k": C.TARGET_COMMUNITIES[ku], "인구하한": fl,
                     "k": int(lab.max()) + 1, "IFR": g.ifr(lab), "Q": g.q(lab), "pop_cv": float(zp.std() / zp.mean()),
                     "ARI_vs_공식": ari(lab, off), "ARI_vs_Leiden": ari(lab, lei)})
        labs += [{"year": year, "Dong": d, "인구하한": fl, "label": int(l)} for d, l in zip(g.nodes, lab)]
    return rows, labs, round(time.time() - t0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--restarts", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20260924)
    ap.add_argument("--workers", type=int, default=C.N_WORKERS)
    ap.add_argument("--ku", nargs="*", type=int, default=None)
    a = ap.parse_args()
    for y in YEARS:
        load_pop(y)                                    # 인구 캐시를 먼저 만들어 둠 (병렬 작업 간 충돌 방지)
    tasks = [(y, ku, a.restarts, a.seed) for y in YEARS for ku in (a.ku or KU_ORDER)]
    rows, labs = [], []
    with cf.ProcessPoolExecutor(max_workers=a.workers) as ex:
        for i, f in enumerate(cf.as_completed([ex.submit(job, t) for t in tasks]), 1):
            r, l, sec = f.result(); rows += r; labs += l
            print(f"[{i}/{len(tasks)}] {r[0]['year']} {r[0]['구']} k={[x['k'] for x in r]} {sec}s", flush=True)
    rows.sort(key=lambda r: (r["year"], r["구"], r["인구하한"]))
    d = pd.DataFrame(rows)
    save(d, "maxp_sweep", "x7"); save(pd.DataFrame(labs), "maxp_labels", "x7")
    tot = d.groupby(["year", "인구하한"]).agg(k합계=("k", "sum"), IFR평균=("IFR", "mean"), Q평균=("Q", "mean"),
                                           popCV=("pop_cv", "mean"), ARI공식=("ARI_vs_공식", "mean"),
                                           ARI_Leiden=("ARI_vs_Leiden", "mean")).reset_index()
    tot["공식과같은구"] = [int(d[(d.year == r.year) & (d.인구하한 == r.인구하한)].eval("k == 공식k").sum()) for r in tot.itertuples()]
    save(tot, "maxp_totals", "x7")
    L = ["# x7 — C2 max-p-regions (인구 하한 → 개수 최대)", "",
         f"속성 = 이동 프로파일(구 안 동별 교류 비율의 주성분 5개). 하한마다 구성 {a.restarts}회 중 p 최대·이질성 최소 해.", "",
         md_table(tot), ""]
    for y in YEARS:
        t = tot[tot.year == y]; b = t.iloc[(t["k합계"] - C.N_LZ).abs().argmin()]
        x = d[(d.year == y) & (d.인구하한 == b["인구하한"])]
        L += [f"## {y}", "",
              f"- 합계가 116 에 가장 가까운 하한 {int(b['인구하한']):,}명 → 합계 {b['k합계']}, 공식과 같은 구 {b['공식과같은구']}/25, "
              f"평균 IFR {b['IFR평균']:.3f}, ARI(공식) {b['ARI공식']:.3f}, ARI(Leiden) {b['ARI_Leiden']:.3f}", "",
              md_table(x[["구", "공식k", "k", "IFR", "Q", "pop_cv", "ARI_vs_공식", "ARI_vs_Leiden"]]), ""]
    (out_dir("x7") / "x7_report.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join([l for l in L if l.startswith("- ") or l.startswith("## ")]))


if __name__ == "__main__":
    main()
