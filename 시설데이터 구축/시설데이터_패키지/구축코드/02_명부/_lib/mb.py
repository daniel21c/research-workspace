# -*- coding: utf-8 -*-
"""02_명부 공통 모듈: 다운로드+metadata, 지오코딩(Kakao→VWorld, 캐시), 공간결합, 공통 열.
Windows/리눅스 모두 상대경로로 동작. API 키는 파일에서 읽기만 하고 출력·저장하지 않는다."""
import os, re, json, hashlib, time, datetime as dt, unicodedata
from pathlib import Path
import requests
import pandas as pd

LIB = Path(__file__).resolve().parent
BASE = LIB.parent                      # 02_명부
ROOT = BASE.parent                     # 시설_2020_2025_v1
WORK = ROOT.parent                     # 시설데이터 구축
BND = WORK / 'SGIS_인구경계_2019_2024'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'

SNAP = {
    '2020_01': dict(ref=dt.date(2019, 12, 31), lo=dt.date(2019, 9, 1), hi=dt.date(2020, 5, 31)),
    '2025_01': dict(ref=dt.date(2024, 12, 31), lo=dt.date(2024, 9, 1), hi=dt.date(2025, 5, 31)),
}
COLS = ['facility_id', 'category_group', 'facility_type', 'facility_subtype', 'year_snapshot', 'name', 'address',
        'lon', 'lat', 'x_5179', 'y_5179', 'coord_method', 'grade', 'source_org', 'source_dataset', 'source_url',
        'source_file', 'source_row_id', 'source_reference_date', 'reference_month_delta', 'temporal_reason',
        'inside_seoul', 'adm_dong_cd', 'oa_cd', 'grid100_cd']


def month_delta(ref_date, snap):
    """자료 기준일과 목표 기준일(2019-12 / 2024-12)의 월 차이. 창 안이면 0이 아닐 수 있으나 기록만 한다."""
    if isinstance(ref_date, str):
        ref_date = dt.date.fromisoformat(ref_date[:10])
    r = SNAP[snap]['ref']
    return (ref_date.year - r.year) * 12 + (ref_date.month - r.month)


def in_window(ref_date, snap):
    if isinstance(ref_date, str):
        ref_date = dt.date.fromisoformat(ref_date[:10])
    return SNAP[snap]['lo'] <= ref_date <= SNAP[snap]['hi']


# ---------------------------------------------------------------- 다운로드
def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def fetch(url, dest, method='GET', params=None, data=None, headers=None, session=None, ref_date='', note='',
          force=False, timeout=170):
    """원본을 dest에 저장하고 dest+'.metadata.json'을 남긴다. 이미 있으면 다시 받지 않는다."""
    dest = Path(dest)
    meta_p = Path(str(dest) + '.metadata.json')
    if dest.exists() and meta_p.exists() and not force:
        return json.loads(meta_p.read_text(encoding='utf-8'))
    s = session or requests.Session()
    h = {'User-Agent': UA}
    h.update(headers or {})
    r = s.request(method, url, params=params, data=data, headers=h, timeout=timeout)
    r.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    meta = dict(url=url, method=method, params=params, form=data,
                request_headers={k: v for k, v in h.items() if k.lower() != 'cookie'},
                download_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
                http_status=r.status_code, content_disposition=r.headers.get('Content-Disposition'),
                content_type=r.headers.get('Content-Type'), bytes=len(r.content), sha256=sha256(dest),
                reference_date=ref_date, note=note)
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    return meta


def register_local(src, dest, ref_date='', note='', url='', method='copy'):
    """이미 받은 사본을 raw/로 복사하고 metadata를 남긴다(원 URL 기재)."""
    import shutil
    dest = Path(dest)
    meta_p = Path(str(dest) + '.metadata.json')
    if not dest.exists():
        shutil.copy2(src, dest)
    if not meta_p.exists():
        meta = dict(url=url, method=method, copied_from=str(src),
                    copied_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
                    source_mtime_utc=dt.datetime.fromtimestamp(os.path.getmtime(src), dt.timezone.utc).isoformat(timespec='seconds'),
                    bytes=os.path.getsize(dest), sha256=sha256(dest), reference_date=ref_date, note=note)
        meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    return json.loads(meta_p.read_text(encoding='utf-8'))


# ---------------------------------------------------------------- 문자열 정규화
def nfc(s):
    return unicodedata.normalize('NFC', str(s)) if s is not None else ''


def clean(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ''
    s = nfc(s).replace('\u3000', ' ').replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', s).strip()


GU = ['종로구', '중구', '용산구', '성동구', '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구', '노원구', '은평구',
      '서대문구', '마포구', '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구', '관악구', '서초구', '강남구', '송파구', '강동구']


def seoulize(addr, gu=''):
    """주소 앞에 '서울특별시'가 없으면 붙인다(구 이름은 있으면 사용)."""
    a = clean(addr)
    a = re.sub(r'^(서울시|서울특별시|서울)\s*', '', a)
    if gu and not any(a.startswith(g) for g in GU):
        a = gu + ' ' + a
    return '서울특별시 ' + a


ROAD_RE = re.compile(r'([가-힣A-Za-z0-9·.]+(?:로|길))\s*,?\s*(?:지하\s*)?(\d+)(?:\s*-\s*(\d+))?(?!\d)(?!\s*(?:가(?:\s|$|\d)|번?길(?![가-힣])|로(?![가-힣])))')
JIBUN_RE = re.compile(r'(?<![0-9A-Za-z가-힣])([가-힣][가-힣0-9·.]*(?:동|가|리))\s*(산\s*)?(\d+)(?:\s*-\s*(\d+))?(?!\d)')


def _norm_variants(a):
    a = clean(a)
    a0 = re.sub(r'\([^)]*\)', ' ', a)
    a0 = re.sub(r'\s+', ' ', a0).strip()
    a0 = re.sub(r'(로|길)\s+(\d+[가-힣]?)\s*(번?길)(?=\s|\d|$|,)', r'\1\2\3', a0)
    a0 = re.sub(r'(\d)\s*번지', r'\1', a0)
    # 붙어 쓴 구 이름 떼기(강서구강서로 → 강서구 강서로)
    a0 = re.sub(r'(?<![가-힣])(' + '|'.join(sorted(GU, key=len, reverse=True)) + r')(?=[가-힣0-9])', r'\1 ', a0)
    vs = [a0]
    # 후보 1: 붙어 쓴 동 이름 떼기(잠실동올림픽로 → 잠실동 올림픽로). 틀린 분리는 건물번호 일치 검사에서 걸러진다
    a1 = re.sub(r'([가-힣]+\d*(?:동|가))(?=[가-힣]{2,}\d*[가-힣]?(?:로|길)\s*\d)', r'\1 ', a0)
    # 후보 2: '평창 30길', '홍지문 1길' → 붙여 씀
    a2 = re.sub(r'(?<![가-힣])([가-힣]{2,}(?<![구시동읍면리가]))\s+(\d+[가-힣]?(?:번?길))(?=\s|\d|$|,)', r'\1\2', a0)
    for v in (a1, a2):
        if v not in vs:
            vs.append(v)
    return vs


def parse_addr(a):
    """주소를 '시 구 도로명 번호' 또는 '시 구 동 번지' 검색문과 기대 번호로 바꾼다(여러 후보, 순서대로 시도)."""
    out = []
    seen = set()
    for a0 in _norm_variants(a):
        for c in _parse_one(a0):
            if c['query'] not in seen:
                seen.add(c['query']); out.append(c)
    # 도로명 후보를 지번 후보보다 앞에
    return [c for c in out if c['kind'] == 'road'] + [c for c in out if c['kind'] == 'jibun']


OTHER_SIDO = re.compile(r'(경기도|경기|인천광역시|인천시|인천|강원도|강원특별자치도|충청북도|충청남도|충북|충남|부산광역시|대구광역시|대전광역시|광주광역시|울산광역시|세종특별자치시|전라북도|전북특별자치도|전라남도|경상북도|경상남도|제주특별자치도)\s+([가-힣]+(?:시|군|구))(?:\s+([가-힣]+구)(?=\s))?')


def _parse_one(a0):
    out = []
    mo = OTHER_SIDO.search(a0)
    if mo:  # 서울 밖 소재(서울시 소유 시설 등): 그 시도·시군으로 검색
        pre = ' '.join(x for x in mo.groups() if x)
        rest = a0[mo.end():]
        for c in _parse_one_core(rest, pre):
            out.append(c)
        return out
    gu = next((g for g in GU if re.search(r'(^|\s)' + g + r'(\s|$)', a0)), '')
    return _parse_one_core(a0, ' '.join(x for x in ['서울특별시', gu] if x))


def _parse_one_core(a0, prefix):
    out = []
    m = ROAD_RE.search(a0)
    if m:
        q = prefix
        q = f"{q} {m.group(1)} {m.group(2)}" + (f"-{m.group(3)}" if m.group(3) else '')
        out.append(dict(kind='road', query=q.strip(), road=m.group(1), main=int(m.group(2)),
                        sub=int(m.group(3)) if m.group(3) else 0))
    m2 = JIBUN_RE.search(a0)
    if m2 and not re.search(r'(로|길)$', m2.group(1)):
        dongs = [m2.group(1)]
        mh = re.match(r'^(\D+?)\d+동$', m2.group(1))  # 행정동식 표기(역삼1동) → 법정동(역삼동)도 시도
        if mh:
            dongs.append(mh.group(1) + '동')
        for dg in dongs:
            q = prefix
            q = f"{q} {dg} {'산 ' if m2.group(2) else ''}{m2.group(3)}" + (f"-{m2.group(4)}" if m2.group(4) else '')
            out.append(dict(kind='jibun', query=q.strip(), dong=dg, main=int(m2.group(3)),
                            sub=int(m2.group(4)) if m2.group(4) else 0, san=bool(m2.group(2))))
    return out


# ---------------------------------------------------------------- 지오코딩
_KEYS = None


def keys():
    global _KEYS
    if _KEYS is None:
        # API 키: 환경변수 FACILITY_API_ENV 또는 00_박사논문_연구체계/_secrets/facility_api.env (공유본에 없음)
        cands = [os.environ.get('FACILITY_API_ENV', ''), next(p for p in Path(__file__).resolve().parents if (p / '시설데이터 구축').is_dir()) / '_secrets' / 'facility_api.env']
        _KEYS = {}
        for c in cands:
            if c and Path(c).exists():
                for line in Path(c).read_text(encoding='utf-8').splitlines():
                    if '=' in line and not line.strip().startswith('#'):
                        k, v = line.split('=', 1)
                        _KEYS[k.strip()] = v.strip().strip('"').strip("'")
                break
    return _KEYS


_S = requests.Session()


def _cached(cache_dir, tag, query, fn):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha1(f'{tag}|{query}'.encode('utf-8')).hexdigest()[:20]
    p = cache_dir / f'{tag}_{h}.json'
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except ValueError:  # 중단된 쓰기로 깨진 캐시 → 다시 조회해 덮어씀
            pass
    for i in range(4):
        try:
            res = fn(query)
            break
        except Exception as e:  # 일시 오류 재시도
            res = {'_error': str(e)[:200]}
            time.sleep(1.5 * (i + 1))
    if '_error' in res:
        return res  # 오류는 캐시하지 않음
    rec = dict(provider=tag, query=query, fetched_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), response=res)
    import uuid
    tmp = p.with_name(p.stem + '.' + uuid.uuid4().hex[:8] + '.tmp')
    tmp.write_text(json.dumps(rec, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, p)
    return rec


def _kakao(q):
    r = _S.get('https://dapi.kakao.com/v2/local/search/address.json', params={'query': q, 'size': 10},
               headers={'Authorization': 'KakaoAK ' + keys()['KAKAO_REST_API_KEY']}, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f'kakao http {r.status_code}')
    return r.json()


def _vworld(q, typ):
    r = _S.get('https://api.vworld.kr/req/address', params=dict(service='address', request='getcoord', version='2.0',
               crs='epsg:4326', address=q, refine='true', simple='false', format='json', type=typ,
               key=keys()['VWORLD_API_KEY']), timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f'vworld http {r.status_code}')
    j = r.json()
    return j


def _num(s):
    try:
        return int(str(s).strip() or 0)
    except ValueError:
        return -1


def _norm_road(s):
    return re.sub(r'\s+', '', s or '')


def geocode(addr, cache_dir):
    """반환: (lon, lat, method, detail). 도로명+건물번호 또는 지번 번지 일치만 채택."""
    cands = parse_addr(addr)
    if not cands:
        return None, None, 'unresolved', 'parse_fail'
    # 1) Kakao
    for c in cands:
        rec = _cached(cache_dir, 'kakao', c['query'], _kakao)
        docs = (rec.get('response') or {}).get('documents', []) if 'response' in rec else []
        for d in docs:
            ra, ja = d.get('road_address'), d.get('address')
            if c['kind'] == 'road' and ra and d.get('address_type') in ('ROAD_ADDR', 'REGION_ADDR'):
                if _norm_road(ra.get('road_name')) == _norm_road(c['road']) and _num(ra.get('main_building_no')) == c['main'] \
                        and _num(ra.get('sub_building_no')) == c['sub']:
                    return float(ra['x']), float(ra['y']), 'geocode_kakao_exact', f"road:{ra.get('address_name')}"
            if c['kind'] == 'jibun' and ja and d.get('address_type') in ('REGION_ADDR', 'ROAD_ADDR'):
                if _num(ja.get('main_address_no')) == c['main'] and _num(ja.get('sub_address_no')) == c['sub'] \
                        and (ja.get('mountain_yn') == 'Y') == c['san'] and c['dong'] in (ja.get('address_name') or ''):
                    return float(ja['x']), float(ja['y']), 'geocode_kakao_exact', f"jibun:{ja.get('address_name')}"
    # 2) VWorld
    for c in cands:
        typ = 'road' if c['kind'] == 'road' else 'parcel'
        rec = _cached(cache_dir, 'vworld_' + typ, c['query'], lambda q: _vworld(q, typ))
        resp = (rec.get('response') or {}).get('response', {}) if 'response' in rec else {}
        if resp.get('status') != 'OK':
            continue
        st = (resp.get('refined') or {}).get('structure') or {}
        pt = (resp.get('result') or {}).get('point') or {}
        if c['kind'] == 'road':
            num = str(st.get('level5', ''))
            m = re.match(r'^(\d+)(?:-(\d+))?$', num)
            if m and _norm_road(st.get('level4L')) == _norm_road(c['road']) and int(m.group(1)) == c['main'] \
                    and int(m.group(2) or 0) == c['sub']:
                return float(pt['x']), float(pt['y']), 'geocode_vworld_exact', f"road:{resp['refined'].get('text')}"
        else:
            num = str(st.get('level5', ''))
            m = re.match(r'^(산)?\s*(\d+)(?:-(\d+))?$', num)
            if m and int(m.group(2)) == c['main'] and int(m.group(3) or 0) == c['sub'] and bool(m.group(1)) == c['san']:
                return float(pt['x']), float(pt['y']), 'geocode_vworld_exact', f"jibun:{resp['refined'].get('text')}"
    return None, None, 'unresolved', 'no_exact_match:' + ' || '.join(c['query'] for c in cands)


def geocode_df(df, cache_dir, addr_col='address', workers=8, budget=None):
    """budget(초, 환경변수 GEOCODE_BUDGET)가 지나면 새 조회를 멈추고 'not_attempted'로 둔다(다시 실행하면 캐시로 이어감)."""
    from concurrent.futures import ThreadPoolExecutor
    budget = budget or float(os.environ.get('GEOCODE_BUDGET', '0') or 0)
    t0 = time.time()
    uniq = list(dict.fromkeys(df[addr_col].fillna('').tolist()))

    def one(a):
        if not a:
            return (None, None, 'unresolved', 'no_address')
        if budget and time.time() - t0 > budget:
            return (None, None, 'unresolved', 'not_attempted')
        return geocode(a, cache_dir)
    with ThreadPoolExecutor(workers) as ex:
        res = dict(zip(uniq, ex.map(one, uniq)))
    df = df.copy()
    df['lon'] = [res[a][0] for a in df[addr_col].fillna('')]
    df['lat'] = [res[a][1] for a in df[addr_col].fillna('')]
    df['coord_method'] = [res[a][2] for a in df[addr_col].fillna('')]
    df['geocode_detail'] = [res[a][3] for a in df[addr_col].fillna('')]
    return df


# ---------------------------------------------------------------- 공간 결합
_B = {}


def boundaries():
    if not _B:
        import geopandas as gpd
        d = gpd.read_file(BND / '03_행정구역/경계_2025_2Q/bnd_dong_00_2025_2Q/bnd_dong_00_2025_2Q.shp')
        _B['dong'] = d[d.ADM_CD.astype(str).str.startswith('11')][['ADM_CD', 'ADM_NM', 'geometry']]
        o = gpd.read_file(BND / '02_집계구/경계_2025_2Q/bnd_oa_00_2025_2Q.shp')
        _B['oa'] = o[o.ADM_CD.astype(str).str.startswith('11')][['TOT_OA_CD', 'geometry']]
    return _B


def grid100(x, y):
    X = '가나다라마바사아자차카타파하'
    try:
        return X[int((x - 700000) // 100000)] + X[int((y - 1300000) // 100000)] + \
            f'{int((x % 100000) // 100):03d}{int((y % 100000) // 100):03d}'
    except Exception:
        return ''


def spatial(df):
    import geopandas as gpd
    from pyproj import Transformer
    df = df.copy().reset_index(drop=True)
    tr = Transformer.from_crs(4326, 5179, always_xy=True)
    ok = df.lon.notna() & df.lat.notna()
    xs, ys = tr.transform(df.loc[ok, 'lon'].values, df.loc[ok, 'lat'].values)
    df['x_5179'] = pd.NA
    df['y_5179'] = pd.NA
    df.loc[ok, 'x_5179'] = xs.round(2)
    df.loc[ok, 'y_5179'] = ys.round(2)
    df['adm_dong_cd'] = ''
    df['oa_cd'] = ''
    df['grid100_cd'] = ''
    df['inside_seoul'] = pd.NA
    if ok.any():
        g = gpd.GeoDataFrame(df.loc[ok, []], geometry=gpd.points_from_xy(xs, ys), crs=5179)
        b = boundaries()
        j = gpd.sjoin(g, b['dong'], how='left', predicate='within')
        j = j[~j.index.duplicated()]
        df.loc[ok, 'adm_dong_cd'] = j['ADM_CD'].fillna('').astype(str).values
        j2 = gpd.sjoin(g, b['oa'], how='left', predicate='within')
        j2 = j2[~j2.index.duplicated()]
        df.loc[ok, 'oa_cd'] = j2['TOT_OA_CD'].fillna('').astype(str).values
        df.loc[ok, 'inside_seoul'] = (df.loc[ok, 'adm_dong_cd'] != '').values
        df.loc[ok, 'grid100_cd'] = [grid100(x, y) for x, y in zip(xs, ys)]
    return df


# ---------------------------------------------------------------- facility_id
def norm_name(s):
    s = clean(s)
    s = re.sub(r'\([^)]*\)', '', s)
    s = re.sub(r'(사회복지법인|재단법인|사단법인|\(재\)|\(사\)|\(주\)|주식회사)', '', s)
    s = re.sub(r'[^0-9A-Za-z가-힣]', '', s)
    s = s.replace('서울특별시', '').replace('서울시', '')
    return s.lower()


def addr_key(a):
    """주소 정규화 키: 첫 번째 도로명+번호(없으면 동+번지)."""
    c = parse_addr(a)
    if not c:
        return re.sub(r'\s+', '', clean(a))
    c = c[0]
    if c['kind'] == 'road':
        return f"R:{_norm_road(c['road'])}{c['main']}-{c['sub']}"
    return f"J:{c['dong']}{'산' if c['san'] else ''}{c['main']}-{c['sub']}"


def assign_ids(d20, d25, prefix, extra_key=None):
    """두 시점 매칭 규칙(순서대로):
    0) 정규화 명칭 + 주소키 + subtype 동일  1) 정규화 명칭 + 주소키 동일  2) 정규화 명칭 동일(각 시점 유일)  3) 주소키 동일 + 같은 subtype(각 시점 유일)
    4) 좌표 50m 이내 + 명칭 앞 4자 동일.  매칭 안 되면 새 id. id = prefix + 순번(2020 행 순서, 이어서 2025)."""
    d20 = d20.copy().reset_index(drop=True)
    d25 = d25.copy().reset_index(drop=True)
    for d in (d20, d25):
        d['_n'] = d['name'].map(norm_name)
        d['_a'] = d['address'].map(addr_key)
        d['_s'] = d['facility_subtype'].fillna('') if extra_key is None else d[extra_key].fillna('')
    match = {}  # idx25 -> idx20
    rule = {}
    used20 = set()

    def try_rule(keyf, name):
        k20 = {}
        for i, r in d20.iterrows():
            if i in used20:
                continue
            k20.setdefault(keyf(r), []).append(i)
        k25 = {}
        for i, r in d25.iterrows():
            if i in match:
                continue
            k25.setdefault(keyf(r), []).append(i)
        for k, l25 in k25.items():
            if not k or k not in k20:
                continue
            l20 = [x for x in k20[k] if x not in used20]
            if len(l25) == 1 and len(l20) == 1:
                match[l25[0]] = l20[0]; used20.add(l20[0]); rule[l25[0]] = name
            elif name in ('name+addr+subtype', 'name+addr'):  # 여러 개면 순서대로 짝
                for a, b in zip(l25, l20):
                    match[a] = b; used20.add(b); rule[a] = name
    try_rule(lambda r: (r['_n'], r['_a'], r['_s']) if r['_n'] else None, 'name+addr+subtype')
    try_rule(lambda r: (r['_n'], r['_a']) if r['_n'] else None, 'name+addr')
    try_rule(lambda r: r['_n'] or None, 'name')
    try_rule(lambda r: (r['_a'], r['_s']) if r['_a'] else None, 'addr+subtype')
    # 좌표 근접
    if 'x_5179' in d20 and d20['x_5179'].notna().any():
        import numpy as np
        for i, r in d25.iterrows():
            if i in match or pd.isna(r.get('x_5179')):
                continue
            best = None
            for j, q in d20.iterrows():
                if j in used20 or pd.isna(q.get('x_5179')):
                    continue
                dd = ((float(r.x_5179) - float(q.x_5179)) ** 2 + (float(r.y_5179) - float(q.y_5179)) ** 2) ** .5
                if dd <= 50 and r['_n'][:4] == q['_n'][:4] and (best is None or dd < best[0]):
                    best = (dd, j)
            if best:
                match[i] = best[1]; used20.add(best[1]); rule[i] = 'coord50m+name4'
    d20['facility_id'] = [f'{prefix}{i + 1:05d}' for i in range(len(d20))]
    n = len(d20)
    ids25 = []
    for i in range(len(d25)):
        if i in match:
            ids25.append(d20.loc[match[i], 'facility_id'])
        else:
            n += 1
            ids25.append(f'{prefix}{n:05d}')
    d25['facility_id'] = ids25
    d25['id_match_rule'] = [rule.get(i, 'new') for i in range(len(d25))]
    d20['id_match_rule'] = ['in_2025' if i in used20 else 'not_in_2025' for i in range(len(d20))]
    stats = dict(matched=len(match), by_rule=pd.Series(list(rule.values())).value_counts().to_dict() if rule else {},
                 only_2020=len(d20) - len(used20), only_2025=len(d25) - len(match))
    return d20.drop(columns=['_n', '_a', '_s']), d25.drop(columns=['_n', '_a', '_s']), stats


# ---------------------------------------------------------------- 저장·QA
def finalize(df, snap, outdir, typ):
    outdir = Path(outdir)
    df = df.copy()
    df['year_snapshot'] = snap
    for c in COLS:
        if c not in df:
            df[c] = pd.NA
    sz = [c for c in df.columns if c.startswith('sz_')]
    extra = [c for c in df.columns if c not in COLS and c not in sz]
    df = df[COLS + sz + extra]
    p = outdir / f'facilities_{typ}_{snap}'
    df.to_csv(str(p) + '.csv', index=False, encoding='utf-8-sig')
    d2 = df.copy()
    for c in d2.columns:
        if d2[c].dtype == object:
            d2[c] = d2[c].map(lambda v: None if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NA else str(v))
    for c in ['lon', 'lat', 'x_5179', 'y_5179']:
        d2[c] = pd.to_numeric(d2[c], errors='coerce')
    d2.to_parquet(str(p) + '.parquet', index=False)
    return df


def geo_qa(df):
    n = len(df)
    vc = df['coord_method'].value_counts().to_dict()
    has = int(df['lon'].notna().sum())
    return dict(rows=n, coord_rows=has, coord_rate=round(has / n, 4) if n else None, coord_method=vc,
                outside_seoul=int((df['inside_seoul'] == False).sum()),
                note='명부에 좌표가 없어 과거 명부 주소를 현재(2026-09) 지오코더(Kakao 우선, VWorld 보조)로 좌표화함. 건물번호/번지 일치만 채택.')


def dup_qa(df, cols=('name', 'address')):
    k = df[list(cols)].astype(str).apply(lambda r: '|'.join(r), axis=1)
    kn = df['name'].map(norm_name) + '|' + df['address'].map(addr_key)
    xy = df.dropna(subset=['x_5179']).groupby(['x_5179', 'y_5179']).size()
    ks = kn + '|' + df['facility_subtype'].astype(str)
    return dict(exact_dup_name_addr=int(k.duplicated().sum()), norm_dup_name_addr=int(kn.duplicated().sum()),
                norm_dup_name_addr_same_subtype=int(ks.duplicated().sum()),
                note='같은 기관이 여러 subtype(예: 방문요양+방문목욕)으로 올라 있으면 명칭+주소 중복으로 셈. 같은 subtype 안 중복은 별도 열',
                same_coord_groups=int((xy > 1).sum()), same_coord_rows=int(xy[xy > 1].sum()),
                duplicate_facility_id=int(df['facility_id'].duplicated().sum()))


def write_json(p, obj):
    def conv(o):
        if hasattr(o, 'item'):
            return o.item()
        if isinstance(o, (dt.date, dt.datetime)):
            return o.isoformat()
        return str(o)
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=conv), encoding='utf-8')
