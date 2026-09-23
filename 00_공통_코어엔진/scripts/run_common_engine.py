# -*- coding: utf-8 -*-
"""
run_common_engine.py — 공통 코어엔진 다위계 통합 실행 스크립트
============================================================
목적:
  1. 정본 공간 데이터 (동 423개, 공식 116개) 및 매핑 3종 로드:
     - 공식 생활권 (116개)
     - 레이든 2020 (116개)
     - 레이든 2025 (116개)
  2. 3개 경계 일괄 dissolve 및 통합 GPKG(seoul_boundaries_all.gpkg) 생성
  3. 공간 정합성(IoU) 산출:
     - 공식 vs 레이든 2020
     - 공식 vs 레이든 2025
     - 레이든 2020 vs 레이든 2025 (시계열 경계 변화)
  4. 2020년 & 2025년 이동데이터(09~21시, 비통근) 기반 다위계 IFR 및 Modularity 산출:
     - 생활권별(구내) IFR (116개 단위)
     - 동별(생활권내) IFR (423개 단위)
  5. 통합 비교 결과물 저장 (Zone IFR, Dong IFR, IoU, Comprehensive Summary)

실행: python run_common_engine.py
"""

import os, sys, gc, time, logging, warnings
import pickle
import io

# Windows 콘솔 인코딩 대응
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import geopandas as gpd
import pandas as pd
import numpy as np

warnings.filterwarnings('ignore')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from config import (
    DONG_423_GPKG, LZ_116_GPKG, BOUNDARIES_ALL_GPKG,
    DONG_LZ_MAPPING, DONG_LEIDEN_2020_MAPPING, DONG_LEIDEN_2025_MAPPING,
    PRE_PKL_DIR, CRS_PROJECTED
)
from boundary_metrics_engine import (
    dissolve_to_boundary, calculate_ifr, calculate_gu_ifr,
    calculate_dong_within_zone_ifr, calculate_iou, calculate_modularity
)

OUT_DIR = os.path.join(SCRIPT_DIR, '..', 'output')
os.makedirs(OUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(OUT_DIR, 'run_common_engine.log'), encoding='utf-8')
    ]
)
log = logging.getLogger(__name__)

# 자치구 코드 매핑
KU_CODE_NAME = {
    11010: '종로구', 11020: '중구', 11030: '용산구', 11040: '성동구',
    11050: '광진구', 11060: '동대문구', 11070: '중랑구', 11080: '성북구',
    11090: '강북구', 11100: '도봉구', 11110: '노원구', 11120: '은평구',
    11130: '서대문구', 11140: '마포구', 11150: '양천구', 11160: '강서구',
    11170: '구로구', 11180: '금천구', 11190: '영등포구', 11200: '동작구',
    11210: '관악구', 11220: '서초구', 11230: '강남구', 11240: '송파구',
    11250: '강동구'
}


# ────────────────────────────────────────────────────────────────
# Step 1: 데이터 로드 및 검증
# ────────────────────────────────────────────────────────────────
def step1_load_data():
    log.info("=" * 65)
    log.info("Step 1. 정본 공간 데이터 및 매핑 3종 로드")
    log.info("=" * 65)

    dong_gdf = gpd.read_file(str(DONG_423_GPKG), layer='epsg5179')
    if 'ku_name' not in dong_gdf.columns:
        dong_gdf['ku_name'] = dong_gdf['Ku'].map(KU_CODE_NAME)

    map_official = pd.read_csv(str(DONG_LZ_MAPPING))
    map_ld20     = pd.read_csv(str(DONG_LEIDEN_2020_MAPPING))
    map_ld25     = pd.read_csv(str(DONG_LEIDEN_2025_MAPPING))

    # 표준 컬럼 정리
    map_official['community'] = map_official['life_zone_id'].astype(int)
    map_official['community_name'] = map_official['life_zone_name']

    map_ld20['community'] = map_ld20['global_community_id'].astype(int)
    map_ld25['community'] = map_ld25['global_community_id'].astype(int)

    for name, df in [('Official', map_official), ('Leiden_2020', map_ld20), ('Leiden_2025', map_ld25)]:
        assert len(df) == 423, f"{name} 행 수 != 423"
        assert df['Dong'].nunique() == 423, f"{name} Dong 중복"
        assert df['community'].nunique() == 116, f"{name} 커뮤니티 수 != 116"
        log.info(f"  [{name}] 423개 동, 116개 생활권/커뮤니티 검증 완료")

    return dong_gdf, map_official, map_ld20, map_ld25


# ────────────────────────────────────────────────────────────────
# Step 2: 3대 경계 Dissolve 및 통합 GPKG 생성
# ────────────────────────────────────────────────────────────────
def step2_generate_all_boundaries(dong_gdf, map_official, map_ld20, map_ld25):
    log.info("=" * 65)
    log.info("Step 2. 3대 경계 Dissolve 및 통합 GPKG 저장")
    log.info("=" * 65)

    b_official = dissolve_to_boundary(
        dong_gdf, map_official,
        dong_col='Dong', community_col='community', ku_col='ku_name'
    )
    b_ld20 = dissolve_to_boundary(
        dong_gdf, map_ld20,
        dong_col='Dong', community_col='community', ku_col='ku_name'
    )
    b_ld25 = dissolve_to_boundary(
        dong_gdf, map_ld25,
        dong_col='Dong', community_col='community', ku_col='ku_name'
    )

    log.info(f"  Official 경계: {len(b_official)}개")
    log.info(f"  Leiden 2020 경계: {len(b_ld20)}개")
    log.info(f"  Leiden 2025 경계: {len(b_ld25)}개")

    # 통합 GPKG 저장
    gpkg_path = str(BOUNDARIES_ALL_GPKG)
    b_official.to_file(gpkg_path, layer='official_livingzone_116', driver='GPKG')
    b_ld20.to_file(gpkg_path, layer='leiden_community_2020_116', driver='GPKG')
    b_ld25.to_file(gpkg_path, layer='leiden_community_2025_116', driver='GPKG')
    log.info(f"  통합 경계 GPKG 저장 완료: {gpkg_path}")

    return b_official, b_ld20, b_ld25


# ────────────────────────────────────────────────────────────────
# Step 3: 공간 정합성(IoU) 비교 산출
# ────────────────────────────────────────────────────────────────
def step3_calculate_all_ious(b_official, b_ld20, b_ld25):
    log.info("=" * 65)
    log.info("Step 3. 공간 정합성(IoU) 1:1 비교 산출")
    log.info("=" * 65)

    # 1) 공식 vs 레이든 2020
    d_20, gu_20, city_20 = calculate_iou(
        community_boundary_gdf=b_ld20,
        official_lz_gdf=b_official,
        community_ku_col='ku_name', community_name_col='community_name',
        lz_ku_col='ku_name', lz_name_col='community_name',
        target_crs=CRS_PROJECTED
    )
    log.info(f"  [공식 vs Leiden 2020] 서울 전체 IoU: {city_20:.2f}%")

    # 2) 공식 vs 레이든 2025
    d_25, gu_25, city_25 = calculate_iou(
        community_boundary_gdf=b_ld25,
        official_lz_gdf=b_official,
        community_ku_col='ku_name', community_name_col='community_name',
        lz_ku_col='ku_name', lz_name_col='community_name',
        target_crs=CRS_PROJECTED
    )
    log.info(f"  [공식 vs Leiden 2025] 서울 전체 IoU: {city_25:.2f}%")

    # 3) 레이든 2020 vs 레이든 2025 (경계 시계열 안정성)
    d_ts, gu_ts, city_ts = calculate_iou(
        community_boundary_gdf=b_ld25,
        official_lz_gdf=b_ld20,
        community_ku_col='ku_name', community_name_col='community_name',
        lz_ku_col='ku_name', lz_name_col='community_name',
        target_crs=CRS_PROJECTED
    )
    log.info(f"  [Leiden 2020 vs Leiden 2025 시계열 정합성] 서울 전체 IoU: {city_ts:.2f}%")

    # IoU 통합 엑셀 저장
    iou_out_path = os.path.join(OUT_DIR, "iou_comparison_official_vs_leiden.xlsx")
    with pd.ExcelWriter(iou_out_path, engine='openpyxl') as writer:
        # Gu Summary sheet
        gu_summary = gu_20.rename(columns={'IoU_pct': 'IoU_Official_vs_LD20'})
        gu_summary['IoU_Official_vs_LD25'] = gu_25['IoU_pct']
        gu_summary['IoU_LD20_vs_LD25']     = gu_ts['IoU_pct']
        gu_summary.to_excel(writer, sheet_name='Gu_Summary', index=False)

        d_20.to_excel(writer, sheet_name='Detail_Official_vs_LD20', index=False)
        d_25.to_excel(writer, sheet_name='Detail_Official_vs_LD25', index=False)
        d_ts.to_excel(writer, sheet_name='Detail_LD20_vs_LD25', index=False)

        city_summary = pd.DataFrame([
            {'비교대상': 'Official vs Leiden 2020', '서울전체_IoU_pct': city_20},
            {'비교대상': 'Official vs Leiden 2025', '서울전체_IoU_pct': city_25},
            {'비교대상': 'Leiden 2020 vs Leiden 2025', '서울전체_IoU_pct': city_ts},
        ])
        city_summary.to_excel(writer, sheet_name='City_Summary', index=False)

    log.info(f"  IoU 비교표 저장 완료: {iou_out_path}")
    return city_20, city_25, city_ts


# ────────────────────────────────────────────────────────────────
# Step 4: 연도별 이동데이터 로드 & 필터링
# ────────────────────────────────────────────────────────────────
def step4_load_movement(year_str):
    pkl_path = str(PRE_PKL_DIR / f"preprocessed_movement_data_{year_str}_01.pkl")
    if not os.path.exists(pkl_path):
        log.error(f"PKL 없음: {pkl_path}")
        return None

    t0 = time.time()
    log.info(f"[{year_str}] 생활이동 PKL 로드 중... ({os.path.getsize(pkl_path)/1e9:.1f} GB)")
    with open(pkl_path, 'rb') as f:
        df = pickle.load(f)
    log.info(f"  원본: {len(df):,}건 ({time.time()-t0:.1f}초)")

    mask = (
        (df['도착시간'].between(9, 20)) &
        (~df['이동유형'].isin(['HW', 'WH'])) &
        ((df['ku_O'] // 1000) == 11) &
        ((df['ku_D'] // 1000) == 11)
    )
    df_filtered = df[mask].copy()
    log.info(f"  일상생활통행 필터 후: {len(df_filtered):,}건 ({len(df_filtered)/len(df):.1%})")

    del df; gc.collect()
    return df_filtered


# ────────────────────────────────────────────────────────────────
# Step 5: 다위계 IFR 및 Modularity 산출 (연도별)
# ────────────────────────────────────────────────────────────────
def step5_calculate_metrics_for_year(year_str, df_flow, map_official, map_leiden):
    log.info("-" * 60)
    log.info(f"[{year_str}] 다위계 IFR 및 Modularity 산출 (Official & Leiden)")
    log.info("-" * 60)

    # ── A. 생활권별(Zone-level) IFR
    # 1) Official Zone IFR
    ifr_off_zone = calculate_ifr(map_official, df_flow, dong_col='Dong', community_col='community')
    ifr_off_zone = ifr_off_zone.merge(
        map_official[['community', 'ku_name', 'community_name']].drop_duplicates(),
        on='community', how='left'
    )
    tot_w_off = ifr_off_zone['total_flow'].sum()
    w_ifr_off = (ifr_off_zone['ifr'] * ifr_off_zone['total_flow']).sum() / tot_w_off if tot_w_off > 0 else 0

    # 2) Leiden Zone IFR
    ifr_ld_zone = calculate_ifr(map_leiden, df_flow, dong_col='Dong', community_col='community')
    ifr_ld_zone = ifr_ld_zone.merge(
        map_leiden[['community', 'ku_name', 'community_name']].drop_duplicates(),
        on='community', how='left'
    )
    tot_w_ld = ifr_ld_zone['total_flow'].sum()
    w_ifr_ld = (ifr_ld_zone['ifr'] * ifr_ld_zone['total_flow']).sum() / tot_w_ld if tot_w_ld > 0 else 0

    log.info(f"  [{year_str}] 생활권별 가중평균 IFR - Official: {w_ifr_off:.4f} | Leiden: {w_ifr_ld:.4f}")

    # ── B. 구별(Gu-level) IFR (구 내 생활권 내부통행합 / 구 내 생활권 출발통행합)
    ifr_off_gu = calculate_gu_ifr(ifr_off_zone, ku_col='ku_name')
    ifr_ld_gu  = calculate_gu_ifr(ifr_ld_zone,  ku_col='ku_name')
    log.info(f"  [{year_str}] 구별 IFR 산출 완료 (25개 구: 내부통행합/출발통행합)")

    # ── C. 동별(Dong-level within-zone) IFR
    # 1) Official Dong IFR
    ifr_off_dong = calculate_dong_within_zone_ifr(map_official, df_flow, dong_col='Dong', community_col='community')
    # 2) Leiden Dong IFR
    ifr_ld_dong  = calculate_dong_within_zone_ifr(map_leiden, df_flow, dong_col='Dong', community_col='community')

    m_dong_off = ifr_off_dong['dong_within_zone_ifr'].mean()
    m_dong_ld  = ifr_ld_dong['dong_within_zone_ifr'].mean()
    log.info(f"  [{year_str}] 동별 생활권내 IFR 단순평균 - Official: {m_dong_off:.4f} | Leiden: {m_dong_ld:.4f}")

    # ── D. Modularity Q
    q_off = calculate_modularity(map_official, df_flow, dong_col='Dong', community_col='community')
    q_ld  = calculate_modularity(map_leiden, df_flow, dong_col='Dong', community_col='community')
    log.info(f"  [{year_str}] Modularity Q - Official: {q_off:.4f} | Leiden: {q_ld:.4f}")

    return {
        'year': year_str,
        'ifr_off_zone': ifr_off_zone, 'ifr_ld_zone': ifr_ld_zone,
        'ifr_off_gu': ifr_off_gu,     'ifr_ld_gu': ifr_ld_gu,
        'ifr_off_dong': ifr_off_dong, 'ifr_ld_dong': ifr_ld_dong,
        'w_ifr_off': w_ifr_off,       'w_ifr_ld': w_ifr_ld,
        'm_dong_off': m_dong_off,     'm_dong_ld': m_dong_ld,
        'q_off': q_off,               'q_ld': q_ld
    }


# ────────────────────────────────────────────────────────────────
# Step 6: 통합 비교 보고서 엑셀 저장
# ────────────────────────────────────────────────────────────────
def step6_save_comparative_reports(res20, res25, city_iou20, city_iou25, city_iou_ts):
    log.info("=" * 65)
    log.info("Step 6. 최종 통합 비교 보고서 생성 및 엑셀 저장")
    log.info("=" * 65)

    # ── Report 1: ifr_zone_level_comparison_2020_2025.xlsx
    zone_path = os.path.join(OUT_DIR, "ifr_zone_level_comparison_2020_2025.xlsx")
    with pd.ExcelWriter(zone_path, engine='openpyxl') as writer:
        for yr, res in [('2020', res20), ('2025', res25)]:
            # 116개 zone 단위
            df_off = res['ifr_off_zone'][['community', 'ku_name', 'community_name', 'internal_flow', 'total_flow', 'ifr']].copy()
            df_off.columns = ['official_id', 'ku_name', 'official_name', 'off_internal', 'off_total', 'off_ifr']

            df_ld = res['ifr_ld_zone'][['community', 'ku_name', 'community_name', 'internal_flow', 'total_flow', 'ifr']].copy()
            df_ld.columns = ['leiden_id', 'ku_name', 'leiden_name', 'ld_internal', 'ld_total', 'ld_ifr']

            df_off.to_excel(writer, sheet_name=f'Official_{yr}', index=False)
            df_ld.to_excel(writer, sheet_name=f'Leiden_{yr}', index=False)

        summary_rows = [
            {'연도': '2020', '경계유형': 'Official', '가중평균_IFR': round(res20['w_ifr_off'], 6), 'Modularity_Q': round(res20['q_off'], 4)},
            {'연도': '2020', '경계유형': 'Leiden',   '가중평균_IFR': round(res20['w_ifr_ld'], 6),  'Modularity_Q': round(res20['q_ld'], 4)},
            {'연도': '2025', '경계유형': 'Official', '가중평균_IFR': round(res25['w_ifr_off'], 6), 'Modularity_Q': round(res25['q_off'], 4)},
            {'연도': '2025', '경계유형': 'Leiden',   '가중평균_IFR': round(res25['w_ifr_ld'], 6),  'Modularity_Q': round(res25['q_ld'], 4)},
        ]
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name='Zone_Summary', index=False)

    log.info(f"  생활권별 IFR 비교 저장: {zone_path}")

    # ── Report 2: ifr_gu_level_comparison_2020_2025.xlsx (신규: 25개 자치구 위계)
    gu_path = os.path.join(OUT_DIR, "ifr_gu_level_comparison_2020_2025.xlsx")
    with pd.ExcelWriter(gu_path, engine='openpyxl') as writer:
        gu20_off = res20['ifr_off_gu'][['ku_name', 'n_zones', 'gu_ifr']].rename(
            columns={'gu_ifr': 'gu_ifr_off_2020'}
        )
        gu20_ld = res20['ifr_ld_gu'][['ku_name', 'gu_ifr']].rename(
            columns={'gu_ifr': 'gu_ifr_ld_2020'}
        )
        gu25_off = res25['ifr_off_gu'][['ku_name', 'gu_ifr']].rename(
            columns={'gu_ifr': 'gu_ifr_off_2025'}
        )
        gu25_ld = res25['ifr_ld_gu'][['ku_name', 'gu_ifr']].rename(
            columns={'gu_ifr': 'gu_ifr_ld_2025'}
        )

        all_gu = (
            gu20_off
            .merge(gu20_ld, on='ku_name', how='left')
            .merge(gu25_off, on='ku_name', how='left')
            .merge(gu25_ld, on='ku_name', how='left')
        )
        all_gu['delta_gu_ifr_2020 (LD - Off)'] = (all_gu['gu_ifr_ld_2020'] - all_gu['gu_ifr_off_2020']).round(6)
        all_gu['delta_gu_ifr_2025 (LD - Off)'] = (all_gu['gu_ifr_ld_2025'] - all_gu['gu_ifr_off_2025']).round(6)
        all_gu['ts_delta_off (2025 - 2020)']   = (all_gu['gu_ifr_off_2025'] - all_gu['gu_ifr_off_2020']).round(6)
        all_gu['ts_delta_ld (2025 - 2020)']    = (all_gu['gu_ifr_ld_2025'] - all_gu['gu_ifr_ld_2020']).round(6)

        all_gu.to_excel(writer, sheet_name='Gu_Comparison_All', index=False)
        res20['ifr_off_gu'].to_excel(writer, sheet_name='Detail_Official_2020', index=False)
        res20['ifr_ld_gu'].to_excel(writer, sheet_name='Detail_Leiden_2020', index=False)
        res25['ifr_off_gu'].to_excel(writer, sheet_name='Detail_Official_2025', index=False)
        res25['ifr_ld_gu'].to_excel(writer, sheet_name='Detail_Leiden_2025', index=False)

    log.info(f"  구별 IFR 비교 저장: {gu_path}")

    # ── Report 3: ifr_dong_level_within_zone_2020_2025.xlsx
    dong_path = os.path.join(OUT_DIR, "ifr_dong_level_within_zone_2020_2025.xlsx")
    with pd.ExcelWriter(dong_path, engine='openpyxl') as writer:
        # 423개 동별 단일 통합 데이터프레임
        d20_off = res20['ifr_off_dong'][['Dong', 'Ku', 'ku_name', 'ADM_NM', 'life_zone_name', 'dong_within_zone_ifr']].rename(
            columns={'life_zone_name': 'official_lz_name', 'dong_within_zone_ifr': 'ifr_dong_off_2020'}
        )
        d20_ld = res20['ifr_ld_dong'][['Dong', 'community_name', 'dong_within_zone_ifr']].rename(
            columns={'community_name': 'leiden_com_2020', 'dong_within_zone_ifr': 'ifr_dong_ld_2020'}
        )
        d25_off = res25['ifr_off_dong'][['Dong', 'dong_within_zone_ifr']].rename(
            columns={'dong_within_zone_ifr': 'ifr_dong_off_2025'}
        )
        d25_ld = res25['ifr_ld_dong'][['Dong', 'community_name', 'dong_within_zone_ifr']].rename(
            columns={'community_name': 'leiden_com_2025', 'dong_within_zone_ifr': 'ifr_dong_ld_2025'}
        )

        all_dong = (
            d20_off
            .merge(d20_ld, on='Dong', how='left')
            .merge(d25_off, on='Dong', how='left')
            .merge(d25_ld, on='Dong', how='left')
        )
        all_dong['delta_ifr_2020 (LD - Off)'] = (all_dong['ifr_dong_ld_2020'] - all_dong['ifr_dong_off_2020']).round(6)
        all_dong['delta_ifr_2025 (LD - Off)'] = (all_dong['ifr_dong_ld_2025'] - all_dong['ifr_dong_off_2025']).round(6)

        all_dong.to_excel(writer, sheet_name='Dong_Level_All', index=False)

        # 소외 동 진단 (공식 IFR 대비 레이든 IFR 증가 폭이 가장 큰 상위 20개 동)
        top_beneficiary = all_dong.sort_values('delta_ifr_2025 (LD - Off)', ascending=False).head(20)
        top_beneficiary.to_excel(writer, sheet_name='Top20_Boundary_Mismatched_Dongs', index=False)

    log.info(f"  동별 생활권내 IFR 저장: {dong_path}")

    # ── Report 4: comprehensive_boundary_metrics_summary.xlsx
    summary_path = os.path.join(OUT_DIR, "comprehensive_boundary_metrics_summary.xlsx")
    comp_df = pd.DataFrame([
        {
            '연도': '2020',
            '경계유형': '공식 생활권 (116개)',
            '생활권_가중평균_IFR': round(res20['w_ifr_off'], 4),
            '동_생활권내_평균_IFR': round(res20['m_dong_off'], 4),
            'Modularity_Q': round(res20['q_off'], 4),
            '서울전체_IoU_pct': 100.0,
        },
        {
            '연도': '2020',
            '경계유형': '레이든 커뮤니티 (116개)',
            '생활권_가중평균_IFR': round(res20['w_ifr_ld'], 4),
            '동_생활권내_평균_IFR': round(res20['m_dong_ld'], 4),
            'Modularity_Q': round(res20['q_ld'], 4),
            '서울전체_IoU_pct': round(city_iou20, 2),
        },
        {
            '연도': '2025',
            '경계유형': '공식 생활권 (116개)',
            '생활권_가중평균_IFR': round(res25['w_ifr_off'], 4),
            '동_생활권내_평균_IFR': round(res25['m_dong_off'], 4),
            'Modularity_Q': round(res25['q_off'], 4),
            '서울전체_IoU_pct': 100.0,
        },
        {
            '연도': '2025',
            '경계유형': '레이든 커뮤니티 (116개)',
            '생활권_가중평균_IFR': round(res25['w_ifr_ld'], 4),
            '동_생활권내_평균_IFR': round(res25['m_dong_ld'], 4),
            'Modularity_Q': round(res25['q_ld'], 4),
            '서울전체_IoU_pct': round(city_iou25, 2),
        },
    ])
    with pd.ExcelWriter(summary_path, engine='openpyxl') as writer:
        comp_df.to_excel(writer, sheet_name='Boundary_Summary', index=False)
        all_gu.to_excel(writer, sheet_name='Gu_Level_Summary', index=False)

    log.info(f"  종합 평가 보고서 저장 완료: {summary_path}")
    log.info("\n" + "="*70 + "\n[종합 분석 결과표]\n" + comp_df.to_string(index=False) + "\n" + "="*70)


# ────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────
def main():
    t_start = time.time()
    log.info("=" * 65)
    log.info("  공통 코어엔진 다위계 통합 배치 실행 시작")
    log.info("=" * 65)

    # 1. 데이터 및 매핑 로드
    dong_gdf, map_official, map_ld20, map_ld25 = step1_load_data()

    # 2. 3대 경계 생성 및 GPKG 저장
    b_official, b_ld20, b_ld25 = step2_generate_all_boundaries(dong_gdf, map_official, map_ld20, map_ld25)

    # 3. 공간 정합성(IoU) 산출
    city_iou20, city_iou25, city_iou_ts = step3_calculate_all_ious(b_official, b_ld20, b_ld25)

    # 4 & 5. 이동데이터 로드 및 다위계 IFR 산출
    # 2020년
    df_flow_20 = step4_load_movement('2020')
    res20 = step5_calculate_metrics_for_year('2020', df_flow_20, map_official, map_ld20)
    del df_flow_20; gc.collect()

    # 2025년
    df_flow_25 = step4_load_movement('2025')
    res25 = step5_calculate_metrics_for_year('2025', df_flow_25, map_official, map_ld25)
    del df_flow_25; gc.collect()

    # 6. 최종 통합 비교 보고서 엑셀 저장
    step6_save_comparative_reports(res20, res25, city_iou20, city_iou25, city_iou_ts)

    elapsed = time.time() - t_start
    log.info(f"  전체 완료 소요시간: {elapsed:.1f}초")


if __name__ == '__main__':
    main()
