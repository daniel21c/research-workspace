# -*- coding: utf-8 -*-
"""보건의료 승격 공용: 역산 결과(01_인허가) 구별 집계·좌표율, 공식 통계와 서울/구 비교."""
from pathlib import Path
import numpy as np, pandas as pd
V1 = Path(__file__).resolve().parents[3]
LIC = V1 / '01_인허가'
GU25 = ['종로구','중구','용산구','성동구','광진구','동대문구','중랑구','성북구','강북구','도봉구','노원구','은평구','서대문구','마포구',
        '양천구','강서구','구로구','금천구','영등포구','동작구','관악구','서초구','강남구','송파구','강동구']

def load(fac, y):
    d = pd.read_parquet(LIC / f'{fac}/facilities_{fac}_{y}_01.parquet')
    return add_gu(d)

def add_gu(d):
    """구 = 좌표 기반 adm_dong_cd(SGIS 5자리, 11010=종로…11250=강동) 우선, 없으면 주소의 '서울 …구'. gu_src에 출처 기록."""
    code = {f'11{(i+1)*10:03d}': g for i, g in enumerate(GU25)}
    a = d.adm_dong_cd.astype(str).str[:5].map(code) if 'adm_dong_cd' in d else pd.Series(index=d.index, dtype=object)
    b = d.address.fillna('').str.extract(r'서울(?:특별시|시)?\s*([가-힣]+구)')[0]
    b = b.where(b.isin(GU25))
    d['gu'] = a.fillna(b); d['gu_src'] = np.where(a.notna(), 'adm_dong_cd', np.where(b.notna(), 'address', 'none'))
    d['gu_addr'] = b
    return d

def coverage(d):
    ins = d[d.gu.isin(GU25)]
    g = ins.groupby('gu').lon.apply(lambda s: s.notna().mean())
    return dict(n=len(d), coord_rate=round(float(d.lon.notna().mean()), 4), inside_seoul_rate=round(float(d.inside_seoul.fillna(False).mean()), 4),
                gu_parsed_rate=round(float(d.gu.isin(GU25).mean()), 4), min_gu_coord_rate=round(float(g.min()), 4), min_gu=g.idxmin(),
                n_gu_below85=int((g < 0.85).sum()))

def gu_compare(ours_gu: pd.Series, off: pd.Series):
    """ours_gu: 구 이름 Series(행=시설), off: index=구, 값=공식 수"""
    g = pd.DataFrame({'ours': ours_gu.value_counts().reindex(GU25).fillna(0), 'official': off.reindex(GU25)}).astype(float)
    g['diff'] = g.ours - g.official; g['diff_pct'] = (g['diff'] / g.official.replace(0, np.nan) * 100).round(1)
    ok = g.official.notna()
    st = dict(r=round(float(np.corrcoef(g.ours[ok], g.official[ok])[0, 1]), 4), max_abs_diff=int(g['diff'].abs().max()),
              max_abs_diff_gu=g['diff'].abs().idxmax(), max_abs_pct=float(g.diff_pct.abs().max()),
              gu_within5pct=int((g.diff_pct.abs() <= 5).sum()), gu_within10pct=int((g.diff_pct.abs() <= 10).sum()),
              sum_ours=int(g.ours.sum()), sum_official=int(g.official.sum()))
    return st, g

def pct(a, b):
    return round((a - b) / b * 100, 2) if b else None
