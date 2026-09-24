"""체육시설업: 정의 맞춤 규칙 C(현재 상태가 취소/말소/만료/정지/중지인 행 제외)를 scope_flag 로 표시한 산출본 + 좌표율 점검."""
import re, json
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parents[1]; V1 = HERE.parents[1]; SRC = V1 / '01_인허가/체육시설업'
GU = ['종로구','중구','용산구','성동구','광진구','동대문구','중랑구','성북구','강북구','도봉구','노원구','은평구','서대문구','마포구','양천구','강서구','구로구','금천구','영등포구','동작구','관악구','서초구','강남구','송파구','강동구']
GU_RE = re.compile(r'(?<![가-힣])(' + '|'.join(sorted(GU, key=len, reverse=True)) + r')(?=\s|$|\d)')
gu_of = lambda a: (lambda m: m[1] if m else None)(GU_RE.search(str(a or '')))
summ = {}
for k in ['2020_01', '2025_01']:
    d = pd.read_parquet(SRC / f'facilities_체육시설업_{k}.parquet')
    d['scope_flag'] = d.flag_admin_end.map({True: 'C제외_취소말소상태', False: 'C포함'})
    d['coord_stage'] = d.coord_method.map(lambda m: 'source' if m == 'source' else ('geocode_exact_build' if str(m).startswith('geocode') else 'unresolved'))
    d.to_parquet(HERE / f'facilities_체육시설업_{k}.parquet', index=False); d.to_csv(HERE / f'facilities_체육시설업_{k}.csv', index=False, encoding='utf-8-sig')
    for sc, s in (('전체', d), ('C포함', d[d.scope_flag == 'C포함'])):
        g = s.address.map(gu_of); ok = s.inside_seoul == True; r = ok.groupby(g).mean()
        summ[f'{k}|{sc}'] = dict(n=len(s), coord_rate=round(ok.mean() * 100, 2), min_gu=r.idxmin(), min_gu_rate=round(r.min() * 100, 1),
                                 n_gu_below85=int((r < .85).sum()), gu_missing=int(g.isna().sum()))
json.dump(summ, open(HERE / 'summary_체육시설업.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(summ, ensure_ascii=False, indent=1))
