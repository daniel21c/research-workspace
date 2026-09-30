# -*- coding: utf-8 -*-
"""실험 15 (B2): Abbiasov 외 2024형 "15분 이용" vs "접근" — 동 단위.
이용(usage) = 출발 동의 비통근 생활이동(od-daily-v1: HW/WH 제외, 도착 09~20시) 중, 출발 동과 도착 동의 인구가중 중심 격자 간 보행시간 ≤ 15분인 통행 비율.
              (Abbiasov는 블록그룹 중심 15분 등시선 안 필수시설로 간 통행 비율. 우리는 목적지 시설을 모르므로 "15분 안 동으로 간 비통근 통행"으로 근사)
접근(access) = 동 인구 중 (a) Logan형 7범주 15분 완결 비율, (b) 평균 도달 범주 수, (c) 서울 계획 6분야 10분 완결 비율.
출력: 동별 표, 상관(스피어만), 구·생활권 단위 집계 상관, 밀도 통제 부분상관.
사용: python exp15_usage.py <연도>"""
import sys, time
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from r1lib import Year, OUT, X, md

year = sys.argv[1] if len(sys.argv) > 1 else "2020"; t0 = time.time()
Yr = Year(year, tmax=1800); pop = Yr.pop; n = len(Yr.M); popped = Yr.popped
ud = Yr.units["동"]; dong_codes = pd.factorize(Yr.M.dong)[1]
# 동 인구가중 중심 → 가장 가까운 인구 격자
cx = np.bincount(ud, pop * Yr.M.x_c) / np.maximum(np.bincount(ud, pop), 1); cy = np.bincount(ud, pop * Yr.M.y_c) / np.maximum(np.bincount(ud, pop), 1)
cent = np.empty(len(dong_codes), int)
for k in range(len(dong_codes)):
    m = np.where((ud == k) & popped)[0]; cent[k] = m[np.argmin((Yr.M.x_c.to_numpy()[m] - cx[k]) ** 2 + (Yr.M.y_c.to_numpy()[m] - cy[k]) ** 2)] if len(m) else -1
# 중심 격자 간 보행시간 행렬 (≤ 1,800초 간선)
g2d = {g: k for k, g in enumerate(cent) if g >= 0}
isC = np.zeros(n, bool); isC[cent[cent >= 0]] = True
m = isC[Yr._o_all] & isC[Yr._d_all]; o, d, t = Yr._o_all[m], Yr._d_all[m], Yr._t_all[m]
TT = np.full((len(dong_codes), len(dong_codes)), 99999.0)
for a, b, s in zip(o, d, t): TT[g2d[a], g2d[b]] = min(TT[g2d[a], g2d[b]], s)
np.fill_diagonal(TT, 0)
# OD
od = Yr.od.copy(); pos = pd.Series(np.arange(len(dong_codes)), index=dong_codes)
od = od[od.dong_O.isin(pos.index) & od.dong_D.isin(pos.index)]
oi = pos.reindex(od.dong_O).to_numpy(); di = pos.reindex(od.dong_D).to_numpy(); fl = od.flow.to_numpy()
tt = TT[oi, di]; tot = np.bincount(oi, fl, minlength=len(dong_codes)); loc = np.bincount(oi, fl * (tt <= 900), minlength=len(dong_codes))
loc_ex = np.bincount(oi, fl * ((tt <= 900) & (oi != di)), minlength=len(dong_codes)); tot_ex = np.bincount(oi, fl * (oi != di), minlength=len(dong_codes))
usage = np.divide(loc, tot, out=np.full(len(dong_codes), np.nan), where=tot > 0); usage_ex = np.divide(loc_ex, tot_ex, out=np.full(len(dong_codes), np.nan), where=tot_ex > 0)
# 접근
Yr.use_T(900); CATS = ["교육", "문화", "보육·복지", "생활서비스", "소매", "의료", "행정·안전"]
R = []
for c in CATS:
    g = Yr.F[Yr.F.cat_A == c].grid100_cd.dropna().unique(); Yr.fac["_c"] = (Yr.gix.reindex(g).dropna().astype(int).to_numpy(), 900); R.append(Yr.reach("_c"))
R = np.vstack(R); cnt = R.sum(0); comp = (cnt == 7) & popped
Yr.use_T(600)
SEO = []
for name, idx in (("공원", Yr.fac["공원"][0]), ("도서관", Yr.fac["도서관"][0]), ("노인", Yr.fac["노인이용시설"][0]),
                  ("청소년아동", np.union1d(Yr.fac["청소년수련시설"][0], Yr.fac["지역아동센터"][0])),
                  ("보육", Yr.gix.reindex(Yr.F[Yr.F["시설"] == "어린이집"].grid100_cd.dropna().unique()).dropna().astype(int).to_numpy()), ("공공체육", Yr.fac["공공체육"][0])):
    Yr.fac["_s"] = (np.unique(idx), 600); SEO.append(Yr.reach("_s"))
seo = np.vstack(SEO).all(0) & popped
den = np.bincount(ud, pop); v = den > 0
acc_comp = np.bincount(ud, pop * comp) / np.maximum(den, 1); acc_cnt = np.bincount(ud, pop * cnt) / np.maximum(den, 1); acc_seo = np.bincount(ud, pop * seo) / np.maximum(den, 1)
area = X.load_dong().set_index("Dong").geometry.area.reindex(dong_codes).to_numpy() / 1e6; dens = np.log(den / np.maximum(area, 1e-6) + 1)
D = pd.DataFrame({"year": year, "dong": dong_codes, "pop": den, "15분이용": usage, "15분이용_자기동제외": usage_ex, "접근_7범주완결": acc_comp, "접근_평균범주수": acc_cnt, "접근_서울6분야10분": acc_seo, "log밀도": dens})
D = D[v & D["15분이용"].notna()]; D.to_csv(OUT / f"표4.1-17_이용vs접근_{year}.csv", index=False, encoding="utf-8-sig")
def resid(a, b):
    A = np.c_[np.ones(len(b)), b]; return a - A @ np.linalg.lstsq(A, a, rcond=None)[0]
rows = []
for u in ("15분이용", "15분이용_자기동제외"):
    for a in ("접근_7범주완결", "접근_평균범주수", "접근_서울6분야10분"):
        r, p = spearmanr(D[u], D[a]); rp, pp = spearmanr(resid(D[u].to_numpy(), D["log밀도"].to_numpy()), resid(D[a].to_numpy(), D["log밀도"].to_numpy()))
        rows.append({"year": year, "이용": u, "접근": a, "n": len(D), "ρ": round(r, 3), "p": round(p, 4), "ρ_밀도통제": round(rp, 3), "p_밀도통제": round(pp, 4)})
S = pd.DataFrame(rows)
w = D["pop"]; summ = f"서울 인구가중 15분 이용 {np.average(D['15분이용'], weights=w):.3f} (자기 동 제외 {np.average(D['15분이용_자기동제외'].fillna(0), weights=w):.3f}); 동 중앙값 {D['15분이용'].median():.3f}"
open(OUT / f"표4.1-17_이용vs접근_{year}.md", "w", encoding="utf-8").write(f"# 표 4.1-17 15분 이용 vs 접근 ({year}, 동 {len(D)})\n\n{summ}\n\n" + md(S, "{}"))
print(summ); print(S.to_string(index=False)); print("done", f"{time.time()-t0:.0f}s")
