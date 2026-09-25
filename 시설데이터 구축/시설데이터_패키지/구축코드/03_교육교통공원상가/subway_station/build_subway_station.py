# -*- coding: utf-8 -*-
"""지하철·광역철도역 2020_01 / 2025_01 (서울 경계 내)
좌표 마스터: 서울시 역사마스터 정보(OA-21232, 현재판, 수도권 노선-역 단위, GTX-A 포함) — 좌표 source.
시점: 원천에 개통일이 없어 조사된 2020-01~2024-12 서울 내 신규 노선-역 목록으로 역산(B).
  2020_01 = 현재 마스터 − (2020-01-01 이후 개통 노선-역) − 미개통(GTX-A 삼성)
  2025_01 = 현재 마스터 − 2025-01-01 이후 개통(서울 내 해당 없음 확인) − 미개통(GTX-A 삼성)
고유 역(환승역 통합): 노선-역을 이름 토큰(괄호 안 부역명 포함) 일치 & 700m 이내, 또는 150m 이내면 같은 역으로 묶음.
  facilities_subway_station_*: 고유 역 위치(구성 노선-역 좌표 평균), subway_line_station_*.csv: 노선-역 단위.
대조: KRIC 역사정보(도시철도, 현재판) 서울 주소 행 수, 서울교통공사 개통현황(OA-13317)."""
import sys, re, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import fac
import pandas as pd, numpy as np

RAW = HERE / 'raw'; TYP = 'subway_station'
fac.seoul_sheet('OA-21232', RAW / 'OA-21232_역사마스터.csv', ref_date='다운로드 시점 현재', note='서울시 역사마스터 정보')
fac.fetch('https://data.kric.go.kr/rips/dataset/download.file', RAW / 'KRIC_역사정보_id32.xlsx',
          params=dict(type='filedata', id=32, operation=1), ref_date='현재판(데이터기준일자 열 참조)',
          note='국가철도공단 레일포털 역사정보(전체 기관) 표준데이터')
fac.seoul_file('OA-13317', 4, 1, RAW / 'OA-13317_개통현황_20250813.csv', ref_date='2025-08-13', note='서울교통공사 개통 현황')
fac.seoul_file('OA-13317', 2, 1, RAW / 'OA-13317_개통현황_202003.csv', ref_date='2020-03', note='서울교통공사 개통 현황 2020.3판')

OPEN = [  # (호선(마스터 표기), 역사명, 개통일, 근거)
    ('5호선', '강일', '2021-03-27', '5호선 하남선 2단계 개통'),
    *[('신림선', n, '2022-05-28', '신림선 개통') for n in ['관악산(서울대)', '서울대벤처타운', '서원', '신림', '당곡', '보라매병원',
                                                        '보라매공원', '보라매', '서울지방병무청', '대방', '샛강']],
    *[('신분당선(연장2)', n, '2022-05-28', '신분당선 신사~강남 연장') for n in ['신사', '논현', '신논현']],
    ('서해선', '김포공항', '2023-07-01', '서해선 대곡~소사 개통'),
    ('8호선', '암사역사공원', '2024-08-10', '8호선 별내선 연장 개통'),
    ('수도권 광역급행철도', '수서', '2024-03-30', 'GTX-A 수서~동탄 개통'),
    ('수도권 광역급행철도', '서울', '2024-12-28', 'GTX-A 운정~서울역 개통'),
    ('수도권 광역급행철도', '연신내', '2024-12-28', 'GTX-A 운정~서울역 개통')]
NOT_OPEN = [('수도권 광역급행철도', '삼성', 'GTX-A 삼성역 미개통(무정차 통과)')]

m = fac.read_csv_any(RAW / 'OA-21232_역사마스터.csv'); m['row'] = np.arange(2, len(m) + 2)
m = fac.attach_geo(m, lon='경도', lat='위도')
s = m[m['inside_seoul'] == True].copy()
op = pd.DataFrame(OPEN, columns=['호선', '역사명', 'open_date', 'open_note'])
s = s.merge(op, on=['호선', '역사명'], how='left')
chk = op.merge(s[['호선', '역사명']], on=['호선', '역사명'], how='left', indicator=True)
qa = {'type': TYP, 'notes': [__doc__.strip()], 'master_rows': len(m), 'master_rows_seoul': len(s),
      'master_rows_outside_seoul_dropped': int((m['inside_seoul'] != True).sum()),
      'open_list_matched': int((chk['_merge'] == 'both').sum()), 'open_list_total': len(op),
      'open_list_unmatched': chk.loc[chk['_merge'] != 'both', ['호선', '역사명']].values.tolist(),
      'master_lines_seoul': s['호선'].value_counts().to_dict()}
no = pd.DataFrame(NOT_OPEN, columns=['호선', '역사명', 'not_open_note'])
s = s.merge(no, on=['호선', '역사명'], how='left')

# 고유 역 그룹
def toks(n):
    n = str(n); t = set([re.sub(r'역$', '', re.sub(r'\(.*?\)', '', n).strip())])
    t |= set(x.strip() for x in re.findall(r'\((.*?)\)', n))
    return {x for x in t if x}
s = s.reset_index(drop=True); s['_t'] = s['역사명'].map(toks)
par = list(range(len(s)))
def f(i):
    while par[i] != i:
        par[i] = par[par[i]]; i = par[i]
    return i
X = s['x_5179'].values; Y = s['y_5179'].values
for i in range(len(s)):
    for j in range(i + 1, len(s)):
        dd = np.hypot(X[i] - X[j], Y[i] - Y[j])
        if dd < 150 or (dd < 700 and s.at[i, '_t'] & s.at[j, '_t']):
            par[f(i)] = f(j)
s['grp'] = [f(i) for i in range(len(s))]
gid = s.groupby('grp')['역사_ID'].agg(lambda x: min(x, key=lambda v: int(v) if str(v).isdigit() else 10 ** 9))
s['station_id'] = 'SUB_' + s['grp'].map(gid).astype(str)

kr = pd.read_excel(RAW / 'KRIC_역사정보_id32.xlsx', dtype=str)
kr_seoul = int(kr['역사도로명주소'].astype(str).str.startswith('서울').sum())
outs = {}
for snap in ['2020_01', '2025_01']:
    D = pd.Timestamp(fac.SNAP[snap]['ref'])
    keep = s['not_open_note'].isna() & (s['open_date'].isna() | (pd.to_datetime(s['open_date']) <= D))
    ls = s[keep].copy()
    ls['year_snapshot'] = snap
    lcols = ['station_id', '역사_ID', '역사명', '호선', 'lon', 'lat', 'x_5179', 'y_5179', 'open_date', 'open_note', 'adm_dong_cd', 'grid100_cd', 'year_snapshot']
    ls[lcols].to_csv(HERE / f'subway_line_station_{snap}.csv', index=False, encoding='utf-8-sig')
    g = ls.groupby('station_id')
    o = pd.DataFrame({'name': g['역사명'].agg(lambda x: sorted(x, key=len)[0]),
                      'x_5179': g['x_5179'].mean(), 'y_5179': g['y_5179'].mean(),
                      'lines': g['호선'].agg(lambda x: '|'.join(sorted(x))),
                      'line_station_ids': g['역사_ID'].agg(lambda x: '|'.join(sorted(x))),
                      'sz_lines': g['호선'].nunique(), 'rows': g['row'].agg(lambda x: '|'.join(map(str, sorted(x)))),
                      'newest_open': g['open_date'].agg(lambda x: max(x.dropna()) if x.notna().any() else None)}).reset_index()
    o['facility_id'] = o['station_id']; o['category_group'] = '교통'; o['facility_type'] = '지하철역'
    o['facility_subtype'] = np.where(o['sz_lines'] > 1, '환승역', '단일노선역'); o['year_snapshot'] = snap
    o['address'] = None; o['coord_method'] = 'source'; o['grade'] = 'B'
    o['source_org'] = '서울특별시(역사마스터) + 개통일 조사표'; o['source_dataset'] = '서울시 역사마스터 정보 OA-21232(현재판) 개통일 역산'
    o['source_url'] = 'https://data.seoul.go.kr/dataList/OA-21232/S/1/datasetView.do'
    o['source_file'] = 'raw/OA-21232_역사마스터.csv'; o['source_row_id'] = o['rows']
    o['source_reference_date'] = fac.SNAP[snap]['ref']; o['reference_month_delta'] = 0
    o['temporal_reason'] = '현재 마스터에서 기준일 이후 개통 노선-역 제외(개통일 조사표), 좌표는 현재판(역 위치 불변 가정)'
    o = o.drop(columns=['rows'])
    o = fac.attach_geo(o, x='x_5179', y='y_5179')
    o = fac.write_out(o, HERE, TYP, snap); outs[snap] = o
    q = fac.qa_block(o)
    q.update(line_station_rows=len(ls), unique_stations=len(o), transfer_stations=int((o['sz_lines'] > 1).sum()),
             removed_open_after_ref=int((s['open_date'].notna() & (pd.to_datetime(s['open_date']) > D)).sum()),
             removed_not_open=int(s['not_open_note'].notna().sum()), by_line=ls['호선'].value_counts().to_dict(),
             kric_current_rows_seoul_address=kr_seoul, kric_data_date=str(kr['데이터기준일자'].iloc[0]))
    qa[snap] = q
c = set(outs['2020_01']['facility_id']) & set(outs['2025_01']['facility_id'])
qa['panel'] = dict(common_ids=len(c), only_2020=len(outs['2020_01']) - len(c), only_2025=len(outs['2025_01']) - len(c),
                   new_unique_stations_2025=sorted(outs['2025_01'].loc[~outs['2025_01']['facility_id'].isin(c), 'name'].tolist()))
fac.dump_qa(HERE, TYP, qa)
print({k: {kk: qa[k][kk] for kk in ['line_station_rows', 'unique_stations', 'transfer_stations', 'removed_open_after_ref', 'outside_seoul']} for k in ['2020_01', '2025_01']}, qa['open_list_matched'], qa['open_list_unmatched'], qa['panel'])
