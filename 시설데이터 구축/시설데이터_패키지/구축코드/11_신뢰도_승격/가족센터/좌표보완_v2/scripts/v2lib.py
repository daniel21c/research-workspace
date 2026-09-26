# -*- coding: utf-8 -*-
"""좌표보완_v2 조회 도우미 (키는 파일에서 읽기만, 출력·저장 금지. 응답만 캐시). 요청 간 0.15초 이상."""
import sys, json, time, hashlib, math, re
from pathlib import Path
sys.dont_write_bytecode = True
import requests, os
HERE = Path(__file__).resolve().parent
CACHE = HERE.parent / 'cache'
_K = {}
def keys():
    if not _K:
        # API 키: 환경변수 FACILITY_API_ENV 또는 00_박사논문_연구체계/_secrets/facility_api.env (공유본에 없음, 키 값은 읽기만)
        cands = [Path(os.environ.get('FACILITY_API_ENV', '') or '_none_'), next(q for q in Path(__file__).resolve().parents if (q / '시설데이터 구축').is_dir()) / '_secrets' / 'facility_api.env']
        envp = next(c for c in cands if c.exists())
        for line in envp.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.split('=', 1); _K[k.strip()] = v.strip().strip('"').strip("'")
    return _K
S = requests.Session(); _last = [0.0]
def _thr():
    d = time.time() - _last[0]
    if d < 0.15: time.sleep(0.15 - d)
    _last[0] = time.time()
def cached(tag, q, fn):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{tag}_{hashlib.sha1((tag + '|' + q).encode()).hexdigest()[:20]}.json"
    if p.exists(): return json.loads(p.read_text(encoding='utf-8'))['response']
    _thr(); r = fn(q)
    p.write_text(json.dumps({'tag': tag, 'query': q, 'at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'response': r}, ensure_ascii=False), encoding='utf-8')
    return r
def kakao_addr(q):
    return cached('kakao_addr', q, lambda q: S.get('https://dapi.kakao.com/v2/local/search/address.json', params={'query': q, 'size': 10},
        headers={'Authorization': 'KakaoAK ' + keys()['KAKAO_REST_API_KEY']}, timeout=20).json())
def kakao_kw(q):
    return cached('kakao_kw', q, lambda q: S.get('https://dapi.kakao.com/v2/local/search/keyword.json', params={'query': q, 'size': 15},
        headers={'Authorization': 'KakaoAK ' + keys()['KAKAO_REST_API_KEY']}, timeout=20).json())
def vw_coord(q, typ='road'):
    return cached('vw_' + typ, q, lambda q: S.get('https://api.vworld.kr/req/address', params=dict(service='address', request='getcoord', version='2.0',
        crs='epsg:4326', address=q, refine='true', simple='false', format='json', type=typ, key=keys()['VWORLD_API_KEY']), timeout=20).json())
def vw_search(q, typ='place', cat=None):
    def f(q):
        p = dict(service='search', request='search', version='2.0', crs='EPSG:4326', size=20, page=1, query=q, type=typ, format='json', errorformat='json', key=keys()['VWORLD_API_KEY'])
        if cat: p['category'] = cat
        return S.get('https://api.vworld.kr/req/search', params=p, timeout=20).json()
    return cached(f'vws_{typ}_{cat}', q, f)
def juso(q, hist='Y'):
    return cached('juso_h' + hist, q, lambda q: S.get('https://business.juso.go.kr/addrlink/addrLinkApi.do', params=dict(confmKey=keys()['JUSO_SEARCH_CONFM_KEY'],
        currentPage=1, countPerPage=20, keyword=q, resultType='json', hstryYn=hist, firstSort='road'), timeout=20).json())
def juso_coord(admCd, rnMgtSn, udrtYn, buldMnnm, buldSlno):
    q = f'{admCd}|{rnMgtSn}|{udrtYn}|{buldMnnm}|{buldSlno}'
    return cached('juso_coord', q, lambda q: S.get('https://business.juso.go.kr/addrlink/addrCoordApi.do', params=dict(confmKey=keys()['JUSO_COORD_CONFM_KEY'],
        admCd=admCd, rnMgtSn=rnMgtSn, udrtYn=udrtYn, buldMnnm=buldMnnm, buldSlno=buldSlno, resultType='json'), timeout=20).json())
def hav(lon1, lat1, lon2, lat2):
    R = 6371000; p1, p2 = math.radians(lat1), math.radians(lat2); dp = p2 - p1; dl = math.radians(lon2 - lon1)
    return 2 * R * math.asin(math.sqrt(math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))
def show(kind, q):
    if kind == 'juso':
        j = juso(q); c = j.get('results', {}).get('common', {}); print('juso', c.get('errorCode'), c.get('errorMessage'), c.get('totalCount'))
        for x in j.get('results', {}).get('juso') or []:
            print(' ', x['roadAddrPart1'], '|', x['jibunAddr'], '|', x.get('bdNm'), '| hst:', x.get('hstryYn'), '| rel:', x.get('relJibun'), '|', x['admCd'], x['rnMgtSn'], x['udrtYn'], x['buldMnnm'], x['buldSlno'])
    elif kind == 'jusoN':
        j = juso(q, 'N'); c = j.get('results', {}).get('common', {}); print('jusoN', c.get('errorCode'), c.get('totalCount'))
        for x in j.get('results', {}).get('juso') or []:
            print(' ', x['roadAddrPart1'], '|', x['jibunAddr'], '|', x.get('bdNm'))
    elif kind == 'ka':
        for d in kakao_addr(q).get('documents', []):
            print(' ', d['address_type'], d['address_name'], '|', (d.get('road_address') or {}).get('address_name'), d['x'], d['y'])
    elif kind == 'kw':
        for d in kakao_kw(q).get('documents', []):
            print(' ', d['place_name'], '|', d['road_address_name'], '|', d['address_name'], '|', d['category_name'], d['x'], d['y'], d.get('place_url'))
    elif kind in ('vwr', 'vwp'):
        r = vw_coord(q, 'road' if kind == 'vwr' else 'parcel')['response']; print(' ', r.get('status'), (r.get('refined') or {}).get('text'), (r.get('result') or {}).get('point'))
    elif kind == 'vws':
        r = vw_search(q)['response']; print(' ', r.get('status'), (r.get('record') or {}).get('total'))
        for it in ((r.get('result') or {}).get('items') or []):
            print('   ', it.get('title'), '|', (it.get('address') or {}).get('road'), '|', (it.get('address') or {}).get('parcel'), '|', it.get('category'), it.get('point'))
if __name__ == '__main__':
    for arg in sys.argv[1:]:
        k, q = arg.split(':', 1); print(f'## {k} {q}'); show(k, q)
