# -*- coding: utf-8 -*-
"""S4 비교: 공식 116 · Leiden(공통 정본) · Louvain(S3 산출)을 같은 지표로 구별 비교한다.

지표 정의는 공통 정의표(기준 문서 7절)와 9/29 패키지를 따른다.
  Q    : 구 내부 무방향 가중 그래프(f_ij+f_ji, 자기 루프 f_ii 간선 1회), γ=1.  구별 Q 평균을 서울 Q라 하지 않는다.
  IFR  : 구 출발 통행 중 같은 권역 안에서 끝난 통행 / 구에서 서울 전체로 출발한 통행(자기 동 포함). 상위 집계는 분자합/분모합.
  연속성: 권역별로 동 폴리곤이 서로 닿는(touches) 연결요소가 1개인가. 코어 s03 의 contiguity()와 같은 방법.
산출: results/tables/L1_algorithm_comparison_2025.csv(구별), L2_city_summary_2025.csv(서울), audit/s4_checks.json
"""
from __future__ import annotations
import importlib.util, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd

PKG = Path(__file__).resolve().parents[1]
INP = PKG / "inputs"
LOUV = Path(__import__("os").environ.get("LOUVAIN_DIR", PKG / "output" / "louvain" / "2025"))   # 별도 재실행 결과로 바꿔 검증할 때 환경변수로 지정
OUT = PKG / "results" / "tables"
OLD_T3 = PKG / "results" / "reused_20260929" / "T3_district_2025.csv"         # 9/29 패키지 결과표 사본(s5_reuse.py 가 해시와 함께 복사)

sys.path.insert(0, str(PKG / "code" / "engine"))
import config as C                                              # noqa: E402
import s03_louvain_consensus as S                               # noqa: E402  (modularity_q, contiguity, ari 재사용)
spec = importlib.util.spec_from_file_location("analyze_20260929", PKG / "code" / "reused" / "analyze_20260929.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)   # overlap(), q_matrix(), q_networkx()


def part_arrays(mapping: pd.DataFrame, col: str, nodes):
    s = mapping.set_index("Dong")[col]
    return s.loc[nodes].to_numpy()


def evaluate(f, labels, out_total, nodes_adj):
    """f: 구 내부 방향 OD 행렬, out_total: 구 출발 서울 전체 통행량"""
    q = A.q_matrix(f, labels)
    inside = (labels[:, None] == labels[None, :])
    ifr = float(f[inside].sum() / out_total)
    contig = S.contiguity(pd.factorize(labels)[0], nodes_adj)
    return {"n_communities": int(len(np.unique(labels))), "q": q, "ifr": ifr, "internal_flow": float(f[inside].sum()),
            "n_contiguous": int(sum(v == 1 for v in contig.values())), "n_noncontiguous": int(sum(v > 1 for v in contig.values()))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    od = pd.read_parquet(INP / "od_daily_202501.parquet")
    dong = gpd.read_file(INP / "seoul_dong_424_dissolved.gpkg", layer="epsg5179")
    dong["Dong"] = dong["Dong"].astype(int); dong["Ku"] = dong["Ku"].astype(int)
    leiden = pd.read_csv(INP / "dong_to_leiden_2025_mapping_424.csv", encoding="utf-8-sig")
    louv = pd.read_csv(LOUV / "metrics" / "louvain_mapping_2025.csv", encoding="utf-8-sig")
    louv_met = pd.read_csv(LOUV / "metrics" / "louvain_metrics_2025.csv", encoding="utf-8-sig").set_index("ku_code")
    leid_met = pd.read_csv(INP / "leiden_metrics_2025.csv", encoding="utf-8-sig").set_index("ku_code")   # 2025 Leiden 정본을 만든 같은 실행의 지표표(S0 보조 입력)
    mets = {"leiden": leid_met, "louvain": louv_met}
    official = dong[["Dong", "life_zone_id"]]

    checks = {"louvain_424_unique": bool(louv["Dong"].nunique() == 424 and len(louv) == 424),
              "leiden_424_unique": bool(leiden["Dong"].nunique() == 424 and len(leiden) == 424)}
    rows = []
    for ku in sorted(C.TARGET_COMMUNITIES):
        g = dong[dong["Ku"] == ku].sort_values("Dong").reset_index(drop=True)
        nodes = g["Dong"].tolist(); n = len(nodes); idx = {d: i for i, d in enumerate(nodes)}
        o = od[od["dong_O"].isin(set(nodes))]
        out_total = float(o["flow"].sum())
        f = np.zeros((n, n))
        for a, b, w in o[o["dong_D"].isin(set(nodes))][["dong_O", "dong_D", "flow"]].itertuples(index=False):
            f[idx[a], idx[b]] += w
        sidx = g.sindex; adj = [[] for _ in nodes]
        for i, geom in enumerate(g.geometry.values):
            for j in sidx.query(geom, predicate="touches"):
                if j != i:
                    adj[i].append(int(j))
        lab = {"official": g["life_zone_id"].to_numpy(),
               "leiden": part_arrays(leiden, "global_community_id", nodes),
               "louvain": part_arrays(louv, "global_community_id", nodes)}
        ev = {k: evaluate(f, v, out_total, adj) for k, v in lab.items()}
        target = C.TARGET_COMMUNITIES[ku]
        row = {"ku": ku, "ku_name": C.KU_NAME[ku], "n_dong": n, "target": target, "total_outflow": out_total}
        for k in ("official", "leiden", "louvain"):
            row.update({f"{k}_{m}": v for m, v in ev[k].items() if m != "internal_flow"})
            row[f"{k}_hit_target"] = bool(ev[k]["n_communities"] == target)
        row["g_leiden"] = ev["leiden"]["ifr"] - ev["official"]["ifr"]
        row["g_louvain"] = ev["louvain"]["ifr"] - ev["official"]["ifr"]
        row["dq_leiden"] = ev["leiden"]["q"] - ev["official"]["q"]
        row["dq_louvain"] = ev["louvain"]["q"] - ev["official"]["q"]
        row["leiden_minus_louvain_q"] = ev["leiden"]["q"] - ev["louvain"]["q"]
        row["leiden_minus_louvain_ifr"] = ev["leiden"]["ifr"] - ev["louvain"]["ifr"]
        for name, (x, y) in {"lz_leiden": ("official", "leiden"), "lz_louvain": ("official", "louvain"), "leiden_louvain": ("leiden", "louvain")}.items():
            ov = A.overlap(lab[x], lab[y])
            row.update({f"{name}_iou_1to1": ov["iou_1to1"], f"{name}_matched_share": ov["matched_share"],
                        f"{name}_jaccard_maxmatch_share": ov["jaccard_maxmatch_share"], f"{name}_ari": ov["ari"]})
        for k, met in mets.items():     # 두 알고리즘 모두 같은 합의 절차이므로 같은 항목을 같은 표에 둔다
            m = met.loc[ku]
            row.update({f"{k}_resolution": float(m["resolution"]), f"{k}_stage": m["stage"],
                        f"{k}_n_resolutions_hitting_target": int(m["n_resolutions_hitting_target"]),
                        f"{k}_modal_share": float(m["modal_share"]), f"{k}_modal_equals_consensus": bool(m["modal_equals_consensus"]),
                        f"{k}_n_distinct_partitions": int(m["n_distinct_partitions"]),
                        f"{k}_stability_ari_mean": float(m["stability_ari_mean"]), f"{k}_stability_ari_min": float(m["stability_ari_min"]),
                        f"{k}_n_dongs_changed_in_trials": int(m["n_dongs_changed_in_any_trial"]),
                        f"{k}_notes": m["notes"] if isinstance(m["notes"], str) else ""})
        # 검증 재료
        row["_q_networkx_louvain"] = A.q_networkx(f, lab["louvain"])
        for k, met in mets.items():
            row[f"_engine_q_{k}"] = float(met.loc[ku, "modularity"]); row[f"_engine_ifr_{k}"] = float(met.loc[ku, "ifr"])
            row[f"_engine_k_{k}"] = int(met.loc[ku, "n_communities"])
        rows.append(row)
    L1 = pd.DataFrame(rows)

    # ── 검증 ────────────────────────────────────────────────────────────────────────
    checks["q_louvain_vs_networkx_max_abs_diff"] = float((L1["louvain_q"] - L1["_q_networkx_louvain"]).abs().max())
    for k in ("louvain", "leiden"):   # 엔진이 기록한 지표(반올림 6자리)와 이 스크립트가 매핑에서 다시 계산한 값
        checks[f"q_{k}_vs_engine_metrics_max_abs_diff"] = float((L1[f"{k}_q"] - L1[f"_engine_q_{k}"]).abs().max())
        checks[f"ifr_{k}_vs_engine_metrics_max_abs_diff"] = float((L1[f"{k}_ifr"] - L1[f"_engine_ifr_{k}"]).abs().max())
        checks[f"{k}_n_communities_same_as_engine_metrics"] = bool((L1[f"{k}_n_communities"] == L1[f"_engine_k_{k}"]).all())
    # IFR 독립 계산 (pandas groupby)
    comm = louv.set_index("Dong")["global_community_id"]; ku_of = dong.set_index("Dong")["Ku"]
    d2 = od.assign(ku=od["dong_O"].map(ku_of), co=od["dong_O"].map(comm), cd=od["dong_D"].map(comm))
    ind = d2[d2["co"] == d2["cd"]].groupby("ku")["flow"].sum() / d2.groupby("ku")["flow"].sum()
    checks["ifr_louvain_vs_pandas_max_abs_diff"] = float((L1.set_index("ku")["louvain_ifr"] - ind).abs().max())
    if OLD_T3.exists():
        t3 = pd.read_csv(OLD_T3).set_index("ku")
        m = L1.set_index("ku")
        checks["leiden_official_vs_20260929_T3_max_abs_diff"] = float(max((m["leiden_q"] - t3["q_ld"]).abs().max(), (m["official_q"] - t3["q_lz"]).abs().max(),
                                                                          (m["leiden_ifr"] - t3["ifr_ld"]).abs().max(), (m["official_ifr"] - t3["ifr_lz"]).abs().max()))
    checks["pass"] = bool(checks["louvain_424_unique"] and checks["leiden_424_unique"]
                          and checks["q_louvain_vs_networkx_max_abs_diff"] < 1e-12
                          and all(checks[f"q_{k}_vs_engine_metrics_max_abs_diff"] < 1e-6 and checks[f"ifr_{k}_vs_engine_metrics_max_abs_diff"] < 1e-6
                                  and checks[f"{k}_n_communities_same_as_engine_metrics"] for k in ("louvain", "leiden"))
                          and checks["ifr_louvain_vs_pandas_max_abs_diff"] < 1e-12
                          and checks.get("leiden_official_vs_20260929_T3_max_abs_diff", 0) < 1e-9)
    (PKG / "audit" / "s4_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")

    L1 = L1.drop(columns=[c for c in L1.columns if c.startswith("_")])
    L1.to_csv(OUT / "L1_algorithm_comparison_2025.csv", index=False, encoding="utf-8-sig", float_format="%.12g")

    # ── 서울 요약 ───────────────────────────────────────────────────────────────────
    tot_out = L1["total_outflow"].sum()
    # 분자합: 구별 ifr × total_outflow
    summ = []
    for k in ("official", "leiden", "louvain"):
        num = float((L1[f"{k}_ifr"] * L1["total_outflow"]).sum())
        summ.append({"partition": k, "n_communities_total": int(L1[f"{k}_n_communities"].sum()),
                     "districts_hit_target": int(L1[f"{k}_hit_target"].sum()), "districts": int(len(L1)),
                     "contiguous_communities": int(L1[f"{k}_n_contiguous"].sum()),
                     "contiguous_share": float(L1[f"{k}_n_contiguous"].sum() / L1[f"{k}_n_communities"].sum()),
                     "districts_with_noncontiguous": int((L1[f"{k}_n_noncontiguous"] > 0).sum()),
                     "q_district_median": float(L1[f"{k}_q"].median()), "q_district_min": float(L1[f"{k}_q"].min()), "q_district_max": float(L1[f"{k}_q"].max()),
                     "ifr_district_min": float(L1[f"{k}_ifr"].min()), "ifr_district_max": float(L1[f"{k}_ifr"].max()),
                     "ifr_seoul_num_over_den": num / float(tot_out)})
    for r in summ:   # 합의 재현성(두 알고리즘 공통 절차): 확정 해상도의 최빈 분할 비율, 독립 반복 안정성
        k = r["partition"]
        if k in mets:
            r.update({"modal_share_median": float(L1[f"{k}_modal_share"].median()), "modal_share_min": float(L1[f"{k}_modal_share"].min()),
                      "districts_modal_not_equal_consensus": int((~L1[f"{k}_modal_equals_consensus"]).sum()),
                      "districts_stability_ari_below_1": int((L1[f"{k}_stability_ari_min"] < 1 - 1e-12).sum()),
                      "stability_ari_min_overall": float(L1[f"{k}_stability_ari_min"].min()),
                      "districts_hitting_target_at_few_resolutions_le10": int((L1[f"{k}_n_resolutions_hitting_target"] <= 10).sum())})
    L2 = pd.DataFrame(summ)
    L2["districts_leiden_q_ge_louvain"] = int((L1["leiden_minus_louvain_q"] >= -1e-12).sum())
    L2["districts_leiden_ifr_ge_louvain"] = int((L1["leiden_minus_louvain_ifr"] >= -1e-12).sum())
    L2["districts_same_partition_leiden_louvain"] = int((L1["leiden_louvain_ari"] > 1 - 1e-12).sum())
    L2.to_csv(OUT / "L2_city_summary_2025.csv", index=False, encoding="utf-8-sig", float_format="%.12g")
    print(json.dumps(checks, ensure_ascii=False, indent=1))
    print(L2.T.to_string())
    assert checks["pass"], checks


if __name__ == "__main__":
    main()
