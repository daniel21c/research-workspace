# -*- coding: utf-8 -*-
"""실험 19 (C4·C5): 시간 외 표본, 추가 시설 수 곡선, 자료·정의 민감도 — 서울 계획 묶음, IND vs COL(+FLOOR_공식).
C4a 시간 외 표본: 2020 자료(2019 인구·2020 망·2020 시설)로 만든 IND·COL 배치를, 2025 인구·2025 망 + 2020 기존 시설 위에서 평가.
C4b 추가 시설 수 곡선: 유형별 K × 0.5 · 1 · 2 (2020·2025).
C5 민감도(2020·2025): 공공체육 엄격 좌표만 / 공공체육 제외 / 지역아동센터 제외(청소년수련만) / 임계 15분 / 공원 = UPIS2024(2025만).
사용: python exp19_holdout_sens.py"""
import time, json
import numpy as np, pandas as pd
from bundlelib import Ctx, State, run_IND, run_FLOOR, greedy_free, summarize
from r1lib import OUT, md
t0 = time.time(); rows = []; Ys = {}
def both(ctx, tag, year, extra=None):
    ind = run_IND(ctx); col = greedy_free(State(ctx)); fl = run_FLOOR(ctx, ctx.Yr.units["공식LZ"])
    for name, st in (("IND", ind), ("COL", col), ("FLOOR_공식", fl)):
        r = summarize(st, {"실험": tag, "year": year, "방식": name}); r.update(extra or {}); rows.append(r)
    a, b = rows[-3], rows[-2]
    print(tag, year, f"IND {a['완결률']:.4f} COL {b['완결률']:.4f} 이득 {b['완결률']/a['완결률']-1:+.2%} 취약 {a['취약20_완결률']:.3f}->{b['취약20_완결률']:.3f}", f"{time.time()-t0:.0f}s", flush=True)
    return ind, col
# 기준(두 해)
base = {}
for y in ("2020", "2025"):
    c = Ctx("seoul", y, years=Ys); Ys = c.Y; base[y] = both(c, "기준", y)
# C4a 시간 외 표본
ch = Ctx("seoul", "2025", years=Ys, fac_year="2020")
ind20, col20 = base["2020"]
for name, st20 in (("IND(2020계획)", ind20), ("COL(2020계획)", col20)):
    st = State(ch); st.B = {s: 10 ** 6 for s in ch.SUB}
    for s, js in st20.placed.items():
        for j in js:
            if s in ch.SUB: st.apply(j, [s])
    rows.append(summarize(st, {"실험": "C4a_시간외표본(2020계획→2025인구·망)", "year": "2025평가", "방식": name}))
print("holdout", [(r["방식"], round(r["완결률"], 4)) for r in rows[-2:]], flush=True)
# C4b 추가 수 곡선
for y in ("2020", "2025"):
    for ks in (0.5, 2.0):
        both(Ctx("seoul", y, years=Ys, kscale=ks), f"C4b_추가수×{ks}", y, {"kscale": ks})
# C5 민감도
for y in ("2020", "2025"):
    for v in ("strict_sports", "no_sports", "no_childcenter", "T900"):
        both(Ctx("seoul", y, years=Ys, variant=v), f"C5_{v}", y)
both(Ctx("seoul", "2025", years=Ys, variant="upis_park"), "C5_upis_park", "2025")
D = pd.DataFrame(rows); D.to_csv(OUT / "표4.1-22_시간외표본_추가수_민감도_seoul.csv", index=False, encoding="utf-8-sig")
P = D.pivot_table(index=["실험", "year"], columns="방식", values=["완결률", "취약20_완결률", "평균범주수"]).round(4)
open(OUT / "표4.1-22_시간외표본_추가수_민감도_seoul.md", "w", encoding="utf-8").write("# 표 4.1-22 시간 외 표본·추가 수·민감도 (서울 계획 묶음)\n\n" + md(P.reset_index(), "{}"))
print(P.to_string()); print("done", f"{time.time()-t0:.0f}s")
