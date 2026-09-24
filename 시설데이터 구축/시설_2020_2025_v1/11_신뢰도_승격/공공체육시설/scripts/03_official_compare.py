"""공공체육시설: 구축본(=문체부 명부 파싱) vs 명부 서울 공식 집계(시도별현황·종목 시트) + 범위별·도시재생 분류별 집계."""
import json
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parents[1]; V1 = HERE.parents[1]; SRC = V1 / '02_명부/공공체육시설'
q = json.load(open(SRC / 'qa_공공체육시설.json', encoding='utf-8'))
rows = []
for k, v in q['snapshots'].items():
    ot = v['official_total']
    rows.append(dict(snapshot=k, item='개별시설 합계(간이운동장 제외)', built=ot['parsed_individual'], official=ot['official_individual']))
    rows.append(dict(snapshot=k, item='간이운동장(마을체육시설, 구 집계표만)', built=v['village_table']['sum_시설수'], official=ot['official_village']))
    for t, c in v['official_check'].items():
        if c.get('official_seoul_count') is not None: rows.append(dict(snapshot=k, item=t, built=c['parsed_rows'], official=c['official_seoul_count']))
    d = pd.read_parquet(HERE / f'facilities_공공체육시설_{k}.parquet')
    for sc, n in d.scope_flag.value_counts().items(): rows.append(dict(snapshot=k, item=f'범위:{sc}', built=int(n), official=None))
    s = d[d.scope_flag != '서울밖소재(분석제외)']
    for (sc, c), n in s.groupby([s.scope_flag, s.urban_regen_class]).size().items(): rows.append(dict(snapshot=k, item=f'별표2:{c}|{sc}', built=int(n), official=None))
c = pd.DataFrame(rows); c['diff'] = c.built - c.official
c['official_source'] = c.snapshot.map({'2020_01': '문체부 전국 공공체육시설 현황(2019.12.31 기준) 총괄·마을체육시설', '2025_01': '문체부 전국 공공체육시설 현황(2024.12.31 기준) 종합본'})
c.to_csv(HERE / 'official_compare_공공체육시설.csv', index=False, encoding='utf-8-sig'); print(c.to_string())
