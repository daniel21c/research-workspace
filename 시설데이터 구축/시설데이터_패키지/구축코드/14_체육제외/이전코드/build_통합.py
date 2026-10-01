# -*- coding: utf-8 -*-
"""../데이터/시설별/ 32개 시설 폴더(신뢰도 상; 일상소매 제외) → ../데이터/통합_신뢰도상_2020_2025.parquet (csv 사본은 OUT_CSV=1일 때만)
공통 20열 + '시설'(폴더 이름). 규모변수 sz_*와 시설별 추가 열은 개별 파일 참조.
환경변수 FAC_OVERRIDE_DIR가 있으면 그 아래 같은 상대경로 파일을 우선 사용(보정본 시험용). OUT_DIR로 출력 위치 변경.
실행: python build_통합.py"""
import os, glob
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 시설데이터_패키지
T = os.environ.get('FAC_T_DIR') or os.path.join(PKG, '데이터', '시설별')
OV = os.environ.get('FAC_OVERRIDE_DIR', '')
OUT = os.environ.get('OUT_DIR') or os.path.join(PKG, '데이터')
COLS = ['facility_id', 'category_group', 'facility_type', 'facility_subtype', 'year_snapshot', 'name', 'address', 'lon', 'lat', 'x_5179',
        'y_5179', 'coord_method', 'grade', 'source_org', 'source_dataset', 'source_reference_date', 'inside_seoul', 'adm_dong_cd', 'oa_cd', 'grid100_cd']


def pick(k, y):
    if OV:
        f = glob.glob(os.path.join(OV, k, f'facilities_*_{y}_01.parquet'))
        if f: return f[0]
    f = glob.glob(os.path.join(T, k, f'facilities_*_{y}_01.parquet')); assert len(f) == 1, (k, y, f)
    return f[0]


L = []
for d0 in sorted(glob.glob(os.path.join(T, '*'))):
    k = os.path.basename(d0)
    if not os.path.isdir(d0) or k.startswith('_'): continue
    for y in ['2020', '2025']:
        d = pd.read_parquet(pick(k, y))
        d = d[[c for c in COLS if c in d.columns]].copy(); d['시설'] = k; L.append(d)
a = pd.concat(L, ignore_index=True)
for c in ['lon', 'lat', 'x_5179', 'y_5179']: a[c] = pd.to_numeric(a[c], errors='coerce')
a['inside_seoul'] = a.inside_seoul.astype(str).isin(['True', '1', 'true'])
for c in a.columns:
    if a[c].dtype == object or str(a[c].dtype) == 'str': a[c] = a[c].astype('string')
a.to_parquet(os.path.join(OUT, '통합_신뢰도상_2020_2025.parquet'), index=False)
if os.environ.get('OUT_CSV'): a.to_csv(os.path.join(OUT, '통합_신뢰도상_2020_2025.csv'), index=False, encoding='utf-8-sig')
print(len(a), a['시설'].nunique())
