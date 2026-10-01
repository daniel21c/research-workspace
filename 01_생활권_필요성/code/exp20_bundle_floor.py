# -*- coding: utf-8 -*-
"""실험 20: 권역별 묶음 완결 하한(최저선) 정수계획 — "생활권마다 최저선을 걸면 비어 있던 생활권이 사라지는가, 그 비용은 얼마인가" (2026-10-02).
묶음: 서울 계획 대상 6분야(600초), 추가량 상한 = exp16 과 같음(유형별 점유 격자 순증).
정식화: max Σ_i p_i z_i − M Σ_u pop_u d_u
   z_i ≤ Σ_{s∈S(k)} Σ_j A^s_ij x_sj      (격자 i 의 빠진 배치 범주 k 마다; exp16 과 같음)
   base_u + Σ_{i∈I∩u} p_i z_i + pop_u d_u ≥ τ_u pop_u   (권역 u 마다; d_u ≥ 0 은 미달분)
   Σ_j x_sj ≤ K_s,  x ∈ {0,1}, z ∈ [0,1]
   τ_u = min(τ, 그 권역에서 구조적으로 가능한 최대 완결률). 공원(고정 범주)에 닿지 않는 격자는 어떤 배치로도 완결되지 않으므로 그 상한을 넘는 최저선은 요구하지 않는다.
   M(=50)은 권역 최저선을 먼저 채우고(미달 1명을 완결 50명보다 무겁게) 남는 추가량으로 총량을 최대화하게 하는 가중이다.
권역 단위: 공식 생활권 116, 이동 커뮤니티(Leiden) 116, 자치구 25, 행정동 424, 무작위 연접 116(반복).
출력: 표4.1-23_권역최저선_{연도}.csv(설정별 총 완결률·하위20·미달 권역·0% 생활권·최저선 비용), exp20_picks_{연도}_{단위}_{τ}.json
사용: python exp20_bundle_floor.py <연도> <단위: 공식LZ|Leiden|구|동|rand116_<seed>> <τ> [시간제한초=3600]"""
import sys, time, json, os
import numpy as np, pandas as pd
from scipy import sparse
from scipy.optimize import milp, LinearConstraint, Bounds
from bundlelib import Ctx, State
from r1lib import OUT

year = sys.argv[1]; unit_name = sys.argv[2]; tau = float(sys.argv[3]); TL = float(sys.argv[4]) if len(sys.argv) > 4 else 3600; M = 50.0; t0 = time.time()
ctx = Ctx("seoul", year); Yr = ctx.Yr; n = ctx.n; pop = ctx.pop; popped = ctx.popped; R0 = ctx.R0; NC = ctx.NC; Eo, Ed = ctx.Eo, ctx.Ed
if unit_name.startswith("rand116"):
    seed = int(unit_name.split("_")[1]); u = Yr.dong_series_to_units(Yr.random_partition(116, np.random.default_rng(seed)))
else:
    u = Yr.units[unit_name]
nu = u.max() + 1; pop_u = np.bincount(u, pop, minlength=nu); vu = pop_u > 0
comp0 = ctx.comp0; base = (pop * comp0).sum(); base_u = np.bincount(u, pop * comp0, minlength=nu); tot = pop.sum()
SUBS = [(s, k, K, cand) for s, (k, K, cand) in ctx.SUB.items()]
fixed = [kk for kk in range(NC) if not any(k == kk for _, k, _, _ in SUBS)]
reachable = R0.copy()
for s, k, K, cand in SUBS:
    isc = np.zeros(n, bool); isc[cand] = True; reachable[k, Eo[isc[Ed]]] = True
I = np.where(popped & ~comp0 & np.all(R0[fixed], axis=0) & np.all(reachable, axis=0))[0]
iix = -np.ones(n, int); iix[I] = np.arange(len(I))
cap_u = (base_u + np.bincount(u[I], pop[I], minlength=nu)) / np.maximum(pop_u, 1)   # 구조적 최대 완결률
tau_u = np.where(vu, np.minimum(tau, cap_u), 0.0)
need_u = tau_u * pop_u - base_u; act = np.where(vu & (need_u > 1e-9))[0]          # 최저선이 실제로 걸리는 권역
print(f"{year} {unit_name} τ={tau}: 권역 {int(vu.sum())}, 배치 전 미달 {int((vu & (base_u < tau*pop_u - 1e-9)).sum())}, 구조적 상한 < τ 인 권역 {int((vu & (cap_u < tau - 1e-9)).sum())}, 최저선 활성 {len(act)}; 완결 가능 격자 {len(I):,}", flush=True)
blocks = []; off = 0
for s, k, K, cand in SUBS:
    isc = np.zeros(n, bool); isc[cand] = True; sel = isc[Ed] & (iix[Eo] >= 0) & ~R0[k, Eo]
    jj = np.unique(Ed[sel]); col = -np.ones(n, int); col[jj] = off + np.arange(len(jj)); blocks.append((s, k, K, jj, off, col, Eo[sel], Ed[sel])); off += len(jj)
nX = off; nZ = len(I); nD = len(act); nV = nX + nZ + nD
rows_i, rows_c, rows_v = [], [], []; r = 0
for k in range(NC):
    if k in fixed: continue
    need = I[~R0[k, I]]
    if len(need) == 0: continue
    rid = -np.ones(n, int); rid[need] = r + np.arange(len(need)); r += len(need)
    rows_i += list(rid[need]); rows_c += list(nX + iix[need]); rows_v += [1.0] * len(need)
    for s, kk, K, jj, o_, col, eo, ed in blocks:
        if kk != k: continue
        mm = rid[eo] >= 0; rows_i += list(rid[eo[mm]]); rows_c += list(col[ed[mm]]); rows_v += [-1.0] * int(mm.sum())
A1 = sparse.csr_matrix((rows_v, (rows_i, rows_c)), shape=(r, nV)); A1.sum_duplicates(); A1.data = np.where(A1.data > 0, 1.0, -1.0)
bud = sparse.lil_matrix((len(blocks), nV))
for b, (s, k, K, jj, o_, col, eo, ed) in enumerate(blocks): bud[b, o_:o_ + len(jj)] = 1
bud = bud.tocsr(); Kv = np.array([b[2] for b in blocks], float)
cons = [LinearConstraint(A1, -np.inf, 0), LinearConstraint(bud, 0, Kv)]
if nD:
    aix = -np.ones(nu, int); aix[act] = np.arange(nD); Iu = aix[u[I]]; m = Iu >= 0
    Fl = sparse.csr_matrix((np.r_[pop[I][m], pop_u[act]], (np.r_[Iu[m], np.arange(nD)], np.r_[nX + np.where(m)[0], nX + nZ + np.arange(nD)])), shape=(nD, nV))
    cons.append(LinearConstraint(Fl, need_u[act], np.inf))
c = np.r_[np.zeros(nX), -pop[I], M * pop_u[act]]
ub = np.r_[np.ones(nX + nZ), np.full(nD, np.inf)]
print(f"변수 x {nX:,} z {nZ:,} d {nD}, 제약 {r + nD:,} ({time.time()-t0:.0f}s)", flush=True)
t1 = time.time(); mip = milp(c, constraints=cons, integrality=np.r_[np.ones(nX), np.zeros(nZ + nD)], bounds=Bounds(0, ub), options={"time_limit": TL, "disp": False, "mip_rel_gap": 0.002})
gap = getattr(mip, "mip_gap", None); print(f"MIP 갭 {gap} ({time.time()-t1:.0f}s) {mip.message[:60]}", flush=True)
if mip.x is None:
    print(json.dumps({"year": year, "단위": unit_name, "τ": tau, "status": int(mip.status), "message": mip.message[:80], "초": round(time.time() - t0)}, ensure_ascii=False)); sys.exit(2)
picks = {}
xs = np.round(mip.x[:nX]) > 0.5
for s, k, K, jj, o_, col, eo, ed in blocks: picks[s] = [int(j) for j in jj[xs[o_:o_ + len(jj)]]]
st = State(ctx); st.B = {s: 10 ** 6 for s in ctx.SUB}
for s, js in picks.items():
    for j in js: st.apply(j, [s])
comp = (st.cnt == NC) & popped; sh = np.divide(np.bincount(u, pop * comp, minlength=nu), pop_u, out=np.zeros(nu), where=vu)
ulz = Yr.units["공식LZ"]; den = np.bincount(ulz, pop); vl = den > 0; shl = np.bincount(ulz, pop * comp)[vl] / den[vl]
ref = pd.read_csv(OUT / f"표4.1-19_묶음정수계획_seoul_{year}.csv").iloc[0]
label = unit_name + os.environ.get("EXP20_TAG", "")
row = {"year": year, "단위": label, "τ": tau, "권역수": int(vu.sum()), "완결률": float((pop * comp).sum() / tot), "총량최대_완결률": float(ref["MIP_현재해"]),
       "최저선비용_%p": float((ref["MIP_현재해"] - (pop * comp).sum() / tot) * 100), "하위20_완결률": float((ctx.W20 * comp).sum() / ctx.W20.sum()),
       "배치전_미달권역": int((vu & (base_u < tau * pop_u - 1e-9)).sum()), "배치후_미달권역(τ)": int((vu & (sh < tau - 1e-6)).sum()), "배치후_미달권역(τ_u)": int((vu & (sh < tau_u - 1e-6)).sum()),
       "구조적상한<τ_권역": int((vu & (cap_u < tau - 1e-9)).sum()), "단위내_0%권역": int((vu & (sh <= 0)).sum()),
       "공식LZ_0%권역": int((shl <= 0).sum()), "공식LZ_5%미만": int((shl < 0.05).sum()), "사용": sum(len(v) for v in picks.values()), "갭": gap, "status": int(mip.status), "초": round(time.time() - t0), "시간제한": TL}
print(json.dumps(row, ensure_ascii=False, default=float), flush=True)
tag = f"{year}_{label}_{tau}"
json.dump({"row": row, "picks": picks}, open(OUT / f"exp20_picks_{tag}.json", "w", encoding="utf-8"), ensure_ascii=False, default=float)
f = OUT / f"표4.1-23_권역최저선_{year}.csv"
D = pd.read_csv(f) if f.exists() else pd.DataFrame()
D = pd.concat([D[~((D.get("단위") == label) & (D.get("τ") == tau))] if len(D) else D, pd.DataFrame([row])], ignore_index=True)
D.to_csv(f, index=False, encoding="utf-8-sig"); print("done")
