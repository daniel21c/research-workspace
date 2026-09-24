# -*- coding: utf-8 -*-
"""따릉이 2020_01 역산(1,483) vs 서울시 '일별 대여소별 거치수량'(OA-22223, 2019~2021.5) 2019-12-31 목록 대조."""
import zipfile, io, json, sys
from pathlib import Path
import pandas as pd, numpy as np
HERE = Path(__file__).resolve().parent; V1 = HERE.parents[1]
Z = HERE / 'raw' / 'OA-22223_일별대여소별거치수량_2019_2021.zip'
z = zipfile.ZipFile(Z); frames = {}
for i in z.infolist():
    nm = i.filename.encode('cp437').decode('cp949')
    d = pd.read_csv(io.BytesIO(z.read(i)), encoding='cp949', dtype=str)
    d.columns = ['ts', 'no', 'st_id', 'racked']; d['date'] = d.ts.str[:10]; frames[nm] = d
L = pd.concat(frames.values())
daily = L.groupby('date').no.nunique()
daily.to_csv(HERE / 'station_count_daily_OA22223.csv', encoding='utf-8-sig', header=['stations_listed'])
res = {'source': 'OA-22223 서울시 공공자전거 일별 대여소별 거치수량(2019~2021년), 매일 08시 전후 스냅샷', 'dates': {}}
for dte in ['2019-01-01', '2019-06-30', '2019-11-30', '2019-12-01', '2019-12-15', '2019-12-30', '2019-12-31', '2020-01-01', '2020-01-31', '2020-12-31', '2021-01-31', '2021-05-31']:
    res['dates'][dte] = int(daily.get(dte, -1))
res['dec2019_min_max'] = [int(daily[daily.index.str.startswith('2019-12')].min()), int(daily[daily.index.str.startswith('2019-12')].max())]
res['dec2019_union'] = int(L[L.date.str.startswith('2019-12')].no.nunique())
ref = set(L[L.date == '2019-12-31'].no.astype(int))
rec = pd.read_parquet(V1 / '03_교육교통공원상가/bike_station/facilities_bike_station_2020_01.parquet')
recno = set(rec.facility_id.str.replace('BIKE_', '').astype(int))
e21 = pd.read_parquet(V1 / '03_교육교통공원상가/bike_station/facilities_bike_station_2020_01.parquet')  # placeholder
# 2021-01-31판 전체(설치일 포함)
import importlib.util
raw21 = V1 / '03_교육교통공원상가/bike_station/raw/OA-13252_대여소정보_210131.csv'
t = None
for enc in ['utf-8-sig', 'cp949']:
    try:
        t = pd.read_csv(raw21, header=None, dtype=str, encoding=enc); break
    except UnicodeDecodeError: pass
res['both'] = len(ref & recno); res['only_log_20191231'] = len(ref - recno); res['only_reconstructed'] = len(recno - ref)
res['n_log_20191231'] = len(ref); res['n_reconstructed'] = len(recno)
res['recon_vs_log_pct'] = round((len(recno) / len(ref) - 1) * 100, 2)
# only_log 대여소가 2021-01-31판에 있는가(재설치로 설치일이 2020 이후) → 좌표 확보 가능
t = t.astype(str)
nums21 = {}
for _, r in t.iterrows():
    try: nums21[int(r[0])] = r.tolist()
    except ValueError: pass
ol = sorted(ref - recno)
in21 = [n for n in ol if n in nums21]
res['only_log_in_2101_edition'] = len(in21)
res['only_log_not_in_2101_edition'] = len(ol) - len(in21)
# 2020 중 사라진 시점
last = L.assign(n=L.no.astype(int)).groupby('n').date.max()
res['only_log_last_seen_hist'] = last.reindex(ol).str[:7].value_counts().sort_index().to_dict()
first = L.assign(n=L.no.astype(int)).groupby('n').date.min()
res['only_recon_first_seen_hist'] = first.reindex(sorted(recno - ref)).fillna('never').str[:7].value_counts().sort_index().to_dict()
pd.DataFrame({'no': ol, 'in_2101_edition': [n in nums21 for n in ol], 'last_seen': last.reindex(ol).values,
              'row_2101': [' | '.join(nums21[n][:8]) if n in nums21 else '' for n in ol]}).to_csv(HERE / 'only_in_log_20191231.csv', index=False, encoding='utf-8-sig')
pd.DataFrame({'no': sorted(recno - ref), 'first_seen_log': first.reindex(sorted(recno - ref)).values}).to_csv(HERE / 'only_in_reconstruction.csv', index=False, encoding='utf-8-sig')
json.dump(res, open(HERE / 'station_log_check.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
print(t.head(3).to_string())
