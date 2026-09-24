"""방법 4 민감도: 같은 역산 규칙에서 판정이 흔들릴 수 있는 행을 빼고 서울 합계·구별 대조가 유지되는지 확인.
 A 기준(원 빌드) / B 현재 상태 '휴업' 행 제외(휴업 날짜가 없어 기준일 휴업 여부 판정 불가) /
 C 기준일 이후 '같은 날 20건 이상 일괄 폐업·말소'된 행 제외(실제 폐업이 더 이전일 가능성) / D = B∩C 모두 제외.
사용: python sensitivity.py <시설> → ../<시설>/sensitivity_<시설>.csv"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
sys.argv = sys.argv[:2]
import importlib.util
spec = importlib.util.spec_from_file_location('cmp', HERE / 'compare.py')
src = (HERE / 'compare.py').read_text(encoding='utf-8'); src = src[:src.index('D = {')]   # CFG·load 만 재사용
ns = {'__file__': str(HERE / 'compare.py')}; exec(compile(src, 'compare_cfg', 'exec'), ns)
CFG, load, GU, OUT, FAC = ns['CFG'], ns['load'], ns['GU'], ns['OUT'], ns['FAC']
rows = []
for k, y, Dt in (('2020_01', '2019', '2019-12-31'), ('2025_01', '2024', '2024-12-31')):
    d = load(k)
    e = d.end_date.fillna('')
    cnt = d[e > Dt].groupby('end_date').size(); bulk_dates = set(cnt[cnt >= 20].index)
    flags = {'A_기준': pd.Series(False, index=d.index),
             'B_현재휴업제외': d.src_status.fillna('').str.contains('휴업'),
             'C_사후일괄종료제외': e.isin(bulk_dates) | d.flag_bulk_admin_end.fillna(False)}
    flags['D_B+C제외'] = flags['B_현재휴업제외'] | flags['C_사후일괄종료제외']
    for sc, (flt, ofile, ocols) in CFG[FAC].items():
        off = pd.read_csv(ofile); o = off[off.year == int(y)].set_index('gu')[ocols].sum(axis=1)
        for v, drop in flags.items():
            s = d[flt(d) & ~drop]; b = s.gu.value_counts().reindex(GU, fill_value=0); og = o.reindex(GU)
            pct = 100 * (b - og) / og.replace(0, np.nan)
            rows.append({'scope': sc, 'snapshot': k, 'version': v, 'built': int(len(s)), 'official': int(o['서울합계']),
                         'diff_pct': round(100 * (len(s) - o['서울합계']) / o['서울합계'], 2),
                         'gu_r': round(float(np.corrcoef(b, og)[0, 1]), 4), 'gu_median_abs_pct': round(float(pct.abs().median()), 2),
                         'gu_max_abs_pct': round(float(pct.abs().max()), 2), 'rows_dropped': int((flt(d) & drop).sum())})
r = pd.DataFrame(rows); r.to_csv(OUT / f'sensitivity_{FAC}.csv', index=False, encoding='utf-8-sig')
print(r.to_string())
