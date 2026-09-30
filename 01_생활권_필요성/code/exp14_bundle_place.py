# -*- coding: utf-8 -*-
"""실험 14 (C1): 묶음 배치 실험 — 묶음 정의를 선행연구·제도로 (2026-10-01; 10-02 외부 검토 반영: bundlelib 의 정확 탐욕·결손집단·고정 평가 문턱).
묶음(bundle):
  seoul  — 서울 2030 생활권계획 지역생활권 생활서비스 7분야 중 주차장을 뺀 6분야를 참고해 연구자가 정의한 묶음. 완결 = 6분야 모두 보행 600초 안(AND).
           계획의 "보행 10분·반경 800 m" 를 그대로 재현한 것이 아니다(4 km/h 망 600초 ≈ 667 m; 800 m ≈ 720초는 exp19 의 T720 민감도).
           공원(고정) · 도서관(배치: 공공도서관) · 노인여가(배치: 노인 이용시설) · 청소년아동(도달 = 청소년수련∪지역아동센터, 배치: 청소년수련시설)
           · 보육(도달 = 어린이집 전체(민간 포함), 배치: 국공립어린이집) · 공공체육(배치: 공공체육, 부가 층 신뢰도 중).
  logan7 — Logan형 최댓값 정의, cat_A 7범주 15분. 공공이 놓는 것만 배치: 문화(공공도서관·공공문화시설), 행정·안전(주민센터). 나머지 고정.
각 배치 유형의 추가 수 K = 실제 2020→2025 시설 점유 격자 순증(3 미만이면 2020 수의 10%). 실제 신설 시설 수·동액 예산이 아니라 모형의 유형–입지 추가량이다.
방식: IND(유형별 독립 도달 최대화) / COL(경계 없는 묶음 조정, 정확 탐욕) / FLOOR_u(단위 평균 도달 범주 수 하한 → 조정) / ZONE_u(단위마다 중심 하나씩 순환 배분).
평가: 완결률, 평균 도달 범주 수, 결손집단(배치 전 도달 범주 수 ≤ cut, 동률 포함; 인구 비중 병기) 완결률, 정확한 하위 20%(분수 가중) 완결률,
      평가권역(Leiden·공식·동·구) 최저·미달·FGT0·Gini. 미달·FGT0 의 문턱은 사전 지정 하나(τ_eval = 이 실행 COL 완결률의 절반)를 모든 배치안에 같게 적용하고,
      예전 "배치안별 완결률 절반" 상대 문턱은 *_상대 열에 따로 둔다(검토 F05).
목적함수: f(c) = (c/NC)^P (P=4 본; 환경변수 P_EXP). 배치는 exp14_placements_{묶음}_{연도}.json 에 저장(C2·C3 입력).
사용: python exp14_bundle_place.py <seoul|logan7> <연도> [무작위반복=10]"""
import sys, time, os, json
import numpy as np, pandas as pd
from r1lib import OUT, md
from bundlelib import Ctx, State, greedy_free, run_IND, run_FLOOR, run_ZONE

bundle = sys.argv[1]; year = sys.argv[2]; R = int(sys.argv[3]) if len(sys.argv) > 3 else 10
P_EXP = float(os.environ.get("P_EXP", "4")); t0 = time.time(); rng = np.random.default_rng(20261001)
ctx = Ctx(bundle, year, P_EXP=P_EXP); Yr = ctx.Yr; pop = ctx.pop; popped = ctx.popped; NC = ctx.NC; SUB = ctx.SUB; T = ctx.T
Ktot = sum(v[1] for v in SUB.values())
print(f"{bundle} {year} T={T}s 범주 {ctx.names} 배치 {[(s, v[1]) for s, v in SUB.items()]} 합 {Ktot}; 기준 완결률 {Yr.cov(ctx.comp0):.4f} 평균범주 {(pop*ctx.cnt0).sum()/pop.sum():.3f}; "
      f"결손집단 cut≤{ctx.POOR_cut} 인구비중 {ctx.POOR_share:.4f} (하위20 분수가중 α={ctx.W20_alpha:.3f})", flush=True)
EVAL = {"Leiden": Yr.units["Leiden"], "공식": Yr.units["공식LZ"], "동": Yr.units["동"], "구": Yr.units["구"]}
def gini_w(x, w):
    o_ = np.argsort(x); x, w = x[o_], w[o_]; cw_ = np.cumsum(w); cx = np.cumsum(x * w)
    return 1 - 2 * np.sum(w * (cx - x * w / 2)) / (cw_[-1] * cx[-1]) if cx[-1] > 0 else np.nan

PLACED = {}; STATES = []
def evaluate(st, name, rep, tau_eval):
    PLACED[f"{name}#{rep}"] = st.placed
    comp = (st.cnt == NC) & popped; tau_rel = 0.5 * Yr.cov(comp)
    row = {"bundle": bundle, "year": year, "방식": name, "rep": rep, "완결률": Yr.cov(comp), "완결률_기준": Yr.cov(ctx.comp0), "평균범주수": (pop * st.cnt).sum() / pop.sum(),
           "완결-1이상": pop[popped & (st.cnt >= NC - 1)].sum() / pop.sum(),
           "결손집단_완결률": pop[ctx.POOR & comp].sum() / pop[ctx.POOR].sum(), "결손집단_평균범주수": (pop * st.cnt)[ctx.POOR].sum() / pop[ctx.POOR].sum(),
           "결손집단_인구비중": ctx.POOR_share, "결손집단_cut": ctx.POOR_cut, "하위20_완결률": (ctx.W20 * comp).sum() / ctx.W20.sum(),
           "사용": sum(SUB[s][1] - st.B[s] for s in SUB), "tau_eval": tau_eval, "tau_상대": tau_rel}
    allj = sum(st.placed.values(), []); uj, cj = np.unique(allj, return_counts=True)
    row["입지수"] = len(uj); row["입지당_시설"] = float(cj.mean()) if len(cj) else 0.0; row["다유형_입지수"] = int((cj >= 2).sum())
    for en, eu in EVAL.items():
        num = np.bincount(eu, pop * comp); den = np.bincount(eu, pop); v = den > 0; sh = np.divide(num, den, out=np.zeros_like(num), where=v)
        row[f"{en}_최저"] = sh[v].min(); row[f"{en}_Gini"] = gini_w(sh[v], den[v])
        row[f"{en}_미달수"] = int((v & (sh < tau_eval)).sum()); row[f"{en}_FGT0"] = den[v & (sh < tau_eval)].sum() / den[v].sum()
        row[f"{en}_미달수_상대"] = int((v & (sh < tau_rel)).sum()); row[f"{en}_FGT0_상대"] = den[v & (sh < tau_rel)].sum() / den[v].sum()
    if getattr(st, "floor_info", None): row.update(st.floor_info)
    return row

# 배치 먼저(문턱은 COL 완결률로 사전 지정한 뒤 모든 안에 같게 적용)
st_ind = run_IND(ctx); print("IND", f"{time.time()-t0:.0f}s", flush=True)
st_col = greedy_free(State(ctx)); print("COL", f"{time.time()-t0:.0f}s", flush=True)
tau_eval = 0.5 * Yr.cov((st_col.cnt == NC) & popped)
rows = [evaluate(st_ind, "IND_유형별독립", 0, tau_eval), evaluate(st_col, "COL_조정_무경계", 0, tau_eval)]
print("IND", round(rows[0]["완결률"], 4), "COL", round(rows[1]["완결률"], 4), "τ_eval", round(tau_eval, 4), flush=True)
for lv, tag in (("공식LZ", "공식"), ("Leiden", "Leiden"), ("동", "동"), ("구", "구")):
    rows.append(evaluate(run_FLOOR(ctx, Yr.units[lv]), f"FLOOR_{tag}", 0, tau_eval)); print("FLOOR", tag, round(rows[-1]["완결률"], 4), rows[-1].get("하한_미달권역_후"), f"{time.time()-t0:.0f}s", flush=True)
    rows.append(evaluate(run_ZONE(ctx, Yr.units[lv]), f"ZONE_{tag}", 0, tau_eval)); print("ZONE", tag, round(rows[-1]["완결률"], 4), f"{time.time()-t0:.0f}s", flush=True)
for i in range(R):
    up = Yr.dong_series_to_units(Yr.random_partition(116, rng))
    rows.append(evaluate(run_FLOOR(ctx, up), "FLOOR_무작위116", i, tau_eval)); rows.append(evaluate(run_ZONE(ctx, up), "ZONE_무작위116", i, tau_eval))
    print("rand", i, round(rows[-2]["완결률"], 4), round(rows[-1]["완결률"], 4), f"{time.time()-t0:.0f}s", flush=True)
D = pd.DataFrame(rows); D["tau_c"] = ctx.tau_c; D["P_EXP"] = P_EXP; D["T"] = T; D["K합"] = Ktot
suf = "" if P_EXP == 4 else f"_p{int(P_EXP)}"
D.to_csv(OUT / f"표4.1-18_묶음배치_{bundle}_{year}{suf}.csv", index=False, encoding="utf-8-sig")
json.dump({k: {s: v for s, v in d.items()} for k, d in PLACED.items()}, open(OUT / f"exp14_placements_{bundle}_{year}{suf}.json", "w", encoding="utf-8"), ensure_ascii=False)
S = D.groupby("방식").median(numeric_only=True)
cols = ["완결률", "평균범주수", "완결-1이상", "결손집단_완결률", "하위20_완결률", "입지수", "입지당_시설", "다유형_입지수", "Leiden_최저", "Leiden_미달수", "Leiden_FGT0", "Leiden_Gini", "동_FGT0", "하한_미달권역_후"]
open(OUT / f"표4.1-18_묶음배치_{bundle}_{year}{suf}.md", "w", encoding="utf-8").write(
    f"# 표 4.1-18 묶음 배치 ({bundle}, {year}, T={T}s, 추가 {Ktot}(유형별 점유 격자 순증); 기준 완결률 {Yr.cov(ctx.comp0):.4f}; 무작위 116 {R}회 중앙값)\n\n"
    f"결손집단 = 배치 전 도달 범주 수 ≤ {ctx.POOR_cut}(동률 포함, 인구의 {ctx.POOR_share:.1%}); 하위20 = 동률 구간 분수 가중(α={ctx.W20_alpha:.3f})의 정확한 하위 20%. "
    f"미달수·FGT0 문턱 τ_eval = {tau_eval:.4f}(COL 완결률의 절반, 모든 안에 동일). 하한(FLOOR)은 평균 도달 범주 수 하한 τ_c = {ctx.tau_c:.3f}이며 완결률 하한이 아니다.\n\n" + md(S[cols].round(4).reset_index(), "{}"))
print(S[cols].round(4).to_string()); print("done", f"{time.time()-t0:.0f}s")
