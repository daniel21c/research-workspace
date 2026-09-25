# -*- coding: utf-8 -*-
"""가족센터: 두 시점 정의 맞춤(자치구 본소 25곳 / 광역·중앙 / 지점 분리), 연속성 점검, 공식 수 대조, 좌표 보완.
2020_01: 여가부 건강가정지원센터 현황 20190903(data.go.kr 3077162) — 25개 구 통합센터 + 서울시건강가정지원센터(광역, 중구 소파로4길 6)
         + 서초구 반포대로 217(2005 개소 국비, 구 센터와 별도 → 중앙건강가정지원센터로 판단; 구 본소 아님)
2025_01: 여가부 가족센터 주소록 2025-01-01 — 광역 1 + 구 본소 25 + 지점 15
원본(02_명부/가족센터)은 읽기만."""
import sys, json
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; FD = HERE.parent
sys.path.insert(0, str(FD / '_lib')); import u11, geo11
import pandas as pd
V1 = u11.V1; GU = u11.GU
SRC = V1 / '02_명부' / '가족센터'


def scope(r, snap):
    if snap == '2020_01':
        if r.facility_subtype == '건강·다문화가족지원센터(통합)': return '자치구본소'
        return '광역·중앙'
    if r.facility_subtype == '가족센터(지점)': return '지점'
    return '광역·중앙' if '광역' in r['name'] else '자치구본소'


D = {}; summ = {}
for snap in ['2020_01', '2025_01']:
    d = pd.read_parquet(SRC / f'facilities_가족센터_{snap}.parquet')
    d['scope_flag'] = [scope(r, snap) for _, r in d.iterrows()]
    before = round(float(d.x_5179.notna().mean()), 4)
    d['gu_fill'] = d.gu.where(d.gu.isin(GU), '')
    d = geo11.fill(d, FD / 'raw' / 'geocoding', gu_col='gu_fill')
    d = geo11.respatial(d, lib='mb')
    d = d.drop(columns=['gu_fill'])
    D[snap] = d
    main = d[d.scope_flag == '자치구본소']
    summ[snap] = dict(rows=len(d), by_scope=d.scope_flag.value_counts().to_dict(), main_gu_n=int(main.gu.nunique()),
                      main_gu_missing=sorted(set(GU) - set(main.gu)), main_dup_gu=main.gu[main.gu.duplicated()].tolist(),
                      coord_rate_before=before, coord_rate_after=round(float(d.x_5179.notna().mean()), 4),
                      coord_rate_main=round(float(main.x_5179.notna().mean()), 4),
                      filled=d[d.coord_stage == 'filled_11'][['name', 'address', 'coord_method', 'geocode_detail2']].to_dict('records'),
                      still_missing=d[d.x_5179.isna()][['name', 'address']].to_dict('records'))
    u11.mb.finalize(d, snap, FD, '가족센터')
# 연속성: 구 본소 주소 동일 여부
a = D['2020_01'][D['2020_01'].scope_flag == '자치구본소'].set_index('gu'); b = D['2025_01'][D['2025_01'].scope_flag == '자치구본소'].set_index('gu')
cont = []
for g in GU:
    ka, kb = u11.mb.addr_key(a.loc[g, 'address']), u11.mb.addr_key(b.loc[g, 'address'])
    dist = None
    if pd.notna(a.loc[g, 'x_5179']) and pd.notna(b.loc[g, 'x_5179']):
        dist = round(((float(a.loc[g, 'x_5179']) - float(b.loc[g, 'x_5179'])) ** 2 + (float(a.loc[g, 'y_5179']) - float(b.loc[g, 'y_5179'])) ** 2) ** 0.5)
    cont.append(dict(gu=g, name_2020=a.loc[g, 'name'], addr_2020=a.loc[g, 'address'], name_2025=b.loc[g, 'name'], addr_2025=b.loc[g, 'address'],
                     same_address=ka == kb, moved_m=dist, branches_2025=int(((D['2025_01'].gu == g) & (D['2025_01'].scope_flag == '지점')).sum())))
cont = pd.DataFrame(cont); cont.to_csv(FD / 'continuity_가족센터_본소.csv', index=False, encoding='utf-8-sig')
summ['continuity'] = dict(same_address=int(cont.same_address.sum()), moved=cont[~cont.same_address][['gu', 'moved_m']].to_dict('records'))
# 공식 수 대조
off = [dict(year=2019, ref_date='2019-09-03', scope='자치구본소', official=25, built=summ['2020_01']['by_scope'].get('자치구본소', 0),
            source='여가부 건강가정지원센터 현황 20190903: 서울 25개 구 모두 건강·다문화 통합센터(통합센터=Y)'),
       dict(year=2019, ref_date='2019-09-03', scope='전체(명부 행)', official=27, built=summ['2020_01']['rows'], source='같은 명부 서울 행수(광역·중앙 포함)'),
       dict(year=2024, ref_date='2025-01-01', scope='자치구본소', official=25, built=summ['2025_01']['by_scope'].get('자치구본소', 0),
            source='서울시 「자치구 가족센터 운영 지원」: 서울시내 25개 자치구 운영(news.seoul.go.kr/welfare/archives/107778, 2025.12 기준) / 여가부 주소록 본소 25'),
       dict(year=2024, ref_date='2025-01-01', scope='광역', official=1, built=summ['2025_01']['by_scope'].get('광역·중앙', 0), source='서울시가족센터(광역) 1'),
       dict(year=2024, ref_date='2025-01-01', scope='전체(본소+광역+지점)', official=41, built=summ['2025_01']['rows'], source='여가부 가족센터 주소록 2025-01-01 서울 행수')]
pd.DataFrame(off).assign(diff=lambda z: z.built - z.official).to_csv(FD / 'official_compare_가족센터.csv', index=False, encoding='utf-8-sig')
json.dump(summ, open(FD / 'summary_가족센터.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(summ, ensure_ascii=False, indent=1, default=str)); print(cont.to_string())
