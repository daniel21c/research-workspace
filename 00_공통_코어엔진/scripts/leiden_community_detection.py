# -*- coding: utf-8 -*-
"""
leiden_community_detection.py — 레이든 커뮤니티 구획 공통 엔진
================================================================
00_공통_코어엔진 표준 스크립트.

기반 코드:
  D:/Research/1_OUTPUT/999. python package/DISTRICT_age/
  251022_Leiden_25_scan_병렬_중복해결.py

주요 개선:
  - Co-association Matrix 누적을 파이썬 이중 for 루프 → NumPy 브로드캐스팅으로 교체
    (알고리즘·결과 100% 동일, 수백 배 고속화)
  - 경로·출력을 config.py 기반 공통 코어엔진으로 통합

알고리즘 구조 (기존 방법론 그대로 유지):
  1. 구별(자치구) 무방향 대칭화 네트워크 구성 (w_ij + w_ji)
  2. 해상도 0.01 ~ 2.50 전수 스캔 (각 해상도에서 Consensus 완료 후 개수 확인)
  3. 타겟 커뮤니티 수 (구별 3~7개, 합계 116개) 맞는 해상도에서
     Modularity 우선 → IFR 차선으로 최적 파티션 선택
  4. 미매칭 시 세밀 스캔(Fine-grained scan) 수행

IFR 정의 (방향성, JTG 게재본 Eq.2):
  분자: O∈c AND D∈c (내부 완결)
  분모: O∈c (서울 전체 출발)
"""

import os, sys, gc, io, logging, warnings, pickle, datetime, json
import concurrent.futures, argparse

import numpy as np
import pandas as pd
import geopandas as gpd
import igraph as ig
import leidenalg
import networkx as nx
from tqdm import tqdm

warnings.filterwarnings('ignore')

# Windows 콘솔 인코딩 대응
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from config import (
    DONG_423_GPKG, PRE_PKL_DIR, DONG_LEIDEN_2020_MAPPING, DONG_LEIDEN_2025_MAPPING,
    CRS_PROJECTED
)

# ─────────────────────────────────────────────────────────────────────
# 출력 경로 설정
# ─────────────────────────────────────────────────────────────────────
COMMON_OUT = os.path.join(SCRIPT_DIR, '..', 'output', 'leiden')
os.makedirs(COMMON_OUT, exist_ok=True)

log_filename = os.path.join(COMMON_OUT, f'leiden_run_{datetime.datetime.now():%Y%m%d_%H%M%S}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# 자치구 설정 (기존 코드 그대로)
# ─────────────────────────────────────────────────────────────────────
KU_CODE_NAME = {
    11010: '종로구', 11020: '중구', 11030: '용산구', 11040: '성동구',
    11050: '광진구', 11060: '동대문구', 11070: '중랑구', 11080: '성북구',
    11090: '강북구', 11100: '도봉구', 11110: '노원구', 11120: '은평구',
    11130: '서대문구', 11140: '마포구', 11150: '양천구', 11160: '강서구',
    11170: '구로구', 11180: '금천구', 11190: '영등포구', 11200: '동작구',
    11210: '관악구', 11220: '서초구', 11230: '강남구', 11240: '송파구',
    11250: '강동구'
}

# 구별 목표 커뮤니티 수 (합계 116개)
TARGET_COMMUNITIES = {
    11010: 4, 11020: 3, 11030: 4, 11040: 4, 11050: 4,
    11060: 4, 11070: 3, 11080: 5, 11090: 4, 11100: 5,
    11110: 7, 11120: 5, 11130: 4, 11140: 5, 11150: 5,
    11160: 6, 11170: 4, 11180: 3, 11190: 5, 11200: 5,
    11210: 5, 11220: 4, 11230: 6, 11240: 7, 11250: 5,
}

# 스캔 파라미터
RES_MIN, RES_MAX, RES_STEP = 0.01, 2.50, 0.01   # 250개 해상도 전수 스캔
NUM_ITERATIONS = 200   # 해상도 탐색 시 Consensus 반복 횟수
NUM_ITERATIONS_FINAL = 200  # 최종 확정 파티션 Consensus 반복 횟수
TAU = 0.5              # Co-association 임계값


# ─────────────────────────────────────────────────────────────────────
# 핵심 함수 ①: 무방향 대칭화 네트워크 구성
# ─────────────────────────────────────────────────────────────────────
def make_undirected_flow(df, dong_set):
    """
    방향성 이동 데이터 → 무방향 대칭화 (w_ij + w_ji)
    구(ku) 내부 동 간의 통행만 추출.
    """
    df2 = df.copy()
    df2 = df2.rename(columns={
        '출발 행정동 코드': 'dong_O',
        '도착 행정동 코드': 'dong_D',
        '이동인구(합)': 'flow'
    })
    df2 = df2[
        df2['dong_O'].isin(dong_set) &
        df2['dong_D'].isin(dong_set)
    ][['dong_O', 'dong_D', 'flow']].copy()

    # 양방향 합산 → 무방향
    df_rev = df2.rename(columns={'dong_O': 'dong_D', 'dong_D': 'dong_O'})
    df_sym = (
        pd.concat([df2, df_rev], ignore_index=True)
        .groupby(['dong_O', 'dong_D'])['flow'].sum()
        .reset_index()
    )
    # 자기 자신 제거
    df_sym = df_sym[df_sym['dong_O'] != df_sym['dong_D']].copy()
    return df_sym


# ─────────────────────────────────────────────────────────────────────
# 핵심 함수 ②: consensus_communities (NumPy 벡터화 적용)
# ─────────────────────────────────────────────────────────────────────
def consensus_communities(ig_G, index_to_node, resolution=1.0,
                          num_iterations=NUM_ITERATIONS, tau=TAU):
    """
    Co-association Matrix 기반 합의 클러스터링 (Label Switching 해결).

    [핵심 수정] Co-association Matrix 누적:
      기존: 파이썬 이중 for 루프 O(n²) → 느림
      수정: NumPy 브로드캐스팅  mem[:, None] == mem[None, :]  → 수백 배 빠름
      알고리즘·결과는 100% 동일.

    절차:
      ① num_iterations회 Leiden 실행 → Co-association Matrix 누적
      ② 행렬을 확률(0~1)로 정규화
      ③ τ 이상인 쌍만 엣지로 연결한 합의 그래프 구성
      ④ 연결 컴포넌트(Connected Components) = 최종 커뮤니티 확정
    """
    if not ig_G:
        log.warning("consensus_communities: invalid ig_G.")
        return {}

    try:
        nodes = list(index_to_node.values())
        n_nodes = len(nodes)
        if n_nodes == 0:
            return {}

        node_to_idx = {node: i for i, node in enumerate(nodes)}
        # igraph vertex index → node_to_idx 매핑 (igraph idx → nodes idx)
        ig_to_local = {ig_idx: node_to_idx[node]
                       for ig_idx, node in index_to_node.items()
                       if node in node_to_idx}

        co_assoc_matrix = np.zeros((n_nodes, n_nodes), dtype=np.float32)

        for _ in range(num_iterations):
            partition = leidenalg.find_partition(
                ig_G,
                leidenalg.RBConfigurationVertexPartition,
                resolution_parameter=resolution,
                weights='weight',
                seed=None
            )
            raw_mem = np.array(partition.membership)

            # igraph vertex 순서 → local nodes 순서로 재배열
            local_mem = np.empty(n_nodes, dtype=np.int32)
            for ig_idx, loc_idx in ig_to_local.items():
                local_mem[loc_idx] = raw_mem[ig_idx]

            # ──────────────────────────────────────────────────────────
            # [핵심 수정] 파이썬 이중 for 루프 → NumPy 브로드캐스팅
            # 동일한 커뮤니티 번호인 쌍 (i, j)에 1을 누적
            # ──────────────────────────────────────────────────────────
            co_assoc_matrix += (local_mem[:, None] == local_mem[None, :]).astype(np.float32)

        # 확률로 정규화
        co_assoc_matrix /= num_iterations

        # τ 이상인 쌍으로 합의 그래프 구성
        consensus_graph = ig.Graph(n=n_nodes)
        rows, cols = np.where(
            (co_assoc_matrix >= tau) &
            (np.triu(np.ones((n_nodes, n_nodes), dtype=bool), k=1))
        )
        if len(rows) > 0:
            edges_to_add = list(zip(rows.tolist(), cols.tolist()))
            edge_weights = co_assoc_matrix[rows, cols].tolist()
            consensus_graph.add_edges(edges_to_add)
            consensus_graph.es['weight'] = edge_weights

        # 연결 컴포넌트 = 최종 커뮤니티
        components = consensus_graph.clusters()
        cluster_labels = components.membership
        final_communities = {nodes[i]: int(cluster_labels[i]) for i in range(n_nodes)}
        return final_communities

    except Exception as e:
        log.error(f"consensus_communities error: {e}", exc_info=True)
        return {}


# ─────────────────────────────────────────────────────────────────────
# 핵심 함수 ③: 해상도 전수 스캔
# ─────────────────────────────────────────────────────────────────────
def scan_resolution(ig_G, G_nx, index_to_node, movement_df_ku,
                    ku_code, year_str, target_count,
                    num_iterations=NUM_ITERATIONS, tau=TAU,
                    selection_criteria='modularity', worker_idx=0):
    """
    해상도 0.01~2.50 전수 스캔.
    각 해상도에서 Consensus 완료 후 커뮤니티 수를 확인한 뒤 최적 파티션 선택.
    타겟 미매칭 시 세밀 스캔(100단계) 추가 수행.
    """
    import community as community_louvain

    ku_name = KU_CODE_NAME.get(ku_code, str(ku_code))
    res_array = np.arange(RES_MIN, RES_MAX + RES_STEP / 2, RES_STEP)

    dong_to_com_flow = None
    if movement_df_ku is not None and not movement_df_ku.empty:
        dong_to_com_flow = movement_df_ku

    best_res, best_partition, best_metrics = None, {}, {}
    best_primary = -np.inf if selection_criteria == 'modularity' else -1.0
    best_secondary = -1.0 if selection_criteria == 'modularity' else -np.inf
    found_flag = False
    scan_log = []

    def eval_partition(partition, res):
        n = len(set(partition.values()))
        Q = community_louvain.modularity(partition, G_nx, weight='weight')
        ifr = 0.0
        int_flow = 0.0
        tot_flow = 0.0
        if dong_to_com_flow is not None:
            df_t = dong_to_com_flow.copy()
            df_t['com_O'] = df_t['출발 행정동 코드'].map(partition).fillna(-1).astype(int)
            df_t['com_D'] = df_t['도착 행정동 코드'].map(partition).fillna(-1).astype(int)
            int_flow = float(df_t[(df_t['com_O'] == df_t['com_D']) & (df_t['com_O'] != -1)]['이동인구(합)'].sum())
            tot_flow  = float(df_t[df_t['com_O'] != -1]['이동인구(합)'].sum())
            ifr = int_flow / tot_flow if tot_flow > 0 else 0.0
        return n, Q, ifr, int_flow, tot_flow

    def try_update(partition, res):
        nonlocal best_res, best_partition, best_metrics, best_primary, best_secondary, found_flag
        n, Q, ifr, int_flow, tot_flow = eval_partition(partition, res)
        if n != target_count:
            return n, Q, ifr, int_flow, tot_flow

        primary   = Q if selection_criteria == 'modularity' else ifr
        secondary = ifr if selection_criteria == 'modularity' else Q
        if primary > best_primary or (primary == best_primary and secondary > best_secondary):
            best_primary, best_secondary = primary, secondary
            best_res, best_partition = res, partition.copy()
            best_metrics = {'resolution': round(res, 6), 'n_communities': n,
                            'modularity': round(Q, 4), 'total_flow': round(tot_flow, 2),
                            'internal_flow': round(int_flow, 2), 'ifr': round(ifr, 6)}
            found_flag = True
        return n, Q, ifr, int_flow, tot_flow

    log.info(f"[{ku_name} {year_str}] 해상도 스캔 시작 (250단계, 각 {num_iterations}회 Consensus)")
    for res in tqdm(res_array, desc=f"Leiden {ku_name} {year_str}", leave=False, position=worker_idx):
        try:
            partition = consensus_communities(ig_G, index_to_node, resolution=res,
                                             num_iterations=num_iterations, tau=tau)
            if not partition:
                continue
            n, Q, ifr, int_flow, tot_flow = try_update(partition, res)
            scan_log.append({'resolution': round(res, 4), 'n_communities': n,
                             'modularity': round(Q, 4), 'ifr': round(ifr, 6)})
        except Exception as e:
            log.error(f"[{ku_name} {year_str}] scan res={res:.4f} error: {e}")
        gc.collect()

    # 타겟 미매칭 시 세밀 스캔
    if not found_flag:
        log.warning(f"[{ku_name} {year_str}] 타겟 {target_count}개 미매칭 → 세밀 스캔 수행")
        below = [(r['resolution'], r['n_communities']) for r in scan_log if r['n_communities'] < target_count]
        above = [(r['resolution'], r['n_communities']) for r in scan_log if r['n_communities'] > target_count]
        if below and above:
            r_lo = max(below, key=lambda x: x[1])[0]
            r_hi = min(above, key=lambda x: x[1])[0]
            fine_array = np.linspace(r_lo, r_hi, 100)
            for fres in tqdm(fine_array, desc=f"Fine {ku_name}", leave=False, position=worker_idx):
                try:
                    fp = consensus_communities(ig_G, index_to_node, resolution=fres,
                                              num_iterations=num_iterations, tau=tau)
                    if fp:
                        try_update(fp, fres)
                except Exception as e:
                    log.error(f"[{ku_name} {year_str}] fine scan res={fres:.6f} error: {e}")
                gc.collect()

    if best_partition:
        log.info(f"[{ku_name} {year_str}] 최적 해상도={best_res:.4f}, "
                 f"커뮤니티={best_metrics.get('n_communities')}, "
                 f"Mod={best_metrics.get('modularity')}, IFR={best_metrics.get('ifr')}")
    else:
        log.warning(f"[{ku_name} {year_str}] 파티션 확정 실패")

    return best_res, best_partition, best_metrics, scan_log


# ─────────────────────────────────────────────────────────────────────
# 자치구 단위 Leiden 실행 (병렬 워커)
# ─────────────────────────────────────────────────────────────────────
def run_for_ku(args):
    ku_code, dong_gdf_ku, flow_df, year_str, worker_idx = args
    ku_name = KU_CODE_NAME.get(ku_code, str(ku_code))
    target = TARGET_COMMUNITIES.get(ku_code, 4)

    dong_set = set(dong_gdf_ku['Dong'].astype(int).tolist())
    df_sym = make_undirected_flow(flow_df, dong_set)
    if df_sym.empty:
        log.warning(f"[{ku_name} {year_str}] 무방향 플로우 없음")
        return None

    df_net = df_sym.rename(columns={'dong_O': 'source', 'dong_D': 'target', 'flow': 'weight'})
    sources = df_net['source'].tolist()
    targets = df_net['target'].tolist()
    weights = df_net['weight'].tolist()
    nodes   = list(set(sources + targets))

    node_to_index = {n: i for i, n in enumerate(nodes)}
    index_to_node = {i: n for n, i in node_to_index.items()}

    ig_G = ig.Graph(directed=False)
    ig_G.add_vertices(len(nodes))
    ig_G.add_edges([(node_to_index[s], node_to_index[t]) for s, t in zip(sources, targets)])
    ig_G.es['weight'] = weights

    G_nx = nx.Graph()
    G_nx.add_weighted_edges_from(zip(sources, targets, weights))

    # 이동데이터: 해당 구 내 출발 통행 (IFR 계산용, 방향성 유지)
    flow_ku = flow_df[flow_df['출발 행정동 코드'].isin(dong_set)].copy()

    best_res, best_partition, best_metrics, scan_log = scan_resolution(
        ig_G, G_nx, index_to_node, flow_ku,
        ku_code, year_str, target,
        num_iterations=NUM_ITERATIONS, tau=TAU,
        selection_criteria='modularity',
        worker_idx=worker_idx
    )

    if not best_partition:
        return None

    df_com = pd.DataFrame(list(best_partition.items()), columns=['Dong', 'community'])
    df_com['community'] = df_com['community'].astype(int)
    df_com['ku_code']   = ku_code
    df_com['ku_name']   = ku_name
    best_metrics['ku_code'] = ku_code
    best_metrics['ku_name'] = ku_name

    return {'mapping': df_com, 'metrics': best_metrics, 'scan_log': scan_log}


# ─────────────────────────────────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────────────────────────────────
def main(years=('2020', '2025'), n_workers=4):
    import io as _io

    # 동 정본 로드
    dong_gdf = gpd.read_file(str(DONG_423_GPKG), layer='epsg5179')
    dong_gdf['Dong'] = dong_gdf['Dong'].astype(int)
    dong_gdf['Ku']   = dong_gdf['Ku'].astype(int)
    log.info(f"동 정본 로드 완료: {len(dong_gdf)}개")

    for year_str in years:
        log.info("=" * 60)
        log.info(f"연도: {year_str}")
        log.info("=" * 60)

        pkl_path = str(PRE_PKL_DIR / f"preprocessed_movement_data_{year_str}_01.pkl")
        if not os.path.exists(pkl_path):
            log.error(f"PKL 없음: {pkl_path}")
            continue

        log.info(f"이동데이터 로드: {pkl_path}")
        with open(pkl_path, 'rb') as f:
            df_all = pickle.load(f)

        # 09~21시 비통근 필터
        df_filtered = df_all[
            df_all['도착시간'].between(9, 20) &
            (~df_all['이동유형'].isin(['HW', 'WH'])) &
            ((df_all['ku_O'] // 1000) == 11) &
            ((df_all['ku_D'] // 1000) == 11)
        ].copy()
        log.info(f"필터 후: {len(df_filtered):,}건")
        del df_all; gc.collect()

        year_out = os.path.join(COMMON_OUT, year_str)
        os.makedirs(os.path.join(year_out, 'shapefiles'), exist_ok=True)
        os.makedirs(os.path.join(year_out, 'metrics'), exist_ok=True)

        # 자치구별 병렬 실행
        task_args = [
            (ku_code,
             dong_gdf[dong_gdf['Ku'] == ku_code].copy(),
             df_filtered,
             year_str,
             i % n_workers)
            for i, ku_code in enumerate(sorted(TARGET_COMMUNITIES.keys()))
        ]

        all_mappings = []
        all_metrics  = []

        log.info(f"자치구 {len(task_args)}개 병렬 처리 시작 (workers={n_workers})")
        with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers) as executor:
            futures = {executor.submit(run_for_ku, args): args[0] for args in task_args}
            for future in concurrent.futures.as_completed(futures):
                ku_code = futures[future]
                ku_name = KU_CODE_NAME.get(ku_code, str(ku_code))
                try:
                    result = future.result()
                    if result:
                        all_mappings.append(result['mapping'])
                        all_metrics.append(result['metrics'])
                        log.info(f"[{ku_name} {year_str}] 완료")
                    else:
                        log.warning(f"[{ku_name} {year_str}] 결과 없음")
                except Exception as e:
                    log.error(f"[{ku_name} {year_str}] 오류: {e}", exc_info=True)

        if not all_mappings:
            log.error(f"[{year_str}] 모든 자치구 실패")
            continue

        # 통합 매핑 저장
        df_map = pd.concat(all_mappings, ignore_index=True)
        df_map = df_map.merge(dong_gdf[['Dong', 'ADM_NM']].drop_duplicates(), on='Dong', how='left')

        # global_community_id 부여 (ku_code * 100 + community)
        df_map['global_community_id'] = df_map['ku_code'] * 100 + df_map['community']

        map_csv = os.path.join(year_out, 'metrics', f'leiden_mapping_{year_str}.csv')
        map_xlsx = os.path.join(year_out, 'metrics', f'leiden_mapping_{year_str}.xlsx')
        df_map.to_csv(map_csv, index=False, encoding='utf-8-sig')
        df_map.to_excel(map_xlsx, index=False)
        log.info(f"[{year_str}] 매핑 저장: {map_csv} ({len(df_map)}행)")

        # 통합 지표 저장
        df_met = pd.DataFrame(all_metrics)
        met_xlsx = os.path.join(year_out, 'metrics', f'leiden_metrics_{year_str}.xlsx')
        df_met.to_excel(met_xlsx, index=False)
        log.info(f"[{year_str}] 지표 저장: {met_xlsx}")

        # 통합 SHP 생성 (combined_community_map)
        shp_rows = []
        for _, row in df_map.iterrows():
            dong_geom = dong_gdf[dong_gdf['Dong'] == row['Dong']]
            if not dong_geom.empty:
                shp_rows.append({
                    'Dong': row['Dong'], 'community': row['community'],
                    'ku_code': row['ku_code'], 'ku_name': row['ku_name'],
                    'ADM_NM': row.get('ADM_NM', ''),
                    'global_id': row['global_community_id'],
                    'geometry': dong_geom.iloc[0]['geometry']
                })

        gdf_shp = gpd.GeoDataFrame(shp_rows, crs=dong_gdf.crs)
        gdf_dissolved = gdf_shp.dissolve(by=['ku_code', 'community'], as_index=False, aggfunc='first')
        shp_path = os.path.join(year_out, 'shapefiles', f'combined_community_map_{year_str}.shp')
        gdf_dissolved.to_file(shp_path)
        log.info(f"[{year_str}] SHP 저장: {shp_path} ({len(gdf_dissolved)}개 커뮤니티)")

        # 공통 코어엔진 data/ 정본 CSV 업데이트
        from config import COMMON_DATA_DIR
        norm_csv = str(COMMON_DATA_DIR / f'dong_to_leiden_{year_str}_mapping_423.csv')
        df_map.to_csv(norm_csv, index=False, encoding='utf-8-sig')
        log.info(f"[{year_str}] 정본 매핑 갱신: {norm_csv}")

        del df_filtered; gc.collect()

    log.info("Leiden 커뮤니티 구획 전체 완료")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Leiden Community Detection (공통 코어엔진)')
    parser.add_argument('--years', nargs='+', default=['2020', '2025'],
                        help='처리할 연도 (예: --years 2020 2025)')
    parser.add_argument('--workers', type=int, default=4,
                        help='병렬 처리 워커 수')
    args = parser.parse_args()
    main(years=args.years, n_workers=args.workers)
