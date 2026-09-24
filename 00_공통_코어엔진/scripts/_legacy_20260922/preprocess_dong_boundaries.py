# -*- coding: utf-8 -*-
"""
preprocess_dong_boundaries.py

목적:
1. 서울시 행정동 경계(BND_ADM_DONG_PG_SHP)에서 3개 분할 행정동(구로 오류2동, 강남 신사/압구정, 강동 상일동)을
   Dong(7자리) 기준으로 dissolve하여 무결한 423개 유니크 행정동 공간데이터 구축.
2. 서울시 공식 116개 생활권(UPIS_SHP_ZON100)과 EPSG:5179 평면직각좌표계에서 교차면적을 계산하여,
   모든 행정동이 최대 중첩 면적을 가진 단 1개의 생활권에 배정되도록 1:1 매핑 테이블 확정 (강남구 이중 매핑 버그 원천 제거).
3. 분석 정본 공간데이터 및 매핑 테이블 저장.

산출물:
- 00_공통_데이터_및_모듈/data/seoul_dong_423_dissolved.gpkg (layers: 'epsg5179', 'epsg4326')
- 00_공통_데이터_및_모듈/data/seoul_official_livingzone_116.gpkg (layers: 'epsg5179', 'epsg4326')
- 00_공통_데이터_및_모듈/data/dong_to_official_livingzone_mapping_423.xlsx
- 00_공통_데이터_및_모듈/data/dong_to_official_livingzone_mapping_423.csv
"""

import os
import sys
import logging
import warnings
import geopandas as gpd
import pandas as pd
import numpy as np

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

BASE_DIR = r"D:\Research"
RAW_DONG_SHP = os.path.join(BASE_DIR, r"0_RAW\BND_ADM_DONG_PG_SHP")
RAW_LZ_SHP   = os.path.join(BASE_DIR, r"0_RAW\UPIS_SHP_ZON100\seoul_living_zone.shp")
OUT_DATA_DIR = os.path.join(BASE_DIR, r"00_박사논문_연구체계\00_공통_코어엔진\data")
os.makedirs(OUT_DATA_DIR, exist_ok=True)

ku_code_name_mapping = {
    11010: '종로구', 11020: '중구', 11030: '용산구', 11040: '성동구',
    11050: '광진구', 11060: '동대문구', 11070: '중랑구', 11080: '성북구',
    11090: '강북구', 11100: '도봉구', 11110: '노원구', 11120: '은평구',
    11130: '서대문구', 11140: '마포구', 11150: '양천구', 11160: '강서구',
    11170: '구로구', 11180: '금천구', 11190: '영등포구', 11200: '동작구',
    11210: '관악구', 11220: '서초구', 11230: '강남구', 11240: '송파구',
    11250: '강동구'
}

def main():
    logging.info("Step 1. 서울시 행정동 경계 로드 및 전처리...")
    gdf_dong = gpd.read_file(RAW_DONG_SHP, encoding='cp949')
    gdf_dong = gdf_dong[gdf_dong.geometry.type.isin(['Polygon', 'MultiPolygon'])].copy()
    
    gdf_dong['Dong'] = (gdf_dong['ADM_CD'].astype(int) // 10).astype(int)
    gdf_dong['Ku']   = (gdf_dong['Dong'] // 100).astype(int)
    
    # 서울시(11xxx) 추출
    seoul_dong = gdf_dong[gdf_dong['Ku'] // 1000 == 11].copy()
    logging.info(f"서울시 원본 행정동 행 수: {len(seoul_dong)}, 고유 Dong 수: {seoul_dong['Dong'].nunique()}")
    
    # EPSG:5179 변환 후 Dong 단위 dissolve
    seoul_dong_5179 = seoul_dong.to_crs(epsg=5179)
    
    # 대표 ADM_NM 및 Ku 추출을 위해 first 집계
    dissolved_dong = seoul_dong_5179.dissolve(
        by='Dong',
        aggfunc={
            'Ku': 'first',
            'ADM_CD': 'first',
            'ADM_NM': 'first'
        },
        as_index=False
    )
    dissolved_dong['ku_name'] = dissolved_dong['Ku'].map(ku_code_name_mapping)
    dissolved_dong['dong_area_sqm'] = dissolved_dong.geometry.area
    
    logging.info(f"Dissolve 후 고유 행정동 수: {len(dissolved_dong)} (목표: 423개)")
    assert len(dissolved_dong) == 423, f"행정동 수가 423개가 아닙니다: {len(dissolved_dong)}"
    
    logging.info("Step 2. 서울시 공식 생활권 경계 로드 및 EPSG:5179 변환...")
    gdf_lz = gpd.read_file(RAW_LZ_SHP, encoding='cp949')
    gdf_lz_5179 = gdf_lz.to_crs(epsg=5179).copy()
    
    # 생활권 식별 컬럼 정리
    if 'fid' in gdf_lz_5179.columns:
        gdf_lz_5179['life_zone_id'] = gdf_lz_5179['fid'].astype(int)
    else:
        gdf_lz_5179['life_zone_id'] = range(1, len(gdf_lz_5179) + 1)
        
    gdf_lz_5179['life_zone_name'] = gdf_lz_5179.get('label_1', gdf_lz_5179.get('LZONE_NM', f"LZ_{gdf_lz_5179['life_zone_id']}"))
    logging.info(f"공식 생활권 수: {len(gdf_lz_5179)} (목표: 116개)")
    
    logging.info("Step 3. 행정동 - 공식 생활권 1:1 매핑 계산 (최대 교차면적 기준)...")
    # Spatial overlay (intersection)
    overlay = gpd.overlay(
        dissolved_dong[['Dong', 'Ku', 'ku_name', 'ADM_NM', 'dong_area_sqm', 'geometry']],
        gdf_lz_5179[['life_zone_id', 'life_zone_name', 'geometry']],
        how='intersection'
    )
    overlay['inter_area_sqm'] = overlay.geometry.area
    overlay['overlap_ratio'] = overlay['inter_area_sqm'] / overlay['dong_area_sqm']
    
    # 각 Dong별로 overlap_ratio(교차면적)가 가장 큰 생활권 1개만 선택 (1:1 보장)
    best_mapping = overlay.sort_values(['Dong', 'inter_area_sqm'], ascending=[True, False]).drop_duplicates(subset=['Dong'], keep='first').copy()
    
    mapping_df = best_mapping[['Dong', 'Ku', 'ku_name', 'ADM_NM', 'life_zone_id', 'life_zone_name', 'overlap_ratio']].copy()
    mapping_df.sort_values(['Ku', 'Dong'], inplace=True)
    
    logging.info(f"1:1 매핑 완료: 행 수={len(mapping_df)}, 고유 Dong={mapping_df['Dong'].nunique()}")
    assert len(mapping_df) == 423, f"매핑 결과가 423개가 아닙니다: {len(mapping_df)}"
    assert mapping_df['Dong'].duplicated().sum() == 0, "매핑 테이블에 중복된 Dong이 존재합니다!"
    
    # 강남구 신사/압구정(1123051) 매핑 확인
    gangnam_51 = mapping_df[mapping_df['Dong'] == 1123051]
    logging.info(f"강남구 1123051 매핑 결과: 생활권={gangnam_51['life_zone_name'].values[0]} (비율={gangnam_51['overlap_ratio'].values[0]:.2%})")
    
    # 생활권 컬럼을 행정동 GeoDataFrame에 결합
    dissolved_dong = dissolved_dong.merge(
        mapping_df[['Dong', 'life_zone_id', 'life_zone_name']],
        on='Dong',
        how='left'
    )
    
    # 'fid'는 GPKG의 OGR 예약어이므로 컬럼명 변경
    if 'fid' in gdf_lz_5179.columns:
        gdf_lz_5179.rename(columns={'fid': 'orig_fid'}, inplace=True)
        
    logging.info("Step 4. 정본 데이터 파일 저장...")
    # 1) GPKG 저장 (EPSG:5179 및 EPSG:4326)
    dong_gpkg_path = os.path.join(OUT_DATA_DIR, "seoul_dong_423_dissolved.gpkg")
    if 'fid' in dissolved_dong.columns:
        dissolved_dong.rename(columns={'fid': 'orig_fid'}, inplace=True)
    dissolved_dong.to_file(dong_gpkg_path, layer='epsg5179', driver='GPKG')
    dissolved_dong.to_crs(epsg=4326).to_file(dong_gpkg_path, layer='epsg4326', driver='GPKG')
    logging.info(f"저장 완료: {dong_gpkg_path}")
    
    lz_gpkg_path = os.path.join(OUT_DATA_DIR, "seoul_official_livingzone_116.gpkg")
    gdf_lz_5179.to_file(lz_gpkg_path, layer='epsg5179', driver='GPKG')
    gdf_lz_5179.to_crs(epsg=4326).to_file(lz_gpkg_path, layer='epsg4326', driver='GPKG')
    logging.info(f"저장 완료: {lz_gpkg_path}")
    
    # 2) 엑셀 및 CSV 저장
    mapping_excel_path = os.path.join(OUT_DATA_DIR, "dong_to_official_livingzone_mapping_423.xlsx")
    mapping_csv_path   = os.path.join(OUT_DATA_DIR, "dong_to_official_livingzone_mapping_423.csv")
    
    with pd.ExcelWriter(mapping_excel_path) as writer:
        mapping_df.to_excel(writer, sheet_name='mapping_423', index=False)
        # 구별 요약 시트
        ku_summary = mapping_df.groupby(['Ku', 'ku_name']).agg(
            n_dongs=('Dong', 'count'),
            n_living_zones=('life_zone_id', 'nunique')
        ).reset_index()
        ku_summary.to_excel(writer, sheet_name='ku_summary', index=False)
        
    mapping_df.to_csv(mapping_csv_path, index=False, encoding='utf-8-sig')
    logging.info(f"저장 완료: {mapping_excel_path}")
    logging.info(f"저장 완료: {mapping_csv_path}")
    
    logging.info("■ [00_공통] 행정동 423개 정제 및 공식 생활권 1:1 매핑 완료.")

if __name__ == '__main__':
    main()
