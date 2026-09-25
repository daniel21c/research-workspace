# -*- coding: utf-8 -*-
"""경계 조건을 끈(b = none) 자치구별 COV·MAI 표와 승훈 씨 원고(국토학회 2026 춘계) 값 비교 준비.

연구3 설계 7.2·11.1 단계 3: 시설 입력이 다르므로(직접 구축 33종의 기능 카테고리 8개 vs 승훈 8종) 일치를 요구하지 않고
차이의 방향·원인을 기록한다(2026-09-24 사용자 결정). 승훈 씨 자료(시설·격자 인구·OD)는 쓰지 않는다. 원고에 인쇄된 값만
01_data/external/seunghoon_2026_kpa_seoul_values.csv 에 출처 쪽수와 함께 옮겨 적고 비교한다.
우리 값: 03_output/main(100m) 과 03_output/sens_grid250(250m, 원고 격자 크기와 같음)의 unit_level = ku, b = none.
4분면: 원고와 같은 규칙 — 구 값의 도시 평균(구 단순평균)을 기준으로 COV·MAI 높음(H)/낮음(L).
산출: 03_output/tables/ku_none_COV_MAI.csv, ku_compare_seunghoon.md, ku_compare_template.csv(승훈 씨 구별 값 받으면 채울 틀)
실행: python a08_ku_compare.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a00_config as C  # noqa: E402
import a99_manifest as M  # noqa: E402

TAB = C.OUT / 'tables'
EXT = C.DATA / 'external' / 'seunghoon_2026_kpa_seoul_values.csv'
RUNS = [('main', 100), ('sens_grid250', 250)]


def ku_names():
    u = pd.read_csv(C.DATA / 'boundary' / 'dong424_units.csv', usecols=['ku', 'ku_name']).drop_duplicates()
    return dict(zip(u.ku, u.ku_name))


def load():
    names = ku_names(); rows = []
    for tag, g in RUNS:
        for y in (2020, 2025):
            u = pd.read_csv(C.OUT / tag / f'unit_access_{y}_{g}.csv')
            x = u[(u.unit_level.isin(['ku', 'seoul'])) & (u.b == 'none')].copy()
            x['tag'] = tag
            rows.append(x[['tag', 'year', 'grid_m', 'unit_level', 'unit_id', 'cat', 'pop_total', 'pop_reach', 'COV', 'MAI', 'PWATT_sec']])
    t = pd.concat(rows, ignore_index=True)
    t['ku_name'] = t['unit_id'].map(names).where(t.unit_level == 'ku', '서울 전체')
    return t


def quadrant(k):
    """k: 구 종합값(COV, MAI). 기준 = 구 단순평균."""
    c0, m0 = k.COV.mean(), k.MAI.mean()
    q = np.where(k.COV >= c0, 'H', 'L').astype(object) + np.where(k.MAI >= m0, 'H', 'L').astype(object)
    return pd.Series(q, index=k.index), c0, m0


def md(df, fmt='{:.4f}'):
    cols = list(df.columns)
    out = ['| ' + ' | '.join(map(str, cols)) + ' |', '|' + '---|' * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)) and not pd.isna(v):
                cells.append(fmt.format(v))
            elif isinstance(v, (int, np.integer)):
                cells.append(str(int(v)))
            else:
                cells.append('' if pd.isna(v) else str(v))
        out.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(out)


def main():
    TAB.mkdir(exist_ok=True)
    t = load()
    t.to_csv(TAB / 'ku_none_COV_MAI.csv', index=False, encoding='utf-8-sig', float_format='%.6f', lineterminator='\n')
    ext = pd.read_csv(EXT, encoding='utf-8')
    ev = dict(zip(ext['item'], ext['value']))
    sh_cov, sh_mai = float(ev['seoul_city_mean_coverage']) / 100, float(ev['seoul_city_mean_mai'])
    sh_types = {k.replace('ku_type_', ''): v for k, v in ev.items() if k.startswith('ku_type_')}
    sh_counts = {q: int(ev[f'seoul_n_{q}']) for q in ['HH', 'HL', 'LH', 'LL']}

    comp = t[t.cat == '종합']
    # 1. 도시 수준 비교
    city = []
    quads = {}
    for tag, g in RUNS:
        for y in (2025, 2020):
            k = comp[(comp.tag == tag) & (comp.year == y) & (comp.unit_level == 'ku')].set_index('ku_name')
            s = comp[(comp.tag == tag) & (comp.year == y) & (comp.unit_level == 'seoul')].iloc[0]
            q, c0, m0 = quadrant(k)
            quads[(tag, y)] = (k.assign(유형=q), c0, m0)
            city.append({'자료': f'우리 {g}m {y}', '서울 인구가중 COV': s.COV, '구 단순평균 COV': c0, '서울 인구가중 MAI': s.MAI, '구 단순평균 MAI': m0,
                         'HH': int((q == 'HH').sum()), 'HL': int((q == 'HL').sum()), 'LH': int((q == 'LH').sum()), 'LL': int((q == 'LL').sum())})
    city.append({'자료': '승훈 씨 원고 (250m, 2025 시설·2024 인구)', '서울 인구가중 COV': np.nan, '구 단순평균 COV': sh_cov, '서울 인구가중 MAI': np.nan,
                 '구 단순평균 MAI': sh_mai, **sh_counts})
    city = pd.DataFrame(city)
    # 2. 구별 표 (2025, 두 격자)
    k1, _, _ = quads[('main', 2025)]; k2, _, _ = quads[('sens_grid250', 2025)]
    kt = pd.DataFrame({'COV 100m': k1.COV, 'MAI 100m': k1.MAI, '유형 100m': k1['유형'],
                       'COV 250m': k2.COV, 'MAI 250m': k2.MAI, '유형 250m': k2['유형']})
    kt['원고 유형(문장에 나온 구)'] = kt.index.map(lambda n: sh_types.get(n, ''))
    kt = kt.reset_index().rename(columns={'ku_name': '구'})
    k20, _, _ = quads[('main', 2020)]
    kt.insert(3, '유형 100m 2020', kt['구'].map(k20['유형']))
    # 3. 카테고리별 서울 값 (2025, 경계 없음)
    cat = t[(t.unit_level == 'seoul') & (t.year == 2025) & (t.cat != '종합')].pivot_table(index='cat', columns='grid_m', values=['COV', 'MAI'], sort=False)
    cat.columns = [f'{a} {b}m' for a, b in cat.columns]
    cat = cat.reindex(list(C.CAT_A)).reset_index()
    # 4. 템플릿 (승훈 씨 구별 값 받으면 채움)
    tpl = kt[['구', 'COV 100m', 'MAI 100m', 'COV 250m', 'MAI 250m']].copy()
    tpl['승훈 COV(%)'] = ''; tpl['승훈 MAI'] = ''; tpl['승훈 유형'] = tpl['구'].map(lambda n: sh_types.get(n, ''))
    tpl.to_csv(TAB / 'ku_compare_template.csv', index=False, encoding='utf-8-sig', float_format='%.6f', lineterminator='\n')

    # 방향 기록(숫자는 위 표에서 코드로)
    c100 = city.iloc[0]; c250 = city.iloc[2]
    named = kt[kt['원고 유형(문장에 나온 구)'] != ''][['구', '원고 유형(문장에 나온 구)', '유형 100m', '유형 250m']]
    agree100 = int((named['유형 100m'] == named['원고 유형(문장에 나온 구)']).sum())
    agree250 = int((named['유형 250m'] == named['원고 유형(문장에 나온 구)']).sum())
    corr = np.corrcoef(k1.COV, k2.COV)[0, 1], np.corrcoef(k1.MAI, k2.MAI)[0, 1]
    s25 = comp[(comp.year == 2025) & (comp.unit_level == 'seoul')].set_index('grid_m')
    cat25 = t[(t.unit_level == 'seoul') & (t.year == 2025) & (t.grid_m == 100) & (t.cat != '종합')].set_index('cat')
    L = ['# 자치구별 COV·MAI (경계 조건 없음) — 승훈 씨 원고 값과 비교 준비', '',
         '- 우리 값: `03_output/main/unit_access_*_100.csv`(100m), `03_output/sens_grid250/unit_access_*_250.csv`(250m), unit_level = ku·seoul, b = none(경계 조건 끔). 코드 `02_scripts/a08_ku_compare.py`. 전체 표 `03_output/tables/ku_none_COV_MAI.csv`(카테고리별 포함).',
         f'- 원고 값: `01_data/external/seunghoon_2026_kpa_seoul_values.csv`(원고·발표자료에 인쇄된 값을 쪽수와 함께 옮겨 적음). **원고에는 구별 수치가 숫자로 없다**(지도 색·산점도 점만). 그래서 이번 비교는 서울 도시 평균과 4분면 유형 개수·문장에 나온 구 {len(sh_types)}곳까지다.',
         '- 일치는 요구하지 않는다(시설 입력이 다름, 2026-09-24 사용자 결정). 4분면 기준은 원고와 같이 구 값의 도시 평균(구 단순평균).', '',
         '## 1. 서울 수준', '', md(city), '',
         '- 원고의 "도시 평균"이 구 단순평균인지 인구가중인지는 원고에 명시가 없다. 우리 값은 두 가지를 모두 적었다.', '',
         '## 2. 자치구별 종합값 (2025, 경계 없음)', '', md(kt), '',
         f'- 문장에 나온 구 {len(named)}곳 중 유형이 원고와 같은 구: 100m {agree100}곳, 250m {agree250}곳. 원고 문장은 "등"으로 끝나 전체 목록이 아니다.',
         f'- 우리 100m와 250m의 구별 상관: COV {corr[0]:.3f}, MAI {corr[1]:.3f}.', '',
         '## 3. 서울 카테고리별 값 (2025, 경계 없음)', '', md(cat), '',
         '## 4. 차이의 방향과 원인 (기록)', '',
         f'1. **COV 수준**: 우리 서울 인구가중 COV {s25.loc[100, "COV"]:.4f}(100m)·{s25.loc[250, "COV"]:.4f}(250m), 구 단순평균 {c100["구 단순평균 COV"]:.4f}·{c250["구 단순평균 COV"]:.4f} vs 원고 {sh_cov:.3f} '
         f'→ 구 단순평균 차이 {c100["구 단순평균 COV"] - sh_cov:+.4f}(100m)·{c250["구 단순평균 COV"] - sh_cov:+.4f}(250m). 수준은 {"거의 같다" if abs(c100["구 단순평균 COV"] - sh_cov) < 0.005 else ("우리가 높다" if c100["구 단순평균 COV"] > sh_cov else "우리가 낮다")}(100m 기준, |차| < 0.005를 "거의 같음"으로 봄). '
         f'그러나 같은 수준이 같은 구성을 뜻하지 않는다: (a) 카테고리 구성 — 우리 8개 중 COV가 낮은 것은 문화 {cat25.loc["문화", "COV"]:.3f}·행정·안전 {cat25.loc["행정·안전", "COV"]:.3f}이고 나머지는 {cat25.drop(["문화", "행정·안전"]).COV.min():.3f} 이상; 원고는 도서관·행정이 낮고 공원을 포함(우리는 공원 제외, 자료가공설계 C5). '
         '(b) 경계 밖 시설 — 원고는 행정경계 밖 5km 시설을 도착지에 넣었고 우리는 서울 격자 안 시설만 쓴다 → 외곽 구에서 우리 값이 낮아지는 방향. (c) 보행망 — 원고 OSRM(OSM 2025), 우리 OSM 2025-01 자체 그래프(보도·서비스도로 포함).',
         f'2. **MAI 수준**: 우리 서울 MAI {s25.loc[100, "MAI"]:.3f}(100m)·{s25.loc[250, "MAI"]:.3f}(250m), 구 단순평균 {c100["구 단순평균 MAI"]:.3f}·{c250["구 단순평균 MAI"]:.3f} vs 원고 {sh_mai:.2f}(250m). '
         f'같은 250m에서 우리가 {"높다" if c250["구 단순평균 MAI"] > sh_mai else "낮다"}({c250["구 단순평균 MAI"] - sh_mai:+.2f}), 100m에서는 {"높다" if c100["구 단순평균 MAI"] > sh_mai else "낮다"}({c100["구 단순평균 MAI"] - sh_mai:+.2f}). '
         '250m에서 높은 원인 후보: 우리 카테고리에는 소매(일상소매 포함)·생활서비스(음식점·미용 등)처럼 촘촘한 업종이 있어 한 격자에 여러 카테고리가 겹치기 쉽다(원고 8종은 공공시설 위주). '
         f'격자 크기 효과(우리 250m − 100m = {s25.loc[250, "MAI"] - s25.loc[100, "MAI"]:+.2f})가 시설 구성 차이만큼 크므로, 수준보다 구 순위·유형 비교가 의미 있다.',
         f'3. **4분면 유형**: 대각(HH+LL) 구 수는 우리 100m {int(c100["HH"] + c100["LL"])}·250m {int(c250["HH"] + c250["LL"])}, 원고 {sh_counts["HH"] + sh_counts["LL"]}로 비슷하지만, HH/LL 나뉨은 우리 {int(c100["HH"])}/{int(c100["LL"])}(100m) vs 원고 {sh_counts["HH"]}/{sh_counts["LL"]}로 다르다. '
         f'문장에 나온 구 중 두 격자 모두 원고와 유형이 같은 구: {", ".join(named[(named["유형 100m"] == named["원고 유형(문장에 나온 구)"]) & (named["유형 250m"] == named["원고 유형(문장에 나온 구)"])]["구"]) or "없음"}(2절 표). 원인 후보는 1·2와 같고(특히 소매·생활서비스가 도심 구의 MAI를 올림), 구별 값이 없어 더 좁힐 수 없다.',
         '4. **MAI 정의**: 두 원고 모두 도달 격자 중 동시입지 유형 수 최댓값을 도달 인구로 가중평균한다(원고 발표자료 p.7 예시: 미도달 지역 제외). 원고 식(2)의 공원 가산은 최적화 단계의 점수이고, 현행 MAI에서는 공원을 8종의 하나로 센다. 우리 정의(지표정의_확정.md 3.3)와 같은 계열이며, 종합은 둘 다 유형 단순평균.',
         '5. **인구·시점**: 원고 2024-10 250m 격자 인구·2025 시설, 우리 SGIS 2024 인구(100m, 250m은 면적비 배분)·2024-12-31 시설.',
         '6. **다음 단계**: 승훈 씨에게 서울 25개 구의 종합 COV·MAI(가능하면 카테고리별) CSV를 받아 `03_output/tables/ku_compare_template.csv`의 빈 열에 채우고, 구 순위 상관(Spearman)과 유형 일치표를 추가한다. 원고 값을 우리 결과처럼 쓰지 않는다.', '']
    (TAB / 'ku_compare_seunghoon.md').write_text('\n'.join(L), encoding='utf-8', newline='\n')
    files = [TAB / 'ku_none_COV_MAI.csv', TAB / 'ku_compare_seunghoon.md', TAB / 'ku_compare_template.csv', EXT]
    M.update([M.row(f, 'a08_ku_compare.py' if f != EXT else '수기 전사(원고 인쇄값)', M.count_rows(f)) for f in files])
    print(city.to_string()); print(named.to_string())


if __name__ == '__main__':
    main()
