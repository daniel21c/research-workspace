# -*- coding: utf-8 -*-
"""공원 2020_01 / 2025_01
(1) OSM Geofabrik south-korea-200101 / -250101 .osm.pbf 에서 면(닫힌 way·multipolygon) 추출.
    태그 규칙(facility_subtype): leisure=park | leisure=garden | leisure=nature_reserve | boundary=national_park
    | landuse=recreation_ground. access=private/no 는 제외. 서울 포함 규칙: 폴리곤 대표점이
    SGIS 2025 서울 경계 안이거나, 서울 안 면적이 자기 면적의 50% 이상이거나, 서울 안 면적 ≥ 0.1km²(경계를 걸친 대형 공원·국립공원).
    면적은 서울 경계로 자른 면적(area_in_seoul_m2)도 함께 기록(면적 비교는 이 값 사용).
    폴리곤은 parks_osm_*.gpkg(EPSG:5179), 시설표(facilities_park_*)는 중심점(centroid; 폴리곤 밖이면 대표점) 1행/객체.
    공원 입구 대용 경계점은 만들지 않음.
(2) 공식: 서울시 도시계획시설(공간시설) UQ153 2024.11.07판(OA-21129 seq2)에서 공원(UQT2xx)만 → parks_official_2025_01.gpkg,
    facilities_park_official_2025_01.csv. 2025는 OSM vs 공식 개수·면적 대조(서울 경계 내).
pbf 원본은 용량 때문에 보관하지 않고 URL·sha256·md5 검증 결과만 raw/*.metadata.json에 기록, 추출물(raw/osm_areas_*.geojson)만 저장.
pbf 위치: 환경변수 OSM_PBF_DIR(없으면 raw/_pbf/에 내려받음)."""
import sys, os, json, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import fac
import pandas as pd, numpy as np

RAW = HERE / 'raw'; TYP = 'park'
PBF = {'2020_01': 'south-korea-200101.osm.pbf', '2025_01': 'south-korea-250101.osm.pbf'}
BASEURL = 'https://download.geofabrik.de/asia/'
TAGS = [('leisure', 'park'), ('leisure', 'garden'), ('leisure', 'nature_reserve'), ('boundary', 'national_park'),
        ('landuse', 'recreation_ground')]

def pbf_path(snap):
    fn = PBF[snap]; d = os.environ.get('OSM_PBF_DIR')
    cands = [Path(d) / fn] if d else []
    cands += [RAW / '_pbf' / fn]
    for c in cands:
        if c.exists(): return c
    dest = RAW / '_pbf' / fn; fac.fetch(BASEURL + fn, dest, timeout=3600); return dest

def pbf_meta(snap):
    fn = PBF[snap]; mp = RAW / (fn + '.metadata.json')
    if mp.exists():
        m = json.load(open(mp, encoding='utf-8'))
        if 'size_match' in m: return m
    p = pbf_path(snap)
    h = fac.S.head(BASEURL + fn, timeout=60, allow_redirects=True)
    cl = int(h.headers.get('Content-Length', -1))
    m = dict(url=BASEURL + fn, method='GET', http_status_head=h.status_code, bytes=p.stat().st_size, sha256=fac.sha256(p),
             md5=hashlib.md5(open(p, 'rb').read()).hexdigest(), server_content_length=cl, size_match=(cl == p.stat().st_size),
             server_last_modified=h.headers.get('Last-Modified'), checked_utc=fac.utcnow(),
             reference_date=f'20{fn[12:14]}-{fn[14:16]}-{fn[16:18]}',
             note='Geofabrik 과거 추출본은 .md5가 제공되지 않아 서버 Content-Length와 크기 대조. 원본 pbf는 용량 문제로 결과 폴더에 보관하지 않음. 추출물 raw/osm_areas_*.geojson',
             local_copy_used=str(p.name))
    json.dump(m, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); return m

def extract(snap):
    out = RAW / f'osm_areas_{snap}.geojson'
    if out.exists(): return out
    import osmium
    from shapely import wkb
    from shapely.geometry import box
    wf = osmium.geom.WKBFactory(); B = box(126.70, 37.38, 127.25, 37.75)
    feats = []
    class H(osmium.SimpleHandler):
        def area(s, a):
            t = a.tags; hit = [f'{k}={v}' for k, v in TAGS if t.get(k) == v]
            if not hit: return
            try:
                g = wkb.loads(wf.create_multipolygon(a), hex=True)
            except Exception:
                return
            if not g.intersects(B): return
            feats.append({'type': 'Feature', 'geometry': g.__geo_interface__, 'properties': {
                'osm_type': 'way' if a.from_way() else 'relation', 'osm_id': a.orig_id(), 'tag_hit': '|'.join(hit),
                'name': t.get('name'), 'name_ko': t.get('name:ko'), 'access': t.get('access'),
                'leisure': t.get('leisure'), 'landuse': t.get('landuse'), 'boundary': t.get('boundary'),
                'operator': t.get('operator'), 'park_type': t.get('park:type')}})
    H().apply_file(str(pbf_path(snap)), locations=True, idx='flex_mem')
    tmp = out.with_suffix('.part'); json.dump({'type': 'FeatureCollection', 'features': feats}, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
    os.replace(tmp, out)
    fac.write_meta(out, derived_from=BASEURL + PBF[snap], method='pyosmium area handler (bbox 126.70,37.38,127.25,37.75)',
                   tags=[f'{k}={v}' for k, v in TAGS], created_utc=fac.utcnow(), reference_date=pbf_meta(snap)['reference_date'])
    return out

if len(sys.argv) > 1 and sys.argv[1] == 'meta':
    for s in sys.argv[2:]:
        print(pbf_meta(s)['size_match'])
    sys.exit()
if len(sys.argv) > 1 and sys.argv[1] == 'osm':
    for s in sys.argv[2:]:
        pbf_meta(s); print(extract(s)); sys.stdout.flush()
    sys.exit()

import geopandas as gpd
seoul = fac._bnd()['seoul'].to_crs(5179).geometry.union_all()
qa = {'type': TYP, 'notes': [__doc__.strip()]}
PRI = {t: i for i, t in enumerate(['leisure=park', 'leisure=garden', 'leisure=nature_reserve', 'boundary=national_park', 'landuse=recreation_ground'])}
osm = {}
for snap in ['2020_01', '2025_01']:
    meta = pbf_meta(snap); f = extract(snap)
    g = gpd.read_file(f).set_crs(4326, allow_override=True).to_crs(5179)
    n0 = len(g)
    g = g[~g['access'].isin(['private', 'no'])].copy()
    g['facility_subtype'] = g['tag_hit'].map(lambda s: sorted(s.split('|'), key=lambda x: PRI[x])[0])
    rp = g.geometry.representative_point(); g['rp_in'] = rp.within(seoul)
    g = g[g.intersects(seoul)].copy()
    g['area_m2'] = g.area.round(1); g['area_in_seoul_m2'] = g.geometry.intersection(seoul).area.round(1)
    g['seoul_rule'] = np.where(g['rp_in'], 'rep_point', np.where(g['area_in_seoul_m2'] >= 0.5 * g['area_m2'], 'area_share>=50%',
                               np.where(g['area_in_seoul_m2'] >= 1e5, 'area_in_seoul>=0.1km2', None)))
    g = g[g['seoul_rule'].notna()].copy()
    g['facility_id'] = 'OSM_' + g['osm_type'].str[0] + g['osm_id'].astype(str)
    fac.to_gpkg(g[['facility_id', 'osm_type', 'osm_id', 'facility_subtype', 'tag_hit', 'name', 'name_ko', 'access', 'operator',
                   'park_type', 'area_m2', 'area_in_seoul_m2', 'seoul_rule', 'geometry']], HERE / f'parks_osm_{snap}.gpkg')
    c = g.geometry.centroid; inpoly = c.within(g.geometry)
    pt = c.where(inpoly, g.geometry.representative_point())
    o = pd.DataFrame({'facility_id': g['facility_id'].values, 'x_5179': pt.x.values, 'y_5179': pt.y.values})
    o['category_group'] = '문화체육녹지'; o['facility_type'] = '공원(OSM)'; o['facility_subtype'] = g['facility_subtype'].values
    o['year_snapshot'] = snap; o['name'] = g['name'].fillna(g['name_ko']).values; o['address'] = None
    o['coord_method'] = 'source'; o['grade'] = 'A'; o['source_org'] = 'OpenStreetMap contributors (Geofabrik 추출본)'
    o['source_dataset'] = PBF[snap]; o['source_url'] = BASEURL + PBF[snap]; o['source_file'] = f'raw/osm_areas_{snap}.geojson'
    o['source_row_id'] = (g['osm_type'] + '/' + g['osm_id'].astype(str)).values
    o['source_reference_date'] = meta['reference_date']; o['reference_month_delta'] = 0
    o['temporal_reason'] = 'Geofabrik 연초 스냅샷(기준일 당일)'
    o['point_rule'] = np.where(inpoly.values, 'centroid', 'representative_point')
    o['sz_area_m2'] = g['area_m2'].values; o['sz_area_in_seoul_m2'] = g['area_in_seoul_m2'].values
    o['osm_tag_hit'] = g['tag_hit'].values; o['seoul_rule'] = g['seoul_rule'].values
    o = fac.attach_geo(o, x='x_5179', y='y_5179')
    o = fac.write_out(o, HERE, TYP, snap); osm[snap] = g
    q = fac.qa_block(o)
    un = g[g['facility_subtype'] == 'leisure=park'].geometry.union_all()
    q.update(pbf_sha256=meta['sha256'], pbf_size_match=meta['size_match'], bbox_candidates=n0,
             excluded_private=int(n0 - len(g) - 0), by_subtype_area_km2=(g.groupby('facility_subtype')['area_in_seoul_m2'].sum() / 1e6).round(3).to_dict(),
             leisure_park_count=int((g['facility_subtype'] == 'leisure=park').sum()),
             leisure_park_union_area_in_seoul_km2=round(un.intersection(seoul).area / 1e6, 3),
             all_tags_union_area_in_seoul_km2=round(g.geometry.union_all().intersection(seoul).area / 1e6, 3),
             named_share=round(float(o['name'].notna().mean()), 3), seoul_rule=g['seoul_rule'].value_counts().to_dict())
    q['excluded_private'] = None  # 아래에서 정확히 계산
    qa[snap] = q
    gg = gpd.read_file(f); qa[snap]['excluded_access_private_or_no'] = int(gg['access'].isin(['private', 'no']).sum())

# ---- 공식 도시계획시설 공원 2024.11.07 ----
fac.seoul_file('OA-21129', 2, 1, RAW / 'OA-21129_UQ153_공간시설_20241107.zip', ref_date='2024-11-07',
               note='서울시 도시계획시설(공간시설) UQ153')
fs = fac.unzip(RAW / 'OA-21129_UQ153_공간시설_20241107.zip', RAW / '_x' / 'uq153_20241107')
shp = [p for p in fs if p.suffix.lower() == '.shp'][0]
u = None
for e in ['cp949', 'utf-8']:
    try:
        u = gpd.read_file(shp, encoding=e); u['DGM_NM'].astype(str).str.len(); break
    except Exception:
        u = None
crs_src = str(u.crs)
u = u.to_crs(5179)
park = u[u['LCLAS_CL'].astype(str).str.startswith('UQT2') | u['MLSFC_CL'].astype(str).str.startswith('UQT2')].copy()
CODE = {'UQT205': '소공원', 'UQT210': '어린이공원', 'UQT220': '근린공원', 'UQT230': '도시자연공원', 'UQT240': '묘지공원',
        'UQT250': '체육공원', 'UQT260': '역사공원', 'UQT270': '문화공원', 'UQT280': '수변공원', 'UQT290': '공원시설 기타', 'UQT200': '공원(세분 미상)'}
park['facility_subtype'] = park['MLSFC_CL'].map(CODE).fillna(park['ATRB_SE'].map(CODE)).fillna('공원(세분 미상)')
park['area_m2'] = park.area.round(1); park['area_in_seoul_m2'] = park.geometry.intersection(seoul).area.round(1)
park['facility_id'] = 'UPIS_' + park['PRESENT_SN'].astype(str)
fac.to_gpkg(park[['facility_id', 'PRESENT_SN', 'LCLAS_CL', 'MLSFC_CL', 'ATRB_SE', 'facility_subtype', 'DGM_NM', 'DGM_AR', 'SIGNGU_SE',
                  'EXCUT_SE', 'CREATE_DAT', 'area_m2', 'area_in_seoul_m2', 'geometry']], HERE / 'parks_official_2025_01.gpkg')
c = park.geometry.centroid; inpoly = c.within(park.geometry); pt = c.where(inpoly, park.geometry.representative_point())
o = pd.DataFrame({'facility_id': park['facility_id'].values, 'x_5179': pt.x.values, 'y_5179': pt.y.values})
o['category_group'] = '문화체육녹지'; o['facility_type'] = '공원(도시계획시설)'; o['facility_subtype'] = park['facility_subtype'].values
o['year_snapshot'] = '2025_01'; o['name'] = park['DGM_NM'].values; o['address'] = None; o['coord_method'] = 'source'; o['grade'] = 'A'
o['source_org'] = '서울특별시 도시계획국(UPIS)'; o['source_dataset'] = '서울시 도시계획시설(공간시설) UQ153 2024.11.07판'
o['source_url'] = 'https://data.seoul.go.kr/dataList/OA-21129/S/1/datasetView.do'; o['source_file'] = 'raw/OA-21129_UQ153_공간시설_20241107.zip'
o['source_row_id'] = park['PRESENT_SN'].astype(str).values; o['source_reference_date'] = '2024-11-07'
o['reference_month_delta'] = fac.month_delta('2024-11-07', '2025_01'); o['temporal_reason'] = '2024-11-07 배포본(허용창 내). 결정(계획) 시설로 미조성 포함 가능'
o['point_rule'] = np.where(inpoly.values, 'centroid', 'representative_point'); o['sz_area_m2'] = park['area_m2'].values
o['sz_area_in_seoul_m2'] = park['area_in_seoul_m2'].values; o['excut_se'] = park['EXCUT_SE'].values
o = fac.attach_geo(o, x='x_5179', y='y_5179')
base = HERE / 'facilities_park_official_2025_01'
o = fac.finalize(o); o.to_csv(str(base) + '.csv', index=False, encoding='utf-8-sig')
o2 = o.copy()
for cc in o2.columns:
    if o2[cc].dtype == object: o2[cc] = o2[cc].astype('string')
o2.to_parquet(str(base) + '.parquet', index=False)
qo = fac.qa_block(o)
un_off = park.geometry.union_all().intersection(seoul)
qo.update(source_crs=crs_src, layer_rows=len(u), park_rows=len(park), excut_se=park['EXCUT_SE'].value_counts().to_dict(),
          area_in_seoul_km2=round(park['area_in_seoul_m2'].sum() / 1e6, 3), union_area_in_seoul_km2=round(un_off.area / 1e6, 3),
          by_subtype_area_km2=(park.groupby('facility_subtype')['area_in_seoul_m2'].sum() / 1e6).round(3).to_dict())
qa['official_2025_01'] = qo
# ---- 2025 대조 ----
g = osm['2025_01']; gp = g[g['facility_subtype'] == 'leisure=park']
un_osm = gp.geometry.union_all().intersection(seoul); un_all = g.geometry.union_all().intersection(seoul)
cmp = dict(osm_leisure_park_count=len(gp), official_park_count=len(park),
           osm_leisure_park_union_km2=round(un_osm.area / 1e6, 3), osm_all_tags_union_km2=round(un_all.area / 1e6, 3),
           official_union_km2=round(un_off.area / 1e6, 3),
           official_area_covered_by_osm_park_km2=round(un_off.intersection(un_osm).area / 1e6, 3),
           official_area_covered_by_osm_all_km2=round(un_off.intersection(un_all).area / 1e6, 3))
cmp['official_area_covered_share_osm_park'] = round(cmp['official_area_covered_by_osm_park_km2'] / cmp['official_union_km2'], 3)
cmp['official_area_covered_share_osm_all'] = round(cmp['official_area_covered_by_osm_all_km2'] / cmp['official_union_km2'], 3)
# 개수 기준: 공식 공원 폴리곤 중 OSM 공원과 면적 20% 이상 겹치는 비율 (세부유형별)
sj = gpd.overlay(park[['facility_id', 'facility_subtype', 'area_m2', 'geometry']], gpd.GeoDataFrame(geometry=[un_all], crs=5179), how='intersection')
ov = sj.assign(a=sj.area).groupby('facility_id')['a'].sum()
park['osm_cover'] = (park['facility_id'].map(ov).fillna(0) / park['area_m2']).clip(0, 1)
cmp['official_matched_ge20pct_by_subtype'] = park.assign(m=park['osm_cover'] >= 0.2).groupby('facility_subtype')['m'].agg(['sum', 'count']).astype(int).to_dict('index')
cmp['official_matched_ge20pct_total'] = int((park['osm_cover'] >= 0.2).sum())
qa['compare_2025_osm_vs_official'] = cmp
fac.dump_qa(HERE, TYP, qa)
print(json.dumps({k: qa[k] for k in ['compare_2025_osm_vs_official']}, ensure_ascii=False, default=str)[:3000])
for s in ['2020_01', '2025_01']: print(s, {k: qa[s][k] for k in ['rows', 'leisure_park_count', 'leisure_park_union_area_in_seoul_km2', 'all_tags_union_area_in_seoul_km2', 'subtype', 'excluded_access_private_or_no']})
