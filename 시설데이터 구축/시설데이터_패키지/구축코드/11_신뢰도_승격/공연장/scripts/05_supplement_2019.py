"""민감도용 보완 후보: 2024말 명부에 있고 등록일 ≤ 2019-12-31 인데 2019말 명부에 (이름·주소키 모두) 없는 공연장 → 2020_01 누락 추정."""
import sys
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parents[1]; V1 = HERE.parents[1]
sys.path.insert(0, str(HERE / 'scripts')); sys.path.insert(0, str(V1 / '01_인허가/_common'))
from importlib import import_module; from lic_common import address_key
mo = import_module('01_match_official')
a = pd.read_parquet(HERE / 'facilities_공연장_2020_01.parquet'); b = pd.read_parquet(HERE / 'facilities_공연장_2025_01.parquet')
for d in (a, b): d['nk'] = d.name.map(mo.nk); d['ak'] = d.address_normalized.map(address_key)
old = b[b.reg_date <= '2019-12-31']
s = old[~(old.nk.isin(set(a.nk)) | old.ak.isin(set(a.ak) - {''}))].drop(columns=['nk', 'ak']).copy()
s['year_snapshot'] = '2020_01'; s['scope_flag'] = '보완후보_2024명부_등록일≤2019_2019명부누락'
s['temporal_reason'] = '2024말 명부 행(등록일 ≤ 2019-12-31)을 2020_01 누락 추정으로 차용 — 민감도 전용'
s.to_csv(HERE / 'supplement_공연장_2020_01_명부누락추정.csv', index=False, encoding='utf-8-sig')
print(len(s), s.gu.value_counts().to_dict())
