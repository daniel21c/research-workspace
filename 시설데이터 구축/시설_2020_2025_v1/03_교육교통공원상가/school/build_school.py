# -*- coding: utf-8 -*-
"""초·중·고·특수·각종학교 2020_01 / 2025_01
명부·규모: 서울교육통계 학교별 일람표 2019하(2019-10-01) / 2024하(2024-10-01) (A)
좌표: 학구도안내서비스 초중고 학교 위치 2019.09.16판 / 2024.09.20판(source), 미매칭(특수·각종 등)은 주소 지오코딩
2019하 일람표에는 주소가 없어 2020상(2020-04-01) 일람표의 주소를 학교명+행정구로 연결.
통학구역(초)·중학교 학구 폴리곤은 zones_*.gpkg 별도 저장."""
import sys, json, re, glob
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import fac
import pandas as pd, numpy as np

RAW = HERE / 'raw'; X = RAW / '_x'; GC = RAW / 'geocoding'
TYP = 'school'

# ---------- 1. 다운로드 ----------
def sen(board, fname_part, dest, ref):
    rj = RAW / f'sen_board{board}.json'
    fac.fetch('https://data.sen.go.kr/public/board/read', rj, 'POST',
              data=dict(site_id='public', board_group_idx=7, board_idx=board), note='게시글 메타(attach_files)')
    j = json.load(open(rj, encoding='utf-8'))
    a = [f for f in j['attach_files'] if fname_part in f['original_file_name']][0]
    fac.fetch('https://data.sen.go.kr/public/board/download', dest, 'POST',
              data=dict(group=a['file_group_id'], number=a['file_number'], filename=a['original_file_name']),
              ref_date=ref, note=j.get('board_title', ''))

sen(47, '학교 현황_2019', RAW / 'sen_2019하_학교현황.xlsx', '2019-10-01')
sen(48, '학교별 일람표', RAW / 'sen_2020상_학교별일람표.xlsx', '2020-04-01')
sen(106, '학교별 일람표', RAW / 'sen_2024하_학교별일람표.xlsx', '2024-10-01')

SZ = {  # (nttId, atchFileId) 학구도안내서비스
    'pos_20190916': (2838, 'FILE_000000100002301', '2019-09-16'), 'pos_20240920': (2928, 'FILE_000000100002699', '2024-09-20'),
    'es_20190916': (2837, 'FILE_000000100002303', '2019-09-16'), 'es_20240920': (2927, 'FILE_000000100002703', '2024-09-20'),
    'ms_20190916': (2836, 'FILE_000000100002299', '2019-09-16'), 'ms_20240920': (2926, 'FILE_000000100002698', '2024-09-20'),
    'link_20190916': (2832, 'FILE_000000100002295', '2019-09-16'), 'link_20240920': (2922, 'FILE_000000100002702', '2024-09-20')}
for k, (ntt, atch, ref) in SZ.items():
    fac.fetch('https://schoolzone.emac.kr/publicData/publicDataFileDownload.do', RAW / f'schoolzone_{k}.zip',
              params=dict(nttId=ntt, atchFileId=atch, fileSn=0), ref_date=ref, note='학구도안내서비스 반기 배포본')
    fac.unzip(RAW / f'schoolzone_{k}.zip', X / k)

def find(k, pat):
    fs = [f for f in glob.glob(str(X / k / '**' / pat), recursive=True)]
    return fs[0]

# ---------- 2. 일람표 파싱 ----------
def sen_2019():
    d = pd.read_excel(RAW / 'sen_2019하_학교현황.xlsx', sheet_name='05_학교별주요통계', header=None, dtype=str)
    h = d.index[d.iloc[:, 0].astype(str).str.strip() == '지역교육청'][0]
    b = d.iloc[h + 2:].copy()
    b.columns = ['지역교육청', '행정구', '학제', '학교명', '설립', '주야', '성별', '상태', 'sz_classes', 'sz_students',
                 '학급당학생수', 'sz_teachers', '정규교원', '기간제', '신규', '퇴직', '휴직', '교원1인당', '직원수'] + \
                [f'c{i}' for i in range(19, d.shape[1])]
    b = b[b['학교명'].notna()].copy(); b['row'] = b.index + 1
    lv = {'초등학교': '초등학교', '중학교': '중학교', '일반고': '고등학교', '특성화고(직업)': '고등학교', '자율고': '고등학교',
          '특수목적고': '고등학교', '특수학교': '특수학교', '각종학교': '각종학교', '고등기술학교': '고등기술학교'}
    b['school_level'] = b['학제'].map(lv); b['hs_type'] = np.where(b['school_level'] == '고등학교', b['학제'], None)
    b['조사기준일'] = '2019-10-01'
    return b

def sen_std(f, cls_col):
    d = pd.read_excel(f, sheet_name=0, header=None, dtype=str)
    h = d.index[d.iloc[:, 0].astype(str).str.strip() == '조사기준일'][0]
    b = d.iloc[h + 1:].copy(); b.columns = [str(c).replace('\n', '') for c in d.iloc[h]]
    b = b[b['조사기준일'].astype(str).str.match(r'^\d{8}$')].copy(); b['row'] = b.index + 1
    b = b.rename(columns={cls_col: 'sz_classes', '학생수_총계_계': 'sz_students', '교원수_총계_계': 'sz_teachers',
                          '고등학교유형': 'hs_type'})
    b['school_level'] = b['학교급']
    return b

s19 = sen_2019()
s20 = sen_std(RAW / 'sen_2020상_학교별일람표.xlsx', '학급수_계')
s24 = sen_std(RAW / 'sen_2024하_학교별일람표.xlsx', '편성학급수_계')

LEVELS = ['초등학교', '중학교', '고등학교', '특수학교', '각종학교', '고등기술학교']

def norm(n):
    return re.sub(r'[\s·・.]', '', str(n))

# ---------- 3. 학구도 좌표 ----------
def pos(k):
    p = fac.read_csv_any(find(k, '*.csv'))
    p = p[p['시도교육청명'].str.contains('서울', na=False)].copy()
    p['gu'] = p['소재지도로명주소'].fillna(p['소재지지번주소']).str.extract(r'서울특별시\s+(\S+구)')[0]
    p['nk'] = p['학교명'].map(norm)
    return p

qa = {'type': TYP, 'sources': {}, 'notes': [
    '명부 A: 서울교육통계 학교별 일람표(교육기본통계, 조사기준일 2019-10-01 / 2024-10-01). 폐교·휴교·유치원 제외. 방송통신중·고는 하반기 조사 대상이 아니라 없음.',
    '학급수 기준: 2019하는 인가학급, 2021년부터 편성학급(2024하). sz_class_basis 열에 기록 — 두 시점 학급수 직접 비교 주의.',
    '좌표: 학구도안내서비스 초중고 학교 위치(운영 본교만, 특수·각종 미수록)를 학교명(공백·가운뎃점 제거)+자치구로 매칭 → source. 미매칭은 주소 지오코딩(카카오→브이월드, 번지 일치만).',
    '2019하 일람표는 주소가 없어 2020상(2020-04-01) 일람표의 주소를 학교명+행정구로 연결(없으면 2024하 주소).']}

def build(snap, sen_df, sen_file, pos_k, addr_src):
    w = fac.SNAP[snap]
    s = sen_df[sen_df['school_level'].isin(LEVELS)].copy()
    n_all = len(s)
    st = s['상태'].value_counts().to_dict()
    s = s[~s['상태'].astype(str).str.contains('폐|휴')].copy()
    s['nk'] = s['학교명'].map(norm)
    if '주소' not in s.columns:
        s['주소'] = None
        for src in addr_src:
            a = src[['학교명', '행정구', '주소']].copy(); a['nk'] = a['학교명'].map(norm)
            a = a.drop_duplicates(['nk', '행정구'])
            m = s[['nk', '행정구']].merge(a[['nk', '행정구', '주소']], on=['nk', '행정구'], how='left')
            s['주소'] = s['주소'].fillna(pd.Series(m['주소'].values, index=s.index))
    p = pos(pos_k)
    pk = p.drop_duplicates(['nk', 'gu'])
    m = s[['nk', '행정구']].merge(pk[['nk', 'gu', '학교ID', '위도', '경도', '설립형태', '데이터기준일자']],
                                  left_on=['nk', '행정구'], right_on=['nk', 'gu'], how='left')
    m.index = s.index
    # 자치구 불일치(주소 표기 차이) 시 이름만으로 유일 매칭
    uniq = p[~p['nk'].duplicated(keep=False)].set_index('nk')
    miss = m['학교ID'].isna() & s['nk'].isin(uniq.index)
    for i in m.index[miss]:
        r = uniq.loc[s.at[i, 'nk']]
        m.loc[i, ['학교ID', '위도', '경도', '설립형태', '데이터기준일자']] = r[['학교ID', '위도', '경도', '설립형태', '데이터기준일자']].values
    s['zone_school_id'] = m['학교ID']; s['lat'] = pd.to_numeric(m['위도']); s['lon'] = pd.to_numeric(m['경도'])
    s['coord_method'] = np.where(s['lon'].notna(), 'source', None)
    s['coord_source'] = np.where(s['lon'].notna(), f'학구도안내서비스 초중고 학교 위치 {pos_k[-8:]}', None)
    s = fac.geocode_df(s, '주소', GC)
    s.loc[s['coord_method'].str.startswith('geocode', na=False), 'coord_source'] = 'SEN 일람표 주소 지오코딩'
    ref = sen_df['조사기준일'].iloc[0]; ref = f'{ref[:4]}-{ref[4:6]}-{ref[6:]}' if re.match(r'^\d{8}$', ref) else ref
    out = pd.DataFrame(index=s.index)
    out['facility_id'] = np.where(s['zone_school_id'].notna(), 'SCH_' + s['zone_school_id'].astype(str),
                                  'SCH_SEN_' + s['행정구'].astype(str) + '_' + s['nk'])
    out['category_group'] = '교육보육'; out['facility_type'] = '학교'
    out['facility_subtype'] = s['school_level'] + '|' + s['설립'].astype(str)
    out['year_snapshot'] = snap; out['name'] = s['학교명']; out['address'] = s['주소']
    out['lon'] = s['lon']; out['lat'] = s['lat']; out['coord_method'] = s['coord_method']; out['grade'] = 'A'
    out['source_org'] = '서울특별시교육청(교육통계) + 학구도안내서비스(좌표)'
    out['source_dataset'] = '학교별 일람표 ' + ('2019 하반기' if snap == '2020_01' else '2024 하반기') + f' / 초중고 학교 위치 {pos_k[-8:]}'
    out['source_url'] = 'https://data.sen.go.kr/public/board (board_group_idx=7) ; https://schoolzone.emac.kr/publicData/publicDataList.do'
    out['source_file'] = f'raw/{sen_file}'; out['source_row_id'] = s['row'].astype(str)
    out['source_reference_date'] = ref
    out['reference_month_delta'] = fac.month_delta(ref, snap)
    out['temporal_reason'] = f'교육기본통계 조사기준일 {ref}(허용창 내) 명부; 좌표 학구도 {pos_k[-8:]}판'
    out['school_level'] = s['school_level']; out['establishment'] = s['설립']; out['hs_type'] = s.get('hs_type')
    out['school_status'] = s['상태']; out['gu_name'] = s['행정구']; out['coord_source'] = s['coord_source']
    out['zone_school_id'] = s['zone_school_id']
    if 'KEDI학교코드' in s.columns: out['kedi_school_code'] = s['KEDI학교코드']
    if '개교일' in s.columns: out['open_date'] = s['개교일']
    for c in ['sz_students', 'sz_classes', 'sz_teachers']:
        out[c] = pd.to_numeric(s[c], errors='coerce')
    out['sz_class_basis'] = '인가학급(2020년까지 기준)' if snap == '2020_01' else '편성학급(2021년부터 기준)'
    out = fac.attach_geo(out)
    out = fac.write_out(out, HERE, TYP, snap)
    q = fac.qa_block(out)
    q.update(source_rows_levels=n_all, source_status=st, final=len(out),
             pos_rows_seoul=len(p), matched_to_zone_pos=int(out['zone_school_id'].notna().sum()),
             zone_pos_unmatched=sorted(set(p['학교ID']) - set(out['zone_school_id'].dropna())),
             by_level=out['school_level'].value_counts().to_dict(),
             unresolved_names=out.loc[out['coord_method'] == 'unresolved', 'name'].tolist(),
             geocoded_names=out.loc[out['coord_method'].str.startswith('geocode'), 'name'].tolist(),
             sum_students=int(out['sz_students'].sum()), sum_classes=int(out['sz_classes'].sum()),
             sum_teachers=int(out['sz_teachers'].sum()))
    # 공식 대조: 일람표 자체 학교수(폐교 제외, 휴교 포함) vs 최종
    q['official_count_sen_excl_closed'] = int((~sen_df.loc[sen_df['school_level'].isin(LEVELS), '상태'].astype(str).str.contains('폐')).sum())
    q['excluded_suspended_휴교'] = int(sen_df.loc[sen_df['school_level'].isin(LEVELS), '상태'].astype(str).str.contains('휴').sum())
    return out, q

o20, q20 = build('2020_01', s19, 'sen_2019하_학교현황.xlsx', 'pos_20190916', [s20, s24])
o25, q25 = build('2025_01', s24, 'sen_2024하_학교별일람표.xlsx', 'pos_20240920', [])
qa['2020_01'] = q20; qa['2025_01'] = q25
common = set(o20['facility_id']) & set(o25['facility_id'])
qa['panel'] = dict(common_ids=len(common), only_2020=len(set(o20['facility_id']) - common), only_2025=len(set(o25['facility_id']) - common))

# ---------- 4. 학구 폴리곤 ----------
import geopandas as gpd
zq = {}
for kind, lab in [('es', '초등학교 통학구역(공동통학구역 포함)'), ('ms', '중학교 학구 및 학군')]:
    for snap, k in [('2020_01', f'{kind}_20190916'), ('2025_01', f'{kind}_20240920')]:
        shp = find(k, '*.shp')
        g = None
        for e in ['utf-8', 'cp949']:
            try:
                g = gpd.read_file(shp, encoding=e); g['HAKGUDO_NM'].str.len(); break
            except Exception:
                g = None
        g = g[g['SD_CD'].astype(str) == '11'].to_crs(5179)
        g['year_snapshot'] = snap; g['zone_kind'] = lab; g['area_m2'] = g.area.round(1)
        g['source_file'] = f'raw/schoolzone_{k}.zip'
        fac.to_gpkg(g, HERE / f'zones_{kind}_{snap}.gpkg')
        zq[f'{kind}_{snap}'] = dict(polygons=len(g), by_gb=g['HAKGUDO_GB'].astype(str).value_counts().to_dict(),
                                    base_dt=sorted(g['BASE_DT'].astype(str).unique().tolist()))
    # 연계표(학교ID↔학구ID)
for snap, k in [('2020_01', 'link_20190916'), ('2025_01', 'link_20240920')]:
    l = fac.read_csv_any(find(k, '*.csv'))
    l = l[l.iloc[:, 4].astype(str).isin(['7010000'])]
    l.to_csv(HERE / f'zones_link_{snap}.csv', index=False, encoding='utf-8-sig'); zq[f'link_{snap}'] = len(l)
qa['zones'] = zq
fac.dump_qa(HERE, TYP, qa)
print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk in ('rows', 'coord_rate', 'coord_method', 'matched_to_zone_pos', 'outside_seoul', 'by_level', 'unresolved_names', 'official_count_sen_excl_closed')}) for k, v in qa.items() if k != 'notes'}, ensure_ascii=False, default=str, indent=0))
