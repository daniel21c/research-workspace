"""공연장: 인허가 구축본 vs 문체부 등록공연장 현황(2019.12.31 / 2024.12.31) 매칭 진단."""
import re, sys
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parents[1]; V1 = HERE.parents[1]
sys.path.insert(0, str(V1 / '01_인허가/_common')); from lic_common import address_key
def load_off():
    a = pd.read_excel(HERE / 'raw/mcst_등록공연장현황_2019말.xlsx', header=2); a.columns = ['no', 'sido', 'sgg', 'addr', 'name', 'reg', 'seats']
    b = pd.read_excel(HERE / 'raw/mcst_등록공연장현황_2024말.xlsx', header=1); b.columns = ['no', 'sido', 'sgg', 'addr', 'name', 'reg', 'seats', 'note']
    out = {}
    for k, d in (('2020_01', a), ('2025_01', b)):
        d = d[d.no.notna() & d.sido.astype(str).str.contains('서울')].copy()
        d['addr_full'] = [('' if pd.isna(x) else (str(x) if re.match(r'^서울(특별시|시)?\s', str(x)) else f'서울특별시 {g} {x}')) for x, g in zip(d.addr, d.sgg)]
        d['addr_norm'] = d.addr_full.map(norm_addr)
        d['akey'] = d.addr_norm.map(address_key); d['nkey'] = d.name.map(nk)
        out[k] = d.reset_index(drop=True)
    return out
import difflib
GU25 = ['종로구','중구','용산구','성동구','광진구','동대문구','중랑구','성북구','강북구','도봉구','노원구','은평구','서대문구','마포구','양천구','강서구','구로구','금천구','영등포구','동작구','관악구','서초구','강남구','송파구','강동구']
def match_rows(d, o):
    """d(구축)·o(명부) 모두 akey·nkey 보유. 구축 행 매칭 규칙: ① 정규화 이름 일치 또는 ② 주소키 일치 + 같은 주소 명부 공연장 이름과 유사(비율≥0.5 또는 4자 이상 포함관계).
    반환: (구축 행 bool Series, 명부 행 bool Series, 구축 행별 매칭된 명부 index)"""
    by_addr = o[o.akey != ''].groupby('akey').nkey.apply(list).to_dict(); names = set(o.nkey)
    def ok(ak, n):
        if n in names: return True
        for m in by_addr.get(ak, []):
            if difflib.SequenceMatcher(None, n, m).ratio() >= 0.5 or (min(len(n), len(m)) >= 4 and (n in m or m in n)): return True
        return False
    bm = pd.Series([ok(a, n) for a, n in zip(d.akey, d.nkey)], index=d.index)
    dm = d[bm]; dn = set(dm.nkey); da = dm.groupby('akey').nkey.apply(list).to_dict()
    def ok2(ak, n):
        if n in dn: return True
        for m in da.get(ak, []):
            if difflib.SequenceMatcher(None, n, m).ratio() >= 0.5 or (min(len(n), len(m)) >= 4 and (n in m or m in n)): return True
        return False
    om = pd.Series([ok2(a, n) for a, n in zip(o.akey, o.nkey)], index=o.index)
    return bm, om
def norm_addr(a):
    """명부 주소 표기 정리(정확 일치 규칙은 그대로): '성북구성북로5길'→'성북구 성북로5길', 'D32목동서로'→'목동서로', '지하 806'→'806', '18-0번지'→'18번지'."""
    a = str(a or '')
    a = re.sub(r'(?<=\s)(' + '|'.join(GU25) + r')(?=[가-힣]+(?:로|길)\d)', r'\1 ', a)
    a = re.sub(r'\bD\d+(?=[가-힣])', '', a)
    a = re.sub(r'(로|길)\s*지하\s*(\d)', r'\1 \2', a)
    a = re.sub(r'(\d+)-0(?=번지|\s|$)', r'\1', a)
    return re.sub(r'\s+', ' ', a).strip()
def nk(s):
    s = re.sub(r'\([^)]*\)', '', str(s)); return re.sub(r'[\s·\-_.,\'"]|주식회사|\(주\)', '', s).lower()
if __name__ == '__main__':
    off = load_off()
    for k, o in off.items():
        d = pd.read_parquet(V1 / f'01_인허가/공연장/facilities_공연장_{k}.parquet')
        d['akey'] = d.address.map(address_key); d['nkey'] = d.name.map(nk)
        d['m_off'], o['m_built'] = match_rows(d, o)
        d['yr'] = d.lic_date.str[:4].astype(float); d['has_xy'] = d.x_5179.notna()
        print(k, 'built', len(d), 'official', len(o), '| built∩off', int(d.m_off.sum()), '| off matched', int(o.m_built.sum()))
        print(pd.crosstab([d.has_xy], d.m_off))
        print(pd.crosstab(pd.cut(d.yr, [0, 2000, 2010, 2030]), d.m_off))
        print(o.loc[~o.m_built, ['sgg', 'name', 'addr_full']].head(10).to_string())
