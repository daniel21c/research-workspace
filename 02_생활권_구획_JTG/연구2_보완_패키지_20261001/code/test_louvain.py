# -*- coding: utf-8 -*-
"""S3 구현 시험: 공통 엔진 사본(code/engine)의 Louvain 합의가 원본과 같은 형식·정의로 동작하는지 확인한다.
  T1  γ=1 에서 엔진 Q = NetworkX Q = python-louvain Q (25개 구 전부, 허용오차 1e-12)
  T2  같은 시드로 두 번 돌리면 원시 라벨이 완전히 같다 (결정성)
  T3  igraph community_multilevel 과 교차: 같은 그래프·γ=1 에서 최대 Q 와 합의 분할의 ARI (참고 수치)
  T4  소규모 실행(종로구, 30회, γ 간격 0.1)이 끝까지 돌고 Leiden 원본과 같은 열 구성의 지표표를 낸다
  T5  속도: 가장 큰 구(송파)에서 Louvain 300회 시간
결과는 audit/louvain_tests.json 에 저장한다.
"""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

PKG = Path(__file__).resolve().parents[1]
ENGINE = PKG / "code" / "engine"
sys.path.insert(0, str(ENGINE))
import config as C                                   # noqa: E402  (패키지 사본)
import s03_louvain_consensus as S                    # noqa: E402

import networkx as nx
import community as community_louvain
import igraph as ig

results = {}


def graph_for(ku, od, dong):
    nodes = dong[dong["Ku"] == ku]["Dong"].astype(int).sort_values().tolist()
    nset = set(nodes)
    idx = {d: i for i, d in enumerate(nodes)}
    od_in = od[od["dong_O"].isin(nset) & od["dong_D"].isin(nset)]
    n = len(nodes)
    W = np.zeros((n, n))
    for o, d, f in od_in[["dong_O", "dong_D", "flow"]].itertuples(index=False):
        W[idx[o], idx[d]] += f
    Sm = W + W.T
    edges, weights = [], []
    for i in range(n):
        if W[i, i] > 0:
            edges.append((i, i)); weights.append(W[i, i])
        for j in range(i + 1, n):
            if Sm[i, j] > 0:
                edges.append((i, j)); weights.append(Sm[i, j])
    edges = np.asarray(edges, dtype=np.int64).reshape(-1, 2)
    weights = np.asarray(weights, dtype=np.float64)
    G = ig.Graph(n=n, edges=edges.tolist(), directed=False)
    G.es["weight"] = weights.tolist()
    nxg = nx.Graph(); nxg.add_nodes_from(range(n))
    for (u, v), w in zip(edges.tolist(), weights.tolist()):
        nxg.add_edge(u, v, weight=w)
    return nodes, G, nxg, edges, weights


def main():
    import geopandas as gpd
    dong = gpd.read_file(C.DONG_GPKG, layer="epsg5179")
    dong["Dong"] = dong["Dong"].astype(int); dong["Ku"] = dong["Ku"].astype(int)
    od = pd.read_parquet(C.od_daily_path("2025"))

    # T1 -----------------------------------------------------------------------------------------
    worst = 0.0; rows = []
    for ku in sorted(C.TARGET_COMMUNITIES):
        nodes, G, nxg, edges, weights = graph_for(ku, od, dong)
        part = community_louvain.best_partition(nxg, weight="weight", resolution=1.0, random_state=12345)
        labels = np.fromiter((part[i] for i in range(len(nodes))), dtype=np.int64, count=len(nodes))
        q_engine = S.modularity_q(edges, weights, labels)
        q_nx = nx.community.modularity(nxg, [set(np.flatnonzero(labels == c).tolist()) for c in np.unique(labels)], weight="weight", resolution=1)
        q_pl = community_louvain.modularity(part, nxg, weight="weight")
        d = max(abs(q_engine - q_nx), abs(q_engine - q_pl)); worst = max(worst, d)
        rows.append({"ku": ku, "n_communities": int(labels.max()) + 1, "q_engine": q_engine, "q_networkx": q_nx, "q_python_louvain": q_pl})
    assert worst < 1e-12, f"Q 불일치 {worst}"
    results["T1_q_agreement"] = {"districts": len(rows), "max_abs_diff": worst, "pass": True}

    # T2 -----------------------------------------------------------------------------------------
    nodes, G, nxg, edges, weights = graph_for(11010, od, dong)
    a = S.consensus_once(G, len(nodes), 1.0, 200, 0.5, 777)
    b = S.consensus_once(G, len(nodes), 1.0, 200, 0.5, 777)
    c2 = S.consensus_once(G, len(nodes), 1.0, 200, 0.5, 778)
    same = bool(np.array_equal(a["runs"], b["runs"]) and np.array_equal(a["labels"], b["labels"]))
    results["T2_determinism"] = {"same_seed_identical": same, "different_seed_runs_differ": bool(not np.array_equal(a["runs"], c2["runs"])), "pass": same}
    assert same

    # T3 -----------------------------------------------------------------------------------------
    cross = []
    for ku in (11010, 11240):                          # 종로(작은 구), 송파(가장 큰 구)
        nodes, G, nxg, edges, weights = graph_for(ku, od, dong)
        n = len(nodes)
        ql, qi, labs_l, labs_i = [], [], [], []
        for k in range(300):
            part = community_louvain.best_partition(nxg, weight="weight", resolution=1.0, random_state=1000 + k)
            lab = np.fromiter((part[i] for i in range(n)), dtype=np.int64, count=n)
            labs_l.append(lab); ql.append(S.modularity_q(edges, weights, lab))
            vc = G.community_multilevel(weights="weight", resolution=1.0)
            li = np.asarray(vc.membership); labs_i.append(li); qi.append(S.modularity_q(edges, weights, li))
        best_l = labs_l[int(np.argmax(ql))]; best_i = labs_i[int(np.argmax(qi))]
        cross.append({"ku": ku, "q_max_python_louvain": max(ql), "q_max_igraph_multilevel": max(qi),
                      "q_mean_python_louvain": float(np.mean(ql)), "q_mean_igraph_multilevel": float(np.mean(qi)),
                      "ari_best_partitions": S.ari(best_l, best_i)})
    ok3 = all(abs(x["q_max_python_louvain"] - x["q_max_igraph_multilevel"]) < 0.01 for x in cross)
    results["T3_igraph_cross_check"] = {"rows": cross, "pass": ok3, "note": "참고 수치. 두 구현의 최대 Q 차이 0.01 미만이면 통과"}
    assert ok3

    # T5 속도 -------------------------------------------------------------------------------------
    nodes, G, nxg, edges, weights = graph_for(11240, od, dong)
    t0 = time.perf_counter()
    for k in range(300):
        community_louvain.best_partition(nxg, weight="weight", resolution=1.0, random_state=k)
    per = (time.perf_counter() - t0) / 300
    t0 = time.perf_counter()
    for k in range(300):
        import leidenalg
        leidenalg.find_partition(G, leidenalg.RBConfigurationVertexPartition, resolution_parameter=1.0, weights="weight", seed=k)
    per_leiden = (time.perf_counter() - t0) / 300
    results["T5_speed_songpa_27dong"] = {"louvain_ms_per_run": per * 1000, "leiden_ms_per_run": per_leiden * 1000,
                                         "est_songpa_full_scan_minutes": per * 250 * 3000 / 60,
                                         "note": "해상도 250개 × 3,000회, 단일 코어, 안정성 반복 제외"}

    # T4 소규모 실행 --------------------------------------------------------------------------------
    cmd = [sys.executable, str(ENGINE / "s03_louvain_consensus.py"), "--years", "2025", "--ku", "11010", "--n-iter", "30",
           "--res-step", "0.1", "--stab-trials", "2", "--workers", "1", "--tag", "_test"]
    t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    sec = time.perf_counter() - t0
    out = C.LEIDEN_OUT / "2025_test"
    met = pd.read_csv(out / "metrics" / "louvain_metrics_2025.csv")
    core_cols = pd.read_csv(PKG.parents[1] / "00_공통_코어엔진" / "output" / "leiden" / "2025" / "metrics" / "leiden_metrics_2025.csv", nrows=1).columns.tolist()
    files_ok = all((out / p).exists() for p in ("run_info.json", "metrics/louvain_mapping_2025.csv", "boundaries/louvain_communities_2025.gpkg"))
    cols_same = met.columns.tolist() == core_cols
    results["T4_smoke_run"] = {"returncode": r.returncode, "seconds": sec, "files_written": files_ok, "metric_columns_same_as_leiden": cols_same,
                               "row": met.iloc[0].to_dict(), "pass": bool(r.returncode == 0 and files_ok and cols_same)}
    if r.returncode != 0:
        results["T4_smoke_run"]["stderr_tail"] = r.stderr[-1500:]
    assert results["T4_smoke_run"]["pass"], r.stderr[-1500:]

    (PKG / "audit" / "louvain_tests.json").write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: (v.get("pass", None) if isinstance(v, dict) else v) for k, v in results.items()}, ensure_ascii=False))
    print("Q 최대 차이:", results["T1_q_agreement"]["max_abs_diff"])
    print("속도(송파 1회, ms): louvain %.2f  leiden %.2f  → 송파 전체 스캔 추정 %.1f분(단일코어)" % (
        results["T5_speed_songpa_27dong"]["louvain_ms_per_run"], results["T5_speed_songpa_27dong"]["leiden_ms_per_run"],
        results["T5_speed_songpa_27dong"]["est_songpa_full_scan_minutes"]))
    for x in cross:
        print("교차", x)


if __name__ == "__main__":
    main()
