# -*- coding: utf-8 -*-
"""
연구4 지표 함수 모음 (연구설계.md 5절의 식을 그대로 코드로 옮긴 것)

기호
  f_od : 동 o에서 동 d로 가는 필터 통행량 (od_daily)
  T_K  : 출발이 구 K인 서울 내 모든 통행량 합 (두 경계 공통 분모)          … 5.1
  N^B_K: 출발이 구 K이고, 경계 B에서 출발·도착이 같은 권역인 통행량 합      … 5.2
  a_K  : LD에서만 내부인 통행량,  b_K : LZ에서만 내부인 통행량              … 5.3
  G_K  = (a-b)/T = IFR^LD - IFR^LZ  (격차의 방향)                          … 5.4
  D_K  = (a+b)/T                    (격차의 크기, 상쇄 전 총 판정차)        … 5.5
상위 단위는 언제나 분자합/분모합이다. 비율의 평균을 쓰지 않는다.

이 모듈은 파일 경로를 모른다. 입력은 모두 DataFrame/Series로 받는다.
그래야 7.1의 손계산 예제를 그대로 테스트로 넣을 수 있다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ------------------------------------------------------------------------------
# 1. 핵심: 통행 하나하나에 두 경계의 내부/외부 판정을 붙여서 a, b, T를 만든다
# ------------------------------------------------------------------------------

def tag_flows(od: pd.DataFrame, lz: pd.Series, ld: pd.Series, ku: pd.Series) -> pd.DataFrame:
    """
    od : columns dong_O, dong_D, flow
    lz : index=동코드, value=공식 생활권 id (서울 전체에서 유일)
    ld : index=동코드, value=이동 기반 경계 id (서울 전체에서 유일)
    ku : index=동코드, value=구 코드
    반환: od에 ku_O, in_lz, in_ld, self 열을 붙인 표.
    모든 동이 세 매핑에 다 있어야 한다. 하나라도 빠지면 통행이 조용히 사라지므로 멈춘다.
    """
    dongs = pd.Index(sorted(set(od["dong_O"]) | set(od["dong_D"])))
    for name, m in (("lz", lz), ("ld", ld), ("ku", ku)):
        missing = dongs.difference(m.index)
        if len(missing):
            raise ValueError(f"{name} 매핑에 없는 동 {len(missing)}개: {list(missing)[:5]} …")
    t = od[["dong_O", "dong_D", "flow"]].copy()
    t["ku_O"] = t["dong_O"].map(ku).astype(int)
    t["lz_O"] = t["dong_O"].map(lz)
    t["in_lz"] = (t["lz_O"].values == t["dong_D"].map(lz).values)
    t["in_ld"] = (t["dong_O"].map(ld).values == t["dong_D"].map(ld).values)
    t["self"] = t["dong_O"].values == t["dong_D"].values
    return t


def _sum_by(t: pd.DataFrame, key: str) -> pd.DataFrame:
    f = t["flow"]
    g = pd.DataFrame({
        key: t[key],
        "T": f,
        "N_lz": f * t["in_lz"],
        "N_ld": f * t["in_ld"],
        "both": f * (t["in_lz"] & t["in_ld"]),
        "a": f * (t["in_ld"] & ~t["in_lz"]),      # LD만 내부
        "b": f * (t["in_lz"] & ~t["in_ld"]),      # LZ만 내부
        "self_flow": f * t["self"],
    }).groupby(key).sum()
    return g


def derive(g: pd.DataFrame) -> pd.DataFrame:
    """a, b, T, N에서 비율 지표를 만든다. 분자합/분모합이므로 어느 단위에서든 같은 함수."""
    out = g.copy()
    out["IFR_lz"] = out["N_lz"] / out["T"]
    out["IFR_ld"] = out["N_ld"] / out["T"]
    out["G"] = (out["a"] - out["b"]) / out["T"]
    out["D"] = (out["a"] + out["b"]) / out["T"]
    out["SR"] = out["self_flow"] / out["T"]        # 동 내부통행 비율 (H4)
    return out


def metrics_by_gu(t: pd.DataFrame) -> pd.DataFrame:
    return derive(_sum_by(t, "ku_O"))


def metrics_by_lz(t: pd.DataFrame) -> pd.DataFrame:
    """출발 동의 공식 생활권 기준 116 보조표 (연구설계 5.6)."""
    return derive(_sum_by(t, "lz_O"))


def metrics_total(g: pd.DataFrame) -> pd.Series:
    """구(또는 생활권) 표를 서울 전체로 합친다. 분자합/분모합."""
    cols = ["T", "N_lz", "N_ld", "both", "a", "b", "self_flow"]
    return derive(g[cols].sum().to_frame().T).iloc[0]


# ------------------------------------------------------------------------------
# 2. 점검 (연구설계 7.3 T2~T4)
# ------------------------------------------------------------------------------

def check_identities(g: pd.DataFrame, tol: float = 1e-6) -> None:
    """N_ld - N_lz == a - b,  |G| <= D,  a+b+both+neither == T (neither는 계산 안 하지만 a+b+both<=T)."""
    lhs = g["N_ld"] - g["N_lz"]
    rhs = g["a"] - g["b"]
    if not np.allclose(lhs, rhs, rtol=0, atol=tol * g["T"].max()):
        raise AssertionError("항등식 N_ld - N_lz = a - b 가 깨졌다. 두 경계의 분모가 다르거나 매핑 오류.")
    if (g["G"].abs() > g["D"] + tol).any():
        raise AssertionError("|G| <= D 가 깨졌다.")
    if ((g["a"] + g["b"] + g["both"]) > g["T"] * (1 + tol)).any():
        raise AssertionError("a + b + both 가 T 를 넘는다.")


def check_aggregation(gu: pd.DataFrame, lz: pd.DataFrame, tol: float = 1e-9) -> None:
    """구 합산 == 생활권 합산 (T4). 생활권은 구를 넘지 않으므로 두 합계가 같아야 한다."""
    for c in ("T", "a", "b", "N_lz", "N_ld"):
        if not np.isclose(gu[c].sum(), lz[c].sum(), rtol=tol):
            raise AssertionError(f"구 합산과 생활권 합산이 다르다: {c}")


# ------------------------------------------------------------------------------
# 3. 변화와 분해 (연구설계 4.4 ⑤, 7.1 예제 C)
# ------------------------------------------------------------------------------

def decompose(x00: pd.Series, x01: pd.Series, x11: pd.Series, x10: pd.Series) -> pd.DataFrame:
    """
    x_su = X(경계 LD_s, 통행 OD_u).  s,u ∈ {0: 2020, 1: 2025}
    순서1: 통행 효과 = x01 - x00, 경계 재도출 효과 = x11 - x01
    순서2: 경계 재도출 효과 = x10 - x00, 통행 효과 = x11 - x10
    두 순서의 합은 모두 x11 - x00 이어야 한다(항등식).
    """
    out = pd.DataFrame({
        "total": x11 - x00,
        "flow_effect_o1": x01 - x00,
        "boundary_effect_o1": x11 - x01,
        "boundary_effect_o2": x10 - x00,
        "flow_effect_o2": x11 - x10,
    })
    out["flow_effect_mean"] = (out["flow_effect_o1"] + out["flow_effect_o2"]) / 2
    out["boundary_effect_mean"] = (out["boundary_effect_o1"] + out["boundary_effect_o2"]) / 2
    s1 = out["flow_effect_o1"] + out["boundary_effect_o1"]
    s2 = out["flow_effect_o2"] + out["boundary_effect_o2"]
    if not (np.allclose(s1, out["total"]) and np.allclose(s2, out["total"])):
        raise AssertionError("분해 항등식이 깨졌다.")
    return out


# ------------------------------------------------------------------------------
# 4. 분할 비교: ARI (라벨 번호와 무관)
# ------------------------------------------------------------------------------

def adjusted_rand_index(a: pd.Series, b: pd.Series) -> float:
    a, b = a.align(b, join="inner")
    ct = pd.crosstab(a.values, b.values).values.astype(float)
    n = ct.sum()
    comb = lambda x: x * (x - 1) / 2.0
    sum_ij = comb(ct).sum()
    sum_a = comb(ct.sum(axis=1)).sum()
    sum_b = comb(ct.sum(axis=0)).sum()
    expected = sum_a * sum_b / comb(n) if n > 1 else 0.0
    max_idx = (sum_a + sum_b) / 2.0
    if np.isclose(max_idx, expected):
        return 1.0
    return float((sum_ij - expected) / (max_idx - expected))


# ------------------------------------------------------------------------------
# 5. 귀무 분할: 같은 구·같은 개수·인접 제약 무작위 분할 (H4)
# ------------------------------------------------------------------------------

def random_contiguous_partition(adj: dict, nodes: list, k: int, rng: np.random.Generator) -> np.ndarray:
    """
    nodes: 구 안 동 인덱스 리스트, adj: {i: set(j)} 인접.
    k개의 씨앗 동을 뽑고, 무작위 순서로 인접한 미배정 동을 하나씩 붙여 나간다(region growing).
    각 권역이 씨앗에서 인접으로만 자라므로 공간적으로 연속이다.
    구 그래프가 연결되어 있지 않으면 남는 동을 가장 가까운(임의) 권역에 붙이고 표시한다.
    """
    n = len(nodes)
    idx = {v: i for i, v in enumerate(nodes)}
    label = -np.ones(n, dtype=int)
    seeds = rng.choice(n, size=k, replace=False)
    label[seeds] = np.arange(k)
    frontier = [(int(s), int(l)) for s, l in zip(seeds, np.arange(k))]
    while (label < 0).any() and frontier:
        pos = rng.integers(len(frontier))
        node, lab = frontier.pop(pos)
        nbrs = [idx[j] for j in adj.get(nodes[node], ()) if j in idx and label[idx[j]] < 0]
        if not nbrs:
            continue
        j = nbrs[rng.integers(len(nbrs))]
        label[j] = lab
        frontier.append((j, lab))
        frontier.append((node, lab))  # 이 노드는 다른 이웃이 더 있을 수 있으니 다시 넣는다
    if (label < 0).any():            # 연결되지 않은 조각: 임의 권역에 붙인다
        label[label < 0] = rng.integers(k, size=(label < 0).sum())
    return label


def ifr_of_labels(W: np.ndarray, T: float, labels: np.ndarray) -> float:
    """W: 구 안 동×동 통행 행렬(출발 구 안, 도착 구 안), T: 출발 구 안 → 서울 전체 합. 같은 라벨 쌍 합/T."""
    k = labels.max() + 1
    M = np.eye(k)[labels]                 # n×k one-hot
    internal = np.trace(M.T @ W @ M)
    return float(internal / T)
