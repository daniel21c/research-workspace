# -*- coding: utf-8 -*-
"""연구3(AG) 표·그림: T5 카테고리별 ΔCOV·ΔMAI 기술통계, F3 동별 ΔCOV·ΔMAI 지도.

정의: Δ = 값(Leiden LD116) − 값(공식 LZ116), 동 424 단위, 본 분석(main) unit_access 에서 읽는다(03_불일치_접근성_AG/연구설계.md 5·11.2절).
  연구3 본 시점은 2025(LD = ld2025). 2020(LD = ld2020)은 참고로 같은 표에 둔다.
  COV·MAI 는 경계 조건 b = lz116 / ld 의 동 값(격자에서 바로 분자합/분모합). 종합 = 카테고리 단순평균(엔진 값 그대로).
  MAI 는 도달 인구가 0 이면 정의되지 않음 → 그 동은 해당 카테고리 ΔMAI 에서 빠진다(수를 표에 적음).
산출: 데이터/결과/tables/T5_category_delta_LD_LZ.{csv,md}, 데이터/결과/tables/F3_dong_delta_2025.csv,
      데이터/결과/figures/F3_dong_dCOV_dMAI_2025.{png,pdf}, 데이터/결과/figures/F3s_dong_delta_by_category_2025.png
실행: python a07_study3_outputs.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a00_config as C  # noqa: E402
import a99_manifest as M  # noqa: E402

TAB = C.OUT / 'tables'; FIG = C.OUT / 'figures'
CATS = list(C.CAT_A) + ['종합']
EPS = 1e-12                                     # Δ=0 판정(a06b_summary.dist 와 같은 기준)


def dong_delta_all(year):
    u = pd.read_csv(C.OUT / 'main' / f'unit_access_{year}_100.csv')
    d = u[(u.unit_level == 'dong424') & (u.b.isin(['lz116', 'ld']))]
    p = d.pivot_table(index=['unit_id', 'cat'], columns='b', values=['COV', 'MAI'], dropna=False)
    p.columns = [f'{a}_{b}' for a, b in p.columns]
    p = p.reset_index().rename(columns={'unit_id': 'dong424'})
    p['dCOV'] = p['COV_ld'] - p['COV_lz116']
    p['dMAI'] = p['MAI_ld'] - p['MAI_lz116']
    p['year'] = year
    return p


def stats(s):
    s = s.dropna()
    return {'n': len(s), '평균': s.mean(), '표준편차': s.std(), 'p10': s.quantile(.1), '중위': s.median(), 'p90': s.quantile(.9),
            '최소': s.min(), '최대': s.max(), 'Δ=0 동': int((s.abs() <= EPS).sum()), 'Δ>0 동': int((s > EPS).sum()), 'Δ<0 동': int((s < -EPS).sum())}


def t5():
    rows = []
    for y in (2025, 2020):
        p = dong_delta_all(y)
        for cat in CATS:
            x = p[p.cat == cat]
            for ind in ['COV', 'MAI']:
                r = {'year': y, 'cat': cat, '지표': ind, 'LZ 동 평균': x[f'{ind}_lz116'].mean(), 'LD 동 평균': x[f'{ind}_ld'].mean(), **stats(x[f'd{ind}'])}
                r['정의 안 됨 동(LZ 또는 LD)'] = int(x[f'd{ind}'].isna().sum())
                rows.append(r)
    t = pd.DataFrame(rows)
    t.to_csv(TAB / 'T5_category_delta_LD_LZ.csv', index=False, encoding='utf-8-sig', float_format='%.6f', lineterminator='\n')
    return t


def md(df, fmt='{:.4f}', ints=('n', 'year', 'Δ=0 동', 'Δ>0 동', 'Δ<0 동', '정의 안 됨 동(LZ 또는 LD)')):
    cols = list(df.columns)
    out = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (int, float, np.integer, np.floating)) and not pd.isna(v):
                cells.append(str(int(v)) if c in ints else fmt.format(v))
            else:
                cells.append('' if pd.isna(v) else str(v))
        out.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(out)


def write_t5_md(t):
    L = ['# T5 카테고리별 ΔCOV·ΔMAI 기술통계 (동 424, Δ = Leiden LD116 − 공식 LZ116)', '',
         '- 원자료: `데이터/결과/main/unit_access_{2025,2020}_100.csv`(본 분석: A 8개 카테고리, T = 15분, 4.0 km/h, 100m 격자). 코드 `코드/a07_study3_outputs.py`.',
         '- 각 동의 COV·MAI는 경계 조건 b 아래 격자 값에서 바로 분자합/분모합으로 만든 값이다. "LZ·LD 동 평균"은 동 값의 단순평균(기술통계용)이며 서울 전체 값이 아니다.',
         '- Δ>0 은 Leiden 경계 안에서 접근성이 더 높은 동. Δ=0 판정은 |Δ| ≤ 1e-12. MAI는 도달 인구가 없는 동에서 정의되지 않아 그 카테고리의 n에서 빠진다.',
         '- 연구3 본 시점은 2025(LD = Leiden 2025). 2020(LD = Leiden 2020)은 참고.', '']
    keep = ['cat', 'LZ 동 평균', 'LD 동 평균', 'n', '평균', '표준편차', 'p10', '중위', 'p90', '최소', '최대', 'Δ=0 동', 'Δ>0 동', 'Δ<0 동', '정의 안 됨 동(LZ 또는 LD)']
    for y in (2025, 2020):
        for ind in ['COV', 'MAI']:
            x = t[(t.year == y) & (t['지표'] == ind)][keep]
            L += [f'## {y} Δ{ind}' + (' (참고)' if y == 2020 else ''), '', md(x), '']
    L += ['## 필수 문구', '', 'MAI는 경계 안에서 해당 카테고리 시설에 도달한 인구만을 대상으로 한 조건부·상한 지표이며, 실제 통행사슬을 재현하지 않는다. '
          '도달하지 못한 인구의 값은 0이 아니라 정의되지 않으며, 그 사정은 Coverage가 보여 준다.', '']
    (TAB / 'T5_category_delta_LD_LZ.md').write_text('\n'.join(L), encoding='utf-8', newline='\n')


# ------------------------------------------------------------------ F3 지도
def diverging_cmap():
    """blue ↔ red, 중립 회색 중간(dataviz 기준 팔레트). Δ>0(Leiden 쪽 높음) = 파랑, Δ<0 = 빨강."""
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list('div_rb', ['#8c1f1f', '#e34948', '#f0efec', '#2a78d6', '#163f78'], N=256)


def sym_limit(v):
    a = np.abs(v.dropna()); a = a[a > EPS]
    return float(np.quantile(a, 0.95)) if len(a) else 1.0


def draw(ax, gdf, col, lim, cmap, ku, lz, ld, title, lw=0.55, fs=10.5):
    from matplotlib.colors import Normalize
    norm = Normalize(-lim, lim)
    miss = gdf[col].isna()
    gdf[~miss].plot(column=col, ax=ax, cmap=cmap, norm=norm, edgecolor='white', linewidth=0.15)
    if miss.any():
        gdf[miss].plot(ax=ax, facecolor='none', edgecolor='#8a8a86', hatch='////', linewidth=0.2)
    ld.boundary.plot(ax=ax, color='#1f1f1d', linewidth=lw, linestyle=(0, (2.2, 1.4)))
    lz.boundary.plot(ax=ax, color='#1f1f1d', linewidth=lw)
    ax.set_title(title, fontsize=fs, loc='left')
    ax.set_axis_off(); ax.set_aspect('equal')
    return norm


def legend_lines(fig):
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color='#1f1f1d', lw=0.9, label='공식 생활권 LZ116 경계'),
         Line2D([], [], color='#1f1f1d', lw=0.9, linestyle=(0, (2.2, 1.4)), label='Leiden 2025 LD116 경계')]
    fig.legend(handles=h, loc='lower center', ncol=2, frameon=False, fontsize=8.5)


def f3():
    import geopandas as gpd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    plt.rcParams['font.family'] = 'Malgun Gothic'; plt.rcParams['axes.unicode_minus'] = False
    gp = C.DATA / 'boundary' / 'seoul_boundaries_all.gpkg'
    dong = gpd.read_file(gp, layer='dong_424')[['Dong', 'Ku', 'ku_name', 'ADM_NM', 'geometry']]
    dong['Dong'] = dong['Dong'].astype('int64')
    lz = gpd.read_file(gp, layer='official_livingzone_116_dongbased')
    ld = gpd.read_file(gp, layer='leiden_2025_116')
    ku = dong.dissolve('Ku')
    p = dong_delta_all(2025)
    comp = p[p.cat == '종합'][['dong424', 'COV_lz116', 'COV_ld', 'dCOV', 'MAI_lz116', 'MAI_ld', 'dMAI']]
    g = dong.merge(comp, left_on='Dong', right_on='dong424', how='left')
    assert g['dCOV'].notna().sum() == 424, '동 경계와 결과의 동 코드가 424개 모두 맞지 않음'
    out = g.drop(columns='geometry').drop(columns='dong424').rename(columns={'Dong': 'dong424', 'Ku': 'ku', 'ADM_NM': 'dong_name'})
    out.to_csv(TAB / 'F3_dong_delta_2025.csv', index=False, encoding='utf-8-sig', float_format='%.6f', lineterminator='\n')
    cmap = diverging_cmap()
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.4))
    for ax, col, name in [(axes[0], 'dCOV', 'ΔCOV'), (axes[1], 'dMAI', 'ΔMAI')]:
        lim = sym_limit(g[col])
        n = g[col]
        title = f'{name} = Leiden - 공식 (2025, 종합)\n동 {n.notna().sum()}개 · Δ>0 {int((n > EPS).sum())} · Δ=0 {int((n.abs() <= EPS).sum())} · Δ<0 {int((n < -EPS).sum())}'
        norm = draw(ax, g, col, lim, cmap, ku, lz, ld, title)
        cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=ax, fraction=0.035, pad=0.01, extend='both')
        cb.ax.tick_params(labelsize=8); cb.outline.set_linewidth(0.3)
        cb.set_label(f'{name}  (색 범위 ±{lim:.3g} = |Δ|≠0 동의 95분위, 넘는 값은 끝색)', fontsize=7.5)
    legend_lines(fig)
    fig.text(0.01, 0.005, '자료: 데이터/결과/main/unit_access_2025_100.csv (A 8개 카테고리, 15분, 4.0 km/h, 100m). 파랑 = Leiden 경계 안 접근성이 더 높음, 빨강 = 공식 생활권 쪽이 더 높음, 회색 = 같음.',
             fontsize=7, color='#5c5c58')
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    for ext in ('png', 'pdf'):
        fig.savefig(FIG / f'F3_dong_dCOV_dMAI_2025.{ext}', dpi=300, facecolor='white', metadata={'Creator': 'a07_study3_outputs.py'} if ext == 'pdf' else None)
    plt.close(fig)
    # 부록: 카테고리별 작은 지도(색 범위는 지표마다 카테고리 공통)
    cats = list(C.CAT_A)
    fig, axes = plt.subplots(2, 8, figsize=(18, 5.6))
    for i, (ind, name) in enumerate([('dCOV', 'ΔCOV'), ('dMAI', 'ΔMAI')]):
        allv = p[p.cat.isin(cats)][ind]
        lim = sym_limit(allv)
        for j, cat in enumerate(cats):
            x = dong.merge(p[p.cat == cat][['dong424', ind]], left_on='Dong', right_on='dong424', how='left')
            norm = draw(axes[i, j], x, ind, lim, cmap, ku, lz, ld, f'{cat} {name}', lw=0.2, fs=9)
        cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=axes[i, :].tolist(), fraction=0.012, pad=0.005, extend='both')
        cb.ax.tick_params(labelsize=7); cb.set_label(f'{name} (±{lim:.3g})', fontsize=7.5)
    legend_lines(fig)
    fig.text(0.01, 0.005, '2025, Δ = Leiden - 공식. 빗금 = 한쪽 경계에서 MAI 정의 안 됨(도달 인구 0). 자료: 데이터/결과/main/unit_access_2025_100.csv', fontsize=7, color='#5c5c58')
    fig.savefig(FIG / 'F3s_dong_delta_by_category_2025.png', dpi=220, facecolor='white', bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    TAB.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
    t = t5(); write_t5_md(t); f3()
    files = [TAB / 'T5_category_delta_LD_LZ.csv', TAB / 'T5_category_delta_LD_LZ.md', TAB / 'F3_dong_delta_2025.csv',
             FIG / 'F3_dong_dCOV_dMAI_2025.png', FIG / 'F3_dong_dCOV_dMAI_2025.pdf', FIG / 'F3s_dong_delta_by_category_2025.png']
    M.update([M.row(f, 'a07_study3_outputs.py', M.count_rows(f)) for f in files])
    print(t[(t.year == 2025)][['cat', '지표', 'n', '평균', '표준편차', 'Δ=0 동', 'Δ>0 동', 'Δ<0 동']].to_string())
