# -*- coding: utf-8 -*-
"""장애인복지시설: 일람표 앞머리 '총괄표'(서울 행)와 명부 행수 대조, 기준일 확인, 범위(이용시설) 규칙, 좌표·구 보완.
공식 총괄표 값:
 - 2020년 일람표(2020.7 발간) p3~5 '장애인 거주시설 총괄표(2019.12)', '지역사회재활시설 및 의료재활시설 총괄표(2019.12.)',
   '장애인직업재활시설 총괄표(2019.12.)' — 표가 이미지라 페이지를 렌더링(raw/_render)해 서울 행을 판독·입력.
 - 2025년 일람표 p3~5 '...총괄표(2024.12)' — pdftotext로 추출.
원본(02_명부/장애인복지시설)은 읽기만."""
import sys, json, re
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; FD = HERE.parent
sys.path.insert(0, str(FD / '_lib')); import u11, geo11
import pandas as pd
V1 = u11.V1; GU = u11.GU
SRC = V1 / '02_명부' / '장애인복지시설'
# 총괄표 서울 행 (시설수)
OFF = {2019: {'거주/지체': 2, '거주/시각': 3, '거주/청각': 1, '거주/지적': 15, '거주/중증': 25, '거주/장애영유아': 2, '거주/단기': 43, '거주/공동생활가정': 190,
              '지역/장애인복지관': 49, '지역/주간보호·주간이용': 128, '지역/체육시설': 7, '지역/수어통역센터': 26, '지역/생활이동지원·시각장애인등생활지원': 1,
              '지역/점자도서관': 2, '지역/점자도서·녹음서출판': 1, '지역/수련시설': 1, '지역/재활치료시설': 0, '의료재활': 6,
              '직업/근로사업장': 12, '직업/보호작업장': 116, '직업/직업적응훈련': 5},
       2024: {'거주/지체': 2, '거주/시각': 3, '거주/청각': 1, '거주/지적': 14, '거주/중증': 23, '거주/장애영유아': 2, '거주/단기': 40, '거주/공동생활가정': 163,
              '지역/장애인복지관': 52, '지역/주간보호·주간이용': 134, '지역/체육시설': 7, '지역/수어통역센터': 26, '지역/생활이동지원·시각장애인등생활지원': 1,
              '지역/점자도서관': 0, '지역/점자도서·녹음서출판': 0, '지역/수련시설': 0, '지역/재활치료시설': 0, '의료재활': 6,
              '직업/근로사업장': 11, '직업/보호작업장': 116, '직업/직업적응훈련': 9}}
OFF_SRC = {2019: '보건복지부 2020년 장애인복지시설 일람표 총괄표(2019.12.) p3~5 (이미지 판독)',
           2024: '보건복지부 2025 장애인복지시설 일람표 총괄표(2024.12) p3~5'}
OFF_NOTE = '판매시설(장애인생산품 판매시설)은 직업재활시설 총괄표에 없음(명부 각 1곳). 2025 지역사회재활 소계 226은 의료재활 6 포함.'


def key(sub):
    s = sub.replace(' ', '')
    rules = [('지체장애인시설', '거주/지체'), ('시각장애인시설', '거주/시각'), ('청각', '거주/청각'), ('지적장애인시설', '거주/지적'),
             ('중증장애인거주', '거주/중증'), ('장애영유아', '거주/장애영유아'), ('단기거주', '거주/단기'), ('공동생활가정', '거주/공동생활가정'),
             ('장애인복지관', '지역/장애인복지관'), ('주간보호', '지역/주간보호·주간이용'), ('주간이용', '지역/주간보호·주간이용'),
             ('체육시설', '지역/체육시설'), ('수어통역', '지역/수어통역센터'), ('생활이동지원', '지역/생활이동지원·시각장애인등생활지원'),
             ('생활지원센터', '지역/생활이동지원·시각장애인등생활지원'), ('점자도서관', '지역/점자도서관'), ('출판', '지역/점자도서·녹음서출판'),
             ('수련시설', '지역/수련시설'), ('재활치료', '지역/재활치료시설'), ('의료재활', '의료재활'), ('근로사업장', '직업/근로사업장'),
             ('보호작업장', '직업/보호작업장'), ('직업적응', '직업/직업적응훈련'), ('판매시설', '판매시설')]
    return next(v for k, v in rules if k in s)


def scope(k):
    if k.startswith('지역/'): return '이용시설'               # 지역사회재활시설 = 장애인·가족이 찾아가 이용하는 시설
    if k.startswith('직업/'): return '이용시설_직업재활'      # 매일 통근해 이용(보호작업장 등) — 별도 그룹
    if k.startswith('거주/'): return '거주시설'
    return '제외'                                             # 의료재활(병·의원), 생산품 판매시설


rows = []; summ = {}
off_rows = [dict(year=y, ref_date=f'{y}-12-31', key=k, official=v, source=OFF_SRC[y], note=OFF_NOTE) for y in OFF for k, v in OFF[y].items()]
pd.DataFrame(off_rows).to_csv(FD / 'raw' / 'official_장애인복지시설_서울_종류_2019_2024.csv', index=False, encoding='utf-8-sig')
dn = u11.sgis_dongs('2025_2Q'); cd2gu = dict(zip(dn.CD.astype(str).str[:5], dn.gu))
for snap, y in [('2020_01', 2019), ('2025_01', 2024)]:
    d = pd.read_parquet(SRC / f'facilities_장애인복지시설_{snap}.parquet')
    d['type_key'] = d.facility_subtype.map(key); d['scope_flag'] = d.type_key.map(scope)
    before = d.groupby('scope_flag').x_5179.apply(lambda s: round(float(s.notna().mean()), 4)).to_dict()
    d = geo11.fill(d, FD / 'raw' / 'geocoding', gu_col='gu', mask=d.scope_flag != '제외')
    d = geo11.respatial(d, lib='mb')
    d['gu_addr'] = d.address.map(u11.gu_of)
    d['gu_point'] = d.adm_dong_cd.fillna('').astype(str).str[:5].map(cd2gu)
    d['location_outside_seoul'] = (d.inside_seoul.astype(str) == 'False') | d.address.fillna('').map(lambda a: bool(u11.mb.OTHER_SIDO.match(a)))
    vc = d.type_key.value_counts()
    for k, v in OFF[y].items():
        rows.append(dict(year=y, scope_flag=scope(k), level='서울_종류', key=k, built=int(vc.get(k, 0)), official=v, diff=int(vc.get(k, 0)) - v))
    for sc in ['이용시설', '이용시설_직업재활', '거주시설']:
        x = d[d.scope_flag == sc]; off = sum(v for k, v in OFF[y].items() if scope(k) == sc)
        rows.append(dict(year=y, scope_flag=sc, level='서울_합계', key='계', built=len(x), official=off, diff=len(x) - off,
                         diff_pct=round((len(x) - off) / off * 100, 2)))
        xin = x[~x.location_outside_seoul]
        cov = geo11.coord_rate_by_gu(xin, 'gu'); cov.to_csv(FD / f'coord_by_gu_장애인복지시설_{sc}_{snap}.csv', encoding='utf-8-sig')
        summ.setdefault(snap, {})[sc] = dict(
            built=len(x), official=off, coord_rate_before=before.get(sc), coord_rate_after=round(float(x.x_5179.notna().mean()), 4),
            located_outside_seoul=int(x.location_outside_seoul.sum()),
            min_gu_rate=float(cov.rate.min()), min_gu=str(cov.rate.idxmin()), gu_below_85=cov.index[cov.rate < 0.85].tolist(),
            gu_with_zero_rows=cov.index[cov.n == 0].tolist(),
            filled=int((x.coord_stage == 'filled_11').sum()), still_missing=int(x.x_5179.isna().sum()),
            gu_col_missing=int((~x.gu.isin(GU)).sum()), gu_col_vs_addr_mismatch=int(((x.gu_addr != '') & (x.gu_addr != x.gu)).sum()),
            gu_col_vs_point_mismatch=int((x.gu_point.notna() & (x.gu_point != x.gu)).sum()))
    d.drop(columns=['gu_addr']).pipe(lambda z: u11.mb.finalize(z, snap, FD, '장애인복지시설'))
    d[d.coord_stage == 'filled_11'][['facility_id', 'facility_subtype', 'name', 'address', 'coord_method', 'geocode_detail2']].to_csv(
        FD / f'filled_coords_장애인복지시설_{snap}.csv', index=False, encoding='utf-8-sig')
    d[(d.scope_flag != '제외') & d.x_5179.isna()][['facility_id', 'scope_flag', 'facility_subtype', 'gu', 'name', 'address', 'geocode_detail2']].to_csv(
        FD / f'unresolved_장애인복지시설_{snap}.csv', index=False, encoding='utf-8-sig')
    mm = d[(d.gu_point.notna() & (d.gu_point != d.gu)) | ((d.gu_addr != '') & (d.gu_addr != d.gu))][['facility_subtype', 'name', 'gu', 'gu_addr', 'gu_point', 'address']]
    if len(mm): print(snap, 'gu mismatch\n', mm.to_string())
pd.DataFrame(rows).to_csv(FD / 'official_compare_장애인복지시설.csv', index=False, encoding='utf-8-sig')
json.dump(summ, open(FD / 'summary_장애인복지시설.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(summ, ensure_ascii=False, indent=1, default=str))
r = pd.DataFrame(rows); print(r[r['diff'] != 0].to_string() if (r['diff'] != 0).any() else 'all type counts match')
print(r[r.level == '서울_합계'].to_string())
