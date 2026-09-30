# -*- coding: utf-8 -*-
"""부가 층 v1.5 후보 구축 (2026-10-01, 연구1 요청). 엔진 입력(facility-v1.4)은 건드리지 않는다.
층:
  공공체육  — 시설 패키지 `구축코드/11_신뢰도_승격/공공체육시설/좌표보완_v2/facilities_공공체육시설_{2020_01,2025_01}.parquet`
             (문체부 전국 공공체육시설 현황 2019-12-31·2024-12-31), scope_flag == 핵심종목, 서울 안 좌표. 신뢰도 "중".
             coord_valid_v2 == True 인 행만 쓰는 엄격 변형 플래그 포함.
  지역아동센터 — 서울 열린데이터광장 OA-20967(우리동네키움포털, 2026-09-03 갱신 CSV). 개소일 필드가 없어(등록일시는 2020년 일괄 등록)
             **두 시점 공통 고정 층**으로 쓴다. 좌표 결측 3곳·'테스트' 1곳 제외.
  공원     — 주: 서울시 생활권계획 시설(공원) 공간정보 OA-15529(UPIS_SHP_ZON216, 2018 기준; 2030 서울생활권계획 생활서비스시설 분석 층)를
             **두 시점 공통 고정 층**으로. 보조: 도시계획시설(공간시설) OA-21129 2024-11-07 스냅샷의 공원(LCLAS_CL == UQT200, 결정 기준)을 2025 민감도로.
             면 시설: 경계 다각형과 겹치는 100 m 격자를 모두 도달점으로 둔다(출입구 자료 없음).
출력: `부가층_{층}_{2020_01|2025_01}.parquet` (열: layer, year_snapshot, facility_id, name, subtype, grid100_cd, x_5179, y_5179, strict, source),
      README.md, manifest_sha256.csv"""
from pathlib import Path
import hashlib, zipfile, io
import numpy as np, pandas as pd, geopandas as gpd
from shapely.geometry import box
from scipy.spatial import cKDTree
from pyproj import Transformer

HERE = Path(__file__).parent; RAW = HERE / "원자료"; PKG = HERE.parent
HUB = HERE.resolve().parents[2]  # 부가층 → 시설데이터_패키지 → 시설데이터 구축 → 허브
GRID = HUB / "06_접근성분석" / "접근성분석_패키지" / "데이터" / "입력" / "grid" / "grid100_master.parquet"
M = pd.read_parquet(GRID, columns=["grid_cd", "x_c", "y_c"]); tree = cKDTree(M[["x_c", "y_c"]].to_numpy())
T4326 = Transformer.from_crs(4326, 5179, always_xy=True)

def to_grid(x, y):
    d, i = tree.query(np.c_[x, y]); g = M.grid_cd.to_numpy()[i].astype(object); g[d > 71] = None; return g   # 100 m 격자 반대각선 이내

rows = []
# ── 공공체육 ─────────────────────────────────────────
for ys in ("2020_01", "2025_01"):
    d = pd.read_parquet(PKG / f"구축코드/11_신뢰도_승격/공공체육시설/좌표보완_v2/facilities_공공체육시설_{ys}.parquet")
    d = d[(d.scope_flag == "핵심종목") & (d.inside_seoul == True) & d.x_5179.notna()]
    g = to_grid(d.x_5179.to_numpy(), d.y_5179.to_numpy())
    rows.append(pd.DataFrame({"layer": "공공체육", "year_snapshot": ys, "facility_id": d.facility_id.to_numpy(), "name": d.name.to_numpy(),
                              "subtype": d.facility_subtype.to_numpy(), "grid100_cd": g, "x_5179": d.x_5179.to_numpy(), "y_5179": d.y_5179.to_numpy(),
                              "strict": d.coord_valid_v2.fillna(False).to_numpy(), "source": "문체부 전국 공공체육시설 현황(시설 패키지 좌표보완_v2), 신뢰도 중"}))
# ── 지역아동센터 ─────────────────────────────────────
c = pd.read_csv(RAW / "child_seoul.csv", encoding="cp949"); c = c[~c.시설명.str.contains("테스트", na=False) & c.X좌표값.notna()]
x, y = T4326.transform(c.X좌표값.to_numpy(), c.Y좌표값.to_numpy()); g = to_grid(x, y)
for ys in ("2020_01", "2025_01"):
    rows.append(pd.DataFrame({"layer": "지역아동센터", "year_snapshot": ys, "facility_id": c.시설ID.to_numpy(), "name": c.시설명.to_numpy(), "subtype": c.연령구분.to_numpy(),
                              "grid100_cd": g, "x_5179": x, "y_5179": y, "strict": True, "source": "서울 열린데이터광장 OA-20967(2026-09 갱신), 두 시점 공통 고정"}))
# ── 공원 ─────────────────────────────────────────────
cells = gpd.GeoDataFrame(M[["grid_cd"]], geometry=[box(a - 50, b - 50, a + 50, b + 50) for a, b in zip(M.x_c, M.y_c)], crs=5179)
def park_cells(gdf, idcol, namecol, subcol, label, ys, src):
    gdf = gdf.to_crs(5179); gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy(); gdf["pid"] = gdf[idcol].astype(str)
    j = gpd.sjoin(cells, gdf[["pid", namecol, subcol, "geometry"]], predicate="intersects", how="inner")
    cen = M.set_index("grid_cd").loc[j.grid_cd]
    return pd.DataFrame({"layer": label, "year_snapshot": ys, "facility_id": j.pid.to_numpy(), "name": j[namecol].to_numpy(), "subtype": j[subcol].to_numpy(),
                         "grid100_cd": j.grid_cd.to_numpy(), "x_5179": cen.x_c.to_numpy(), "y_5179": cen.y_c.to_numpy(), "strict": True, "source": src})
with zipfile.ZipFile(RAW / "park_lz_2018.zip") as z: z.extractall(HERE / "_tmp_park18")
p18 = gpd.read_file(HERE / "_tmp_park18/UPIS_SHP_ZON216.shp", encoding="cp949")
p18["kind"] = p18.LABEL.str.extract(r"(어린이공원|근린공원|소공원|문화공원|역사공원|수변공원|체육공원|묘지공원|도시자연공원|강변공원|도시농업공원|방재공원)")[0].fillna("기타")
for ys in ("2020_01", "2025_01"):
    rows.append(park_cells(p18, "ID", "LABEL", "kind", "공원", ys, "서울시 생활권계획 시설(공원) OA-15529, 2018 기준, 두 시점 공통 고정; 면 시설 = 겹치는 격자 전부"))
with zipfile.ZipFile(RAW / "upis_space_20241107.zip") as z: z.extractall(HERE / "_tmp_upis24")
u = gpd.read_file(next((HERE / "_tmp_upis24").rglob("UPIS_C_UQ153.shp")), encoding="cp949"); u = u[u.LCLAS_CL == "UQT200"]
rows.append(park_cells(u, "PRESENT_SN", "DGM_NM", "MLSFC_CL", "공원_UPIS2024", "2025_01", "도시계획시설(공간시설) OA-21129 2024-11-07, 공원 결정 기준, 2025 민감도"))
D = pd.concat(rows, ignore_index=True)
summary = []
for (lay, ys), d in D.groupby(["layer", "year_snapshot"]):
    fn = HERE / f"부가층_{lay}_{ys}.parquet"; d.reset_index(drop=True).to_parquet(fn, index=False)
    summary.append({"layer": lay, "year": ys, "rows": len(d), "facilities": d.facility_id.nunique(), "grid_cells": d.grid100_cd.nunique(), "no_grid": int(d.grid100_cd.isna().sum()), "strict": int(d.strict.sum())})
S = pd.DataFrame(summary); S.to_csv(HERE / "요약.csv", index=False, encoding="utf-8-sig"); print(S.to_string(index=False))
import shutil; shutil.rmtree(HERE / "_tmp_park18", ignore_errors=True); shutil.rmtree(HERE / "_tmp_upis24", ignore_errors=True)
man = [{"file": str(p.relative_to(HERE)).replace("\\", "/"), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(HERE.rglob("*")) if p.is_file() and p.name != "manifest_sha256.csv"]
pd.DataFrame(man).to_csv(HERE / "manifest_sha256.csv", index=False, encoding="utf-8-sig"); print("manifest", len(man))
