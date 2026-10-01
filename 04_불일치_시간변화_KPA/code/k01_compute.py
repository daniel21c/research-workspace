# -*- coding: utf-8 -*-
"""
k01 — 지표 계산 (연구설계 4.4 ①~⑥)

입력: 코어엔진 확정 배포본 (od_daily 2020/2025, 공식 생활권 매핑, Leiden 매핑 2020/2025, 동 경계)
출력: results/
  t01_data_summary.csv        자료 요약 (연도별 통행량, * 비율, 동·권역 수)
  t02_gu_metrics_{year}.csv   구별 T, N, a, b, IFR_lz, IFR_ld, G, D, SR
  t02_gu_metrics_long.csv     두 해를 한 표로
  t03_gu_change.csv           구별 ΔIFR, ΔG, ΔD + 서울 전체
  t04_decomposition.csv       경계 재도출 효과 / 통행 효과 분해 (G, D 각각)
  t05_null_partitions.csv     귀무 분할 IFR 분포 (H4)
  t08_lz116_metrics.csv       생활권 116 보조표
  t09_ari_ld20_ld25.csv       구별 LD2020 vs LD2025 ARI, 소속이 바뀐 동
  t10_iou_vs_gap.csv          구별 IoU(1:1 대응)와 G·D, t10_iou_regression.csv 는 D·G ~ IoU 회귀의 R²·p
  results.json                핵심 수치 (원고 작성 스크립트가 읽는다)

실행: python k01_compute.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
import kpa_metrics as km


# ---------------------------------------------------------------- 입력 읽기
def read_mapping(path: Path, col: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["Dong"] = df["Dong"].astype(int)
    if df["Dong"].duplicated().any():
        raise ValueError(f"{path.name}: 동 코드 중복")
    if len(df) != 424:
        raise ValueError(f"{path.name}: 424행이 아니다 ({len(df)})")
    return df.set_index("Dong")


def load_inputs():
    lz = read_mapping(C.LZ_MAP, "life_zone_id")
    ku = lz["Ku"].astype(int)
    lz_zone = lz["life_zone_id"].astype(int)
    ld = {y: read_mapping(C.ld_map(y), "global_community_id")["global_community_id"].astype(int) for y in C.YEARS}
    od = {y: pd.read_parquet(C.od_daily(y)) for y in C.YEARS}
    for y in C.YEARS:
        od[y]["dong_O"] = od[y]["dong_O"].astype(int)
        od[y]["dong_D"] = od[y]["dong_D"].astype(int)
    return od, lz_zone, ld, ku, lz


def gu_frame(g: pd.DataFrame) -> pd.DataFrame:
    g = g.copy()
    g.index.name = "ku_code"
    g.insert(0, "ku_name", [C.KU_NAME[k] for k in g.index])
    g.insert(1, "ku_name_en", [C.KU_NAME_EN[k] for k in g.index])
    return g


# ---------------------------------------------------------------- 귀무 분할 (H4)
def build_adjacency():
    import geopandas as gpd
    g = gpd.read_file(C.DONG_GPKG, layer="epsg5179")[["Dong", "Ku", "geometry"]]
    g["Dong"] = g["Dong"].astype(int)
    g["Ku"] = g["Ku"].astype(int)
    sidx = g.sindex
    adj = {d: set() for d in g["Dong"]}
    geoms = g.geometry.values
    for i, geom in enumerate(geoms):
        for j in sidx.query(geom, predicate="intersects"):
            if i != j and g["Ku"].iat[i] == g["Ku"].iat[j] and geom.buffer(1).intersects(geoms[j]):
                adj[g["Dong"].iat[i]].add(g["Dong"].iat[j])
    return adj, g


def null_partitions(od, ku, lz_zone, ld, adj, dongs_by_ku):
    """구마다 N_NULL개의 무작위 인접 분할을 만들고, 같은 분할을 두 해 통행에 적용해 IFR을 계산한다."""
    rng = np.random.default_rng(C.NULL_SEED)
    rows = []
    for k, dongs in dongs_by_ku.items():
        dongs = list(dongs)
        pos = {d: i for i, d in enumerate(dongs)}
        target = C.TARGET_COMMUNITIES[k]
        W, T = {}, {}
        for y in C.YEARS:
            o = od[y][od[y]["dong_O"].isin(pos)]
            T[y] = float(o["flow"].sum())
            inside = o[o["dong_D"].isin(pos)]
            M = np.zeros((len(dongs), len(dongs)))
            M[inside["dong_O"].map(pos).values, inside["dong_D"].map(pos).values] = inside["flow"].values
            W[y] = M
        labels = [km.random_contiguous_partition(adj, dongs, target, rng) for _ in range(C.N_NULL)]
        for i, lab in enumerate(labels):
            r = {"ku_code": k, "draw": i}
            for y in C.YEARS:
                r[f"IFR_{y}"] = km.ifr_of_labels(W[y], T[y], lab)
            r["dIFR"] = r[f"IFR_{C.Y1}"] - r[f"IFR_{C.Y0}"]
            rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 메인
def main():
    t0 = time.time()
    od, lz_zone, ld, ku, lz_df = load_inputs()
    manifest = json.loads(C.MANIFEST.read_text(encoding="utf-8"))

    # ① 자료 요약
    summ = []
    for y in C.YEARS:
        s = json.loads(C.od_summary(y).read_text(encoding="utf-8"))
        o = od[y]
        summ.append({
            "year": y,
            "flow_daily_seoul": float(o["flow"].sum()),
            "rows_daily": int(len(o)),
            "n_masked_rows_daily": int(o["n_masked"].sum()) if "n_masked" in o else None,
            "n_rows_daily_raw": int(o["n_rows"].sum()) if "n_rows" in o else None,
            "masked_row_share_daily": float(o["n_masked"].sum() / o["n_rows"].sum()) if "n_masked" in o else None,
            "n_dong": int(pd.Index(o["dong_O"]).union(o["dong_D"]).nunique()),
            "n_lz": int(lz_zone.nunique()),
            "n_ld": int(ld[y].nunique()),
            "ld_base_seed": manifest["years"][y]["run_info"]["base_seed"],
            "ld_n_iter": manifest["years"][y]["run_info"]["params"]["n_iter"],
            "ld_stability_ari_min": manifest["years"][y]["metrics_summary"]["stability_ari_min"],
            "od_sha256": manifest["files"][f"od_daily_{y}01.parquet"]["sha256"],
            "ld_sha256": manifest["files"][f"dong_to_leiden_{y}_mapping_424.csv"]["sha256"],
        })
    t01 = pd.DataFrame(summ)
    t01.to_csv(C.TAB / "t01_data_summary.csv", index=False, encoding="utf-8-sig")

    # ② 연도별 구 지표 (본분석: 연도별 LD)
    gu, lz116, tagged = {}, {}, {}
    for y in C.YEARS:
        t = km.tag_flows(od[y], lz_zone, ld[y], ku)
        tagged[y] = t
        g = km.metrics_by_gu(t)
        km.check_identities(g)                                  # T3
        z = km.metrics_by_lz(t)
        km.check_aggregation(g, z)                              # T4
        if not np.isclose(g["T"].sum(), od[y]["flow"].sum()):   # T1
            raise AssertionError("구별 T 합이 서울 내부 총량과 다르다")
        gu[y], lz116[y] = gu_frame(g), z
        gu_frame(g).to_csv(C.TAB / f"t02_gu_metrics_{y}.csv", encoding="utf-8-sig")

    long = pd.concat([gu[y].assign(year=y) for y in C.YEARS]).reset_index()
    long.to_csv(C.TAB / "t02_gu_metrics_long.csv", index=False, encoding="utf-8-sig")
    seoul = {y: km.metrics_total(gu[y]) for y in C.YEARS}

    # ③ 변화
    ch = gu[C.Y0][["ku_name", "ku_name_en"]].copy()
    for c in ("IFR_lz", "IFR_ld", "G", "D", "SR"):
        ch[f"{c}_{C.Y0}"] = gu[C.Y0][c]
        ch[f"{c}_{C.Y1}"] = gu[C.Y1][c]
        ch[f"d{c}"] = gu[C.Y1][c] - gu[C.Y0][c]
    ch["absG_grew"] = gu[C.Y1]["G"].abs() > gu[C.Y0]["G"].abs()
    ch["quadrant"] = np.select(
        [(ch[f"G_{C.Y0}"] > 0) & (ch[f"G_{C.Y1}"] > 0), (ch[f"G_{C.Y0}"] <= 0) & (ch[f"G_{C.Y1}"] > 0),
         (ch[f"G_{C.Y0}"] <= 0) & (ch[f"G_{C.Y1}"] <= 0)], ["I (+,+)", "II (-,+)", "III (-,-)"], "IV (+,-)")
    seoul_row = {"ku_name": "서울 전체", "ku_name_en": "Seoul"}
    for c in ("IFR_lz", "IFR_ld", "G", "D", "SR"):
        seoul_row[f"{c}_{C.Y0}"] = seoul[C.Y0][c]; seoul_row[f"{c}_{C.Y1}"] = seoul[C.Y1][c]
        seoul_row[f"d{c}"] = seoul[C.Y1][c] - seoul[C.Y0][c]
    ch_out = pd.concat([ch, pd.DataFrame([seoul_row], index=["SEOUL"])])
    ch_out.index.name = "ku_code"
    ch_out.to_csv(C.TAB / "t03_gu_change.csv", encoding="utf-8-sig")

    # ⑤ 분해: X(LD_s, OD_u) 네 조합
    combo = {}
    for s in C.YEARS:
        for u in C.YEARS:
            combo[(s, u)] = km.metrics_by_gu(km.tag_flows(od[u], lz_zone, ld[s], ku))
    dec_rows = []
    for metric in ("G", "D", "IFR_ld"):
        x = {k: v[metric] for k, v in combo.items()}
        d = km.decompose(x[(C.Y0, C.Y0)], x[(C.Y0, C.Y1)], x[(C.Y1, C.Y1)], x[(C.Y1, C.Y0)])
        d.insert(0, "metric", metric)
        d.insert(1, "ku_name", [C.KU_NAME[k] for k in d.index])
        # 서울 전체
        tot = {k: km.metrics_total(v)[metric] for k, v in combo.items()}
        ts = km.decompose(*(pd.Series([tot[k]], index=["SEOUL"]) for k in
                            [(C.Y0, C.Y0), (C.Y0, C.Y1), (C.Y1, C.Y1), (C.Y1, C.Y0)]))
        ts.insert(0, "metric", metric); ts.insert(1, "ku_name", "서울 전체")
        dec_rows += [d, ts]
    dec = pd.concat(dec_rows); dec.index.name = "ku_code"
    dec.to_csv(C.TAB / "t04_decomposition.csv", encoding="utf-8-sig")
    # LD2020 고정 시 2025 지표 (민감도 표)
    fixed = gu_frame(combo[(C.Y0, C.Y1)])[["ku_name", "IFR_lz", "IFR_ld", "G", "D"]]
    fixed.columns = ["ku_name", "IFR_lz_2025", "IFR_ld20on25", "G_ld20on25", "D_ld20on25"]
    fixed.to_csv(C.TAB / "t04b_fixed_ld2020_on_2025.csv", encoding="utf-8-sig")

    # ⑧ 생활권 116 보조표
    z = pd.concat([lz116[y].assign(year=y) for y in C.YEARS]).reset_index()
    names = lz_df.drop_duplicates("life_zone_id").set_index("life_zone_id")["life_zone_name"]
    z.insert(1, "life_zone_name", z["lz_O"].map(names))
    z.to_csv(C.TAB / "t08_lz116_metrics.csv", index=False, encoding="utf-8-sig")

    # ⑨ LD2020 vs LD2025 경계 변화 (구별 ARI, 소속 바뀐 동)
    ari_rows = []
    for k in sorted(C.KU_NAME):
        dongs = ku.index[ku == k]
        a, b = ld[C.Y0].loc[dongs], ld[C.Y1].loc[dongs]
        ari = km.adjusted_rand_index(a, b)
        # 소속이 바뀐 동: 2020 커뮤니티 동료 집합과 2025 동료 집합이 다른 동
        peers20 = {d: frozenset(a.index[a == a[d]]) for d in dongs}
        peers25 = {d: frozenset(b.index[b == b[d]]) for d in dongs}
        changed = [d for d in dongs if peers20[d] != peers25[d]]
        ari_rows.append({"ku_code": k, "ku_name": C.KU_NAME[k], "n_dong": len(dongs),
                         "ari_ld20_ld25": ari, "n_dong_changed": len(changed),
                         "dongs_changed": ";".join(lz_df.loc[changed, "ADM_NM"]),
                         "ari_ld_lz_2020": km.adjusted_rand_index(a, lz_zone.loc[dongs]),
                         "ari_ld_lz_2025": km.adjusted_rand_index(b, lz_zone.loc[dongs])})
    ari = pd.DataFrame(ari_rows).set_index("ku_code")
    ari.to_csv(C.TAB / "t09_ari_ld20_ld25.csv", encoding="utf-8-sig")

    # ⑩ 경계 모양 일치도 IoU (연구2 5.3(b) 1:1 최대교집합 배정, 동 개수 기준) — D의 외부 검증용
    from scipy.optimize import linear_sum_assignment
    def iou_1to1(a, b):
        ct = pd.crosstab(a, b).values
        r, c = linear_sum_assignment(-ct)
        S = ct[r, c].sum(); N = ct.sum()
        return float(S / (2 * N - S))
    iou_rows = []
    for k in sorted(C.KU_NAME):
        dongs = ku.index[ku == k]
        row = {"ku_code": k, "ku_name": C.KU_NAME[k]}
        for y in C.YEARS:
            row[f"IoU_{y}"] = iou_1to1(lz_zone.loc[dongs], ld[y].loc[dongs])
        row["dIoU"] = row[f"IoU_{C.Y1}"] - row[f"IoU_{C.Y0}"]
        iou_rows.append(row)
    iou = pd.DataFrame(iou_rows).set_index("ku_code")
    for y in C.YEARS:
        for c in ("G", "D", "IFR_lz", "IFR_ld"):
            iou[f"{c}_{y}"] = gu[y][c]
    iou["dG"] = ch["dG"]; iou["dD"] = ch["dD"]
    iou.to_csv(C.TAB / "t10_iou_vs_gap.csv", encoding="utf-8-sig")
    # D·G ~ IoU 선형회귀(구 25개): 원고 Ⅲ.1 3)의 R²·p를 결과 파일로 남긴다(2026-10-02 감사 지적: 원고 수치 대조가 계산해 쓰던 값과 고정 문구 "p < 0.001").
    from scipy.stats import linregress
    reg_rows = []
    for y in C.YEARS:
        for target in ("D", "G"):
            for sample in ("전체", "같은_구_제외"):
                sub = iou if sample == "전체" else iou[iou[f"D_{y}"] != 0]          # 같은 구 = 두 경계가 완전히 같아 D = 0
                r = linregress(sub[f"IoU_{y}"], sub[f"{target}_{y}"])
                reg_rows.append({"year": y, "target": target, "sample": sample, "n": len(sub), "r2": r.rvalue ** 2, "slope": r.slope, "p_value": r.pvalue})
    pd.DataFrame(reg_rows).to_csv(C.TAB / "t10_iou_regression.csv", index=False, encoding="utf-8-sig")

    # ⑪ 생활권(116) 단위 변화표 — 본문에는 쓰지 않고, 선별 구 안에서 문제 생활권을 지목할 때만 쓴다
    zw = z.pivot(index="lz_O", columns="year", values=["G", "D", "T"])
    zw.columns = [f"{a}_{b}" for a, b in zw.columns]
    zw["life_zone_name"] = z.drop_duplicates("lz_O").set_index("lz_O")["life_zone_name"]
    zw["ku_code"] = lz_df.drop_duplicates("life_zone_id").set_index("life_zone_id")["Ku"].astype(int)
    zw["dD"] = zw[f"D_{C.Y1}"] - zw[f"D_{C.Y0}"]; zw["dG"] = zw[f"G_{C.Y1}"] - zw[f"G_{C.Y0}"]
    zw.to_csv(C.TAB / "t08b_lz116_change.csv", encoding="utf-8-sig")

    # ⑥ 귀무 분할 (H4)
    adj, gdf = build_adjacency()
    dongs_by_ku = {k: sorted(ku.index[ku == k]) for k in sorted(C.KU_NAME)}
    null = null_partitions(od, ku, lz_zone, ld, adj, dongs_by_ku)
    null.to_csv(C.TAB / "t05_null_partitions.csv", index=False, encoding="utf-8-sig")
    nsum = null.groupby("ku_code").agg(
        null_IFR_2020_med=("IFR_2020", "median"), null_IFR_2025_med=("IFR_2025", "median"),
        null_dIFR_med=("dIFR", "median"), null_dIFR_p05=("dIFR", lambda s: s.quantile(0.05)),
        null_dIFR_p95=("dIFR", lambda s: s.quantile(0.95)))
    nsum["dIFR_lz"] = ch["dIFR_lz"]; nsum["dIFR_ld"] = ch["dIFR_ld"]
    nsum["lz_within_null90"] = (nsum["dIFR_lz"] >= nsum["null_dIFR_p05"]) & (nsum["dIFR_lz"] <= nsum["null_dIFR_p95"])
    nsum["ld_within_null90"] = (nsum["dIFR_ld"] >= nsum["null_dIFR_p05"]) & (nsum["dIFR_ld"] <= nsum["null_dIFR_p95"])
    # 귀무 IFR 대비 백분위 (수준)
    for y in C.YEARS:
        for B in ("lz", "ld"):
            nsum[f"pct_{B}_{y}"] = [float((null.loc[null.ku_code == k, f"IFR_{y}"] < gu[y].loc[k, f"IFR_{B}"]).mean())
                                    for k in nsum.index]
    nsum.insert(0, "ku_name", [C.KU_NAME[k] for k in nsum.index])
    nsum.to_csv(C.TAB / "t05_null_summary.csv", encoding="utf-8-sig")

    # results.json
    res = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "inputs": {k: manifest["files"][k]["sha256"] for k in manifest["files"]},
        "seoul": {y: {c: float(seoul[y][c]) for c in ("T", "IFR_lz", "IFR_ld", "G", "D", "SR", "a", "b")} for y in C.YEARS},
        "seoul_change": {c: float(seoul[C.Y1][c] - seoul[C.Y0][c]) for c in ("IFR_lz", "IFR_ld", "G", "D", "SR")},
        "gu_simple_mean": {y: {c: float(gu[y][c].mean()) for c in ("IFR_lz", "IFR_ld", "G", "D")} for y in C.YEARS},
        "counts": {
            "G_pos_2020": int((gu[C.Y0]["G"] > 0).sum()), "G_pos_2025": int((gu[C.Y1]["G"] > 0).sum()),
            "G_zero_2020": int(np.isclose(gu[C.Y0]["G"], 0, atol=C.FLOAT_TOL).sum()),
            "G_zero_2025": int(np.isclose(gu[C.Y1]["G"], 0, atol=C.FLOAT_TOL).sum()),
            "dD_pos": int((ch["dD"] > 0).sum()), "dG_pos": int((ch["dG"] > 0).sum()),
            "absG_grew": int(ch["absG_grew"].sum()),
            "dIFR_lz_pos": int((ch["dIFR_lz"] > 0).sum()), "dIFR_ld_pos": int((ch["dIFR_ld"] > 0).sum()),
            "quadrant": ch["quadrant"].value_counts().to_dict(),
        },
        "range": {f"d{c}": [float(ch[f"d{c}"].min()), float(ch[f"d{c}"].max())] for c in ("IFR_lz", "IFR_ld", "G", "D")},
        "decomposition_seoul": {m: dec[(dec.index == "SEOUL") & (dec.metric == m)].iloc[0][
            ["total", "flow_effect_mean", "boundary_effect_mean"]].astype(float).to_dict() for m in ("G", "D", "IFR_ld")},
        "null": {"n_per_gu": C.N_NULL, "seed": C.NULL_SEED,
                 "lz_within_null90_n": int(nsum["lz_within_null90"].sum()),
                 "ld_within_null90_n": int(nsum["ld_within_null90"].sum()),
                 "seoul_null_dIFR_median_of_gu_medians": float(nsum["null_dIFR_med"].median())},
        "iou_seoul_mean": {y: float(iou[f"IoU_{y}"].mean()) for y in C.YEARS},
        "ari_ld20_ld25_seoul": float(km.adjusted_rand_index(ld[C.Y0], ld[C.Y1])),
        "seconds": round(time.time() - t0, 1),
    }
    (C.TAB / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("seoul", "seoul_change", "counts")}, ensure_ascii=False, indent=1))
    print(f"완료 {res['seconds']}s → {C.TAB}")


if __name__ == "__main__":
    main()
