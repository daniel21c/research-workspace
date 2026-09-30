# -*- coding: utf-8 -*-
"""실험 10: 설계만 하고 돌리지 않은 항목들 (2026-09-30, 현행 facility-v1.4 / access-engine-v3.3 입력).
공공 시설 7종, K = 실제 2020→2025 격자 순증(exp9와 같음), τ = 행정동 Coverage 인구가중 중위 × 0.6.

과제(task):
  policy    — 정책 비교 + 독립 평가권역(코덱스 v4 서울판) + "권역으로 약속, 격자로 채움"(혼합) + 인구가중 하한(V0 D8)
              정책: P0, PG(λ=1,2: 격자 취약도 가중 도달), PL_공식, PL_Leiden, PD_동, PU_구, PL_무작위116(R회), HY_공식(PL_공식 + PG 채움),
                    HY_무작위116(R회), PLw_공식(인구가중 부족분)
              평가: 전체 COV, 취약 상위 20% 인구 도달률, 평가권역 R ∈ {Leiden, 공식, 동, 구} 에서 최저·τ 미달 수·FGT0·평균 부족분·인구 하위 절반 권역 평균
  stability — V0 H4 / Fable M7: 인구 교란(로그정규 σ=0.1, 10회) 뒤 선택 입지·우선 목록의 Jaccard
  exposure  — Fable M10: 15분 보행권(출발 격자 기준)이 단위 경계를 넘는 인구 비율 — 공식·Leiden·동·구·무작위 116(R회)
  shuffle   — 교수님 9/21 15:07 방식: 시설을 후보 격자에 무작위로 다시 뿌렸을 때도 공식 경계의 이용권 완결성 우위가 남는가(20회)
  handcalc  — V0 7.1 손계산 예제 단위시험
사용: python exp10_extra.py <task> <연도> [무작위반복=20]"""
import sys, time
import numpy as np, pandas as pd
from r1lib import Year, OUT, md, PLACE_SETS

task = sys.argv[1]; year = sys.argv[2] if len(sys.argv) > 2 else "2020"; R = int(sys.argv[3]) if len(sys.argv) > 3 else 20
t0 = time.time(); rng = np.random.default_rng(20260930)

def wmedian(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return x[o][np.searchsorted(cw, cw[-1] / 2)]

def handcalc():
    # V0 7.1: 8칸, 반경 1칸, A=1~4, B=5~8, 인구 50,50,50,50,4,4,6,6, 기존 시설 칸2, K=1, τ=0.8
    pop = np.array([50, 50, 50, 50, 4, 4, 6, 6.]); u = np.array([0, 0, 0, 0, 1, 1, 1, 1]); r0 = np.zeros(8, bool); r0[[0, 1, 2]] = True
    cover = {j: [x for x in (j - 1, j, j + 1) if 0 <= x < 8] for j in range(8)}
    rows = []
    for j in range(8):
        c = r0.copy(); c[cover[j]] = True
        Cu = np.bincount(u, pop * c) / np.bincount(u, pop); sf = np.maximum(0, 0.8 - Cu).sum()
        rows.append((j + 1, (pop * c).sum(), round(sf, 3), (pop * (c & ~r0)).sum()))
    p0 = max(rows, key=lambda r: r[1]); p1 = min(rows, key=lambda r: (r[2], -r[1]))
    assert p0[0] == 5 and p0[1] == 208 and p1[0] == 7 and p1[1] == 166, (p0, p1)
    assert p0[3] == 58 and p1[3] == 16
    print("handcalc PASS: P0=칸5(208, 취약 도달 58/70), P1=칸7(166, 취약 도달 16/70), R_eff=16/58")

if task == "handcalc": handcalc(); sys.exit()

Yr = Year(year); Y25 = Year("2025") if year == "2020" else Yr; Y20 = Year("2020") if year == "2025" else Yr
pop = Yr.pop
def K_of(fac):
    n20, n25 = len(Y20.fac[fac][0]), len(Y25.fac[fac][0]); K = n25 - n20
    return K if K >= 3 else max(3, int(round(0.1 * n20)))
PARTS = [Yr.dong_series_to_units(Yr.random_partition(116, rng)) for _ in range(R)]
EVAL = {"Leiden": Yr.units["Leiden"], "공식": Yr.units["공식LZ"], "동": Yr.units["동"], "구": Yr.units["구"]}

def jac(a, b):
    a, b = set(map(int, a)), set(map(int, b)); return len(a & b) / max(1, len(a | b))

if task == "policy":
    rows = []
    for fac in PLACE_SETS:
        Yr.use_T(Yr.fac[fac][1]); K = K_of(fac); r0 = Yr.reach(fac); cand = Yr.candidates(fac)
        Cd, dd = Yr.unit_cov(Yr.units["동"], r0); tau = 0.6 * wmedian(Cd[dd > 0], dd[dd > 0])
        v = Yr.vulnerability(r0); P20 = Yr.poor20(v); base = None
        def ev(name, picks, kmin, rep=0, extra=None):
            global base
            c = Yr.cov_after(r0, picks, K); g = (pop * c).sum() - (pop * r0).sum()
            row = {"year": year, "시설": fac, "K": K, "τ": tau, "정책": name, "rep": rep, "K_min": kmin, "가능": (kmin is not None and kmin <= K) if kmin != -1 else True,
                   "도달증가": g, "COV": Yr.cov(c), "취약20_도달률": (pop * c)[P20].sum() / pop[P20].sum()}
            for en, eu in EVAL.items():
                Cu, den = Yr.unit_cov(eu, c); vv = den > 0; small = vv & (den <= np.median(den[vv]))
                Cu0, _ = Yr.unit_cov(eu, r0)
                row[f"{en}_최저"] = Cu[vv].min(); row[f"{en}_미달수"] = int((vv & (Cu < tau)).sum())
                row[f"{en}_FGT0"] = den[vv & (Cu < tau)].sum() / den[vv].sum(); row[f"{en}_평균부족"] = np.maximum(0, tau - Cu[vv]).mean()
                row[f"{en}_소인구권역_COV증가"] = (Cu[small] - Cu0[small]).mean()
            if extra: row.update(extra)
            rows.append(row)
        p0, _, _ = Yr.place(r0, None, 0, K, cand); ev("P0", p0, -1)
        for lam in (1, 2):
            pg, _, _ = Yr.place(r0, None, 0, K, cand, w=1 + lam * v); ev(f"PG{lam}", pg, -1)
        kc = max(700, 4 * K)
        for lv, tag in (("공식LZ", "공식"), ("Leiden", "Leiden"), ("동", "동"), ("구", "구")):
            u = Yr.units[lv]; pk, km, _ = Yr.place(r0, u, tau, K, cand, kcap=kc); ev(f"PL_{tag}", pk, km)
        for lv, tag in (("공식LZ", "공식"), ("Leiden", "Leiden")):
            u = Yr.units[lv]; pk, km, _ = Yr.place(r0, u, tau, K, cand, kcap=kc, w=1 + v); ev(f"HY_{tag}", pk, km)
        u = Yr.units["공식LZ"]; den = np.bincount(u, pop); pk, km, _ = Yr.place(r0, u, tau, K, cand, kcap=kc, uw=den / den[den > 0].mean()); ev("PLw_공식", pk, km)
        for i, up in enumerate(PARTS):
            pk, km, _ = Yr.place(r0, up, tau, K, cand, kcap=kc); ev("PL_무작위116", pk, km, i)
            pk, km, _ = Yr.place(r0, up, tau, K, cand, kcap=kc, w=1 + v); ev("HY_무작위116", pk, km, i)
        print(year, fac, f"K={K} τ={tau:.3f} {time.time()-t0:.0f}s", flush=True)
        pd.DataFrame(rows).to_csv(OUT / f"표4.1-10_정책비교_{year}.csv", index=False, encoding="utf-8-sig")
    D = pd.DataFrame(rows)
    # 요약: 무작위는 중앙값, 공식의 무작위 분위
    S = []
    for fac in PLACE_SETS:
        d = D[D.시설 == fac]
        for pol in ["P0", "PG1", "PG2", "PL_공식", "PL_Leiden", "PL_동", "PL_구", "PLw_공식", "HY_공식", "HY_Leiden", "PL_무작위116", "HY_무작위116"]:
            x = d[d.정책 == pol]
            if x.empty: continue
            m = x.median(numeric_only=True)
            S.append({"시설": fac, "정책": pol, "K": int(m.K), "가능비율": x["가능"].mean(), "COV": m.COV, "취약20": m.취약20_도달률,
                      "Leiden_미달수": m.Leiden_미달수, "Leiden_평균부족": m.Leiden_평균부족, "Leiden_최저": m.Leiden_최저,
                      "공식_미달수": m.공식_미달수, "동_FGT0": m.동_FGT0, "Leiden_소인구증가": m.Leiden_소인구권역_COV증가})
    S = pd.DataFrame(S); S.to_csv(OUT / f"표4.1-10_정책비교_요약_{year}.csv", index=False, encoding="utf-8-sig")
    # 공식이 무작위 116 분포에서 어디에 있는가(평가권역 Leiden 기준, 작을수록 좋음)
    Q = []
    for fac in PLACE_SETS:
        d = D[D.시설 == fac]
        for a, b in (("PL_공식", "PL_무작위116"), ("HY_공식", "HY_무작위116")):
            o = d[d.정책 == a].iloc[0]; rr = d[d.정책 == b]
            for col in ("Leiden_미달수", "Leiden_평균부족", "Leiden_FGT0", "동_FGT0", "취약20_도달률", "COV"):
                Q.append({"시설": fac, "비교": f"{a} vs {b}", "지표": col, "공식": o[col], "무작위중앙": rr[col].median(), "분위(무작위<공식)": float((rr[col] < o[col]).mean())})
    Q = pd.DataFrame(Q); Q.to_csv(OUT / f"표4.1-10_공식vs무작위_{year}.csv", index=False, encoding="utf-8-sig")
    open(OUT / f"표4.1-10_정책비교_{year}.md", "w", encoding="utf-8").write(f"# 표 4.1-10 정책 비교 ({year})\n\n" + md(S.round(3), "{}") + "\n\n## 공식 vs 무작위 116 (평가권역 Leiden)\n\n" + md(Q.round(3), "{}"))
    print("done", f"{time.time()-t0:.0f}s")

elif task == "stability":
    rows = []
    for fac in PLACE_SETS:
        Yr.use_T(Yr.fac[fac][1]); K = K_of(fac); r0 = Yr.reach(fac); cand = Yr.candidates(fac)
        Cd, dd = Yr.unit_cov(Yr.units["동"], r0); tau = 0.6 * wmedian(Cd[dd > 0], dd[dd > 0])
        def run(popv):
            Yr.pop = popv; v = Yr.vulnerability(r0); out = {}
            out["P0"], _, _ = Yr.place(r0, None, 0, K, cand); out["PG1"], _, _ = Yr.place(r0, None, 0, K, cand, w=1 + v)
            for lv in ("공식LZ", "구", "동"): out[f"PL_{lv}"] = Yr.place(r0, Yr.units[lv], tau, K, cand, kcap=max(700, 4 * K))[0][:K]
            out["HY_공식LZ"] = Yr.place(r0, Yr.units["공식LZ"], tau, K, cand, kcap=max(700, 4 * K), w=1 + v)[0][:K]
            out["격자우선(취약20)"] = np.where(Yr.poor20(v))[0]
            for lv in ("동", "공식LZ", "구"):
                Cu, den = Yr.unit_cov(Yr.units[lv], r0); out[f"미달단위_{lv}"] = np.where((den > 0) & (Cu < tau))[0]
            return out
        pop0 = pop.copy(); B = run(pop0)
        for rep in range(10):
            pp = pop0 * rng.lognormal(0, 0.1, len(pop0)); pp[pop0 == 0] = 0
            Pt = run(pp)
            for k in B: rows.append({"year": year, "시설": fac, "rep": rep, "항목": k, "Jaccard": jac(B[k], Pt[k])})
        Yr.pop = pop0
        print(year, fac, f"{time.time()-t0:.0f}s", flush=True)
    D = pd.DataFrame(rows); D.to_csv(OUT / f"표4.1-11_교란안정성_{year}.csv", index=False, encoding="utf-8-sig")
    S = D.groupby(["시설", "항목"]).Jaccard.median().unstack(); S.to_csv(OUT / f"표4.1-11_교란안정성_요약_{year}.csv", encoding="utf-8-sig")
    open(OUT / f"표4.1-11_교란안정성_{year}.md", "w", encoding="utf-8").write(f"# 표 4.1-11 인구 교란(σ=0.1, 10회) 뒤 Jaccard 중앙값 ({year})\n\n" + md(S.round(3).reset_index(), "{}"))
    print("done", f"{time.time()-t0:.0f}s")

elif task == "exposure":
    Yr.use_T(900); rows = []
    def expo(u):
        cross = np.bincount(Yr.o, (u[Yr.o] != u[Yr.d]) & Yr.popped[Yr.d], minlength=len(pop)) > 0
        return (pop * cross).sum() / pop.sum()
    for lv in ("동", "공식LZ", "Leiden", "구"): rows.append({"year": year, "단위": lv, "rep": 0, "경계노출인구비율": expo(Yr.units[lv])})
    for i, up in enumerate(PARTS): rows.append({"year": year, "단위": "무작위116", "rep": i, "경계노출인구비율": expo(up)})
    D = pd.DataFrame(rows); D.to_csv(OUT / f"표4.1-12_경계노출_{year}.csv", index=False, encoding="utf-8-sig")
    r = D[D.단위 == "무작위116"].경계노출인구비율
    for lv in ("공식LZ", "Leiden"):
        x = D[D.단위 == lv].경계노출인구비율.iloc[0]; print(lv, round(x, 4), "무작위 중앙", round(r.median(), 4), "분위", float((r < x).mean()))
    print(D.groupby("단위").경계노출인구비율.median().round(4).to_string()); print("done")

elif task == "shuffle":
    rows = []
    for fac in PLACE_SETS:
        Yr.use_T(Yr.fac[fac][1]); idx0, T = Yr.fac[fac]; pool = np.union1d(Yr.candidates(fac), idx0)
        for rep in range(R + 1):
            idx = idx0 if rep == 0 else np.sort(rng.choice(pool, len(idx0), replace=False))
            Yr.fac[fac] = (idx, T); C = Yr.cov(Yr.reach(fac))
            lo = C - Yr.cov(Yr.reach(fac, Yr.units["공식LZ"])); ll = C - Yr.cov(Yr.reach(fac, Yr.units["Leiden"]))
            lr = [C - Yr.cov(Yr.reach(fac, up)) for up in PARTS[:10]]
            rows.append({"year": year, "시설": fac, "rep": rep, "실제배치": rep == 0, "C": C, "손실_공식": lo, "손실_Leiden": ll, "손실_무작위중앙": float(np.median(lr)),
                         "공식<무작위중앙": lo < np.median(lr), "Leiden<무작위중앙": ll < np.median(lr)})
        Yr.fac[fac] = (idx0, T)
        print(year, fac, f"{time.time()-t0:.0f}s", flush=True)
    D = pd.DataFrame(rows); D.to_csv(OUT / f"표4.1-13_시설섞기_{year}.csv", index=False, encoding="utf-8-sig")
    S = D[~D.실제배치].groupby("시설").agg(공식손실=("손실_공식", "median"), 무작위손실=("손실_무작위중앙", "median"), 공식우위비율=("공식<무작위중앙", "mean"), Leiden우위비율=("Leiden<무작위중앙", "mean"))
    A = D[D.실제배치].set_index("시설")[["손실_공식", "손실_무작위중앙"]].rename(columns={"손실_공식": "실제_공식손실", "손실_무작위중앙": "실제_무작위손실"})
    S = A.join(S); S.to_csv(OUT / f"표4.1-13_시설섞기_요약_{year}.csv", encoding="utf-8-sig")
    open(OUT / f"표4.1-13_시설섞기_{year}.md", "w", encoding="utf-8").write(f"# 표 4.1-13 시설 무작위 재배치 {R}회 ({year})\n\n" + md(S.round(3).reset_index(), "{}"))
    print(S.round(3).to_string()); print("done", f"{time.time()-t0:.0f}s")
