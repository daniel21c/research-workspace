# -*- coding: utf-8 -*-
"""접근성분석 패키지 무결성·신뢰성 검증 + 전체 SHA-256 목록.

검증 묶음 (결과: 문서/검증보고서.md, 데이터/검증결과.json, 데이터/manifest_sha256.csv)
  1. 입력 무결성  — 시설 원본이 배포목록 facility-v1.3 해시와 같은가, 경계 사본이 코어엔진 정본과 같은가,
                    격자·보행망·소요시간표가 2026-09-24 확정 해시와 같은가(소요시간표는 a05 결합 해시 규칙, 옛 경로 이름으로 재계산)
                    시설–경계 연결표(a02 산출)가 원본과 행 수·분석가능 수가 같고 분석가능 행이 모두 동에 배정됐는가
  2. 계산 정확성  — 단위시험 전체, run_meta의 기록된 불변조건(빈 기록/과거 지문 부재는 WARN), 2SFCA 서울 전체 독립 구현(pandas) 대조,
                    같은 입력으로 본 분석을 다시 돌렸을 때 결과 파일 해시가 같은가(결정성)
  3. 판 변경 검증 — access-engine-v2 → v3 에서 도달시간·Coverage·MAI 가 모든 행에서 그대로인가, 2SFCA 는 공급 중복 제거로
                    공급이 줄어든 항목에서만 바뀌었는가 (이전 판 결과가 있을 때만: PREV_OUT)
  4. 신뢰성       — 민감도 설정(10분·3.6 km/h·250m·일상소매 제외·네트워크 고정)에서 동 순위가 얼마나 유지되는가(Spearman),
                    연구3 핵심변수 Δ(LD−LZ)와 2SFCA 공공시설의 순위 안정성
  5. 패키지 해시  — 코드·문서·데이터 모든 파일의 SHA-256 (manifest_sha256.csv, a99 형식)
실행: python a10_verify.py [--skip-rerun]
"""
import argparse, datetime as dt, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a00_config as C   # noqa: E402
import a99_manifest as M  # noqa: E402
import a06c_delta as D   # noqa: E402
import a11_provenance as P

DEPLOY = C.BASE / '데이터_배포목록.md'
PREV_OUT = Path(os.environ.get('ACCESS_PREV_OUT', C.ROOT / '데이터' / '_이전판_결과'))   # 판 변경 검증용 이전 판 결과 폴더(없으면 3번 생략; 판을 바꿀 때 기존 결과/를 여기 복사해 두고 실행)
# 2026-09-24 확정 해시(배포목록 pop-grid·grid-master·network-walk·ttm-walk 행; ttm 은 a05 결합 해시, 옛 경로 01_data/ 기준)
FIXED = {
    'grid/grid100_master.parquet': 'f96efa65a36827f2d2cf892e01d9177daacc96665b1383f6a3890fedb1d38312',
    'grid/grid250_master.parquet': '60ddd455fe27e20ab8bf91830f10a15d5fcaea40206f9f35581faaf89e256aa0',
    'network/walk_2020_graph.npz': '1f5f7c8600d3cf07d6f677955f84b67e42ebc831b27a10353964750c0959c62b',
    'network/walk_2025_graph.npz': '008f98052c285080cb7061c463f0267e73e1faeaef0c61126acecd4f374d48c5',
}
FIXED_TTM = {'ttm100_2020': 'e7f81258424a490697ab9df1268b0f4a9db037962fb10194572a9d6dd44ca2a4',
             'ttm100_2025': '4920b8de8e6786f4b8f6385e93d929349ddd4d79ddd8d83a00feea434861172e',
             'ttm250_2020': '2e2ef3cf4c00f9f6491edb5fd7dbf1ff7aca08ef0b179cf4a113095c7c9ded50',
             'ttm250_2025': '66860eb29ee99076370ff90834feb564076c50fc33d1521e74798a32234e0fb5',
             'ttm100_2025_for2020': '0f14f78b14eb62eb7fa8c1f789a1bd8e7e415d5f16bf326e1e745a593126d498'}
SENS = [('sens_T600', 100), ('sens_speed36', 100), ('sens_grid250', 250), ('sens_retail_without', 100), ('sens_union', 100), ('sens_snap', 100)]
RES = {}


def rec(group, name, ok, detail):
    RES.setdefault(group, []).append({'항목': name, '결과': 'PASS' if ok else ('WARN' if ok is None else 'FAIL'), '내용': detail})
    print(('PASS' if ok else ('WARN' if ok is None else 'FAIL')), group, name, '—', detail)


def legacy_combined(dirpath: Path):
    """a05_ttm.combined_hash 규칙(상대경로 문자열 + 파일 해시를 이어 SHA-256)을 옛 경로 이름(01_data/ttm/...)으로 재계산."""
    files = sorted(dirpath.glob('ku=*/chunk_*.parquet'), key=lambda f: str(f.relative_to(C.DATA)).replace('\\', '/'))
    h = hashlib.sha256()
    for f in files:
        h.update(('01_data/' + str(f.relative_to(C.DATA)).replace('\\', '/')).encode()); h.update(M.sha256(f).encode())
    return h.hexdigest(), len(files)


# ---------------------------------------------------------------- 1. 입력 무결성
def check_inputs():
    g = '1. 입력 무결성'
    txt = DEPLOY.read_text(encoding='utf-8') if DEPLOY.exists() else ''
    m = re.search(r'\| facility-v1\.3 \|.*?\| ([0-9a-f]{64}) \|', txt)
    h = M.sha256(C.FACILITY_PARQUET)
    rec(g, '시설 원본 = 배포목록 facility-v1.3', bool(m) and m.group(1) == h, f'{C.FACILITY_PARQUET.name} {h[:16]}… (배포목록 {m.group(1)[:16] + "…" if m else "행 없음"})')
    src = pd.read_parquet(C.FACILITY_PARQUET, columns=['year', '분석가능'])
    u = pd.read_parquet(C.DATA / 'facility' / 'facility_2020_2025_units.parquet', columns=['year', '분석가능', 'dong424', 'cat_A'])
    rec(g, '시설–경계 연결표 행 수·분석가능 수 = 원본', len(src) == len(u) and int(src['분석가능'].sum()) == int(u['분석가능'].sum()),
        f'원본 {len(src):,}행·분석가능 {int(src["분석가능"].sum()):,} / 연결표 {len(u):,}행·{int(u["분석가능"].sum()):,}')
    src_h = C.units_source_sha256()
    rec(g, '시설–경계 연결표가 현재 시설 원본으로 만들어짐(a02 기록 해시)', src_h == h,
        f'a02 기록 {src_h[:16] + "…" if src_h else "없음(→ run_engine.bat facility)"} / 현재 원본 {h[:16]}…')
    ok = u['분석가능'].astype(bool)
    rec(g, '분석가능 행의 동 424 배정률 100%', bool(u.loc[ok, 'dong424'].notna().all()), f'미배정 {int(u.loc[ok, "dong424"].isna().sum())}행')
    rec(g, '모든 시설에 카테고리(8개 또는 통제)', bool(u['cat_A'].notna().all()), f'결측 {int(u["cat_A"].isna().sum())}')
    for f in ['seoul_boundaries_all.gpkg', 'dong_to_official_livingzone_mapping_424.csv', 'dong_to_leiden_2020_mapping_424.csv', 'dong_to_leiden_2025_mapping_424.csv']:
        a, b = C.DATA / 'boundary' / f, C.CORE / 'data' / f
        rec(g, f'경계 사본 = 코어엔진 정본 ({f})', b.exists() and M.sha256(a) == M.sha256(b), f'{M.sha256(a)[:16]}…')
    for rel, hh in FIXED.items():
        x = M.sha256(C.DATA / rel)
        rec(g, f'확정 입력 해시 ({rel})', x == hh, f'{x[:16]}…')
    for d, hh in FIXED_TTM.items():
        x, n = legacy_combined(C.DATA / 'ttm' / d)
        rec(g, f'소요시간표 결합 해시 ({d}, {n}청크)', x == hh, f'{x[:16]}… (확정 {hh[:16]}…)')


# ---------------------------------------------------------------- 2. 계산 정확성
def run_tests():
    g = '2. 계산 정확성'
    r = subprocess.run([sys.executable, str(HERE / 'tests' / 'test_engine.py')], capture_output=True, text=True, encoding='utf-8',
                       env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    last = [l for l in r.stdout.splitlines() if '통과' in l]
    rec(g, '단위시험 (손계산 예제·독립 구현 대조·2SFCA)', r.returncode == 0, last[-1] if last else r.stdout[-300:])
    r2 = subprocess.run([sys.executable, str(HERE / 'tests' / 'test_geometry.py')], capture_output=True, text=True, encoding='utf-8',
                        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    rec(g, '기하 시험 (컴팩트성·인접·250m 코드)', r2.returncode == 0, (r2.stdout.strip().splitlines() or ['(출력 없음)'])[-1])

    r3 = subprocess.run([sys.executable, '-B', str(HERE/'tests/test_release.py')], capture_output=True, text=True, encoding='utf-8')
    rec(g, '배포 회귀시험 (빈 검사·stale 지문·xb·공통범주)', r3.returncode == 0, (r3.stdout+r3.stderr)[-500:])


def check_run_meta():
    g = '2. 계산 정확성'
    paths=sorted(C.OUT.glob('*/run_meta_*.json'))
    counts={'fully_recorded':0,'historical_or_incomplete':0,'failed':0}
    for p in paths:
        m=json.loads(p.read_text(encoding='utf-8'))
        failures,unverified=P.metadata_issues(m,p)
        counts['failed' if failures else ('historical_or_incomplete' if unverified else 'fully_recorded')]+=1
        rec(g,f'실행 메타 {p.parent.name}/{p.name}',False if failures else (None if unverified else True),
            '; '.join(failures+unverified) or '기록된 필수 불변조건·출력·현재 코드/입력 지문 일치 (독립 재계산 아님)')
    rec(g,'실행 메타 검사 범위',None if counts['historical_or_incomplete'] else counts['failed']==0,str(counts))
    u = pd.read_csv(C.OUT / 'main' / 'unit_access_2025_100.csv', usecols=['unit_level', 'unit_id'])
    cnt = u.groupby('unit_level').unit_id.nunique().to_dict()
    rec(g, '단위 수 (동 424·공식 116·Leiden 116·구 25)', cnt.get('dong424') == 424 and cnt.get('lz116') == 116 and cnt.get('ld') == 116 and cnt.get('ku') == 25, str(cnt))


def independent_sfca(year=2025, items=('공공도서관', '주민센터', '보건소·보건지소', '문화'), bounds=('none', 'lz116')):
    """엔진 코드를 쓰지 않는 2SFCA 구현(pandas merge·groupby)으로 서울 전체 격자 값을 다시 계산해 grid_sfca 와 대조."""
    g = '2. 계산 정확성'
    py = C.YEARS[year]['pop_year']
    gm = pd.read_parquet(C.DATA / 'grid' / 'grid100_master.parquet', columns=['grid_cd', f'pop_{py}', 'lz116'])
    gm = gm.rename(columns={f'pop_{py}': 'pop'})
    f = pd.read_parquet(C.DATA / 'facility' / 'facility_2020_2025_units.parquet',
                        columns=['year', '시설', '시설_세부', '분석가능', 'cat_A', 'role', 'grid100_cd', 'name', 'x_5179', 'y_5179'])
    f = f[(f.year == year) & f['분석가능'].astype(bool) & (f.role.astype(str) != 'control') & f.cat_A.isin(list(C.CAT_A)) & f.grid100_cd.isin(gm.grid_cd)]
    # 공급 중복 규칙(지표정의_확정.md 3.4)을 엔진과 따로 적용: 시설 항목 = (시설, 이름, 좌표) 한 곳,
    # 카테고리 항목 = 문화기반시설 중 공공도서관 행 제외 후 (카테고리, 이름, 좌표) 한 곳
    key = ['name', 'x_5179', 'y_5179']
    f_fac = f.loc[~f.duplicated(['시설'] + key)]
    f_cat = f_fac[~((f_fac['시설'] == '문화기반시설') & (f_fac['시설_세부'] == '공공도서관'))]
    f_cat = f_cat.loc[~f_cat.duplicated(['cat_A'] + key)]
    files = sorted((C.DATA / 'ttm' / f'ttm100_{year}').glob('ku=*/chunk_*.parquet'))
    tt = pd.concat([pq.read_table(p, columns=['o_grid', 'd_grid', 't_sec']).to_pandas() for p in files], ignore_index=True)
    tt = tt[tt.t_sec <= C.T_SEC]
    tt = tt.merge(gm.rename(columns={'grid_cd': 'o_grid', 'pop': 'p_o', 'lz116': 'lz_o'}), on='o_grid').merge(
        gm[['grid_cd', 'lz116']].rename(columns={'grid_cd': 'd_grid', 'lz116': 'lz_d'}), on='d_grid')
    tt = tt[tt.p_o > 0]
    eng = pd.read_parquet(C.OUT / 'main' / f'grid_sfca_{year}_100.parquet')
    eng = eng[eng.item.isin(items) & eng.b.isin(bounds)].astype({'b': str, 'item': str})
    worst = 0.0; n = 0
    for b in bounds:
        x = tt if b == 'none' else tt[tt.lz_o == tt.lz_d]
        D = x.groupby('d_grid').p_o.sum().rename('D')
        for it in items:
            src, col = (f_cat, 'cat_A') if it in C.CAT_A else (f_fac, '시설')
            S = src[src[col] == it].groupby('grid100_cd').size().rename('S')
            R = (S / D.reindex(S.index)).dropna().rename('R')
            A = x.merge(R, left_on='d_grid', right_index=True).groupby('o_grid').R.sum() * 1e4
            e = eng[(eng.b == b) & (eng.item == it)].set_index('grid_cd').A_per10k
            cmp = pd.concat([e.rename('eng'), A.rename('ind')], axis=1).fillna(0.0)
            err = (cmp.eng - cmp.ind).abs() / np.maximum(cmp.ind.abs(), 1e-3)
            worst = max(worst, float(err.max())); n += len(cmp)
    rec(g, f'2SFCA 서울 전체 독립 구현 대조 ({year}, {"·".join(items)} × b {"·".join(bounds)})', worst < 1e-5,
        f'격자 {n:,}개 비교, 최대 상대오차 {worst:.2e} (엔진 격자 값은 float32 저장)')


def rerun_determinism():
    g = '2. 계산 정확성'
    tmp = Path(tempfile.mkdtemp(prefix='a10_rerun_'))
    try:
        r = subprocess.run([sys.executable, str(HERE / 'a06_engine.py'), '--year', '2025', '--grid', '100', '--tag', 'main', '--out-root', str(tmp)],
                           capture_output=True, text=True, encoding='utf-8', env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        same = []
        for fn in ['unit_access_2025_100.csv', 'sfca_unit_2025_100.csv']:
            same.append((fn, M.sha256(tmp / 'main' / fn) == M.sha256(C.OUT / 'main' / fn)))
        a = pd.read_parquet(tmp / 'main' / 'grid_access_2025_100.parquet'); b = pd.read_parquet(C.OUT / 'main' / 'grid_access_2025_100.parquet')
        same.append(('grid_access_2025_100.parquet(내용)', a.equals(b)))
        rec(g, '재실행 결정성 (본 분석 2025 다시 계산)', r.returncode == 0 and all(s for _, s in same), ', '.join(f'{fn} {"같음" if s else "다름"}' for fn, s in same))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 3. 판 변경 검증
def check_version_change():
    """access-engine-v2 → v3: 바뀐 것은 2SFCA 공급 중복 제거뿐이므로 도달시간·Coverage·MAI 는 모든 행이 같아야 하고,
    2SFCA 는 중복 제거로 공급이 줄어든 항목에서만 바뀌어야 한다. 이전 판 결과(PREV_OUT)가 있을 때만."""
    g = '3. 판 변경 (access-engine-v2 → v3)'
    if not PREV_OUT.exists():
        rec(g, '이전 판 결과', None, '이전 판 결과 없음 → 생략(패키지를 받은 쪽에서는 정상)'); return
    rows = []; bad_u = 0; bad_s_items = set(); n_s = 0
    for y in (2020, 2025):
        o = pd.read_csv(PREV_OUT / 'main' / f'unit_access_{y}_100.csv'); n = pd.read_csv(C.OUT / 'main' / f'unit_access_{y}_100.csv')
        k = ['unit_level', 'unit_id', 'b', 'cat']
        mm = o.merge(n, on=k, suffixes=('_o', '_n'), how='outer', indicator=True)
        diff = (mm['_merge'] != 'both')
        for c in ['pop_total', 'pop_reach', 'COV', 'MAI', 'PWATT_sec', 'n_cat_mai']:
            diff |= ~(((mm[f'{c}_o'] - mm[f'{c}_n']).abs() <= 1e-9) | (mm[f'{c}_o'].isna() & mm[f'{c}_n'].isna()))
        bad_u += int(diff.sum())
        so = pd.read_csv(PREV_OUT / 'main' / f'sfca_unit_{y}_100.csv'); sn = pd.read_csv(C.OUT / 'main' / f'sfca_unit_{y}_100.csv')
        ks = ['unit_level', 'unit_id', 'b', 'item_type', 'item']
        ms = so.merge(sn, on=ks, suffixes=('_o', '_n'))
        ch = (ms.SFCA_per10k_o - ms.SFCA_per10k_n).abs() > 1e-9
        sup_same = (ms.supply_in_unit_o == ms.supply_in_unit_n)
        n_s += len(ms)
        for (t, it), d in ms.groupby(['item_type', 'item']):
            c = int(((d.SFCA_per10k_o - d.SFCA_per10k_n).abs() > 1e-9).sum())
            seo = d[(d.unit_level == 'seoul') & (d.b == 'none')]
            rows.append({'year': y, 'item_type': t, 'item': it, '서울 공급 v2': float(seo.supply_in_unit_o.iloc[0]), '서울 공급 v3': float(seo.supply_in_unit_n.iloc[0]),
                         '서울 2SFCA v2': float(seo.SFCA_per10k_o.iloc[0]), '서울 2SFCA v3': float(seo.SFCA_per10k_n.iloc[0]), '바뀐 행': c})
        bad_s_items |= set(ms.loc[ch & sup_same.groupby([ms.item_type, ms.item]).transform('all'), 'item'])
    rec(g, '도달시간·Coverage·MAI 모든 행 불변(두 연도, 모든 단위·경계 조건·카테고리)', bad_u == 0, f'바뀐 행 {bad_u}')
    rec(g, '2SFCA 는 공급이 줄어든 항목에서만 변동', not bad_s_items, f'비교 {n_s:,}행; 공급 불변인데 값이 바뀐 항목 {sorted(bad_s_items) or "없음"}')
    t = pd.DataFrame(rows); RES['_판변경표'] = t[t['서울 공급 v2'] != t['서울 공급 v3']].to_dict('records')


# ---------------------------------------------------------------- 4. 신뢰성 (순위 안정성)
def spearman(a, b):
    x = pd.concat([a, b], axis=1).dropna()
    return float(x.iloc[:, 0].rank().corr(x.iloc[:, 1].rank())) if len(x) > 2 else np.nan


def check_reliability():
    g = '4. 신뢰성 (민감도 대비 동 순위 안정성)'
    rows = []
    base = {y: pd.read_csv(C.OUT / 'main' / f'unit_access_{y}_100.csv') for y in (2020, 2025)}
    def dong(u, b, col):
        d = u[(u.unit_level == 'dong424') & (u.cat == '종합') & (u.b == b)].set_index('unit_id')[col]; return d
    def delta(u, col):                      # 연구3 Δ: MAI 는 공통 카테고리 평균(a06c_delta)
        return D.dong_delta(u, col)
    for tag, grid in SENS + [('sens_net2025', 100)]:
        for y in ((2020,) if tag == 'sens_net2025' else (2020, 2025)):
            p = C.OUT / tag / f'unit_access_{y}_{grid}.csv'
            if not p.exists():
                continue
            s = pd.read_csv(p); m = base[y]
            rows.append({'tag': tag, 'year': y,
                         'COV 공식 LZ 동 순위 ρ': spearman(dong(m, 'lz116', 'COV'), dong(s, 'lz116', 'COV')),
                         'MAI 공식 LZ 동 순위 ρ': spearman(dong(m, 'lz116', 'MAI'), dong(s, 'lz116', 'MAI')),
                         'ΔCOV(LD−LZ) 동 ρ': spearman(delta(m, 'COV'), delta(s, 'COV')),
                         'ΔMAI(LD−LZ) 동 ρ': spearman(delta(m, 'MAI'), delta(s, 'MAI'))})
    t = pd.DataFrame(rows); RES['_신뢰성표'] = t.to_dict('records')

    def weakest(cols):
        """열들 가운데 ρ < 0.7 인 (tag, year, 열) 목록과 최솟값."""
        low = [f'{t.loc[i, "tag"]} {t.loc[i, "year"]} {c} {t.loc[i, c]:.3f}' for i in t.index for c in cols if t.loc[i, c] < 0.7]
        return t[cols].min().min(), low
    # 신뢰성은 계산 오류가 아니라 결과의 설정 의존성이다 → 기준(ρ ≥ 0.7) 미달은 FAIL 이 아니라 WARN 으로 표시하고 어디서인지 적는다
    lo, low = weakest([c for c in t.columns if 'ρ' in c and 'Δ' not in c])
    rec(g, '동 COV·MAI 순위(공식 생활권 경계) 민감도 간 Spearman', True if not low else None,
        f'최솟값 {lo:.3f}. ρ < 0.7: ' + ('; '.join(low) if low else '없음') + ' — 250 m 격자는 셀이 커져 동시입지 카테고리 수(MAI)가 달라지므로 MAI 수준·순위가 격자 크기에 의존한다')
    dl, lowd = weakest([c for c in t.columns if 'Δ' in c])
    rec(g, '연구3 핵심변수 Δ(LD−LZ) 동 순위 Spearman', True if not lowd else None,
        f'최솟값 {dl:.3f}. ρ < 0.7: ' + ('; '.join(lowd) if lowd else '없음') + ' — Δ는 대부분 동에서 0이고 크기가 작아 격자·임계 설정에 따라 순위가 흔들린다(연구3은 민감도 결과를 함께 보고)')
    srows = []
    ms = pd.read_csv(C.OUT / 'main' / 'sfca_unit_2025_100.csv')
    for tag, grid in SENS:
        p = C.OUT / tag / f'sfca_unit_2025_{grid}.csv'
        if not p.exists():
            continue
        s = pd.read_csv(p)
        for it in C.SFCA_PUBLIC:
            a = ms[(ms.unit_level == 'dong424') & (ms.b == 'none') & (ms.item == it)].set_index('unit_id').SFCA_per10k
            b = s[(s.unit_level == 'dong424') & (s.b == 'none') & (s.item == it)].set_index('unit_id').SFCA_per10k
            srows.append({'tag': tag, 'item': it, '동 2SFCA 순위 ρ (2025, 경계 없음)': spearman(a, b)})
    st = pd.DataFrame(srows); RES['_신뢰성표_2SFCA'] = st.to_dict('records')
    if len(st):
        mn = st['동 2SFCA 순위 ρ (2025, 경계 없음)'].min()
        rec(g, '2SFCA 공공시설 동 순위 Spearman 최솟값', True if mn >= 0.7 else None, f'{mn:.3f}')


# ---------------------------------------------------------------- 5. 패키지 해시 목록
SCRIPT_BY_PREFIX = [('데이터/입력/grid/', 'a01_grid_master.py'), ('데이터/입력/facility/', 'a02_facility_boundary.py'), ('데이터/입력/boundary/', 'a03_boundary_metrics.py'),
                    ('데이터/입력/network/', 'a04_network.py'), ('데이터/입력/ttm/ttm100_2025_for2020', 'a05c_ttm_supplement.py'), ('데이터/입력/ttm/', 'a05_ttm.py'),
                    ('데이터/입력/external/', '수기 전사(원고 인쇄값)'), ('데이터/결과/tables/T5', 'a07_study3_outputs.py'), ('데이터/결과/tables/F3', 'a07_study3_outputs.py'),
                    ('데이터/결과/figures/', 'a07_study3_outputs.py'), ('데이터/결과/tables/ku_', 'a08_ku_compare.py'), ('데이터/결과/tables/SFCA', 'a06b_summary.py'),
                    ('코드/', '코드'), ('문서/', '문서')]


def write_manifest():
    rows = []
    skip = {C.MANIFEST.resolve()}
    for p in sorted(C.ROOT.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or p.resolve() in skip or p.suffix in ('.tmp', '.pyc'):
            continue
        rel = str(p.relative_to(C.ROOT)).replace('\\', '/')
        scr = next((s for pre, s in SCRIPT_BY_PREFIX if rel.startswith(pre)), '')
        if rel.startswith('데이터/결과/temporal_common4/'): scr = 'a06d_temporal_sensitivity.py'
        if not scr and rel.startswith('데이터/결과/'):
            scr = 'a06b_summary.py' if (p.name.startswith('summary') or p.name.startswith('decomp')) else 'a06_engine.py'
        if rel in ('README.md', '데이터/검증결과.json'):
            scr = 'a10_verify.py' if rel.endswith('.json') else '문서'
        rows.append({'file': rel, 'sha256': M.sha256(p), 'bytes': str(p.stat().st_size),
                     'created': dt.datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'), 'script': scr,
                     'rows': str(M.count_rows(p)) if p.suffix in ('.csv', '.parquet') else ''})
    import csv
    with open(C.MANIFEST, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=M.COLS, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    return len(rows), sum(int(r['bytes']) for r in rows)


# ---------------------------------------------------------------- 보고서
def md_table(recs):
    if not recs:
        return ''
    df = pd.DataFrame(recs); cols = list(df.columns)
    out = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    for _, r in df.iterrows():
        out.append('| ' + ' | '.join((f'{v:.3f}' if isinstance(v, float) else str(v)) for v in r.values) + ' |')
    return '\n'.join(out)


def write_report(n_files, n_bytes, t0):
    groups = [k for k in RES if not k.startswith('_')]
    allrec = [r for k in groups for r in RES[k]]
    verdict = 'FAIL' if any(r['결과'] == 'FAIL' for r in allrec) else 'PASS'
    L = ['# 접근성분석 패키지 무결성·신뢰성 검증 보고서', '',
         f'- 생성: {dt.datetime.now():%Y-%m-%d %H:%M} · 코드 `코드/a10_verify.py` · 소요 {time.time() - t0:.0f}초 · 이 보고서의 숫자는 모두 코드가 파일에서 계산한 값이다.',
         f'- **종합 판정: {verdict}** — 실제 실행·기록한 검사에서 FAIL이 없으면 PASS이며 모든 산출물의 완전 검증을 뜻하지 않는다. 누락된 과거 지문·미실행 검사는 WARN으로 남는다. 4(신뢰성)는 결과가 설정에 얼마나 의존하는지를 보여 주는 항목이라 기준(ρ ≥ 0.7) 미달은 WARN(해석 주의)으로 적는다.', '']
    for k in groups:
        L += [f'## {k}', '', md_table(RES[k]), '']
        if k.startswith('3') and RES.get('_판변경표'):
            L += ['### 공급 중복 제거로 바뀐 2SFCA 항목 (서울 전체, 경계 없음; 공급 = 시설 수, 2SFCA = 인구 1만 명당)', '', md_table(RES['_판변경표']), '',
                  '- v3 중복 제거: 시설 항목은 (시설, 이름, 좌표)가 같은 행을 한 곳으로, 카테고리 항목은 문화기반시설의 공공도서관 행을 빼고 (카테고리, 이름, 좌표)가 같은 행을 한 곳으로 센다(`문서/지표정의_확정.md` 3.4).', '']
        if k.startswith('4'):
            L += ['### 민감도별 동 순위 상관 (본 분석 대비 Spearman ρ, 동 424)', '', md_table(RES.get('_신뢰성표', [])), '',
                  '### 2SFCA 공공시설 동 순위 상관 (2025, 경계 없음)', '', md_table(RES.get('_신뢰성표_2SFCA', [])), '',
                  '- 250m는 격자 크기 자체가 달라 MAI 수준이 약 +1.5 높으므로 순위 비교만 의미가 있다. 네트워크 고정은 2020 시설·인구에 2025 보행망을 쓴 것.', '']
    L += ['## 5. 패키지 해시', '', f'- `데이터/manifest_sha256.csv`: 코드·문서·데이터 {n_files:,}개 파일, {n_bytes / 1e6:,.1f} MB의 SHA-256. (이 목록 파일 자신은 빠짐)',
          '- 받은 쪽 확인: `python 코드/a10_verify.py --check-only` 는 계산 없이 목록과 파일 해시만 대조한다.', '']
    (C.REC / '검증보고서.md').write_text('\n'.join(L) + '\n', encoding='utf-8', newline='\n')
    out = {k: v for k, v in RES.items()}; out['판정'] = verdict; out['생성'] = f'{dt.datetime.now():%Y-%m-%d %H:%M:%S}'
    (C.ROOT / '데이터' / '검증결과.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding='utf-8', newline='\n')
    return verdict


def manifest_errors(root, manifest):
    import csv
    root=Path(root).resolve();bad=[];seen=set();n=0
    with open(manifest,encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            rel=r['file'];p=(root/rel).resolve();n+=1
            if rel in seen or not p.is_relative_to(root):bad.append('중복/외부경로: '+rel);continue
            seen.add(rel)
            if not p.is_file() or p.stat().st_size!=int(r['bytes']) or M.sha256(p)!=r['sha256']:bad.append(rel)
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=Path(manifest).resolve()
            and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.tmp')}
    bad += ['미등록: '+r for r in sorted(actual-seen)]
    return n,bad


def check_only():
    n,bad=manifest_errors(C.ROOT,C.MANIFEST)
    print(f'해시 대조: {n}개 중 불일치·없음·미등록 {len(bad)}개'+(': '+', '.join(bad[:10]) if bad else ''))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--skip-rerun', action='store_true', help='재실행 결정성 점검 생략')
    ap.add_argument('--check-only', action='store_true', help='manifest 와 파일 해시만 대조(계산 없음)')
    ap.add_argument('--metadata-only', action='store_true', help='결과 메타·출력 해시·기록된 코드/입력 지문만 확인(재계산·쓰기 없음)')
    a = ap.parse_args()
    if a.check_only:
        sys.exit(check_only())
    if a.metadata_only:
        check_run_meta()
        sys.exit(1 if any(r['결과']=='FAIL' for rows in RES.values() for r in rows) else 0)
    t0 = time.time()
    check_inputs(); run_tests(); check_run_meta(); independent_sfca()
    if not a.skip_rerun:
        rerun_determinism()
    check_version_change(); check_reliability()
    rec('4. 신뢰성 (민감도 대비 동 순위 안정성)', 'xb 검사 범위', None, 'xb는 경계 교차 산출물이며 일반 민감도 rho 비교와 분리. 재현 및 공통4카테고리는 배포 검증기록·temporal_common4 참조')
    # 보고서·json 을 먼저 쓰고(해시 목록에 들어가도록) 목록을 만든 뒤, 파일 수를 넣어 보고서를 다시 쓴다
    write_report(0, 0, t0)
    n, b = write_manifest()
    verdict = write_report(n, b, t0)
    n, b = write_manifest()
    print('판정', verdict, f'manifest {n}개')
    sys.exit(0 if verdict == 'PASS' else 1)


if __name__ == '__main__':
    main()
