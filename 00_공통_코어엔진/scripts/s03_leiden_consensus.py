# -*- coding: utf-8 -*-
"""
s03_leiden_consensus.py — 자치구별 Leiden 합의 구획 (2020 / 2025)
=====================================================================
방법은 JTG 게재본 → 2025-10 재구현(251022_Leiden_25_scan_병렬_중복해결.py)의 절차를 그대로 따르고,
기록만 늘렸다. 결정 근거는 ../결정기록.md.

구 하나에 대해:
  [그래프]  일상통행 OD(od_daily)에서 출발·도착이 모두 이 구인 행을 가져와
            동 i–j 가중치 = f_ij + f_ji (무방향), 동 내부 통행 f_ii 는 자기 루프로 포함(config.INCLUDE_SELF_LOOPS).
  [스캔]    해상도 γ = 0.01, 0.02, …, 2.50 (250개) 마다 아래 [합의]를 한 번씩 수행하고 결과를 모두 기록.
  [합의]    Leiden(RBConfiguration, weight, seed=None)을 N_ITER(3,000)번 실행.
            ① co-association: 동 쌍 (i,j)가 같은 커뮤니티였던 횟수 / N_ITER → 확률 행렬 P.
               P_ij ≥ τ(0.5)인 쌍을 이어 연결요소 = 합의 분할 (정본). 라벨 번호를 쓰지 않으므로 라벨 스위칭과 무관.
            ② 같은 3,000개 결과를 라벨 정규화(동코드 오름차순으로 처음 나오는 묶음부터 0,1,2…)해
               가장 자주 나온 분할(최빈 분할)과 빈도를 세고, ①과 같은 분할인지 기록. (설명·검증용, 정본 아님)
  [평가]    분할마다 커뮤니티 수, Modularity Q(자기 루프 포함, python-louvain 정의와 동일), IFR
            IFR = (출발이 이 구 & 출발·도착이 같은 커뮤니티인 통행량) / (출발이 이 구인 서울 내 모든 통행량)
  [선정]    커뮤니티 수 == 구 목표 개수(공식 생활권 수)인 해상도 중 Q 최대, 동점이면 IFR 최대.
            없으면 목표 아래/위로 가장 가까운 두 해상도 사이를 FINE_SCAN_STEPS 등분해 다시 스캔.
  [안정성]  확정 해상도에서 [합의]를 STABILITY_TRIALS(10)번 독립 반복해 확정 분할과의 ARI, 매번 달라진 동을 기록.
  [번호]    확정 커뮤니티 번호는 총 출발통행량 내림차순으로 0,1,2… (연도 간 번호 안정용. 번호 자체는 의미 없음)

출력 (output/leiden/{year}/)
  metrics/leiden_mapping_{year}.csv            Dong, Ku, community, global_community_id(=Ku*100+community), 소속확률
  metrics/leiden_metrics_{year}.csv/.xlsx      구별 확정 해상도·Q·IFR·안정성 요약
  resolution_scan_logs/{ku}_{year}.csv         해상도별 전 기록
  stability/{ku}_{year}.json                   독립 반복 ARI, 달라진 동
  coassoc/{ku}_{year}_coassoc.csv              확정 해상도 co-association 행렬
  coassoc/{ku}_{year}_runs.npz                 확정 해상도 3,000회 원시 라벨 (재검증용)
  boundaries/leiden_communities_{year}.gpkg    커뮤니티 경계 (dissolve)
  run_info.json, leiden_run_{ts}.log

실행:  python s03_leiden_consensus.py --years 2020 2025 --workers 4
       python s03_leiden_consensus.py --years 2020 --ku 11010 --n-iter 30 --res-step 0.1   (빠른 점검)
"""
import sys, os, json, time, argparse, logging, datetime
from collections import Counter
from pathlib import Path
import concurrent.futures as cf

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C

log = logging.getLogger("s03")


# ──────────────────────────────────────────────────────────────────────────────
# 순수 함수들 (검증 스크립트에서도 import 해서 쓴다)
# ──────────────────────────────────────────────────────────────────────────────
def canonical_labels(mem: np.ndarray) -> tuple:
    """라벨 정규화: 노드 순서대로 처음 나오는 묶음부터 0,1,2… → 같은 분할이면 같은 튜플"""
    out = np.empty(len(mem), dtype=np.int32)
    seen = {}
    for i, l in enumerate(mem):
        if l not in seen:
            seen[l] = len(seen)
        out[i] = seen[l]
    return tuple(out.tolist())


def ari(a, b) -> float:
    """Adjusted Rand Index (Hubert & Arabie 1985). 라벨 번호와 무관하게 두 분할의 일치도. 1=동일."""
    a, b = np.asarray(a), np.asarray(b)
    n = len(a)
    if n < 2:
        return 1.0
    ct = pd.crosstab(a, b).values
    comb = lambda x: x * (x - 1) / 2.0
    sum_ij = comb(ct).sum()
    sum_a = comb(ct.sum(axis=1)).sum()
    sum_b = comb(ct.sum(axis=0)).sum()
    total = comb(n)
    expected = sum_a * sum_b / total
    max_idx = (sum_a + sum_b) / 2.0
    if max_idx == expected:
        return 1.0
    return float((sum_ij - expected) / (max_idx - expected))


def modularity_q(edges: np.ndarray, weights: np.ndarray, labels: np.ndarray) -> float:
    """
    무방향 가중 그래프의 Modularity Q. python-louvain(community.modularity)과 같은 관례:
      m = 모든 간선 가중치 합 (자기 루프는 1번),  d_i = 노드 i 의 가중 차수 (자기 루프는 2w 로 셈)
      Q = Σ_c [ L_c / m − ( D_c / 2m )² ],  L_c = 커뮤니티 c 안 간선 가중치 합(자기 루프 포함), D_c = Σ_{i∈c} d_i
    edges: (E,2) 노드 인덱스, weights: (E,), labels: (n,)
    """
    m = float(weights.sum())
    if m <= 0:
        return 0.0
    n = int(labels.max()) + 1
    src, dst = edges[:, 0], edges[:, 1]
    deg = np.zeros(len(labels))
    np.add.at(deg, src, weights)
    np.add.at(deg, dst, weights)            # 자기 루프면 같은 노드에 두 번 더해져 2w
    same = labels[src] == labels[dst]
    L = np.bincount(labels[src[same]], weights=weights[same], minlength=n)
    D = np.bincount(labels, weights=deg, minlength=n)
    return float((L / m - (D / (2 * m)) ** 2).sum())


def consensus_once(ig_G, n_nodes: int, resolution: float, n_iter: int, tau: float, seed_base=None):
    """
    [합의] 한 번. 반환 dict:
      labels        : co-association 연결요소 분할 (정본), 길이 n_nodes
      coassoc       : (n,n) 확률 행렬
      runs          : (n_iter, n) 원시 라벨
      modal         : 최빈 분할 튜플, modal_count, modal_n_comm, modal_equals_cc
      n_distinct    : 서로 다른 분할 수
    """
    import igraph as ig, leidenalg
    runs = np.empty((n_iter, n_nodes), dtype=np.int16)
    co = np.zeros((n_nodes, n_nodes), dtype=np.int32)
    for k in range(n_iter):
        seed = None if seed_base is None else int(seed_base) + k
        part = leidenalg.find_partition(ig_G, leidenalg.RBConfigurationVertexPartition,
                                        resolution_parameter=resolution, weights="weight", seed=seed)
        mem = np.asarray(part.membership, dtype=np.int16)
        runs[k] = mem
        co += (mem[:, None] == mem[None, :])
    P = co / float(n_iter)
    iu = np.triu_indices(n_nodes, k=1)
    keep = P[iu] >= tau
    H = ig.Graph(n=n_nodes, edges=list(zip(iu[0][keep].tolist(), iu[1][keep].tolist())))
    labels = np.asarray(H.connected_components().membership, dtype=np.int32)

    cnt = Counter(canonical_labels(runs[k]) for k in range(n_iter))
    modal, modal_count = cnt.most_common(1)[0]
    modal_arr = np.asarray(modal, dtype=np.int32)
    return {"labels": labels, "coassoc": P, "runs": runs,
            "modal": modal_arr, "modal_count": int(modal_count), "modal_n_comm": int(modal_arr.max()) + 1,
            "modal_equals_cc": bool(ari(labels, modal_arr) == 1.0), "n_distinct": len(cnt)}


def contiguity(labels: np.ndarray, adj: list) -> dict:
    """커뮤니티별 공간 연결요소 수 (adj: 노드별 인접 노드 인덱스 리스트). 1이면 연속."""
    import igraph as ig
    out = {}
    for c in np.unique(labels):
        idx = np.where(labels == c)[0]
        pos = {v: i for i, v in enumerate(idx)}
        e = [(pos[v], pos[u]) for v in idx for u in adj[v] if u in pos and v < u]
        out[int(c)] = len(ig.Graph(n=len(idx), edges=e).connected_components())
    return out


# ──────────────────────────────────────────────────────────────────────────────
# 구 단위 작업 (별도 프로세스에서 실행)
# ──────────────────────────────────────────────────────────────────────────────
def run_ku(task: dict) -> dict:
    import igraph as ig
    t0 = time.time()
    ku, year = task["ku"], task["year"]
    nodes = task["nodes"]                       # 동 코드 오름차순 (n,)
    n = len(nodes)
    idx = {d: i for i, d in enumerate(nodes)}
    target = C.TARGET_COMMUNITIES[ku]
    p = task["params"]
    msgs = []

    # 그래프: 구 내부 OD → 무방향 대칭화 (+ 자기 루프)
    od_in = task["od_in"]                       # (dong_O, dong_D, flow) 출발·도착 모두 이 구
    W = np.zeros((n, n))
    for o, d, f in od_in:
        W[idx[o], idx[d]] += f
    S = W + W.T
    edges, weights = [], []
    for i in range(n):
        if p["self_loops"] and W[i, i] > 0:
            edges.append((i, i)); weights.append(W[i, i])
        for j in range(i + 1, n):
            if S[i, j] > 0:
                edges.append((i, j)); weights.append(S[i, j])
    edges = np.asarray(edges, dtype=np.int64).reshape(-1, 2)
    weights = np.asarray(weights, dtype=np.float64)
    G = ig.Graph(n=n, edges=edges.tolist(), directed=False)
    G.es["weight"] = weights.tolist()

    # IFR 용: 출발이 이 구인 서울 내 모든 OD
    od_from = task["od_from"]                   # (dong_O, dong_D, flow), dong_D 는 서울 어디든
    o_i = np.asarray([idx[o] for o, _, _ in od_from])
    d_i = np.asarray([idx.get(d, -1) for _, d, _ in od_from])
    f_v = np.asarray([f for *_, f in od_from], dtype=np.float64)
    total_out = float(f_v.sum())

    def evaluate(labels):
        q = modularity_q(edges, weights, labels)
        inside = d_i >= 0
        internal = float(f_v[inside & (labels[o_i] == labels[np.where(inside, d_i, 0)])].sum())
        return q, internal, (internal / total_out if total_out > 0 else 0.0)

    # 해상도 스캔
    res_grid = np.round(np.arange(p["res_min"], p["res_max"] + p["res_step"] / 2, p["res_step"]), 6)
    scan, cache = [], {}
    # 시드: 구별 base(task["seed_base"]) 에서 해상도 j 의 k번째 반복 = base + j*n_iter + k. 반복마다 다른 시드,
    # 같은 base 면 재현 가능. (leidenalg 의 seed=None 은 벽시계 초 단위 시드라 같은 초 안의 반복이 모두 같아진다 — 결정기록 §3)
    ku_seed_base = int(task["seed_base"])
    seed_counter = {"n": 0}
    def next_seed_block(size):
        s = ku_seed_base + seed_counter["n"]
        seed_counter["n"] += size
        return s
    def scan_one(res, stage):
        sb = next_seed_block(p["n_iter"])
        r = consensus_once(G, n, float(res), p["n_iter"], p["tau"], sb)
        labels = r["labels"]
        q, internal, ifr = evaluate(labels)
        row = {"stage": stage, "resolution": float(res), "target": target, "seed_base": sb, "n_communities": int(labels.max()) + 1,
               "modularity": round(q, 6), "internal_flow": round(internal, 2), "total_outflow": round(total_out, 2),
               "ifr": round(ifr, 6), "modal_count": r["modal_count"], "modal_share": round(r["modal_count"] / p["n_iter"], 4),
               "modal_n_communities": r["modal_n_comm"], "modal_equals_consensus": r["modal_equals_cc"],
               "n_distinct_partitions": r["n_distinct"]}
        scan.append(row)
        cache[float(res)] = (r, row)
        return row

    # 진행 상황 파일 (메인 프로세스가 주기적으로 읽어 보여준다)
    prog_path = Path(task["progress_path"]) if task.get("progress_path") else None
    def progress(stage, i, total):
        if prog_path is None:
            return
        try:
            prog_path.write_text(json.dumps({"ku": ku, "ku_name": C.KU_NAME[ku], "stage": stage, "done": i, "total": total,
                                             "elapsed_s": round(time.time() - t0, 1)}, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    for i, res in enumerate(res_grid):
        scan_one(res, "grid")
        if (i + 1) % 5 == 0 or i + 1 == len(res_grid):
            progress("해상도 스캔", i + 1, len(res_grid))

    def pick(rows):
        cands = [r for r in rows if r["n_communities"] == target]
        if not cands:
            return None
        key = (lambda r: (r["modularity"], r["ifr"])) if p["primary"] == "modularity" else (lambda r: (r["ifr"], r["modularity"]))
        return max(cands, key=key)

    best = pick(scan)
    if best is None:
        below = [r for r in scan if r["n_communities"] < target]
        above = [r for r in scan if r["n_communities"] > target]
        if below and above:
            r_lo = max(below, key=lambda r: r["n_communities"])["resolution"]
            r_hi = min(above, key=lambda r: r["n_communities"])["resolution"]
            msgs.append(f"목표 {target} 미달 → 세밀 스캔 {r_lo}~{r_hi}")
            for i, res in enumerate(np.linspace(min(r_lo, r_hi), max(r_lo, r_hi), p["fine_steps"])):
                scan_one(round(float(res), 6), "fine")
                if (i + 1) % 5 == 0:
                    progress("세밀 스캔", i + 1, p["fine_steps"])
            best = pick(scan)
    if best is None:
        # 그래도 없으면 목표에 가장 가까운 개수 중 Q 최대 (기록에 남기고 진행)
        gap = min(abs(r["n_communities"] - target) for r in scan)
        near = [r for r in scan if abs(r["n_communities"] - target) == gap]
        best = max(near, key=lambda r: r["modularity"])
        msgs.append(f"목표 {target}개를 만드는 해상도 없음 → 가장 가까운 {best['n_communities']}개 채택")

    best_res = best["resolution"]
    r_best, _ = cache[best_res]
    labels = r_best["labels"].copy()

    # 안정성: 확정 해상도에서 독립 반복
    trials = []
    changed = np.zeros(n, dtype=int)
    for t in range(p["stab_trials"]):
        progress("안정성 반복", t, p["stab_trials"])
        sb = next_seed_block(p["stab_iter"])
        rt = consensus_once(G, n, best_res, p["stab_iter"], p["tau"], sb)
        a = ari(labels, rt["labels"])
        trials.append({"trial": t, "seed_base": sb, "ari_vs_final": round(a, 4), "n_communities": int(rt["labels"].max()) + 1,
                       "modal_share": round(rt["modal_count"] / p["stab_iter"], 4)})
        # 확정 분할과 묶음이 달라진 동: 같은 묶음 관계가 하나라도 바뀐 동
        same_final = labels[:, None] == labels[None, :]
        same_trial = rt["labels"][:, None] == rt["labels"][None, :]
        changed += (same_final != same_trial).any(axis=1)
    aris = [t["ari_vs_final"] for t in trials]

    # 커뮤니티 번호: 총 출발통행량 내림차순
    out_by_c = np.bincount(labels[o_i], weights=f_v, minlength=labels.max() + 1)
    order = {int(c): rank for rank, c in enumerate(np.argsort(-out_by_c))}
    labels_final = np.asarray([order[int(c)] for c in labels], dtype=np.int32)

    # 동별 소속 확률: 확정 묶음의 다른 동들과 같은 방이었던 평균 확률
    P = r_best["coassoc"]
    prob = np.ones(n)
    for i in range(n):
        mates = np.where((labels_final == labels_final[i]) & (np.arange(n) != i))[0]
        if len(mates):
            prob[i] = P[i, mates].mean()

    contig = contiguity(labels_final, task["adj"])
    mapping = pd.DataFrame({"Dong": nodes, "Ku": ku, "ku_name": C.KU_NAME[ku], "community": labels_final,
                            "membership_prob": np.round(prob, 4), "changed_in_trials": changed})
    metrics = {"ku_code": ku, "ku_name": C.KU_NAME[ku], "year": year, "n_dongs": n, "n_edges": int(len(weights)),
               "seed_base_ku": ku_seed_base, "seed_base_final_resolution": best["seed_base"],
               "target": target, "resolution": best_res, "stage": best["stage"], "n_communities": best["n_communities"],
               "modularity": best["modularity"], "ifr": best["ifr"], "internal_flow": best["internal_flow"],
               "total_outflow": best["total_outflow"], "modal_share": best["modal_share"],
               "modal_equals_consensus": best["modal_equals_consensus"], "n_distinct_partitions": best["n_distinct_partitions"],
               "n_resolutions_hitting_target": sum(r["n_communities"] == target for r in scan),
               "stability_ari_mean": round(float(np.mean(aris)), 4), "stability_ari_min": round(float(np.min(aris)), 4),
               "n_dongs_changed_in_any_trial": int((changed > 0).sum()),
               "min_membership_prob": round(float(prob.min()), 4),
               "n_noncontiguous_communities": int(sum(v > 1 for v in contig.values())),
               "seconds": round(time.time() - t0, 1), "notes": "; ".join(msgs)}
    return {"ku": ku, "mapping": mapping, "metrics": metrics, "scan": pd.DataFrame(scan),
            "stability": {"ku_code": ku, "year": year, "resolution": best_res, "trials": trials,
                          "dongs_changed": [int(nodes[i]) for i in np.where(changed > 0)[0]], "contiguity": contig},
            "coassoc": pd.DataFrame(P, index=nodes, columns=nodes), "runs": r_best["runs"], "labels_raw": r_best["labels"]}


# ──────────────────────────────────────────────────────────────────────────────
def build_tasks(year: str, dong, od, params, ku_filter=None):
    import geopandas as gpd
    tasks = []
    dong = dong.sort_values("Dong").reset_index(drop=True)
    for ku in sorted(C.TARGET_COMMUNITIES):
        if ku_filter and ku not in ku_filter:
            continue
        g = dong[dong["Ku"] == ku]
        nodes = g["Dong"].astype(int).tolist()
        nset = set(nodes)
        od_from = od[od["dong_O"].isin(nset)]
        od_in = od_from[od_from["dong_D"].isin(nset)]
        # 공간 인접 (touches) — 연속성 점검용
        sidx = g.sindex
        adj = [[] for _ in nodes]
        geoms = g.geometry.values
        for i, geom in enumerate(geoms):
            for j in sidx.query(geom, predicate="touches"):
                if j != i:
                    adj[i].append(int(j))
        tasks.append({"ku": ku, "year": year, "nodes": nodes, "adj": adj, "params": params,
                      "od_in": od_in[["dong_O", "dong_D", "flow"]].values.tolist(),
                      "od_from": od_from[["dong_O", "dong_D", "flow"]].values.tolist()})
    return tasks


def main():
    import geopandas as gpd
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="+", default=list(C.YEARS))
    ap.add_argument("--workers", type=int, default=C.N_WORKERS)
    ap.add_argument("--ku", nargs="*", type=int, default=None, help="일부 구만 (점검용)")
    ap.add_argument("--n-iter", type=int, default=C.N_ITER)
    ap.add_argument("--res-step", type=float, default=C.RES_STEP)
    ap.add_argument("--stab-trials", type=int, default=C.STABILITY_TRIALS)
    ap.add_argument("--tag", default="", help="출력 폴더 접미사 (점검 실행을 정본 실행과 분리)")
    a = ap.parse_args()

    params = {"res_min": C.RES_MIN, "res_max": C.RES_MAX, "res_step": a.res_step, "n_iter": a.n_iter, "tau": C.TAU,
              "self_loops": C.INCLUDE_SELF_LOOPS, "primary": C.SELECTION_PRIMARY,
              "fine_steps": C.FINE_SCAN_STEPS, "stab_trials": a.stab_trials,
              "stab_iter": a.n_iter if a.n_iter != C.N_ITER else C.STABILITY_ITER}

    dong_all = gpd.read_file(C.DONG_GPKG, layer="epsg5179")
    dong_all["Dong"] = dong_all["Dong"].astype(int); dong_all["Ku"] = dong_all["Ku"].astype(int)
    if len(dong_all) != C.N_DONG:
        raise SystemExit(f"동 정본 {len(dong_all)}개 != {C.N_DONG}. s01 을 먼저 실행하세요.")

    for year in a.years:
        out = C.LEIDEN_OUT / (year + a.tag)
        for sub in ("metrics", "resolution_scan_logs", "stability", "coassoc", "boundaries"):
            (out / sub).mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S",
                            handlers=[logging.FileHandler(out / f"leiden_run_{ts}.log", encoding="utf-8"), logging.StreamHandler(sys.stdout)], force=True)
        t_year = time.time()
        od = pd.read_parquet(C.od_daily_path(year))
        log.info(f"[{year}] od_daily {len(od):,}행, 통행량 {od['flow'].sum():,.0f} | params={params}")
        tasks = build_tasks(year, dong_all, od, params, set(a.ku) if a.ku else None)

        # 실행 base 시드: config.SEED 가 None 이면 실행마다 무작위로 뽑아 run_seed.json 에 기록 (이어서 실행하면 같은 값을 다시 쓴다).
        # 구 i 는 base + i*10^7 부터 연속 구간을 쓴다 (해상도 350개 × 3,000 + 안정성 10 × 3,000 < 10^7).
        seed_file = out / "run_seed.json"
        if seed_file.exists():
            base_seed = int(json.loads(seed_file.read_text(encoding="utf-8"))["base_seed"])
            log.info(f"[{year}] 이전 실행의 base 시드 재사용: {base_seed}")
        else:
            base_seed = int(C.SEED) if C.SEED is not None else int.from_bytes(os.urandom(4), "little")
            seed_file.write_text(json.dumps({"base_seed": base_seed, "source": "config.SEED" if C.SEED is not None else "os.urandom",
                                             "created": datetime.datetime.now().isoformat(timespec="seconds")}), encoding="utf-8")
            log.info(f"[{year}] base 시드 = {base_seed} ({'config.SEED' if C.SEED is not None else '무작위'}) → run_seed.json")
        params = {**params, "base_seed": base_seed}
        ku_order = sorted(C.TARGET_COMMUNITIES)
        for t in tasks:
            t["params"] = params
            t["seed_base"] = base_seed + ku_order.index(t["ku"]) * 10_000_000

        # 이어서 실행: 구별 결과를 _partial/ 에 저장해 두고, 이미 끝난 구는 건너뛴다 (중단 후 재실행 대비)
        import pickle
        part_dir = out / "_partial"
        part_dir.mkdir(exist_ok=True)
        results = []
        for t in list(tasks):
            pf = part_dir / f"{t['ku']}.pkl"
            if pf.exists():
                with open(pf, "rb") as fh:
                    saved = pickle.load(fh)
                if saved.get("params") == params:
                    results.append(saved["result"])
                    tasks.remove(t)
                    log.info(f"[{year}] {C.KU_NAME[t['ku']]}: 이전 실행 결과 재사용 ({pf.name})")
        prog_dir = out / "progress"
        prog_dir.mkdir(exist_ok=True)
        for t in tasks:
            t["progress_path"] = str(prog_dir / f"{t['ku']}.json")
            Path(t["progress_path"]).write_text(json.dumps({"ku": t["ku"], "ku_name": C.KU_NAME[t["ku"]], "stage": "대기", "done": 0,
                                                            "total": len(np.arange(params["res_min"], params["res_max"] + params["res_step"] / 2, params["res_step"]))},
                                                           ensure_ascii=False), encoding="utf-8")
        log.info(f"[{year}] 구 {len(tasks)}개, 워커 {a.workers}개 시작. 진행률은 60초마다 아래에, 파일로는 {prog_dir} 에서 볼 수 있음")

        def progress_summary(done_kus):
            rows = []
            for t in tasks:
                try:
                    pj = json.loads(Path(t["progress_path"]).read_text(encoding="utf-8"))
                except Exception:
                    continue
                if t["ku"] in done_kus:
                    rows.append(f"{pj['ku_name']} 완료")
                elif pj["stage"] == "해상도 스캔":
                    rows.append(f"{pj['ku_name']} {pj['done']}/{pj['total']}")
                elif pj["stage"] != "대기":
                    rows.append(f"{pj['ku_name']} {pj['stage']}")
            pct = 100 * len(done_kus) / n_total
            return f"[{year}] 완료 {len(done_kus)}/{n_total}구 ({pct:.0f}%) | " + ", ".join(rows)

        done_kus = {r["ku"] for r in results}
        n_total = len(tasks) + len(results)
        with cf.ProcessPoolExecutor(max_workers=a.workers) as ex:
            futs = {ex.submit(run_ku, t): t["ku"] for t in tasks}
            pending = set(futs)
            last_report = time.time()
            while pending:
                done, pending = cf.wait(pending, timeout=60, return_when=cf.FIRST_COMPLETED)
                for f in done:
                    r = f.result()
                    m = r["metrics"]
                    done_kus.add(r["ku"])
                    log.info(f"[{year}] {m['ku_name']}: γ={m['resolution']:.3f} ({m['stage']}), k={m['n_communities']}/{m['target']}, "
                             f"Q={m['modularity']:.4f}, IFR={m['ifr']:.4f}, 최빈분할 {m['modal_share']:.1%} "
                             f"{'=' if m['modal_equals_consensus'] else '≠'}합의, ARI {m['stability_ari_mean']:.3f} "
                             f"(min {m['stability_ari_min']:.3f}), 비연속 {m['n_noncontiguous_communities']}, {m['seconds']}s {m['notes']}")
                    results.append(r)
                    with open(part_dir / f"{r['ku']}.pkl", "wb") as fh:
                        pickle.dump({"params": params, "result": r}, fh)
                if pending and time.time() - last_report >= 60:
                    log.info(progress_summary(done_kus))
                    last_report = time.time()
        results.sort(key=lambda r: r["ku"])

        # 저장
        mapping = pd.concat([r["mapping"] for r in results], ignore_index=True)
        mapping["global_community_id"] = mapping["Ku"] * 100 + mapping["community"]
        mapping["community_name"] = mapping["ku_name"] + "_커뮤니티" + mapping["community"].astype(str)
        mapping = mapping.merge(dong_all[["Dong", "ADM_NM", "life_zone_id", "life_zone_name"]], on="Dong", how="left")
        mapping = mapping[["Dong", "Ku", "ku_name", "ADM_NM", "community", "global_community_id", "community_name",
                           "membership_prob", "changed_in_trials", "life_zone_id", "life_zone_name"]].sort_values("Dong")
        mapping.to_csv(out / "metrics" / f"leiden_mapping_{year}.csv", index=False, encoding="utf-8-sig")
        met = pd.DataFrame([r["metrics"] for r in results])
        met.to_csv(out / "metrics" / f"leiden_metrics_{year}.csv", index=False, encoding="utf-8-sig")
        met.to_excel(out / "metrics" / f"leiden_metrics_{year}.xlsx", index=False)
        for r in results:
            ku = r["ku"]; en = C.KU_NAME_EN[ku]
            r["scan"].to_csv(out / "resolution_scan_logs" / f"{ku}_{en}_{year}.csv", index=False, encoding="utf-8-sig")
            (out / "stability" / f"{ku}_{en}_{year}.json").write_text(json.dumps(r["stability"], ensure_ascii=False, indent=1), encoding="utf-8")
            r["coassoc"].to_csv(out / "coassoc" / f"{ku}_{en}_{year}_coassoc.csv", encoding="utf-8-sig")
            np.savez_compressed(out / "coassoc" / f"{ku}_{en}_{year}_runs.npz", runs=r["runs"], labels_cc=r["labels_raw"],
                                nodes=np.asarray(r["mapping"]["Dong"]))
        # 경계
        gdf = dong_all.merge(mapping[["Dong", "community", "global_community_id", "community_name", "membership_prob"]], on="Dong")
        comm = gdf.dissolve(by="global_community_id", aggfunc={"Ku": "first", "ku_name": "first", "community": "first",
                                                                "community_name": "first", "membership_prob": "mean"}, as_index=False)
        comm["n_dongs"] = gdf.groupby("global_community_id").size().reindex(comm["global_community_id"]).values
        comm["area_km2"] = comm.geometry.area / 1e6
        C.save_gpkg_layers(out / "boundaries" / f"leiden_communities_{year}.gpkg",
                           {"communities_epsg5179": comm, "dongs_epsg5179": gdf})
        info = {"year": year, "env": C.env_info(), "params": params, "base_seed": base_seed,
                "seed_rule": "구 i(코드 오름차순)의 시드 구간 시작 = base_seed + i*1e7; 해상도 j의 k번째 Leiden 시드 = 구간시작 + j*n_iter + k; 안정성 반복은 그 뒤 연속",
                "n_ku": len(results),
                "n_communities_total": int(mapping["global_community_id"].nunique()), "n_dongs": int(len(mapping)),
                "seconds": round(time.time() - t_year, 1), "input_od": C.sha256_of(C.od_daily_path(year)),
                "input_dong": C.sha256_of(C.DONG_GPKG), "log": f"leiden_run_{ts}.log"}
        (out / "run_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info(f"[{year}] 완료: 커뮤니티 {info['n_communities_total']}개, 동 {info['n_dongs']}개, {info['seconds']}s → {out}")


if __name__ == "__main__":
    main()
