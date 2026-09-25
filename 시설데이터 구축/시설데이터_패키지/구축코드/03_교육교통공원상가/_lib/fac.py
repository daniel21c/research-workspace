# -*- coding: utf-8 -*-
"""03_교육교통공원상가 공통 유틸 (다운로드+metadata, 공간 결합, 출력, 지오코딩).
경로는 이 파일 위치 기준 상대경로 → Windows에서도 동작."""
import os, re, json, hashlib, datetime, time
from pathlib import Path
import requests
import numpy as np
import pandas as pd

GROUP = Path(__file__).resolve().parents[1]           # .../시설_2020_2025_v1/03_교육교통공원상가
V1 = GROUP.parent                                     # .../시설_2020_2025_v1
BASE = V1.parent                                      # .../시설데이터 구축
SGIS = BASE / 'SGIS_인구경계_2019_2024'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'
S = requests.Session(); S.headers['User-Agent'] = UA

SNAP = {'2020_01': dict(ref='2019-12-31', lo='2019-09-01', hi='2020-05-31'),
        '2025_01': dict(ref='2024-12-31', lo='2024-09-01', hi='2025-05-31')}

COMMON = ['facility_id', 'category_group', 'facility_type', 'facility_subtype', 'year_snapshot', 'name', 'address',
          'lon', 'lat', 'x_5179', 'y_5179', 'coord_method', 'grade', 'source_org', 'source_dataset', 'source_url',
          'source_file', 'source_row_id', 'source_reference_date', 'reference_month_delta', 'temporal_reason',
          'inside_seoul', 'adm_dong_cd', 'oa_cd', 'grid100_cd']


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256(p, bs=1 << 20):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(bs), b''):
            h.update(b)
    return h.hexdigest()


def _meta_path(dest):
    dest = Path(dest)
    return dest.with_name(dest.name + '.metadata.json')


def write_meta(dest, **kw):
    dest = Path(dest)
    m = dict(kw)
    if dest.exists():
        m.setdefault('bytes', dest.stat().st_size)
        m.setdefault('sha256', sha256(dest))
    json.dump(m, open(_meta_path(dest), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return m


def fetch(url, dest, method='GET', data=None, params=None, headers=None, ref_date='', note='', force=False,
          timeout=170, verify=True):
    """원본을 받아 dest에 저장하고 dest.metadata.json 작성. 이미 있으면 건너뜀(재현 시 force=True)."""
    dest = Path(dest); dest.parent.mkdir(parents=True, exist_ok=True)
    mp = _meta_path(dest)
    if dest.exists() and mp.exists() and not force:
        return json.load(open(mp, encoding='utf-8'))
    t = utcnow()
    r = S.request(method, url, data=data, params=params, headers=headers or {}, timeout=timeout, stream=True,
                  verify=verify)
    tmp = dest.with_name(dest.name + '.part')
    with open(tmp, 'wb') as f:
        for c in r.iter_content(1 << 16):
            f.write(c)
    os.replace(tmp, dest)
    return write_meta(dest, url=url, method=method, params=params, data=data, download_utc=t,
                      http_status=r.status_code, content_disposition=r.headers.get('Content-Disposition'),
                      content_type=r.headers.get('Content-Type'), reference_date=ref_date, note=note)


def seoul_sheet(inf, dest, ref_date='', note=''):
    return fetch('https://datafile.seoul.go.kr/bigfile/iot/sheet/csv/download.do', dest, 'POST',
                 data=dict(srvType='S', infId=inf, serviceKind=1, pageNo=1, ssUserId='SAMPLE_VIEW', strWhere='',
                           strOrderby='', filterCol='', txtFilter=''), ref_date=ref_date, note=note)


def seoul_file(inf, seq, infseq, dest, ref_date='', note=''):
    return fetch('https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false', dest, 'POST',
                 data={'infId': inf, 'seqNo': '', 'seq': str(seq), 'infSeq': str(infseq)}, ref_date=ref_date,
                 note=note)


def read_csv_any(p, **k):
    for e in ['utf-8-sig', 'cp949', 'euc-kr']:
        try:
            return pd.read_csv(p, dtype=str, encoding=e, **k)
        except UnicodeDecodeError:
            pass
    raise ValueError(p)


def month_delta(src_date, snap):
    """원천 기준일과 목표(2020-01-01 / 2025-01-01) 사이 월 차이(원천-목표, 월 단위 반올림)."""
    if not src_date:
        return None
    d = pd.Timestamp(src_date); tgt = pd.Timestamp('2020-01-01' if snap == '2020_01' else '2025-01-01')
    return int(round((d - tgt).days / 30.44))


def in_window(src_date, snap):
    w = SNAP[snap]; d = pd.Timestamp(src_date)
    return pd.Timestamp(w['lo']) <= d <= pd.Timestamp(w['hi'])


# ---------------- 공간 결합 ----------------
_BND = {}


def _bnd():
    if _BND:
        return _BND
    import geopandas as gpd
    b = SGIS / '03_행정구역' / '경계_2025_2Q'
    sido = gpd.read_file(b / 'bnd_sido_00_2025_2Q' / 'bnd_sido_00_2025_2Q.shp')
    _BND['seoul'] = sido[sido['SIDO_CD'].astype(str) == '11'].to_crs(5179)
    dong = gpd.read_file(b / 'bnd_dong_00_2025_2Q' / 'bnd_dong_00_2025_2Q.shp')
    _BND['dong'] = dong[dong['ADM_CD'].astype(str).str.startswith('11')][['ADM_CD', 'geometry']].to_crs(5179)
    oa = gpd.read_file(SGIS / '02_집계구' / '경계_2025_2Q' / 'bnd_oa_00_2025_2Q.shp')
    _BND['oa'] = oa[oa['ADM_CD'].astype(str).str.startswith('11')][['TOT_OA_CD', 'geometry']].to_crs(5179)
    return _BND


def seoul_geom():
    return _bnd()['seoul'].geometry.union_all() if hasattr(_bnd()['seoul'].geometry, 'union_all') else \
        _bnd()['seoul'].geometry.unary_union


def grid100(x, y):
    """SGIS 100m 격자코드: '다사' + floor((x-900000)/100) 3자리 + floor((y-1900000)/100) 3자리 (다사 도엽 밖이면 None)."""
    out = []
    for a, b in zip(x, y):
        if a is None or b is None or (isinstance(a, float) and np.isnan(a)) or (isinstance(b, float) and np.isnan(b)):
            out.append(None); continue
        i, j = int((a - 900000) // 100), int((b - 1900000) // 100)
        out.append(f'다사{i:03d}{j:03d}' if 0 <= i < 1000 and 0 <= j < 1000 else None)
    return out


def attach_geo(df, lon='lon', lat='lat', x=None, y=None):
    """lon/lat(4326) 또는 x/y(5179)에서 x_5179,y_5179,lon,lat,inside_seoul,adm_dong_cd,oa_cd,grid100_cd 채움."""
    import geopandas as gpd
    from pyproj import Transformer
    df = df.copy()
    if x and y:
        xs = pd.to_numeric(df[x], errors='coerce'); ys = pd.to_numeric(df[y], errors='coerce')
        t = Transformer.from_crs(5179, 4326, always_xy=True)
        lo, la = t.transform(xs.values, ys.values)
        df['lon'] = np.where(xs.notna(), lo, np.nan); df['lat'] = np.where(xs.notna(), la, np.nan)
        df['x_5179'] = xs; df['y_5179'] = ys
    else:
        lo = pd.to_numeric(df[lon], errors='coerce'); la = pd.to_numeric(df[lat], errors='coerce')
        bad = ~((lo > 120) & (lo < 135) & (la > 30) & (la < 45))
        lo[bad] = np.nan; la[bad] = np.nan
        df['lon'] = lo; df['lat'] = la
        t = Transformer.from_crs(4326, 5179, always_xy=True)
        xx, yy = t.transform(lo.fillna(0).values, la.fillna(0).values)
        df['x_5179'] = np.where(lo.notna(), xx, np.nan); df['y_5179'] = np.where(lo.notna(), yy, np.nan)
    has = df['x_5179'].notna()
    pts = gpd.GeoDataFrame(df.loc[has, []], geometry=gpd.points_from_xy(df.loc[has, 'x_5179'], df.loc[has, 'y_5179']),
                           crs=5179)
    B = _bnd()
    ins = gpd.sjoin(pts, B['seoul'][['geometry']], how='left', predicate='intersects')
    ins = ins[~ins.index.duplicated()]
    df['inside_seoul'] = pd.Series(pd.NA, index=df.index, dtype='boolean')
    df.loc[has, 'inside_seoul'] = ins['index_right'].notna().values
    d = gpd.sjoin(pts, B['dong'], how='left', predicate='intersects'); d = d[~d.index.duplicated()]
    df['adm_dong_cd'] = None; df.loc[has, 'adm_dong_cd'] = d['ADM_CD'].values
    o = gpd.sjoin(pts, B['oa'], how='left', predicate='intersects'); o = o[~o.index.duplicated()]
    df['oa_cd'] = None; df.loc[has, 'oa_cd'] = o['TOT_OA_CD'].values
    df['grid100_cd'] = grid100(df['x_5179'].tolist(), df['y_5179'].tolist())
    df['x_5179'] = df['x_5179'].round(2); df['y_5179'] = df['y_5179'].round(2)
    return df


def finalize(df, extra_first=()):
    for c in COMMON:
        if c not in df.columns:
            df[c] = None
    rest = [c for c in df.columns if c not in COMMON]
    sz = [c for c in rest if c.startswith('sz_')]
    oth = [c for c in rest if not c.startswith('sz_')]
    return df[COMMON + sz + oth]


def write_out(df, tdir, typ, snap):
    tdir = Path(tdir); df = finalize(df)
    base = tdir / f'facilities_{typ}_{snap}'
    df.to_csv(str(base) + '.csv', index=False, encoding='utf-8-sig')
    d2 = df.copy()
    for c in d2.columns:
        if d2[c].dtype == object:
            d2[c] = d2[c].astype('string')
    d2.to_parquet(str(base) + '.parquet', index=False)
    return df


def qa_block(df):
    n = len(df)
    q = dict(rows=n,
             coord_rate=round(float(df['x_5179'].notna().mean()), 4) if n else None,
             coord_method=df['coord_method'].value_counts(dropna=False).to_dict(),
             inside_seoul=int((df['inside_seoul'] == True).sum()),
             outside_seoul=int((df['inside_seoul'] == False).sum()),
             no_coord=int(df['x_5179'].isna().sum()),
             grade=df['grade'].value_counts(dropna=False).to_dict(),
             dup_facility_id=int(df['facility_id'].duplicated().sum()),
             subtype=df['facility_subtype'].value_counts(dropna=False).to_dict())
    xy = df[['x_5179', 'y_5179']].dropna()
    q['dup_exact_xy'] = int(xy.duplicated().sum())
    return q


def dump_qa(tdir, typ, qa):
    def conv(o):
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return None if np.isnan(o) else float(o)
        if isinstance(o, (np.bool_,)): return bool(o)
        if isinstance(o, (pd.Timestamp,)): return str(o)
        return str(o)
    qa = dict(qa); qa['generated_utc'] = utcnow()
    rf = []
    for m in sorted(Path(tdir, 'raw').glob('*.metadata.json')):
        j = json.load(open(m, encoding='utf-8'))
        rf.append({k: j.get(k) for k in ['url', 'method', 'params', 'data', 'download_utc', 'http_status', 'bytes',
                                         'sha256', 'reference_date', 'note']} | {'file': m.name[:-14]})
    qa['raw_files'] = rf
    qa.pop('sources', None)
    json.dump(qa, open(Path(tdir) / f'qa_{typ}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1,
              default=conv)


# ---------------- 지오코딩 ----------------
def _env():
    for p in [os.environ.get('FACILITY_API_ENV', ''), BASE.parent / '_secrets' / 'facility_api.env',
              Path.home() / 'mnt' / '_secrets' / 'facility_api.env', Path('D:/Research/_secrets/facility_api.env')]:
        if p and Path(p).exists():
            e = {}
            for l in open(p, encoding='utf-8'):
                m = re.match(r'\s*([A-Za-z_.]+)\s*=\s*(.*?)\s*$', l)
                if m and not l.strip().startswith('#'):
                    e[m.group(1)] = m.group(2)
            return e
    return {}


ROAD_RE = re.compile(r'^(.*?[가-힣A-Za-z0-9·.]+(?:로|길))\s*(\d+)(?:\s*-\s*(\d+))?(?![\d가길번동])')
JIBUN_RE = re.compile(r'^(.*?[가-힣0-9]+(?:동|가|리|로\d*가))\s*(?:산\s*)?(\d+)(?:\s*-\s*(\d+))?(?!\d)')


def clean_addr(a):
    """주소를 '…로/길 번호[-부번]' 또는 '…동 번지[-부번]'까지로 자른다(층·호·괄호 제거)."""
    if a is None or (isinstance(a, float) and np.isnan(a)):
        return None, None
    a = re.sub(r'\([^)]*\)', ' ', str(a)); a = re.sub(r'\s+', ' ', a).strip()
    a = a.replace('서울시 ', '서울특별시 ')
    if not a.startswith('서울'):
        a = '서울특별시 ' + a
    m = ROAD_RE.match(a)
    if m:
        return 'road', (f'{m.group(1)} {m.group(2)}' + (f'-{m.group(3)}' if m.group(3) else ''), m.group(2),
                        m.group(3) or '0')
    m = JIBUN_RE.match(a)
    if m:
        return 'jibun', (f'{m.group(1)} {m.group(2)}' + (f'-{m.group(3)}' if m.group(3) else ''), m.group(2),
                         m.group(3) or '0')
    return None, None


def _cache(cdir, key):
    cdir = Path(cdir); cdir.mkdir(parents=True, exist_ok=True)
    return cdir / (hashlib.sha1(key.encode('utf-8')).hexdigest() + '.json')


def geocode(addr, cdir):
    """(lon, lat, method, matched) 반환. 도로명+건물번호 또는 지번 번지 일치만 채택."""
    kind, p = clean_addr(addr)
    if not kind:
        return None, None, 'unresolved', 'unparsable'
    q, main, sub = p
    env = None
    # kakao
    cf = _cache(cdir, 'kakao|' + q)
    if cf.exists():
        j = json.load(open(cf, encoding='utf-8'))
    else:
        env = env or _env()
        k = env.get('KAKAO_REST_API_KEY')
        j = None
        if k:
            for _ in range(3):
                try:
                    r = S.get('https://dapi.kakao.com/v2/local/search/address.json', params={'query': q},
                              headers={'Authorization': 'KakaoAK ' + k}, timeout=20)
                    j = r.json(); break
                except Exception:
                    time.sleep(2)
            if j is not None:
                json.dump({'query': q, 'response': j}, open(cf, 'w', encoding='utf-8'), ensure_ascii=False)
                j = {'query': q, 'response': j}
    if j:
        for d in j['response'].get('documents', []) or []:
            ra, pa = d.get('road_address') or {}, d.get('address') or {}
            if kind == 'road' and d.get('address_type') == 'ROAD_ADDR' and ra.get('main_building_no') == main \
                    and (ra.get('sub_building_no') or '0') == sub:
                return float(d['x']), float(d['y']), 'geocode_kakao_exact', ra.get('address_name')
            if kind == 'jibun' and d.get('address_type') == 'REGION_ADDR' and pa.get('main_address_no') == main \
                    and (pa.get('sub_address_no') or '0') == sub:
                return float(d['x']), float(d['y']), 'geocode_kakao_exact', pa.get('address_name')
    # vworld
    cf = _cache(cdir, 'vworld|' + kind + '|' + q)
    if cf.exists():
        j = json.load(open(cf, encoding='utf-8'))
    else:
        env = env or _env(); k = env.get('VWORLD_API_KEY'); j = None
        if k:
            for _ in range(3):
                try:
                    r = S.get('https://api.vworld.kr/req/address',
                              params={'service': 'address', 'request': 'getcoord', 'version': '2.0',
                                      'crs': 'epsg:4326', 'address': q, 'refine': 'true', 'simple': 'false',
                                      'format': 'json', 'type': 'road' if kind == 'road' else 'parcel', 'key': k},
                              timeout=20)
                    j = r.json(); break
                except Exception:
                    time.sleep(2)
            if j is not None:
                j = {'query': q, 'response': j}
                json.dump(j, open(cf, 'w', encoding='utf-8'), ensure_ascii=False)
    if j:
        rs = j['response'].get('response', {})
        if rs.get('status') == 'OK':
            st = rs.get('refined', {}).get('structure', {}); l5 = str(st.get('level5', ''))
            want = main + ('' if sub == '0' else '-' + sub)
            if l5 == want or l5.replace('번지', '') == want:
                pt = rs['result']['point']
                return float(pt['x']), float(pt['y']), 'geocode_vworld_exact', rs.get('refined', {}).get('text')
    return None, None, 'unresolved', 'no_exact_match'


def geocode_df(df, addr_col, cdir, lon='lon', lat='lat'):
    """좌표 없는 행만 지오코딩. coord_method 갱신."""
    need = df[lon].isna() & df[addr_col].notna()
    res = {}
    for a in df.loc[need, addr_col].unique():
        res[a] = geocode(a, cdir)
    for i in df.index[need]:
        x, y, m, _ = res[df.at[i, addr_col]]
        if x is not None:
            df.at[i, lon] = x; df.at[i, lat] = y
        df.at[i, 'coord_method'] = m
    df.loc[df[lon].isna(), 'coord_method'] = 'unresolved'
    return df


def unzip(zp, outdir):
    """zip 해제(cp949 파일명 복원). 해제된 파일 경로 목록 반환."""
    import zipfile
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True); out = []
    with zipfile.ZipFile(zp) as z:
        for i in z.infolist():
            n = i.filename
            if not (i.flag_bits & 0x800):
                try:
                    n = n.encode('cp437').decode('cp949')
                except Exception:
                    pass
            if n.endswith('/'):
                continue
            p = outdir / n
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                with z.open(i) as src, open(p, 'wb') as dst:
                    dst.write(src.read())
            out.append(p)
    return out


def to_gpkg(g, dest, layer=None):
    """네트워크/동기화 드라이브에서 sqlite 잠금 문제가 있어 임시폴더에 쓴 뒤 복사."""
    import tempfile, shutil
    dest = Path(dest)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / dest.name
        g.to_file(t, driver='GPKG', layer=layer or dest.stem)
        shutil.copyfile(t, dest)
