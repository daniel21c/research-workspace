# -*- coding: utf-8 -*-
"""실험 6: 임계·격자 민감도 — 실험 1(4단위 K_min·효율·소외)과 실험 2(은폐 H)가 설정에 강건한가.
변형: (a) 도서관 임계 10분(T=600), (b) 보행 3.6 km/h(소요시간 × 4.0/3.6), (c) τ = 서울 평균 × 0.8 / 1.0 / 하위 20% 분위값.
250 m 격자·면적비 분할은 접근성 패키지 sens_grid250 결과 표로 대신 보고(배치 실험은 100 m 고정).
사용: python exp6_sensitivity.py [연도=2020]"""
import sys, time
import numpy as np, pandas as pd
from r1lib import Year, OUT, md

year = sys.argv[1] if len(sys.argv) > 1 else "2020"
K = 32; t0 = time.time(); rows = []
def wmedian(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return x[o][np.searchsorted(cw, cw[-1] / 2)]
Yr = Year(year); pop = Yr.pop
LEV = ("동", "공식LZ", "Leiden", "구")

def run_variant(label, r0, tau_rule):
    cand = Yr.candidates("도서관"); C0 = Yr.cov(r0)
    Cd, dd = Yr.unit_cov(Yr.units["동"], r0); v = dd > 0
    taus = {"중위60%": 0.6 * wmedian(Cd[v], dd[v]), "평균×0.8": 0.8 * C0, "평균×1.0": C0,
            "하위20%분위": float(np.quantile(np.repeat(Cd[v], np.maximum(1, (dd[v] / 1000).astype(int))), 0.2))}
    for tr in ([tau_rule] if tau_rule else taus):
        tau = min(taus[tr], 0.9999)
        p0, _, _ = Yr.place(r0, None, 0, K, cand); base = (pop * Yr.cov_after(r0, p0, K)).sum() - (pop * r0).sum()
        for lv in LEV:
            u = Yr.units[lv]; pk, kmin, _ = Yr.place(r0, u, tau, K, cand, kcap=700); cov = Yr.cov_after(r0, pk, K)
            Cu, den = Yr.unit_cov(u, cov); vv = den > 0
            Cu0, _ = Yr.unit_cov(u, r0); H = Yr.H(u, r0, tau)
            rows.append({"year": year, "변형": label, "τ규칙": tr, "τ": tau, "서울C": C0, "단위": lv, "K_min": kmin,
                         "효율유지율": ((pop * cov).sum() - (pop * r0).sum()) / base,
                         "자기단위_FGT0(기준)": den[vv & (Cu0 < tau)].sum() / den[vv].sum(), "자기단위_FGT0(후)": den[vv & (Cu < tau)].sum() / den[vv].sum(),
                         "H(τ)": H})
        print(label, tr, f"{time.time()-t0:.0f}s", flush=True)

run_variant("15분·4.0km/h(본)", Yr.reach("도서관"), None)
Yr.use_T(600); run_variant("10분", Yr.reach("도서관10분"), "중위60%"); Yr.use_T(900)
# 3.6 km/h: t' = t × 4.0/3.6 → 15분 안 = t ≤ 810초
idx, _ = Yr.fac["도서관"]; isf = np.zeros(len(Yr.M), bool); isf[idx] = True
m = isf[Yr.d] & (Yr.t <= 810); r36 = np.zeros(len(Yr.M), bool); r36[Yr.o[m]] = True
# place() 는 cover_of(j)=15분(900초) 도달권을 쓰므로 3.6 km/h 변형에서는 도달권도 810초로 좁혀야 한다
Yr.t_backup = Yr.t
mask = Yr.t <= 810; o2, d2, t2 = Yr.o[mask], Yr.d[mask], Yr.t[mask]
Yr.o, Yr.d, Yr.t = o2, d2, t2; n = len(Yr.M); Yr.starts = np.searchsorted(Yr.d, np.arange(n)); Yr.ends = np.searchsorted(Yr.d, np.arange(n), side="right")
run_variant("3.6km/h", r36, "중위60%")
D = pd.DataFrame(rows); D.to_csv(OUT / f"표4.1-6_민감도_{year}.csv", index=False, encoding="utf-8-sig")
piv = D.pivot_table(index=["변형", "τ규칙", "τ"], columns="단위", values=["K_min", "효율유지율", "자기단위_FGT0(후)", "H(τ)"])
out = f"# 표 4.1-6 민감도 ({year}, 도서관, K=32)\n"
for mname in ["K_min", "효율유지율", "자기단위_FGT0(후)", "H(τ)"]:
    out += f"\n## {mname}\n\n" + md(piv[mname][list(LEV)].round(3).reset_index(), "{}") + "\n"
open(OUT / f"표4.1-6_민감도_{year}.md", "w", encoding="utf-8").write(out); print(out); print("done", f"{time.time()-t0:.0f}s")
