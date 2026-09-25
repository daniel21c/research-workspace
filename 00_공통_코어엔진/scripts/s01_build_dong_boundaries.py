# -*- coding: utf-8 -*-
"""
s01_build_dong_boundaries.py — 동 경계 정본(424) · 공식 생활권(116) · 동→생활권 매핑
=========================================================================================
입력 (읽기 전용)
  - 통계청 행정동 경계 SHP  : config.RAW_DONG_SHP   (ADM_CD 8자리, BASE_DATE 20230701)
  - 서울 지역생활권 SHP     : config.RAW_LZ_SHP
  - 생활이동 행정동 코드표  : config.RAW_DONG_CODE_XLSX (2021-09-07, 7자리 코드)

처리
  1. SHP ADM_CD(8자리) → 생활이동 7자리 코드(Dong).
     기본: 앞 7자리. 예외: ADM_CD_TO_DONG_OVERRIDE (개포3동 11230511 → 1123074).
     ※ 이전 코드는 개포3동을 신사동(1123051)에 합쳐 423개가 되었고, 개포3동 통행이 모두 빠졌다.
  2. 같은 Dong 코드 폴리곤을 dissolve (오류2동+항동 → 1117068, 상일1동+상일2동 → 1125052).
  3. Dong 집합이 생활이동 코드표의 서울 424개와 정확히 같은지 확인. 다르면 중단.
  4. 공식 생활권 116 로드, EPSG:5179 에서 동×생활권 교차면적 → 동마다 교차면적 최대 생활권 1개 배정.
  5. 구별 생활권 수 == config.TARGET_COMMUNITIES 확인.

출력 (data/)
  - seoul_dong_424_dissolved.gpkg          layers epsg5179 / epsg4326
  - seoul_official_livingzone_116.gpkg     layers epsg5179 / epsg4326
  - dong_to_official_livingzone_mapping_424.csv / .xlsx
  - output/s01_report.json                 검증 수치

실행:  python s01_build_dong_boundaries.py
"""
import sys, json, logging
from pathlib import Path

import pandas as pd
import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("s01")


def load_dong_code_table() -> pd.DataFrame:
    """생활이동 코드표 → 서울 동 코드 424개 (Dong, ADM_NM_code)"""
    x = pd.read_excel(C.RAW_DONG_CODE_XLSX)
    x.columns = [str(c).strip() for c in x.columns]
    # 열: 시도, 시군구, 읍면동, name, full_name
    x = x[x["시도"].astype(int) == 11000].copy()
    x["Dong"] = x["읍면동"].astype(int)
    x["Ku"] = x["시군구"].astype(int)
    return x[["Dong", "Ku", "name"]].rename(columns={"name": "name_codetable"})


def build_dong(code_tbl: pd.DataFrame) -> gpd.GeoDataFrame:
    g = gpd.read_file(C.RAW_DONG_SHP, encoding="cp949")
    g = g[g.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
    g["ADM_CD"] = g["ADM_CD"].astype(str).str.zfill(8)
    g = g[g["ADM_CD"].str.startswith("11")].copy()           # 서울
    g["Dong"] = g["ADM_CD"].map(lambda c: C.ADM_CD_TO_DONG_OVERRIDE.get(c, int(c[:7])))
    g["Ku"] = g["Dong"] // 100
    log.info(f"SHP 서울 폴리곤 {len(g)}개 → 고유 Dong {g['Dong'].nunique()}개")

    # 어떤 폴리곤이 합쳐지는지 기록
    merged = (g.groupby("Dong")["ADM_NM"].agg(list).loc[lambda s: s.str.len() > 1])
    for d, names in merged.items():
        log.info(f"  dissolve: Dong {d} ← {names}")

    g = g.to_crs(C.CRS_PROJECTED)
    d = g.dissolve(by="Dong", aggfunc={"Ku": "first", "ADM_CD": "first", "ADM_NM": "first"}, as_index=False)
    d["ku_name"] = d["Ku"].map(C.KU_NAME)
    d["dong_area_sqm"] = d.geometry.area
    d["source_adm_cd"] = g.groupby("Dong")["ADM_CD"].agg(lambda s: "+".join(sorted(s))).reindex(d["Dong"]).values
    d["source_adm_nm"] = g.groupby("Dong")["ADM_NM"].agg(lambda s: "+".join(s)).reindex(d["Dong"]).values

    # 코드표와 대조
    shp_set, tbl_set = set(d["Dong"]), set(code_tbl["Dong"])
    only_shp, only_tbl = sorted(shp_set - tbl_set), sorted(tbl_set - shp_set)
    if only_shp or only_tbl:
        raise SystemExit(f"동 코드 불일치. SHP에만: {only_shp} / 코드표에만: {only_tbl}")
    if len(d) != C.N_DONG:
        raise SystemExit(f"동 수 {len(d)} != {C.N_DONG}")
    d = d.merge(code_tbl[["Dong", "name_codetable"]], on="Dong", how="left")
    # 명칭 불일치(예: 일원2동↔개포3동)는 기록만
    diff = d[d["ADM_NM"] != d["name_codetable"]][["Dong", "ADM_NM", "name_codetable"]]
    for _, r in diff.iterrows():
        log.info(f"  명칭 차이: {r.Dong} SHP={r.ADM_NM} / 코드표={r.name_codetable}")
    return d.sort_values("Dong").reset_index(drop=True)


def build_lz() -> gpd.GeoDataFrame:
    lz = gpd.read_file(C.RAW_LZ_SHP, encoding="cp949").to_crs(C.CRS_PROJECTED)
    if "fid" in lz.columns:
        lz = lz.rename(columns={"fid": "orig_fid"})
        lz["life_zone_id"] = lz["orig_fid"].astype(int)
    else:
        lz["life_zone_id"] = range(1, len(lz) + 1)
    name_col = "label_1" if "label_1" in lz.columns else ("LZONE_NM" if "LZONE_NM" in lz.columns else None)
    lz["life_zone_name"] = lz[name_col].astype(str) if name_col else "LZ_" + lz["life_zone_id"].astype(str)
    if len(lz) != C.N_LZ:
        raise SystemExit(f"공식 생활권 수 {len(lz)} != {C.N_LZ}")
    return lz


def map_dong_to_lz(dong: gpd.GeoDataFrame, lz: gpd.GeoDataFrame) -> pd.DataFrame:
    ov = gpd.overlay(dong[["Dong", "Ku", "ku_name", "ADM_NM", "dong_area_sqm", "geometry"]],
                     lz[["life_zone_id", "life_zone_name", "geometry"]], how="intersection")
    ov["inter_area_sqm"] = ov.geometry.area
    ov["overlap_ratio"] = ov["inter_area_sqm"] / ov["dong_area_sqm"]
    best = (ov.sort_values(["Dong", "inter_area_sqm"], ascending=[True, False])
              .drop_duplicates("Dong", keep="first"))
    m = best[["Dong", "Ku", "ku_name", "ADM_NM", "life_zone_id", "life_zone_name", "overlap_ratio"]].copy()
    m = m.sort_values(["Ku", "Dong"]).reset_index(drop=True)
    if len(m) != C.N_DONG or m["Dong"].duplicated().any():
        raise SystemExit("동→생활권 매핑 행 수 오류")
    per_ku = m.groupby("Ku")["life_zone_id"].nunique().to_dict()
    bad = {k: (v, C.TARGET_COMMUNITIES[k]) for k, v in per_ku.items() if v != C.TARGET_COMMUNITIES[k]}
    if bad:
        raise SystemExit(f"구별 생활권 수가 TARGET_COMMUNITIES와 다름: {bad}")
    low = m[m["overlap_ratio"] < 0.5]
    for _, r in low.iterrows():
        log.warning(f"  교차 비율 50% 미만: {r.Dong} {r.ADM_NM} → {r.life_zone_name} ({r.overlap_ratio:.1%})")
    return m


def main():
    C.ensure_dirs()
    code_tbl = load_dong_code_table()
    log.info(f"코드표 서울 동 {len(code_tbl)}개")
    dong = build_dong(code_tbl)
    lz = build_lz()
    m = map_dong_to_lz(dong, lz)
    dong = dong.merge(m[["Dong", "life_zone_id", "life_zone_name"]], on="Dong", how="left")

    # 저장
    # 같은 이름의 정본은 이 스크립트가 다시 만든다 (이전 판은 data/_archive_* 에 보관)
    C.save_gpkg_layers(C.DONG_GPKG, {"epsg5179": dong, "epsg4326": dong.to_crs(C.CRS_GEOGRAPHIC)})
    C.save_gpkg_layers(C.LZ_GPKG, {"epsg5179": lz, "epsg4326": lz.to_crs(C.CRS_GEOGRAPHIC)})
    m.to_csv(C.DONG_LZ_MAP, index=False, encoding="utf-8-sig", lineterminator="\n")   # LF 고정: 운영체제와 무관하게 같은 해시
    with pd.ExcelWriter(C.DONG_LZ_MAP.with_suffix(".xlsx")) as w:
        m.to_excel(w, sheet_name=f"mapping_{C.N_DONG}", index=False)
        (m.groupby(["Ku", "ku_name"]).agg(n_dongs=("Dong", "count"), n_living_zones=("life_zone_id", "nunique"))
           .reset_index().to_excel(w, sheet_name="ku_summary", index=False))

    # 다중 폴리곤 동(떨어진 조각) 기록 — 정상적으로는 신사동에 개포3동이 붙어 있지 않아야 한다
    ex = dong.explode(index_parts=True)
    ex = ex[ex.area > 10_000]
    parts = ex.groupby(level=0).size()
    multipart = dong.loc[parts[parts > 1].index, ["Dong", "ADM_NM"]].values.tolist()

    report = {
        "env": C.env_info(),
        "n_dong": int(len(dong)), "n_lz": int(len(lz)),
        "dong_total_area_km2": round(float(dong.area.sum() / 1e6), 3),
        "lz_total_area_km2": round(float(lz.area.sum() / 1e6), 3),
        "override_applied": C.ADM_CD_TO_DONG_OVERRIDE,
        "dissolved_dongs": dong[dong["source_adm_cd"].str.contains(r"\+")][["Dong", "source_adm_nm"]].values.tolist(),
        "multipart_dongs_over_1ha": multipart,
        "lz_per_ku": m.groupby("Ku")["life_zone_id"].nunique().to_dict(),
        "min_overlap_ratio": float(m["overlap_ratio"].min()),
        "outputs": {p.name: C.sha256_of(p) for p in (C.DONG_GPKG, C.LZ_GPKG, C.DONG_LZ_MAP)},
    }
    C.OUTPUT_DIR.mkdir(exist_ok=True)
    (C.OUTPUT_DIR / "s01_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    log.info(f"완료: 동 {len(dong)}개, 생활권 {len(lz)}개, 매핑 {len(m)}행 → {C.DATA_DIR}")
    log.info(f"떨어진 조각이 있는 동: {multipart}")


if __name__ == "__main__":
    main()
