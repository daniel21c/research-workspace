"""대규모점포 등 옛 지번주소 표기('구로동 736번지 1   호', '창신동 766호') 보완 파서 → key_parcel2 추가.
법정동명 그대로(행정동명 '수유3동' 등은 그대로 두며 geocoder 응답의 법정동과 일치해야만 채택되므로 자연히 탈락)."""
import re, sys
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent; V1 = next(p for p in Path(__file__).resolve().parents if (p / '01_인허가').exists())
FAC = sys.argv[1]; P = V1 / '11_신뢰도_승격' / FAC / 'raw/geocode_candidates.parquet'
def k2(v):
    if not isinstance(v, str): return ''
    m = re.search(r'서울특별시\s+([가-힣]+구)\s+([가-힣0-9]+(?:동|가|리))\s*(\d+)\s*(?:번지)?\s*(\d+)?\s*호?(?:$|\s|,)', v)
    if not m: return ''
    lot = m[3] + (f'-{m[4]}' if m[4] and m[4] != '0' else '')
    return f'parcel:{m[1]}|{m[2]}|{lot}'
c = pd.read_parquet(P); c['key_parcel2'] = c['지번주소'].map(k2)
c.loc[c.key_parcel2.isin(c.key_parcel), 'key_parcel2'] = ''
c.to_parquet(P, index=False)
print(c[['지번주소', 'key_parcel', 'key_parcel2']][c.key_parcel2 != ''].to_string())
