# -*- coding: utf-8 -*-
"""11_신뢰도_승격 공통 도우미(읽기 전용으로 기존 모듈 import, 바이트코드 미생성).
- mb(02_명부/_lib), fac(03_교육교통공원상가/_lib) 재사용. API 키는 mb.keys()로만 접근, 출력 금지."""
import sys, re
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V1 = HERE.parents[2]
sys.path.insert(0, str(V1 / '02_명부' / '_lib'))
sys.path.insert(0, str(V1 / '03_교육교통공원상가' / '_lib'))
import mb, fac  # noqa
import pandas as pd, numpy as np
import geopandas as gpd

GU = mb.GU
SGIS = V1.parent / 'SGIS_인구경계_2019_2024' / '03_행정구역'


def gu_of(addr):
    a = mb.clean(addr)
    for g in sorted(GU, key=len, reverse=True):
        if re.search(r'(^|\s|특별시|서울시|서울)' + g + r'(\s|$|\d|[가-힣])', a):
            return g
    return ''


def sgis_dongs(q):
    d = gpd.read_file(SGIS / f'경계_{q}' / f'bnd_dong_00_{q}' / f'bnd_dong_00_{q}.shp', ignore_geometry=True)
    c = [x for x in d.columns if x.endswith('_CD')][0]; n = [x for x in d.columns if x.endswith('_NM')][0]
    d = d.rename(columns={c: 'CD', n: 'NM'}); d = d[d.CD.astype(str).str.startswith('11')].copy()
    s = gpd.read_file(SGIS / f'경계_{q}' / f'bnd_sigungu_00_{q}' / f'bnd_sigungu_00_{q}.shp', ignore_geometry=True)
    s = s[s.SIGUNGU_CD.astype(str).str.startswith('11')]
    d['gu'] = d.CD.astype(str).str[:5].map(dict(zip(s.SIGUNGU_CD.astype(str), s.SIGUNGU_NM)))
    return d


def gu_coverage(df, gu_col='gu', ok=None):
    """자치구별 행 수·좌표 수·좌표율."""
    ok = df['x_5179'].notna() if ok is None else ok
    g = pd.DataFrame({'gu': df[gu_col].values, 'ok': ok.values})
    r = g.groupby('gu').agg(n=('ok', 'size'), coord=('ok', 'sum')).reindex(GU).fillna(0).astype(int)
    r['rate'] = (r.coord / r.n.replace(0, np.nan)).round(4)
    return r


def compare(built, official, label=''):
    """구별 대조: 구축 vs 공식, 차이·상관·최대 편차."""
    t = pd.DataFrame({'built': built, 'official': official}).reindex(GU).fillna(0)
    t['diff'] = t.built - t.official
    t['diff_pct'] = (t['diff'] / t.official.replace(0, np.nan) * 100).round(1)
    corr = float(np.corrcoef(t.built, t.official)[0, 1]) if t.official.std() > 0 and t.built.std() > 0 else None
    return t, dict(label=label, built_total=int(t.built.sum()), official_total=int(t.official.sum()),
                   diff_pct=round((t.built.sum() - t.official.sum()) / t.official.sum() * 100, 2) if t.official.sum() else None,
                   corr=round(corr, 4) if corr is not None else None, max_abs_diff=int(t['diff'].abs().max()),
                   max_abs_gu=str(t['diff'].abs().idxmax()))
