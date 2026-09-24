# -*- coding: utf-8 -*-
"""따릉이 공식 대여소 수 대조표 + 구별 역산판 vs 운영목록판 비교."""
import json, sys
from pathlib import Path
import pandas as pd, numpy as np
HERE = Path(__file__).resolve().parent; V1 = HERE.parents[1]
rec = pd.read_parquet(V1 / '03_교육교통공원상가/bike_station/facilities_bike_station_2020_01.parquet')
new = pd.read_parquet(HERE / 'facilities_bike_station_2020_01.parquet')
y25 = pd.read_parquet(V1 / '03_교육교통공원상가/bike_station/facilities_bike_station_2025_01.parquet')
q = json.load(open(HERE / 'station_log_check.json', encoding='utf-8'))
rows = [
 dict(snapshot='2020_01', official_source='서울시 OA-22223 일별 대여소별 거치수량, 2019-12-31 목록(1~99번 센터 3개 제외)', official_ref_date='2019-12-31', official_value=len(new), ours_version='역산판(03_, 21.01.31판 설치≤2019-12-31)', ours_value=len(rec)),
 dict(snapshot='2020_01', official_source='서울시 내 손안에 서울 2020-04-08 "따릉이 25,000대, 약 1,540개 대여소"', official_ref_date='2020-04 발표(2020-03 시점 서술)', official_value=1540, ours_version='역산판', ours_value=len(rec)),
 dict(snapshot='2020_01', official_source='서울시 내 손안에 서울 2020-04-08 "약 1,540개"', official_ref_date='2020-04 발표', official_value=1540, ours_version='운영목록판(11_)', ours_value=len(new)),
 dict(snapshot='2020_01', official_source='이투데이 2019-12-10(서울시 발표 인용) "2만5000대, 1540곳"', official_ref_date='2019-12 발표', official_value=1540, ours_version='운영목록판(11_)', ours_value=len(new)),
 dict(snapshot='2020_01', official_source='서울시설공단 따릉이 운영현황 표 "2019년" 열(2026-09-24 열람)', official_ref_date='2019년(월 미표기)', official_value=2085, ours_version='운영목록판(11_)', ours_value=len(new)),
 dict(snapshot='2020_01', official_source='서울시설공단 운영현황 표 "2018년" 열', official_ref_date='2018년(월 미표기)', official_value=1540, ours_version='운영목록판(11_)', ours_value=len(new)),
 dict(snapshot='2025_01', official_source='서울시설공단 따릉이 운영현황 표 "2024년" 열 2,766(+4)', official_ref_date='2024년(연말 추정)', official_value=2766, ours_version='24.12월 기준판(03_, A)', ours_value=len(y25)),
 dict(snapshot='(참고)', official_source='OA-22223 2020-12-31 목록', official_ref_date='2020-12-31', official_value=q['dates']['2020-12-31'], ours_version='OA-13252 21.01.31판 행수', ours_value=2154),
 dict(snapshot='(참고)', official_source='서울시설공단 표 "2020년" 열', official_ref_date='2020년', official_value=2228, ours_version='OA-22223 2020-12-31 목록', ours_value=q['dates']['2020-12-31']),
 dict(snapshot='(참고)', official_source='서울시설공단 표 "2021년" 열', official_ref_date='2021년', official_value=2600, ours_version='OA-13252 21.12월판 행수', ours_value=2586),
]
t = pd.DataFrame(rows); t['diff_pct'] = ((t.ours_value / t.official_value - 1) * 100).round(2)
t.to_csv(HERE / 'official_compare_따릉이.csv', index=False, encoding='utf-8-sig')
g = pd.DataFrame({'recon_2101': rec.groupby('gu_name').size(), 'log_20191231': new.groupby('gu_name').size(), 'y2025': y25.groupby('gu_name').size()}).fillna(0).astype(int)
g['recon_vs_log_pct'] = ((g.recon_2101 / g.log_20191231 - 1) * 100).round(1)
g.to_csv(HERE / 'gu_compare_따릉이.csv', encoding='utf-8-sig')
r = np.corrcoef(g.recon_2101, g.log_20191231)[0, 1]
print(t.to_string()); print(g.to_string()); print('gu r', round(r, 4), 'max abs pct', g.recon_vs_log_pct.abs().max())
print('2025 rows outside Seoul', int((y25.inside_seoul.astype('boolean') == False).sum()), 'ids<100', int((y25.facility_id.str.replace('BIKE_','').astype(int) < 100).sum()))
