# -*- coding: utf-8 -*-
"""독립 검증: s01 산출물(동 424, 공식 생활권 116, 동→생활권 매핑) — s01 코드 미사용"""
import json
import numpy as np, pandas as pd, geopandas as gpd, pyogrio
from pathlib import Path

RAW = Path(r"D:\Research\0_RAW")
CORE = Path(r"D:\Research\00_박사논문_연구체계\00_공통_코어엔진")
D = CORE / "data"
R = {}

TARGET = {11010: 4, 11020: 3, 11030: 4, 11040: 4, 11050: 4, 11060: 4, 11070: 3, 11080: 5, 11090: 4, 11100: 5, 11110: 7, 11120: 5,
          11130: 4, 11140: 5, 11150: 5, 11160: 6, 11170: 4, 11180: 3, 11190: 5, 11200: 5, 11210: 5, 11220: 4, 11230: 6, 11240: 7, 11250: 5}

# 1) 원자료 동 SHP → 독립 dissolve
raw = gpd.read_file(RAW / "BND_ADM_DONG_PG_SHP/BND_ADM_DONG_PG.shp", encoding="cp949")
raw = raw[raw.ADM_CD.astype(str).str.startswith("11")].copy()
R["raw_seoul_polys"] = len(raw)
raw["Dong"] = raw.ADM_CD.astype(str).str[:7].astype(int)
raw.loc[raw.ADM_CD.astype(str) == "11230511", "Dong"] = 1123074
R["raw_dup_codes"] = raw.Dong[raw.Dong.duplicated(keep=False)].astype(str).unique().tolist()
mine = raw.to_crs(5179).dissolve("Dong").reset_index()
R["my_n_dong"] = len(mine)

# 코드표
ct = pd.read_excel(RAW / "2401-2406_SEOUL_MOVING_CSV/서울생활이동데이터_행정동코드_20210907.xlsx")
ct_seoul = set(ct.loc[ct["시도"] == 11000, "읍면동"].astype(int))
R["codetable_seoul"] = len(ct_seoul)
R["mine_eq_codetable"] = set(mine.Dong) == ct_seoul
R["mine_minus_ct"] = sorted(set(mine.Dong) - ct_seoul); R["ct_minus_mine"] = sorted(ct_seoul - set(mine.Dong))

# 정본 동 gpkg 대조
can = gpd.read_file(D / "seoul_dong_424_dissolved.gpkg", layer="epsg5179")
R["canon_dong_cols"] = list(can.columns)
dcol = "Dong" if "Dong" in can.columns else [c for c in can.columns if c.lower().startswith("dong")][0]
can[dcol] = can[dcol].astype(int)
R["canon_n"] = len(can); R["canon_codes_eq"] = set(can[dcol]) == set(mine.Dong)
m = mine.set_index("Dong").geometry; c = can.set_index(dcol).geometry.reindex(m.index)
sd = [m[k].symmetric_difference(c[k]).area / m[k].area for k in m.index]
R["dong_geom_symdiff_max_ratio"] = float(np.max(sd))
R["canon_valid"] = bool(can.is_valid.all()); R["canon_crs"] = str(can.crs)
R["canon_multipart"] = int((can.geometry.geom_type == "MultiPolygon").sum())
g4326 = gpd.read_file(D / "seoul_dong_424_dissolved.gpkg", layer="epsg4326")
R["dong4326_n"] = len(g4326); R["dong4326_crs"] = str(g4326.crs)
R["dong4326_vs_5179_centroid_shift_m_max"] = float(g4326.to_crs(5179).set_index(g4326[dcol].astype(int)).geometry.centroid
                                                  .distance(can.set_index(dcol).geometry.centroid).max())

# 2) 공식 생활권
lzr = gpd.read_file(RAW / "UPIS_SHP_ZON100/seoul_living_zone.shp")
R["lz_raw_n"] = len(lzr); R["lz_raw_crs"] = str(lzr.crs)
lz = lzr.to_crs(5179)
# EPSG:5174 변환이 맞는지: 생활권 합집합 vs 동 합집합(서울 경계) 겹침, 생활권 ↔ 배정 동 합집합 IoU
seoul_dong = mine.union_all(); seoul_lz = lz.union_all()
R["seoul_area_dong_km2"] = seoul_dong.area / 1e6; R["seoul_area_lz_km2"] = seoul_lz.area / 1e6
R["seoul_iou_dong_vs_lz"] = seoul_dong.intersection(seoul_lz).area / seoul_dong.union(seoul_lz).area
# 독립 배정: 교차면적 최대
inter = gpd.overlay(mine[["Dong", "geometry"]], lz.reset_index()[["index", "label_1", "Gu", "geometry"]], how="intersection", keep_geom_type=True)
inter["a"] = inter.area
best = inter.sort_values("a", ascending=False).drop_duplicates("Dong").set_index("Dong")
best["ratio"] = best["a"] / mine.set_index("Dong").area.reindex(best.index)
R["assign_ratio_min"] = float(best.ratio.min()); R["assign_ratio_lt_0.9"] = best.ratio[best.ratio < 0.9].round(3).to_dict()
mp = pd.read_csv(D / "dong_to_official_livingzone_mapping_424.csv", encoding="utf-8-sig")
R["map_rows"] = len(mp); R["map_unique_dong"] = mp.Dong.nunique(); R["map_n_lz"] = mp.life_zone_id.nunique()
mp = mp.set_index("Dong")
# 이름으로 대조 (id 체계가 다를 수 있음)
R["assign_name_agree"] = int((best.label_1.reindex(mp.index) == mp.life_zone_name).sum())
R["assign_name_disagree"] = {int(k): (mp.life_zone_name[k], best.label_1.get(k)) for k in mp.index if best.label_1.get(k) != mp.life_zone_name[k]}
cnt = mp.groupby("Ku").life_zone_id.nunique().to_dict()
R["per_ku_count_ok"] = all(cnt.get(k) == v for k, v in TARGET.items())
# 생활권이 한 구 안에만 있는가, 생활권 이름의 구와 동의 구가 같은가
R["lz_spanning_multiple_ku"] = int((mp.groupby("life_zone_id").Ku.nunique() > 1).sum())
# 생활권 ↔ 배정 동 합집합 IoU (5174 변환 오차 점검)
du = mine.set_index("Dong").join(mp[["life_zone_name"]]).dissolve("life_zone_name")
lzn = lz.set_index("label_1")
ious = {n: du.geometry[n].intersection(lzn.geometry[n]).area / du.geometry[n].union(lzn.geometry[n]).area for n in du.index}
s = pd.Series(ious)
R["lz_vs_donguni_iou_median"] = float(s.median()); R["lz_vs_donguni_iou_min"] = float(s.min())
R["lz_vs_donguni_iou_lt_0.8"] = s[s < 0.8].round(3).to_dict()
# 경계선 평균 이동(수 m 수준이면 좌표계 문제 없음): 생활권 합집합 경계와 동 경계 사이 Hausdorff (서울 외곽선)
R["seoul_outline_hausdorff_m"] = float(seoul_dong.boundary.hausdorff_distance(seoul_lz.boundary))
# 정본 LZ gpkg 대조
lzc = gpd.read_file(D / "seoul_official_livingzone_116.gpkg", layer="epsg5179")
R["lz_gpkg_n"] = len(lzc); R["lz_gpkg_cols"] = list(lzc.columns)

# 3) 통합 gpkg 레이어
for lyr in pyogrio.list_layers(D / "seoul_boundaries_all.gpkg")[:, 0]:
    g = gpd.read_file(D / "seoul_boundaries_all.gpkg", layer=lyr)
    R[f"all_{lyr}"] = dict(n=len(g), crs=str(g.crs), valid=bool(g.is_valid.all()), area_km2=round(g.area.sum() / 1e6 if g.crs and g.crs.is_projected else float("nan"), 3), cols=list(g.columns)[:8])
(Path(__file__).resolve().parents[1] / "output" / "audit_20260925" / "a2_result.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
