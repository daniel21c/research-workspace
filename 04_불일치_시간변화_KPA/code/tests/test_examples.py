# -*- coding: utf-8 -*-
"""
연구설계.md 7.1의 손계산 예제 A~D를 코드 테스트로 옮긴 것.
실행:  python -m pytest tests -q   또는   python tests/test_examples.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kpa_metrics as km  # noqa: E402


def _example_a():
    # 구 K = 동 1~4, X = 구 밖 서울 동 9 (분모에는 들어가고 분자에는 안 들어간다)
    rows = [
        (1, 1, 10), (1, 2, 20), (1, 3, 5), (1, 4, 0), (1, 9, 15),
        (2, 1, 10), (2, 2, 10), (2, 3, 0), (2, 4, 10), (2, 9, 10),
        (3, 1, 5), (3, 2, 0), (3, 3, 10), (3, 4, 15), (3, 9, 10),
        (4, 1, 0), (4, 2, 5), (4, 3, 20), (4, 4, 10), (4, 9, 15),
    ]
    od = pd.DataFrame(rows, columns=["dong_O", "dong_D", "flow"])
    lz = pd.Series({1: "Z1", 2: "Z1", 3: "Z2", 4: "Z2", 9: "Z9"})
    ld = pd.Series({1: "C1", 2: "C1", 3: "C1", 4: "C2", 9: "C9"})
    ku = pd.Series({1: 11, 2: 11, 3: 11, 4: 11, 9: 99})
    return od, lz, ld, ku


def test_example_a_values():
    od, lz, ld, ku = _example_a()
    g = km.metrics_by_gu(km.tag_flows(od, lz, ld, ku)).loc[11]
    assert g["T"] == 180
    assert g["N_lz"] == 105 and g["N_ld"] == 80
    assert g["a"] == 10 and g["b"] == 35
    assert np.isclose(g["IFR_lz"], 105 / 180) and np.isclose(g["IFR_ld"], 80 / 180)
    assert np.isclose(g["G"], -25 / 180) and np.isclose(g["D"], 45 / 180)
    assert abs(g["G"]) <= g["D"]
    km.check_identities(g.to_frame().T)


def test_example_a_wrong_denominator_breaks_identity():
    # LD 분모를 구 안 도착만(130)으로 잘못 잡으면 IFR 차이가 (a-b)/T 와 맞지 않는다
    od, lz, ld, ku = _example_a()
    inside = od[od["dong_D"] != 9]["flow"].sum()
    assert inside == 130
    wrong_gap = 80 / 130 - 105 / 180
    assert not np.isclose(wrong_gap, -25 / 180)
    assert wrong_gap > 0  # 부호까지 뒤집힌다


def test_example_b_signed_gap_trap():
    T = 200
    def gd(a, b):
        return (a - b) / T, (a + b) / T
    G0, D0 = gd(5, 11)
    G1a, D1a = gd(9, 11)   # B1
    G1b, D1b = gd(3, 5)    # B2
    assert np.isclose(G1a - G0, 0.02) and np.isclose(G1b - G0, 0.02)   # Δgap 같음
    assert D1a - D0 > 0 and D1b - D0 < 0                                # 크기는 반대


def test_example_c_decomposition_identity():
    idx = pd.Index(["K"])
    x00, x01, x11, x10 = (pd.Series([v], index=idx) for v in (0.10, 0.13, 0.12, 0.09))
    d = km.decompose(x00, x01, x11, x10)
    assert np.isclose(d["total"].iloc[0], 0.02)
    assert np.isclose(d["flow_effect_o1"].iloc[0], 0.03)
    assert np.isclose(d["boundary_effect_o1"].iloc[0], -0.01)
    assert np.isclose(d["boundary_effect_o2"].iloc[0], -0.01)
    assert np.isclose(d["flow_effect_o2"].iloc[0], 0.03)


def test_example_d_aggregation_is_ratio_of_sums():
    g = pd.DataFrame({"T": [180, 820], "a": [10, 30], "b": [35, 10],
                      "N_lz": [105, 400], "N_ld": [80, 420], "both": [70, 390], "self_flow": [40, 200]},
                     index=[11, 12])
    g = km.derive(g)
    tot = km.metrics_total(g)
    assert np.isclose(tot["G"], (-25 + 20) / 1000)
    assert np.isclose(tot["D"], (45 + 40) / 1000)
    assert not np.isclose(tot["G"], g["G"].mean())   # 단순평균과 다르다


def test_ari_basic():
    a = pd.Series([0, 0, 1, 1, 2, 2])
    b = pd.Series([5, 5, 7, 7, 9, 9])
    assert np.isclose(km.adjusted_rand_index(a, b), 1.0)
    c = pd.Series([0, 1, 0, 1, 0, 1])
    assert km.adjusted_rand_index(a, c) < 0.2


def test_random_partition_is_contiguous_and_has_k_labels():
    # 2×3 격자
    nodes = [0, 1, 2, 3, 4, 5]
    adj = {0: {1, 3}, 1: {0, 2, 4}, 2: {1, 5}, 3: {0, 4}, 4: {1, 3, 5}, 5: {2, 4}}
    rng = np.random.default_rng(1)
    for _ in range(50):
        lab = km.random_contiguous_partition(adj, nodes, 2, rng)
        assert set(lab) == {0, 1}
        for l in (0, 1):
            members = [nodes[i] for i in range(6) if lab[i] == l]
            seen, stack = {members[0]}, [members[0]]
            while stack:
                v = stack.pop()
                for w in adj[v]:
                    if w in members and w not in seen:
                        seen.add(w); stack.append(w)
            assert seen == set(members)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
