# -*- coding: utf-8 -*-
"""손계산 예제: Polsby–Popper·Queen 인접·250m 격자 코드."""
import sys, math
from pathlib import Path
import numpy as np, geopandas as gpd
from shapely.geometry import box, Polygon
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from a03_boundary_metrics import polsby_popper, queen_adjacency
from a02_facility_boundary import grid250_code

def test_polsby_popper_square():
    sq = gpd.GeoSeries([box(0, 0, 1000, 1000)], crs=5179)
    assert abs(polsby_popper(sq).iloc[0] - math.pi / 4) < 1e-9      # 1 km 정사각형 → 0.785

def test_polsby_popper_circle_and_thin():
    from shapely.geometry import Point
    c = gpd.GeoSeries([Point(0, 0).buffer(1000, 4096)], crs=5179)
    assert abs(polsby_popper(c).iloc[0] - 1.0) < 1e-4                 # 원 → 1
    thin = gpd.GeoSeries([box(0, 0, 10000, 100)], crs=5179)
    assert polsby_popper(thin).iloc[0] < 0.05                         # 길쭉 → 0에 가까움

def test_queen_adjacency_2x2_plus_island():
    # 2×2 체스판: 대각선 셀은 점 공유(vertex), 가로세로는 선 공유(edge); 멀리 떨어진 섬 1개
    cells = [box(0, 0, 1, 1), box(1, 0, 2, 1), box(0, 1, 1, 2), box(1, 1, 2, 2), box(10, 10, 11, 11)]
    g = gpd.GeoDataFrame({'Dong': [1, 2, 3, 4, 5]}, geometry=cells, crs=5179)
    pairs, W, islands, deg = queen_adjacency(g)
    assert list(deg[:4]) == [3, 3, 3, 3] and deg[4] == 0 and islands == [5]
    assert (pairs.kind == 'vertex').sum() == 4 and (pairs.kind == 'edge').sum() == 8   # 유향 쌍
    assert (W != W.T).nnz == 0

def test_grid250_code():
    # 원점 셀, 1km 블록 내 250m 순번
    assert grid250_code([900000 + 125], [1900000 + 125])[0] == '다사00aa00aa'
    assert grid250_code([900000 + 56 * 1000 + 2 * 250 + 1], [1900000 + 47 * 1000 + 1 * 250 + 1])[0] == '다사56ba47ab'
    assert grid250_code([935000 + 10], [1936500 + 10])[0] == '다사35aa36ba'


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    fails = 0
    for fn in tests:
        try:
            fn(); print('PASS', fn.__name__)
        except AssertionError as ex:
            fails += 1; print('FAIL', fn.__name__, ex)
    print(f'{len(tests) - fails}/{len(tests)} 통과')
    sys.exit(1 if fails else 0)
