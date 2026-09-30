# -*- coding: utf-8 -*-
"""그림 1~4 (영문 원고용). 수치는 results/ 파일에서만 읽는다.
Fig1 연구 지역: 공식 116생활권·25구, 2025 통행 기준 재배정 동. Fig2 재배정 동 수 k별 누락 변화(통행 기준 vs 무작위 100경로).
Fig3 대안 지도 1,000장의 누락 분포와 공식 생활권. Fig4 범주별 공존 편상관(두 해).
실행: python code/a05_figures.py      출력: manuscript/figures/Fig{1..4}.png(600 dpi)·.pdf
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent; AG = HERE.parent; ROOT = AG.parent; RES = AG / 'results'; FIG = AG / 'manuscript' / 'figures'; FIG.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE)); import study as S  # noqa: E402
plt.rcParams.update({'font.family': 'Arial', 'font.size': 8, 'axes.linewidth': .6, 'axes.spines.top': False, 'axes.spines.right': False, 'savefig.dpi': 600})
CAT_EN = {'교육': 'Education', '보육·복지': 'Childcare & welfare', '의료': 'Health', '문화': 'Culture', '행정·안전': 'Civic & safety', '소매': 'Retail', '생활서비스': 'Personal services'}
YEARS = (2020, 2025)


def save(fig, name):
    fig.savefig(FIG / f'{name}.png', bbox_inches='tight'); fig.savefig(FIG / f'{name}.pdf', bbox_inches='tight'); plt.close(fig)


def fig1():
    y = 2025; paths = S.input_paths(ROOT, y); D = S.load(ROOT, y, paths); g = D['geom'].copy(); g['zone'] = D['LZ']; g['ku'] = D['ku']
    mv = pd.read_csv(RES / str(y) / 'a01_flow_moves.csv'); moved = set(mv.dong)
    g['moved'] = g.Dong.isin(moved)
    zones = g.dissolve('zone'); gus = g.dissolve('ku')
    fig, ax = plt.subplots(figsize=(6.3, 5.0))
    g[~g.moved].plot(ax=ax, color='#f2f2f2', edgecolor='#c8c8c8', linewidth=.2)
    g[g.moved].plot(ax=ax, color='#e08a3c', edgecolor='#c8c8c8', linewidth=.2)
    zones.boundary.plot(ax=ax, color='#555555', linewidth=.45); gus.boundary.plot(ax=ax, color='black', linewidth=1.0)
    ax.set_axis_off()
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], color='black', lw=1.0, label='District (gu) boundary'), Line2D([], [], color='#555555', lw=.45, label='Official living zone'),
                       Patch(facecolor='#e08a3c', edgecolor='#c8c8c8', label='Dong moved by flow-guided revision (2025)'), Patch(facecolor='#f2f2f2', edgecolor='#c8c8c8', label='Other dongs')],
              loc='upper center', bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False, fontsize=7)
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim(); L = 5000
    ax.plot([x1 - L - 1500, x1 - 1500], [y0 + 1500] * 2, color='black', lw=1.5); ax.text(x1 - L / 2 - 1500, y0 + 2100, '5 km', ha='center', fontsize=7)
    ax.annotate('N', xy=(x1 - 2500, y1 - 1500), xytext=(x1 - 2500, y1 - 4500), ha='center', fontsize=8, arrowprops=dict(arrowstyle='-|>', color='black', lw=.8))
    save(fig, 'Fig1')


def fig2():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9), sharey=True)
    for ax, y in zip(axes, YEARS):
        s = json.load(open(RES / str(y) / 'a01_summary.json', encoding='utf-8')); C = pd.DataFrame(s['curve']); R = pd.read_csv(RES / str(y) / 'a01_states.csv')
        rd = R[R.strategy == 'RAND']; k0 = pd.DataFrame({'k': [0], 'flow_dL': [0.0], 'rand_median': [0.0], 'rand_p2.5': [0.0], 'rand_p97.5': [0.0]}); C = pd.concat([k0, C], ignore_index=True)
        for _, g in rd.groupby('rep'):
            ax.plot(g.k, g.dL / 1e3, color='#9bb7d4', lw=.3, alpha=.35, zorder=1)
        ax.fill_between(C.k, C['rand_p2.5'] / 1e3, C['rand_p97.5'] / 1e3, color='#4f7cac', alpha=.18, lw=0, zorder=2, label='Random, central 95%')
        ax.plot(C.k, C.rand_median / 1e3, color='#1f4e79', lw=1.2, zorder=3, label='Random, median')
        ax.plot(C.k, C.flow_dL / 1e3, color='#c0392b', lw=1.6, zorder=4, label='Flow-guided')
        ax.axhline(0, color='black', lw=.5); ax.set_title(f'({"a" if y == 2020 else "b"}) {y}', loc='left', fontsize=8.5)
        ax.set_xlabel('Number of boundary dongs reassigned, k'); ax.set_xlim(0, C.k.max())
        kk = s['first_k_from_which_flow_below_all_random']; ax.axvline(kk, color='#777777', lw=.5, ls=':')
        ax.text(kk + .8, -118, f'k = {kk}', fontsize=6.5, color='#555555', va='bottom')
    axes[0].set_ylabel('Change in excluded residents (thousand)'); axes[0].legend(frameon=False, fontsize=6.5, loc='upper left')
    save(fig, 'Fig2')


def fig3():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7), sharey=True)
    for ax, y in zip(axes, YEARS):
        P = pd.read_csv(RES / str(y) / 'a03_ensemble_plans.csv'); s = json.load(open(RES / str(y) / 'a03_ensemble_summary.json', encoding='utf-8')); E = P[P.plan.str.startswith('E')]
        ax.hist(E.L / 1e6, bins=40, color='#8fa9c7', edgecolor='white', lw=.3)
        ax.axvline(s['L_LZ'] / 1e6, color='#c0392b', lw=1.5); ax.axvline(s['L_median_all'] / 1e6, color='#1f4e79', lw=1.0, ls='--')
        ax.text(s['L_LZ'] / 1e6, ax.get_ylim()[1] * .95, ' Official', color='#c0392b', fontsize=7, va='top')
        ax.text(s['L_median_all'] / 1e6, ax.get_ylim()[1] * .80, ' Median of\n alternatives', color='#1f4e79', fontsize=6.5, va='top', bbox=dict(facecolor='white', edgecolor='none', alpha=.85, pad=1))
        ax.set_title(f'({"a" if y == 2020 else "b"}) {y}', loc='left', fontsize=8.5); ax.set_xlabel('Excluded residents (million)')
    axes[0].set_ylabel('Alternative maps')
    save(fig, 'Fig3')


def fig4():
    cats = list(CAT_EN); fig, ax = plt.subplots(figsize=(4.6, 2.9)); w = .38; x = np.arange(len(cats))
    for j, (y, col) in enumerate(zip(YEARS, ('#8fa9c7', '#1f4e79'))):
        s = json.load(open(RES / str(y) / 'a04_mechanism_summary.json', encoding='utf-8'))
        ax.barh(x + (j - .5) * w, [s['partial_by_category'][c]['est'] for c in cats], height=w, color=col, label=str(y))
    ax.set_yticks(x); ax.set_yticklabels([CAT_EN[c] for c in cats]); ax.invert_yaxis(); ax.axvline(0, color='black', lw=.5)
    ax.set_xlabel('Partial Spearman correlation, trip share ~ facility share'); ax.legend(frameon=False, fontsize=7, loc='lower right')
    save(fig, 'Fig4')


if __name__ == '__main__':
    which = sys.argv[1:] or ['1', '2', '3', '4']
    for w in which:
        globals()[f'fig{w}']()
