"""체육시설업 구축본(01_인허가) vs 문체부 「전국 등록·신고 체육시설업 현황」(2019말·2024말) 서울 업종별·구별 대조."""
import re, json
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parents[1]
V1 = HERE.parents[1]
SRC = V1 / '01_인허가/체육시설업'
GU = ['종로구','중구','용산구','성동구','광진구','동대문구','중랑구','성북구','강북구','도봉구','노원구','은평구','서대문구','마포구',
      '양천구','강서구','구로구','금천구','영등포구','동작구','관악구','서초구','강남구','송파구','강동구']
GU_RE = re.compile(r'(?<![가-힣])(' + '|'.join(sorted(GU, key=len, reverse=True)) + r')(?=\s|$|\d)')
def addr_gu(a):
    m = GU_RE.search(str(a or '')); return m[1] if m else None
off = pd.read_csv(HERE / 'raw/mcst_seoul_gu_parsed.csv')
off['snap'] = off.year.map({2019: '2020_01', 2024: '2025_01'})
TOT = off.groupby(['snap', 'subtype']).seoul_total_in_book.first()
SUBS = ['당구장', '체력단련장', '체육도장', '골프연습장', '수영장', '종합체육시설', '빙상장']
SCEN = {'A_전체': lambda d: pd.Series(True, index=d.index),
        'B_일괄말소제외': lambda d: ~d.flag_bulk_admin_end,
        'C_취소말소상태전체제외': lambda d: ~d.flag_admin_end}
rows, gurows = [], []
for k in ['2020_01', '2025_01']:
    d = pd.read_parquet(SRC / f'facilities_체육시설업_{k}.parquet')
    d['gu'] = d.address.map(addr_gu)
    print(k, 'gu 미상:', int(d.gu.isna().sum()))
    for sc, f in SCEN.items():
        s = d[f(d)]
        for excl_jung in (False, True):
            ss = s[s.gu != '중구'] if excl_jung else s
            for t in SUBS + ['7업종합계']:
                b = len(ss) if t == '7업종합계' else int((ss.facility_subtype == t).sum())
                if t == '7업종합계':
                    o = sum(TOT[(k, x)] for x in SUBS)
                    oj = off[(off.snap == k) & (off.gu == '중구') & off.subtype.isin(SUBS)].official_n.fillna(0).sum()
                else:
                    o = TOT[(k, t)]; oj = off[(off.snap == k) & (off.gu == '중구') & (off.subtype == t)].official_n.fillna(0).sum()
                o2 = o - oj if excl_jung else o
                rows.append(dict(snapshot=k, scenario=sc, excl_junggu=excl_jung, subtype=t, built=b, official=int(o2),
                                 diff=b - int(o2), diff_pct=round((b - o2) / o2 * 100, 2)))
        # 구별
        for t in SUBS + ['7업종합계']:
            sb = s if t == '7업종합계' else s[s.facility_subtype == t]
            bg = sb.gu.value_counts()
            og = off[(off.snap == k) & (off.subtype.isin(SUBS) if t == '7업종합계' else (off.subtype == t))].groupby('gu').official_n.sum(min_count=1)
            for g in GU:
                gurows.append(dict(snapshot=k, scenario=sc, subtype=t, gu=g, built=int(bg.get(g, 0)),
                                   official=(None if pd.isna(og.get(g, np.nan)) else int(og.get(g)))))
cmp_ = pd.DataFrame(rows); gcmp = pd.DataFrame(gurows)
gcmp['official_method'] = np.where(gcmp.subtype.isin(['당구장', '체력단련장', '체육도장']), '책자 구별표', '책자 업소목록 소재지 구 토큰 계수')
gcmp.loc[gcmp.subtype == '7업종합계', 'official_method'] = '혼합(구별표+목록계수)'
cmp_.to_csv(HERE / 'official_compare_체육시설업.csv', index=False, encoding='utf-8-sig')
gcmp.to_csv(HERE / 'official_compare_체육시설업_구별.csv', index=False, encoding='utf-8-sig')
# 구별 통계
st = []
for (k, sc, t), g in gcmp.groupby(['snapshot', 'scenario', 'subtype']):
    g = g[g.official.notna() & (g.official > 0)]
    if len(g) < 5: continue
    dp = (g.built - g.official) / g.official * 100
    st.append(dict(snapshot=k, scenario=sc, subtype=t, n_gu=len(g), pearson_r=round(np.corrcoef(g.built, g.official)[0, 1], 4),
                   max_abs_diff_pct=round(dp.abs().max(), 1), max_gu=g.gu.iloc[int(dp.abs().values.argmax())],
                   n_gu_within5=int((dp.abs() <= 5).sum()), n_gu_within10=int((dp.abs() <= 10).sum())))
st = pd.DataFrame(st); st.to_csv(HERE / 'official_compare_체육시설업_구별요약.csv', index=False, encoding='utf-8-sig')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
print(cmp_.pivot_table(index=['subtype'], columns=['snapshot', 'scenario', 'excl_junggu'], values='diff_pct'))
print(st[st.subtype.isin(['7업종합계', '당구장', '체력단련장', '체육도장', '골프연습장'])])
