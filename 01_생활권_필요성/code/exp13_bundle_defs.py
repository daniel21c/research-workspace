# -*- coding: utf-8 -*-
"""실험 13: "하루 묶음" 완결을 선행연구·제도의 정의로 잰다 (2026-10-01; `묶음정의_선행연구대조_20261001.md`).
정의:
  logan7  — Logan 외 2022 형: 범주별 최근접 보행시간의 최댓값 x* (범주 = cat_A 7). x* ≤ 10/15/20분 인구 비율(누적분포).
  abb8    — 같은 최댓값 정의, 범주는 Abbiasov 외 2024 9종 대응(식료품소매·음식점·생활서비스·의료·약국·학교·문화·행정; 공원·종교 없음).
  bruno7  — Bruno 외 2024 형: 범주별 최근접 k=20개 평균시간의 범주 평균 PT; PT ≤ 15 비율과 셀 간 Gini(인구 가중).
  seoul7  — 서울 2030 생활권계획 지역생활권 생활서비스시설(자료 있는 것): 도서관·노인여가복지·청소년아동복지·보육(어린이집)·문화시설(권역)·보건소(권역); 공원·주차장·공공체육 없음.
            임계 = 보행 10분(600초, 계획의 800 m 기준) 본, 15분 보조. 최댓값 정의.
사용: python exp13_bundle_defs.py <연도>   (간선 ≤ 1,200초 적재)"""
import sys, time
import numpy as np, pandas as pd
from r1lib import Year, OUT, md

year = sys.argv[1] if len(sys.argv) > 1 else "2020"; t0 = time.time()
Yr = Year(year, tmax=1200); pop = Yr.pop; n = len(Yr.M); popped = Yr.popped; F = Yr.F
INF = 10_000
def gini_w(x, w):
    o = np.argsort(x); x, w = x[o], w[o]; cw = np.cumsum(w); cx = np.cumsum(x * w)
    return 1 - 2 * np.sum(w * (cx - x * w / 2)) / (cw[-1] * cx[-1]) if cx[-1] > 0 else np.nan
def fac_idx(sel):
    g = F[sel(F)].grid100_cd.dropna().unique(); return Yr.gix.reindex(g).dropna().astype(int).to_numpy()
def nearest_time(idx, k=1):
    """격자별 시설 집합 idx 까지 최근접 k개 평균 보행시간(초). 없으면 INF."""
    isf = np.zeros(n, bool); isf[np.unique(idx)] = True
    m = isf[Yr._d_all]; o, t = Yr._o_all[m], Yr._t_all[m]
    order = np.lexsort((t, o)); o, t = o[order], t[order]
    out = np.full(n, float(INF))
    if k == 1:
        first = np.r_[True, o[1:] != o[:-1]]; out[o[first]] = t[first]
    else:
        # 각 o 안 순위
        starts = np.r_[0, np.flatnonzero(o[1:] != o[:-1]) + 1]; rank = np.arange(len(o)) - np.repeat(starts, np.diff(np.r_[starts, len(o)]))
        mk = rank < k; s = np.bincount(o[mk], t[mk], minlength=n); c = np.bincount(o[mk], minlength=n); v = c > 0; out[v] = s[v] / c[v]
    return out

CATS_A = ["교육", "문화", "보육·복지", "생활서비스", "소매", "의료", "행정·안전"]
ABB8 = {"식료품소매": lambda f: f.cat_A == "소매", "음식점": lambda f: f["시설"].isin(["일반음식점", "휴게음식점"]),
        "생활서비스": lambda f: f["시설"].isin(["미용업", "이용업", "세탁업", "목욕장업"]), "의료": lambda f: f["시설"].isin(["의원", "병원급", "응급의료기관", "보건소·보건지소"]),
        "약국": lambda f: f["시설"] == "약국", "학교": lambda f: f["시설"] == "학교", "문화": lambda f: f.cat_A == "문화", "행정": lambda f: f.cat_A == "행정·안전"}
# 서울 지역생활권 7분야 중 자료 있는 4(공원·주차장·공공체육 없음). 권역생활권 4분야(문화시설·장애인복지·주민복지·보건소)는 권역 5개 단위라 보행 기준이 없어 별도 15분 참고.
SEOUL7 = {"도서관": lambda f: f["시설"] == "공공도서관", "노인여가복지": lambda f: f["시설"] == "노인 이용시설", "청소년아동복지": lambda f: f["시설"] == "청소년수련시설",
          "보육": lambda f: f["시설"] == "어린이집"}
SEOUL_R = {"문화시설(권역)": lambda f: (f["시설"] == "문화기반시설") & ~f["시설_세부"].str.contains("도서관", na=False), "장애인복지(권역)": lambda f: f["시설"] == "장애인 이용시설",
           "주민복지(권역)": lambda f: f["시설"] == "가족센터(자치구 본소)", "보건소(권역)": lambda f: f["시설"] == "보건소·보건지소"}

def add_idx(lay):
    return Yr.fac[lay][0] if lay in Yr.fac else np.array([], int)
# 서울 2030 생활권계획 지역생활권 7분야(주차장 제외 6): 공원·도서관·노인여가·청소년아동(청소년수련+지역아동센터)·보육(어린이집)·공공체육
SEOUL_FULL = {"공원": lambda: add_idx("공원"), "도서관": lambda: fac_idx(lambda f: f["시설"] == "공공도서관"),
              "노인여가복지": lambda: fac_idx(lambda f: f["시설"] == "노인 이용시설"),
              "청소년아동복지": lambda: np.union1d(fac_idx(lambda f: f["시설"] == "청소년수련시설"), add_idx("지역아동센터")),
              "보육": lambda: fac_idx(lambda f: f["시설"] == "어린이집"), "공공체육": lambda: add_idx("공공체육")}
LOGAN4 = {"약국": lambda: fac_idx(lambda f: f["시설"] == "약국"), "슈퍼마켓": lambda: fac_idx(lambda f: f["시설"].isin(["대규모점포(주요4업태)", "식료품소매(즉석판매·제과)"])),
          "공원": lambda: add_idx("공원"), "초등학교": lambda: fac_idx(lambda f: (f["시설"] == "학교") & f["시설_세부"].str.startswith("초등학교", na=False))}
rows = []; curves = []; miss = []
def missdist(name, NTd, T):
    k = np.vstack([v > T for v in NTd.values()]).sum(0); inc = popped & (k > 0)
    row = {"year": year, "정의": name, "임계(분)": T // 60, "미완결인구비율": (pop * inc).sum() / pop.sum()}
    for m in range(1, len(NTd) + 1): row[f"결손{m}개"] = (pop * (inc & (k == m))).sum() / max((pop * inc).sum(), 1)
    for c, v in NTd.items(): row[f"결손포함_{c}"] = (pop * (inc & (v > T))).sum() / max((pop * inc).sum(), 1)
    miss.append(row)
def report(name, xstar, thresholds, note=""):
    for T in thresholds:
        c = (xstar <= T) & popped
        row = {"year": year, "정의": name, "임계(분)": T // 60, "완결률": (pop * c).sum() / pop.sum(), "비고": note}
        for en, eu in (("동", Yr.units["동"]), ("공식", Yr.units["공식LZ"]), ("Leiden", Yr.units["Leiden"]), ("구", Yr.units["구"])):
            num = np.bincount(eu, pop * c); den = np.bincount(eu, pop); v = den > 0; sh = np.divide(num, den, out=np.zeros_like(num), where=v)
            row[f"{en}_최저"] = sh[v].min(); row[f"{en}_Gini"] = gini_w(sh[v], den[v]); row[f"{en}_미달(<50%)수"] = int((v & (sh < 0.5)).sum())
        rows.append(row)
    for T in range(0, 1201, 60): curves.append({"year": year, "정의": name, "분": T // 60, "완결률": (pop * ((xstar <= T) & popped)).sum() / pop.sum()})

# logan7
NT = {c: nearest_time(fac_idx(lambda f, c=c: f.cat_A == c)) for c in CATS_A}
x = np.max(np.vstack([NT[c] for c in CATS_A]), axis=0); report("logan7_최댓값(cat_A 7)", x, (600, 900, 1200))
binding = {c: (pop * ((NT[c] > 900) & popped & (x > 900))).sum() / max((pop * ((x > 900) & popped)).sum(), 1) for c in CATS_A}
# abb8
NT8 = {c: nearest_time(fac_idx(sel)) for c, sel in ABB8.items()}
x8 = np.max(np.vstack(list(NT8.values())), axis=0); report("abb8_최댓값(Abbiasov 9종 대응, 공원·종교 없음)", x8, (600, 900, 1200))
# bruno7 (k=20 평균의 범주 평균)
NT20 = {c: nearest_time(fac_idx(lambda f, c=c: f.cat_A == c), k=20) for c in CATS_A}
pt = np.mean(np.vstack([np.minimum(NT20[c], 1200) for c in CATS_A]), axis=0); report("bruno7_평균PT(k=20)", pt, (900,), note="1,200초 초과는 1,200으로 절단")
pt_gini = gini_w(pt[popped], pop[popped])
# seoul7
NTS = {c: nearest_time(fac_idx(sel)) for c, sel in SEOUL7.items()}
xs = np.max(np.vstack(list(NTS.values())), axis=0); report("seoul_지역생활권서비스(4분야: 도서관·노인여가·청소년아동·보육; 공원·주차·체육 없음)", xs, (600, 900))
xs3 = np.max(np.vstack([NTS[c] for c in ("도서관", "노인여가복지", "보육")]), axis=0); report("seoul_3분야(청소년수련 제외; 66개소라 지역 단위 대리 부적합)", xs3, (600, 900))
NTR = {c: nearest_time(fac_idx(sel)) for c, sel in SEOUL_R.items()}; xr = np.max(np.vstack(list(NTR.values())), axis=0); report("seoul_권역생활권서비스(4분야, 참고)", xr, (900, 1200))
binding_s = {c: (pop * ((NTS[c] > 600) & popped & (xs > 600))).sum() / max((pop * ((xs > 600) & popped)).sum(), 1) for c in SEOUL7}
missdist("logan7_최댓값(cat_A 7)", NT, 900); missdist("seoul_4분야", NTS, 600)
# 부가 층 포함 정의
NTF = {c: nearest_time(fn()) for c, fn in SEOUL_FULL.items()}
xf = np.max(np.vstack(list(NTF.values())), axis=0); report("seoul_FULL_6분야(공원·도서관·노인여가·청소년아동·보육·공공체육)", xf, (600, 900, 1200))
missdist("seoul_FULL_6분야", NTF, 600); missdist("seoul_FULL_6분야", NTF, 900)
NTFx = {c: v for c, v in NTF.items() if c != "공공체육"}; xfx = np.max(np.vstack(list(NTFx.values())), axis=0); report("seoul_FULL_5분야(공공체육 제외 민감도)", xfx, (600, 900))
if "공공체육_엄격" in Yr.fac:
    NTFs = dict(NTF); NTFs["공공체육"] = nearest_time(Yr.fac["공공체육_엄격"][0]); report("seoul_FULL_6분야(공공체육 엄격 좌표만)", np.max(np.vstack(list(NTFs.values())), axis=0), (600, 900))
NTL = {c: nearest_time(fn()) for c, fn in LOGAN4.items()}
xl = np.max(np.vstack(list(NTL.values())), axis=0); report("logan4_원정의(약국·슈퍼·공원·초등)", xl, (600, 900, 1200)); missdist("logan4_원정의", NTL, 900)
NT9 = dict(NT8); NT9["공원"] = nearest_time(add_idx("공원")); report("abb9_최댓값(Abbiasov 9종 대응 + 공원; 종교 없음)", np.max(np.vstack(list(NT9.values())), axis=0), (600, 900, 1200)); missdist("abb9", NT9, 900)
NT20b = dict(NT20); NT20b["야외활동(공원)"] = nearest_time(add_idx("공원"), k=20); NT20b["신체활동(공공체육)"] = nearest_time(add_idx("공공체육"), k=20)
ptb = np.mean(np.vstack([np.minimum(v, 1200) for v in NT20b.values()]), axis=0); report("bruno9_평균PT(k=20, 공원·공공체육 포함)", ptb, (900,), note="1,200초 절단")
if "공원_UPIS2024" in Yr.fac:
    NTu = dict(NTF); NTu["공원"] = nearest_time(Yr.fac["공원_UPIS2024"][0]); report("seoul_FULL_6분야(공원=UPIS2024 민감도)", np.max(np.vstack(list(NTu.values())), axis=0), (600, 900))
MS = pd.DataFrame(miss); MS.to_csv(OUT / f"표4.1-16_결손수분포_{year}.csv", index=False, encoding="utf-8-sig")
D = pd.DataFrame(rows); D.to_csv(OUT / f"표4.1-16_묶음정의별_완결_{year}.csv", index=False, encoding="utf-8-sig")
C = pd.DataFrame(curves); C.to_csv(OUT / f"표4.1-16_묶음정의별_곡선_{year}.csv", index=False, encoding="utf-8-sig")
s = f"# 표 4.1-16 묶음 정의별 완결률 ({year})\n\n" + md(D.round(3), "{}")
s += f"\n\n- logan7 15분 미완결의 결손 범주 비율: " + ", ".join(f"{k} {v:.2f}" for k, v in binding.items())
s += f"\n- seoul 10분 미완결의 결손 분야 비율: " + ", ".join(f"{k} {v:.2f}" for k, v in binding_s.items())
s += f"\n- bruno PT 셀 간 인구가중 Gini: {pt_gini:.3f}\n\n## 누적분포(분)\n\n" + md(C.pivot(index="분", columns="정의", values="완결률").round(3).reset_index(), "{}")
open(OUT / f"표4.1-16_묶음정의별_완결_{year}.md", "w", encoding="utf-8").write(s); print(s); print("done", f"{time.time()-t0:.0f}s")
