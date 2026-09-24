# -*- coding: utf-8 -*-
"""주민센터(동 행정복지센터) 2020_01 / 2025_01 — 행정안전부 읍면동 하부행정기관 현황(data.go.kr 15059715) (C)
허용창 안의 판이 없어 2020_01은 20190630판(−6개월), 2025_01은 20240731판(−5개월)을 쓰고 전후판(20201231, 20251231)과
명칭 변동을 대조한다. 좌표 없음 → 주소 지오코딩(카카오→브이월드, 도로명 건물번호/지번 번지 일치만).
검증: 지오코딩 점이 속한 2025 행정동 명칭과 센터 명칭 일치율."""
import sys, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import fac
import pandas as pd, numpy as np

RAW = HERE / 'raw'; TYP = 'community_center'; GC = RAW / 'geocoding'
F = {'20190630': 'FILE_000000002249938', '20201231': 'FILE_000000002461414', '20240731': 'FILE_000000003207209',
     '20251231': 'FILE_000000003620457'}
for k, a in F.items():
    fac.fetch('https://www.data.go.kr/cmm/cmm/fileDownload.do', RAW / f'mois_하부행정기관_{k}.csv',
              params=dict(atchFileId=a, fileDetailSn=1), ref_date=f'{k[:4]}-{k[4:6]}-{k[6:]}',
              note='행정안전부_읍면동 하부행정기관 현황(data.go.kr 15059715) 과거판')

def load(k):
    d = fac.read_csv_any(RAW / f'mois_하부행정기관_{k}.csv'); d.columns = [re.sub(r'\s', '', c) for c in d.columns]
    d['row'] = np.arange(2, len(d) + 2)
    d = d[d['시도'].astype(str).str.strip().isin(['서울', '서울특별시'])].copy()
    for c in ['시군구', '읍면동', '주소']: d[c] = d[c].astype(str).str.strip()
    d['시군구'] = d['시군구'].str.replace(r'\s', '', regex=True).replace({'성복구': '성북구'})
    d['dong'] = d['읍면동'].str.replace(r'\(.*?\)', '', regex=True).str.replace(r'\s', '', regex=True) \
        .str.replace(r'(행정복지센터|주민센터|주민센토)$', '', regex=True)
    d['dong_key'] = d['dong'].str.replace(r'[·.\-]', '', regex=True).str.replace(r'제(?=\d)', '', regex=True)
    return d

import geopandas as gpd
dn = gpd.read_file(fac.SGIS / '03_행정구역' / '경계_2025_2Q' / 'bnd_dong_00_2025_2Q' / 'bnd_dong_00_2025_2Q.shp')
dn = dn[dn['ADM_CD'].astype(str).str.startswith('11')]
DN = dict(zip(dn['ADM_CD'].astype(str), dn['ADM_NM']))
def nd(x): return re.sub(r'[·.\s제]', '', str(x))
import glob
d19 = gpd.read_file(glob.glob(str(fac.SGIS / '03_행정구역' / '경계_2019_4Q' / '*dong*' / '*.shp'))[0])
qa = {'type': TYP, 'notes': [__doc__.strip()], 'official_dong_count': {'2020_01': int(d19.iloc[:, 1].astype(str).str.startswith('11').sum()), '2025_01': len(dn)},
      'official_dong_source': 'SGIS 센서스 경계 2019_4Q(2019-12-31) / 2025_2Q(2025-06-30) 서울 읍면동 수'}
for snap, k, alt in [('2020_01', '20190630', '20201231'), ('2025_01', '20240731', '20251231')]:
    d = load(k); a = load(alt)
    o = pd.DataFrame(index=d.index)
    o['facility_id'] = 'CMC_' + d['시군구'] + '_' + d['dong_key']; o['category_group'] = '복지행정안전'
    o['facility_type'] = '주민센터'; o['facility_subtype'] = '동주민센터'; o['year_snapshot'] = snap
    o['name'] = d['읍면동']; o['address'] = d['주소']; o['lon'] = np.nan; o['lat'] = np.nan; o['coord_method'] = None
    o = fac.geocode_df(o, 'address', GC)
    ref = f'{k[:4]}-{k[4:6]}-{k[6:]}'
    o['grade'] = 'C'; o['source_org'] = '행정안전부'; o['source_dataset'] = f'읍면동 하부행정기관 현황 {k}판'
    o['source_url'] = 'https://www.data.go.kr/data/15059715/fileData.do'; o['source_file'] = f'raw/mois_하부행정기관_{k}.csv'
    o['source_row_id'] = d['row'].astype(str); o['source_reference_date'] = ref
    o['reference_month_delta'] = fac.month_delta(ref, snap)
    o['temporal_reason'] = f'허용창 내 판 없음 → {ref}판 사용(창 밖, 전후판 {alt}와 대조)'
    o['gu_name'] = d['시군구']; o['dong_name'] = d['dong']
    o = fac.attach_geo(o); o.loc[o['x_5179'].isna(), 'coord_method'] = 'unresolved'
    o = fac.write_out(o, HERE, TYP, snap)
    q = fac.qa_block(o)
    nm = o['adm_dong_cd'].astype(str).map(DN)
    match = [nd(x) == nd(y) or nd(x) in nd(y) or nd(y) in nd(x) for x, y in zip(o['dong_name'], nm.fillna(''))]
    q.update(source_rows_seoul=len(d), point_in_same_named_dong_2025=int(sum(match)),
             point_in_other_dong=o.loc[[not m for m in match], ['name', 'address', 'adm_dong_cd']].assign(
                 adm_dong_nm=nm[[not m for m in match]]).astype(str).values.tolist(),
             alt_release={alt: len(a)}, names_only_in_main=sorted(set(d['시군구'] + '_' + d['dong_key']) - set(a['시군구'] + '_' + a['dong_key'])),
             names_only_in_alt=sorted(set(a['시군구'] + '_' + a['dong_key']) - set(d['시군구'] + '_' + d['dong_key'])),
             unresolved=o.loc[o['coord_method'] == 'unresolved', ['name', 'address']].values.tolist())
    qa[snap] = q
o20 = set(fac.read_csv_any(HERE / 'facilities_community_center_2020_01.csv')['facility_id']); o25 = set(o['facility_id'])
qa['panel'] = dict(common_ids=len(o20 & o25), only_2020=sorted(o20 - o25), only_2025=sorted(o25 - o20))
qa['notes'].append('미해결 좌표는 폐지·변경된 도로명주소로 카카오·브이월드·도로명주소 이력검색(juso hstryYn=Y) 모두 불일치 — 명칭 키워드 검색은 현재 위치를 줄 수 있어 쓰지 않음.')
fac.dump_qa(HERE, TYP, qa)
for s in ['2020_01', '2025_01']:
    print(s, {kk: qa[s][kk] for kk in ['rows', 'coord_rate', 'coord_method', 'outside_seoul', 'point_in_same_named_dong_2025', 'point_in_other_dong', 'names_only_in_main', 'names_only_in_alt', 'dup_facility_id']})
print(qa['panel'])
