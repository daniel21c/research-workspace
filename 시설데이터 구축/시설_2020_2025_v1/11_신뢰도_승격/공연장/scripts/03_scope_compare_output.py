"""공연장: 재지오코딩 반영 + 문체부 등록공연장 명부 매칭 scope_flag + 서울·구별 대조 + 좌표율."""
import sys, json, re
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parents[1]; V1 = HERE.parents[1]; SRC = V1 / '01_인허가/공연장'
sys.path.insert(0, str(V1 / '01_인허가/_common')); sys.path.insert(0, str(HERE / 'scripts'))
from lic_common import address_key, spatial_attach, tf
from importlib import import_module
mo = import_module('01_match_official')
GU = ['종로구','중구','용산구','성동구','광진구','동대문구','중랑구','성북구','강북구','도봉구','노원구','은평구','서대문구','마포구','양천구','강서구','구로구','금천구','영등포구','동작구','관악구','서초구','강남구','송파구','강동구']
GU_RE = re.compile(r'(?<![가-힣])(' + '|'.join(sorted(GU, key=len, reverse=True)) + r')(?=\s|$|\d)')
gu_of = lambda a: (lambda m: m[1] if m else None)(GU_RE.search(str(a or '')))
geo = json.load(open(HERE / 'geocode_retry_공연장.json', encoding='utf-8'))
off = mo.load_off(); rows, grows, summ = [], [], {}
for k in ['2020_01', '2025_01']:
    d = pd.read_parquet(SRC / f'facilities_공연장_{k}.parquet')
    d['coord_stage'] = np.where(d.coord_method == 'source', 'source', np.where(d.coord_method.str.startswith('geocode'), 'geocode_exact_build', 'unresolved'))
    for i in d.index[d.coord_method == 'unresolved']:
        g = geo.get(d.at[i, 'facility_id'], {})
        if g.get('status') == 'ok':
            X, Y = tf(4326, 5179).transform(g['lon'], g['lat'])
            d.loc[i, ['lon', 'lat', 'x_5179', 'y_5179']] = [g['lon'], g['lat'], X, Y]; d.at[i, 'coord_method'] = g['method']; d.at[i, 'coord_stage'] = 'geocode_exact_retry_' + g['key_kind']
    d = spatial_attach(d)
    o = off[k]; d['akey'] = d.address.map(address_key); d['nkey'] = d.name.map(mo.nk)
    m_, o['m'] = mo.match_rows(d, o)
    d['scope_flag'] = np.where(m_, '등록공연장명부_매칭', '명부_미매칭')
    d['gu'] = d.address.map(gu_of)
    d.drop(columns=['akey', 'nkey']).to_parquet(HERE / f'lic_공연장_명부매칭표시_{k}.parquet', index=False)
    d.drop(columns=['akey', 'nkey']).to_csv(HERE / f'lic_공연장_명부매칭표시_{k}.csv', index=False, encoding='utf-8-sig')
    for sc, s in (('A_전체', d), ('D_인허가중 명부매칭행', d[m_])):
        n = len(s); rows.append(dict(snapshot=k, scope=sc, built=n, official=len(o), diff=n - len(o), diff_pct=round((n - len(o)) / len(o) * 100, 2),
                                     official_matched_in_built=int(o.m.sum())))
        ok = s.inside_seoul == True; r = ok.groupby(s.gu).mean()
        bg = s.gu.value_counts(); og = o.sgg.value_counts()
        gg = pd.DataFrame({'built': bg, 'official': og}).reindex(GU).fillna(0).astype(int)
        for g, rr in gg.iterrows(): grows.append(dict(snapshot=k, scope=sc, gu=g, built=rr.built, official=rr.official, coord_rate=round(r.get(g, np.nan) * 100, 1)))
        summ[f'{k}|{sc}'] = dict(n=n, coord_rate=round(ok.mean() * 100, 2), min_gu=r.idxmin(), min_gu_rate=round(r.min() * 100, 1), n_gu_below85=int((r < .85).sum()),
                                 gu_below85=r[r < .85].round(3).to_dict(), gu_missing=int(s.gu.isna().sum()), gu_r=round(np.corrcoef(gg.built, gg.official)[0, 1], 3),
                                 coord_stage=s.coord_stage.value_counts().to_dict())
pd.DataFrame(rows).to_csv(HERE / 'official_compare_공연장.csv', index=False, encoding='utf-8-sig')
pd.DataFrame(grows).to_csv(HERE / 'official_compare_공연장_구별.csv', index=False, encoding='utf-8-sig')
json.dump(summ, open(HERE / 'summary_공연장.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(pd.DataFrame(rows).to_string()); print(json.dumps(summ, ensure_ascii=False, indent=1))
g = pd.DataFrame(grows); print(g[g.scope != 'A_전체'].pivot_table(index='gu', columns='snapshot', values=['built', 'official']).to_string())
