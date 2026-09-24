# -*- coding: utf-8 -*-
"""민감도: 인허가 역산 수를 몇 가지 정의로 바꿔 국세청 가동사업자 수와 비교(두 시점 동일 규칙).
V0 기본 / V1 같은 이름+주소 중복 1건 / V2 현재 '휴업' 상태 제외 / V3 V1+V2 / V4 같은 건물주소(도로명+건물번호 또는 지번)당 1건(사업자 단위 근사, 참고용)."""
import sys, warnings; warnings.filterwarnings('ignore')
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import cmp_lib as C
sys.path.insert(0, str(C.LIC / '_common')); from lic_common import address_key
fac, NTS = sys.argv[1], {'동물병원': {'2020': 817, '2025': 915}, '안경업': {'2020': 2060, '2025': 2021}}[sys.argv[1]]
OUT = Path(__file__).resolve().parents[2] / fac; rows = []
for y in ('2020', '2025'):
    loc = OUT / f'facilities_{fac}_{y}_01.parquet'
    d = pd.read_parquet(loc) if loc.exists() else C.load(fac, y)
    d['ak'] = d.address.map(address_key); d.loc[d.ak == '', 'ak'] = d.address
    v = {'V0_기본': len(d), 'V1_이름주소중복제거': len(d.drop_duplicates(['name', 'ak'])), 'V2_현재휴업제외': int((d.src_status != '휴업').sum()),
         'V3_V1+V2': len(d[d.src_status != '휴업'].drop_duplicates(['name', 'ak'])), 'V4_건물주소당1(참고)': int(d.ak.nunique())}
    for k, n in v.items():
        rows.append(dict(snapshot=f'{y}_01', variant=k, ours=n, nts=NTS[y], diff_pct=C.pct(n, NTS[y])))
t = pd.DataFrame(rows); t.to_csv(OUT / f'sensitivity_{fac}.csv', index=False, encoding='utf-8-sig')
print(t.pivot(index='variant', columns='snapshot', values='diff_pct'))
