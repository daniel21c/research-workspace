# -*- coding: utf-8 -*-
"""실험 9: 공공 시설 7종 각각에 대해 ①~④를 돌린다 (두 해).
① 보장 가능 창: 단위 수 k(구 25, 무작위 50·80·116·160·250, 동 424, 공식·Leiden 116)에 대해
   K_min(τ_main) 과 '구속력'(P0 배치 후 τ 미만 단위 거주 인구 비율 FGT0_P0)을 구한다.
   k_bind = FGT0_P0 ≥ 0.01 이 되는 최소 k(이보다 크면 하한이 P0 와 같은 답), k_afford = K_min ≤ K 인 최대 k.
② 반사실: 실제 2020→2025 신규 시설(격자) vs 같은 K 의 P0·P1 공식 — 도달 증가, 소외 생활권 FGT0(후), 소외 동 입지 비율.
③ 진단: 은폐 H(τ_main), 경계 제한 손실, 기준 상태 FGT0 — 4단위.
④ 관할: 시설 1개 도달권이 걸치는 단위 수.
K = 시설별 실제 2020→2025 증가분(시설 수). 탐욕법. 사용: python exp9_multi_facility.py [연도=2020] [무작위반복=8] [τ규칙=중위60%|평균60%|절대0.2]
τ규칙: 중위60% = 행정동 Coverage 인구가중 중위 × 0.6(본), 평균60% = 서울 Coverage × 0.6(Martens 계열 평균 비율), 절대0.2 = 고정 0.2. 극히 성긴 시설에서 상대 τ 가 0 에 가까워지는 문제의 보완."""
import sys, time, json
import numpy as np, pandas as pd
from r1lib import Year, OUT, md, PLACE_SETS

year = sys.argv[1] if len(sys.argv) > 1 else "2020"; R = int(sys.argv[2]) if len(sys.argv) > 2 else 8
TAU_RULE = sys.argv[3] if len(sys.argv) > 3 else "중위60%"; KMODE = sys.argv[4] if len(sys.argv) > 4 else "net"   # net = 격자 순증(본), new = 신규 입지 격자 수(감사 F2 민감도)
SUF = ("" if TAU_RULE == "중위60%" else f"_{TAU_RULE}") + ("" if KMODE == "net" else "_Knew")
rng = np.random.default_rng(20260928); t0 = time.time()
Y = {"2020": Year("2020"), "2025": Year("2025")}; Yr = Y[year]; pop = Yr.pop
KS = [50, 80, 116, 160, 250]
def wmedian(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return x[o][np.searchsorted(cw, cw[-1] / 2)]
win_rows, cf_rows, diag_rows = [], [], []
for fac in PLACE_SETS:
    n20, n25 = len(Y["2020"].fac[fac][0]), len(Y["2025"].fac[fac][0])
    # K = 시설 수 증가분(격자 수 기준; 시설 행 수와 거의 같음). 증가분이 0 이하이면 2020 수의 10% 로 대체하고 표시
    K = n25 - n20; K_note = "실제 증가분"
    if K < 3: K = max(3, int(round(0.1 * n20))); K_note = "증가분 부족→2020 수의 10%"
    if KMODE == "new": K = len(np.setdiff1d(Y["2025"].fac[fac][0], Y["2020"].fac[fac][0])); K_note = "신규 입지 격자 수"
    Yr.use_T(Yr.fac[fac][1])   # 감사 F1 교정: 시설별 임계로 간선 제한
    r0 = Yr.reach(fac); C0 = Yr.cov(r0); cand = Yr.candidates(fac)
    Cd, dd = Yr.unit_cov(Yr.units["동"], r0)
    tau = {"중위60%": 0.6 * wmedian(Cd[dd > 0], dd[dd > 0]), "평균60%": 0.6 * C0, "절대0.2": 0.2}[TAU_RULE]
    p0, _, _ = Yr.place(r0, None, 0, K, cand); cov0 = Yr.cov_after(r0, p0, K); base = (pop * cov0).sum() - (pop * r0).sum()
    def one(u, tag, k, rep):
        Cu, den = Yr.unit_cov(u, cov0); v = den > 0; fgt0_p0 = den[v & (Cu < tau)].sum() / den[v].sum()
        Cu0, _ = Yr.unit_cov(u, r0); fgt0_base = den[v & (Cu0 < tau)].sum() / den[v].sum()
        pk, kmin, sf = Yr.place(r0, u, tau, K, cand, kcap=max(700, 4 * K))
        c = Yr.cov_after(r0, pk, K); reff = ((pop * c).sum() - (pop * r0).sum()) / base if base > 0 else np.nan
        win_rows.append({"year": year, "시설": fac, "K": K, "τ": tau, "서울C": C0, "tag": tag, "k": k, "rep": rep, "n_units": int(v.sum()),
                         "FGT0_기준": fgt0_base, "FGT0_P0후": fgt0_p0, "K_min": kmin if kmin is not None else np.nan, "효율유지율": reff,
                         "손실": C0 - Yr.cov(Yr.reach(fac, u)), "H": Yr.H(u, r0, tau), "span": Yr.catchment_spans(u, fac) if tag in ("동", "공식LZ", "Leiden", "구") else np.nan})
    one(Yr.units["구"], "구", 25, 0); one(Yr.units["동"], "동", 424, 0); one(Yr.units["공식LZ"], "공식LZ", 116, 0); one(Yr.units["Leiden"], "Leiden", 116, 0)
    for k in KS:
        for rep in range(R): one(Yr.dong_series_to_units(Yr.random_partition(k, rng)), f"rand{k}", k, rep)
    # ② 반사실 (2020 기준만)
    if year == "2020":
        new = np.setdiff1d(Y["2025"].fac[fac][0], Yr.fac[fac][0]); new = [int(j) for j in new if Yr.ends[j] > Yr.starts[j]]  # use_T 적용된 간선 기준
        Ka = len(new)
        if Ka > 0:
            p0b, _, _ = Yr.place(r0, None, 0, Ka, cand); p1b, _, _ = Yr.place(r0, Yr.units["공식LZ"], tau, Ka, cand, kcap=max(700, 4 * Ka)); p1b = p1b[:Ka]
            Cl0, dl = Yr.unit_cov(Yr.units["공식LZ"], r0); vl = dl > 0; below_lz = vl & (Cl0 < tau); below_d = (dd > 0) & (Cd < tau)
            for lab, pk in (("실제", new), ("P0", p0b), ("P1 공식LZ", p1b)):
                c = Yr.cov_after(r0, pk, Ka); Cl, _ = Yr.unit_cov(Yr.units["공식LZ"], c)
                cf_rows.append({"시설": fac, "규칙": lab, "K": Ka, "도달증가": (pop * c).sum() - (pop * r0).sum(),
                                "소외생활권_FGT0(후)": dl[vl & (Cl < tau)].sum() / dl[vl].sum(), "소외생활권수(후)": int((vl & (Cl < tau)).sum()),
                                "소외동입지비율": float(np.mean(below_d[Yr.units["동"][pk]])), "소외생활권입지비율": float(np.mean(below_lz[Yr.units["공식LZ"][pk]]))})
    print(year, fac, f"K={K} ({K_note}) C={C0:.3f} τ={tau:.3f} {time.time()-t0:.0f}s", flush=True)
    pd.DataFrame(win_rows).to_csv(OUT / f"표4.1-9_시설별_창_{year}{SUF}.csv", index=False, encoding="utf-8-sig")
W = pd.DataFrame(win_rows); W.to_csv(OUT / f"표4.1-9_시설별_창_{year}{SUF}.csv", index=False, encoding="utf-8-sig")
if cf_rows: pd.DataFrame(cf_rows).to_csv(OUT / f"표4.1-9_시설별_반사실_2020{SUF}.csv", index=False, encoding="utf-8-sig")
# 요약: 시설별 창
rows = []
for fac in PLACE_SETS:
    d = W[W.시설 == fac]; K = int(d.K.iloc[0])
    def med(tag, col): v = d[d.tag == tag][col].astype(float).dropna(); return v.median() if len(v) else np.nan
    ks = [25] + KS + [424]; tags = ["구"] + [f"rand{k}" for k in KS] + ["동"]
    kmin = [med(t, "K_min") for t in tags]; bind = [med(t, "FGT0_P0후") for t in tags]
    k_afford = max([k for k, v in zip(ks, kmin) if not np.isnan(v) and v <= K], default=np.nan)
    k_bind = min([k for k, v in zip(ks, bind) if v >= 0.01], default=np.nan)
    o = d[d.tag == "공식LZ"].iloc[0]
    rows.append({"시설": fac, "K": K, "서울C": round(float(d.서울C.iloc[0]), 3), "τ": round(float(d.τ.iloc[0]), 3),
                 "k_bind(구속시작)": k_bind, "k_afford(예산한계)": k_afford, "116 안?": (not np.isnan(k_bind)) and (not np.isnan(k_afford)) and k_bind <= 116 <= k_afford,
                 "K_min 구/공식/Leiden/동": f"{med('구','K_min'):.0f} / {o.K_min:.0f} / {med('Leiden','K_min'):.0f} / {med('동','K_min'):.0f}",
                 "FGT0_P0후 구/공식/동": f"{med('구','FGT0_P0후'):.3f} / {o['FGT0_P0후']:.3f} / {med('동','FGT0_P0후'):.3f}",
                 "효율유지율 공식": round(float(o.효율유지율), 3), "H 동/공식/구": f"{med('동','H'):.2f} / {o.H:.2f} / {med('구','H'):.2f}",
                 "손실 동/공식/rand116/구": f"{med('동','손실'):.3f} / {o.손실:.3f} / {med('rand116','손실'):.3f} / {med('구','손실'):.3f}",
                 "span 동/공식/구": f"{med('동','span'):.1f} / {o.span:.1f} / {med('구','span'):.1f}"})
S = pd.DataFrame(rows); s = f"# 표 4.1-9 시설별 보장 가능 창 ({year}; 무작위 구획 {R}회 중앙값, 탐욕법)\n\n" + md(S, "{}")
if cf_rows: s += "\n\n## 반사실 (2020→2025 실제 vs 같은 K 의 P0·P1)\n\n" + md(pd.DataFrame(cf_rows).round(3), "{}")
open(OUT / f"표4.1-9_시설별_창_{year}{SUF}.md", "w", encoding="utf-8").write(s); print(s); print("done", f"{time.time()-t0:.0f}s")
