# -*- coding: utf-8 -*-
"""정수계획·유형별 정확해의 저장 입지로 하위 20%(분수 가중)·결손집단 완결률을 계산 (2026-10-02, 검토 2차 G05).
입력: output/exp16_milp_picks_{seoul|seoulT720|seoulT900}_{연도}.json. 출력: 표4.1-19_정확해_하위20.csv
사용: python exp16_low20.py"""
import json
import numpy as np, pandas as pd
from bundlelib import Ctx, State
from r1lib import OUT

rows = []; Ys = {}
for name, year, var in (("seoul", "2020", ""), ("seoul", "2025", ""), ("seoulT720", "2025", "T720"), ("seoulT900", "2025", "T900")):
    f = OUT / f"exp16_milp_picks_{name}_{year}.json"
    if not f.exists(): print("없음", f.name); continue
    J = json.load(open(f, encoding="utf-8")); ctx = Ctx("seoul", year, years=Ys, variant=var); Ys = ctx.Y
    for lab, picks in (("정수계획", J["MIP"]["picks"]), ("IND_정확해", J["IND"]["picks"])):
        st = State(ctx); st.B = {s: 10 ** 6 for s in ctx.SUB}
        for s, js in picks.items():
            for j in js: st.apply(int(j), [s])
        comp = (st.cnt == ctx.NC) & ctx.popped; pop = ctx.pop
        rows.append({"묶음": name, "year": year, "T": ctx.T, "해": lab, "완결률": (pop * comp).sum() / pop.sum(),
                     "하위20_완결률": (ctx.W20 * comp).sum() / ctx.W20.sum(), "결손집단_완결률": pop[ctx.POOR & comp].sum() / pop[ctx.POOR].sum(),
                     "결손집단_인구비중": ctx.POOR_share, "W20_alpha": ctx.W20_alpha, "W20_합/총인구": ctx.W20.sum() / pop.sum(), "사용": sum(len(v) for v in picks.values())})
        print(rows[-1], flush=True)
D = pd.DataFrame(rows); D.to_csv(OUT / "표4.1-19_정확해_하위20.csv", index=False, encoding="utf-8-sig"); print(D.round(4).to_string()); print("done")
