# -*- coding: utf-8 -*-
"""공공체육시설 좌표보완 v2 공통 모듈 (2026-09-24, 사전 등록 방법).
검색 방법(정확도 시험과 보완에 똑같이 사용; 주소·기존 좌표는 쓰지 않음, 이름+구+종목만):
  Kakao Local 키워드 검색 '<구> <시설명>' → 변형(번호·괄호 제거, 종목어 추가, 소속 공원/시설명 + 종목어) 순서대로.
  후보 조건: (1) Kakao 주소가 같은 구('서울 <구>') (2) 장소명에 시설명 핵심 토큰 또는 소속 공원/시설명 포함
             (3) 장소명+카테고리에 종목 관련어(coord_fill.KW) 포함 (4) 주차장·화장실·정류장·출입구·매표소 등 부속 POI 제외.
  결정: 1위 후보에서 100 m 안의 다른 후보는 같은 장소로 봄. 남은 후보 1건이면 이름 유사도 ≥0.5,
        2건 이상이면 1위 ≥0.6 이고 2위와 차이 ≥0.15 일 때만 채택(coord_fill.stage3 임계값 그대로) → coord_precision='facility'.
  시설 POI를 못 찾으면 소속 공원/시설 POI(이름 유사도 ≥0.8, 같은 구) → 공원·유수지·배수지 = 'park_level',
        수련관·센터 등 건물 = 'host_building'. 한강공원 지구·하천변(~천, 둔치)처럼 길게 뻗은 공원은 공원 POI를 채택하지 않음.
API 키는 mb.keys()로 읽기만 하고 출력·저장하지 않는다. 호출 간 0.12초 이상(≤10건/초), 응답은 cache/ 에 저장."""
import sys, os, re, time, json, hashlib, difflib, datetime as dt, uuid
sys.dont_write_bytecode = True
from pathlib import Path
import numpy as np, pandas as pd

V2 = Path(__file__).resolve().parents[1]; PUB = V2.parent; V1 = PUB.parents[1]
CACHE = V2 / 'cache'
sys.path.insert(0, str(V1 / '02_명부/_lib')); sys.path.insert(0, str(V1 / '02_명부/공공체육시설'))
import mb
from coord_fill import KW, TYPE_OK, nname
GU = mb.GU
_last = [0.0]


def _throttle():
    w = 0.12 - (time.time() - _last[0])
    if w > 0: time.sleep(w)
    _last[0] = time.time()


def cached(tag, query, fn):
    CACHE.mkdir(exist_ok=True)
    p = CACHE / f"{tag}_{hashlib.sha1(f'{tag}|{query}'.encode()).hexdigest()[:20]}.json"
    if p.exists():
        try: return json.loads(p.read_text(encoding='utf-8'))['response']
        except Exception: pass
    for i in range(3):
        try:
            _throttle(); res = fn(query); break
        except Exception as e:
            res = None; err = str(e)[:100]; time.sleep(1.5 * (i + 1))
    if res is None: return {'_error': err}
    tmp = p.with_name(p.stem + uuid.uuid4().hex[:6] + '.tmp')
    tmp.write_text(json.dumps(dict(tag=tag, query=query, fetched_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), response=res), ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, p); return res


def kakao_kw(q):
    def f(q):
        r = mb._S.get('https://dapi.kakao.com/v2/local/search/keyword.json', params={'query': q, 'size': 15},
                      headers={'Authorization': 'KakaoAK ' + mb.keys()['KAKAO_REST_API_KEY']}, timeout=20)
        if r.status_code != 200: raise RuntimeError(f'kakao {r.status_code}')
        return r.json()
    return (cached('kakao_kw', q, f) or {}).get('documents', [])


def vworld_place(q):
    def f(q):
        r = mb._S.get('https://api.vworld.kr/req/search', params=dict(service='search', request='search', version='2.0', crs='EPSG:4326',
                      size=30, page=1, query=q, type='place', format='json', errorformat='json', key=mb.keys()['VWORLD_API_KEY']), timeout=20)
        if r.status_code != 200: raise RuntimeError(f'vworld {r.status_code}')
        return r.json()
    j = cached('vworld_place', q, f) or {}
    return (((j.get('response') or {}).get('result') or {}).get('items') or [])


def vworld_addr(q, typ):
    j = cached('vworld_' + typ, q, lambda q: mb._vworld(q, typ)) or {}
    resp = j.get('response') or {}
    if resp.get('status') != 'OK': return None
    pt = (resp.get('result') or {}).get('point') or {}
    return float(pt['x']), float(pt['y'])


def geocode_exact(addr):
    """원 빌드 규칙(건물번호/번지 정확 일치) 그대로, 캐시만 v2/cache."""
    return mb.geocode(addr, CACHE)


_TF = {}
def to5179(lon, lat):
    from pyproj import Transformer
    if 't' not in _TF: _TF['t'] = Transformer.from_crs(4326, 5179, always_xy=True)
    return _TF['t'].transform(lon, lat)


def dist(lo1, la1, lo2, la2):
    x1, y1 = to5179(lo1, la1); x2, y2 = to5179(lo2, la2)
    return float(np.hypot(x1 - x2, y1 - y2))


# ---------------------------------------------------------------- 이름 처리
TYPEWORD = {'축구장': '축구장', '야구장': '야구장', '테니스장': '테니스장', '수영장': '수영장', '생활체육관': '체육관', '구기체육관': '체육관',
            '투기체육관': '체육관', '게이트볼장': '게이트볼장', '골프연습장': '골프연습장', '빙상장': '빙상장', '롤러스케이트장': '인라인스케이트장',
            '국궁장': '국궁장', '육상경기장': '운동장', '하키장': '하키장', '싸이클경기장': '경륜장', '파크골프장': '파크골프장',
            '기타체육시설(풋살장)': '풋살장', '기타체육시설(그외)': '', '기타체육시설': ''}
GENERIC = {'축구장', '야구장', '테니스장', '수영장', '체육관', '게이트볼장', '골프연습장', '빙상장', '롤러스케이트장', '인라인스케이트장', '국궁장',
           '운동장', '경기장', '하키장', '경륜장', '파크골프장', '풋살장', '족구장', '배드민턴장', '농구장', '구장', '인조잔디구장', '다목적체육관',
           '대체육관', '소체육관', '실내', '실외', '야외', '간이', '다목적', '생활체육관', '구기체육관', '체육시설', '스포츠센터', '체육센터', '국민체육센터',
           '구민체육센터', '문화체육센터', '실내체육관', '한강공원', '한강시민공원', '지구', '공원', '임시', '일반', '리틀', '성인', '어린이', '하드코트',
           '인조잔디', '천연잔디', '잔디구장', '보조경기장', '주경기장', '연습장', '제1', '제2', '제3', '구립', '시립', '서울', '서울시', '서울특별시'}
TYPE_SUFFIX = r'(인조잔디구장|다목적체육관|대체육관|소체육관|실내체육관|체육관|축구장|야구장|테니스장|수영장|게이트볼장|골프연습장|빙상장|롤러스케이트장|인라인스케이트장|국궁장|운동장|경기장|하키장|경륜장|파크골프장|풋살장|족구장|배드민턴장|농구장|구장)$'
HOST_RE = re.compile(r'([가-힣A-Za-z0-9·]{2,}?(?:체육공원|근린공원|어린이공원|생태공원|공원|유수지|배수지|선수촌|스포츠타운|레포츠타운|레포츠센터|청소년수련관|수련관|문화센터|체육센터|스포츠센터|복지관|문화관|회관|센터|학교|대학교|천|둔치))')
LINEAR = re.compile(r'(한강|천$|천변|둔치|지구$)')
ZONES = ['이촌', '뚝섬', '망원', '강서', '광나루', '난지', '잠실', '잠원', '여의도', '반포', '양화']
BAD_POI = re.compile(r'(주차장|화장실|정류장|출입구|입구|매표소|관리사무소|안내소|매점|카페|편의점)$')


def strip_gu(s, gu):
    s = re.sub(r'^(서울특별시|서울시|서울)\s*', '', s)
    return re.sub('^' + re.escape(gu) + r'\s*', '', s) if gu else s


def clean_variants(nm, gu, st):
    """검색어 변형(순서 고정)."""
    n0 = strip_gu(mb.clean(nm), gu)
    n1 = re.sub(r'\([^)]*\)', ' ', n0)                                  # 괄호 제거
    n2 = re.sub(r'(?<=[가-힣])\s*\d+(\s*[,~]\s*\d+)*\s*$', '', re.sub(r'\s+', ' ', n1)).strip()   # 끝 번호 제거
    n2 = re.sub(r'(?<=[가-힣])\d+(?=\s|$)', '', n2).strip()
    tw = TYPEWORD.get(st, '')
    n3 = n2 if (not tw or any(k in n2 for k in KW.get(st, [])[:2])) else f'{n2} {tw}'
    paren = re.findall(r'\(([^)]*)\)', n0)
    out = [n0, n1.strip(), n2, n3]
    for p in paren:
        if len(p) >= 2 and not re.fullmatch(r'(임시|일반|리틀|성인|어린이|실내|실외|\d.*)', p): out.append(f'{p} {tw}'.strip())
    return [re.sub(r'\s+', ' ', x).strip() for x in dict.fromkeys(out) if x and x.strip()]


def host_of(nm, gu):
    """소속 공원/시설명(검색어)과 좌표 정밀도 종류."""
    n = strip_gu(mb.clean(nm), gu)
    z = next((z for z in ZONES if z in n), None)
    if z and ('한강' in n or '지구' in n): return f'{z}한강공원', 'linear'
    n1 = re.sub(r'\([^)]*\)', ' ', n)
    for tok in re.split(r'\s+', n1):
        m = HOST_RE.match(tok)
        if m and len(m.group(1)) >= 3 and m.group(1) not in GENERIC:
            h = m.group(1)
            if LINEAR.search(h): return h, 'linear'
            if re.search(r'(공원|유수지|배수지|선수촌|스포츠타운|레포츠타운)$', h): return h, 'park_level'
            return h, 'host_building'
    m = HOST_RE.search(n1.replace(' ', ''))
    if m and len(m.group(1)) >= 3:
        h = m.group(1)
        if LINEAR.search(h): return h, 'linear'
        if re.search(r'(공원|유수지|배수지|선수촌|스포츠타운|레포츠타운)$', h): return h, 'park_level'
        return h, 'host_building'
    return None, None


def core_tokens(nm, gu):
    n = re.sub(r'\([^)]*\)', ' ', strip_gu(mb.clean(nm), gu))
    toks = []
    for t in re.split(r'[\s,·]+', n):
        t = re.sub(r'\d+$', '', t)
        t2 = re.sub(TYPE_SUFFIX, '', t)
        for x in (t2, t):
            x = re.sub(r'^(제\d)', '', x)
            if len(x) >= 2 and x not in GENERIC and not x.isdigit(): toks.append(x); break
    return list(dict.fromkeys(toks))


def sim(a, b): return difflib.SequenceMatcher(None, a, b).ratio()


def _in_gu(x, gu):
    a = (x.get('road_address_name') or '') + ' ' + (x.get('address_name') or '')
    return f'서울 {gu}' in a


def _decide(cands, key):
    """cands: [(score, doc)] → (doc|None, reason)."""
    if not cands: return None, 'no_candidate'
    cands = sorted(cands, key=lambda t: -t[0]); top = cands[0]
    rest = [c for c in cands[1:] if dist(float(top[1]['x']), float(top[1]['y']), float(c[1]['x']), float(c[1]['y'])) > 100]
    if not rest:
        return (top[1], 'single') if top[0] >= 0.5 else (None, 'single_low_similarity')
    if top[0] >= 0.6 and top[0] - rest[0][0] >= 0.15: return top[1], 'clear_top'
    return None, 'ambiguous'


def search(nm, gu, st):
    """반환 dict(result, lon, lat, precision, query, place_name, place_addr, category, score, n_cand, reason, trace)."""
    kws = KW.get(st, ['체육']); host, hkind = host_of(nm, gu); toks = core_tokens(nm, gu)
    if host: toks = list(dict.fromkeys(toks + [host]))
    z = next((z for z in ZONES if z in nm), None)
    if hkind == 'linear' and z and host.endswith('한강공원'): toks = [t for t in toks if t != z + '지구'] + [z + '한강']
    key = nname(nm, gu); trace = []
    qs = [f'{gu} {v}' for v in clean_variants(nm, gu, st)]
    tw = TYPEWORD.get(st, '')
    if host: qs.append(f'{gu} {host} {tw}'.strip())
    for q in dict.fromkeys(qs):
        docs = kakao_kw(q); cands = []
        for x in docs:
            pn = x.get('place_name') or ''; pnn = pn.replace(' ', '')
            if not _in_gu(x, gu) or BAD_POI.search(pn) or '교통,수송' in (x.get('category_name') or ''): continue
            if not any(t.replace(' ', '') in pnn for t in toks): continue
            if not any(k in pn + ' ' + (x.get('category_name') or '') for k in kws): continue
            cands.append((sim(key, nname(pn, gu)), x))
        doc, why = _decide(cands, key); trace.append(f'{q}:{len(docs)}/{len(cands)}:{why}')
        if doc is not None:
            return dict(result='accepted', lon=float(doc['x']), lat=float(doc['y']), precision='facility', query=q, place_name=doc['place_name'],
                        place_addr=doc.get('road_address_name') or doc.get('address_name'), category=doc.get('category_name'),
                        score=round(max(s for s, d in cands if d is doc), 3), n_cand=len(cands), reason=why, trace=' || '.join(trace))
    if host and hkind != 'linear':
        q = f'{gu} {host}'; docs = kakao_kw(q); hk = nname(host, gu); cands = []
        for x in docs:
            pn = x.get('place_name') or ''
            if not _in_gu(x, gu) or BAD_POI.search(pn) or '교통,수송' in (x.get('category_name') or ''): continue
            s = sim(hk, nname(pn, gu))
            if s >= 0.8 and (hk in nname(pn, gu) or nname(pn, gu) in hk): cands.append((s, x))
        cands = [c for c in cands if not ('>' in (c[1].get('category_name') or '') and c[0] < 1 and re.search(r'(점|호|층|동)$', c[1]['place_name']))]
        doc, why = _decide(cands, hk); trace.append(f'HOST {q}:{len(docs)}/{len(cands)}:{why}')
        if doc is not None:
            return dict(result='accepted', lon=float(doc['x']), lat=float(doc['y']), precision=hkind, query=q, place_name=doc['place_name'],
                        place_addr=doc.get('road_address_name') or doc.get('address_name'), category=doc.get('category_name'),
                        score=None, n_cand=len(cands), reason='host_' + why, trace=' || '.join(trace))
    elif host: trace.append(f'HOST {host}: linear_park_not_accepted')
    anydocs = any(re.search(r':(\d+)/', t) and re.search(r':(\d+)/', t).group(1) != '0' for t in trace)
    return dict(result='no_result' if not anydocs else 'rejected', lon=None, lat=None, precision=None, query='', place_name='', place_addr='',
                category='', score=None, n_cand=0, reason=trace[-1].split(':')[-1] if trace else '', trace=' || '.join(trace))
