# -*- coding: utf-8 -*-
"""S1 자료 개요: 공통 od_daily(2025-01)에서 입력 규모를 집계하고, 공식 116 생활권 구성표(424동 기준)를 만든다.
산출: results/tables/T1_input_overview.csv, results/tables/C1_official_zone_composition.csv, audit/s1_checks.json
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd

PKG = Path(__file__).resolve().parents[1]
INP = PKG / "inputs"
OUT = PKG / "results" / "tables"
OLD_T1 = PKG / "results" / "reused_20260929" / "T1_input_overview.csv"        # 9/29 패키지 결과표 사본(s5_reuse.py 가 해시와 함께 복사)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    od = pd.read_parquet(INP / "od_daily_202501.parquet")
    dong = gpd.read_file(INP / "seoul_dong_424_dissolved.gpkg", layer="epsg5179")[["Dong", "Ku", "ku_name", "ADM_NM", "life_zone_id", "life_zone_name"]]
    dong["Dong"] = dong["Dong"].astype(int); dong["Ku"] = dong["Ku"].astype(int)
    ku_of = dong.set_index("Dong")["Ku"]

    same_dong = od["dong_O"] == od["dong_D"]
    same_ku = od["dong_O"].map(ku_of) == od["dong_D"].map(ku_of)
    total_flow = float(od["flow"].sum())
    rows = int(od["n_rows"].sum()); masked = int(od["n_masked"].sum())
    t1 = pd.DataFrame([{
        "year": 2025, "month": 1, "n_dong": int(dong["Dong"].nunique()), "n_district": int(dong["Ku"].nunique()),
        "n_official_zones": int(dong["life_zone_id"].nunique()),
        "od_pairs": int(len(od)), "selected_rows": rows, "masked_rows": masked, "masked_share_rows": masked / rows,
        "total_flow": total_flow,
        "within_dong_flow": float(od.loc[same_dong, "flow"].sum()), "within_dong_share_flow": float(od.loc[same_dong, "flow"].sum() / total_flow),
        "within_district_flow": float(od.loc[same_ku, "flow"].sum()), "within_district_share_flow": float(od.loc[same_ku, "flow"].sum() / total_flow),
        "within_district_rows": int(od.loc[same_ku, "n_rows"].sum()), "within_district_share_rows": float(od.loc[same_ku, "n_rows"].sum() / rows),
    }])
    t1.to_csv(OUT / "T1_input_overview.csv", index=False, encoding="utf-8-sig", float_format="%.12g")

    comp = (dong.groupby(["Ku", "ku_name", "life_zone_id", "life_zone_name"]).agg(n_dong=("Dong", "size")).reset_index()
            .sort_values(["Ku", "life_zone_id"]))
    comp["n_dong_in_district"] = comp.groupby("Ku")["n_dong"].transform("sum")
    comp["n_zones_in_district"] = comp.groupby("Ku")["life_zone_id"].transform("nunique")
    comp.to_csv(OUT / "C1_official_zone_composition.csv", index=False, encoding="utf-8-sig")

    checks = {
        "n_dong_424": bool(dong["Dong"].nunique() == 424 and len(dong) == 424),
        "n_district_25": bool(dong["Ku"].nunique() == 25),
        "n_zones_116": bool(comp["life_zone_id"].nunique() == 116 and len(comp) == 116),
        "composition_sums_to_424": bool(comp["n_dong"].sum() == 424),
        "every_od_dong_in_boundary": bool(set(od["dong_O"]).issubset(ku_of.index) and set(od["dong_D"]).issubset(ku_of.index)),
        "no_negative_flow": bool((od["flow"] >= 0).all()),
    }
    if OLD_T1.exists():
        old = pd.read_csv(OLD_T1)
        r = old[old["year"] == 2025].iloc[0]
        checks["same_as_20260929_T1_2025"] = bool(
            int(r["selected_rows"]) == rows and int(r["masked_rows"]) == masked and abs(r["total_flow"] - total_flow) < 0.01
            and abs(r["within_dong_flow"] - t1.loc[0, "within_dong_flow"]) < 0.01 and abs(r["within_district_flow"] - t1.loc[0, "within_district_flow"]) < 0.01)
    (PKG / "audit" / "s1_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False))
    print(t1.T.to_string())
    assert all(checks.values()), checks


if __name__ == "__main__":
    main()
