"""HIRA 요양기관개설현황(data.go.kr 15051057) 대조. 2024.12판 = 2025_01 직접 대조, 2021.12판 개설일자≤2019-12-31 = 2020_01 하한 대조."""
import re
import pandas as pd
from lic_common import LIC_ROOT, address_key
H24 = LIC_ROOT / '의원/raw/hira_establishments_20241231.csv'
H21 = LIC_ROOT / '의원/raw/hira_establishments_20211231.csv'
MAP = {'상급종합병원': '종합병원'}

def norm(s):
    s = s.fillna('').str.replace(r'\([^)]*\)', '', regex=True)
    s = s.str.replace(r'의료법인|재단법인|사회복지법인|학교법인|사단법인|주식회사|\(주\)|㈜', '', regex=True)
    return s.str.replace(r'[^0-9A-Za-z가-힣]', '', regex=True).str.lower()

def gu_of(a):
    return a.fillna('').str.extract(r'서울특별시\s*([가-힣]+구)')[0].fillna('')

def load(which):
    p = H24 if which == 2024 else H21
    d = pd.read_csv(p, encoding='cp949', dtype=str)
    d = d[d['시도명'] == '서울특별시'].copy()
    addr = d['도로명주소'] if '도로명주소' in d else d['주소']
    d['addr'] = addr
    key = ['암호화된요양기호'] if '암호화된요양기호' in d else ['요양기관명', 'addr', '요양종별']
    d = d.drop_duplicates(key)
    d['kind'] = d['요양종별'].map(lambda v: MAP.get(v, v))
    d['nk'] = d['시군구명'].fillna('') + '|' + norm(d['요양기관명'])
    d['ak'] = d['addr'].map(address_key) + '|' + d['kind']
    d['open'] = pd.to_datetime(d['개설일자'], errors='coerce')
    return d

def compare(ours: pd.DataFrame, which: int, kinds, open_le=None):
    h = load(which)
    if open_le is not None:
        h = h[h.open <= pd.Timestamp(open_le)]
    h = h[h.kind.isin(kinds)]
    o = ours[ours.facility_subtype.isin(kinds)].copy()
    o['nk'] = gu_of(o.address) + '|' + norm(o.name)
    o['ak'] = o.address.map(address_key) + '|' + o.facility_subtype
    hn, ha = set(h.nk), set(h.ak)
    on, oa = set(o.nk), set(o.ak)
    res = {}
    for k in kinds:
        hk = h[h.kind == k]; ok = o[o.facility_subtype == k]
        res[k] = {'hira': int(len(hk)), 'ours': int(len(ok)), 'diff_ours_minus_hira': int(len(ok) - len(hk)),
                  'ratio_ours_to_hira': round(len(ok) / len(hk), 4) if len(hk) else None,
                  'ours_matched_in_hira_name_or_addr': round(float((ok.nk.isin(hn) | ok.ak.isin(ha)).mean()), 4) if len(ok) else None,
                  'hira_matched_in_ours_name_or_addr': round(float((hk.nk.isin(on) | hk.ak.isin(oa)).mean()), 4) if len(hk) else None}
    return res

def official(outputs, kinds):
    return {
        '2025_01_vs_HIRA_20241231': {'source': 'raw/../의원/raw/hira_establishments_20241231.csv (data.go.kr 15051057 FILE_000000003181518)',
                                      'note': '상급종합병원은 종합병원에 합산. 매칭 = 같은 구+정규화 기관명 또는 같은 도로명주소·건물번호+종별.',
                                      'by_kind': compare(outputs['2025_01'], 2024, kinds)},
        '2020_01_vs_HIRA_20211231_open_le_20191231': {'source': '의원/raw/hira_establishments_20211231.csv (FILE_000000002512937)',
                                      'note': '2021.12판 개설중 기관 중 개설일자≤2019-12-31 → 2020~2021 폐업기관이 빠진 하한값(역산 수는 이보다 커야 정상). 2021년 이후 주소 이전 기관은 주소 매칭 실패 가능.',
                                      'by_kind': compare(outputs['2020_01'], 2021, kinds, open_le='2019-12-31')},
    }
