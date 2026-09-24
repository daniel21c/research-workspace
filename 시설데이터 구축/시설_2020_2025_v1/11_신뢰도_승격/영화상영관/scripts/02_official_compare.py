"""영화상영관: 구축본(상영관·극장 단위) vs 영진위 『한국 영화산업 결산』 서울 극장·스크린 수 + KOBIS 현재 목록 기반 구별 참고 비교."""
import sys, re, json
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parents[1]; V1 = HERE.parents[1]; SRC = V1 / '01_인허가/영화상영관'
sys.path.insert(0, str(HERE / 'scripts'))
from importlib import import_module
km = import_module('01_kobis_match')
OFF = {'2020_01': dict(theaters=90, screens=591, seats=97232, src='KOFIC 연구 2020-05 「2019년 한국 영화산업 결산」 <표58> 2019년 지역별 극장, 스크린 수 (2019.12.31 기준)'),
       '2025_01': dict(theaters=90, screens=572, seats=87457, src='KOFIC 연구 2025-02 「2024년 한국 영화산업 결산」 <표41> 2024년 지역별 극장 수, 스크린 수, 좌석 수 (2024.12.31 기준, 휴·폐관 제외)')}
rows = []; m = pd.read_csv(HERE / 'kobis_match_영화상영관.csv')
for k, o in OFF.items():
    t = pd.read_parquet(SRC / f'facilities_영화상영관_극장단위_{k}.parquet'); s = pd.read_parquet(SRC / f'facilities_영화상영관_{k}.parquet')
    for unit, b, off in (('극장', len(t), o['theaters']), ('스크린(상영관)', len(s), o['screens'])):
        rows.append(dict(snapshot=k, scope='A_구축본 전체', unit=unit, built=b, official=off, diff=b - off, diff_pct=round((b - off) / off * 100, 2), official_source=o['src']))
    mm = m[m.snapshot == k]
    live = mm[mm.kobis_stat.fillna('').str.contains('영업|휴업')]
    if k == '2025_01':   # KOBIS 상태는 2026-09 조회 시점 → 2025_01에만 근사 적용(참고)
        for unit, b, off in (('극장', len(live), o['theaters']), ('스크린(상영관)', int(live.screens.sum()), o['screens'])):
            rows.append(dict(snapshot=k, scope='S_참고: KOBIS 현재 영업·휴업과 매칭된 극장만', unit=unit, built=b, official=off, diff=b - off,
                             diff_pct=round((b - off) / off * 100, 2), official_source=o['src']))
c = pd.DataFrame(rows); c.to_csv(HERE / 'official_compare_영화상영관.csv', index=False, encoding='utf-8-sig'); print(c.drop(columns='official_source').to_string())
# 구별 참고: KOBIS 목록(개관일<=2024-12-31, 현재 영업/휴업) vs 구축 2025 극장 수
k = km.load_kobis(); kk = k[(k['개관일'] <= '2024-12-31') & k['영업상태'].isin(['영업', '휴업'])]
t = pd.read_parquet(SRC / 'facilities_영화상영관_극장단위_2025_01.parquet'); t['gu'] = t.address.map(km.gu_of)
g = pd.DataFrame({'built_2025': t.gu.value_counts(), 'kobis_proxy_2024말': kk['기초단체'].value_counts()}).fillna(0).astype(int)
g['diff'] = g.built_2025 - g.kobis_proxy_2024말; g.index.name = 'gu'; g.to_csv(HERE / 'gu_compare_영화상영관_KOBIS참고.csv', encoding='utf-8-sig')
print(g.sort_values('diff').to_string()); print('KOBIS proxy total', len(kk), 'r', round(np.corrcoef(g.built_2025, g.kobis_proxy_2024말)[0, 1], 3))
# 좌표율
for kx in OFF:
    for nm in ('facilities_영화상영관', 'facilities_영화상영관_극장단위'):
        d = pd.read_parquet(SRC / f'{nm}_{kx}.parquet'); d['gu'] = d.address.map(km.gu_of); ok = d.inside_seoul == True; r = ok.groupby(d.gu).mean()
        print(kx, nm, len(d), round(ok.mean() * 100, 1), r.idxmin(), round(r.min() * 100, 1), int((r < .85).sum()), d.loc[~ok, ['name', 'address']].values.tolist())
