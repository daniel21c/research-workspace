# -*- coding: utf-8 -*-
"""
02_check_facility_availability.py

목적:
- 교수님 지침(26.09.21): "2020·2025 공통 시설자료 직접 구축하지 말고 어디까지 입수 가능한지만 일단 정리.
  소상공인 상가정보, 도로명주소/건물 DB, 병원 등 과거자료 확보가 가능한 시설 조사."
- 로컬 D 드라이브 및 공공 데이터 소스에서 2020년과 2025년 시점 공통 확보 가능한 시설 데이터 현황 점검 보고서 작성.
"""

import os
import sys
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

BASE_DIR = r"D:\Research"
OUT_DIR  = os.path.join(BASE_DIR, r"00_박사논문_연구체계\04_KPA_시계열_불일치진단\output")

def check_local_facility_files():
    """로컬 D 드라이브 내 시설 데이터 현황 점검"""
    candidates = [
        (r"0_RAW\110m_cultural", "문화시설 격자 데이터"),
        (r"1_OUTPUT\community_detection\OD 데이터(승훈이데이터)\Public_data", "승훈 공공데이터 parquet (2025 단면)"),
        (r"999_논문\전국도서관표준데이터.csv", "전국 공공도서관 데이터"),
        (r"999_논문\국토학회_시계열비교\승훈이 자료", "국토학회 시계열 승훈 자료")
    ]
    
    status_list = []
    for rel_path, desc in candidates:
        full_path = os.path.join(BASE_DIR, rel_path)
        exists = os.path.exists(full_path)
        size_str = f"{os.path.getsize(full_path):,} bytes" if exists and os.path.isfile(full_path) else ("존재 (폴더)" if exists else "미존재")
        status_list.append({
            '데이터 구분': desc,
            '경로': rel_path,
            '존재여부': 'O' if exists else 'X',
            '비고': size_str
        })
    return pd.DataFrame(status_list)

def get_facility_time_series_assessment():
    """2020 vs 2025 시계열 시설자료 가용성 종합 평가"""
    assessments = [
        {
            '시설 유형': '공공도서관',
            '데이터 출처': '공공데이터포털 (전국도서관표준데이터)',
            '2020년 확보': '가능 (개관일자 필터링으로 2020년 시점 복원 가능)',
            '2025년 확보': '가능 (최신 데이터)',
            '시계열 일관성': '높음',
            '추천 여부': '적극 추천'
        },
        {
            '시설 유형': '병의원 / 약국',
            '데이터 출처': '건강보험심사평가원 (병원/약국 개설일자 DB)',
            '2020년 확보': '가능 (개설일자 및 폐업일자 기반 복원 가능)',
            '2025년 확보': '가능 (최신 데이터)',
            '시계열 일관성': '높음',
            '추천 여부': '추천'
        },
        {
            '시설 유형': '소상공인 상가정보',
            '데이터 출처': '소상공인시장진흥공단 (분기별 상가업소 DB)',
            '2020년 확보': '가능 (공공데이터포털 2020년 4분기/1분기 파일)',
            '2025년 확보': '가능 (2025년 최신 분기 파일)',
            '시계열 일관성': '중간 (표준산업분류 변경 및 수집방식 변경 영향)',
            '추천 여부': '신중 검토'
        },
        {
            '시설 유형': '도로명주소 / 건물 DB',
            '데이터 출처': '도로명주소 전자지도 (건물군)',
            '2020년 확보': '어려움 (과거 시점 전자지도는 별도 공문 신청 필요)',
            '2025년 확보': '가능 (현재 최신 DB)',
            '시계열 일관성': '낮음',
            '추천 여부': '비추천'
        }
    ]
    return pd.DataFrame(assessments)

def main():
    logging.info("Step 1. 로컬 보관 시설자료 점검...")
    df_local = check_local_facility_files()
    
    logging.info("Step 2. 2020-2025 시계열 시설 DB 가용성 평가...")
    df_eval = get_facility_time_series_assessment()
    
    out_path = os.path.join(OUT_DIR, "facility_availability_assessment_2020_2025.xlsx")
    with pd.ExcelWriter(out_path) as writer:
        df_local.to_excel(writer, sheet_name='로컬보관현황', index=False)
        df_eval.to_excel(writer, sheet_name='시계열구축평가', index=False)
        
    logging.info(f"시설 가용성 평가 보고서 저장 완료: {out_path}")
    print(df_eval.to_string())

if __name__ == '__main__':
    main()
