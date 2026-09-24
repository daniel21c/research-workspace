# -*- coding: utf-8 -*-
"""따릉이 2020_01 개선판: 대여소 집합 = OA-22223 일별 거치수량 2019-12-31 목록(서울시 운영 시스템 기록, 기준일 자료).
좌표: ① 기존 역산판(21.01.31판, 설치≤2019-12-31) ② 21.01.31판(설치일 2020 이후로 갱신된 같은 번호) ③ 21.06·21.12판 같은 번호
      ④ 없음 → unresolved(자치구는 번호대 이웃으로 추정: gu_name_inferred). coord_stage 열에 단계 기록."""
import sys, io, zipfile, json
from pathlib import Path
import pandas as pd, numpy as np
HERE = Path(__file__).resolve().parent; V1 = HERE.parents[1]
sys.path.insert(0, str(V1 / '03_교육교통공원상가' / '_lib'))
import fac   # 읽기 전용 사용(attach_geo, finalize, qa_block)

z = zipfile.ZipFile(HERE / 'raw' / 'OA-22223_일별대여소별거치수량_2019_2021.zip')
L = []
for i in z.infolist():
    d = pd.read_csv(io.BytesIO(z.read(i)), encoding='cp949', dtype=str); d.columns = ['ts', 'no', 'st_id', 'racked']; L.append(d)
L = pd.concat(L); L['date'] = L.ts.str[:10]
day = L[L.date == '2019-12-31'].drop_duplicates('no').copy(); day['sid'] = day.no.astype(int).astype(str)
CENTER = sorted(int(x) for x in day.sid if int(x) < 100)   # 1~99번: 어떤 대여소 정보 판에도 없음 → 센터·정비거점으로 보고 제외
day = day[day.sid.astype(int) >= 100]
ref = set(day.sid)

def parse(d):
    d = d.copy(); d.columns = range(d.shape[1]); d['row'] = d.index + 2
    d = d[pd.to_numeric(d[0], errors='coerce').notna()].copy()
    return pd.DataFrame({'sid': d[0].astype(str).str.replace(r'\.0$', '', regex=True).str.strip(), 'name': d[1], 'gu': d[2], 'addr': d[3],
                         'lat': d[4], 'lon': d[5], 'inst': pd.to_datetime(d[6], errors='coerce'), 'lcd': pd.to_numeric(d[7], errors='coerce'),
                         'qr': pd.to_numeric(d[8], errors='coerce'), 'op': d[9], 'row': d['row']})
B = V1 / '03_교육교통공원상가' / 'bike_station'
e2101 = parse(fac.read_csv_any(B / 'raw' / 'OA-13252_대여소정보_210131.csv', header=None))
e2106 = parse(pd.read_excel(HERE / 'raw' / 'OA-13252_대여소정보_2106.xlsx', header=None, dtype=str))
e2112 = parse(pd.read_excel(HERE / 'raw' / 'OA-13252_대여소정보_2112.xlsx', header=None, dtype=str))
old = pd.read_parquet(B / 'facilities_bike_station_2020_01.parquet')
old['sid'] = old.facility_id.str.replace('BIKE_', '')

rows = []
keep = old[old.sid.isin(ref)].copy()
keep['coord_stage'] = '1_recon_2101_inst_le_20191231'
keep['temporal_reason'] = 'OA-22223 2019-12-31 운영 목록에 있음; 좌표·속성은 21.01.31판'
keep['grade'] = 'A'
rest = sorted(ref - set(keep.sid), key=int)
add = []
for stage, ed, fn in [('2_ed2101_inst_after_ref', e2101, 'raw/OA-13252_대여소정보_210131.csv (03_교육교통공원상가/bike_station)'),
                      ('3_ed2106', e2106, '11_신뢰도_승격/따릉이/raw/OA-13252_대여소정보_2106.xlsx'),
                      ('3_ed2112', e2112, '11_신뢰도_승격/따릉이/raw/OA-13252_대여소정보_2112.xlsx')]:
    s = ed[ed.sid.isin(rest)].drop_duplicates('sid')
    if len(s):
        s = s.assign(coord_stage=stage, src=fn); add.append(s); rest = [r for r in rest if r not in set(s.sid)]
add = pd.concat(add) if add else pd.DataFrame()
# 21.01.31판에 좌표가 비어 있으면 21.06 → 21.12판 같은 번호 좌표로 채움
for ed, tag in [(e2106, '+coord_ed2106'), (e2112, '+coord_ed2112')]:
    m = pd.to_numeric(add['lat'], errors='coerce').isna()
    if m.any():
        mp = ed.drop_duplicates('sid').set_index('sid')
        hit = m & add.sid.isin(mp.index)
        add.loc[hit, 'lat'] = add.loc[hit, 'sid'].map(mp['lat']); add.loc[hit, 'lon'] = add.loc[hit, 'sid'].map(mp['lon'])
        add.loc[hit, 'coord_stage'] = add.loc[hit, 'coord_stage'] + tag
# 좌표 없는 대여소: 번호대 이웃으로 구 추정
e_all = pd.concat([e2101, e2106, e2112]).drop_duplicates('sid'); e_all['n'] = e_all.sid.astype(int)
def infer_gu(n, k=6):
    nb = e_all.iloc[(e_all.n - n).abs().argsort()[:k]]
    return nb.gu.mode().iloc[0], round(float((nb.gu == nb.gu.mode().iloc[0]).mean()), 2)
un = pd.DataFrame({'sid': rest})
if len(un):
    g = un.sid.astype(int).map(infer_gu); un['gu'] = g.str[0]; un['gu_infer_share'] = g.str[1]
    un['coord_stage'] = '4_unresolved'; un['src'] = 'OA-22223 목록만(좌표·이름 없음)'
new = pd.concat([add, un], ignore_index=True)
o = pd.DataFrame(index=new.index)
o['facility_id'] = 'BIKE_' + new.sid; o['category_group'] = '교통'; o['facility_type'] = '공공자전거대여소'
o['facility_subtype'] = new.get('op').fillna('미상') if 'op' in new else '미상'; o['year_snapshot'] = '2020_01'
o['name'] = new.get('name'); o['address'] = new.get('addr'); o['lon'] = new.get('lon'); o['lat'] = new.get('lat')
o['coord_method'] = 'source'; o['grade'] = 'A'; o['source_org'] = '서울특별시(서울시설공단)'
o['source_dataset'] = 'OA-22223 일별 대여소별 거치수량 2019-12-31 목록 + OA-13252 판별 좌표'
o['source_url'] = 'https://data.seoul.go.kr/dataList/OA-22223/F/1/datasetView.do'; o['source_file'] = new.src
o['source_row_id'] = new.get('row').astype('Int64').astype(str) if 'row' in new else None
o['source_reference_date'] = '2019-12-31'; o['reference_month_delta'] = 0
o['temporal_reason'] = np.where(new.coord_stage == '4_unresolved', 'OA-22223 2019-12-31 운영 목록에 있음; 2021년 이후 판에 없음(2020년 중 철거·번호변경) → 좌표 없음',
                                'OA-22223 2019-12-31 운영 목록에 있음; 좌표는 이후 판의 같은 번호(이전 설치 가능성 있음)')
o['install_date'] = new.get('inst').dt.strftime('%Y-%m-%d') if 'inst' in new else None
o['gu_name'] = new.gu; o['sz_racks'] = new.get('lcd').fillna(0) + new.get('qr').fillna(0) if 'lcd' in new else np.nan
o['coord_stage'] = new.coord_stage; o['gu_infer_share'] = new.get('gu_infer_share')
o = fac.attach_geo(o); o.loc[o.x_5179.isna(), 'coord_method'] = 'unresolved'
keep = keep.drop(columns=['sid'])
out = pd.concat([keep, o], ignore_index=True)
out['scope_flag'] = 'OA22223_20191231'
out['racked_20191231'] = out.facility_id.str.replace('BIKE_', '').map(dict(zip(day.sid, pd.to_numeric(day.racked, errors='coerce'))))
out = fac.finalize(out)
base = HERE / 'facilities_bike_station_2020_01'
out.to_csv(str(base) + '.csv', index=False, encoding='utf-8-sig')
d2 = out.copy()
for c in d2.columns:
    if d2[c].dtype == object: d2[c] = d2[c].astype('string')
d2.to_parquet(str(base) + '.parquet', index=False)
# 좌표율(서울 안 기준·구별)
ins = out.inside_seoul.astype('boolean')
gu_tab = out.assign(has=out.x_5179.notna()).groupby('gu_name').agg(n=('facility_id', 'size'), coord=('has', 'sum'))
gu_tab['rate'] = (gu_tab.coord / gu_tab.n).round(4)
gu_tab.to_csv(HERE / 'coord_rate_by_gu_2020_01.csv', encoding='utf-8-sig')
q = dict(rows=len(out), coord_stage=out.coord_stage.value_counts().to_dict(), coord_rate=round(float(out.x_5179.notna().mean()), 4),
         inside_seoul=int((ins == True).sum()), outside_seoul=int((ins == False).sum()), no_coord=int(out.x_5179.isna().sum()),
         min_gu_coord_rate=float(gu_tab.rate.min()), min_gu=str(gu_tab.rate.idxmin()), gu_lt85=int((gu_tab.rate < .85).sum()),
         dup_facility_id=int(out.facility_id.duplicated().sum()), excluded_center_ids_lt100=CENTER,
         log_rows_20191231_all=int(len(day) + len(CENTER)),
         unresolved=un.to_dict('records'))
json.dump(q, open(HERE / 'qa_bike_station_2020_01_logbased.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps({k: v for k, v in q.items() if k != 'unresolved'}, ensure_ascii=False)); print(un.to_string())
