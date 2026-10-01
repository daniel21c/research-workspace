# -*- coding: utf-8 -*-
"""상가(상권)정보 4개 판 비교 (2026-10-01)
판: 20191231·20241231(기존 일상소매 2020_01·2025_01의 원천) + 20201231·20251231(4분기 판, 새로 받음).
원본 zip은 ../raw/ 에서 읽기만 한다. 기존 시설 parquet·extract는 바꾸지 않는다.
산출: summary.json, nation_by_large.csv, seoul_by_large.csv, seoul_retail9.csv, seoul_retail9_by_gu.csv, id_overlap.csv
부산물: ../raw/sbiz_seoul_extract_202012.csv, _202512.csv (build_retail_daily.py extract와 같은 규칙: 9개 소분류 + 의원·병원 Q101·Q102)
실행: python compare_q4.py"""
import zipfile, io, json, re
from pathlib import Path
import pandas as pd, numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / 'raw'
FAC = Path(r'C:\Users\cyion\.codex\tmp\facility-integrity-audit-20260929\isolated_rebuild\서울시설_2020_2025_분석용.parquet')
REL = ['20191231', '20201231', '20241231', '20251231']
CODES = {'G20404': '슈퍼마켓', 'G20405': '편의점', 'G20499': '그 외 기타 종합 소매업', 'G20501': '곡물/곡분 소매업',
         'G20503': '정육점', 'G20504': '건어물/젓갈 소매업', 'G20505': '수산물 소매업', 'G20506': '채소/과일 소매업',
         'G20509': '반찬/식료품 소매업'}
USE = ['상가업소번호', '상호명', '지점명', '상권업종대분류코드', '상권업종대분류명', '상권업종중분류코드', '상권업종중분류명',
       '상권업종소분류코드', '상권업종소분류명', '표준산업분류코드', '시도명', '시군구명', '행정동코드', '행정동명', '지번주소',
       '도로명주소', '건물명', '층정보', '경도', '위도']
EXTRACT_USE = ['상가업소번호', '상호명', '지점명', '상권업종대분류코드', '상권업종중분류코드', '상권업종중분류명', '상권업종소분류코드',
               '상권업종소분류명', '표준산업분류코드', '시군구명', '행정동코드', '행정동명', '지번주소', '도로명주소', '건물명', '층정보', '경도', '위도']
BULK = {'202208', '202410'}


def zname(i):
    if i.flag_bits & 0x800: return i.filename
    try: return i.filename.encode('cp437').decode('cp949', 'replace')
    except UnicodeEncodeError: return i.filename


def csvs(z, prefix=''):
    """zip 안(중첩 zip 포함)의 CSV를 (이름, 파일객체)로 돌려준다."""
    for i in z.infolist():
        n = zname(i)
        if n.lower().endswith('.csv'): yield prefix + n, z.open(i)
        elif n.lower().endswith('.zip'): yield from csvs(zipfile.ZipFile(io.BytesIO(z.read(i))), prefix + n + '!')


def load(rel):
    zp = RAW / f'sbiz_상가상권정보_{rel}.zip'
    parts, names = [], []
    for n, f in csvs(zipfile.ZipFile(zp)):
        d = pd.read_csv(f, dtype=str, usecols=lambda c: c in USE, encoding='utf-8', encoding_errors='replace', low_memory=False)
        d['_file'] = n.split('!')[-1].split('/')[-1]; parts.append(d); names.append(n)
    d = pd.concat(parts, ignore_index=True)
    d['시도명'] = d['시도명'].str.strip()
    return d, names


def issue_ym(s):
    s = s.astype(str); ok = s.str.match(r'^MA01\d{2}\d{6}')
    return s.str[6:12].where(ok)


S, nat_large, seoul_large, seoul9, gu9, ids9 = {}, [], [], [], [], {}
for rel in REL:
    d, names = load(rel)
    ym = issue_ym(d['상가업소번호']); ref = rel[:6]
    seoul = d[d['시도명'] == '서울특별시']
    r9 = seoul[seoul['상권업종소분류코드'].isin(CODES)]
    ids9[rel] = set('SBIZ_' + r9['상가업소번호'])
    ym9 = issue_ym(r9['상가업소번호'])
    S[rel] = dict(files=len(names), nation_rows=len(d), seoul_rows=len(seoul), seoul_retail9=len(r9),
                  dup_id_nation=int(d['상가업소번호'].duplicated().sum()),
                  coord_rate_seoul=float(pd.to_numeric(seoul['경도'], errors='coerce').notna().mean()),
                  large_codes=sorted(d['상권업종대분류코드'].dropna().unique().tolist()),
                  id_issue_after_ref_nation=int((ym > ref).sum()), id_issue_after_ref_seoul9=int((ym9 > ref).sum()),
                  id_nonbulk_seoul9=int((~ym9.isin(BULK) & ym9.notna()).sum()),
                  id_issue_top_seoul9=ym9.value_counts().head(8).to_dict(),
                  id_issue_max_nation=str(ym.max()))
    nat_large.append(d.groupby(['상권업종대분류코드', '상권업종대분류명']).size().rename(rel))
    seoul_large.append(seoul.groupby(['상권업종대분류코드', '상권업종대분류명']).size().rename(rel))
    seoul9.append(r9.groupby('상권업종소분류코드').size().rename(rel))
    gu9.append(r9.groupby('시군구명').size().rename(rel))
    # 4분기 신판은 기존 extract와 같은 규칙으로 서울 추출본을 남긴다
    if rel in ('20201231', '20251231'):
        out = RAW / f'sbiz_seoul_extract_{ref}.csv'
        if not out.exists():
            e = seoul[seoul['상권업종소분류코드'].isin(CODES) | seoul['상권업종중분류코드'].isin(['Q101', 'Q102'])]
            e[[c for c in EXTRACT_USE if c in e.columns]].to_csv(out, index=False, encoding='utf-8-sig')
    print(rel, S[rel]['nation_rows'], S[rel]['seoul_rows'], S[rel]['seoul_retail9'], flush=True)
    del d, seoul

pd.concat(nat_large, axis=1).to_csv(HERE / 'nation_by_large.csv', encoding='utf-8-sig')
pd.concat(seoul_large, axis=1).to_csv(HERE / 'seoul_by_large.csv', encoding='utf-8-sig')
t9 = pd.concat(seoul9, axis=1); t9.insert(0, '소분류명', t9.index.map(CODES)); t9.to_csv(HERE / 'seoul_retail9.csv', encoding='utf-8-sig')
pd.concat(gu9, axis=1).to_csv(HERE / 'seoul_retail9_by_gu.csv', encoding='utf-8-sig')

# 기존 시설 parquet(일상소매)과 대조
a = pd.read_parquet(FAC, columns=['facility_id', 'year', '시설'])
fac = {y: set(a.loc[(a['시설'] == '일상소매') & (a.year == y), 'facility_id']) for y in (2020, 2025)}
S['existing'] = {str(y): len(v) for y, v in fac.items()}
S['existing_matches_release'] = {'2020_vs_20191231': fac[2020] == ids9['20191231'], '2025_vs_20241231': fac[2025] == ids9['20241231']}
rows = []
for a_, b_ in [('20191231', '20201231'), ('20241231', '20251231'), ('20201231', '20251231'), ('20191231', '20241231')]:
    A, B = ids9[a_], ids9[b_]
    rows.append(dict(a=a_, b=b_, n_a=len(A), n_b=len(B), common=len(A & B), only_a=len(A - B), only_b=len(B - A),
                     jaccard=round(len(A & B) / len(A | B), 4)))
pd.DataFrame(rows).to_csv(HERE / 'id_overlap.csv', index=False, encoding='utf-8-sig')
S['id_overlap'] = rows
json.dump(S, open(HERE / 'summary.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(S, ensure_ascii=False, indent=1, default=str))
