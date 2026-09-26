"""지방행정 인허가(구 LOCALDATA) 현재 전체 이력 → 2019-12-31·2024-12-31 운영 시설 역산 공통 모듈.

00_SPEC.md(B 등급 역산 규칙)를 구현한다. 각 유형 폴더의 build_<유형>.py 가 CFG 를 넘겨 build() 를 호출한다.
모든 경로는 이 파일 기준 상대경로이므로 Windows(D:\\...\\시설데이터 구축\\...)에서도 그대로 실행된다.
API 키 값은 읽기만 하고 출력·저장하지 않는다.
"""
from __future__ import annotations
import hashlib, json, os, re, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

COMMON = Path(__file__).resolve().parent
LIC_ROOT = COMMON.parent                      # 01_인허가
V1_ROOT = LIC_ROOT.parent                     # 시설_2020_2025_v1
BASE = V1_ROOT.parent                         # 시설데이터 구축
SGIS = BASE / 'SGIS_인구경계_2019_2024'
DONG_SHP = SGIS / '03_행정구역/경계_2025_2Q/bnd_dong_00_2025_2Q/bnd_dong_00_2025_2Q.shp'
SIDO_SHP = SGIS / '03_행정구역/경계_2025_2Q/bnd_sido_00_2025_2Q/bnd_sido_00_2025_2Q.shp'
OA_SHP = SGIS / '02_집계구/경계_2025_2Q/bnd_oa_00_2025_2Q.shp'
CACHE = COMMON / 'cache'

SNAPS = {'2020_01': pd.Timestamp('2019-12-31'), '2025_01': pd.Timestamp('2024-12-31')}
TARGET_MONTH = {'2020_01': (2020, 1), '2025_01': (2025, 1)}
SEOUL_SHEET_URL = 'https://datafile.seoul.go.kr/bigfile/iot/sheet/csv/download.do'
LOCALDATA_URL = 'https://file.localdata.go.kr/file/download/{slug}/info?orgCode=6110000_ALL'
CLOSED_CODES = {'03', '04', '05'}   # 03 폐업, 04 취소/말소/만료/정지/중지, 05 제외/삭제/전출
BULK_N = 20   # 같은 날 일괄 말소로 보는 최소 건수
CLOSED_PAT = r'폐업|취소|말소|만료|폐쇄|폐지|전출|제외|삭제'
COMMON_COLS = ['facility_id', 'category_group', 'facility_type', 'facility_subtype', 'year_snapshot', 'name', 'address',
               'lon', 'lat', 'x_5179', 'y_5179', 'coord_method', 'grade', 'source_org', 'source_dataset', 'source_url',
               'source_file', 'source_row_id', 'source_reference_date', 'reference_month_delta', 'temporal_reason',
               'inside_seoul', 'adm_dong_cd', 'oa_cd', 'grid100_cd']

# ---------------------------------------------------------------- 날짜
def todt(s: pd.Series, cap: bool = True) -> pd.Series:
    """cap=True: 2027-01-01 이후 날짜를 결측(입력 오류로 간주). 휴업 시작·종료일은 cap=False로 읽는다(2026-09-25 보정:
    휴업종료일 ≥ 2027인 장기 휴업이 휴업 제외 규칙에서 빠지던 문제, 12_무결성보정/02_fix_suspension.py 참고)."""
    s = s.fillna('').astype(str).str.strip().str.slice(0, 10).str.replace(r'[./]', '-', regex=True)
    s = s.where(~s.str.match(r'^\d{8}$'), s.str.slice(0, 4) + '-' + s.str.slice(4, 6) + '-' + s.str.slice(6, 8))
    d = pd.to_datetime(s, errors='coerce', format='%Y-%m-%d')
    return d.where((d > pd.Timestamp('1901-01-01')) & ((d < pd.Timestamp('2027-01-01')) | (not cap)))

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def detect_enc(p: Path) -> str:
    with open(p, 'rb') as f:
        b = f.read(400000)
    if b.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    try:
        b.decode('utf-8'); return 'utf-8'
    except UnicodeDecodeError as e:
        if e.start > len(b) - 4:
            return 'utf-8'
        return 'cp949'

# ---------------------------------------------------------------- 좌표·경계
_TF = {}
def tf(a, b):
    from pyproj import Transformer
    if (a, b) not in _TF:
        _TF[(a, b)] = Transformer.from_crs(a, b, always_xy=True)
    return _TF[(a, b)]

X_LETTERS = '가나다라마바사아자차카타파하'
def grid100(x, y):
    """SGIS/국가지점번호 체계 100m 격자 코드 (EPSG:5179): 문자(x 100km: 가=700000) + 문자(y 100km: 가=1300000) + x3 + y3."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    out = np.full(x.shape, None, dtype=object)
    ok = np.isfinite(x) & np.isfinite(y)
    xi = np.floor((x[ok] - 700000) / 100000).astype(int); yi = np.floor((y[ok] - 1300000) / 100000).astype(int)
    xr = np.floor((x[ok] % 100000) / 100).astype(int); yr = np.floor((y[ok] % 100000) / 100).astype(int)
    res = []
    for a, b, c, d in zip(xi, yi, xr, yr):
        res.append(f'{X_LETTERS[a]}{X_LETTERS[b]}{c:03d}{d:03d}' if 0 <= a < 14 and 0 <= b < 14 else None)
    out[ok] = res
    return out

def boundaries():
    import geopandas as gpd
    CACHE.mkdir(exist_ok=True)
    fs = {k: CACHE / f'seoul_{k}_2025_2Q.parquet' for k in ('sido', 'dong', 'oa')}
    if not all(p.exists() for p in fs.values()):
        s = gpd.read_file(SIDO_SHP); s = s[s.SIDO_CD.astype(str) == '11'][['SIDO_CD', 'geometry']]
        d = gpd.read_file(DONG_SHP); d = d[d.ADM_CD.astype(str).str.startswith('11')][['ADM_CD', 'ADM_NM', 'geometry']]
        o = gpd.read_file(OA_SHP); o = o[o.ADM_CD.astype(str).str.startswith('11')][['ADM_CD', 'TOT_OA_CD', 'geometry']]
        for k, g in (('sido', s), ('dong', d), ('oa', o)):
            g.to_crs(5179).to_parquet(fs[k])
        json.dump({'sources': {k: str(p.relative_to(BASE)) for k, p in (('sido', SIDO_SHP), ('dong', DONG_SHP), ('oa', OA_SHP))},
                   'filter': 'SIDO_CD==11 / ADM_CD startswith 11', 'crs': 'EPSG:5179',
                   'created_utc': datetime.now(timezone.utc).isoformat()},
                  open(CACHE / 'README_cache.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return {k: gpd.read_parquet(p) for k, p in fs.items()}

def spatial_attach(df: pd.DataFrame) -> pd.DataFrame:
    import geopandas as gpd
    B = boundaries()
    df = df.copy()
    df['inside_seoul'] = pd.NA; df['adm_dong_cd'] = None; df['oa_cd'] = None; df['grid100_cd'] = None
    ok = df.x_5179.notna() & df.y_5179.notna()
    if ok.sum() == 0:
        return df
    pts = gpd.GeoDataFrame(index=df.index[ok], geometry=gpd.points_from_xy(df.loc[ok, 'x_5179'], df.loc[ok, 'y_5179']), crs=5179)
    ins = gpd.sjoin(pts, B['sido'], predicate='within', how='left')
    ins = ins[~ins.index.duplicated()]
    df.loc[ok, 'inside_seoul'] = ins['SIDO_CD'].notna().values
    dj = gpd.sjoin(pts, B['dong'][['ADM_CD', 'geometry']], predicate='within', how='left'); dj = dj[~dj.index.duplicated()]
    df.loc[ok, 'adm_dong_cd'] = dj['ADM_CD'].values
    oj = gpd.sjoin(pts, B['oa'][['TOT_OA_CD', 'geometry']], predicate='within', how='left'); oj = oj[~oj.index.duplicated()]
    df.loc[ok, 'oa_cd'] = oj['TOT_OA_CD'].values
    df.loc[ok, 'grid100_cd'] = grid100(df.loc[ok, 'x_5179'].values, df.loc[ok, 'y_5179'].values)
    return df

# ---------------------------------------------------------------- 지오코딩 (Kakao → VWorld, 건물번호/번지 일치만 채택)
def load_keys():
    # API 키: 환경변수 FACILITY_API_ENV 또는 00_박사논문_연구체계/_secrets/facility_api.env (공유본에 없음, 받은 쪽은 자기 키를 넣는다)
    cands = [os.environ.get('FACILITY_API_ENV', ''), str(next(p for p in Path(__file__).resolve().parents if (p / '시설데이터 구축').is_dir()) / '_secrets' / 'facility_api.env')]
    for c in cands:
        if c and Path(c).exists():
            out = {}
            for line in Path(c).read_text(encoding='utf-8-sig').splitlines():
                if '=' in line and not line.lstrip().startswith('#'):
                    k, v = line.split('=', 1); out[k.strip()] = v.strip().strip('"\'')
            return out
    return {}

def address_key(v):
    """'road:구|도로명|건물번호' 또는 'parcel:구|동|번지' — 정확 일치 비교용."""
    v = re.sub(r'^서울(?:특별시|시)(?=\s)', '서울', re.sub(r'\([^)]*\)', '', str(v)))
    v = re.sub(r'(로|길)\s+(\d+[가-힣]*길)', r'\1\2', v)
    m = re.search(r'서울\s*([가-힣]+구)\s+(.+)', v)
    if not m:
        return ''
    rest = m[2]
    road = re.search(r'(?:^|\s)([가-힣0-9·.]+(?:로|길))\s*(\d+(?:-\d+)?)(?=$|[\s,.(]|번지)', rest)
    if road:
        return 'road:' + '|'.join((m[1], road[1], road[2]))
    rest = re.sub(r'(\d+)번지\s*(\d+)호', r'\1-\2', rest)
    parcel = re.search(r'([가-힣0-9]+(?:동|가|리))\s*(?:산\s*)?(\d+(?:-\d+)?)(?:번지)?(?=$|[\s,(]|번지)', rest)
    return 'parcel:' + '|'.join((m[1], parcel[1], parcel[2])) if parcel else ''

def geocode_one(key, secret, cache_dir: Path):
    """key: address_key. 캐시 파일명은 key 의 sha256. 반환 (lon, lat, method) 또는 None."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    p = cache_dir / (hashlib.sha256(key.encode()).hexdigest() + '.json')
    r = None
    if p.exists():
        try:
            r = json.loads(p.read_text(encoding='utf-8'))
        except ValueError:
            r = None                                   # 중단으로 깨진 캐시 → 재조회 후 덮어씀
    if r is None:
        kind, body = key.split(':', 1); gu, a, b = body.split('|')
        q = f'서울특별시 {gu} {a} {b}'
        r = {'address_key': key, 'query': q, 'queried_at_utc': datetime.now(timezone.utc).isoformat(), 'kakao': None, 'vworld': None}
        if secret.get('KAKAO_REST_API_KEY'):
            url = 'https://dapi.kakao.com/v2/local/search/address.json?' + urllib.parse.urlencode({'query': q, 'analyze_type': 'exact'})
            try:
                req = urllib.request.Request(url, headers={'Authorization': 'KakaoAK ' + secret['KAKAO_REST_API_KEY']})
                with urllib.request.urlopen(req, timeout=8) as h:
                    r['kakao'] = {'endpoint': url, 'status': h.status, 'response': json.load(h)}
            except Exception as e:
                r['kakao'] = {'endpoint': url, 'error': type(e).__name__, 'http_status': getattr(e, 'code', None)}
            time.sleep(0.05)
        docs = ((r.get('kakao') or {}).get('response') or {}).get('documents', [])
        if not any(_kakao_match(d, key) for d in docs) and secret.get('VWORLD_API_KEY'):
            prm = {'service': 'address', 'request': 'getcoord', 'version': '2.0', 'crs': 'epsg:4326', 'refine': 'true',
                   'simple': 'false', 'format': 'json', 'type': 'road' if kind == 'road' else 'parcel', 'address': q}
            url_nokey = 'https://api.vworld.kr/req/address?' + urllib.parse.urlencode(prm)
            try:
                with urllib.request.urlopen(url_nokey + '&key=' + urllib.parse.quote(secret['VWORLD_API_KEY']), timeout=8) as h:
                    r['vworld'] = {'endpoint': url_nokey, 'status': h.status, 'response': json.load(h)}
            except Exception as e:
                r['vworld'] = {'endpoint': url_nokey, 'error': type(e).__name__, 'http_status': getattr(e, 'code', None)}
            time.sleep(0.05)
        tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding='utf-8'); os.replace(tmp, p)
    for d in ((r.get('kakao') or {}).get('response') or {}).get('documents', []):
        if _kakao_match(d, key):
            return float(d['x']), float(d['y']), 'geocode_kakao_exact'
    vw = ((r.get('vworld') or {}).get('response') or {}).get('response', {})
    if vw.get('status') == 'OK':
        ref = (vw.get('refined') or {}).get('text', '')
        if address_key(ref) == key:
            pt = vw['result']['point']; return float(pt['x']), float(pt['y']), 'geocode_vworld_exact'
    return None

def _kakao_match(d, key):
    ra = d.get('road_address') or {}; pa = d.get('address') or {}
    if key.startswith('road:'):
        return bool(ra) and address_key(ra.get('address_name', '')) == key
    return bool(pa) and address_key(pa.get('address_name', '')) == key

# ---------------------------------------------------------------- 원본 적재·역산
DATE_COLS = ['인허가일자', '인허가취소일자', '폐업일자', '휴업시작일자', '휴업종료일자', '최종수정일자', '최종수정시점']

def process_file(path: Path, slug: str, keep_cols, chunksize=150000):
    """전 행 상태 집계 + 두 기준일 중 하나라도 운영인 후보 행만 반환."""
    enc = detect_enc(path)
    st = dict(rows=0, status={}, lic_unknown=0, lic_dummy_1900_0001=0, lic_unknown_not_closed_pre2020=0,
              closed_nodate=0, closed_nodate_no_lastmod=0, active_status_with_end_date=0, end_before_lic=0,
              suspended_excluded={k: 0 for k in SNAPS}, substituted={k: 0 for k in SNAPS}, active={k: 0 for k in SNAPS},
              org_codes=set(), max_data_update=None, max_last_mod=None)
    out = []; rowbase = 0
    for ch in pd.read_csv(path, encoding=enc, encoding_errors='replace', dtype=str, chunksize=chunksize, low_memory=False):
        ch.columns = [c.strip().lstrip('\ufeff') for c in ch.columns]
        ch = ch.rename(columns={'최종수정시점': '최종수정일자', '데이터갱신시점': '데이터갱신일자'})
        for c in ch.columns:
            ch[c] = ch[c].str.strip()
        n = len(ch)
        ch['_src_row'] = np.arange(rowbase + 1, rowbase + n + 1); rowbase += n
        st['rows'] += n
        stname = ch.get('영업상태명', pd.Series('', index=ch.index)).fillna('')
        for k, v in stname.value_counts().items():
            st['status'][k] = st['status'].get(k, 0) + int(v)
        code = ch.get('영업상태코드', pd.Series('', index=ch.index)).fillna('').str.zfill(2)
        closed = code.isin(CLOSED_CODES) | ((code == '00') & stname.str.contains(CLOSED_PAT))
        closed = closed | (~code.isin({'01', '02', '03', '04', '05'}) & stname.str.contains(CLOSED_PAT))
        rawlic = ch['인허가일자'].fillna('')
        st['lic_dummy_1900_0001'] += int((rawlic.str.startswith('1900') | rawlic.str.startswith('0001')).sum())
        lic = todt(ch['인허가일자'])
        def g(c, cap=True):
            return todt(ch[c], cap) if c in ch else pd.Series(pd.NaT, index=ch.index)
        cl, ca, hs, he, fm = g('폐업일자'), g('인허가취소일자'), g('휴업시작일자', False), g('휴업종료일자', False), g('최종수정일자')
        end = cl.combine_first(ca)
        st['active_status_with_end_date'] += int((~closed & end.notna()).sum())
        end = end.where(closed)                      # 영업/휴업 상태의 종료일은 무시(재개업 등)
        nod = closed & end.isna()
        st['closed_nodate'] += int(nod.sum())
        st['closed_nodate_no_lastmod'] += int((nod & fm.isna()).sum())
        end2 = end.where(~nod, fm)
        endunk = closed & end2.isna()               # 종료 사실은 있으나 날짜 전혀 없음 → 판정 불가
        st['end_before_lic'] += int((end2.notna() & lic.notna() & (end2 < lic)).sum())
        st['lic_unknown'] += int(lic.isna().sum())
        st['lic_unknown_not_closed_pre2020'] += int((lic.isna() & ~(end2 < pd.Timestamp('2020-01-01'))).sum())
        keep = pd.Series(False, index=ch.index)
        for k, D in SNAPS.items():
            susp = hs.notna() & he.notna() & (hs <= D) & (he >= D)
            base = lic.notna() & (lic <= D) & (end2.isna() | (end2 > D)) & ~endunk
            a = base & ~susp
            ch['_endok_' + k] = (end2.isna() | (end2 > D)) & ~endunk & ~susp
            st['suspended_excluded'][k] += int((base & susp).sum())
            st['active'][k] += int(a.sum())
            st['substituted'][k] += int((a & nod).sum())
            ch['_active_' + k] = a
            keep |= a
        ch['_lic'] = lic; ch['_end'] = end2; ch['_end_substituted'] = nod; ch['_closed'] = closed
        if '개방자치단체코드' in ch:
            st['org_codes'].update(ch['개방자치단체코드'].dropna().unique().tolist())
        for c, kk in (('데이터갱신일자', 'max_data_update'), ('최종수정일자', 'max_last_mod')):
            if c in ch:
                m = ch[c].dropna().max()
                if isinstance(m, str) and (st[kk] is None or m > st[kk]):
                    st[kk] = m
        cols = [c for c in ch.columns if c in keep_cols or c.startswith('_')]
        out.append(ch.loc[keep, cols])
    st['org_codes'] = sorted(st['org_codes'])
    st['n_org_codes'] = len(st['org_codes'])
    st['all_org_codes_seoul'] = all(str(o).startswith('3') and len(str(o)) == 7 and 3000000 <= int(o) <= 3250000 for o in st['org_codes'] if str(o).isdigit())
    st['encoding'] = enc
    df = pd.concat(out, ignore_index=True) if out else pd.DataFrame()
    df['_slug'] = slug
    return df, st

# ---------------------------------------------------------------- 전출 이관 보정
def _norm_name(s):
    s = s.fillna('').str.replace(r'\([^)]*\)', '', regex=True)
    return s.str.replace(r'[^0-9A-Za-z가-힣]', '', regex=True).str.lower()

def fix_transfers(df):
    """자치구 간 이전(전출) 시 새 구 기록이 원 인허가일자를 승계해 두 기록이 동시에 운영으로 잡히는 문제 보정.
    같은 업종·정규화 사업장명·인허가일자 묶음에서 종료일 순으로 정렬해, 앞 기록이 모두 '전출'이면
    뒤 기록의 유효 시작일 = max(인허가일, 앞 기록 종료일)."""
    df = df.copy()
    df['_start'] = df['_lic']; df['_transfer_adjusted'] = False
    det = df.get('상세영업상태명', pd.Series('', index=df.index)).fillna('')
    stn = df.get('영업상태명', pd.Series('', index=df.index)).fillna('')
    is_tr = det.str.contains('전출') | ((det == '') & stn.str.contains('전출') & ~stn.str.contains('제외|삭제'))
    df['_is_transfer_out'] = is_tr
    info = {'transfer_out_rows_in_candidates': int(is_tr.sum()), 'groups': 0, 'adjusted_rows': 0, 'ambiguous_groups': 0,
            'removed_from_active': {}}
    if is_tr.sum() == 0:
        return df, info
    key = df['_slug'] + '|' + _norm_name(df['사업장명']) + '|' + df['_lic'].dt.strftime('%Y-%m-%d').fillna('NA')
    df['_tk'] = key
    ks = set(key[is_tr & df['_lic'].notna()])
    grp = df[key.isin(ks)]
    before = {k: int(df['_active_' + k].sum()) for k in SNAPS}
    for k_, g in grp.groupby('_tk'):
        if len(g) < 2:
            continue
        info['groups'] += 1
        g = g.assign(_o=g['_end'].fillna(pd.Timestamp('2100-01-01'))).sort_values(['_o', '_src_row'])
        if not g['_is_transfer_out'].iloc[:-1].all():
            info['ambiguous_groups'] += 1; continue
        prev_end = None
        for i in g.index:
            if prev_end is not None and pd.notna(prev_end) and prev_end > df.at[i, '_start']:
                df.at[i, '_start'] = prev_end; df.at[i, '_transfer_adjusted'] = True; info['adjusted_rows'] += 1
            prev_end = df.at[i, '_end']
    for k, D in SNAPS.items():
        df['_active_' + k] = df['_start'].notna() & (df['_start'] <= D) & df['_endok_' + k]
        info['removed_from_active'][k] = before[k] - int(df['_active_' + k].sum())
    return df, info

# ---------------------------------------------------------------- 원본 raw/ 배치 및 metadata
def stage_raw(src: dict, raw_dir: Path) -> dict:
    """src: {slug, local(작업 사본 경로), dest_name, kind('seoul_sheet'|'localdata'), oa, downloaded_utc, http_status, note}"""
    import shutil
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / src['dest_name']
    meta_p = raw_dir / (src['dest_name'] + '.metadata.json')
    if dest.exists() and meta_p.exists():
        return json.loads(meta_p.read_text(encoding='utf-8'))
    local = Path(src.get('local') or '/nonexistent')
    if not local.exists():
        raise FileNotFoundError(f'{dest} 없음 — raw/ 에 원본을 두거나 _common/download.py 로 재수신')
    shutil.copy2(local, dest)
    if src['kind'] == 'seoul_sheet':
        meta = {'url': SEOUL_SHEET_URL, 'method': 'POST',
                'params': {'srvType': 'S', 'infId': src['oa'], 'serviceKind': '1', 'pageNo': '1', 'ssUserId': 'SAMPLE_VIEW',
                           'strWhere': '', 'strOrderby': '', 'filterCol': '', 'txtFilter': ''},
                'dataset_page': f"https://data.seoul.go.kr/dataList/{src['oa']}/S/1/datasetView.do"}
    else:
        meta = {'url': LOCALDATA_URL.format(slug=src['slug']), 'method': 'GET',
                'params': {'orgCode': '6110000_ALL'}, 'pre_request': 'https://file.localdata.go.kr/file/validate/download-count (browser UA, cookie)'}
    meta.update({'file': src['dest_name'], 'slug': src['slug'], 'download_utc': src['downloaded_utc'],
                 'http_status': src.get('http_status'), 'bytes': dest.stat().st_size, 'sha256': sha256(dest),
                 'reference_date': None, 'note': src.get('note', '')})
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    return meta

def month_delta(ref: str, snap: str):
    try:
        y, m = int(ref[:4]), int(ref[5:7])
    except Exception:
        return None
    ty, tm = TARGET_MONTH[snap]
    return (y - ty) * 12 + (m - tm)

# ---------------------------------------------------------------- 메인 빌드
def build(cfg: dict, here: Path):
    """cfg keys: type, category_group, sources[list of src dict + subtype(fixed) ], subtype_fn(df)->Series,
    filter_fn(df)->mask, size_map{sz_col: expr|col}, attr_map{out: col}, geocode(bool), official_fn(out_dict)->dict"""
    t0 = time.time()
    here = Path(here); raw_dir = here / 'raw'
    T = cfg['type']
    parts, stats, metas = [], {}, {}
    keep_cols = set(['개방자치단체코드', '관리번호', '사업장명', '도로명주소', '지번주소', '좌표정보(X)', '좌표정보(Y)',
                     '영업상태명', '상세영업상태명', '업태구분명', '데이터갱신일자', '최종수정일자'])
    for v in list(cfg.get('size_map', {}).values()) + list(cfg.get('attr_map', {}).values()) + cfg.get('extra_keep', []):
        for c in (v if isinstance(v, (list, tuple)) else [v]):
            keep_cols.add(c)
    for src in cfg['sources']:
        meta = stage_raw(src, raw_dir)
        p = raw_dir / src['dest_name']
        df, st = process_file(p, src['slug'], keep_cols)
        ref = (st['max_data_update'] or '')[:10] or None
        if meta.get('reference_date') != ref:
            meta['reference_date'] = ref; meta['reference_date_basis'] = 'max(데이터갱신일자) in file'
            (raw_dir / (src['dest_name'] + '.metadata.json')).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
        df['_src_file'] = 'raw/' + src['dest_name']; df['_ref'] = ref
        df['_dataset'] = src.get('dataset', ''); df['_src_url'] = meta['url'] + ('' if meta['method'] == 'GET' else f" (POST infId={meta['params']['infId']})")
        df['_org'] = src.get('org', '행정안전부 지방행정 인허가데이터(서울 열린데이터광장 재배포)' if src['kind'] == 'seoul_sheet' else '행정안전부 지방행정 인허가데이터(file.localdata.go.kr)')
        if 'subtype' in src:
            df['_subtype_fixed'] = src['subtype']
        parts.append(df); stats[src['dest_name']] = st; metas[src['dest_name']] = meta
    df = pd.concat(parts, ignore_index=True)
    qa = {'facility_type': T, 'grade': 'B', 'built_utc': datetime.now(timezone.utc).isoformat(),
          'rule': 'B: 인허가일 ≤ D, 종료일(폐업일, 없으면 인허가취소일) 없음 또는 > D. 폐업·취소·말소·제외 등 상태인데 날짜 없으면 최종수정일자로 대체. 1900/0001 등 더미·결측 인허가일은 unknown(제외). 휴업은 시작·종료일이 모두 있고 D가 그 사이일 때만 제외. 영업/휴업 상태 행의 폐업/취소일은 무시.',
          'snapshot_dates': {k: str(v.date()) for k, v in SNAPS.items()},
          'sources': {k: {'slug': metas[k]['slug'], 'url': metas[k]['url'], 'params': metas[k].get('params'), 'sha256': metas[k]['sha256'],
                          'bytes': metas[k]['bytes'], 'download_utc': metas[k]['download_utc'], 'reference_date': metas[k]['reference_date'],
                          **{kk: vv for kk, vv in stats[k].items() if kk != 'org_codes'}} for k in stats}}
    df, qa['transfer_fix'] = fix_transfers(df)
    # 필터 (예: 주유소만)
    if cfg.get('filter_fn'):
        m = cfg['filter_fn'](df)
        qa['filter'] = {'desc': cfg.get('filter_desc', ''), 'candidates_before': int(len(df)), 'candidates_after': int(m.sum()),
                        'active_before': {k: int(df['_active_' + k].sum()) for k in SNAPS},
                        'active_after': {k: int((df['_active_' + k] & m).sum()) for k in SNAPS}}
        df = df[m].reset_index(drop=True)
    # subtype
    df['facility_subtype'] = cfg['subtype_fn'](df) if cfg.get('subtype_fn') else df.get('_subtype_fixed', T)
    # 좌표
    x = pd.to_numeric(df.get('좌표정보(X)'), errors='coerce'); y = pd.to_numeric(df.get('좌표정보(Y)'), errors='coerce')
    okc = x.between(100000, 300000) & y.between(300000, 700000)
    df['lon'] = np.nan; df['lat'] = np.nan; df['x_5179'] = np.nan; df['y_5179'] = np.nan
    if okc.any():
        lo, la = tf(5174, 4326).transform(x[okc].values, y[okc].values)
        X5, Y5 = tf(5174, 5179).transform(x[okc].values, y[okc].values)
        df.loc[okc, 'lon'] = lo; df.loc[okc, 'lat'] = la; df.loc[okc, 'x_5179'] = X5; df.loc[okc, 'y_5179'] = Y5
    df['coord_method'] = np.where(okc, 'source', 'unresolved')
    df['address'] = df['도로명주소'].where(df['도로명주소'].fillna('').str.len() > 0, df['지번주소'])
    # 지오코딩(소·중규모 유형만)
    geo = {'enabled': bool(cfg.get('geocode')), 'attempted_addresses': 0}
    need = (~okc) & (df[[c for c in df.columns if c.startswith('_active_')]].any(axis=1))
    if cfg.get('geocode') and cfg.get('geocode_max') and need.sum() > cfg['geocode_max']:
        geo.update(skipped=True, reason=f"좌표 없는 운영 후보 {int(need.sum())}행 > geocode_max {cfg['geocode_max']} → 대용량 규칙상 지오코딩 생략", rows_needing=int(need.sum()))
    elif cfg.get('geocode') and need.any():
        secret = load_keys()
        cache_dir = raw_dir / 'geocoding'
        keys_ = {}
        for i in df.index[need]:
            k = address_key(df.at[i, '도로명주소'] or '') or address_key(df.at[i, '지번주소'] or '')
            if k:
                keys_[i] = k
        geo['rows_needing'] = int(need.sum()); geo['rows_no_parsable_address'] = int(need.sum() - len(keys_))
        uniq = sorted(set(keys_.values())); geo['attempted_addresses'] = len(uniq)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=6) as pool:
            res = dict(zip(uniq, pool.map(lambda k: geocode_one(k, secret, cache_dir), uniq)))
        for i, k in keys_.items():
            r = res.get(k)
            if r:
                lo, la, meth = r
                X5, Y5 = tf(4326, 5179).transform(lo, la)
                df.loc[i, ['lon', 'lat', 'x_5179', 'y_5179']] = [lo, la, X5, Y5]; df.at[i, 'coord_method'] = meth
        geo['accepted_rows'] = int(df.coord_method.str.startswith('geocode').sum())
        geo['accepted_addresses'] = int(sum(1 for v in res.values() if v))
        geo['by_method'] = df.loc[df.coord_method.str.startswith('geocode'), 'coord_method'].value_counts().to_dict()
        geo['secrets_found'] = {k: bool(secret.get(k)) for k in ('KAKAO_REST_API_KEY', 'VWORLD_API_KEY')}
    qa['geocoding'] = geo
    df = spatial_attach(df)
    # 공통 열
    df['facility_id'] = 'LIC-' + df['_slug'] + '-' + df['개방자치단체코드'].fillna('') + '-' + df['관리번호'].fillna('')
    df['category_group'] = cfg['category_group']; df['facility_type'] = T
    df['name'] = df['사업장명']; df['grade'] = 'B'
    df['source_org'] = df['_org']; df['source_dataset'] = df['_dataset']; df['source_url'] = df['_src_url']
    df['source_file'] = df['_src_file']; df['source_row_id'] = df['_src_row'].astype(str) + ':' + df['관리번호'].fillna('')
    df['source_reference_date'] = df['_ref']
    df['lic_date'] = df['_lic'].dt.strftime('%Y-%m-%d'); df['eff_start_date'] = df['_start'].dt.strftime('%Y-%m-%d'); df['end_date'] = df['_end'].dt.strftime('%Y-%m-%d')
    df['src_status'] = df.get('영업상태명'); df['src_status_detail'] = df.get('상세영업상태명')
    for out_c, v in cfg.get('size_map', {}).items():
        if isinstance(v, (list, tuple)):
            vals = [pd.to_numeric(df[c], errors='coerce') for c in v if c in df]
            df[out_c] = sum(vals) if vals else np.nan
        else:
            df[out_c] = pd.to_numeric(df[v], errors='coerce') if v in df else np.nan
    attr_cols = []
    for out_c, v in cfg.get('attr_map', {}).items():
        df[out_c] = df[v] if v in df else None; attr_cols.append(out_c)
    # 행정 일괄 말소·취소 표시: 상태코드 04(취소/말소/만료/정지/중지) 이고 같은 업종·같은 종료일이 BULK_N 건 이상
    code4 = df.get('영업상태명', pd.Series('', index=df.index)).fillna('').str.contains('취소|말소|만료|정지|중지')
    df['flag_admin_end'] = code4
    cnt = df[code4].groupby(['_slug', 'end_date']).size()
    bulk_keys = set(cnt[cnt >= BULK_N].index)
    df['flag_bulk_admin_end'] = code4 & pd.Series([(a, b) in bulk_keys for a, b in zip(df['_slug'], df['end_date'])], index=df.index)
    qa['bulk_admin_end_dates'] = {f'{a}|{b}': int(cnt[(a, b)]) for a, b in sorted(bulk_keys)}
    # 원천 중복(같은 업종·사업장명·주소·인허가일, 관리번호만 다름) → 첫 관리번호만 남김
    nk = df['_slug'] + '|' + df['사업장명'].fillna('').str.replace(r'\s+', '', regex=True) + '|' + \
         df['address'].fillna('').str.replace(r'\s+', '', regex=True) + '|' + df['lic_date'].fillna('')
    df['_dupkey'] = nk
    extra = ['lic_date', 'eff_start_date', 'end_date', 'src_status', 'src_status_detail', 'flag_admin_end', 'flag_bulk_admin_end'] + attr_cols + list(cfg.get('size_map', {}).keys())
    qa['candidates_either_snapshot'] = int(len(df))
    outputs = {}
    for k, D in SNAPS.items():
        s = df[df['_active_' + k]].copy().sort_values(['_dupkey', '관리번호'])
        dmask = s.duplicated('_dupkey', keep='first') if cfg.get('dedup', True) else pd.Series(False, index=s.index)
        removed = s[dmask]
        removed[['facility_id', 'name', 'address', 'lic_date', 'end_date', 'src_status', 'source_row_id']].assign(kept_facility_id=
            removed['_dupkey'].map(s[~dmask].drop_duplicates('_dupkey').set_index('_dupkey')['facility_id'])).to_csv(here / f'dedup_removed_{T}_{k}.csv', index=False, encoding='utf-8-sig')
        s = s[~dmask]
        s['year_snapshot'] = k
        s['reference_month_delta'] = s['source_reference_date'].map(lambda r: month_delta(r or '', k))
        base_reason = f'B:현재이력역산(D={D.date()},원천기준={{}})'
        s['temporal_reason'] = [base_reason.format(r) + (';폐업·취소 날짜없음→최종수정일자 대체' if sub else '')
                                + (';전출 이관기록: 시작일=전출 전 기록의 종료일' if tr else '')
                                for r, sub, tr in zip(s['source_reference_date'], s['_end_substituted'], s['_transfer_adjusted'])]
        s = s[COMMON_COLS + extra].sort_values('facility_id').reset_index(drop=True)
        if cfg.get('post_fn'):
            s = cfg['post_fn'](s, k)
        fn = f'facilities_{T}_{k}'
        s.to_csv(here / f'{fn}.csv', index=False, encoding='utf-8-sig')
        s.to_parquet(here / f'{fn}.parquet', index=False)
        outputs[k] = s
        nm = s.name.fillna('').str.replace(r'\s+', '', regex=True); ad = s.address.fillna('').str.replace(r'\s+', '', regex=True)
        cm = s.coord_method.value_counts().to_dict()
        qa[k] = {'n_final': int(len(s)), 'n_active_before_dedup': int(len(s) + len(removed)), 'dedup_removed_exact': int(len(removed)),
                 'flag_admin_end': int(s.flag_admin_end.sum()), 'flag_bulk_admin_end': int(s.flag_bulk_admin_end.sum()),
                 'n_final_excl_bulk_admin_end': int((~s.flag_bulk_admin_end).sum()), 'transfer_adjusted_start': int(s.temporal_reason.str.contains('전출 이관').sum()), 'by_subtype': s.facility_subtype.value_counts().to_dict(),
                 'by_current_status': s.src_status.value_counts().to_dict(),
                 'closed_nodate_substituted': int(s.temporal_reason.str.contains('대체').sum()),
                 'coord_method': cm, 'coord_rate': round(float((s.coord_method != 'unresolved').mean()), 4) if len(s) else None,
                 'source_coord_rate': round(float((s.coord_method == 'source').mean()), 4) if len(s) else None,
                 'outside_seoul': int((s.inside_seoul == False).sum()),
                 'no_dong_among_inside': int(((s.inside_seoul == True) & s.adm_dong_cd.isna()).sum()),
                 'no_oa_among_inside': int(((s.inside_seoul == True) & s.oa_cd.isna()).sum()),
                 'dup_same_name_address': int((nm + '|' + ad).duplicated(keep=False).sum()),
                 'dup_same_coord_5179': int(s.dropna(subset=['x_5179']).duplicated(['x_5179', 'y_5179'], keep=False).sum()),
                 'facility_id_unique': bool(s.facility_id.is_unique),
                 'reference_month_delta': sorted(set(int(v) for v in s.reference_month_delta.dropna()))}
        for c in cfg.get('size_map', {}):
            qa[k].setdefault('size_nonnull_gt0', {})[c] = int((s[c] > 0).sum())
    ids = [set(outputs[k].facility_id) for k in SNAPS]
    qa['panel'] = {'in_both': len(ids[0] & ids[1]), 'only_2020_01': len(ids[0] - ids[1]), 'only_2025_01': len(ids[1] - ids[0])}
    if cfg.get('official_fn'):
        try:
            qa['official_comparison'] = cfg['official_fn'](outputs)
        except Exception as e:
            qa['official_comparison'] = {'error': f'{type(e).__name__}: {e}'}
    else:
        qa['official_comparison'] = {'status': cfg.get('official_note', '공식 집계 대조원 없음(미대조)')}
    if cfg.get('notes'):
        qa['notes'] = cfg['notes']
    if cfg.get('extra_qa_fn'):
        qa.update(cfg['extra_qa_fn'](outputs, here))
    qa['build_seconds'] = round(time.time() - t0, 1)
    (here / f'qa_{T}.json').write_text(json.dumps(qa, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    return outputs, qa
