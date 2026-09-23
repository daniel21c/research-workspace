# -*- coding: utf-8 -*-
"""
common_flow_loader.py

목적:
- 2020년 및 2025년 서울 생활이동데이터를 일관된 필터링 기준(09~21시, 비통근/비통학)으로 로드하고,
  자치구별 내부통행(internal) 및 유출입통행(ifr)을 제공하는 표준 공통 모듈.
- 사전 전처리된 pkl 파일(D:\\Research\\1_OUTPUT\\0_preprocessed_data)을 최우선 활용하여 고속 로딩.
"""

import os
import gc
import pickle
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

BASE_DIR = r"D:\Research"
PRE_DIR  = os.path.join(BASE_DIR, r"1_OUTPUT\0_preprocessed_data")

def get_movement_pkl_path(year_str):
    """연도별 사전 전처리 pkl 경로 반환"""
    return os.path.join(PRE_DIR, f"preprocessed_movement_data_{year_str}_01.pkl")

def load_filtered_movement_data(year_str):
    """
    지정된 연도의 서울 생활이동데이터를 로드하고 일상생활 통행 필터링을 적용합니다.
    
    필터링 기준:
    1. 요일: 전체 요일 (day 0~6, 월~일)
    2. 시간대: 주간 09:00~21:00 (도착시간 9~20시)
    3. 통행유형: 비통근·비통학 통행 (이동유형 != 'HW' and != 'WH')
    4. 공간범위: 서울 시내 통행 (ku_O, ku_D 모두 11xxx)
    """
    pkl_path = get_movement_pkl_path(year_str)
    if not os.path.exists(pkl_path):
        raise FileNotFoundError(f"전처리 이동데이터 pkl을 찾을 수 없습니다: {pkl_path}")
        
    logging.info(f"[{year_str}] 생활이동데이터 pkl 로드 중... ({pkl_path})")
    with open(pkl_path, 'rb') as f:
        df = pickle.load(f)
    logging.info(f"[{year_str}] 원본 로드 완료: {len(df):,}건")
    
    # 시간 필터
    df['도착시간'] = pd.to_numeric(df['도착시간'], errors='coerce')
    df.dropna(subset=['도착시간'], inplace=True)
    df['도착시간'] = df['도착시간'].astype(int)
    
    # 일상생활통행 필터 (주간 09~20시, HW/WH 제외)
    mask = (
        (df['도착시간'].between(9, 20)) &
        (~df['이동유형'].isin(['HW', 'WH'])) &
        (df['ku_O'] // 1000 == 11) &
        (df['ku_D'] // 1000 == 11)
    )
    df_filtered = df[mask].copy()
    logging.info(f"[{year_str}] 일상통행 필터링 완료: {len(df_filtered):,}건 (원데이터 대비 {len(df_filtered)/len(df):.1%})")
    
    del df
    gc.collect()
    return df_filtered

def get_ku_subsets(df_filtered, ku_code):
    """
    특정 자치구(ku_code)에 대한:
    1. 완전 내부통행 (O와 D가 모두 해당 구)
    2. 유출입 통행 (O 또는 D가 해당 구 - IFR 산출용)
    을 분리하여 반환합니다.
    """
    df_internal = df_filtered[(df_filtered['ku_O'] == ku_code) & (df_filtered['ku_D'] == ku_code)].copy()
    df_ifr      = df_filtered[(df_filtered['ku_O'] == ku_code) | (df_filtered['ku_D'] == ku_code)].copy()
    return df_internal, df_ifr
