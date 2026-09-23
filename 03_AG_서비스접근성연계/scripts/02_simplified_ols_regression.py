# -*- coding: utf-8 -*-
"""
02_simplified_ols_regression.py

목적:
- Applied Geography(AG) 논문 및 박사논문 제4장 제3절용 단순화 OLS 회귀분석 스크립트.
- 교수님 지도사항 반영:
  1. "분석을 심플하게 가라": 핵심 설명변수는 MAI, Coverage 위주로 구성.
  2. "면적과 Compactness는 Control variable이지 핵심 메시지가 아니다."
  3. "공간모형(Moran's I)은 OLS의 공간의존성 왜곡 여부를 확인하는 검증용으로만 사용."
  4. "MAI가 도달 가능한 대상 기준의 조건부 지표임을 명확히 해석."

분석 모델:
- Model 1 (LZ): LZ_IFR ~ LZ 내부 접근성 (MAI, Coverage) + 통제변수 (면적, 인구밀도)
- Model 2 (LD): LD_IFR ~ LD 내부 접근성 (MAI, Coverage) + 통제변수
- Model 3 (Gap - 핵심): ΔIFR (LD - LZ) ~ Δ접근성 (LD - LZ) + 통제변수
"""

import os
import sys
import logging
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

BASE_DIR = r"D:\Research\00_박사논문_연구체계\03_AG_서비스접근성_연계"
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# 입력 파일 경로
IFR_F = r"D:\Research\1_OUTPUT\community_detection\comparison_gap_leiden_livingzone_2020_vs_2025\comparison_gap_leiden_livingzone_2020_vs_2025_all_metrics.xlsx"
LD_F  = os.path.join(OUTPUT_DIR, r"correct_boundary_v4_2025\LD_merged_v3.csv")
LZ_F  = os.path.join(OUTPUT_DIR, r"correct_boundary_v4_2025\LZ_merged_v3.csv")
CTL_F = os.path.join(OUTPUT_DIR, r"gu_controls_2025_01.csv")

FACILITIES = ['Commercial', 'Education', 'Green', 'Health', 'Recreation', 'Services']
METRICS    = ['MAI_within', 'coverage_within', 'w_dist_within']
WITHIN_COLS = [f'{m}_{f}' for m in METRICS for f in FACILITIES]

def aggregate_to_gu(df_raw, prefix):
    """커뮤니티/생활권 행 -> 자치구 단위 집계 (인구 pop_total 가중평균)"""
    rows = []
    for ku_code, grp in df_raw.groupby('ku_code'):
        row = {'ku_code': ku_code}
        for col in WITHIN_COLS:
            if col in grp.columns:
                valid = grp[['pop_total', col]].dropna(subset=[col])
                if len(valid) > 0 and valid['pop_total'].sum() > 0:
                    row[f'{prefix}_{col}'] = np.average(valid[col], weights=valid['pop_total'])
                else:
                    row[f'{prefix}_{col}'] = np.nan
            else:
                row[f'{prefix}_{col}'] = np.nan
        rows.append(row)
    return pd.DataFrame(rows)

def avg_facilities(df, prefix):
    """6대 시설 평균 산출"""
    for m in METRICS:
        cols = [f'{prefix}_{m}_{f}' for f in FACILITIES if f'{prefix}_{m}_{f}' in df.columns]
        if cols:
            df[f'{prefix}_{m}_avg'] = df[cols].mean(axis=1, skipna=True)
    return df

def run_regression_model(y, X, model_name="Model"):
    """상수항 추가 및 OLS 회귀분석 실행 및 요약 출력"""
    X_const = sm.add_constant(X)
    model = sm.OLS(y, X_const).fit()
    
    # VIF 계산
    vif_data = pd.DataFrame()
    vif_data["feature"] = X_const.columns
    vif_data["VIF"] = [variance_inflation_factor(X_const.values, i) for i in range(len(X_const.columns))]
    
    return model, vif_data

def main():
    logging.info("Step 1. 2025년 단면 IFR 및 접근성 데이터 로드...")
    if not os.path.exists(IFR_F) or not os.path.exists(LD_F) or not os.path.exists(LZ_F):
        logging.error(f"필요한 입력 파일이 누락되었습니다. 경로를 확인하세요.")
        return

    df_ifr = pd.read_excel(IFR_F, usecols=[
        'ku_code', 'ku_name', 'ku_name_en',
        'leiden_2025_internal_flow_ratio',
        'livingzone_2025_internal_flow_ratio'
    ]).rename(columns={
        'leiden_2025_internal_flow_ratio':    'LD_IFR',
        'livingzone_2025_internal_flow_ratio': 'LZ_IFR'
    })
    df_ifr['IFR_gap'] = df_ifr['LD_IFR'] - df_ifr['LZ_IFR']

    df_ld_raw = pd.read_csv(LD_F)
    df_lz_raw = pd.read_csv(LZ_F)
    
    df_ld_acc = aggregate_to_gu(df_ld_raw, 'LD')
    df_lz_acc = aggregate_to_gu(df_lz_raw, 'LZ')
    
    df_ld_acc = avg_facilities(df_ld_acc, 'LD')
    df_lz_acc = avg_facilities(df_lz_acc, 'LZ')

    merged = df_ifr.merge(df_ld_acc, on='ku_code').merge(df_lz_acc, on='ku_code')
    
    # 통제변수 결합 (면적, 인구밀도 등)
    if os.path.exists(CTL_F):
        df_ctl = pd.read_csv(CTL_F)
        ctl_cols = [c for c in ['ku_code', 'area_km2', 'pop_density'] if c in df_ctl.columns]
        if len(ctl_cols) > 1:
            merged = merged.merge(df_ctl[ctl_cols], on='ku_code', how='left')

    # 격차(Gap) 변수 생성
    merged['MAI_gap']      = merged['LD_MAI_within_avg'] - merged['LZ_MAI_within_avg']
    merged['Coverage_gap'] = merged['LD_coverage_within_avg'] - merged['LZ_coverage_within_avg']

    logging.info(f"데이터 결합 완료: N={len(merged)}개 자치구")

    logging.info("Step 2. OLS 회귀분석 실행...")
    
    # Model 1: LZ IFR
    X_lz = merged[['LZ_MAI_within_avg', 'LZ_coverage_within_avg']].copy()
    m_lz, vif_lz = run_regression_model(merged['LZ_IFR'], X_lz, "Model 1 (LZ)")
    logging.info(f"[Model 1: LZ] R-squared: {m_lz.rsquared:.4f}, Adj R-squared: {m_lz.rsquared_adj:.4f}")

    # Model 2: LD IFR
    X_ld = merged[['LD_MAI_within_avg', 'LD_coverage_within_avg']].copy()
    m_ld, vif_ld = run_regression_model(merged['LD_IFR'], X_ld, "Model 2 (LD)")
    logging.info(f"[Model 2: LD] R-squared: {m_ld.rsquared:.4f}, Adj R-squared: {m_ld.rsquared_adj:.4f}")

    # Model 3: Gap Model (핵심)
    X_gap = merged[['MAI_gap', 'Coverage_gap']].copy()
    m_gap, vif_gap = run_regression_model(merged['IFR_gap'], X_gap, "Model 3 (Gap)")
    logging.info(f"[Model 3: Gap] R-squared: {m_gap.rsquared:.4f}, Adj R-squared: {m_gap.rsquared_adj:.4f}")

    # 요약 결과표 생성 및 저장
    results_summary = []
    for model_name, m in [("Model 1 (LZ)", m_lz), ("Model 2 (LD)", m_ld), ("Model 3 (Gap)", m_gap)]:
        for var in m.params.index:
            results_summary.append({
                'Model': model_name,
                'Variable': var,
                'Coef': round(m.params[var], 4),
                'Std_Err': round(m.bse[var], 4),
                't_val': round(m.tvalues[var], 4),
                'p_val': round(m.pvalues[var], 4),
                'R_squared': round(m.rsquared, 4),
                'Adj_R_squared': round(m.rsquared_adj, 4)
            })
            
    df_res = pd.DataFrame(results_summary)
    out_xlsx = os.path.join(OUTPUT_DIR, "ag_simplified_ols_regression_results.xlsx")
    df_res.to_excel(out_xlsx, index=False)
    logging.info(f"회귀분석 결과 저장 완료: {out_xlsx}")
    print(df_res.to_string())

if __name__ == '__main__':
    main()
