# -*- coding: utf-8 -*-
"""a06_engine 단위시험 — 손계산 예제 재현 + 독립 구현 대조.

실행:  python 코드/tests/test_engine.py      (pytest 가 있으면 python -m pytest 코드/tests 도 가능)
근거: 03_불일치_접근성_AG/연구설계.md 7.1 (예제 1·3), 문서/지표정의_확정.md 3절.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import a06_engine as E  # noqa: E402
import a00_config as C  # noqa: E402

TOL = 1e-9


def _close(a, b, tol=1e-3):
    return abs(float(a) - float(b)) <= tol


# ------------------------------------------------------------------ 예제 1 (연구3 7.1)
# 격자 번호: 0=o1(인구100) 1=o2(인구50) 2=g1{A,B} 3=g2{A} 4=g3{A,B,C}
# LZ: o1,o2,g1,g2 = X(1), g3 = Y(2) / LD: 모두 X(1). 동 i 하나.
def _example1(extra_A_in_g1=False):
    cells = [2, 2, 3, 4, 4, 4]
    bits = [0, 1, 0, 0, 1, 2]
    if extra_A_in_g1:
        cells += [2]; bits += [0]                      # g1 에 A 시설 하나 더
    Cm = E.build_cmask(np.array(cells), np.array(bits), 5)
    o = np.array([0, 0, 1, 1, 1]); d = np.array([2, 4, 2, 3, 4])
    t = np.array([10, 12, 20, 5, 14]) * 60.0
    units = {'none': None, 'lz116': np.array([1, 1, 1, 1, 2]), 'ld': np.array([1, 1, 1, 1, 1])}
    res = E.origin_access(o, d, t, Cm, units, K=3, T=900, union=True)
    pop = np.array([100, 50, 0, 0, 0], float)
    rows = []
    for b, v in res.items():
        for i, gi in enumerate(v['o']):
            for c, cat in enumerate(['A', 'B', 'C']):
                rows.append(dict(gi=gi, b=b, cat=cat, pop=pop[gi], r=v['r'][i, c], m=v['m'][i, c], t=v['t'][i, c], U=v['U'][i], dong424=1))
    df = pd.DataFrame(rows)
    old = E.BOUNDS
    E.BOUNDS = ['none', 'lz116', 'ld']
    try:
        agg = E.aggregate(df, 'dong424', ['A', 'B', 'C'], 900, True)
    finally:
        E.BOUNDS = old
    return res, agg, Cm


def test_example1_lz():
    _, agg, _ = _example1()
    a = agg[agg.b == 'lz116'].set_index('cat')
    assert _close(a.loc['A', 'COV'], 1.0) and _close(a.loc['B', 'COV'], 0.667) and _close(a.loc['C', 'COV'], 0.0)
    assert _close(a.loc['종합', 'COV'], 0.556)
    assert _close(a.loc['A', 'MAI'], 1.667) and _close(a.loc['B', 'MAI'], 2.0)
    assert np.isnan(a.loc['C', 'MAI'])                       # 정의 안 됨
    assert _close(a.loc['종합', 'MAI'], 1.833)                 # 값 있는 카테고리 단순평균
    assert not _close(a.loc['B', 'MAI'], 200 / 150)           # 미도달 격자가 0 으로 들어가면 1.333 (틀린 코드)
    assert a.loc['종합', 'n_cat_mai'] == 2


def test_example1_ld():
    _, agg, _ = _example1()
    a = agg[agg.b == 'ld'].set_index('cat')
    for c in ['A', 'B', 'C', '종합']:
        assert _close(a.loc[c, 'COV'], 1.0)
        assert _close(a.loc[c, 'MAI'], 3.0)


def test_example1_union():
    res, _, _ = _example1()
    assert list(res['lz116']['U']) == [2, 1]                   # o1 {A,B}, o2 {A}
    assert list(res['ld']['U']) == [3, 3]


def test_duplicate_facility_does_not_raise_Cg():
    _, agg1, Cm1 = _example1(False)
    _, agg2, Cm2 = _example1(True)
    assert (Cm1 == Cm2).all() and E.popcount(Cm1)[2] == 2
    pd.testing.assert_frame_equal(agg1, agg2)


# ------------------------------------------------------------------ 예제 3 (상위 집계 = 분자합/분모합)
def test_example3_upper_aggregation():
    # 동 a: 인구 100 중 50 도달, 동 b: 인구 10 중 9 도달 → 생활권 COV = 59/110 = 0.536 (평균 0.7 이면 틀림)
    rows = []
    for gi, dong, p, r in [(0, 1, 50, 1), (1, 1, 50, 0), (2, 2, 9, 1), (3, 2, 1, 0)]:
        rows.append(dict(gi=gi, b='none', cat='A', pop=p, r=r, m=1.0 if r else np.nan, t=60.0 if r else np.nan, dong424=dong, lz116=9))
    df = pd.DataFrame(rows)
    a = E.aggregate(df, 'lz116', ['A'], 900, False)
    v = a[(a.cat == 'A')]['COV'].iloc[0]
    assert _close(v, 59 / 110, 1e-12) and _close(v, 0.536)
    assert not _close(v, 0.7)


# ------------------------------------------------------------------ PWATT 손계산
def test_pwatt_conditional():
    # o1 인구100 5분, o2 인구50 10분, o3 인구30 20분(>15분 미도달) → PWATT = (100·300+50·600)/150 = 400초, COV = 150/180
    Cm = E.build_cmask(np.array([3]), np.array([0]), 4)
    o = np.array([0, 1, 2]); d = np.array([3, 3, 3]); t = np.array([300.0, 600.0, 1200.0])
    res = E.origin_access(o, d, t, Cm, {'none': None}, K=1, T=900)
    v = res['none']
    assert list(v['r'][:, 0]) == [1, 1, 0] and v['t'][2, 0] == 1200.0   # t_min 은 30분 안이면 남김
    df = pd.DataFrame(dict(gi=v['o'], b='none', cat='A', pop=[100, 50, 30], r=v['r'][:, 0], m=v['m'][:, 0], t=v['t'][:, 0], seoul=0))
    a = E.aggregate(df, 'seoul', ['A'], 900, False)
    a = a[a.cat == 'A'].iloc[0]
    assert _close(a['PWATT_sec'], 400.0, 1e-12) and _close(a['COV'], 150 / 180, 1e-12)


def test_speed_conversion():
    # 4.0 km/h 표에서 850초 → 3.6 km/h 에서 944초 > 900 → 미도달
    Cm = E.build_cmask(np.array([1]), np.array([0]), 2)
    t = np.array([850.0]) * C.WALK_KMH / 3.6
    v = E.origin_access(np.array([0]), np.array([1]), t, Cm, {'none': None}, K=1, T=900)['none']
    assert v['r'][0, 0] == 0 and _close(v['t'][0, 0], 944.444, 1e-3)


def test_natstd_or_within_category():
    # 교육 = 유치원(10분) OR 초등(15분). o0: 유치원 12분·초등 14분 → 초등으로 충족. o1: 유치원 12분만 → 미충족
    groups = [('교육', '유치원', 600.0, np.array([2])), ('교육', '학교', 900.0, np.array([3]))]
    o = np.array([0, 0, 1]); d = np.array([2, 3, 2]); t = np.array([720.0, 840.0, 720.0])
    uo, rg, rc = E.natstd_access(o, d, t, groups, 4)
    assert rg.tolist() == [[0, 1], [0, 0]] and rc[:, 0].tolist() == [1, 0]


# ------------------------------------------------------------------ 2SFCA 손계산 (지표정의_확정.md 3.4)
# 격자: 0=o1(인구100, 단위X) 1=o2(인구300, 단위Y) 2=g1(시설1, X) 3=g2(시설2, Y) 4=g3(시설1, X)
# 15분 안 쌍: o1→g1, o2→g1, o2→g2, o2→g3
def _sfca_example():
    pop = np.array([100, 300, 0, 0, 0], float)
    S = np.array([[0], [0], [1], [2], [1]], float)
    o = np.array([0, 1, 1, 1]); d = np.array([2, 2, 3, 4])
    units = {'none': None, 'lz116': np.array([1, 2, 1, 2, 1])}
    return pop, S, E.sfca_access(o, d, pop, S, units)


def test_sfca_hand_example():
    pop, S, r = _sfca_example()
    a = r['none']['A'][:, 0]
    # 경계 없음: D(g1)=400, D(g2)=300, D(g3)=300 → A(o1)=1/400, A(o2)=1/400+2/300+1/300
    assert _close(a[0], 1 / 400, 1e-12) and _close(a[1], 1 / 400 + 3 / 300, 1e-12)
    assert _close((pop * a).sum(), 4.0, 1e-12)                      # 공급 보존: 시설 4개 모두 할당
    b = r['lz116']
    # 경계 조건: o2→g1, o2→g3 는 다른 단위 → D(g1)=100, D(g2)=300, D(g3)=0(할당 안 됨)
    assert _close(b['A'][0, 0], 1 / 100, 1e-12) and _close(b['A'][1, 0], 2 / 300, 1e-12)
    assert (not b['assigned'][4]) and b['assigned'][2] and b['assigned'][3]
    assert _close((pop * b['A'][:, 0]).sum(), 3.0, 1e-12)           # 할당된 3개만 보존
    assert _close(100 * b['A'][0, 0], 1.0, 1e-12) and _close(300 * b['A'][1, 0], 2.0, 1e-12)   # 단위마다 보존


def test_sfca_duplicates_count():
    # MAI와 달리 같은 격자의 시설 수가 그대로 공급이 된다: 시설 2개면 1인당 몫 2배
    pop = np.array([50, 0], float); o = np.array([0]); d = np.array([1])
    r1 = E.sfca_access(o, d, pop, np.array([[0], [1]], float), {'none': None})['none']['A'][0, 0]
    r2 = E.sfca_access(o, d, pop, np.array([[0], [2]], float), {'none': None})['none']['A'][0, 0]
    assert _close(r2, 2 * r1, 1e-15) and _close(r1, 1 / 50, 1e-15)


def test_sfca_conservation_random():
    rng = np.random.default_rng(7); n = 300
    pop = rng.integers(0, 50, n).astype(float); S = rng.integers(0, 3, (n, 4)).astype(float)
    o = rng.integers(0, n, 4000); d = rng.integers(0, n, 4000); keep = pop[o] > 0; o, d = o[keep], d[keep]
    units = {'none': None, 'dong424': rng.integers(0, 12, n)}
    r = E.sfca_access(o, d, pop, S, units)
    for b, v in r.items():
        assert np.allclose((pop[:, None] * v['A']).sum(0), S[v['assigned']].sum(0), rtol=1e-12)
        if b != 'none':
            u = units[b]
            for uu in np.unique(u):
                m = u == uu
                assert np.allclose((pop[m, None] * v['A'][m]).sum(0), S[m & v['assigned']].sum(0), rtol=1e-12, atol=1e-12)


def test_boundary_monotone():
    # 경계 제한은 도달을 늘릴 수 없다
    res, _, _ = _example1()
    for b in ['lz116', 'ld']:
        assert (res[b]['r'] <= res['none']['r']).all()


# ------------------------------------------------------------------ 독립 구현 대조 (실자료 한 구)
def _independent_pandas(year, grid, ku, T, net_year=None):
    """엔진 코드를 쓰지 않는 두 번째 구현: merge + groupby. net_year 가 다르면 그 시점 소요시간표 + 보충표를 읽는다."""
    py = C.YEARS[year]['pop_year']
    gm = pd.read_parquet(C.DATA / 'grid' / f'grid{grid}_master.parquet')
    gm = gm[['grid_cd', f'pop_{py}', 'dong424', 'lz116', f'ld{year}', 'ku']].rename(columns={f'pop_{py}': 'pop', f'ld{year}': 'ld'})
    gcol = 'grid100_cd' if grid == 100 else 'grid250_cd'
    f = pd.read_parquet(C.DATA / 'facility' / 'facility_2020_2025_units.parquet', columns=['year', '분석가능', 'cat_A', 'role', gcol])
    f = f[(f.year == year) & f['분석가능'].astype(bool) & (f.role.astype(str) != 'control') & f.cat_A.isin(list(C.CAT_A))]
    fc = f[[gcol, 'cat_A']].drop_duplicates().rename(columns={gcol: 'd_grid', 'cat_A': 'cat'})
    fc = fc[fc.d_grid.isin(gm.grid_cd)]
    ncat = fc.groupby('d_grid').cat.nunique().rename('nC').reset_index()
    net = year if net_year is None else net_year
    files = sorted((C.DATA / 'ttm' / f'ttm{grid}_{net}' / f'ku={ku}').glob('*.parquet'))
    if net != year:
        files += sorted((C.DATA / 'ttm' / f'ttm{grid}_{net}_for{year}' / f'ku={ku}').glob('*.parquet'))
    tt = pd.concat([pd.read_parquet(p, columns=['o_grid', 'd_grid', 't_sec']) for p in files], ignore_index=True)
    tt = tt.merge(gm.add_prefix('o_'), left_on='o_grid', right_on='o_grid_cd').merge(gm.add_prefix('d_'), left_on='d_grid', right_on='d_grid_cd')
    tt = tt[tt.o_pop > 0]
    x = tt.merge(fc, on='d_grid').merge(ncat, on='d_grid')
    out = []
    for b in E.BOUNDS:
        y = x if b == 'none' else x[x[f'o_{b}'] == x[f'd_{b}']]
        tmin = y.groupby(['o_grid', 'cat']).t_sec.min().rename('t_ind')
        mm = y[y.t_sec <= T].groupby(['o_grid', 'cat']).nC.max().rename('m_ind')
        z = pd.concat([tmin, mm], axis=1).reset_index(); z['b'] = b
        out.append(z)
    return pd.concat(out, ignore_index=True)


def _engine_ku(year, grid, ku, T, net_year=None):
    gm, cats, Cm, _, _ = E.load_inputs(year, grid, 'A', 'with')
    code = pd.Series(gm['gi'].values, index=gm['grid_cd'].values)
    units = {'none': None, **{b: gm[b].astype(np.int64).values for b in E.BOUNDS[1:]}}
    dset, _ = E.ttm_partitions(year, grid, ku, net_year)
    o, d, t, _ = E.read_ttm_ku(dset, ku, code, gm['pop'].values, 1.0)
    res = E.origin_access(o, d, t, Cm, units, len(cats), T)
    rows = []
    for b, v in res.items():
        n = len(v['o'])
        rows.append(pd.DataFrame({'o_grid': np.repeat(gm['grid_cd'].values[v['o']], len(cats)), 'cat': np.tile(cats, n), 'b': b,
                                  'r': v['r'].ravel(), 'm': v['m'].ravel(), 't': v['t'].ravel()}))
    return pd.concat(rows, ignore_index=True)


def test_independent_implementation_ku(year=2025, grid=100, ku=11010, T=900):
    if not (C.DATA / 'ttm' / f'ttm{grid}_{year}' / f'ku={ku}').exists():
        print('  (skip: 소요시간표 없음)'); return
    e = _engine_ku(year, grid, ku, T)
    ind = _independent_pandas(year, grid, ku, T)
    m = e.merge(ind, on=['o_grid', 'cat', 'b'], how='left')
    # t: 30분 안에 해당 카테고리 격자가 있으면 같아야 함
    assert ((m.t.isna() & m.t_ind.isna()) | (np.abs(m.t - m.t_ind) < TOL)).all()
    # r: 독립 구현의 m_ind 존재 여부와 같아야 함
    assert ((m.r == 1) == m.m_ind.notna()).all()
    assert ((m.m.isna() & m.m_ind.isna()) | (np.abs(m.m - m.m_ind) < TOL)).all()
    print(f'  pandas 독립 구현 대조: {year} {grid}m ku={ku} 격자×b×c {len(m):,}행 모두 일치')
    try:
        import duckdb  # noqa: F401
    except ImportError:
        print('  (DuckDB 없음: SQL 대조 생략)'); return
    _duckdb_check(e, year, grid, ku, T)


def test_net_year_independent_ku(year=2020, net=2025, grid=100, ku=11010, T=900):
    """네트워크 고정 민감도(--net-year): 2020 시설·인구 + 2025 소요시간표(+보충표). 출발 누락 0, 독립 구현과 완전 일치."""
    extra = C.DATA / 'ttm' / f'ttm{grid}_{net}_for{year}'
    if not extra.exists():
        print('  (skip: 보충표 없음 — a05c_ttm_supplement.py 먼저)'); return
    e = _engine_ku(year, grid, ku, T, net_year=net)
    gm = pd.read_parquet(C.DATA / 'grid' / f'grid{grid}_master.parquet', columns=['grid_cd', 'ku', f'pop_{C.YEARS[year]["pop_year"]}'])
    need = set(gm.loc[(gm.ku == ku) & (gm[f'pop_{C.YEARS[year]["pop_year"]}'] > 0), 'grid_cd'])
    assert need == set(e.o_grid), f'출발 누락 {len(need - set(e.o_grid))}'
    main_o = set(pd.concat([pd.read_parquet(f, columns=['o_grid']) for f in (C.DATA / 'ttm' / f'ttm{grid}_{net}' / f'ku={ku}').glob('*.parquet')]).o_grid)
    add_o = set(pd.concat([pd.read_parquet(f, columns=['o_grid']) for f in (extra / f'ku={ku}').glob('*.parquet')]).o_grid) if (extra / f'ku={ku}').exists() else set()
    assert not (main_o & add_o)                                  # 보충표는 확정표에 없는 출발만
    ind = _independent_pandas(year, grid, ku, T, net_year=net)
    m = e.merge(ind, on=['o_grid', 'cat', 'b'], how='left')
    assert ((m.t.isna() & m.t_ind.isna()) | (np.abs(m.t - m.t_ind) < TOL)).all()
    assert ((m.r == 1) == m.m_ind.notna()).all()
    assert ((m.m.isna() & m.m_ind.isna()) | (np.abs(m.m - m.m_ind) < TOL)).all()
    print(f'  네트워크 고정 {year} 시설·인구 × {net} 보행망 ku={ku}: 출발 {len(need):,}셀(보충 {len(add_o)}), 격자×b×c {len(m):,}행 독립 구현과 일치')


def _duckdb_check(e, year, grid, ku, T):
    import duckdb
    py = C.YEARS[year]['pop_year']; gcol = 'grid100_cd' if grid == 100 else 'grid250_cd'
    con = duckdb.connect()
    gmp = str(C.DATA / 'grid' / f'grid{grid}_master.parquet').replace('\\', '/')
    fp = str(C.DATA / 'facility' / 'facility_2020_2025_units.parquet').replace('\\', '/')
    tp = str(C.DATA / 'ttm' / f'ttm{grid}_{year}' / f'ku={ku}' / '*.parquet').replace('\\', '/')
    cats = "','".join(C.CAT_A)
    q = f"""
    with g as (select grid_cd, pop_{py} as pop, dong424, lz116, ld{year} as ld, ku from '{gmp}'),
    fc as (select distinct {gcol} as d_grid, cat_A as cat from '{fp}'
           where year={year} and "분석가능" and role<>'control' and cat_A in ('{cats}') and {gcol} in (select grid_cd from g)),
    nc as (select d_grid, count(distinct cat) as nC from fc group by 1),
    t as (select o_grid, d_grid, t_sec from read_parquet('{tp}')),
    x as (select t.o_grid, t.d_grid, t.t_sec, fc.cat, nc.nC, go.dong424 o_dn, gd.dong424 d_dn, go.lz116 o_lz, gd.lz116 d_lz,
                 go.ld o_ld, gd.ld d_ld, go.ku o_ku, gd.ku d_ku
          from t join g go on go.grid_cd=t.o_grid join g gd on gd.grid_cd=t.d_grid
          join fc on fc.d_grid=t.d_grid join nc on nc.d_grid=t.d_grid where go.pop>0),
    bb as (select 'none' b, * from x union all select 'dong424', * from x where o_dn=d_dn union all select 'lz116', * from x where o_lz=d_lz
           union all select 'ld', * from x where o_ld=d_ld union all select 'ku', * from x where o_ku=d_ku)
    select o_grid, cat, b, min(t_sec) t_sql, max(case when t_sec<={T} then nC end) m_sql from bb group by 1,2,3
    """
    s = con.execute(q).df()
    m = e.merge(s, on=['o_grid', 'cat', 'b'], how='left')
    assert ((m.t.isna() & m.t_sql.isna()) | (np.abs(m.t - m.t_sql) < TOL)).all()
    assert ((m.m.isna() & m.m_sql.isna()) | (np.abs(m.m - m.m_sql) < TOL)).all()
    assert ((m.r == 1) == m.m_sql.notna()).all()
    print(f'  DuckDB SQL 독립 구현 대조: {len(m):,}행 모두 일치')


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    fails = 0
    for fn in tests:
        try:
            fn(); print('PASS', fn.__name__)
        except AssertionError as ex:
            fails += 1; print('FAIL', fn.__name__, ex)
    print(f'{len(tests) - fails}/{len(tests)} 통과')
    sys.exit(1 if fails else 0)
