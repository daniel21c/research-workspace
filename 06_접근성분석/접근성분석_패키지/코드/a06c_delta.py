# -*- coding: utf-8 -*-
"""연구3 핵심변수 Δ(LD − LZ) 동 값의 유일한 계산 함수 (a06b 요약·a07 표/그림·a10 신뢰성이 같이 쓴다).

정의 (문서/지표정의_확정.md 3.3):
  ΔCOV_종합(d) = COV_종합,ld(d) − COV_종합,lz116(d)                       (COV 종합은 8개 카테고리 모두 값이 있음)
  ΔMAI_종합(d) = mean_{c ∈ K_d} [MAI_c,ld(d) − MAI_c,lz116(d)],  K_d = 두 경계 조건 모두 MAI 값이 있는 카테고리
  MAI 종합(값 있는 카테고리 평균)끼리 바로 빼면 두 경계에서 평균에 들어간 카테고리 묶음이 다를 때(동 약 14~24개)
  서로 다른 대상의 차가 되므로, Δ는 공통 카테고리에서만 계산한다. K_d 가 비면 정의되지 않음(NaN).
"""
import pandas as pd

LZ, LD = 'lz116', 'ld'


def _dong(u: pd.DataFrame, year=None) -> pd.DataFrame:
    d = u[(u.unit_level == 'dong424') & (u.b.astype(str).isin([LZ, LD]))].copy()
    if year is not None:
        d = d[d.year == year]
    d['b'] = d['b'].astype(str)
    return d


def dmai_by_category(u: pd.DataFrame, year=None) -> pd.DataFrame:
    """동 × 카테고리(종합 제외)의 MAI_lz116, MAI_ld, dMAI (어느 한쪽이 없으면 dMAI = NaN)."""
    d = _dong(u, year)
    d = d[d.cat != '종합']
    p = d.pivot_table(index=['unit_id', 'cat'], columns='b', values='MAI', dropna=False)
    p = p.reindex(columns=[LZ, LD])
    p['dMAI'] = p[LD] - p[LZ]
    return p


def dong_delta(u: pd.DataFrame, col: str, year=None) -> pd.Series:
    """동 424 종합 Δ(LD − LZ). col = 'COV' | 'MAI'. 반환: unit_id 색인 Series."""
    if col == 'MAI':
        p = dmai_by_category(u, year)
        return p['dMAI'].groupby(level='unit_id').mean()          # 공통 카테고리 평균(NaN 건너뜀), 모두 NaN이면 NaN
    d = _dong(u, year)
    d = d[d.cat == '종합']
    p = d.pivot_table(index='unit_id', columns='b', values=col)
    return p[LD] - p[LZ]


def dmai_common_n(u: pd.DataFrame, year=None) -> pd.Series:
    """동별 ΔMAI 종합에 들어간 공통 카테고리 수 |K_d|."""
    p = dmai_by_category(u, year)
    return p['dMAI'].notna().groupby(level='unit_id').sum().astype(int)
