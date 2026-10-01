# -*- coding: utf-8 -*-
"""P2. 32종 시설 분석용 파일에 경계 단위(동424·구·공식생활권116·Leiden 2020/2025)·카테고리(A 7개, A4, B 4개+τ, 역할)·250m 격자 코드를 붙인다.
입력: a00_config.FACILITY_PARQUET, BOUND_GPKG(dong_424), DONG_LZ_MAP, DONG_LD_MAP, GRID250_SRC
출력: 데이터/입력/facility/facility_2020_2025_units.parquet, 문서/시설경계연결_구축기록.md, 데이터/manifest_sha256.csv 갱신
(2026-09-25부터 355 MB csv 사본은 만들지 않는다 — 같은 내용이 parquet 에 있음)
규칙: 지표정의_확정.md §1(시설 점 → 동424 폴리곤 → 구·LZ·LD), §2(카테고리). 동 폴리곤 밖의 점은 50m 이내 최근접 동, 아니면 NA.
"""
import sys, hashlib, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import a00_config as C

NEAREST_MAX_M = 50
OUT_PQ = C.DATA / 'facility' / 'facility_2020_2025_units.parquet'
REC_MD = C.REC / '시설경계연결_구축기록.md'
MANIFEST = C.MANIFEST

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def append_manifest(paths, script):
    """해시 목록 갱신은 a99_manifest(문자열 보존)로 한다."""
    import a99_manifest as M
    rows = [M.row(p, script, M.count_rows(p)) for p in paths]
    M.update(rows)
    return rows

# ---------- 카테고리 ----------
FAC2CATA = {f: k for k, fs in C.CAT_A.items() for f in fs}
CATA2A4 = {a: k for k, cs in C.CAT_A4.items() for a in cs}

def assign_cat_B(df):
    """CAT_B 규칙: (카테고리, 시설, 세부조건, τ). 첫 일치 규칙 적용."""
    cat = pd.Series(pd.NA, index=df.index, dtype='string')
    tau = pd.Series(pd.NA, index=df.index, dtype='Int64')
    for name, fac, cond, t in C.CAT_B:
        m = (df['시설'] == fac) & cat.isna()
        if cond is not None:
            m &= df['시설_세부'].map(lambda s: bool(cond(s)) if pd.notna(s) else False).astype(bool)
        cat[m] = name; tau[m] = t
    return cat, tau

def grid250_code(x, y):
    """국가격자체계 250m 코드(다사 블록, 원점 900000/1900000). gid = '다사' + XX(km) + {aa,ab,ba,bb}[250m 순번] + YY(km) + {..}.
    GRID250_SRC(서울_격자_250_5179_clean.gpkg)의 gid와 동일한 부호화임을 본 스크립트에서 표본 검증한다."""
    sub = np.array(['aa', 'ab', 'ba', 'bb'])
    ix = np.floor((np.asarray(x, float) - 900000) / 250).astype('int64')
    iy = np.floor((np.asarray(y, float) - 1900000) / 250).astype('int64')
    out = np.array(['다사' + f'{a // 4:02d}' + sub[a % 4] + f'{b // 4:02d}' + sub[b % 4] for a, b in zip(ix, iy)], dtype=object)
    return out

def main():
    t0 = dt.datetime.now()
    log = []
    P = lambda s: (print(s), log.append(s))
    P(f'# 시설–경계 연결 구축기록 (P2)\n\n- 실행: {t0:%Y-%m-%d %H:%M} · 스크립트 `코드/a02_facility_boundary.py`')
    P(f'- 입력 시설: `{C.FACILITY_PARQUET.name}` sha256={sha256(C.FACILITY_PARQUET)}')
    P(f'- 입력 경계: `{C.BOUND_GPKG.name}` layer dong_424 sha256={sha256(C.BOUND_GPKG)}')
    for p in [C.DONG_LZ_MAP, C.DONG_LD_MAP[2020], C.DONG_LD_MAP[2025]]:
        P(f'- 입력 매핑: `{p.name}` sha256={sha256(p)}')
    P(f'- 250m 격자: `{C.GRID250_SRC.name}` sha256={sha256(C.GRID250_SRC)}')

    fac = pd.read_parquet(C.FACILITY_PARQUET)
    n0 = len(fac)
    P(f'\n## 1. 입력\n- 행 {n0:,} (연도별 {fac.year.value_counts().sort_index().to_dict()}), 좌표 결측 {fac.x_5179.isna().sum():,}, 분석가능 True {int(fac["분석가능"].sum()):,}')

    # ---------- 동424 공간결합 ----------
    dong = gpd.read_file(C.BOUND_GPKG, layer='dong_424')[['Dong', 'Ku', 'ku_name', 'ADM_NM', 'geometry']]
    assert dong.crs.to_epsg() == C.CRS
    has_xy = fac.x_5179.notna() & fac.y_5179.notna()
    pts = gpd.GeoDataFrame(fac.loc[has_xy, []], geometry=gpd.points_from_xy(fac.loc[has_xy, 'x_5179'], fac.loc[has_xy, 'y_5179']), crs=C.CRS)
    j = gpd.sjoin(pts, dong, how='left', predicate='intersects')
    dup = j.index.duplicated(keep='first')
    n_dup = int(dup.sum()); j = j[~dup]
    miss = j.Dong.isna()
    n_miss = int(miss.sum())
    n_near = 0; n_far = 0
    if n_miss:
        jn = gpd.sjoin_nearest(pts.loc[j.index[miss]], dong, how='left', max_distance=NEAREST_MAX_M, distance_col='d_m')
        jn = jn[~jn.index.duplicated(keep='first')]
        ok = jn.Dong.notna(); n_near = int(ok.sum()); n_far = int((~ok).sum())
        for col in ['Dong', 'Ku', 'ku_name', 'ADM_NM']:
            j.loc[jn.index[ok], col] = jn.loc[ok, col].values
        j['nearest_d_m'] = np.nan; j.loc[jn.index, 'nearest_d_m'] = jn['d_m'].values
    fac['dong424'] = pd.array(j['Dong'].reindex(fac.index).astype('Int64'), dtype='Int64')
    fac['ku'] = pd.array(j['Ku'].reindex(fac.index).astype('Int64'), dtype='Int64')
    fac['ku_name'] = j['ku_name'].reindex(fac.index).astype('string')
    fac['dong424_name'] = j['ADM_NM'].reindex(fac.index).astype('string')
    fac['dong424_method'] = pd.Series(pd.NA, index=fac.index, dtype='string')
    fac.loc[fac.dong424.notna(), 'dong424_method'] = 'within'
    if n_miss:
        fac.loc[jn.index[ok], 'dong424_method'] = f'nearest<={NEAREST_MAX_M}m'
    P(f'\n## 2. 동424 배정\n- 좌표 있는 점 {int(has_xy.sum()):,} 중 폴리곤 내부(intersects) {int((~miss).sum()):,}, 경계선 위 중복(첫 동 유지) {n_dup:,}, 폴리곤 밖 {n_miss:,} → 50m 이내 최근접 동 {n_near:,}, 50m 초과 NA {n_far:,}')
    P(f'- 좌표 없는 행 {int((~has_xy).sum()):,} → dong424 NA')

    # ---------- LZ · LD ----------
    lz = pd.read_csv(C.DONG_LZ_MAP)[['Dong', 'life_zone_id']].rename(columns={'life_zone_id': 'lz116'})
    l20 = pd.read_csv(C.DONG_LD_MAP[2020])[['Dong', 'global_community_id']].rename(columns={'global_community_id': 'ld2020'})
    l25 = pd.read_csv(C.DONG_LD_MAP[2025])[['Dong', 'global_community_id']].rename(columns={'global_community_id': 'ld2025'})
    mp = lz.merge(l20, on='Dong').merge(l25, on='Dong'); assert len(mp) == 424
    fac = fac.merge(mp, left_on='dong424', right_on='Dong', how='left').drop(columns='Dong')
    for col in ['lz116', 'ld2020', 'ld2025']:
        fac[col] = fac[col].astype('Int64')
    assert (fac.lz116.isna() == fac.dong424.isna()).all()

    # ---------- 카테고리 ----------
    unknown = set(fac['시설'].dropna().unique()) - set(FAC2CATA) - set(C.CONTROL)
    assert not unknown, f'카테고리 미정 시설: {unknown}'
    fac['cat_A'] = fac['시설'].map(FAC2CATA).astype('string')
    fac.loc[fac['시설'].isin(C.CONTROL), 'cat_A'] = 'control'
    fac['cat_A4'] = fac['cat_A'].map(CATA2A4).astype('string')
    fac.loc[fac['cat_A'] == 'control', 'cat_A4'] = 'control'
    fac['cat_B'], fac['tau_B_min'] = assign_cat_B(fac)
    fac['role'] = 'A'
    fac.loc[fac.cat_B.notna(), 'role'] = 'A+B'
    fac.loc[fac.cat_A == 'control', 'role'] = 'control'
    fac['role'] = fac['role'].astype('string')
    assert fac.cat_A.notna().all() and fac.cat_A4.notna().all()

    # ---------- 250m 격자 ----------
    fac['grid250_cd'] = pd.Series(pd.NA, index=fac.index, dtype='string')
    hx = fac.x_5179.notna() & fac.y_5179.notna()
    fac.loc[hx, 'grid250_cd'] = grid250_code(fac.loc[hx, 'x_5179'], fac.loc[hx, 'y_5179'])
    g250 = gpd.read_file(C.GRID250_SRC)
    # 검증 1: gpkg 전체 셀의 좌표 → 코드가 gid와 같은가
    cen = g250.geometry.representative_point()
    calc = grid250_code(cen.x, cen.y)
    n_bad = int((calc != g250.gid.values).sum())
    # 검증 2: 시설 표본 5,000점 공간결합 gid와 계산 코드 비교
    smp = fac.loc[hx].sample(min(5000, int(hx.sum())), random_state=1)
    sp = gpd.GeoDataFrame(smp[['grid250_cd']], geometry=gpd.points_from_xy(smp.x_5179, smp.y_5179), crs=C.CRS)
    sj = gpd.sjoin(sp, g250[['gid', 'geometry']], how='left', predicate='intersects')
    sj = sj[~sj.index.duplicated()]
    both = sj.gid.notna()
    n_smp_bad = int((sj.loc[both, 'gid'] != sj.loc[both, 'grid250_cd']).sum())
    in_src = fac.grid250_cd.isin(set(g250.gid))
    P(f'\n## 3. 250m 격자 코드\n- 부호화 규칙: `다사` + X(km, 2자리) + {{aa,ab,ba,bb}}(250m 순번) + Y(km, 2자리) + {{aa,ab,ba,bb}}; 원점 (900000, 1900000), 250m 간격 — `{C.GRID250_SRC.name}` 10,125셀 전체에서 대표점→코드가 gid와 불일치 {n_bad}건')
    P(f'- 시설 표본 {len(sp):,}점 공간결합 gid vs 계산 코드 불일치 {n_smp_bad}건 (gpkg 셀 밖 표본 {int((~both).sum())}건)')
    P(f'- 좌표 있는 시설 {int(hx.sum()):,} 중 계산 코드가 gpkg 서울 셀(10,125)에 없는 행 {int((hx & ~in_src).sum()):,} (서울 경계 밖·경계 근접 점; 코드는 유지)')

    # ---------- 저장 ----------
    OUT_PQ.parent.mkdir(parents=True, exist_ok=True)
    fac.to_parquet(OUT_PQ, index=False)
    import json
    C.UNITS_SOURCE_JSON.write_text(json.dumps(dict(source=str(C.FACILITY_PARQUET.relative_to(C.BASE)).replace('\\', '/'),
                                                   source_sha256=sha256(C.FACILITY_PARQUET), units_sha256=sha256(OUT_PQ), selection_rule_sha256=sha256(C.FACILITY_SELECTION_JSON), analysis_scope=C.ANALYSIS_SCOPE),
                                              ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    P(f'\n## 4. 출력\n- `{OUT_PQ.relative_to(C.ROOT)}` {len(fac):,}행 × {fac.shape[1]}열 (2026-09-25부터 csv 사본은 만들지 않음)')
    P('- 추가 열: dong424, dong424_name, ku, ku_name, lz116, ld2020, ld2025, dong424_method, cat_A, cat_A4, cat_B, tau_B_min, role, grid250_cd')

    # ---------- 검증 ----------
    P('\n## 5. 검증')
    ok = fac['분석가능'] == True
    rows = []
    for y, d in fac.groupby('year'):
        o = d[ok.loc[d.index]]
        sgis_ku = o.adm_dong_cd.astype('string').str[:5]
        both = o.ku.notna() & sgis_ku.notna() & (sgis_ku.str.len() == 5)
        mism = (sgis_ku[both].astype(int) != o.ku[both].astype(int))
        rows.append(dict(year=y, rows=len(d), 분석가능=len(o), dong424_assigned=int(o.dong424.notna().sum()),
                         assigned_share=round(o.dong424.notna().mean(), 5), ku_mismatch=int(mism.sum()), ku_mismatch_share=round(mism.mean(), 5),
                         nearest_used=int((o.dong424_method.str.startswith('nearest')).sum())))
    t = pd.DataFrame(rows)
    P('### 5.1 연도별 배정률·구 불일치(분석가능 행)\n' + t.to_markdown(index=False))
    P('\n- 구 불일치 = SGIS 2025_2Q adm_dong_cd 앞 5자리(구) ≠ 동424 폴리곤의 Ku. 경계 차이(2023-07 동424 vs 2025_2Q)와 좌표 정밀도에 따른 소수.')

    ct = pd.crosstab(fac.loc[ok, 'cat_A'], fac.loc[ok, 'year'], margins=True)
    P('\n### 5.2 연도별 cat_A(분석가능)\n' + ct.to_markdown())
    cb = pd.crosstab(fac.loc[ok & fac.cat_B.notna(), 'cat_B'], fac.loc[ok & fac.cat_B.notna(), 'year'], margins=True)
    P('\n### 5.3 연도별 cat_B(분석가능)\n' + cb.to_markdown())
    cbd = fac.loc[ok & fac.cat_B.notna()].groupby(['cat_B', '시설', 'tau_B_min', 'year']).size().unstack('year')
    P('\n### 5.4 cat_B 시설별·τ\n' + cbd.to_markdown())
    rl = pd.crosstab(fac.loc[ok, 'role'], fac.loc[ok, 'year'], margins=True)
    P('\n### 5.5 역할(A / A+B / control)\n' + rl.to_markdown())
    # 학교 세부·체육 세부 확인
    sch = fac.loc[ok & (fac['시설'] == '학교')].groupby(['year', fac['시설_세부'].str[:4]]).size().unstack(0)
    P('\n### 5.6 학교 `시설_세부` 앞 4자(초등학교만 cat_B)\n' + sch.to_markdown())
    P('\n### 5.7 체육시설업 제외\n- facility-v1.4에서 두 연도 전체 제외. 공공체육 대체 없음. 선택규칙 JSON 및 원천 증거 보존.')

    # 격자 g (100m) 통계 — MAI 용 |C_g|
    A = fac.loc[ok & (fac.cat_A != 'control') & fac.grid100_cd.notna()]
    P('\n### 5.8 시설 격자(100m, 시설 ≥1, 분석가능·A 27종)')
    gc = A.groupby('year').grid100_cd.nunique()
    P('- 연도별 시설 격자 수: ' + ', '.join(f'{y}: {n:,}' for y, n in gc.items()))
    gcc = A.groupby(['cat_A', 'year']).grid100_cd.nunique().unstack(1)
    P('- 카테고리별 시설 격자 수:\n' + gcc.to_markdown())
    hist = A.groupby(['year', 'grid100_cd']).cat_A.nunique().rename('Cg').reset_index()
    h = pd.crosstab(hist.Cg, hist.year); h.loc['합계'] = h.sum()
    P('\n### 5.9 격자별 동시입지 카테고리 수 |C_g| 분포 (1..7, 분석가능·A 27종, 100m)\n' + h.to_markdown())
    mean_cg = hist.groupby('year').Cg.mean().round(3).to_dict()
    P(f'- |C_g| 평균: {mean_cg}')
    A250 = A[A.grid250_cd.notna()]
    h250 = A250.groupby(['year', 'grid250_cd']).cat_A.nunique().rename('Cg').reset_index()
    h2 = pd.crosstab(h250.Cg, h250.year); h2.loc['합계'] = h2.sum()
    P('\n### 5.10 (참고) 250m 격자 |C_g| 분포\n' + h2.to_markdown())
    ctrl = fac.loc[ok & (fac.cat_A == 'control')].groupby(['시설', 'year']).size().unstack(1)
    P('\n### 5.11 통제변수 5종 연도별\n' + ctrl.to_markdown())

    rows = append_manifest([OUT_PQ], 'a02_facility_boundary.py')
    P('\n## 6. 해시 (manifest_sha256.csv)\n' + pd.DataFrame(rows).to_markdown(index=False))
    P(f'\n소요 {(dt.datetime.now() - t0).total_seconds():.0f}초')
    REC_MD.write_text('\n'.join(log) + '\n', encoding='utf-8', newline='\n')
    print('기록:', REC_MD)

if __name__ == '__main__':
    main()
