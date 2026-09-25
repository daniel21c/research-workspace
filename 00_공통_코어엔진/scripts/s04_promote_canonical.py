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
  - (2026-09-25) s03 run_info 의 입력 해시(od_daily, 동 정본)가 지금 data/ 파일과 같음 — 입력을 바꾼 뒤 s03 을 안 돌렸으면 멈춤
  - (2026-09-25) 정본(태그 없음)은 s03 이 정본 설정(3,000회, τ 0.5, Q 우선, 해상도 0.01~2.50, 안정성 10회, 목표 개수 = 공식)으로 돈 결과여야 함
  - (2026-09-25) data/ 에 쓸 때는 두 해를 함께만. 모든 연도를 먼저 검사하고, 임시 폴더에 다 만든 뒤 한꺼번에 옮긴다

출력 (data/)
  - dong_to_leiden_{year}_mapping_424.csv / .xlsx
  - seoul_boundaries_all.gpkg   layers: dong_424 (모든 매핑 열 포함), official_livingzone_116 (공식 폴리곤),
                                        official_livingzone_116_dongbased (동 매핑 dissolve), leiden_2020_116, leiden_2025_116
  - manifest.json               정본 파일별 SHA-256·크기·생성시각, 입력(OD·동 정본) 해시, s03 실행 파라미터

실행:  python s04_promote_canonical.py --years 2020 2025
       python s04_promote_canonical.py --years 2020 --tag _test   (점검 실행 결과를 임시로 올려볼 때; 정본 폴더 대신 data/_preview/ 에 씀)
       python s04_promote_canonical.py --out-dir <폴더>           (정본을 건드리지 않고 같은 결과·해시가 나오는지 재현 확인)
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


def check_inputs(year: str, run_info: dict, canonical: bool) -> list:
    """s03 실행이 지금 data/ 의 입력으로, (정본이면) 정본 설정으로 만든 것인지 확인. 문제 목록을 돌려준다."""
    errs = []
    if run_info.get("input_od") != C.sha256_of(C.od_daily_path(year)):
        errs.append(f"s03 이 쓴 od_daily 해시가 현재 {C.od_daily_path(year).name} 와 다름 → s02 뒤에 s03 을 다시 돌려야 함")
    if run_info.get("input_dong") != C.sha256_of(C.DONG_GPKG):
        errs.append(f"s03 이 쓴 동 정본 해시가 현재 {C.DONG_GPKG.name} 와 다름 → s01 뒤에 s03 을 다시 돌려야 함")
    if canonical:
        p = run_info.get("params", {})
        want = {"res_min": C.RES_MIN, "res_max": C.RES_MAX, "res_step": C.RES_STEP, "n_iter": C.N_ITER, "tau": C.TAU,
                "self_loops": C.INCLUDE_SELF_LOOPS, "primary": C.SELECTION_PRIMARY, "stab_trials": C.STABILITY_TRIALS}
        diff = {k: (p.get(k), v) for k, v in want.items() if p.get(k) != v}
        if diff:
            errs.append(f"정본 설정과 다른 s03 실행 {{항목: (실행값, 정본값)}}: {diff}")
        if "targets_file" in p:
            errs.append(f"목표 개수 파일로 돌린 실행({p['targets_file']})은 정본이 될 수 없음")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="+", default=list(C.YEARS))
    ap.add_argument("--tag", default="")
    ap.add_argument("--allow-noncontiguous", action="store_true")
    ap.add_argument("--out-dir", default=None,
                    help="정본 대신 이 폴더에 써 본다 (재현 확인용. 예: 공동연구자가 data/ 를 건드리지 않고 같은 해시가 나오는지 볼 때)")
    a = ap.parse_args()
    years = [y for y in C.YEARS if y in set(a.years)] + sorted(set(a.years) - set(C.YEARS))

    # 2026-09-25: data/ 정본은 두 해를 함께만 승격한다. 한 해만 주면 통합 gpkg·manifest 가 그 해만으로 다시 쓰여 다른 해가 빠졌다.
    writes_canonical = not a.tag and a.out_dir is None
    if writes_canonical and set(years) != set(C.YEARS):
        raise SystemExit(f"정본(data/)은 {', '.join(C.YEARS)} 를 함께 승격해야 합니다 (요청: {', '.join(years)}). "
                         f"한 해만 점검하려면 --tag 또는 --out-dir 를 쓰세요.")
    out_dir = Path(a.out_dir) if a.out_dir else (C.DATA_DIR if not a.tag else C.DATA_DIR / "_preview")
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

    # 1단계: 모든 연도를 먼저 검사한다 (하나라도 어기면 아무것도 쓰지 않는다)
    loaded, problems = {}, []
    for year in years:
        src = C.LEIDEN_OUT / (year + a.tag)
        m = pd.read_csv(src / "metrics" / f"leiden_mapping_{year}.csv")
        metrics = pd.read_csv(src / "metrics" / f"leiden_metrics_{year}.csv")
        run_info = json.loads((src / "run_info.json").read_text(encoding="utf-8"))
        try:
            nc = check_mapping(m, dong, year, a.allow_noncontiguous, metrics)
        except SystemExit as e:
            problems.append(str(e)); continue
        errs = check_inputs(year, run_info, canonical=not a.tag)
        if errs:
            problems.append(f"[{year}] 정본 승격 중단:\n  - " + "\n  - ".join(errs)); continue
        loaded[year] = (src, m, metrics, run_info, nc)
    if problems:
        raise SystemExit("\n".join(problems) + "\n→ 아무 파일도 쓰지 않았습니다.")

    # 2단계: 임시 폴더에 전부 만든 뒤 마지막에 한꺼번에 옮긴다 (중간에 멈춰도 정본이 섞이지 않게)
    import os, shutil
    stage = out_dir / f"_staging_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    stage.mkdir()
    manifest = {"created": datetime.datetime.now().isoformat(timespec="seconds"), "env": C.env_info(),
                "n_dong": C.N_DONG, "n_lz": C.N_LZ, "years": {}, "files": {}}
    for year in years:
        src, m, metrics, run_info, nc = loaded[year]
        m = m[COLS].sort_values("Dong").reset_index(drop=True)

        csv_path = stage / f"dong_to_leiden_{year}_mapping_{C.N_DONG}.csv"
        m.to_csv(csv_path, index=False, encoding="utf-8-sig", lineterminator="\n")   # LF 고정: Windows 에서 다시 만들어도 등록 해시와 같게
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
    gpkg = stage / C.BOUNDARIES_ALL_GPKG.name
    C.save_gpkg_layers(gpkg, layers)
    for p in (gpkg, C.DONG_GPKG, C.LZ_GPKG, C.DONG_LZ_MAP):
        manifest["files"][p.name] = {"sha256": C.sha256_of(p), "bytes": p.stat().st_size}
    for year in years:
        p = C.od_daily_path(year)
        if p.exists():
            manifest["files"][p.name] = {"sha256": C.sha256_of(p), "bytes": p.stat().st_size}
    (stage / C.MANIFEST_JSON.name).write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for f in sorted(stage.iterdir()):          # manifest 는 맨 마지막에 옮긴다 (manifest 가 있으면 나머지는 이미 새 판)
        if f.name != C.MANIFEST_JSON.name:
            os.replace(f, out_dir / f.name)
    os.replace(stage / C.MANIFEST_JSON.name, out_dir / C.MANIFEST_JSON.name)
    shutil.rmtree(stage, ignore_errors=True)
    print(f"정본 생성 완료 → {out_dir}")
    for k, v in manifest["files"].items():
        print(f"  {k:48s} {v['sha256'][:16]}…  {v['bytes']:,} B")


if __name__ == "__main__":
    main()
