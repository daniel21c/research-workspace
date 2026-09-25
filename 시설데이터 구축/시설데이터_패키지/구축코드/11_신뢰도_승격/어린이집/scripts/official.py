# -*- coding: utf-8 -*-
"""공식 보육통계(서울 자치구×유형, 12.31 기준) 추출 → raw/official_보육통계_서울_구유형_2019_2024.csv
2019: 보건복지부 2019년 보육통계 xlsx 시트 '6'(가-1. 어린이집현황(시군구), 2019.12.31 현재)
2024: 교육부 2024년 보육통계 pdf 가-1. 어린이집 현황(시･군･구) (2024.12.31 현재)
보조: 서울시 보육통계 OA-15457(연말 자치구×유형)."""
import sys, re, subprocess
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; FD = HERE.parent; RAW = FD / 'raw'
sys.path.insert(0, str(FD / '_lib')); import u11
import pandas as pd, openpyxl
GU = u11.GU
T = ['계', '국공립', '사회복지법인', '법인·단체등', '민간', '가정', '협동', '직장']


def y2019():
    wb = openpyxl.load_workbook(RAW / '보육통계_2019_20191231.xlsx', read_only=True, data_only=True)
    rows = [list(r) for r in wb['6'].iter_rows(values_only=True)]
    k = next(i for i, r in enumerate(rows) if r[0] and '서울' in str(r[0]))
    out = []
    for r in rows[k:k + 26]:
        g = '서울합계' if '소' in str(r[1]) else str(r[1]).strip()
        out.append(dict(year=2019, ref_date='2019-12-31', gu=g, **{t: int(v) for t, v in zip(T, r[2:10])}))
    return out


def y2024():
    txt = subprocess.run(['pdftotext', '-layout', str(RAW / '보육통계_2024_교육부.pdf'), '-'], capture_output=True).stdout.decode('utf-8', 'ignore')
    lines = txt.splitlines()
    i0 = next(i for i, l in enumerate(lines) if '가-1. 어린이집 현황' in l and '···' not in l)
    out = []; seen = set()
    m = re.search(r'서울특별시\s+([\d,]+(?:\s+[\d,]+){7})', txt)
    out.append(dict(year=2024, ref_date='2024-12-31', gu='서울합계', **{t: int(v.replace(',', '')) for t, v in zip(T, m.group(1).split())}))
    for l in lines[i0:i0 + 200]:
        mm = re.search(r'(?:^|\s)(' + '|'.join(sorted(GU, key=len, reverse=True)) + r')\s+([\d,]+(?:\s+[\d,]+){7})\s*$', l)
        if mm and mm.group(1) not in seen:
            seen.add(mm.group(1))
            out.append(dict(year=2024, ref_date='2024-12-31', gu=mm.group(1), **{t: int(v.replace(',', '')) for t, v in zip(T, mm.group(2).split())}))
        if len(seen) == 25:
            break
    return out


def oa15457():
    d = pd.read_csv(RAW / 'seoul_OA-15457_보육통계_어린이집현황_자치구유형별.csv', encoding='cp949', dtype=str)
    d = d[d['통계연도'].isin(['2019', '2024'])]
    m = {'시설수합계': '계', '어린이집수_국공립': '국공립', '어린이집수_사회복지법인': '사회복지법인', '어린이집수_법인단체등': '법인·단체등',
         '어린이집수_민간': '민간', '어린이집수_가정': '가정', '어린이집수_부모협동': '협동', '어린이집수_직장': '직장'}
    d = d.rename(columns=m)
    for c in m.values():
        d[c] = pd.to_numeric(d[c])
    d['gu'] = d['자치구명'].map(lambda s: '서울합계' if s in ('소계', '합계', '서울시') else next((g for g in GU if g[:-1] == s or g == s), s))
    return d


if __name__ == '__main__':
    o = pd.DataFrame(y2019() + y2024())
    assert (o.groupby('year').gu.nunique() == 26).all(), o.groupby('year').gu.nunique()
    for y in (2019, 2024):
        s = o[(o.year == y) & (o.gu != '서울합계')][T].sum(); t = o[(o.year == y) & (o.gu == '서울합계')][T].iloc[0]
        assert (s.values == t.values).all(), (y, s, t)
    o['source'] = o.year.map({2019: '보건복지부 2019년 보육통계 가-1(시군구) 2019.12.31 현재', 2024: '교육부 2024년 보육통계 가-1(시･군･구) 2024.12.31 현재'})
    o.to_csv(RAW / 'official_보육통계_서울_구유형_2019_2024.csv', index=False, encoding='utf-8-sig')
    a = oa15457()
    chk = a.merge(o, left_on=[a['통계연도'].astype(int), 'gu'], right_on=['year', 'gu'], suffixes=('_oa', '_rep'))
    print('OA-15457 vs 보고서 불일치 셀 수:', int(sum((chk[t + '_oa'] != chk[t + '_rep']).sum() for t in T)), '/ rows', len(chk))
    print(o[o.gu == '서울합계'].to_string())
