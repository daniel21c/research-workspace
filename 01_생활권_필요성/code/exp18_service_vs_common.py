# -*- coding: utf-8 -*-
"""실험 18 (C6): 서비스별 권역 vs 공통 권역.
질문: "서비스마다 따로 권역(학군·보건소 관할처럼)을 두면 되지, 왜 하나의 공통 권역인가?"
비교(같은 묶음·같은 추가 시설 수·같은 임계):
  S1 서비스별 권역 + 서비스별 하한: 배치 유형 s 마다 자기 권역(무작위 연접 구획, 권역 수 k_s = 그 범주 기존 시설 수 = "시설 1곳당 관할 1개", 25~424로 절단;
     10분 도달권 면적 기준은 모든 유형이 동보다 작아 424로 잘려 쓰지 않음)
     을 두고 유형별 도달 하한(τ_s = 그 유형 동 Coverage 인구가중 중위 × 0.6)을 먼저 채운 뒤 유형별 도달 최대화.
  S2 공통 권역 + 서비스별 하한: 같은 규칙, 모든 유형이 공식 생활권 116을 쓴다.
  S3 공통 권역 + 묶음 하한 + 조정(= exp14 FLOOR_공식).
  S4 무경계 조정(= COL, 기준).
평가: (i) 묶음 완결률·평균 범주 수·취약 20% 완결률, (ii) 점검 단위 수: 서비스별 권역 수의 합(S1) vs 116,
      (iii) 판정 단위 수: 인구 격자가 속한 (유형별 권역 조합)의 서로 다른 개수 = "이 동네는 하루가 완결되는가"를 한 단위로 판정하려면 필요한 단위 수,
      (iv) 공식 생활권 116 안에서 판정할 때 한 권역이 여러 서비스 권역에 걸쳐 쪼개지는 정도(권역당 평균 조합 수).
S1은 무작위 구획 R회(기본 5) 중앙값.
사용: python exp18_service_vs_common.py <seoul|logan7> <연도> [R=5]"""
import sys, time
import numpy as np, pandas as pd
from bundlelib import Ctx, State, ind_type, run_FLOOR, greedy_free, summarize
from r1lib import OUT, md

bundle = sys.argv[1]; year = sys.argv[2]; R = int(sys.argv[3]) if len(sys.argv) > 3 else 5; t0 = time.time(); rng = np.random.default_rng(20261003)
ctx = Ctx(bundle, year); Yr = ctx.Yr; pop = ctx.pop; popped = ctx.popped
def wmed(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return x[o][np.searchsorted(cw, cw[-1] / 2)]
ud = Yr.units["동"]; dd = np.bincount(ud, pop)
tau_s = {}; k_s = {}
area_pop = popped.sum()   # 인구 격자 수(100 m = 0.01 km²)
for s, (k, K, cand) in ctx.SUB.items():
    Cd = np.bincount(ud, pop * ctx.R0[k]) / np.maximum(dd, 1); tau_s[s] = 0.6 * wmed(Cd[dd > 0], dd[dd > 0])
    # 관할 논리: 시설 1곳당 권역 1개(학군·보건소 관할처럼) — 권역 수 = 그 유형 기존 시설 수(청소년아동은 청소년수련+지역아동센터), 25~424로 절단.
    kcat = ctx.CATS[k][1]; k_s[s] = int(np.clip(len(kcat), 25, 424))
print(f"{bundle} {year} τ_s {({s: round(v, 3) for s, v in tau_s.items()})} k_s {k_s}", flush=True)
ulz = Yr.units["공식LZ"]
def overlay_count(parts):
    key = np.zeros(len(pop), dtype=np.int64)
    for p in parts: key = key * 1000 + p
    return len(np.unique(key[popped]))
def lz_split(parts):
    key = np.zeros(len(pop), dtype=np.int64)
    for p in parts: key = key * 1000 + p
    df = pd.DataFrame({"lz": ulz[popped], "k": key[popped]}); return float(df.groupby("lz").k.nunique().mean())
rows = []
for i in range(R):
    parts = {s: Yr.dong_series_to_units(Yr.random_partition(k_s[s], rng)) for s in ctx.SUB}
    st = State(ctx)
    for s in ctx.SUB: ind_type(st, s, unit=parts[s], tau=tau_s[s])
    rows.append(summarize(st, {"방식": "S1_서비스별권역+서비스별하한", "rep": i, "점검단위수": sum(k_s.values()), "판정단위수": overlay_count(list(parts.values())), "생활권당_쪼개짐": lz_split(list(parts.values()))}))
    print("S1", i, {k: round(v, 4) if isinstance(v, float) else v for k, v in rows[-1].items()}, f"{time.time()-t0:.0f}s", flush=True)
st = State(ctx)
for s in ctx.SUB: ind_type(st, s, unit=ulz, tau=tau_s[s])
rows.append(summarize(st, {"방식": "S2_공통116+서비스별하한", "rep": 0, "점검단위수": 116, "판정단위수": 116, "생활권당_쪼개짐": 1.0}))
rows.append(summarize(run_FLOOR(ctx, ulz), {"방식": "S3_공통116+묶음하한+조정", "rep": 0, "점검단위수": 116, "판정단위수": 116, "생활권당_쪼개짐": 1.0}))
rows.append(summarize(greedy_free(State(ctx)), {"방식": "S4_무경계조정(COL)", "rep": 0, "점검단위수": np.nan, "판정단위수": np.nan, "생활권당_쪼개짐": np.nan}))
st = State(ctx)
for s in ctx.SUB: ind_type(st, s)
rows.append(summarize(st, {"방식": "S0_무경계서비스별(IND)", "rep": 0, "점검단위수": np.nan, "판정단위수": np.nan, "생활권당_쪼개짐": np.nan}))
D = pd.DataFrame(rows); D["bundle"] = bundle; D["year"] = year
D.to_csv(OUT / f"표4.1-21_서비스별vs공통권역_{bundle}_{year}.csv", index=False, encoding="utf-8-sig")
S = D.groupby("방식").median(numeric_only=True).drop(columns=["rep"])
open(OUT / f"표4.1-21_서비스별vs공통권역_{bundle}_{year}.md", "w", encoding="utf-8").write(
    f"# 표 4.1-21 서비스별 권역 vs 공통 권역 ({bundle}, {year}; 서비스별 권역 수 {k_s}; S1 무작위 {R}회 중앙값)\n\n" + md(S.round(4).reset_index(), "{}"))
print(S.round(4).to_string()); print("done", f"{time.time()-t0:.0f}s")
