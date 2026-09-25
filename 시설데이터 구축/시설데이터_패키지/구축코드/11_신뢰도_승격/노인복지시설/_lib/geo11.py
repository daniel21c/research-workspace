# -*- coding: utf-8 -*-
"""11_신뢰도_승격 좌표 보완 도우미.
1) 주소 표기 정규화 변형(괄호·층·호 제거, 도로명 내부 띄어쓰기 제거, 'X동[Y동] N번지 M호'→'Y동 N-M')으로 mb.geocode(Kakao→VWorld, 건물번호/번지 일치) 재시도
2) Kakao 키워드(시설명) 검색 결과 중 도로명+건물번호 또는 법정동+번지가 명부 주소와 정확히 같은 장소만 채택
API 키는 mb.keys()로만 접근, 출력하지 않음. 초당 10건 이하(요청 간 0.12초)."""
import re, time, json, hashlib, sys
import pandas as pd
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import u11  # noqa
mb = u11.mb

_last = [0.0]


def _throttle():
    dt_ = time.time() - _last[0]
    if dt_ < 0.12:
        time.sleep(0.12 - dt_)
    _last[0] = time.time()


def variants(addr):
    a0 = mb.clean(addr)
    out = []
    a = re.sub(r'\[[^\]]*\]', lambda m: ' ' + m.group(0)[1:-1] + ' ', a0)          # 논현제1동[논현동] → 논현동
    a = re.sub(r'[가-힣]+제?\d+동\s+([가-힣]+동)\s', r'\1 ', a)                     # 행정동 뒤 법정동 → 법정동만
    a = re.sub(r'(\d+)\s*번지\s*(\d+)\s*호', r'\1-\2', a)
    a = re.sub(r'(\d+)\s*번지', r'\1', a)
    a = re.sub(r'\([^)]*\)', ' ', a)
    a = re.sub(r'(로\d+길)\s+(\d+)길', r'\1 \2', a)                                # 동남로81길 8길 → 동남로81길 8
    a = re.sub(r'(로)\s+(\d+)\s*([가-힣]?길|번길)', r'\1\2\3', a)                     # 월드컵북로 47길 → 월드컵북로47길
    a = re.sub(r'(\d+)\s+(가길|번길)', r'\1\2', a)                                 # 응암로21 가길 → 응암로21가길
    a = re.sub(r'(구 )([가-힣]{1,4}(?<![동가리구시]))\s+([가-힣]+(?:로|길))(?=\s*\d)', r'\1\2\3', a)  # 조원 중앙로 → 조원중앙로
    a = re.sub(r'\s+', ' ', a).strip()
    # PDF 추출 등으로 붙은 표기 분리
    a = re.sub(r'^(서울특별시|서울시|서울(?!특별시|시))(?=[가-힣])', r'\1 ', a)
    for g in sorted(mb.GU, key=len, reverse=True):
        a = re.sub(r'(?<=[\s시])' + g + r'(?=[가-힣0-9])', g + ' ', a)
    a = re.sub(r'(로|길)\s*,\s*(\d)', r'\1 \2', a)                                  # 신리로58길, 8 → 신리로58길 8
    a = re.sub(r'(로|길)\s*(\d+(?:-\d+)?)(\d)층', r'\1 \2 \3층', a)                  # 오현로1892층 → 오현로 189 2층
    a = re.sub(r'(로|길)(\d+(?:-\d+)?)(?!\d|-|[가-힣]?길|번길|가(?:\s|$|\d))', r'\1 \2', a)  # 화랑로130 → 화랑로 130
    a = re.sub(r'(\d),\s*\d+층.*$', r'\1', a)                                       # 272,4층 → 272
    a = re.sub(r'\s+', ' ', a).strip()
    for x in (a, a0):
        if x and x not in out:
            out.append(x)
    return out


def geocode_variants(addr, cdir):
    last = (None, None, 'unresolved', 'no_variant')
    for v in variants(addr):
        _throttle()
        r = mb.geocode(v, cdir)
        if r[0] is not None:
            return r[0], r[1], r[2], r[3] + (f' | variant:{v}' if v != mb.clean(addr) else '')
        last = r
    return last


def _kakao_kw(q):
    r = mb._S.get('https://dapi.kakao.com/v2/local/search/keyword.json', params={'query': q, 'size': 15},
                  headers={'Authorization': 'KakaoAK ' + mb.keys()['KAKAO_REST_API_KEY']}, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f'kakao kw http {r.status_code}')
    return r.json()


def keyword_exact(name, addr, cdir, extra=''):
    """시설명 키워드 검색 → 장소의 도로명/지번 주소가 명부 주소 후보와 정확히 일치할 때만 채택."""
    cands = []
    for v in variants(addr)[:1]:          # 정규화된 첫 변형만(원문 오파싱 방지)
        cands += mb.parse_addr(v) or []
    if not cands:
        return None, None, 'unresolved', 'parse_fail'
    q = (extra + ' ' + mb.clean(name)).strip()
    _throttle()
    rec = mb._cached(cdir, 'kakaokw', q, _kakao_kw)
    docs = (rec.get('response') or {}).get('documents', []) if 'response' in rec else []
    for d in docs:
        ra = mb.parse_addr(d.get('road_address_name') or '') or []
        ja = mb.parse_addr(d.get('address_name') or '') or []
        for c in cands:
            for p in (ra if c['kind'] == 'road' else ja):
                if p['kind'] != c['kind']:
                    continue
                if c['kind'] == 'road' and mb._norm_road(p['road']) == mb._norm_road(c['road']) and p['main'] == c['main'] and p['sub'] == c['sub']:
                    return float(d['x']), float(d['y']), 'geocode_kakao_keyword_addr_exact', f"kw:{q} → {d.get('place_name')} / {d.get('road_address_name')}"
                if c['kind'] == 'jibun' and p['dong'] == c['dong'] and p['main'] == c['main'] and p['sub'] == c['sub'] and p['san'] == c['san']:
                    return float(d['x']), float(d['y']), 'geocode_kakao_keyword_addr_exact', f"kw:{q} → {d.get('place_name')} / {d.get('address_name')}"
    return None, None, 'unresolved', 'kw_no_exact:' + q


def fill(df, cdir, name_col='name', addr_col='address', gu_col='gu', mask=None, kw=True):
    """좌표 없는 행(mask)만 보완. lon/lat/coord_method/coord_stage/geocode_detail2 갱신한 사본 반환."""
    df = df.copy()
    if 'coord_stage' not in df:
        df['coord_stage'] = df['lon'].notna().map({True: 'original', False: 'missing'})
    m = df['lon'].isna() if mask is None else (df['lon'].isna() & mask)
    df['geocode_detail2'] = df.get('geocode_detail2', '')
    for i in df.index[m]:
        lon, lat, meth, det = geocode_variants(df.at[i, addr_col], cdir)
        if lon is None and kw:
            gu = df.at[i, gu_col] if gu_col in df else ''
            lon, lat, meth, det = keyword_exact(df.at[i, name_col], df.at[i, addr_col], cdir, extra=str(gu or ''))
        if lon is not None:
            df.at[i, 'lon'] = lon; df.at[i, 'lat'] = lat; df.at[i, 'coord_method'] = meth
            df.at[i, 'coord_stage'] = 'filled_11'
        df.at[i, 'geocode_detail2'] = det
    return df


def respatial(df, lib='mb'):
    """coord_stage=='filled_11' 행만 원 빌드와 같은 함수로 x_5179,y_5179,inside_seoul,adm_dong_cd,oa_cd,grid100_cd 재계산."""
    df = df.copy()
    m = df.get('coord_stage', pd.Series('', index=df.index)) == 'filled_11'
    if not m.any():
        return df
    sub = df.loc[m].copy()
    if lib == 'mb':
        r = mb.spatial(sub[['lon', 'lat']].reset_index(drop=True))
    else:
        r = u11.fac.attach_geo(sub[['lon', 'lat']].reset_index(drop=True))
    for c in ['x_5179', 'y_5179', 'inside_seoul', 'adm_dong_cd', 'oa_cd', 'grid100_cd']:
        df[c] = df[c].astype(object)
        df.loc[m, c] = r[c].values
    for c in ['x_5179', 'y_5179', 'lon', 'lat']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    if lib != 'mb':
        df['inside_seoul'] = df['inside_seoul'].map(lambda v: pd.NA if v is None or v is pd.NA or (isinstance(v, float) and v != v) else bool(v)).astype('boolean')
    return df


def coord_rate_by_gu(df, gu_col):
    ok = pd.to_numeric(df['x_5179'], errors='coerce').notna() & (df['inside_seoul'].astype(str) == 'True')
    ok_any = pd.to_numeric(df['x_5179'], errors='coerce').notna()
    g = pd.DataFrame({'gu': df[gu_col].values, 'ok': ok_any.values})
    r = g.groupby('gu').agg(n=('ok', 'size'), coord=('ok', 'sum')).reindex(u11.GU).fillna(0).astype(int)
    r['rate'] = (r.coord / r.n.replace(0, float('nan'))).round(4)
    return r
