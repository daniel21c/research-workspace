# -*- coding: utf-8 -*-
"""실험 18 (C6): 서비스별 권역 vs 공통 권역. (2026-10-01; 10-02 외부 검토 F07·F08 반영: 요인 비교 추가, 단위 수 집계 분리)
질문: "서비스마다 따로 권역(학군·보건소 관할처럼)을 두면 되지, 왜 하나의 공통 권역인가?"
A. 관행 시나리오(권역 수·목적·하한이 함께 다른 복합 비교; 경계 단독 효과가 아님):
  S0 무경계 서비스별(IND).  S4 무경계 조정(COL).
  S1 서비스별 권역 + 서비스별 하한 + 독립: 유형 s 마다 자기 권역(무작위 연접 구획, k_s = 그 범주 기존 시설 수, 25~424 절단)에서 유형별 하한(τ_s = 동 Coverage 인구가중 중위 × 0.6) 후 도달 최대화.
  S2 공통 116 + 서비스별 하한 + 독립.  S3 공통 116 + 묶음 하한(평균 도달 범주 수 τ_c) + 조정(= exp14 FLOOR_공식).
B. 요인 비교(경계 효과 분리): 모든 유형 권역 수 116 고정, 하한 규칙 동일(서비스별 τ_s), 평가 동일.
  F1 서비스별 116(유형마다 다른 무작위 구획) + 독립   F2 공통 116(공식) + 독립
  F3 서비스별 116 + 조정(하한 채운 뒤 정확 탐욕)        F4 공통 116 + 조정
  R1/R3 공유 무작위 116(같은 생성기의 구획 하나를 전 유형이 공유) + 독립/조정 — F1/F3 과 짝지어 "공통화 여부"만의 효과(검토 2차 B1).
  경계 효과 = F2−F1(독립), F4−F3(조정), R1−F1·R3−F3(공유 여부만); 목적 효과 = F3−F1(서비스별), F4−F2(공통).
평가: 완결률·평균 범주 수·결손집단(동률 포함)·하위20(분수 가중) 완결률; 공식 116 에서 최저·미달수(τ_eval = S4 완결률 절반, 모든 안 동일).
단위 수는 세 가지로 나눠 센다(검토 F08): 고유 경계(구획) 수, 유형×권역 항목 수, 판정 단위 수(인구 격자가 속한 유형별 권역 조합의 개수).
  S1 의 판정 단위 수는 설계값에 크게 좌우된다(보육 k=424 면 동 단위 중첩이 424 를 만든다) → 관찰 결과가 아니라 설계의 산물로 표시.
S1·F1·F3 은 무작위 구획 R회(기본 5) 중앙값.
사용: python exp18_service_vs_common.py <seoul|logan7> <연도> [R=5]"""
import sys, time
import numpy as np, pandas as pd
from bundlelib import Ctx, State, ind_type, ind_floor, run_FLOOR, greedy_free, summarize
from r1lib import OUT, md

bundle = sys.argv[1]; year = sys.argv[2]; R = int(sys.argv[3]) if len(sys.argv) > 3 else 5; t0 = time.time(); rng = np.random.default_rng(20261003)
ctx = Ctx(bundle, year); Yr = ctx.Yr; pop = ctx.pop; popped = ctx.popped; NC = ctx.NC; NT = len(ctx.SUB)
def wmed(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return x[o][np.searchsorted(cw, cw[-1] / 2)]
ud = Yr.units["동"]; dd = np.bincount(ud, pop)
tau_s = {}; k_s = {}
for s, (k, K, cand) in ctx.SUB.items():
    Cd = np.bincount(ud, pop * ctx.R0[k]) / np.maximum(dd, 1); tau_s[s] = 0.6 * wmed(Cd[dd > 0], dd[dd > 0])
    kcat = ctx.CATS[k][1]; k_s[s] = int(np.clip(len(kcat), 25, 424))
print(f"{bundle} {year} τ_s {({s: round(v, 3) for s, v in tau_s.items()})} k_s {k_s}", flush=True)
ulz = Yr.units["공식LZ"]; den_lz = np.bincount(ulz, pop); v_lz = den_lz > 0
def overlay_count(parts):
    key = np.zeros(len(pop), dtype=np.int64)
    for p in parts: key = key * 1000 + p
    return len(np.unique(key[popped]))
def lz_split(parts):
    key = np.zeros(len(pop), dtype=np.int64)
    for p in parts: key = key * 1000 + p
    df = pd.DataFrame({"lz": ulz[popped], "k": key[popped]}); return float(df.groupby("lz").k.nunique().mean())
def ev(st, name, rep, units, boundary, objective, floor):
    """units: 유형별 구획 dict 또는 None(무경계)."""
    parts = list(units.values()) if units else []
    distinct = len({id(p) for p in parts}) if units else 0
    kk = {s: int(u.max() + 1) for s, u in units.items()} if units else {}
    r = summarize(st, {"방식": name, "rep": rep, "경계": boundary, "목적": objective, "하한": floor,
                       "고유경계수": distinct, "유형×권역_항목수": sum(kk.values()) if kk else np.nan,
                       "판정단위수": overlay_count(parts) if parts else np.nan, "생활권당_쪼개짐": lz_split(parts) if parts else np.nan})
    comp = (st.cnt == NC) & popped; sh = np.divide(np.bincount(ulz, pop * comp, minlength=len(den_lz)), den_lz, out=np.zeros_like(den_lz), where=v_lz)
    r["공식116_최저"] = float(sh[v_lz].min()); r["_sh"] = sh; return r
rows = []
# A. 관행 시나리오
st = State(ctx)
for s in ctx.SUB: ind_type(st, s)
rows.append(ev(st, "S0_무경계서비스별(IND)", 0, None, "무경계", "독립", "없음"))
st_col = greedy_free(State(ctx)); rows.append(ev(st_col, "S4_무경계조정(COL)", 0, None, "무경계", "조정", "없음"))
tau_eval = 0.5 * rows[-1]["완결률"]; print("S0", round(rows[0]["완결률"], 4), "S4", round(rows[1]["완결률"], 4), "τ_eval", round(tau_eval, 4), f"{time.time()-t0:.0f}s", flush=True)
for i in range(R):
    parts = {s: Yr.dong_series_to_units(Yr.random_partition(k_s[s], rng)) for s in ctx.SUB}
    st = State(ctx)
    for s in ctx.SUB: ind_type(st, s, unit=parts[s], tau=tau_s[s])
    rows.append(ev(st, "S1_서비스별권역(관행k)+서비스별하한+독립", i, parts, "서비스별(관행 k_s)", "독립", "서비스별"))
    print("S1", i, round(rows[-1]["완결률"], 4), f"{time.time()-t0:.0f}s", flush=True)
common = {s: ulz for s in ctx.SUB}
st = State(ctx)
for s in ctx.SUB: ind_type(st, s, unit=ulz, tau=tau_s[s])
rows.append(ev(st, "S2_공통116+서비스별하한+독립", 0, common, "공통 116", "독립", "서비스별"))
rows.append(ev(run_FLOOR(ctx, ulz), "S3_공통116+묶음하한+조정", 0, common, "공통 116", "조정", "묶음(평균 범주 수)"))
print("S2", round(rows[-2]["완결률"], 4), "S3", round(rows[-1]["완결률"], 4), f"{time.time()-t0:.0f}s", flush=True)
# B. 요인 비교 (k = 116 고정, 하한 규칙 동일)
for i in range(R):
    parts = {s: Yr.dong_series_to_units(Yr.random_partition(116, rng)) for s in ctx.SUB}
    st = State(ctx)
    for s in ctx.SUB: ind_type(st, s, unit=parts[s], tau=tau_s[s])
    rows.append(ev(st, "F1_서비스별116+서비스별하한+독립", i, parts, "서비스별(116)", "독립", "서비스별"))
    st = State(ctx)
    for s in ctx.SUB: ind_floor(st, s, parts[s], tau_s[s])
    rows.append(ev(greedy_free(st), "F3_서비스별116+서비스별하한+조정", i, parts, "서비스별(116)", "조정", "서비스별"))
    print("F1/F3", i, round(rows[-2]["완결률"], 4), round(rows[-1]["완결률"], 4), f"{time.time()-t0:.0f}s", flush=True)
    # 짝 비교(검토 2차 B1): 같은 무작위 생성기에서 하나를 전 유형이 공유(R1) vs 유형별 독립(F1·F3) — 공통화 여부만 다름
    shared = Yr.dong_series_to_units(Yr.random_partition(116, rng)); sh_units = {s: shared for s in ctx.SUB}
    st = State(ctx)
    for s in ctx.SUB: ind_type(st, s, unit=shared, tau=tau_s[s])
    rows.append(ev(st, "R1_공유무작위116+서비스별하한+독립", i, sh_units, "공유 무작위 116", "독립", "서비스별"))
    st = State(ctx)
    for s in ctx.SUB: ind_floor(st, s, shared, tau_s[s])
    rows.append(ev(greedy_free(st), "R3_공유무작위116+서비스별하한+조정", i, sh_units, "공유 무작위 116", "조정", "서비스별"))
    print("R1/R3", i, round(rows[-2]["완결률"], 4), round(rows[-1]["완결률"], 4), f"{time.time()-t0:.0f}s", flush=True)
rows.append(dict(rows[[r_["방식"] for r_ in rows].index("S2_공통116+서비스별하한+독립")], 방식="F2_공통116+서비스별하한+독립"))
st = State(ctx)
for s in ctx.SUB: ind_floor(st, s, ulz, tau_s[s])
rows.append(ev(greedy_free(st), "F4_공통116+서비스별하한+조정", 0, common, "공통 116", "조정", "서비스별"))
print("F4", round(rows[-1]["완결률"], 4), f"{time.time()-t0:.0f}s", flush=True)
for r_ in rows:
    sh = r_.pop("_sh"); r_["공식116_미달수"] = int((v_lz & (sh < tau_eval)).sum()); r_["tau_eval"] = tau_eval
D = pd.DataFrame(rows); D["bundle"] = bundle; D["year"] = year; D["tau_s"] = str({s: round(v, 3) for s, v in tau_s.items()}); D["k_s"] = str(k_s)
D.to_csv(OUT / f"표4.1-21_서비스별vs공통권역_{bundle}_{year}.csv", index=False, encoding="utf-8-sig")
S = D.groupby("방식").median(numeric_only=True).drop(columns=["rep"])
cols = ["완결률", "평균범주수", "결손집단_완결률", "하위20_완결률", "공식116_최저", "공식116_미달수", "고유경계수", "유형×권역_항목수", "판정단위수", "생활권당_쪼개짐"]
m = lambda k: S.loc[k, "완결률"]
Dr = D.set_index(["방식", "rep"])["완결률"]
pair = lambda a_, b_: [Dr[(a_, i)] - Dr[(b_, i)] for i in range(R)]
pr1 = pair("R1_공유무작위116+서비스별하한+독립", "F1_서비스별116+서비스별하한+독립"); pr3 = pair("R3_공유무작위116+서비스별하한+조정", "F3_서비스별116+서비스별하한+조정")
eff = pd.DataFrame([{"효과": "경계 공유(공유 무작위−유형별 무작위), 독립 [짝 중앙값; 최소~최대]", "완결률 차": float(np.median(pr1)), "범위": f"{min(pr1):+.4f}~{max(pr1):+.4f}"},
                    {"효과": "경계 공유(공유 무작위−유형별 무작위), 조정 [짝 중앙값; 최소~최대]", "완결률 차": float(np.median(pr3)), "범위": f"{min(pr3):+.4f}~{max(pr3):+.4f}"},
                    {"효과": "경계(공식 공통−유형별 무작위), 독립", "완결률 차": m("F2_공통116+서비스별하한+독립") - m("F1_서비스별116+서비스별하한+독립")},
                    {"효과": "경계(공식 공통−유형별 무작위), 조정", "완결률 차": m("F4_공통116+서비스별하한+조정") - m("F3_서비스별116+서비스별하한+조정")},
                    {"효과": "목적(조정−독립), 서비스별 116", "완결률 차": m("F3_서비스별116+서비스별하한+조정") - m("F1_서비스별116+서비스별하한+독립")},
                    {"효과": "목적(조정−독립), 공통 116", "완결률 차": m("F4_공통116+서비스별하한+조정") - m("F2_공통116+서비스별하한+독립")},
                    {"효과": "하한(묶음−서비스별), 공통 116·조정", "완결률 차": m("S3_공통116+묶음하한+조정") - m("F4_공통116+서비스별하한+조정")},
                    {"효과": "관행 복합(S3−S1)", "완결률 차": m("S3_공통116+묶음하한+조정") - m("S1_서비스별권역(관행k)+서비스별하한+독립")}])
open(OUT / f"표4.1-21_서비스별vs공통권역_{bundle}_{year}.md", "w", encoding="utf-8").write(
    f"# 표 4.1-21 서비스별 권역 vs 공통 권역 ({bundle}, {year}; 관행 k_s {k_s}; 무작위 구획 {R}회 중앙값; τ_eval {tau_eval:.4f})\n\n"
    "A 관행 시나리오(S)는 권역 수·목적·하한이 함께 달라 복합 비교이고, B 요인 비교(F)는 권역 수 116·하한 규칙을 고정해 경계와 목적을 따로 바꾼다. "
    "판정단위수는 유형별 권역의 중첩 개수로, 관행 k_s 의 설계값(예: 보육 424)에 좌우된다.\n\n" + md(S[cols].round(4).reset_index(), "{}") + "\n\n## 요인 효과(완결률 차, %p 아님·비율)\n\n" + md(eff.round(4), "{}"))
print(S[cols].round(4).to_string()); print(eff.round(4).to_string(index=False)); print("done", f"{time.time()-t0:.0f}s")
