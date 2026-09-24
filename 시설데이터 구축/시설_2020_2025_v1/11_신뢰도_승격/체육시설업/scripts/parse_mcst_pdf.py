"""문체부 「전국 등록·신고 체육시설업 현황」 PDF(2019말·2024말) → 서울 업종별·구별 업소수.
- 체력단련장·당구장: 책자 내 구별 표 직접 파싱
- 그 외 업종: 세부현황(업소 목록) 소재지의 자치구 토큰 계수 → 합계와 일치 검사
"""
import re, subprocess, json
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parents[1]; RAW = HERE / 'raw'
GU = ['종로구','중구','용산구','성동구','광진구','동대문구','중랑구','성북구','강북구','도봉구','노원구','은평구','서대문구','마포구',
      '양천구','강서구','구로구','금천구','영등포구','동작구','관악구','서초구','강남구','송파구','강동구']
CFG = {'2019': dict(pdf='mcst_체육시설업현황_2019말.pdf', pages=(75, 211)),
       '2024': dict(pdf='mcst_체육시설업현황_2024말.pdf', pages=(80, 280))}
SEC = {'빙상장업':'빙상장','종합체육시설업':'종합체육시설','수영장업':'수영장','체육도장업':'체육도장','골프연습장업':'골프연습장',
       '체력단련장업':'체력단련장','당구장업':'당구장','가상체육시설업':'가상체험체육시설(골프·야구)'}
BOOK_TOTAL = {'2019': {'빙상장': 13, '종합체육시설': 91, '수영장': 125, '체육도장': 2173, '골프연습장': 1838, '체력단련장': 2524, '당구장': 3273},
              '2024': {'빙상장': 22, '종합체육시설': 99, '수영장': 129, '체육도장': 2349, '골프연습장': 1411, '체력단련장': 3987, '당구장': 2513,
                       '가상체험체육시설(골프·야구)': 896}}   # 책자 '서울 총괄현황(2) 신고체육시설업' 표(2019: p.72-73, 2024: p.70-71)
GU_RE = re.compile(r'(?<![가-힣])(' + '|'.join(sorted(GU, key=len, reverse=True)) + r')(?=\s)')
out = []
for yr, c in CFG.items():
    txt = subprocess.run(['pdftotext', '-layout', '-f', str(c['pages'][0]), '-l', str(c['pages'][1]), str(RAW / c['pdf']), '-'],
                         capture_output=True, text=True).stdout
    txt = txt.split('부 산 광 역 시')[0]
    parts = re.split(r'\n\s*\((?:가|나|다|라|마|바|사|아|자|차|카|타|파|하)\)\s*([가-힣]+업)\s*\n', txt)
    # 첫 '(가) 골프장업'(등록) 이후 신고 섹션
    for name, body in zip(parts[1::2], parts[2::2]):
        if name not in SEC:
            continue
        t = SEC[name]
        total = BOOK_TOTAL[yr][t]
        if t in ('체력단련장', '당구장', '체육도장'):
            cnt = {}; notes = []
            blocks = re.split(r'\n\s*[○◦]\s*', body) if t == '체육도장' else [body]
            blocks = [b for b in blocks if re.search(r'합\s*계', b)]
            if t == '체육도장':
                total = 0
            for b in blocks:
                bt = int(re.search(r'합\s*계\s+([\d,]+)', b)[1].replace(',', ''))
                bc = {}; dup = []
                for line in b.splitlines():
                    mm = re.match(r'^\s*([가-힣](?:\s*[가-힣]){0,4}\s*구)\s+([\d,]+)', line)
                    if mm:
                        g = re.sub(r'\s+', '', mm[1])
                        if g in GU:
                            if g in bc: dup.append(g)
                            bc[g] = int(mm[2].replace(',', ''))
                if t == '체육도장':
                    total += bt
                if sum(bc.values()) != bt or dup:
                    notes.append(f"block_total={bt} parsed={sum(bc.values())} dup={dup} head={b.strip()[:6]}")
                for g, v in bc.items():
                    cnt[g] = cnt.get(g, 0) + v
            method = 'gu_table'
            if notes: print(yr, t, notes)
        else:
            cnt = {g: 0 for g in GU}
            for g in GU_RE.findall(body):
                cnt[g] += 1
            method = 'listing_gu_token_count'
        s = sum(cnt.values())
        for g in GU:
            out.append(dict(year=yr, subtype=t, gu=g, official_n=cnt.get(g, 0 if method != 'gu_table' else None), method=method,
                            seoul_total_in_book=total, sum_parsed=s))
df = pd.DataFrame(out)
df.to_csv(HERE / 'raw' / 'mcst_seoul_gu_parsed.csv', index=False, encoding='utf-8-sig')
print(df.groupby(['year', 'subtype']).agg(total=('seoul_total_in_book', 'first'), parsed=('sum_parsed', 'first'), method=('method', 'first'),
                                          missing_gu=('official_n', lambda x: int(x.isna().sum()))))
