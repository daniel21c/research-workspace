# -*- coding: utf-8 -*-
"""a06 결과 요약: 데이터/결과/{tag}/summary_{tag}.md 와 데이터/결과/summary_sensitivity.md 를 만든다.
숫자는 모두 데이터/결과 의 CSV 에서 읽어 계산한다(손으로 적지 않음).
사용: python a06b_summary.py            (있는 tag 모두)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a00_config as C  # noqa: E402
import a06c_delta as D  # noqa: E402

BL = {'none': '없음', 'dong424': '동424', 'lz116': '공식 LZ116', 'ld': 'Leiden LD116', 'ku': '구25'}
TAGS = {'main': '본 분석 (A 8개, T=15분, 4.0 km/h, 100m, 일상소매 포함)',
        'sens_T600': '임계 T = 10분', 'sens_speed36': '속도 3.6 km/h', 'sens_grid250': '격자 250m',
        'sens_A4': '카테고리 4개(A4)', 'sens_retail_without': '일상소매 제외', 'sens_union': '합집합 카테고리 수(Nicoletti) 추가',
        'natstd_B': '묶음 B 국가 최저기준(시설별 τ, 경계 없음, Coverage)',
        'sens_net2025': '네트워크 고정: 2020 시설·인구 + 2025 보행망(ttm100_2025 + 보충표 ttm100_2025_for2020), Leiden은 ld2020'}
MAI_NOTE = ('MAI는 경계 안에서 해당 카테고리 시설에 도달한 인구만을 대상으로 한 조건부·상한 지표이며, 실제 통행사슬을 재현하지 않는다. '
            '도달하지 못한 인구의 값은 0이 아니라 정의되지 않으며, 그 사정은 Coverage가 보여 준다.')


INTCOLS = {'n', 'year', 'n_units', 'n_defined', '값 0인 동'}


def _f(v, col, fmt):
    if isinstance(v, (float, np.floating, int, np.integer)) and not pd.isna(v):
        return str(int(v)) if col in INTCOLS else fmt.format(v)
    return '' if pd.isna(v) else str(v)


def md(df, fmt='{:.4f}'):
    cols = list(df.columns)
    out = ['| ' + ' | '.join(str(c) for c in cols) + ' |', '|' + '---|' * len(cols)]
    for _, r in df.iterrows():
        out.append('| ' + ' | '.join(_f(v, c, fmt) for c, v in zip(cols, r.values)) + ' |')
    return '\n'.join(out)


def dist(s):
    s = s.dropna()
    return pd.Series({'n': len(s), '평균': s.mean(), '표준편차': s.std(), 'p10': s.quantile(.1), '중위': s.median(), 'p90': s.quantile(.9),
                      '최소': s.min(), '최대': s.max(), '>0 비율': (s > 1e-12).mean(), '<0 비율': (s < -1e-12).mean()})


def load_unit(tag):
    fs = sorted((C.OUT / tag).glob('unit_access_*.csv'))
    return pd.concat([pd.read_csv(f) for f in fs], ignore_index=True) if fs else None


def seoul_comp(u):
    s = u[(u.unit_level == 'seoul') & (u.cat == '종합')].copy()
    s['PWATT_min'] = s['PWATT_sec'] / 60
    return s


def dong_delta(u, year, col):
    """동 종합 Δ(LD − LZ); MAI 는 공통 카테고리 평균(a06c_delta, 지표정의_확정.md 3.3)."""
    return D.dong_delta(u, col, year)


def summary_tag(tag):
    outdir = C.OUT / tag
    metas = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(outdir.glob('run_meta_*.json'))]
    L = [f'# 접근성 엔진 결과 요약 — `{tag}`', '', f'- 설정: {TAGS.get(tag, tag)}', f'- 엔진: {metas[0]["engine"]}, 스크립트 `코드/a06_engine.py`, 요약 `코드/a06b_summary.py`',
         f'- 정의: `문서/지표정의_확정.md`. 상위 단위는 분자합/분모합, 종합은 카테고리 단순평균.', '']
    for m in metas:
        L.append(f'- {m["year"]}: 소요시간표 {m["ttm_rows"]:,}행, 출발(인구>0) {m["origins"]:,}셀, 시설(분석가능·해당 시점) {m["fac_rows_year_analyzable"]:,}행 중 사용 {m["fac_rows_used"]:,}행'
                 + (f', 시설 격자 {m["fac_cells"]:,}' if 'fac_cells' in m else '') + (f', 일상소매 제외 {m["retail_removed"]:,}행' if 'retail_removed' in m else '')
                 + f', 격자 마스터 밖 {m["fac_rows_outside_grid"]}행 제외, 불변조건 {"통과" if all((m.get("checks") or {"ok": True}).values()) else "실패"}')
    L.append('')
    if tag == 'natstd_B':
        fs = sorted(outdir.glob('nat_standard_coverage_*.csv'))
        n = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
        s = n[n.unit_level == 'seoul'].pivot_table(index=['level', 'item'], columns='year', values='COV').reset_index()
        s['변화(2025−2020)'] = s[2025] - s[2020]
        L += ['## 1. 서울 전체 국가 최저기준 충족률 (인구 비율)', '', md(s), '',
              '- 카테고리 값 = 그 카테고리 시설 하위유형 중 하나라도 τ 안에 닿으면 충족(OR). 교육 = 유치원 10분 또는 초등학교 15분.', '']
        d = n[(n.unit_level == 'dong424') & (n.level == 'composite')].pivot_table(index='unit_id', columns='year', values='COV')
        L += ['## 2. 동 424 종합 충족률 분포', '', md(pd.DataFrame({y: dist(d[y]) for y in d.columns}).T.reset_index().rename(columns={'index': 'year'})), '']
        (outdir / f'summary_{tag}.md').write_text('\n'.join(L) + '\n', encoding='utf-8', newline='\n')
        return
    u = load_unit(tag)
    years = sorted(u.year.unique())
    s = seoul_comp(u)
    t1 = s.pivot_table(index='b', columns='year', values=['COV', 'MAI', 'PWATT_min'], observed=True)
    t1.columns = [f'{a} {b}' for a, b in t1.columns]
    t1 = t1.reindex(list(BL)).reset_index(); t1['b'] = t1['b'].map(BL)
    L += ['## 1. 서울 전체 종합값 (경계 조건별)', '', md(t1), '', '- PWATT_min: 15분 안에 도달한 인구만의 인구가중 평균 도달시간(분), 8개 카테고리 단순평균(보조).', '']
    if 'UNI' in u.columns:
        t1u = s.pivot_table(index='b', columns='year', values=['UNI', 'UNI_allpop'], observed=True)
        t1u.columns = [f'{a} {b}' for a, b in t1u.columns]; t1u = t1u.reindex(list(BL)).reset_index(); t1u['b'] = t1u['b'].map(BL)
        L += ['### 1a. 합집합 카테고리 수 U (Nicoletti)', '', md(t1u), '', '- UNI: 카테고리별 도달 인구 조건부 평균의 단순평균 (MAI와 같은 분모). UNI_allpop: 전체 인구 분모(미도달 0).', '']
    for y in years:
        c = u[(u.unit_level == 'seoul') & (u.year == y) & (u.cat != '종합') & (u.b.isin(['none', 'lz116', 'ld']))].copy()
        c['PWATT_min'] = c['PWATT_sec'] / 60
        p = c.pivot_table(index='cat', columns='b', values=['COV', 'MAI', 'PWATT_min'], observed=True, sort=False)
        p = p.reindex(columns=['none', 'lz116', 'ld'], level=1)
        p.columns = [f'{a} {BL[b]}' for a, b in p.columns]
        L += [f'## 2. 서울 카테고리별 값 — {y}', '', md(p.reset_index()), '']
    L += ['## 3. 동별 ΔCOV·ΔMAI (LD − LZ, 종합값) 분포', '']
    rows = []
    for y in years:
        for col in ['COV', 'MAI']:
            r = dist(dong_delta(u, y, col)); r.name = f'Δ{col} {y}'; rows.append(r)
    L += [md(pd.DataFrame(rows).reset_index().rename(columns={'index': '항목'})), '', '- 동 424개. >0 은 Leiden 경계 안에서 접근성이 더 높은 동.', '']
    if len(years) == 2:
        y0, y1 = years
        a = s[s.year == y0].set_index('b'); b = s[s.year == y1].set_index('b')
        ch = pd.DataFrame({'ΔCOV': b['COV'] - a['COV'], 'ΔMAI': b['MAI'] - a['MAI'], 'ΔPWATT_min': b['PWATT_min'] - a['PWATT_min']}).reindex(list(BL)).reset_index()
        ch['b'] = ch['b'].map(BL)
        L += [f'## 4. {y0}→{y1} 변화', '', '### 4.1 서울 종합값 변화', '', md(ch), '']
        c = u[(u.unit_level == 'seoul') & (u.b == 'none') & (u.cat != '종합')].pivot_table(index='cat', columns='year', values=['COV', 'MAI'], observed=True, sort=False)
        cc = pd.DataFrame({'ΔCOV': c['COV'][y1] - c['COV'][y0], 'ΔMAI': c['MAI'][y1] - c['MAI'][y0]}).reset_index()
        L += ['### 4.2 카테고리별 변화 (경계 없음)', '', md(cc), '']
        d = u[(u.unit_level == 'dong424') & (u.cat == '종합')]
        rows = []
        for bb in ['none', 'lz116', 'ld']:
            for col in ['COV', 'MAI']:
                p = d[d.b == bb].pivot_table(index='unit_id', columns='year', values=col, observed=True)
                r = dist(p[y1] - p[y0]); r.name = f'Δ{col} {BL[bb]}'; rows.append(r)
        L += ['### 4.3 동별 변화 분포 (종합값)', '', md(pd.DataFrame(rows).reset_index().rename(columns={'index': '항목'})), '',
              '- 주의: 2025 보행망은 OSM 매핑이 +31.6% 늘어난 판이라 변화에는 실제 시설·인구 변화와 네트워크 표현 변화가 섞인다. Leiden 경계는 연도별(ld2020·ld2025)이다.', '']
    if tag == 'sens_net2025':
        L += net_decomp('##')
    L += sfca_section(tag)
    L += ['## 필수 문구', '', MAI_NOTE, '']
    (outdir / f'summary_{tag}.md').write_text('\n'.join(L) + '\n', encoding='utf-8', newline='\n')


def load_sfca(tag):
    fs = sorted((C.OUT / tag).glob('sfca_unit_*.csv'))
    return pd.concat([pd.read_csv(f) for f in fs], ignore_index=True) if fs else None


def open_ratio_table(s, year):
    """경계 개방비 OR(b = none 행)의 단위 수준별 분포: |log OR| 중위·p90, 정의된 단위 수."""
    rows = []
    for (lvl, item), d in s[(s.year == year) & (s.b == 'none') & (s.unit_level != 'seoul')].groupby(['unit_level', 'item'], sort=False):
        o = d['open_ratio'].dropna(); lo = np.log(o[o > 0])
        rows.append({'year': year, 'unit_level': lvl, 'item_type': d['item_type'].iloc[0], 'item': item, 'n_units': len(d), 'n_defined': int(o.notna().sum()),
                     'OR 중위': o.median(), '|log OR| 중위': lo.abs().median(), '|log OR| p90': lo.abs().quantile(.9),
                     'OR>1 비율': (o > 1).mean() if len(o) else np.nan})
    return pd.DataFrame(rows)


def sfca_section(tag):
    """2SFCA 요약(지표정의_확정.md 3.4). main 이면 경계 개방비 분포 표를 데이터/결과/tables/ 에도 쓴다."""
    s = load_sfca(tag)
    if s is None:
        return []
    years = sorted(s.year.unique()); pub = [k for k in C.SFCA_PUBLIC if k in set(s.item)]
    L = ['## 5. 2SFCA — 인구 1만 명당 시설 수 (15분, 공급 = 시설 개수)', '',
         '- 원자료: `sfca_unit_{연도}_{격자}.csv`. 단위 값 = Σ p·A / Σ p × 10,000(분모 = 전체 인구). 종합값은 만들지 않는다. 공공시설 단일 종 7개를 먼저 보고한다.', '']
    se = s[(s.unit_level == 'seoul') & (s.item.isin(pub))]
    t = se.pivot_table(index='item', columns=['year', 'b'], values='SFCA_per10k', observed=True).reindex(pub)
    t = t.loc[:, [(y, b) for y in years for b in ['none', 'dong424', 'lz116', 'ld', 'ku'] if (y, b) in t.columns]]
    t.columns = [f'{y} {BL[b]}' for y, b in t.columns]
    L += ['### 5.1 서울 전체 (경계 조건별)', '', md(t.reset_index()), '',
          '- 경계 조건을 걸어도 서울 값이 거의 같은 것은 공급 보존 때문이다(할당 안 된 시설만 빠짐). 차이는 단위 안 분포에서 나타난다.', '']
    z = se[se.b == 'none'].pivot_table(index='item', columns='year', values='pop_share_A0', observed=True).reindex(pub)
    z.columns = [f'15분 안 시설 없는 인구 비율 {y}' for y in z.columns]
    L += [md(z.reset_index()), '']
    dd = []
    for y in years:
        d = s[(s.year == y) & (s.unit_level == 'dong424') & (s.b == 'none') & (s.item.isin(pub))]
        for item, x in d.groupby('item', sort=False):
            r = dist(x['SFCA_per10k']); r['값 0인 동'] = int((x['SFCA_per10k'] <= 0).sum()); r.name = f'{item} {y}'; dd.append(r)
    L += ['### 5.2 동 424 분포 (경계 없음)', '', md(pd.DataFrame(dd).drop(columns=['>0 비율', '<0 비율']).reset_index().rename(columns={'index': '항목'})), '']
    y = years[-1]; orr = open_ratio_table(s, y)
    L += [f'### 5.3 경계 개방비 OR = SFCA(경계 없음) / SFCA(단위 자신의 경계), {y}', '',
          '- OR > 1: 경계를 열면 1인당 몫이 늘어남(이웃 단위 시설에 기댐), OR < 1: 자기 단위 시설을 이웃과 나눠 씀. |log OR|가 작을수록 그 단위 안에서 공급·수요가 닫힌다.',
          '- 단위 안에 그 시설이 없으면(분모 0) 정의되지 않는다 → n_defined. 동 단위에서 드문 시설은 대부분 정의되지 않으므로 해석에 주의.', '',
          md(orr[orr.item.isin(pub)].drop(columns=['year', 'item_type'])), '']
    if tag == 'main':
        tb = C.OUT / 'tables'; tb.mkdir(exist_ok=True)
        pd.concat([open_ratio_table(s, yy) for yy in years]).to_csv(tb / 'SFCA_open_ratio.csv', index=False, encoding='utf-8-sig', float_format='%.6f', lineterminator='\n')
        L += ['- 전체 항목(카테고리 8·시설 28)·두 연도: `데이터/결과/tables/SFCA_open_ratio.csv`.', '']
    return L


def net_decomp(h='##'):
    """2020→2025 변화 분해: Δ전체 = main2025 − main2020 = Δ네트워크(sens_net2025 − main2020) + Δ나머지(main2025 − sens_net2025).
    Δ네트워크 = 시설·인구(2020)를 고정하고 보행망만 2020-01 → 2025-01 로 바꾼 효과(대부분 OSM 매핑 증가).
    Δ나머지 = 보행망(2025)을 고정한 시설·인구 변화 (+ b=Leiden 은 경계 ld2020 → ld2025 변화 포함).
    데이터/결과/sens_net2025/decomp_network_2020_2025.csv 를 쓰고 md 줄 목록을 돌려준다."""
    a = load_unit('main'); n = load_unit('sens_net2025')
    if n is None:
        return []
    A, B = a[a.year == 2020], a[a.year == 2025]
    rows = []
    for lvl_b, cats in [(list(BL), ['종합']), (['none'], list(C.CAT_A))]:
        for bb in lvl_b:
            for cat in cats:
                pick = lambda d: d[(d.unit_level == 'seoul') & (d.b == bb) & (d.cat == cat)].iloc[0]
                ra, rn, rb = pick(A), pick(n), pick(B)
                for col, f in [('COV', 1), ('MAI', 1), ('PWATT_min', 1 / 60)]:
                    src = 'PWATT_sec' if col == 'PWATT_min' else col
                    x0, xn, x1 = ra[src] * f, rn[src] * f, rb[src] * f
                    dt_, dn = x1 - x0, xn - x0
                    rows.append({'b': BL[bb], 'cat': cat, '지표': col, 'main 2020': x0, 'net2025 (2020 시설·인구)': xn, 'main 2025': x1,
                                 'Δ전체': dt_, 'Δ네트워크': dn, 'Δ나머지': x1 - xn,
                                 '네트워크 몫': dn / dt_ if abs(dt_) >= 1e-3 else np.nan})
    t = pd.DataFrame(rows)
    t.to_csv(C.OUT / 'sens_net2025' / 'decomp_network_2020_2025.csv', index=False, encoding='utf-8-sig', float_format='%.6f', lineterminator='\n')
    comp = t[t.cat == '종합'].drop(columns='cat')
    cat = t[(t.cat != '종합')].drop(columns='b')
    # 동별 분해 (종합값)
    drows = []
    for bb in ['none', 'lz116', 'ld']:
        for col in ['COV', 'MAI']:
            g = lambda d: d[(d.unit_level == 'dong424') & (d.b == bb) & (d.cat == '종합')].set_index('unit_id')[col]
            x0, xn, x1 = g(A), g(n), g(B)
            r = dist(xn - x0); r.name = f'Δ네트워크 {col} {BL[bb]}'; drows.append(r)
            r = dist(x1 - xn); r.name = f'Δ나머지 {col} {BL[bb]}'; drows.append(r)
    dd = pd.DataFrame(drows).reset_index().rename(columns={'index': '항목'})
    return [f'{h} 네트워크 고정 분해 (2020→2025)', '',
            '- Δ전체 = main 2025 − main 2020 = Δ네트워크 + Δ나머지. Δ네트워크 = sens_net2025 − main 2020(2020 시설·인구 고정, 보행망만 2025-01), '
            'Δ나머지 = main 2025 − sens_net2025(2025 보행망 고정, 시설·인구 변화; Leiden 행은 경계 ld2020→ld2025 변화 포함). 네트워크 몫 = Δ네트워크/Δ전체(|Δ전체| < 0.001이면 비율이 불안정해 빈칸).',
            '- 원자료: `데이터/결과/sens_net2025/decomp_network_2020_2025.csv`.', '',
            f'{h}# 서울 종합값', '', md(comp), '', f'{h}# 카테고리별 (경계 없음)', '', md(cat), '',
            f'{h}# 동 424 종합값 분해 분포', '', md(dd), '']


def summary_sensitivity():
    base = load_unit('main')
    bs = seoul_comp(base).set_index(['year', 'b'])
    rows = []
    for tag in TAGS:
        if tag == 'natstd_B':
            continue
        u = load_unit(tag)
        if u is None:
            continue
        s = seoul_comp(u).set_index(['year', 'b'])
        for (y, b), r in s.iterrows():
            if b not in ('none', 'lz116', 'ld'):
                continue
            rows.append({'tag': tag, 'year': y, 'b': BL[b], 'COV': r.COV, 'ΔCOV vs main': r.COV - bs.loc[(y, b), 'COV'],
                         'MAI': r.MAI, 'ΔMAI vs main': r.MAI - bs.loc[(y, b), 'MAI'], 'PWATT_min': r.PWATT_min,
                         'ΔPWATT vs main': r.PWATT_min - bs.loc[(y, b), 'PWATT_min'],
                         '동 ΔCOV(LD−LZ) 평균': dong_delta(u, y, 'COV').mean(), '동 ΔMAI(LD−LZ) 평균': dong_delta(u, y, 'MAI').mean()})
    t = pd.DataFrame(rows)
    L = ['# 민감도 비교 — 서울 전체 종합값', '', '- 각 tag의 `unit_access_*.csv` 서울 행(종합)과 본 분석(main)의 차이. 경계 조건은 없음·공식 LZ·Leiden LD만 표시(전체는 각 CSV).',
         '- A4는 카테고리 4개라 MAI 범위가 1~4로 달라 main과 수준 비교가 되지 않는다(Δ는 참고).', '- 체육 "규칙 없음"(취소·말소 포함) 민감도는 분석용 파일에 해당 행이 없어 계산하지 않았다. 면적비 격자 배정(연구1 전용)은 이번 범위 밖.', '',
         md(t), '']
    uu = load_unit('sens_union')
    if uu is not None:
        su = seoul_comp(uu)
        su = su[su.b.isin(['none', 'lz116', 'ld'])][['year', 'b', 'MAI', 'UNI', 'UNI_allpop']].copy()
        su['b'] = su['b'].map(BL)
        dl = []
        for y in sorted(uu.year.unique()):
            dl.append({'year': y, '동 ΔMAI(LD−LZ) 평균': dong_delta(uu, y, 'MAI').mean(), '동 ΔUNI(LD−LZ) 평균': dong_delta(uu, y, 'UNI').mean(),
                       '동별 ΔMAI·ΔUNI 상관': np.corrcoef(dong_delta(uu, y, 'MAI'), dong_delta(uu, y, 'UNI'))[0, 1]})
        L += ['## MAI 대비: 합집합 카테고리 수 U (Nicoletti, sens_union)', '', md(su), '', md(pd.DataFrame(dl)), '']
    n = pd.concat([pd.read_csv(f) for f in sorted((C.OUT / 'natstd_B').glob('nat_standard_coverage_*.csv'))], ignore_index=True)
    ns = n[(n.unit_level == 'seoul') & (n.level != 'facility')].pivot_table(index='item', columns='year', values='COV').reset_index()
    L += ['## 묶음 B 국가 최저기준 충족률 (서울)', '', md(ns), '']
    L += net_decomp('##')
    (C.OUT / 'summary_sensitivity.md').write_text('\n'.join(L) + '\n', encoding='utf-8', newline='\n')
    return t


if __name__ == '__main__':
    for tag in TAGS:
        if (C.OUT / tag).exists():
            summary_tag(tag)
            print('summary', tag)
    summary_sensitivity(); print('summary_sensitivity')
