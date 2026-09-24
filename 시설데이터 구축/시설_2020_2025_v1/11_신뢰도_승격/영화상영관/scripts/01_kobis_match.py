"""영화상영관 극장단위 구축본 ↔ KOBIS 영화상영관정보(서울, 전체 영업상태, 2026-09-24 조회) 매칭."""
import re, sys, difflib
from io import StringIO
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parents[1]; V1 = HERE.parents[1]; SRC = V1 / '01_인허가/영화상영관'
sys.path.insert(0, str(V1 / '01_인허가/_common')); from lic_common import address_key
GU = ['종로구','중구','용산구','성동구','광진구','동대문구','중랑구','성북구','강북구','도봉구','노원구','은평구','서대문구','마포구','양천구','강서구','구로구','금천구','영등포구','동작구','관악구','서초구','강남구','송파구','강동구']
GU_RE = re.compile(r'(?<![가-힣])(' + '|'.join(sorted(GU, key=len, reverse=True)) + r')(?=\s|$|\d)')
def gu_of(a):
    m = GU_RE.search(str(a or '')); return m[1] if m else None
ALIAS = {'씨지브이': 'cgv', '롯데컬처웍스주롯데시네마': '롯데시네마', '메가박스중앙주': '메가박스', '메가박스주': '메가박스', '롯데컬처웍스주': '롯데시네마'}
def nn(s):
    s = re.sub(r'\([^)]*\)|<<[^>]*>>|-폐관|폐관', '', str(s)).lower()
    s = re.sub(r'[\s·\-_.,\'"?&]|\(주\)|주식회사', '', s)
    for a, b in ALIAS.items(): s = s.replace(a, b)
    return s.replace('지점', '').replace('점', '').replace('관', '')
def load_kobis():
    t = open(HERE / 'raw/kobis_theater_list_seoul_all_20260924.xls', encoding='utf-8').read()
    k = max(pd.read_html(StringIO(t)), key=len)
    k['개관일'] = pd.to_datetime(k['개관일'], errors='coerce'); k['nkey'] = k['영화상영관명'].map(nn)
    k['pkey'] = k['주소'].fillna('').map(lambda a: address_key(re.sub(r'\s+번지', '번지', a)))
    return k
def match(b, k):
    """b: 극장단위 df. 반환: kobis 코드 list (같은 구 안에서 주소키 일치 또는 이름 유사도≥0.6)."""
    b = b.copy(); b['gu'] = b.address.map(gu_of); b['nkey'] = b.name.map(nn)
    raw = pd.read_csv(SRC / 'raw/movie_theaters_seoul_OA-16053.csv', encoding='cp949', dtype=str)
    jib = dict(zip(raw['관리번호'], raw['지번주소']))
    b['pkeys'] = b.source_row_id.map(lambda s: {address_key(jib.get(x.split(':', 1)[1], '') or '') for x in str(s).split(';')} - {''})
    out = []
    for _, r in b.iterrows():
        c = k[k['기초단체'] == r.gu]
        hit = c[c.pkey.isin(r.pkeys)]
        how = 'parcel'
        if hit.empty:
            sc = c.nkey.map(lambda x: difflib.SequenceMatcher(None, x, r.nkey).ratio())
            hit = c[sc >= 0.6]; how = 'name'
        out.append(dict(theater_key=r.theater_key, gu=r.gu, name=r['name'], screens=r.sz_screens, how=how if len(hit) else 'none',
                        kobis_cd=';'.join(hit['영화상영관코드'].astype(str)), kobis_nm=';'.join(hit['영화상영관명']),
                        kobis_open=hit['개관일'].min(), kobis_stat=';'.join(sorted(set(hit['영업상태']))), kobis_perm=';'.join(sorted(set(hit['상설여부'])))))
    return pd.DataFrame(out)
if __name__ == '__main__':
    pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
    k = load_kobis()
    print('KOBIS 서울 전체', len(k), k['영업상태'].value_counts().to_dict(), k['상설여부'].value_counts().to_dict())
    for D in ['2019-12-31', '2024-12-31']:
        kk = k[k['개관일'] <= D]
        print(D, '개관≤D', len(kk), '상설', int((kk['상설여부'] == '상설').sum()), '현재영업&상설', int(((kk['영업상태'] == '영업') & (kk['상설여부'] == '상설')).sum()))
    res = []
    for snap in ['2020_01', '2025_01']:
        b = pd.read_parquet(SRC / f'facilities_영화상영관_극장단위_{snap}.parquet')
        m = match(b, k); m['snapshot'] = snap; res.append(m)
        print(snap, m.how.value_counts().to_dict())
    m = pd.concat(res); m.to_csv(HERE / 'kobis_match_영화상영관.csv', index=False, encoding='utf-8-sig')
    print(m[m.how != 'parcel'].drop_duplicates('theater_key')[['gu', 'name', 'screens', 'how', 'kobis_nm', 'kobis_open', 'kobis_stat']].to_string())
