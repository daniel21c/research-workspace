"""영화상영관(스크린=상영관 단위 등록) 2020_01·2025_01 역산 + 같은 건물주소 기준 극장 단위 집계본."""
import sys, hashlib, re
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))
from lic_common import build, address_key, COMMON_COLS
from sources import src

SCREEN_PAT = r'\s*[\(（]?\s*(제\s*)?\d+\s*관\s*[\)）]?\s*$|\s*상영관\s*[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ0-9]+\s*$|\s*[A-Za-z가-힣]*관\s*$'

def theater_key(addr):
    k = address_key(addr or '')
    return k if k else re.sub(r'\s+', '', re.sub(r'\([^)]*\)|,.*$', '', str(addr or '')))

def aggregate(outputs, here):
    info = {}
    for k, s in outputs.items():
        s = s.copy()
        s['tkey'] = s.address.map(theater_key)
        s['base_name'] = s.name.fillna('').str.replace(SCREEN_PAT, '', regex=True).str.strip()
        rows = []
        for key, g in s.groupby('tkey', sort=True):
            rep = g.sort_values(['coord_method', 'facility_id']).iloc[0].to_dict()   # 'source' 가 먼저
            r = {c: rep[c] for c in COMMON_COLS}
            r['facility_id'] = 'LIC-movie_theaters-THEATER-' + hashlib.sha1(key.encode()).hexdigest()[:12]
            r['facility_subtype'] = '영화관(극장 단위 집계)'
            r['name'] = g.base_name.mode().iloc[0] if g.base_name.str.len().gt(0).any() else rep['name']
            r['source_row_id'] = ';'.join(g.source_row_id.astype(str))
            r['temporal_reason'] = rep['temporal_reason'] + ';상영관 등록을 건물주소(도로명+건물번호)로 묶은 극장 단위'
            r['sz_screens'] = int(len(g)); r['sz_area_m2'] = float(g.sz_area_m2.sum(min_count=1)) if g.sz_area_m2.notna().any() else None
            r['screen_names'] = ' | '.join(g.name.astype(str))
            r['theater_key'] = key
            rows.append(r)
        t = pd.DataFrame(rows).sort_values('facility_id').reset_index(drop=True)
        fn = f'facilities_영화상영관_극장단위_{k}'
        t.to_csv(here / f'{fn}.csv', index=False, encoding='utf-8-sig'); t.to_parquet(here / f'{fn}.parquet', index=False)
        info[k] = {'n_theaters': int(len(t)), 'n_screens': int(len(s)), 'theaters_1_screen': int((t.sz_screens == 1).sum()),
                   'max_screens': int(t.sz_screens.max()) if len(t) else 0, 'coord_rate': round(float((t.coord_method != 'unresolved').mean()), 4) if len(t) else None}
    return {'theater_aggregate': info}

CFG = {
    'type': '영화상영관', 'category_group': '문화체육녹지', 'sources': [src('movie_theaters', subtype='상영관(스크린)')],
    'size_map': {'sz_area_m2': '시설면적', 'sz_floors_total': '총층수'},
    'attr_map': {'attr_building_use': '건물용도명', 'attr_first_registered': '최초등록시점'},
    'geocode': True, 'extra_qa_fn': aggregate, 'dedup': False,   # 같은 이름·주소·등록일 상영관이 여러 개인 것은 정상(스크린별 등록)
    'official_note': '영화진흥위원회 KOBIS 연도별 극장·스크린 수(서울) 대조 미실시',
    'notes': ['원천 1행 = 상영관(스크린) 1개. 극장 단위본(facilities_영화상영관_극장단위_*)은 같은 도로명주소+건물번호로 묶음(한 건물 두 극장은 합쳐질 수 있음).',
              '영화상영업(film_screenings, 사업자 단위)은 별도 원천이며 여기서는 쓰지 않음.'],
}
if __name__ == '__main__':
    out, qa = build(CFG, HERE)
    print({k: qa[k]['n_final'] for k in out}, qa['theater_aggregate'], qa['geocoding'])
