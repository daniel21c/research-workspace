# -*- coding: utf-8 -*-
"""GeoPackage 두 개의 내용 비교 (레이어·행·속성·기하). gpkg 는 파일 안에 작성 시각을 저장해 같은 내용이어도 해시가 다르다.
사용: python a5_compare_gpkg.py <기준.gpkg> <비교.gpkg>
예:   python ..\\scripts\\s04_promote_canonical.py --out-dir %TEMP%\\repro
      python a5_compare_gpkg.py ..\\data\\seoul_boundaries_all.gpkg %TEMP%\\repro\\seoul_boundaries_all.gpkg
"""
import sys
import geopandas as gpd, pyogrio

a, b = sys.argv[1], sys.argv[2]
la, lb = pyogrio.list_layers(a)[:, 0].tolist(), pyogrio.list_layers(b)[:, 0].tolist()
ok = la == lb
print("레이어 목록 같음:", la == lb, la)
for l in la:
    if l not in lb:
        print(f"  {l}: 비교 파일에 없음"); ok = False; continue
    x, y = gpd.read_file(a, layer=l), gpd.read_file(b, layer=l)
    same_rows = len(x) == len(y)
    attr = same_rows and x.drop(columns="geometry").astype(str).equals(y.drop(columns="geometry").astype(str))
    geom = same_rows and max((x.geometry.iloc[i].symmetric_difference(y.geometry.iloc[i]).area for i in range(len(x))), default=0.0) == 0.0
    crs = x.crs == y.crs
    print(f"  {l}: 행 {len(x)}/{len(y)}  속성 같음={attr}  기하 같음={geom}  좌표계 같음={crs}")
    ok &= bool(attr and geom and crs)
print("판정:", "내용 같음" if ok else "다름")
sys.exit(0 if ok else 1)
