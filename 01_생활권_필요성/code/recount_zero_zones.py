# -*- coding: utf-8 -*-
"""저장된 입지 해를 다시 적용해 0명 생활권 수·인구·완결률을 센다(새 최적화 없음; 2026-10-02 독립 검토 M01·M28, 검증 S2-3·S2-4 대응).
- 기본 층: 2020·2025 배치 전, 묶음 최대화(exp16 MIP), 시설별 정확해(exp16 IND), 조정 P=2(exp14), 생활권 5%(exp20 4시간), 자치구 5%(exp20),
  exp21 2단계(최저선을 지키는 총량 최대화) 해가 있으면 함께.
- 문턱 변형: 2025 12분(T720)·15분(T900)의 배치 전·MIP·IND(exp16 T720/T900 저장 해).
- 공공체육 엄격 좌표(coord_valid_v2=True, Ctx variant "strict_sports"): 같은 저장 입지를 엄격 층에서 다시 평가(배치 전 완결률·0명 생활권·분야별 결손 비율 포함).
출력: results/재집계_0명생활권_인구_문턱_20261002.json (기본·문턱; 원고 4.1·4.2·4.3·4.4), results/재집계_공공체육엄격_20261002.json
실행: python recount_zero_zones.py"""
import json
import numpy as np, pandas as pd
from bundlelib import Ctx, State
from r1lib import OUT as RES

def stats(c, picks):
    st = State(c); st.B = {s: 10 ** 6 for s in c.SUB}
    for s, js in (picks or {}).items():
        for j in js: st.apply(int(j), [s])
    comp = (st.cnt == c.NC) & c.popped
    df = pd.DataFrame({"lz": c.Yr.M.lz.to_numpy(), "p": c.pop, "c": c.pop * comp}).groupby("lz").sum(); sh = df.c / df.p; z = sh <= 0
    return {"zero": int(z.sum()), "below5": int((sh < .05).sum()), "zero_pop_M": round(float(df.p[z].sum()) / 1e6, 3), "completion": round(float((c.pop * comp).sum() / c.pop.sum()), 4)}

def missing_shares(c):
    """배치 전 미완결 주민 가운데 분야별 결손 비율과 두 분야 이상 결손 비율"""
    nc = ~((c.R0.sum(axis=0) == c.NC)) & c.popped; w = c.pop * nc; tot = w.sum()
    out = {n: round(float((w * ~c.R0[k]).sum() / tot), 4) for k, (n, idx, subs) in enumerate(c.CATS)}
    out["two_plus"] = round(float((w * ((c.NC - c.R0.sum(axis=0)) >= 2)).sum() / tot), 4); return out

def load(name):
    p = RES / name; return json.load(open(p, encoding="utf-8")) if p.exists() else None

def rules(y):
    mj = load(f"exp16_milp_picks_seoul_{y}.json"); r = {"before": None, "MIP": mj["MIP"]["picks"], "IND": mj["IND"]["picks"],
         "P2": load(f"exp14_placements_seoul_{y}_p2.json")["COL_조정_무경계#0"], "LZ5": load(f"exp20_picks_{y}_공식LZ_long_0.05.json")["picks"],
         "gu5": load(f"exp20_picks_{y}_구_0.05.json")["picks"]}
    for tau in ("0.01", "0.05"):
        m = load(f"exp21_picks_{y}_공식LZ_max_{tau}.json")
        if m: r[f"LZ{int(float(tau) * 100)}_hard"] = m["picks"]
    return r

out = {}; strict = {}; Ys = {}
for y in ("2020", "2025"):
    c = Ctx("seoul", y, years=Ys); Ys = c.Y
    R = rules(y); out[y] = {k: stats(c, v) for k, v in R.items()}
    cs = Ctx("seoul", y, years=Ys, variant="strict_sports")
    strict[y] = {k: stats(cs, v) for k, v in R.items()}; strict[y]["missing_before"] = missing_shares(cs); out[y]["missing_before"] = missing_shares(c)
for v in ("T720", "T900"):
    c = Ctx("seoul", "2025", years=Ys, variant=v); mj = load(f"exp16_milp_picks_seoul{v}_2025.json")
    out[v] = {"before": stats(c, None), "MIP": stats(c, mj["MIP"]["picks"]), "IND": stats(c, mj["IND"]["picks"])}
json.dump(out, open(RES / "재집계_0명생활권_인구_문턱_20261002.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(strict, open(RES / "재집계_공공체육엄격_20261002.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"base": out, "strict": strict}, ensure_ascii=False, indent=1))
