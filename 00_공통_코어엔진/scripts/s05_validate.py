# -*- coding: utf-8 -*-
"""
s05_validate.py — 정본을 다른 코드로 다시 계산해 맞는지 확인한다 (독립 교차검증)
=====================================================================================
s03 이 낸 숫자를 믿지 않고, data/ 의 정본 매핑과 OD 집계표만 가지고 처음부터 다시 계산한다.

검사 항목
  1. 매핑 완전성: 424개 동 1번씩, 구 코드 일치, 커뮤니티 116개, 구별 개수 == 목표
  2. IFR 재계산 (분자합/분모합): 커뮤니티별·구별·서울 전체, 공식 생활권도 같은 식으로.
     - 구별 Leiden IFR 이 s03 metrics 의 값과 1e-6 안에서 같은지
     - 서울 전체 IFR == 구별 분자합/분모합 == 커뮤니티 분자합/분모합 (같은 수여야 함)
  3. Modularity Q 재계산: config.INCLUDE_SELF_LOOPS 그래프에서 s03 값과 비교. python-louvain 이 있으면 그 함수와도 비교.
  4. 공간 연속성: 커뮤니티마다 연결요소 수 (geometry touches 기준)
  5. 분할 비교 ARI: Leiden2020 vs Leiden2025, 각각 vs 공식 생활권, vs 보관본 423 매핑(공통 423개 동)
  6. 개포3동(1123074) 이 두 해 모두 존재하고 통행량이 0 이 아닌지

출력: output/validation_report_{ts}.md, .json  (표는 md 에)
실행:  python s05_validate.py            (data/ 정본)
       python s05_validate.py --preview  (data/_preview/ 에 올린 점검 결과)
"""
import sys, json, argparse, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C
from s03_leiden_consensus import ari, modularity_q, contiguity


def ifr_table(od: pd.DataFrame, zone_of: pd.Series, name: str) -> pd.DataFrame:
    """zone_of: Dong → zone id. 분자 = 출발·도착 같은 zone, 분모 = 출발 zone 기준 서울 내 전체 출발통행"""
    z_o = od["dong_O"].map(zone_of)
    z_d = od["dong_D"].map(zone_of)
    df = pd.DataFrame({"zone": z_o, "flow": od["flow"], "internal": np.where(z_o == z_d, od["flow"], 0.0)})
    t = df.groupby("zone")[["internal", "flow"]].sum().rename(columns={"flow": "total_outflow"})
    t["ifr"] = t["internal"] / t["total_outflow"]
    t.index.name = name
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--years", nargs="+", default=list(C.YEARS))
    a = ap.parse_args()
    ddir = C.DATA_DIR / "_preview" if a.preview else C.DATA_DIR
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    R = {"checked_at": ts, "data_dir": str(ddir), "years": {}, "problems": []}
    lines = [f"# 경계 정본 교차검증 보고 ({ts})", "", f"대상: `{ddir}`", ""]

    dong = gpd.read_file(C.DONG_GPKG, layer="epsg5179").sort_values("Dong").reset_index(drop=True)
    dong["Dong"] = dong["Dong"].astype(int); dong["Ku"] = dong["Ku"].astype(int)
    lzmap = pd.read_csv(C.DONG_LZ_MAP).set_index("Dong")
    # 인접 리스트 (전체 424)
    sidx = dong.sindex
    adj = [[int(j) for j in sidx.query(geom, predicate="touches") if j != i] for i, geom in enumerate(dong.geometry.values)]
    pos = {d: i for i, d in enumerate(dong["Dong"])}

    maps, ifr_seoul = {}, {}
    for year in a.years:
        y = {}
        m = pd.read_csv(ddir / f"dong_to_leiden_{year}_mapping_{C.N_DONG}.csv").sort_values("Dong").reset_index(drop=True)
        maps[year] = m
        od = pd.read_parquet(C.od_daily_path(year))
        met = pd.read_excel(ddir / f"dong_to_leiden_{year}_mapping_{C.N_DONG}.xlsx", sheet_name="ku_metrics")

        # 1. 완전성
        y["n_rows"] = len(m); y["n_unique_dong"] = int(m["Dong"].nunique())
        y["dong_set_matches"] = set(m["Dong"]) == set(dong["Dong"])
        y["n_communities"] = int(m["global_community_id"].nunique())
        per = m.groupby("Ku")["community"].nunique().to_dict()
        y["ku_count_mismatch"] = {int(k): (int(v), C.TARGET_COMMUNITIES[k]) for k, v in per.items() if v != C.TARGET_COMMUNITIES[k]}
        for cond, msg in [(y["n_rows"] == C.N_DONG, "행 수"), (y["dong_set_matches"], "동 집합"), (y["n_communities"] == C.N_LZ, "커뮤니티 수"),
                          (not y["ku_count_mismatch"], "구별 개수")]:
            if not cond:
                R["problems"].append(f"{year}: {msg} 불일치")

        # 2. IFR 재계산
        zone_ld = m.set_index("Dong")["global_community_id"]
        zone_lz = lzmap["life_zone_id"]
        t_ld = ifr_table(od, zone_ld, "leiden_zone"); t_lz = ifr_table(od, zone_lz, "official_zone")
        ku_of_zone_ld = pd.Series({z: z // 100 for z in t_ld.index})
        ku_ld = t_ld.groupby(ku_of_zone_ld)[["internal", "total_outflow"]].sum(); ku_ld["ifr"] = ku_ld["internal"] / ku_ld["total_outflow"]
        ku_of_zone_lz = lzmap.drop_duplicates("life_zone_id").set_index("life_zone_id")["Ku"]
        ku_lz = t_lz.groupby(ku_of_zone_lz.reindex(t_lz.index).values)[["internal", "total_outflow"]].sum(); ku_lz["ifr"] = ku_lz["internal"] / ku_lz["total_outflow"]
        seoul_ld = t_ld["internal"].sum() / t_ld["total_outflow"].sum()
        seoul_lz = t_lz["internal"].sum() / t_lz["total_outflow"].sum()
        ifr_seoul[year] = {"leiden": seoul_ld, "official": seoul_lz}
        y["ifr_seoul_leiden"] = round(float(seoul_ld), 6); y["ifr_seoul_official"] = round(float(seoul_lz), 6)
        y["ifr_identity_ok"] = bool(abs(ku_ld["internal"].sum() / ku_ld["total_outflow"].sum() - seoul_ld) < 1e-12)
        cmp = met.set_index("ku_code")[["ifr", "modularity"]].join(ku_ld["ifr"].rename("ifr_recomputed"))
        y["ifr_max_abs_diff_vs_s03"] = float((cmp["ifr"] - cmp["ifr_recomputed"]).abs().max())
        if y["ifr_max_abs_diff_vs_s03"] > 1e-6:
            R["problems"].append(f"{year}: 구별 IFR 재계산값이 s03 와 다름 (max diff {y['ifr_max_abs_diff_vs_s03']:.2e})")

        # 3. Modularity 재계산 (구별 그래프)
        qd = {}
        try:
            import networkx as nx, community as louvain
            have_louvain = True
        except Exception:
            have_louvain = False
        for ku in sorted(C.TARGET_COMMUNITIES):
            nodes = sorted(m.loc[m["Ku"] == ku, "Dong"])
            ix = {d: i for i, d in enumerate(nodes)}
            sub = od[od["dong_O"].isin(ix) & od["dong_D"].isin(ix)]
            W = np.zeros((len(nodes), len(nodes)))
            for o, d, f in sub[["dong_O", "dong_D", "flow"]].values:
                W[ix[int(o)], ix[int(d)]] += f
            S = W + W.T
            E, Wt = [], []
            for i in range(len(nodes)):
                if C.INCLUDE_SELF_LOOPS and W[i, i] > 0:
                    E.append((i, i)); Wt.append(W[i, i])
                for j in range(i + 1, len(nodes)):
                    if S[i, j] > 0:
                        E.append((i, j)); Wt.append(S[i, j])
            E = np.asarray(E); Wt = np.asarray(Wt)
            lab = m.set_index("Dong").loc[nodes, "community"].values.astype(int)
            q = modularity_q(E, Wt, lab)
            row = {"q_recomputed": round(q, 6), "q_s03": round(float(met.set_index("ku_code").loc[ku, "modularity"]), 6)}
            if have_louvain:
                G = nx.Graph(); G.add_weighted_edges_from([(int(s), int(t), float(w)) for (s, t), w in zip(E, Wt)])
                row["q_python_louvain"] = round(louvain.modularity({i: int(l) for i, l in enumerate(lab)}, G, weight="weight"), 6)
            qd[ku] = row
        y["q_max_abs_diff_vs_s03"] = max(abs(v["q_recomputed"] - v["q_s03"]) for v in qd.values())
        if have_louvain:
            y["q_max_abs_diff_vs_python_louvain"] = max(abs(v["q_recomputed"] - v["q_python_louvain"]) for v in qd.values())
        if y["q_max_abs_diff_vs_s03"] > 1e-5:
            R["problems"].append(f"{year}: Q 재계산값이 s03 와 다름 (max diff {y['q_max_abs_diff_vs_s03']:.2e})")

        # 4. 공간 연속성
        lab_all = m.set_index("Dong").loc[dong["Dong"], "global_community_id"].values
        comp = contiguity(np.asarray(pd.factorize(lab_all)[0]), adj)
        y["n_noncontiguous_communities"] = int(sum(v > 1 for v in comp.values()))
        if y["n_noncontiguous_communities"]:
            R["problems"].append(f"{year}: 공간적으로 끊어진 커뮤니티 {y['n_noncontiguous_communities']}개")

        # 6. 개포3동
        gp = od[(od["dong_O"] == 1123074) | (od["dong_D"] == 1123074)]["flow"].sum()
        y["gaepo3_in_mapping"] = bool((m["Dong"] == 1123074).any()); y["gaepo3_flow"] = float(gp)
        if not y["gaepo3_in_mapping"] or gp <= 0:
            R["problems"].append(f"{year}: 개포3동(1123074) 누락 또는 통행량 0")

        # 5. 공식 생활권과의 ARI
        y["ari_vs_official"] = round(ari(zone_ld.loc[dong["Dong"]].values, zone_lz.loc[dong["Dong"]].values), 4)
        arch = C.DATA_DIR / "_archive_423_20251029" / f"dong_to_leiden_{year}_mapping_423.csv"
        if arch.exists():
            old = pd.read_csv(arch).set_index("Dong")["global_community_id"]
            common = old.index.intersection(zone_ld.index)
            y["ari_vs_archive_423_common_dongs"] = round(ari(zone_ld.loc[common].values, old.loc[common].values), 4)
            y["n_common_dongs_with_archive"] = int(len(common))

        R["years"][year] = y
        lines += [f"## {year}", "",
                  f"- 매핑: {y['n_rows']}행, 고유 동 {y['n_unique_dong']}, 커뮤니티 {y['n_communities']}, 구별 개수 불일치 {y['ku_count_mismatch'] or '없음'}",
                  f"- 서울 전체 IFR: Leiden {y['ifr_seoul_leiden']:.4f} / 공식 생활권 {y['ifr_seoul_official']:.4f} (분자합/분모합 항등식 {'성립' if y['ifr_identity_ok'] else '불성립'})",
                  f"- 구별 IFR 재계산 vs s03 최대 차이: {y['ifr_max_abs_diff_vs_s03']:.2e}",
                  f"- Q 재계산 vs s03 최대 차이: {y['q_max_abs_diff_vs_s03']:.2e}" + (f", vs python-louvain: {y['q_max_abs_diff_vs_python_louvain']:.2e}" if have_louvain else " (python-louvain 미설치)"),
                  f"- 끊어진 커뮤니티: {y['n_noncontiguous_communities']}개",
                  f"- 개포3동 포함: {y['gaepo3_in_mapping']}, 관련 통행량 {y['gaepo3_flow']:,.0f}",
                  f"- ARI vs 공식 생활권: {y['ari_vs_official']}" + (f", vs 2025-10 보관본(공통 {y.get('n_common_dongs_with_archive')}동): {y.get('ari_vs_archive_423_common_dongs')}" if 'ari_vs_archive_423_common_dongs' in y else ""),
                  "", "구별 IFR (Leiden / 공식):", "", "| 구 | Leiden IFR | 공식 IFR | 차이 | Q(재계산) |", "|---|---|---|---|---|"]
        for ku in sorted(C.TARGET_COMMUNITIES):
            a_, b_ = ku_ld.loc[ku, "ifr"], ku_lz.loc[ku, "ifr"]
            lines.append(f"| {C.KU_NAME[ku]} | {a_:.4f} | {b_:.4f} | {a_-b_:+.4f} | {qd[ku]['q_recomputed']:.4f} |")
        lines.append("")

    if len(a.years) == 2:
        y0, y1 = a.years
        common = maps[y0].set_index("Dong")["global_community_id"], maps[y1].set_index("Dong")["global_community_id"]
        R["ari_between_years"] = round(ari(common[0].loc[dong["Dong"]].values, common[1].loc[dong["Dong"]].values), 4)
        lines += [f"## 연도 간 비교", "", f"- ARI Leiden {y0} vs {y1}: {R['ari_between_years']}", ""]

    lines += ["## 판정", "", ("문제 없음" if not R["problems"] else "\n".join(f"- {p}" for p in R["problems"])), ""]
    C.OUTPUT_DIR.mkdir(exist_ok=True)
    (C.OUTPUT_DIR / f"validation_report_{ts}.md").write_text("\n".join(lines), encoding="utf-8")
    (C.OUTPUT_DIR / f"validation_report_{ts}.json").write_text(json.dumps(R, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
