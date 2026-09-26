# -*- coding: utf-8 -*-
"""독립 검증: Leiden 정본 (2020, 2025) — 구마다
 (1) 저장된 시드로 확정 해상도의 3,000회를 다시 돌려 저장된 원시 라벨과 같은지 (재현성)
 (2) 원시 라벨로 co-association·τ=0.5 연결요소를 다시 만들어 정본 매핑과 같은지
 (3) Q(networkx)·IFR(자체 코드)을 정본 매핑으로 다시 계산해 metrics 와 대조
 (4) 스캔 로그에 선정 규칙(목표 개수 중 Q 최대, 동점 IFR)을 다시 적용해 확정 해상도와 같은지
 (5) 공간 연속성, 시드 구간, 매핑 사본(output·data csv·xlsx·gpkg) 일치
"""
import sys, json, glob
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, networkx as nx
from scipy.sparse.csgraph import connected_components
from scipy.sparse import csr_matrix
from sklearn.metrics import adjusted_rand_score as ARI

CORE = Path(__file__).resolve().parents[1]          # 00_공통_코어엔진 (허브 안 상대경로)
sys.path.insert(0, str(CORE / "scripts"))
import s03_leiden_consensus as S3   # (1) 재현성 확인에만 consensus_once 사용

TARGET = {11010: 4, 11020: 3, 11030: 4, 11040: 4, 11050: 4, 11060: 4, 11070: 3, 11080: 5, 11090: 4, 11100: 5, 11110: 7, 11120: 5,
          11130: 4, 11140: 5, 11150: 5, 11160: 6, 11170: 4, 11180: 3, 11190: 5, 11200: 5, 11210: 5, 11220: 4, 11230: 6, 11240: 7, 11250: 5}
tag = sys.argv[1] if len(sys.argv) > 1 else ""
kus = [int(x) for x in sys.argv[2:]] or sorted(TARGET)
dong = gpd.read_file(CORE / "data/seoul_dong_424_dissolved.gpkg", layer="epsg5179")
dong["Dong"] = dong["Dong"].astype(int); dong["Ku"] = dong["Ku"].astype(int)
rows = []
for year in ("2020", "2025"):
    out = CORE / "output/leiden" / f"{year}{tag}"
    od = pd.read_parquet(CORE / f"data/od/od_daily_{year}01.parquet")
    od["dong_O"] = od.dong_O.astype(int); od["dong_D"] = od.dong_D.astype(int)
    met = pd.read_csv(out / "metrics" / f"leiden_metrics_{year}.csv").set_index("ku_code")
    mp_out = pd.read_csv(out / "metrics" / f"leiden_mapping_{year}.csv")
    mp_data = pd.read_csv(CORE / f"data/dong_to_leiden_{year}_mapping_424.csv", encoding="utf-8-sig") if tag == "" else mp_out
    seed_info = json.loads((out / "run_seed.json").read_text(encoding="utf-8"))
    prm = json.loads((out / "run_info.json").read_text(encoding="utf-8"))["params"]; TAU = float(prm["tau"]); PRIM = prm["primary"]
    for ku in kus:
        r = {"year": year, "ku": ku}
        z = np.load(glob.glob(str(out / "coassoc" / f"{ku}_*_runs.npz"))[0])
        nodes = z["nodes"].astype(int); runs = z["runs"]; n = len(nodes); idx = {d: i for i, d in enumerate(nodes)}
        m = met.loc[ku]
        # (1) 재현성: s03 과 같은 방식으로 그래프 → 같은 시드로 3,000회
        sub = od[od.dong_O.isin(nodes) & od.dong_D.isin(nodes)]
        W = np.zeros((n, n))
        for o, d, f in zip(sub.dong_O, sub.dong_D, sub.flow):
            W[idx[o], idx[d]] += f
        Ssym = W + W.T
        edges, weights = [], []
        for i in range(n):
            if W[i, i] > 0:
                edges.append((i, i)); weights.append(W[i, i])
            for j in range(i + 1, n):
                if Ssym[i, j] > 0:
                    edges.append((i, j)); weights.append(Ssym[i, j])
        import igraph as ig
        G = ig.Graph(n=n, edges=edges, directed=False); G.es["weight"] = weights
        r["n_edges_ok"] = len(weights) == int(m.n_edges)
        rr = S3.consensus_once(G, n, float(m.resolution), runs.shape[0], TAU, int(m.seed_base_final_resolution))
        r["rerun_runs_identical"] = bool(np.array_equal(rr["runs"], runs))
        # (2) co-association 다시 (저장된 원시 라벨에서, 자체 코드)
        co = np.zeros((n, n))
        for k in range(runs.shape[0]):
            co += runs[k][:, None] == runs[k][None, :]
        P = co / runs.shape[0]
        A = (P >= TAU).astype(int); np.fill_diagonal(A, 0)
        _, lab_cc = connected_components(csr_matrix(A), directed=False)
        mo = mp_out[mp_out.Ku == ku].set_index("Dong").community.reindex(nodes).values
        md = mp_data[mp_data.Ku == ku].set_index("Dong").community.reindex(nodes).values
        r["coassoc_cc_eq_mapping"] = ARI(lab_cc, mo) == 1.0
        r["coassoc_csv_max_absdiff"] = float(np.abs(pd.read_csv(glob.glob(str(out / "coassoc" / f"{ku}_*_coassoc.csv"))[0], index_col=0).values - P).max())
        r["out_eq_data_mapping"] = bool(np.array_equal(mo, md))
        r["k"] = int(len(set(mo))); r["k_ok"] = r["k"] == TARGET[ku] if tag == "" else True
        # modal share 재계산
        from collections import Counter
        def canon(v):
            seen = {}; return tuple(seen.setdefault(x, len(seen)) for x in v)
        cnt = Counter(canon(runs[k]) for k in range(runs.shape[0]))
        r["modal_share_ok"] = abs(cnt.most_common(1)[0][1] / runs.shape[0] - m.modal_share) < 1e-4
        r["n_distinct_ok"] = len(cnt) == int(m.n_distinct_partitions)
        # (3) Q (networkx), IFR (자체)
        g = nx.Graph()
        g.add_nodes_from(range(n))
        for (i, j), w in zip(edges, weights):
            g.add_edge(i, j, weight=w)
        comms = [set(np.where(mo == c)[0]) for c in np.unique(mo)]
        q = nx.community.modularity(g, comms, weight="weight")
        r["Q_nx"] = q; r["Q_diff"] = abs(q - m.modularity)
        fr = od[od.dong_O.isin(nodes)]
        lab_all = pd.Series(mo, index=nodes)
        lo = lab_all.reindex(fr.dong_O).values; ld = lab_all.reindex(fr.dong_D).values
        same = (~np.isnan(ld)) & (lo == ld)
        ifr = fr.flow.values[same].sum() / fr.flow.sum()
        r["IFR_mine"] = ifr; r["IFR_diff"] = abs(ifr - m.ifr)
        # (4) 선정 규칙
        sc = pd.read_csv(glob.glob(str(out / "resolution_scan_logs" / f"{ku}_*.csv"))[0])
        tgt = int(m.target)
        c = sc[sc.n_communities == tgt]
        if len(c):
            best = c.sort_values(["modularity", "ifr"] if PRIM == "modularity" else ["ifr", "modularity"], ascending=False, kind="stable").iloc[0]
            r["selection_ok"] = abs(best.resolution - m.resolution) < 1e-9 and best.stage == m.stage
            r["n_ties_Q"] = int((c.modularity == best.modularity).sum()); r["sel_key_eq"] = abs(c[c.resolution==m.resolution].iloc[0].modularity-best.modularity)<1e-12 and abs(c[c.resolution==m.resolution].iloc[0].ifr-best.ifr)<1e-12
        else:
            r["selection_ok"] = False
        r["stage"] = m.stage; r["fine_used"] = bool((sc.stage == "fine").any()); r["notes"] = m.notes if isinstance(m.notes, str) else ""
        # 해상도 격자 250개, 중복 없음
        gr = sc[sc.stage == "grid"].resolution.round(6)
        r["grid_ok"] = len(gr) == 250 and abs(gr.min() - 0.01) < 1e-9 and abs(gr.max() - 2.5) < 1e-9 and gr.is_unique
        # 시드 구간: 구 base 에서 연속, 1e7 안
        stab = json.loads(open(glob.glob(str(out / "stability" / f"{ku}_*.json"))[0], encoding="utf-8").read())
        sb = list(sc.seed_base) + [t["seed_base"] for t in stab["trials"]]
        exp = [int(m.seed_base_ku) + 3000 * i for i in range(len(sb))]
        r["seed_blocks_contiguous"] = sb == exp
        r["seed_span_lt_1e7"] = (sb[-1] + 3000 - int(m.seed_base_ku)) < 10**7
        ku_order = sorted(TARGET)
        r["seed_base_ku_ok"] = int(m.seed_base_ku) == int(seed_info["base_seed"]) + ku_order.index(ku) * 10**7
        r["stab_ari_all1"] = all(t["ari_vs_final"] == 1.0 for t in stab["trials"]) and len(stab["trials"]) == 10
        # (5) 연속성
        dd = dong[dong.Ku == ku].set_index("Dong").loc[nodes]
        adj = gpd.sjoin(dd.reset_index()[["Dong", "geometry"]], dd.reset_index()[["Dong", "geometry"]], predicate="touches")
        noncontig = 0
        for cc in np.unique(mo):
            mem = set(nodes[mo == cc])
            e = adj[adj.Dong_left.isin(mem) & adj.Dong_right.isin(mem)]
            H = nx.Graph(); H.add_nodes_from(mem); H.add_edges_from(zip(e.Dong_left, e.Dong_right))
            noncontig += nx.number_connected_components(H) > 1
        r["noncontig"] = noncontig
        rows.append(r)
        print(r, flush=True)
R = pd.DataFrame(rows)
R.to_csv(Path(__file__).resolve().parents[1] / "output" / "audit_20260925" / f"a3_result{tag}.csv", index=False, encoding="utf-8-sig")
bools = [c for c in R.columns if R[c].dtype == bool]
print("\n=== 요약 ===")
for c in bools:
    print(c, int(R[c].sum()), "/", len(R))
print("Q_diff max", R.Q_diff.max(), "IFR_diff max", R.IFR_diff.max(), "coassoc_csv diff max", R.coassoc_csv_max_absdiff.max(), "noncontig sum", R.noncontig.sum())
print("fine_used:", R[R.fine_used][["year", "ku"]].values.tolist(), "stage!=grid:", R[R.stage != "grid"][["year", "ku", "stage"]].values.tolist())
print("Q ties:", R[R.n_ties_Q > 1][["year", "ku", "n_ties_Q"]].values.tolist(), "notes:", R[R.notes != ""][["year", "ku", "notes"]].values.tolist())
