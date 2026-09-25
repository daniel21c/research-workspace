"""공연장 채택본: 문체부 「등록공연장 현황」(2019.12.31 / 2024.12.31) 서울 행 = 시설 목록(T·D는 공식 명부 그대로).
좌표: ① 인허가(OA-16021) 행 중 주소키(도로명+건물번호 / 동+번지) 완전 일치 & 원천 좌표 보유 → 차용(coord_method=borrowed_lic_same_addrkey)
      ② 없으면 명부 주소를 Kakao→VWorld 정확 일치 지오코딩(lic_common.geocode_one, 캐시 raw/geocoding)
공간 속성(x_5179,y_5179,inside_seoul,adm_dong_cd,oa_cd,grid100_cd)은 01_인허가/_common/lic_common.spatial_attach 로 원 빌드와 같게."""
import sys, json, time
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parents[1]; V1 = HERE.parents[1]; SRC = V1 / '01_인허가/공연장'
sys.path.insert(0, str(V1 / '01_인허가/_common')); sys.path.insert(0, str(HERE / 'scripts'))
from lic_common import address_key, geocode_one, load_keys, spatial_attach, tf, COMMON_COLS
from importlib import import_module
mo = import_module('01_match_official')
URL = {'2020_01': ('https://www.mcst.go.kr/site/s_policy/dept/deptView.jsp?pSeq=1403&pDataCD=0417000000', 'mcst_등록공연장현황_2019말.xlsx', '2019-12-31'),
       '2025_01': ('https://www.mcst.go.kr/site/s_policy/dept/deptView.jsp?pSeq=2085&pDataCD=0417000000', 'mcst_등록공연장현황_2024말.xlsx', '2024-12-31')}
secret = load_keys(); cache = HERE / 'raw/geocoding'; off = mo.load_off(); summ = {}
lic = pd.concat([pd.read_parquet(SRC / f'facilities_공연장_{k}.parquet') for k in URL])
lic = lic[lic.coord_method == 'source'].copy(); lic['akey'] = lic.address.map(address_key)
lic_xy = lic[lic.akey != ''].groupby('akey')[['lon', 'lat']].median()     # 같은 주소키 → 같은 건물
for k, (url, fn, ref) in URL.items():
    o = off[k].copy()
    d = pd.DataFrame({'facility_id': [f'MCST-REGHALL-{k[:4]}-{int(n):04d}' for n in o.no], 'category_group': '문화체육녹지', 'facility_type': '공연장',
                      'facility_subtype': '등록공연장', 'year_snapshot': k, 'name': o.name.values, 'address': o.addr_full.values})
    d['lon'] = np.nan; d['lat'] = np.nan; d['coord_method'] = 'unresolved'
    other = off['2025_01' if k == '2020_01' else '2020_01']
    o['akey_src'] = np.where(o.akey != '', 'self', '')
    for i in o.index[o.akey == '']:          # 명부 주소 결측 → 다른 연도 명부의 같은 구·같은 정규화 이름 1건 주소 차용
        c = other[(other.sgg == o.at[i, 'sgg']) & (other.nkey == o.at[i, 'nkey']) & (other.akey != '')]
        if len(c.akey.unique()) == 1:
            o.at[i, 'akey'] = c.akey.iloc[0]; o.at[i, 'akey_src'] = 'other_edition_same_name'; d.at[i, 'address'] = c.addr_full.iloc[0] + ' (다른 연도 명부 주소 차용)'
    for i, ak in enumerate(o.akey):
        if ak and ak in lic_xy.index:
            d.loc[i, ['lon', 'lat']] = lic_xy.loc[ak].values; d.at[i, 'coord_method'] = 'borrowed_lic_same_addrkey'
    t0 = time.time()
    for i in d.index[d.coord_method == 'unresolved']:
        ak = o.akey[i]
        if not ak: continue
        r = geocode_one(ak, secret, cache)
        if r: d.loc[i, ['lon', 'lat']] = [r[0], r[1]]; d.at[i, 'coord_method'] = r[2]
    ok = d.lon.notna(); d['x_5179'] = np.nan; d['y_5179'] = np.nan
    X, Y = tf(4326, 5179).transform(d.loc[ok, 'lon'].values, d.loc[ok, 'lat'].values); d.loc[ok, 'x_5179'] = X; d.loc[ok, 'y_5179'] = Y
    d['grade'] = 'A'; d['source_org'] = '문화체육관광부'; d['source_dataset'] = f'등록공연장 현황({ref} 기준)'; d['source_url'] = url
    d['source_file'] = f'11_신뢰도_승격/공연장/raw/{fn}'; d['source_row_id'] = [f'연번{int(n)}' for n in o.no]; d['source_reference_date'] = ref
    d['reference_month_delta'] = 1; d['temporal_reason'] = '공식 명부 연말 기준일(목표 창 안)'
    d = spatial_attach(d)
    d['gu'] = o.sgg.values; d['seats'] = pd.to_numeric(o.seats, errors='coerce').values; d['reg_date'] = pd.to_datetime(o.reg, errors='coerce').dt.strftime('%Y-%m-%d').values
    d['coord_stage'] = d.coord_method.map({'borrowed_lic_same_addrkey': '1_인허가 동일주소키 좌표', 'geocode_kakao_exact': '2_명부주소 정확지오코딩',
                                           'geocode_vworld_exact': '2_명부주소 정확지오코딩', 'unresolved': 'unresolved'})
    d['scope_flag'] = '문체부 등록공연장 명부'; d['address_normalized'] = o.addr_norm.values; d['address_key_source'] = o.akey_src.values
    d = d[COMMON_COLS + ['gu', 'seats', 'reg_date', 'coord_stage', 'scope_flag', 'address_normalized', 'address_key_source']]
    d.to_parquet(HERE / f'facilities_공연장_{k}.parquet', index=False); d.to_csv(HERE / f'facilities_공연장_{k}.csv', index=False, encoding='utf-8-sig')
    ins = d.inside_seoul == True; r = ins.groupby(d.gu).mean()
    summ[k] = dict(n=len(d), coord_rate=round(ins.mean() * 100, 2), outside_seoul=int((d.inside_seoul == False).sum()), min_gu=r.idxmin(), min_gu_rate=round(r.min() * 100, 1),
                   gu_below85=r[r < .85].round(3).to_dict(), n_gu=int(d.gu.nunique()), coord_method=d.coord_method.value_counts().to_dict(),
                   unresolved=d.loc[~ins, ['gu', 'name', 'address']].values.tolist(), geocode_sec=round(time.time() - t0, 1))
json.dump(summ, open(HERE / 'summary_공연장_명부채택본.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(summ, ensure_ascii=False, indent=1))
