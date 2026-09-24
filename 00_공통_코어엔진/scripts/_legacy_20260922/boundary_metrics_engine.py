"""
boundary_metrics_engine.py — 경계 지표 통합 산출 엔진
======================================================
박사논문 공통 모듈. 모든 논문 스크립트에서 import해서 사용.

기존 검증된 코드 방식 그대로 구현:
  - IFR   : 251022_Leiden_25_scan_병렬_중복해결.py  L1564 calculate_internal_flows_for_one_ku
  - Modula: community_louvain.modularity (python-louvain)
  - IoU   : 기존CUPUM자료/2. iou_district_250106.py (구별 1:1 매칭, Σintersection/Σunion)

────────────────────────────────────────────────────────────
IFR 정의 (방향성 통행, JTG 게재본 Eq.2a/2b)
  분자: O∈c  AND  D∈c  (커뮤니티 c 내부 완결 통행)
  분모: O∈c            (서울 시내 전체 출발 통행, 외부 유출 포함)
  → directed flow. 커뮤니티 구획 단계 그래프는 별도로 무방향 대칭화.

Modularity 정의 (python-louvain 라이브러리 방식)
  networkx 그래프 G에 weight='weight' 엣지 사용.
  무방향 대칭화: wij = w_ij + w_ji (원본 방향 통행 합산 후 undirected 그래프)

IoU 정의 (구별 면적합 방식)
  공식 생활권 vs 커뮤니티 → 구별로 1:1 최대 IoU 매칭
  구 IoU = Σ(intersection_area) / Σ(union_area)
  서울 전체 IoU = 전 구 Σintersection / Σunion
────────────────────────────────────────────────────────────

Usage 예시:
    from boundary_metrics_engine import (
        dissolve_to_boundary,
        calculate_ifr,
        calculate_modularity,
        calculate_iou,
        evaluate_boundary_all_metrics,
    )
"""

from __future__ import annotations

import logging
import warnings
from typing import Optional

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from shapely.ops import unary_union

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# 1. dissolve_to_boundary
# ──────────────────────────────────────────────────────────────────────────────

def dissolve_to_boundary(
    dong_gdf: gpd.GeoDataFrame,
    mapping_df: pd.DataFrame,
    dong_col: str = "Dong",
    community_col: str = "community",
    ku_col: Optional[str] = "ku_code",
) -> gpd.GeoDataFrame:
    """
    동 폴리곤 GeoDataFrame + 매핑 테이블 → 커뮤니티별 경계 GeoDataFrame 생성.

    Parameters
    ----------
    dong_gdf      : 행정동 GeoDataFrame. 'Dong' 컬럼에 dong_code(int) 보유.
    mapping_df    : 동-커뮤니티 매핑 DataFrame. 최소 [dong_col, community_col] 필요.
    dong_col      : dong_gdf와 mapping_df에서 동 코드 컬럼명 (기본: 'Dong')
    community_col : 커뮤니티 ID 컬럼명 (기본: 'community')
    ku_col        : 구 코드 컬럼명. None이면 구 분리 없이 전체 dissolve.

    Returns
    -------
    GeoDataFrame  : [community_col, (ku_col), geometry]
                    geometry는 dissolve된 커뮤니티 폴리곤.
    """
    if dong_gdf is None or dong_gdf.empty:
        raise ValueError("dong_gdf가 비어있습니다.")
    if mapping_df is None or mapping_df.empty:
        raise ValueError("mapping_df가 비어있습니다.")

    # dong_gdf에 community 매핑
    map_dict = dict(
        zip(
            mapping_df[dong_col].astype(int),
            mapping_df[community_col].astype(int),
        )
    )
    merged = dong_gdf.copy()
    merged[community_col] = merged[dong_col].astype(int).map(map_dict)

    # 매핑 안 된 동 제거
    n_missing = merged[community_col].isna().sum()
    if n_missing > 0:
        logger.warning(f"{n_missing}개 동이 커뮤니티 매핑에서 누락됨 → 제거")
    merged = merged.dropna(subset=[community_col])
    merged[community_col] = merged[community_col].astype(int)

    # dissolve
    dissolve_by = [community_col]
    if ku_col and ku_col in merged.columns:
        dissolve_by = [ku_col, community_col]

    # mapping_df의 부가 정보(이름 등) 컬럼 병합
    extra_cols = [c for c in mapping_df.columns if c not in merged.columns and c != dong_col]
    if extra_cols:
        meta_sub = mapping_df[[dong_col] + extra_cols].drop_duplicates(subset=[dong_col])
        merged = merged.merge(meta_sub, on=dong_col, how='left')

    boundary_gdf = (
        merged.dissolve(by=dissolve_by, as_index=False, aggfunc='first')
        .reset_index(drop=True)
    )
    logger.info(f"dissolve_to_boundary: {len(boundary_gdf)}개 커뮤니티 경계 생성")
    return boundary_gdf


# ──────────────────────────────────────────────────────────────────────────────
# 2. calculate_ifr  (기존 L1564 calculate_internal_flows_for_one_ku 방식 그대로)
# ──────────────────────────────────────────────────────────────────────────────

def calculate_ifr(
    mapping_df: pd.DataFrame,
    movement_df: pd.DataFrame,
    dong_col: str = "Dong",
    community_col: str = "community",
    o_col: str = "출발 행정동 코드",
    d_col: str = "도착 행정동 코드",
    flow_col: str = "이동인구(합)",
) -> pd.DataFrame:
    """
    IFR(Internal Flow Ratio) 산출.

    방향성 통행(directed) 기준:
      분자: O∈c  AND  D∈c   (커뮤니티 내부 완결 통행)
      분모: O∈c              (커뮤니티 출발 전체 통행, 서울 외 포함)

    Parameters
    ----------
    mapping_df   : 동-커뮤니티 매핑. [dong_col, community_col] 최소 보유.
    movement_df  : 이동 데이터. [o_col, d_col, flow_col] 필요.
    dong_col     : 동 코드 컬럼명 (기본: 'Dong')
    community_col: 커뮤니티 ID 컬럼명
    o_col        : 출발 행정동 코드 컬럼명
    d_col        : 도착 행정동 코드 컬럼명
    flow_col     : 이동인구(합) 컬럼명

    Returns
    -------
    DataFrame: [community, internal_flow, total_flow, ifr]
               커뮤니티별 IFR 결과.
    """
    _req_cols = [o_col, d_col, flow_col]
    if not all(c in movement_df.columns for c in _req_cols):
        raise ValueError(f"movement_df에 필요한 컬럼 누락: {_req_cols}")

    # 동-커뮤니티 딕셔너리
    dong_to_com = dict(
        zip(
            mapping_df[dong_col].astype(int),
            mapping_df[community_col].astype(int),
        )
    )

    df_temp = movement_df[[o_col, d_col, flow_col]].copy()
    df_temp["com_O"] = df_temp[o_col].map(dong_to_com).fillna(-1).astype(int)
    df_temp["com_D"] = df_temp[d_col].map(dong_to_com).fillna(-1).astype(int)

    # ── 분자: O∈c AND D∈c (내부 완결)
    df_int = df_temp[(df_temp["com_O"] == df_temp["com_D"]) & (df_temp["com_O"] != -1)]
    grp_int = (
        df_int.groupby("com_O")[flow_col].sum().reset_index()
        .rename(columns={"com_O": "community", flow_col: "internal_flow"})
    )

    # ── 분모: O∈c (외부 유출 통행 포함)
    df_tot = df_temp[df_temp["com_O"] != -1]
    grp_tot = (
        df_tot.groupby("com_O")[flow_col].sum().reset_index()
        .rename(columns={"com_O": "community", flow_col: "total_flow"})
    )

    # ── 병합 & IFR 계산
    all_com = pd.DataFrame({"community": mapping_df[community_col].unique()})
    result = (
        all_com
        .merge(grp_int, on="community", how="left")
        .merge(grp_tot, on="community", how="left")
        .fillna(0)
    )
    result["internal_flow"] = result["internal_flow"].astype(float)
    result["total_flow"]    = result["total_flow"].astype(float)
    result["ifr"] = result.apply(
        lambda r: round(r["internal_flow"] / r["total_flow"], 6)
        if r["total_flow"] > 0 else 0.0,
        axis=1,
    )
    result["community"] = result["community"].astype(int)
    return result[["community", "internal_flow", "total_flow", "ifr"]]


# ──────────────────────────────────────────────────────────────────────────────
# 2-2. calculate_gu_ifr (구 단위 생활권 내부통행 완결 비율)
# ──────────────────────────────────────────────────────────────────────────────

def calculate_gu_ifr(
    zone_ifr_df: pd.DataFrame,
    ku_col: str = "ku_name",
    internal_col: str = "internal_flow",
    total_col: str = "total_flow",
) -> pd.DataFrame:
    """
    구(Gu) 단위 생활권 내부통행 완결 비율(Gu-level IFR) 산출.

    수학적 집계 원칙 (단순 평균 금지):
      분자: 구 g 내 모든 생활권 c의 내부 완결 통행량(internal_flow) 합계
      분모: 구 g 내 모든 생활권 c의 총 출발 통행량(total_flow) 합계
      Gu IFR = 분자 / 분모

    Parameters
    ----------
    zone_ifr_df  : 생활권별 IFR 결과 데이터프레임. [ku_col, internal_col, total_col] 필요.
    ku_col       : 자치구 컬럼명 (기본 'ku_name')
    internal_col : 내부 통행량 컬럼명
    total_col    : 총 출발 통행량 컬럼명

    Returns
    -------
    DataFrame: [ku_col, n_zones, gu_internal_flow, gu_total_flow, gu_ifr]
    """
    _req = [ku_col, internal_col, total_col]
    if not all(c in zone_ifr_df.columns for c in _req):
        raise ValueError(f"zone_ifr_df에 필요한 컬럼 누락: {_req}")

    n_zones_col = "community" if "community" in zone_ifr_df.columns else internal_col
    gu_grp = (
        zone_ifr_df.groupby(ku_col)
        .agg(
            n_zones=(n_zones_col, "count"),
            gu_internal_flow=(internal_col, "sum"),
            gu_total_flow=(total_col, "sum")
        )
        .reset_index()
    )
    gu_grp["gu_internal_flow"] = gu_grp["gu_internal_flow"].astype(float)
    gu_grp["gu_total_flow"]    = gu_grp["gu_total_flow"].astype(float)
    gu_grp["gu_ifr"] = gu_grp.apply(
        lambda r: round(r["gu_internal_flow"] / r["gu_total_flow"], 6)
        if r["gu_total_flow"] > 0 else 0.0,
        axis=1
    )
    return gu_grp


# ──────────────────────────────────────────────────────────────────────────────
# 2-3. calculate_dong_within_zone_ifr (동 단위 생활권내 완결 비율)
# ──────────────────────────────────────────────────────────────────────────────

def calculate_dong_within_zone_ifr(
    mapping_df: pd.DataFrame,
    movement_df: pd.DataFrame,
    dong_col: str = "Dong",
    community_col: str = "community",
    o_col: str = "출발 행정동 코드",
    d_col: str = "도착 행정동 코드",
    flow_col: str = "이동인구(합)",
) -> pd.DataFrame:
    """
    행정동별(동단위) 소속 생활권/커뮤니티 내 통행 완결 비율(Dong-level within-zone IFR) 산출.

    정의:
      분자: 행정동 d에서 출발하여 소속 생활권/커뮤니티 C 내의 행정동으로 도착하는 통행량
            (O = d AND com_O == com_D)
      분모: 행정동 d에서 출발하는 서울 전체 통행량
            (O = d)
      Dong IFR = 분자 / 분모
    """
    _req_cols = [o_col, d_col, flow_col]
    if not all(c in movement_df.columns for c in _req_cols):
        raise ValueError(f"movement_df에 필요한 컬럼 누락: {_req_cols}")

    dong_to_com = dict(
        zip(
            mapping_df[dong_col].astype(int),
            mapping_df[community_col].astype(int),
        )
    )

    df_temp = movement_df[[o_col, d_col, flow_col]].copy()
    df_temp["com_O"] = df_temp[o_col].map(dong_to_com).fillna(-1).astype(int)
    df_temp["com_D"] = df_temp[d_col].map(dong_to_com).fillna(-1).astype(int)

    # 같은 생활권/커뮤니티 내부로 이동한 통행
    df_int = df_temp[(df_temp["com_O"] == df_temp["com_D"]) & (df_temp["com_O"] != -1)]
    grp_int = (
        df_int.groupby(o_col)[flow_col].sum().reset_index()
        .rename(columns={o_col: dong_col, flow_col: "flow_within_zone"})
    )

    # 동 d에서 출발한 전체 통행
    df_tot = df_temp[df_temp["com_O"] != -1]
    grp_tot = (
        df_tot.groupby(o_col)[flow_col].sum().reset_index()
        .rename(columns={o_col: dong_col, flow_col: "total_flow_dong"})
    )

    meta_cols = [c for c in [dong_col, community_col, "Ku", "ku_code", "ku_name", "ADM_NM", "life_zone_name", "community_name"] if c in mapping_df.columns]
    base_df = mapping_df[meta_cols].drop_duplicates(subset=[dong_col]).copy()
    base_df[dong_col] = base_df[dong_col].astype(int)

    result = (
        base_df
        .merge(grp_int, on=dong_col, how="left")
        .merge(grp_tot, on=dong_col, how="left")
        .fillna(0)
    )
    result["flow_within_zone"] = result["flow_within_zone"].astype(float)
    result["total_flow_dong"]  = result["total_flow_dong"].astype(float)
    result["dong_within_zone_ifr"] = result.apply(
        lambda r: round(r["flow_within_zone"] / r["total_flow_dong"], 6)
        if r["total_flow_dong"] > 0 else 0.0,
        axis=1
    )
    return result


# ──────────────────────────────────────────────────────────────────────────────
# 3. calculate_modularity
# ──────────────────────────────────────────────────────────────────────────────

def calculate_modularity(
    mapping_df: pd.DataFrame,
    movement_df: pd.DataFrame,
    dong_col: str = "Dong",
    community_col: str = "community",
    o_col: str = "출발 행정동 코드",
    d_col: str = "도착 행정동 코드",
    flow_col: str = "이동인구(합)",
) -> float:
    """
    Modularity 산출 (python-louvain / networkx 방식).

    무방향 대칭화 그래프:
      wij_undirected = w_ij + w_ji  (방향별 통행 합산)
    partition dict: {node_dong_code: community_id}

    Parameters
    ----------
    mapping_df   : 동-커뮤니티 매핑
    movement_df  : 이동 데이터

    Returns
    -------
    float : Modularity Q 값 (-1 ~ 1)
    """
    try:
        import community as community_louvain  # python-louvain
    except ImportError:
        raise ImportError(
            "python-louvain 라이브러리가 필요합니다. "
            "pip install python-louvain 로 설치하세요."
        )

    dong_to_com = dict(
        zip(
            mapping_df[dong_col].astype(int),
            mapping_df[community_col].astype(int),
        )
    )

    df = movement_df[[o_col, d_col, flow_col]].copy()
    df["com_O"] = df[o_col].map(dong_to_com).fillna(-1).astype(int)
    df["com_D"] = df[d_col].map(dong_to_com).fillna(-1).astype(int)

    # 커뮤니티에 속한 동 간 통행만 사용
    df = df[(df["com_O"] != -1) & (df["com_D"] != -1)]
    if df.empty:
        logger.warning("calculate_modularity: 유효 통행이 없어 Q=0 반환")
        return 0.0

    # 무방향 대칭화: A→B + B→A
    df_sym = (
        df.groupby([o_col, d_col])[flow_col].sum().reset_index()
    )
    df_rev = df_sym.rename(columns={o_col: d_col, d_col: o_col})
    df_undirected = (
        pd.concat([df_sym, df_rev], ignore_index=True)
        .groupby([o_col, d_col])[flow_col].sum().reset_index()
    )

    # networkx 그래프 생성
    G = nx.from_pandas_edgelist(
        df_undirected,
        source=o_col,
        target=d_col,
        edge_attr=flow_col,
        create_using=nx.Graph(),
    )
    nx.set_edge_attributes(G, {
        (r[o_col], r[d_col]): {"weight": r[flow_col]}
        for _, r in df_undirected.iterrows()
    })

    # partition은 동 코드 → 커뮤니티 ID
    partition = {
        node: dong_to_com[node]
        for node in G.nodes()
        if node in dong_to_com
    }

    q = community_louvain.modularity(partition, G, weight="weight")
    logger.info(f"Modularity Q = {q:.6f}")
    return float(q)


# ──────────────────────────────────────────────────────────────────────────────
# 4. calculate_iou  (iou_district_250106.py 방식 그대로)
# ──────────────────────────────────────────────────────────────────────────────

def calculate_iou(
    community_boundary_gdf: gpd.GeoDataFrame,
    official_lz_gdf: gpd.GeoDataFrame,
    community_ku_col: str = "ku_name",
    community_name_col: str = "community",
    lz_ku_col: str = "Gu",
    lz_name_col: str = "label_1",
    target_crs: str = "EPSG:5179",
) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """
    공식 생활권(official_lz_gdf) vs 커뮤니티 경계(community_boundary_gdf)
    구별 1:1 최대 IoU 매칭.

    산출 방식 (iou_district_250106.py 원본과 동일):
      1. 구별로 공식 생활권 × 커뮤니티 1:1 최대 IoU 매칭
      2. 구 IoU = Σintersection_area / Σunion_area  (면적합 기반)
      3. 서울 전체 IoU = 전 구 Σintersection / Σunion

    Parameters
    ----------
    community_boundary_gdf : 커뮤니티 경계 GeoDataFrame.
                             [community_ku_col, community_name_col, geometry] 필요.
    official_lz_gdf        : 공식 생활권 GeoDataFrame.
                             [lz_ku_col, lz_name_col, geometry] 필요.
    community_ku_col       : 커뮤니티 GDF의 구 이름 컬럼 (기본: 'ku_name')
    community_name_col     : 커뮤니티 GDF의 커뮤니티 ID/이름 컬럼 (기본: 'community')
    lz_ku_col              : 공식 생활권 GDF의 구 이름 컬럼 (기본: 'Gu')
    lz_name_col            : 공식 생활권 GDF의 생활권 이름 컬럼 (기본: 'label_1')
    target_crs             : 면적 계산용 좌표계 (기본: EPSG:5179 TM중부원점)

    Returns
    -------
    detail_df   : 생활권별 매칭 결과 DataFrame
    gu_iou_df   : 구별 IoU DataFrame
    city_iou    : 서울시 전체 IoU (0~100, %)
    """
    # 좌표계 통일
    cb = community_boundary_gdf.to_crs(target_crs).copy()
    lz = official_lz_gdf.to_crs(target_crs).copy()

    # 토폴로지 에러 방지
    cb["geometry"] = cb.geometry.buffer(0)
    lz["geometry"] = lz.geometry.buffer(0)

    iou_results = []

    for gu_name, lz_group in lz.groupby(lz_ku_col):
        com_group = cb[cb[community_ku_col] == gu_name]
        if com_group.empty:
            logger.warning(f"{gu_name}: 해당 구 커뮤니티 없음, 건너뜀")
            continue

        for _, lz_row in lz_group.iterrows():
            lz_geom = lz_row.geometry
            max_iou = 0.0
            best_com = None
            best_inter = 0.0
            best_union = 0.0

            for _, com_row in com_group.iterrows():
                com_geom = com_row.geometry
                if not lz_geom.intersects(com_geom):
                    continue
                inter_area = lz_geom.intersection(com_geom).area
                union_area = lz_geom.union(com_geom).area
                iou_val = inter_area / union_area if union_area != 0 else 0.0

                if iou_val > max_iou:
                    max_iou       = iou_val
                    best_com      = com_row[community_name_col]
                    best_inter    = inter_area
                    best_union    = union_area

            iou_results.append({
                "Gu":                  gu_name,
                "living_zone_name":    lz_row[lz_name_col],
                "best_community":      best_com,
                "IoU_pct":             round(max_iou * 100, 2),
                "intersection_area":   best_inter,
                "union_area":          best_union,
            })

    detail_df = pd.DataFrame(iou_results)
    if detail_df.empty:
        logger.warning("calculate_iou: 결과가 비어있습니다.")
        return detail_df, pd.DataFrame(), 0.0

    # 구별 IoU (면적합 기반, 원본 방식 동일)
    gu_stats = (
        detail_df.groupby("Gu")[["intersection_area", "union_area"]]
        .sum()
        .reset_index()
    )
    gu_stats["IoU_pct"] = (
        (gu_stats["intersection_area"] / gu_stats["union_area"])
        .replace([np.inf, -np.inf], 0)
        .fillna(0)
        * 100
    ).round(2)
    gu_iou_df = gu_stats[["Gu", "IoU_pct"]].copy()

    # 서울 전체 IoU
    total_inter = gu_stats["intersection_area"].sum()
    total_union = gu_stats["union_area"].sum()
    city_iou = round((total_inter / total_union) * 100, 2) if total_union > 0 else 0.0

    logger.info(f"서울 전체 IoU = {city_iou:.2f}%")
    return detail_df, gu_iou_df, city_iou


# ──────────────────────────────────────────────────────────────────────────────
# 5. evaluate_boundary_all_metrics  (통합 함수)
# ──────────────────────────────────────────────────────────────────────────────

def evaluate_boundary_all_metrics(
    *,
    mapping_df: pd.DataFrame,
    movement_df: pd.DataFrame,
    dong_gdf: gpd.GeoDataFrame,
    official_lz_gdf: gpd.GeoDataFrame,
    ku_col_in_dong: str = "ku_name",
    lz_ku_col: str = "Gu",
    lz_name_col: str = "label_1",
    dong_col: str = "Dong",
    community_col: str = "community",
    o_col: str = "출발 행정동 코드",
    d_col: str = "도착 행정동 코드",
    flow_col: str = "이동인구(합)",
    skip_modularity: bool = False,
) -> dict:
    """
    IFR + Modularity + IoU 를 한 번에 산출하는 통합 함수.

    Parameters
    ----------
    mapping_df       : 동-커뮤니티 매핑 DataFrame
    movement_df      : 이동 데이터 DataFrame (09~21시 비통근 필터 완료 상태)
    dong_gdf         : 423개 행정동 GeoDataFrame (정본)
    official_lz_gdf  : 116개 공식 생활권 GeoDataFrame (정본)
    skip_modularity  : True이면 Modularity 계산 건너뜀 (python-louvain 없을 때)

    Returns
    -------
    dict:
        "ifr_detail"    : pd.DataFrame  — 커뮤니티별 IFR
        "ifr_mean"      : float         — 가중 평균 IFR (total_flow 가중)
        "modularity"    : float | None  — Modularity Q
        "iou_detail"    : pd.DataFrame  — 생활권별 IoU 매칭
        "iou_gu"        : pd.DataFrame  — 구별 IoU
        "iou_city"      : float         — 서울 전체 IoU (%)
    """
    results: dict = {}

    # ── IFR
    logger.info("IFR 계산 중...")
    ifr_df = calculate_ifr(
        mapping_df, movement_df,
        dong_col=dong_col, community_col=community_col,
        o_col=o_col, d_col=d_col, flow_col=flow_col,
    )
    results["ifr_detail"] = ifr_df

    total_w = ifr_df["total_flow"].sum()
    results["ifr_mean"] = (
        round(
            (ifr_df["ifr"] * ifr_df["total_flow"]).sum() / total_w, 6
        )
        if total_w > 0 else 0.0
    )
    logger.info(f"  가중 평균 IFR = {results['ifr_mean']:.4f}")

    # ── Modularity
    if skip_modularity:
        results["modularity"] = None
        logger.info("Modularity 계산 건너뜀 (skip_modularity=True)")
    else:
        try:
            logger.info("Modularity 계산 중...")
            results["modularity"] = calculate_modularity(
                mapping_df, movement_df,
                dong_col=dong_col, community_col=community_col,
                o_col=o_col, d_col=d_col, flow_col=flow_col,
            )
        except Exception as e:
            logger.warning(f"Modularity 계산 실패: {e}")
            results["modularity"] = None

    # ── 커뮤니티 경계 생성 (IoU용)
    logger.info("커뮤니티 경계 dissolve 중...")
    boundary_gdf = dissolve_to_boundary(
        dong_gdf, mapping_df,
        dong_col=dong_col, community_col=community_col,
        ku_col=ku_col_in_dong if ku_col_in_dong in dong_gdf.columns else None,
    )

    # ── IoU
    logger.info("IoU 계산 중...")
    iou_detail, iou_gu, iou_city = calculate_iou(
        community_boundary_gdf=boundary_gdf,
        official_lz_gdf=official_lz_gdf,
        community_ku_col=ku_col_in_dong if ku_col_in_dong in boundary_gdf.columns else "ku_name",
        community_name_col=community_col,
        lz_ku_col=lz_ku_col,
        lz_name_col=lz_name_col,
    )
    results["iou_detail"] = iou_detail
    results["iou_gu"]     = iou_gu
    results["iou_city"]   = iou_city
    logger.info(f"  서울 전체 IoU = {iou_city:.2f}%")

    # ── 요약 출력
    logger.info(
        f"\n{'='*50}\n"
        f"[경계 지표 요약]\n"
        f"  IFR (가중평균) : {results['ifr_mean']:.4f}\n"
        f"  Modularity Q   : {results['modularity']}\n"
        f"  IoU (서울전체) : {iou_city:.2f}%\n"
        f"{'='*50}"
    )
    return results


# ──────────────────────────────────────────────────────────────────────────────
# 6. 간단한 자체 테스트 (직접 실행 시)
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).replace("boundary_metrics_engine.py", ""))
    from config import DONG_423_GPKG, LZ_116_GPKG, DONG_LZ_MAPPING

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logger.info("boundary_metrics_engine 자체 테스트 시작")

    # 정본 공간 데이터 로드
    dong_gdf = gpd.read_file(DONG_423_GPKG)
    lz_gdf   = gpd.read_file(LZ_116_GPKG)
    map_df   = pd.read_csv(DONG_LZ_MAPPING)

    logger.info(f"dong_gdf: {len(dong_gdf)}행, lz_gdf: {len(lz_gdf)}행")
    logger.info(f"map_df 컬럼: {list(map_df.columns)}")

    # ── dissolve_to_boundary 테스트 (공식 생활권 매핑 기준)
    # map_df에서 공식 생활권 ID를 community로 간주
    if "official_lz_id" in map_df.columns:
        test_map = map_df[["Dong", "official_lz_id"]].copy()
        test_map = test_map.rename(columns={"official_lz_id": "community"})
        boundary = dissolve_to_boundary(dong_gdf, test_map, ku_col=None)
        logger.info(f"dissolve_to_boundary OK: {len(boundary)}개 경계 폴리곤")
    else:
        logger.info("map_df에 'official_lz_id' 없음 → dissolve 테스트 건너뜀")

    logger.info("자체 테스트 완료 (이동 데이터 없으므로 IFR/Modularity 테스트 생략)")
