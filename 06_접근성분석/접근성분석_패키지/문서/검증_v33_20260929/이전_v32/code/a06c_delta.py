# -*- coding: utf-8 -*-
"""연구3 핵심변수 Δ(LD − LZ) 동 값의 유일한 계산 함수 (a06b 요약·a07 표/그림·a10 신뢰성이 같이 쓴다).

정의 (문서/지표정의_확정.md 3.3):
  ΔCOV_종합(d) = COV_종합,ld(d) − COV_종합,lz116(d)                       (COV 종합은 8개 카테고리 모두 값이 있음)
  ΔMAI_종합(d) = mean_{c ∈ K_d} [MAI_c,ld(d) − MAI_c,lz116(d)],  K_d = 두 경계 조건 모두 MAI 값이 있는 카테고리
  MAI 종합(값 있는 카테고리 평균)끼리 바로 빼면 두 경계에서 평균에 들어간 카테고리 묶음이 다를 때(동 약 14~24개)
  서로 다른 대상의 차가 되므로, Δ는 공통 카테고리에서만 계산한다. K_d 가 비면 정의되지 않음(NaN).

2026-09-27: 경계 쌍을 인자로 받는다(pair=(빼이는 쪽, 빼는 쪽), 기본 ('ld', 'lz116')). 연구3 시계열 확장의
ld_other(다른 연도 Leiden) 등 다른 경계 조건에도 같은 규칙을 쓴다.
"""
import pandas as pd

LZ, LD = 'lz116', 'ld'
DEFAULT_PAIR = (LD, LZ)


def _dong(u: pd.DataFrame, year=None, pair=DEFAULT_PAIR) -> pd.DataFrame:
    d = u[(u.unit_level == 'dong424') & (u.b.astype(str).isin(list(pair)))].copy()
    if year is not None:
        d = d[d.year == year]
    d['b'] = d['b'].astype(str)
    if d.duplicated(['unit_id', 'b', 'cat']).any():
        raise ValueError('Select one year/run; duplicate dong-boundary-category rows are ambiguous')
    return d


def dmai_by_category(u: pd.DataFrame, year=None, pair=DEFAULT_PAIR) -> pd.DataFrame:
    """동 × 카테고리(종합 제외)의 MAI_{pair[1]}, MAI_{pair[0]}, dMAI (어느 한쪽이 없으면 dMAI = NaN)."""
    hi, lo = pair
    d = _dong(u, year, pair)
    d = d[d.cat != '종합']
    p = d.pivot_table(index=['unit_id', 'cat'], columns='b', values='MAI', dropna=False)
    p = p.reindex(columns=[lo, hi])
    p['dMAI'] = p[hi] - p[lo]
    return p


def dong_delta(u: pd.DataFrame, col: str, year=None, pair=DEFAULT_PAIR) -> pd.Series:
    """동 424 종합 Δ(pair[0] − pair[1]). col = 'COV' | 'MAI'. 반환: unit_id 색인 Series."""
    hi, lo = pair
    if col == 'MAI':
        p = dmai_by_category(u, year, pair)
        return p['dMAI'].groupby(level='unit_id').mean()          # 공통 카테고리 평균(NaN 건너뜀), 모두 NaN이면 NaN
    d = _dong(u, year, pair)
    d = d[d.cat == '종합']
    p = d.pivot_table(index='unit_id', columns='b', values=col)
    p = p.reindex(columns=[hi, lo])
    return p[hi] - p[lo]


def dmai_common_n(u: pd.DataFrame, year=None, pair=DEFAULT_PAIR) -> pd.Series:
    """동별 ΔMAI 종합에 들어간 공통 카테고리 수 |K_d|."""
    p = dmai_by_category(u, year, pair)
    return p['dMAI'].notna().groupby(level='unit_id').sum().astype(int)


def temporal_dmai_common4(u0, u1, year0=None, year1=None,
                          pair0=DEFAULT_PAIR, pair1=DEFAULT_PAIR):
    """Additional sensitivity: (hi1−lo1)−(hi0−lo0), on categories observed in all 4 cells.

    Does not change dong_delta's approved per-year two-boundary definition.
    Callers must choose fixed/changing network and boundary years explicitly.
    Returns per-dong values and category supports; no common category -> NaN.
    """
    p0=dmai_by_category(u0,year0,pair0)['dMAI']
    p1=dmai_by_category(u1,year1,pair1)['dMAI']
    p=pd.concat([p0.rename('d0'),p1.rename('d1')],axis=1)
    common=p.notna().all(axis=1)
    q=p.where(common)
    means=q.groupby(level='unit_id').mean()
    out=means.rename(columns={'d0':'dMAI_0_common4','d1':'dMAI_1_common4'})
    out['change_common4']=out.dMAI_1_common4-out.dMAI_0_common4
    out['n_common4']=common.groupby(level='unit_id').sum().astype(int)
    out['change_pairwise']=p1.groupby(level='unit_id').mean()-p0.groupby(level='unit_id').mean()
    out['difference']=out.change_common4-out.change_pairwise
    out['categories_common4']=common[common].groupby(level='unit_id').apply(lambda x:'|'.join(x.index.get_level_values('cat'))).reindex(out.index).fillna('')
    return out
