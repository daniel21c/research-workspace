# -*- coding: utf-8 -*-
"""실험 21: 권역 최저선의 실현 가능성 증명(2026-10-02, 독립 검토 E27·M02·M07 대응).
exp20은 목적이 "총량 완결 − M × 미달"이라 갭이 커서, 남은 0명 생활권이 계산 탓인지 구조 탓인지 말할 수 없었다.
여기서는 총량 완결을 목적에서 빼고 장소 목표만 최소화한다(사전식 1단계). 제약·추가량·후보지는 exp20과 같다.
  mode=zero : min Σ_u y_u,  Σ_{i∈I∩u} z_i + y_u ≥ 1 (배치 전 완결자가 없는 구역 u), y_u ∈ {0,1}
              → 완결 주민이 한 명도 없는 구역 수의 최솟값. z_i ≤ 빠진 분야마다 피복 합(정수)이므로 z_i > 0 이면 그 격자는 완결된다.
  mode=max  : 2단계. min −Σ p_i z_i,  base_u + Σ_{i∈I∩u} p_i z_i ≥ τ_u pop_u (모든 구역, 미달 허용 없음) → 최저선을 모두 지키는 해의 최대 완결률과 그 상한.
  mode=short: min Σ_u pop_u d_u,  base_u + Σ_{i∈I∩u} p_i z_i + pop_u d_u ≥ τ_u pop_u, d_u ≥ 0
              → 최저선 미달 인구의 최솟값. 0이면 모든 구역이 τ를 채울 수 있고, 하한 > 0 이면 채울 수 없음이 증명된다.
출력: exp21_row_*.json(실행별) → results/표4.1-24_최저선증명.csv(합본), exp21_picks_{연도}_{단위}_{mode}_{τ}.json
사용: python exp21_floor_proof.py <연도> <단위: 공식LZ|Leiden|구|동|rand116_<seed>> <zero|short> <τ(short만)> [시간제한초=7200]"""
import sys, time, json
import numpy as np, pandas as pd
from scipy import sparse
from scipy.optimize import milp, LinearConstraint, Bounds
from bundlelib import Ctx, State
from r1lib import OUT

year, unit_name, mode = sys.argv[1], sys.argv[2], sys.argv[3]
tau = float(sys.argv[4]) if mode in ("short", "max") else 0.0
TL = float(sys.argv[5]) if len(sys.argv) > 5 else 7200.0
t0 = time.time()
ctx = Ctx("seoul", year); Yr = ctx.Yr; n = ctx.n; pop = ctx.pop; popped = ctx.popped; R0 = ctx.R0; NC = ctx.NC; Eo, Ed = ctx.Eo, ctx.Ed
if unit_name.startswith("rand116"):
    u = Yr.dong_series_to_units(Yr.random_partition(116, np.random.default_rng(int(unit_name.split("_")[1]))))
else:
    u = Yr.units[unit_name]
nu = u.max() + 1; pop_u = np.bincount(u, pop, minlength=nu); vu = pop_u > 0
comp0 = ctx.comp0; base_u = np.bincount(u, pop * comp0, minlength=nu)
SUBS = [(s, k, K, cand) for s, (k, K, cand) in ctx.SUB.items()]
fixed = [kk for kk in range(NC) if not any(k == kk for _, k, _, _ in SUBS)]
reachable = R0.copy()
for s, k, K, cand in SUBS:
    isc = np.zeros(n, bool); isc[cand] = True; reachable[k, Eo[isc[Ed]]] = True
I = np.where(popped & ~comp0 & np.all(R0[fixed], axis=0) & np.all(reachable, axis=0))[0]
iix = -np.ones(n, int); iix[I] = np.arange(len(I))
cnt_I = np.bincount(u[I], minlength=nu)
if mode == "zero":
    act = np.where(vu & (base_u <= 0))[0]                       # 배치 전 완결자가 없는 구역
    struct_empty = int(((cnt_I[act]) == 0).sum())                # 완결 가능한 격자가 아예 없는 구역(구조적으로 비어 있음)
else:
    cap_u = (base_u + np.bincount(u[I], pop[I], minlength=nu)) / np.maximum(pop_u, 1)
    tau_u = np.where(vu, np.minimum(tau, cap_u), 0.0); need_u = tau_u * pop_u - base_u
    act = np.where(vu & (need_u > 1e-9))[0]; struct_empty = int((vu & (cap_u < tau - 1e-9)).sum())
# 목적과 장소 제약에 들어가는 것은 목표 구역의 격자뿐이다. 다른 격자의 z와 그 격자에만 닿는 후보지는 목적값에 영향이 없으므로 뺀다(같은 문제의 축소).
if mode != "max":
    isact = np.zeros(nu, bool); isact[act] = True; I = I[isact[u[I]]]; iix = -np.ones(n, int); iix[I] = np.arange(len(I))
print(f"{year} {unit_name} {mode} τ={tau}: 구역 {int(vu.sum())}, 목표가 걸린 구역 {len(act)}, 구조적으로 불가능한 구역 {struct_empty}, 목표 구역의 완결 가능 격자 {len(I):,}", flush=True)
blocks = []; off = 0
for s, k, K, cand in SUBS:
    isc = np.zeros(n, bool); isc[cand] = True; sel = isc[Ed] & (iix[Eo] >= 0) & ~R0[k, Eo]
    jj = np.unique(Ed[sel]); col = -np.ones(n, int); col[jj] = off + np.arange(len(jj)); blocks.append((s, k, K, jj, off, col, Eo[sel], Ed[sel])); off += len(jj)
nX = off; nZ = len(I); nA = len(act) if mode != "max" else 0; nV = nX + nZ + nA
ri, rc, rv = [], [], []; r = 0
for k in range(NC):
    if k in fixed: continue
    need = I[~R0[k, I]]
    if len(need) == 0: continue
    rid = -np.ones(n, int); rid[need] = r + np.arange(len(need)); r += len(need)
    ri += list(rid[need]); rc += list(nX + iix[need]); rv += [1.0] * len(need)
    for s, kk, K, jj, o_, col, eo, ed in blocks:
        if kk != k: continue
        mm = rid[eo] >= 0; ri += list(rid[eo[mm]]); rc += list(col[ed[mm]]); rv += [-1.0] * int(mm.sum())
A1 = sparse.csr_matrix((rv, (ri, rc)), shape=(r, nV)); A1.sum_duplicates(); A1.data = np.where(A1.data > 0, 1.0, -1.0)
bud = sparse.lil_matrix((len(blocks), nV))
for b, (s, k, K, jj, o_, col, eo, ed) in enumerate(blocks): bud[b, o_:o_ + len(jj)] = 1
cons = [LinearConstraint(A1, -np.inf, 0), LinearConstraint(bud.tocsr(), 0, np.array([b[2] for b in blocks], float))]
aix = -np.ones(nu, int); aix[act] = np.arange(len(act)); Iu = aix[u[I]]; m = Iu >= 0
if mode == "zero":
    G = sparse.csr_matrix((np.r_[np.ones(int(m.sum())), np.ones(nA)], (np.r_[Iu[m], np.arange(nA)], np.r_[nX + np.where(m)[0], nX + nZ + np.arange(nA)])), shape=(nA, nV))
    cons.append(LinearConstraint(G, 1.0, np.inf))
    c = np.r_[np.zeros(nX + nZ), np.ones(nA)]; integ = np.r_[np.ones(nX), np.zeros(nZ), np.ones(nA)]; ub = np.ones(nV)
elif mode == "max":   # 2단계: 모든 구역이 τ_u를 반드시 채운다는 제약 아래 총량 완결 최대화
    G = sparse.csr_matrix((pop[I][m], (Iu[m], nX + np.where(m)[0])), shape=(len(act), nV))
    cons.append(LinearConstraint(G, need_u[act], np.inf))
    c = np.r_[np.zeros(nX), -pop[I]]; integ = np.r_[np.ones(nX), np.zeros(nZ)]; ub = np.ones(nV)
else:
    G = sparse.csr_matrix((np.r_[pop[I][m], pop_u[act]], (np.r_[Iu[m], np.arange(nA)], np.r_[nX + np.where(m)[0], nX + nZ + np.arange(nA)])), shape=(nA, nV))
    cons.append(LinearConstraint(G, need_u[act], np.inf))
    c = np.r_[np.zeros(nX + nZ), pop_u[act]]; integ = np.r_[np.ones(nX), np.zeros(nZ + nA)]; ub = np.r_[np.ones(nX + nZ), np.full(nA, np.inf)]
print(f"변수 x {nX:,} z {nZ:,} 목표 {nA}, 제약 {r + nA:,} ({time.time()-t0:.0f}s)", flush=True)
t1 = time.time()
res = milp(c, constraints=cons, integrality=integ, bounds=Bounds(0, ub), options={"time_limit": TL, "disp": False, "mip_rel_gap": 0.0})
gap = getattr(res, "mip_gap", None); bound = getattr(res, "mip_dual_bound", None)
print(f"상태 {res.status} {res.message[:70]} 값 {res.fun} 하한 {bound} 갭 {gap} ({time.time()-t1:.0f}s)", flush=True)
row = {"year": year, "단위": unit_name, "mode": mode, "τ": tau, "구역수": int(vu.sum()), "목표구역": nA, "구조적불가": struct_empty,
       "최적값": None if res.x is None else float(res.fun), "하한": None if bound is None else float(bound), "갭": gap, "status": int(res.status), "message": res.message[:80], "초": round(time.time() - t0), "시간제한": TL}
if res.x is not None:
    xs = np.round(res.x[:nX]) > 0.5; picks = {s: [int(j) for j in jj[xs[o_:o_ + len(jj)]]] for s, k, K, jj, o_, col, eo, ed in blocks}
    st = State(ctx); st.B = {s: 10 ** 6 for s in ctx.SUB}
    for s, js in picks.items():
        for j in js: st.apply(j, [s])
    comp = (st.cnt == NC) & popped; sh = np.divide(np.bincount(u, pop * comp, minlength=nu), pop_u, out=np.zeros(nu), where=vu)
    ulz = Yr.units["공식LZ"]; den = np.bincount(ulz, pop); vl = den > 0; shl = np.bincount(ulz, pop * comp)[vl] / den[vl]
    if mode == "max":
        ref = pd.read_csv(OUT / f"표4.1-19_묶음정수계획_seoul_{year}.csv").iloc[0]; base_tot = float((pop * comp0).sum())
        row.update({"총량최대_완결률": float(ref["MIP_현재해"]), "최저선비용_%p(해)": float((ref["MIP_현재해"] - (pop * comp).sum() / pop.sum()) * 100),
                    "최저선비용_%p(하한)": None if bound is None else float((ref["MIP_현재해"] - (base_tot - bound) / pop.sum()) * 100)})
    row.update({"단위내_0%권역(재평가)": int((vu & (sh <= 0)).sum()), "단위내_τ미달(재평가)": int((vu & (sh < tau - 1e-6)).sum()) if mode == "short" else None,
                "공식LZ_0%권역": int((shl <= 0).sum()), "완결률": float((pop * comp).sum() / pop.sum()), "사용": sum(len(v) for v in picks.values())})
    json.dump({"row": row, "picks": picks}, open(OUT / f"exp21_picks_{year}_{unit_name}_{mode}_{tau}.json", "w", encoding="utf-8"), ensure_ascii=False, default=float)
print(json.dumps(row, ensure_ascii=False, default=float), flush=True)
json.dump(row, open(OUT / f"exp21_row_{year}_{unit_name}_{mode}_{tau}.json", "w", encoding="utf-8"), ensure_ascii=False, default=float)
rows = [json.load(open(p_, encoding="utf-8")) for p_ in sorted(OUT.glob("exp21_row_*.json"))]   # 병렬 실행이 같은 파일을 덮지 않도록 실행별 JSON을 합쳐 다시 쓴다
pd.DataFrame(rows).to_csv(OUT / "표4.1-24_최저선증명.csv", index=False, encoding="utf-8-sig"); print("done")
