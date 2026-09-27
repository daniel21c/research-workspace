# -*- coding: utf-8 -*-
"""k13·k14 함수 단위시험 — 손계산 예제와 독립 구현(networkx)으로 확인. 실행: python tests/test_benchmark.py"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import networkx as nx
from networkx.algorithms.community import modularity as nx_modularity
from k13_benchmark import grow, grow_free, random_zone, ifr_gu, capture, pct
from k14_reassign import connected, ifr, modularity, dmis

# 연구설계 7.1 예제 A: 구 안 동 1~4, 구 밖 도착 X 포함 출발 합 T
W = np.array([[10, 20, 5, 0], [10, 10, 0, 10], [5, 0, 10, 15], [0, 5, 20, 10]], float)
T = np.array([50, 40, 40, 50], float)
LZ = np.array([0, 0, 1, 1]); LD = np.array([0, 0, 0, 1])
# 3×4 격자 인접(12개 동)
GRID = {i: set() for i in range(12)}
for r in range(3):
    for c in range(4):
        i = r * 4 + c
        if c < 3: GRID[i].add(i + 1); GRID[i + 1].add(i)
        if r < 2: GRID[i].add(i + 4); GRID[i + 4].add(i)
NODES = list(range(12))


def is_contiguous(lab, adj=GRID, nodes=NODES):
    idx = [[j for j in adj[v]] for v in nodes]
    return all(connected(list(np.where(lab == z)[0]), idx) for z in set(lab))


def test_ifr_example_a():
    assert abs(ifr_gu(W, T, LZ) - 105 / 180) < 1e-12 and abs(ifr_gu(W, T, LD) - 80 / 180) < 1e-12
    assert abs(ifr(W, T.sum(), LZ) - 105 / 180) < 1e-12


def test_dmis_example_a():
    assert abs(dmis(W, T.sum(), LZ, LD) - 45 / 180) < 1e-12        # a=10, b=35


def test_capture_example_a():
    c = capture(W, T, LZ)
    assert np.allclose(c, [30 / 50, 20 / 40, 25 / 40, 30 / 50])


def test_modularity_matches_networkx():
    A = W + W.T
    G = nx.Graph()
    for i in range(4):
        for j in range(i, 4):
            if A[i, j] > 0: G.add_edge(i, j, weight=A[i, j] / (2 if i == j else 1))
    for lab in (LZ, LD):
        comms = [set(np.where(lab == z)[0]) for z in set(lab)]
        assert abs(modularity(A, lab) - nx_modularity(G, comms, weight="weight")) < 1e-12


def test_move_delta_identity():
    """동 i를 권역 a→b로 옮길 때 내부 통행 변화 = (i↔b 양방향) − (i↔a\\{i} 양방향). 재계산과 같아야 한다."""
    lab = LZ.copy(); i, b = 2, 0
    new = lab.copy(); new[i] = b
    A_rest = [j for j in np.where(lab == lab[i])[0] if j != i]; B_mem = np.where(lab == b)[0]
    analytic = (W[i, B_mem].sum() + W[B_mem, i].sum() - W[i, A_rest].sum() - W[A_rest, i].sum()) / T.sum()
    assert abs((ifr(W, T.sum(), new) - ifr(W, T.sum(), lab)) - analytic) < 1e-12


def test_grow_exact_sizes_contiguous():
    rng = np.random.default_rng(1)
    for sizes in ([4, 4, 4], [5, 4, 3], [6, 3, 2, 1]):
        for _ in range(50):
            lab = grow(NODES, GRID, np.array(sizes), rng)
            assert lab is not None and sorted(np.bincount(lab)) == sorted(sizes) and is_contiguous(lab)


def test_grow_free_k_labels_contiguous():
    rng = np.random.default_rng(2)
    for _ in range(100):
        lab = grow_free(NODES, GRID, 3, rng)
        assert len(set(lab)) == 3 and (lab >= 0).all() and is_contiguous(lab)


def test_random_zone_connected_size():
    rng = np.random.default_rng(3)
    idx = [[j for j in GRID[v]] for v in NODES]
    for s in (1, 3, 5, 8):
        for _ in range(50):
            z = random_zone(NODES, GRID, s, rng)
            assert len(z) == s and connected(list(z), idx)


def test_pct_definition():
    assert pct(5, [1, 2, 3, 4]) == 1.0 and pct(0, [1, 2]) == 0.0 and pct(2, [1, 2, 3]) == 0.5


def test_determinism():
    a = [grow(NODES, GRID, np.array([5, 4, 3]), np.random.default_rng(7)) for _ in range(3)]
    b = [grow(NODES, GRID, np.array([5, 4, 3]), np.random.default_rng(7)) for _ in range(3)]
    assert all((x == y).all() for x, y in zip(a, b))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); print("ok", k); n += 1
    print(f"{n}/{n} 통과")
