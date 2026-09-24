# -*- coding: utf-8 -*-
"""
s04_promote_canonical.py — Leiden 실행 결과를 검사하고 data/ 정본으로 올린다
==============================================================================
s03 의 output/leiden/{year}/ 는 "실행 결과"이고, 다른 연구(01~04)가 읽는 것은 data/ 의 "정본"이다.
이 스크립트가 그 사이의 문턱이다. 조건을 하나라도 어기면 정본을 만들지 않고 멈춘다.

검사
  - 동 424개 전부 1번씩, 코드가 동 정본과 일치
  - 커뮤니티 116개, 구별 개수 == config.TARGET_COMMUNITIES (== 공식 생활권 구별 개수)
  - 공간적으로 끊어진 커뮤니티가 없음 (있으면 --allow-noncontiguous 로만 통과, 매니페스트에 기록)

출력 (data/)
  - dong_to_leiden_{year}_mapping_424.csv / .xlsx
  - seoul_boundaries_all.gpkg   layers: dong_424 (모든 매핑 열 포함), official_livingzone_116 (공식 폴리곤),
                                        official_livingzone_116_dongbased (동 매핑 dissolve), leiden_2020_116, leiden_2025_116
  - manifest.json               정본 파일별 SHA-256·크기·생성시각, 입력(OD·동 정본) 해시, s03 실행 파라미터

실행:  python s04_promote_canonical.py --years 2020 2025
       python s04_promote_canonical.py --years 2020 --tag _test   (점검 실행 결과를 임시로 올려볼 때; 정본 폴더 대신 data/_preview/ 에 씀)
"""
import sys, json, argparse, datetime
from pathlib import Path

import pandas as pd
import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C

COLS = ["Dong", "Ku", "ku_name", "ADM_NM", "community", "global_community_id", "community_name",
        "membership_prob", "life_zone_id", "life_zone_name"]


def check_mapping(m: pd.DataFrame, dong: pd.DataFrame, year: str, allow_noncontig: bool, metrics: pd.DataFrame):
    errs = []
    if len(m) != C.N_DONG or m["Dong"].nunique() != C.N_DONG:
        errs.append(f"행 수 {len(m)} / 고유 동 {m['Dong'].nunique()} (기대 {C.N_DONG})")
    if set(m["Dong"]) != set(dong["Dong"]):
        errs.append("동 코드 집합이 동 정본과 다름")
    if (m["Dong"] // 100 != m["Ku"]).any():
        errs.append("Ku 가 Dong 앞 5자리와 다른 행 존재")
    if m["global_community_id"].nunique() != C.N_LZ:
        errs.append(f"커뮤니티 수 {m['global_community_id'].nunique()} (기대 {C.N_LZ})")
    per = m.groupby("Ku")["community"].nunique().to_dict()
    bad = {k: (v, C.TARGET_COMMUNITIES[k]) for k, v in per.items() if v != C.TARGET_COMMUNITIES[k]}
    if bad:
        errs.append(f"구별 커뮤니티 수 불일치 {{구: (결과, 목표)}}: {bad}")
    nc = int(metrics["n_noncontiguous_communities"].sum()) if "n_noncontiguous_communities" in metrics else 0
    if nc and not allow_noncontig:
        errs.append(f"공간적으로 끊어진 커뮤니티 {nc}개 (--allow-noncontiguous 로 강제 통과 가능)")
    if errs:
        raise SystemExit(f"[{year}] 정본 승격 중단:\n  - " + "\n  - ".join(errs))
    return nc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="+", default=list(C.YEARS))
    ap.add_argument("--tag", default="")
    ap.add_argument("--allow-noncontiguous", action="store_true")
    a = ap.parse_args()

    out_dir = C.DATA_DIR if not a.tag else C.DATA_DIR / "_preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    dong = gpd.read_file(C.DONG_GPKG, layer="epsg5179")
    dong["Dong"] = dong["Dong"].astype(int); dong["Ku"] = dong["Ku"].astype(int)
    lz = gpd.read_file(C.LZ_GPKG, layer="epsg5179")
    lzmap = pd.read_csv(C.DONG_LZ_MAP)

    layers = {"official_livingzone_116": lz}
    dong_layer = dong[["Dong", "Ku", "ku_name", "ADM_NM", "dong_area_sqm", "life_zone_id", "life_zone_name", "geometry"]].copy()
    lz_dongbased = dong.dissolve(by="life_zone_id", aggfunc={"Ku": "first", "ku_name": "first", "life_zone_name": "first"}, as_index=False)
    lz_dongbased["n_dongs"] = dong.groupby("life_zone_id").size().reindex(lz_dongbased["life_zone_id"]).values
    layers["official_livingzone_116_dongbased"] = lz_dongbased

    manifest = {"created": datetime.datetime.now().isoformat(timespec="seconds"), "env": C.env_info(),
                "n_dong": C.N_DONG, "n_lz": C.N_LZ, "years": {}, "files": {}}
    for year in a.years:
        src = C.LEIDEN_OUT / (year + a.tag)
        m = pd.read_csv(src / "metrics" / f"leiden_mapping_{year}.csv")
        metrics = pd.read_csv(src / "metrics" / f"leiden_metrics_{year}.csv")
        run_info = json.loads((src / "run_info.json").read_text(encoding="utf-8"))
        nc = check_mapping(m, dong, year, a.allow_noncontiguous, metrics)
        m = m[COLS].sort_values("Dong").reset_index(drop=True)

        csv_path = out_dir / f"dong_to_leiden_{year}_mapping_{C.N_DONG}.csv"
        m.to_csv(csv_path, index=False, encoding="utf-8-sig")
        with pd.ExcelWriter(csv_path.with_suffix(".xlsx")) as w:
            m.to_excel(w, sheet_name=f"mapping_{C.N_DONG}", index=False)
            metrics.to_excel(w, sheet_name="ku_metrics", index=False)
            (m.groupby(["Ku", "ku_name"]).agg(n_dongs=("Dong", "count"), n_communities=("community", "nunique"))
               .reset_index().to_excel(w, sheet_name="ku_summary", index=False))

        g = dong.merge(m[["Dong", "community", "global_community_id", "community_name", "membership_prob"]], on="Dong")
        comm = g.dissolve(by="global_community_id", aggfunc={"Ku": "first", "ku_name": "first", "community": "first",
                                                              "community_name": "first", "membership_prob": "mean"}, as_index=False)
        comm["n_dongs"] = g.groupby("global_community_id").size().reindex(comm["global_community_id"]).values
        comm["area_km2"] = comm.geometry.area / 1e6
        layers[f"leiden_{year}_{C.N_LZ}"] = comm
        dong_layer = dong_layer.merge(m[["Dong", "global_community_id", "membership_prob"]]
                                      .rename(columns={"global_community_id": f"leiden_{year}", "membership_prob": f"leiden_{year}_prob"}), on="Dong")
        manifest["years"][year] = {"source": str(src), "run_info": run_info, "noncontiguous_communities": nc,
                                   "metrics_summary": {"resolution_min": float(metrics["resolution"].min()),
                                                        "resolution_max": float(metrics["resolution"].max()),
                                                        "stability_ari_min": float(metrics["stability_ari_min"].min()),
                                                        "modal_equals_consensus_all": bool(metrics["modal_equals_consensus"].all())}}
        manifest["files"][csv_path.name] = {"sha256": C.sha256_of(csv_path), "bytes": csv_path.stat().st_size}

    layers = {"dong_424": dong_layer, **layers}
    gpkg = out_dir / C.BOUNDARIES_ALL_GPKG.name
    C.save_gpkg_layers(gpkg, layers)
    for p in (gpkg, C.DONG_GPKG, C.LZ_GPKG, C.DONG_LZ_MAP):
        manifest["files"][p.name] = {"sha256": C.sha256_of(p), "bytes": p.stat().st_size}
    for year in a.years:
        p = C.od_daily_path(year)
        if p.exists():
            manifest["files"][p.name] = {"sha256": C.sha256_of(p), "bytes": p.stat().st_size}
    (out_dir / C.MANIFEST_JSON.name).write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"정본 생성 완료 → {out_dir}")
    for k, v in manifest["files"].items():
        print(f"  {k:48s} {v['sha256'][:16]}…  {v['bytes']:,} B")


if __name__ == "__main__":
    main()
