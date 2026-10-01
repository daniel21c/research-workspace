# -*- coding: utf-8 -*-
"""원고 수치 자동 대조(2026-10-02, AG a07_claims_check와 같은 취지).
각 주장에 대해 (1) results/ 의 원자료 표 또는 저장된 입지 해(JSON)에서 값을 다시 계산하고,
(2) 원고에 적힌 값과 허용 오차 안에서 같은지, (3) 그 문장이 영문 원고(manuscript.md)와 한국어 원고(manuscript_ko.md)에 실제로 있는지 확인한다.
0명 생활권 수는 저장된 입지(exp16 MIP·IND, exp14 COL P=2, exp20 권역 최저선)를 bundlelib.State로 다시 적용해 센다.
실행: python code/claims_check.py      출력: results/claims_check.json (불일치가 하나라도 있으면 종료 코드 1)"""
import json, re, sys
from pathlib import Path
import numpy as np, pandas as pd
CODE = Path(__file__).parent; R1 = CODE.parent; RES = R1 / "results"; SRC = CODE / "manuscript_src"
EN = (SRC / "manuscript.md").read_text(encoding="utf-8"); KO = (SRC / "manuscript_ko.md").read_text(encoding="utf-8")
EN_BODY = EN.split("## References")[0]; KO_BODY = KO.split("## 참고문헌")[0]
rows = []

def chk(cid, recomputed, shown, tol, en=None, ko=None, note=""):
    rec = [float(x) for x in np.atleast_1d(recomputed)]; sh = [float(x) for x in np.atleast_1d(shown)]
    val_ok = len(rec) == len(sh) and all(abs(a - b) <= tol + 1e-9 for a, b in zip(rec, sh))
    en_ok = True if en is None else all(s in EN_BODY for s in np.atleast_1d(en))
    ko_ok = True if ko is None else all(s in KO_BODY for s in np.atleast_1d(ko))
    rows.append({"id": cid, "recomputed": [round(x, 4) for x in rec], "manuscript": sh, "tol": tol, "value_ok": bool(val_ok),
                 "en_text_ok": bool(en_ok), "ko_text_ok": bool(ko_ok), "ok": bool(val_ok and en_ok and ko_ok), "note": note,
                 "en": en, "ko": ko})

P = lambda x: 100 * x
Y = ("2020", "2025")
# ---------------- 1. 묶음 완결 (표4.1-16) ----------------
W = {y: pd.read_csv(RES / f"표4.1-16_묶음정의별_완결_{y}.csv") for y in Y}
def comp(y, key, t): d = W[y]; return float(d[d.정의.str.startswith(key) & (d["임계(분)"] == t)].완결률.iloc[0])
chk("logan4_15", [P(comp(y, "logan4", 15)) for y in Y], [94.8, 94.6], 0.05, "94.8% (2020) and 94.6% (2025) of residents reach all four amenities", "94.8%(2020)·94.6%(2025)")
chk("logan7_15", [P(comp(y, "logan7", 15)) for y in Y], [73.1, 77.3], 0.05, "73.1% and 77.3% reach all seven everyday categories", "73.1%·77.3%")
chk("logan7_10", [P(comp(y, "logan7", 10)) for y in Y], [37.2, 39.9], 0.05, "37.2% and 39.9% complete the everyday bundle", "37.2%·39.9%")
chk("seoul6_10", [P(comp(y, "seoul_FULL", 10)) for y in Y], [3.7, 5.3], 0.05, ["Only 3.7% (2020) and 5.3% (2025) of residents can reach all six domains", "Only 3.7–5.3% of residents reach all six domains"], ["3.7%(2020)·5.3%(2025)뿐", "3.7~5.3%뿐"])
chk("seoul6_15", [P(comp(y, "seoul_FULL", 15)) for y in Y], [20.9, 27.4], 0.05, "rise only to 20.9% and 27.4%", "20.9%·27.4%에 그친다")
D14 = {y: pd.read_csv(RES / f"표4.1-14_묶음완결_진단_{y}.csv") for y in Y}
cats = ["단일_교육", "단일_문화", "단일_보육·복지", "단일_생활서비스", "단일_소매", "단일_의료", "단일_행정·안전"]
chk("five_of_seven_99", [int((D14[y].iloc[0][cats] > 0.99).sum()) for y in Y], [5, 5], 0, "Five of the seven categories are within 15 minutes of more than 99% of residents", "7개 범주 가운데 5개는 99% 넘는 주민이")
M16 = {y: pd.read_csv(RES / f"표4.1-16_결손수분포_{y}.csv") for y in Y}
def miss(y, key, t): d = M16[y]; return d[d.정의.str.startswith(key) & (d["임계(분)"] == t)].iloc[0]
chk("everyday_lack_one", [P(miss(y, "logan7", 15).결손1개) for y in Y], [86, 84], 0.5, "86% and 84% lack only one category", "86%·84%는 한 범주만")
chk("bundle_lack_two_plus", [P(1 - miss(y, "seoul_FULL", 10).결손1개) for y in Y], [83, 80], 0.5, "83% (2020) and 80% (2025) lack two or more domains", "83%(2020)·80%(2025)는 두 분야 이상")
chk("missing_sports", [P(miss(y, "seoul_FULL", 10).결손포함_공공체육) for y in Y], [80, 77], 0.5, "Public sports (80% and 77%)", "공공체육(80%·77%)")
chk("missing_library", [P(miss(y, "seoul_FULL", 10).결손포함_도서관) for y in Y], [72, 70], 0.5, "the public library (72% and 70%)", "공공도서관(72%·70%)")
reach_childcare = [P(1 - miss(y, "seoul_FULL", 10).미완결인구비율 * miss(y, "seoul_FULL", 10).결손포함_보육) for y in Y]
chk("childcare_reach", [round(min(reach_childcare))], [98], 0.5, "childcare is reached by 98% of residents", "보육은 주민의 98%가", note="1 − 미완결비율 × 미완결 중 보육 결손비율")

# ---------------- 2. 묶음 정수계획 (표4.1-19) ----------------
M19 = {y: pd.read_csv(RES / f"표4.1-19_묶음정수계획_seoul_{y}.csv").iloc[0] for y in Y}
chk("mip_completion", [P(M19[y].MIP_현재해) for y in Y], [22.8, 24.2], 0.05, "from 3.7% to 22.8% (2020) and from 5.3% to 24.2% (2025)", "3.7%에서 22.8%(2020)로, 5.3%에서 24.2%(2025)로")
chk("ind_exact", [P(M19[y]["IND_정확(유형별MCLP·전체후보)"]) for y in Y], [14.7, 16.5], 0.05, "(14.7% and 16.5%)", "(14.7%·16.5%)")
chk("coord_gain_exact", [P(M19[y]["조정이득_하한(MIP현재해/IND정확-1)"]) for y in Y], [55, 47], 0.5, "55% and 47% more than the exact facility-by-facility solution", "55%·47% 높아")
chk("mip_gap0", [M19[y].MIP_갭 for y in Y], [0, 0], 0, note="격자 정수계획 최적성 증명(갭 0)")
chk("mip_hours", [M19[y].초 / 3600 for y in Y] + [pd.read_csv(RES / f"표4.1-19_묶음정수계획_seoul{t}_2025.csv").iloc[0].초 / 3600 for t in ("T720", "T900")], [1.26, 1.36, 0.78, 0.31], 0.05, "in 0.3–1.4 hours", "0.3~1.4시간에", note="풀이 시간 0.3~1.4시간")
L20 = pd.read_csv(RES / "표4.1-19_정확해_하위20.csv")
def low(b, y, h): r = L20[(L20.묶음 == b) & (L20.year == int(y)) & (L20.해 == h)]; return float(r.하위20_완결률.iloc[0])
def low_c(b, y, h): r = L20[(L20.묶음 == b) & (L20.year == int(y)) & (L20.해 == h)]; return float(r.완결률.iloc[0])
chk("mip_bottom20", [P(low("seoul", y, "정수계획")) for y in Y], [0.1, 0.2], 0.05, "reaches only 0.1% and 0.2% of the bottom-20 group", "하위 20%의 0.1%·0.2%에만")
T720 = pd.read_csv(RES / "표4.1-19_묶음정수계획_seoulT720_2025.csv").iloc[0]; T900 = pd.read_csv(RES / "표4.1-19_묶음정수계획_seoulT900_2025.csv").iloc[0]
chk("t720_t900_base", [P(T720.기준_완결), P(T900.기준_완결)], [11.8, 27.4], 0.05, "raises completion before placement to 11.8% and 27.4% (2025)", "11.8%와 27.4%(2025)로")
chk("t720_t900_gain", [P(T720["조정이득_하한(MIP현재해/IND정확-1)"]), P(T900["조정이득_하한(MIP현재해/IND정확-1)"])], [28, 8], 0.5, "by 28% at 12 minutes and 8% at 15 minutes", "12분에서 28%, 15분에서 8%")
B18 = {y: pd.read_csv(RES / f"표4.1-18_묶음배치_seoul_{y}_p2.csv") for y in Y}
def p2_low(y):
    d = B18[y]; r = d[d.iloc[:, 0].astype(str).str.contains("COL")] if d.iloc[:, 0].dtype == object else d
    for c in d.columns:
        if "하위20" in c: return float(d[d.astype(str).apply(lambda s: s.str.contains("COL_조정_무경계")).any(axis=1)][c].iloc[0])
chk("p2_bottom20", [P(p2_low(y)) for y in Y], [5.8, 6.3], 0.05, "reaches 5.8% and 6.3% of the bottom-20 group", "하위 20%의 5.8%·6.3%에")

# ---------------- 3. 권역 최저선 (표4.1-23) ----------------
T23 = {y: pd.read_csv(RES / f"표4.1-23_권역최저선_{y}.csv") for y in Y}
def t23(y, u, tau, col): d = T23[y]; return d[(d.단위 == u) & (np.isclose(d.τ, tau))][col]
chk("gu5_zero", [float(t23(y, "구", 0.05, "공식LZ_0%권역").iloc[0]) for y in Y], [18, 12], 0, "remain at 18 (2020) and 12 (2025) under a 5% gu standard", "18개(2020)·12개(2025)로 남는다")
chk("gu5_below_before", [float(t23(y, "구", 0.05, "배치전_미달권역").iloc[0]) for y in Y] + [float(t23(y, "구", 0.05, "배치후_미달권역(τ)").iloc[0]) for y in Y], [16, 14, 0, 0], 0, "16 (2020) and 14 (2025) gu fall below it before placement", "배치 전 16개(2020)·14개(2025) 자치구가")
chk("gu5_cost", [max(float(t23(y, "구", t, "최저선비용_%p").iloc[0]) for y in Y for t in (0.01, 0.05))], [0.05], 0.005, "at most 0.05 percentage points", "최대 0.05%p")
chk("gu_gap", [max(float(t23(y, "구", t, "갭").iloc[0]) for y in Y for t in (0.01, 0.05))], [0.001], 0.0005, "within 0.1% of optimality", "최적성 0.1% 안까지", note="자치구 정수계획 갭 ≤ 0.1%")
chk("dong5_cost", [float(t23(y, "동", 0.05, "최저선비용_%p").iloc[0]) for y in Y], [5.2, 4.6], 0.05, "the best solutions cost 4.6–5.2 percentage points", "4.6~5.2%p 낮추고")
chk("dong5_below_after", [float(t23(y, "동", 0.05, "배치후_미달권역(τ)").iloc[0]) for y in Y], [221, 198], 0, "198–221 of 424 dong below the standard", "198~221개를")
chk("dong5_zero", [float(t23(y, "동", 0.05, "공식LZ_0%권역").iloc[0]) for y in Y], [20, 16], 0, "(20 and 16)", "(20개와 16개)")
chk("lz5_zero", [float(t23(y, "공식LZ_long", 0.05, "공식LZ_0%권역").iloc[0]) for y in Y], [3, 2], 0, "from 18 to 3 (2020) and from 14 to 2 (2025)", "18개에서 3개(2020)로, 14개에서 2개(2025)로")
chk("lz5_below5", [float(t23(y, "공식LZ_long", 0.05, "공식LZ_5%미만").iloc[0]) for y in Y], [9, 5], 0, "from 33 to 9 and from 29 to 5", "33개에서 9개로, 29개에서 5개로")
chk("lz5_cost", [float(t23(y, "공식LZ_long", 0.05, "최저선비용_%p").iloc[0]) for y in Y], [2.8, 2.1], 0.05, "The cost is 2.8 and 2.1 percentage points", "2.8%p와 2.1%p")
chk("lz1_cost", [float(t23(y, "공식LZ_long", 0.01, "최저선비용_%p").iloc[0]) for y in Y], [1.3, 0.6], 0.05, "1.3 and 0.6 points under a 1% minimum", "1.3%p와 0.6%p")
chk("lz_bottom20_range", [P(min(float(t23(y, u, t, "하위20_완결률").iloc[0]) for y in Y for t in (0.01, 0.05) for u in ["공식LZ_long"])), P(max(float(t23(y, u, t, "하위20_완결률").iloc[0]) for y in Y for t in (0.01, 0.05) for u in ["공식LZ_long"]))], [0.1, 0.4], 0.05, "Bottom-20 completion stays at 0.1–0.4%", "0.1~0.4%로")
chk("lz_gap_range", [P(min(float(t23(y, "공식LZ_long", t, "갭").iloc[0]) for y in Y for t in (0.01, 0.05))), P(max(float(t23(y, "공식LZ_long", t, "갭").iloc[0]) for y in Y for t in (0.01, 0.05)))], [3, 49], 1, "ended with gaps of 3–49%", "갭 3~49%로 끝났다")
rnd = T23["2025"][T23["2025"].단위.str.startswith("rand116") & np.isclose(T23["2025"].τ, 0.05)]["공식LZ_0%권역"]
chk("rand5_zero", [rnd.min(), rnd.max(), float(t23("2025", "Leiden", 0.05, "공식LZ_0%권역").iloc[0])], [5, 7, 4], 0, "reduce zero-completion official living zones to 5–7 and the mobility communities to 4 (2025)", "5~7개로, 이동 공동체는 4개로")
chk("lz_15h_2020", [float(t23("2020", "공식LZ", t, "공식LZ_0%권역").iloc[0]) for t in (0.01, 0.05)] + [float(t23("2020", "공식LZ_long", t, "공식LZ_0%권역").iloc[0]) for t in (0.01, 0.05)], [18, 4, 3, 3], 0, "18 zero-completion living zones remained after 1.5 hours under the 1% standard and 4 under the 5% standard", "1% 최저선에서 18개, 5% 최저선에서 4개")

# ---------------- 4. 시설 7종 정책 비교 (표4.1-10) ----------------
PC = {y: pd.read_csv(RES / f"표4.1-10_정책비교_{y}.csv").groupby(["시설", "정책"]).median(numeric_only=True) for y in Y}
FAC = ["도서관", "공공문화시설", "국공립유치원10분", "국공립어린이집5분", "노인이용시설", "청소년수련시설", "주민센터"]
v = lambda y, f, p, c: float(PC[y].loc[(f, p), c])
wins = sum(v(y, f, "PG1", "취약20_도달률") > v(y, f, "PL_공식", "취약20_도달률") for y in Y for f in FAC)
chk("pg_beats_pl", [wins], [12], 0, "in 12 of 14 facility–year combinations", "14개 조합 가운데 12개에서")
chk("lib2025_vuln", [P(v("2025", "도서관", "PG1", "취약20_도달률")), P(v("2025", "도서관", "PL_공식", "취약20_도달률"))], [57.9, 53.2], 0.05, "it reaches 57.9% of them against 53.2%", "57.9%에 닿아 생활권 최저선(53.2%)")
chk("lib2020_below", [v("2020", "도서관", "P0", "공식_미달수"), v("2020", "도서관", "PG1", "공식_미달수")], [11, 9], 0, "11 zones remain below it under grid efficiency and 9 under access-poor weighting (2020)", "격자 효율에서 11개, 접근 취약 가중에서 9개(2020)")
chk("kg2020_below", [v("2020", "국공립유치원10분", "P0", "공식_미달수"), v("2020", "국공립유치원10분", "PG1", "공식_미달수")], [14, 13], 0, "for public kindergartens, 14 and 13", "국공립유치원은 14개와 13개")
chk("pg_leaves_six", [sum(v(y, f, "PG1", "공식_미달수") > 0 for f in FAC) for y in Y], [6, 6], 0, "access-poor weighting leaves living zones below the minimum for six of them in both years", "접근 취약 가중은 두 시점 모두 6종에서")
chk("pl_zero_six", [sum(v(y, f, "PL_공식", "공식_미달수") == 0 for f in FAC) for y in Y], [6, 6], 0, "brings the number of living zones below the minimum to zero for six of seven facilities in both years", "7종 가운데 6종에서, 두 시점 모두")
chk("youth", [v("2020", "청소년수련시설", "P0", "공식_미달수"), v("2020", "청소년수련시설", "PL_공식", "공식_미달수"), v("2025", "청소년수련시설", "P0", "공식_미달수"), v("2025", "청소년수련시설", "PL_공식", "공식_미달수")], [21, 7, 18, 8], 0, "from 21 to 7 (2020) and from 18 to 8 (2025)", "21개에서 7개(2020)로, 18개에서 8개(2025)로")
chk("gu_lib", [v(y, "도서관", "PL_구", "공식_미달수") for y in Y], [10, 7], 0, "the gu standard leaves 10 and 7 living zones below the minimum", "10개와 7개 남겨")
chk("hy_childcare", [P(v(y, "국공립어린이집5분", "HY_공식", "취약20_도달률")) for y in Y] + [P(v(y, "국공립어린이집5분", "PG1", "취약20_도달률")) for y in Y], [42.6, 42.6, 42.6, 42.8], 0.05, "42.6% of them in both years, against 42.6% and 42.8%", "42.6%에 닿아 접근 취약 가중(42.6%·42.8%)")
chk("hy_kg", [P(v(y, "국공립유치원10분", "HY_공식", "취약20_도달률")) for y in Y] + [P(v(y, "국공립유치원10분", "PG1", "취약20_도달률")) for y in Y], [35.4, 36.8, 35.3, 35.3], 0.05, "35.4% and 36.8% against 35.3%", "35.4%·36.8%로 접근 취약 가중(35.3%)")
K10 = pd.read_csv(RES / "표4.1-10_정책비교_2020.csv").groupby("시설").K.first()
chk("budgets_single", [K10["공공문화시설"], K10["국공립유치원10분"], K10["주민센터"], K10["도서관"], K10["노인이용시설"], K10["청소년수련시설"], K10["국공립어린이집5분"]], [32, 54, 8, 31, 93, 11, 200], 0, "cultural facilities (32), public kindergartens (54) and community centres (8)", "문화시설(32), 국공립유치원(54), 주민센터(8)")
# ---------------- 5. 은폐 H, 정수해 K_min, 창 ----------------
H = pd.read_csv(RES / "표4.1-2_은폐_H.csv"); h = lambda u: float(H[(H.year == 2020) & (H.시설 == "도서관") & (H.단위 == u)]["H_AUC(τ0.5~1.5×평균)"].iloc[0])
chk("H_lib2020", [h("동"), h("공식LZ"), h("구")], [0.21, 0.34, 0.43], 0.005, "0.21 for dong, 0.34 for living zones and 0.43 for gu", "행정동 0.21, 생활권 0.34, 자치구 0.43")
order_ok = []
for (y, f), g in H[H.시설 != "생활체육10분"].groupby(["year", "시설"]):   # 체육시설업은 v1.4에서 빈 집합(H=1.0 동률)이라 제외
    d = g.set_index("단위")["H_AUC(τ0.5~1.5×평균)"]
    if {"동", "공식LZ", "구"} <= set(d.index): order_ok.append(d["동"] < d["공식LZ"] < d["구"])
chk("H_order_all", [sum(order_ok), len(order_ok)], [18, 18], 0, "The order is the same for all nine facility types examined", "시설 9종 모두에서 같다", note=f"연도×시설 {len(order_ok)}건")
def kmin(y, key, f=None):
    d = pd.read_csv(RES / (f or f"정수해대조_{y}.csv")); r = d[d.문제.str.contains(key)]; return float(r.정수해.iloc[0])
D3600 = {y: pd.read_csv(RES / f"정수해대조_{y}_동_TL3600.csv").iloc[0] for y in Y}   # facility-v1.4 입력, 1시간 제한(10-02 재실행)
chk("kmin_lib", [D3600["2025"].정수해, float(D3600["2025"].gap), D3600["2020"].정수해, np.ceil(D3600["2020"].정수해 * (1 - float(D3600["2020"].gap)) - 1e-6), round(100 * float(D3600["2020"].gap))] + [kmin(y, "K_min 공식LZ") for y in Y] + [kmin("2020", "K_min 구")], [58, 0, 67, 65, 3, 21, 18, 2], 0,
    "requires 58 new libraries in 2025 (proven optimal) and 65–67 in 2020 (the best solution after one hour, gap 3%)", "2025년에는 새 도서관 58개(최적성 증명), 2020년에는 65~67개(1시간 뒤 가장 좋은 해, 갭 3%)",
    note="행정동 K_min: 2025 정수해·갭, 2020 정수해·하한(정수해×(1−갭) 올림)·갭%, 생활권·자치구 K_min")
# ---------------- 6. 경계 ----------------
S13 = {y: pd.read_csv(RES / f"표4.1-13_시설섞기_요약_{y}.csv") for y in Y}
T3 = (RES / "표4.1-3_크기축_요약.md").read_text(encoding="utf-8").split("## 2020 크기 축")[1].split("\n## ")[0]
row3 = {l.split("|")[1].strip(): [x.strip().split(" ")[0] for x in l.strip("|").split("|")] for l in T3.splitlines() if l.startswith("| ") and not l.startswith("| 구획")}
chk("loss_lib2020", [P(float(row3["공식LZ"][4])), P(float(row3["rand116"][4]))], [10.0, 13.9], 0.05, "falls by 10.0 percentage points with official boundaries but by 13.9 points (median)", "공식 경계에서는 10.0%p, 116개 무작위 구획에서는 13.9%p")
chk("relocation_all", [min(S13[y].공식우위비율.min() for y in Y), len(S13["2020"])], [1.0, 7], 0, "In all 20 relocations of each of the seven facilities", "시설 7종을 각각 20번씩")
txt3 = (RES / "표4.1-3_크기축_요약.md").read_text(encoding="utf-8")
pmax = {}
for y in Y:
    sec = txt3.split(f"## {y} 116개 치환 검정")[1].split("\n## ")[0]
    for line in sec.splitlines():
        if line.startswith("| 공식LZ |"):
            cells = [c.strip() for c in line.strip("|").split("|")]; pmax.setdefault(y, []).extend(float(c[1:]) for c in cells[4:8] if c.startswith("p"))
chk("perm_p", [max(max(v) for v in pmax.values())], [0.04], 0.0, "(p ≤ 0.04)", "(p ≤ 0.04)", note="공식LZ 경계 제한 손실 4종 × 귀무 3종 × 2시점의 최대 분위")
E12 = {y: pd.read_csv(RES / f"표4.1-12_경계노출_{y}.csv") for y in Y}
e = E12["2020"]; off = float(e[e.단위 == "공식LZ"].경계노출인구비율.iloc[0]); rr = e[e.단위 == "무작위116"].경계노출인구비율
chk("exposure", [off, rr.median(), len(rr), int((rr > off).all())], [0.84, 0.89, 40, 1], 0.005, "0.84 for official living zones against 0.89 for random partitions, lower than every one of 40 draws", "공식 생활권 0.84, 무작위 구획 0.89로, 40개")
C10 = {y: pd.read_csv(RES / f"표4.1-10_공식vs무작위_{y}.csv") for y in Y}
def lead(y):
    d = C10[y]; d = d[(d.비교 == "PL_공식 vs PL_무작위116") & (d.지표 == "Leiden_미달수")]; return int((d.공식 < d.무작위중앙).sum())
chk("leiden_shortfall", [lead("2020"), lead("2025")], [6, 6], 0, "(six of seven facilities in both years)", "(두 시점 모두 7종 가운데 6종)", note="2020 기준. 2025 값은 note2")
rows[-1]["note2"] = f"2025: {lead('2025')}/7"
# ---------------- 7. 민감도 (표4.1-6, 4.1-22, 4.1-11) ----------------
S6 = pd.concat([pd.read_csv(RES / f"표4.1-6_민감도_{y}.csv").assign(year=y) for y in Y])
km = S6[S6.지표 == "K_min"] if "지표" in S6.columns else None
txt6 = "\n".join((RES / f"표4.1-6_민감도_{y}.md").read_text(encoding="utf-8").split("## 효율유지율")[0] for y in Y)
vals = {"동": [], "공식LZ": [], "구": []}
for line in txt6.splitlines():
    if line.startswith("|") and not line.startswith("| 변형") and not line.startswith("|---"):
        c = [x.strip() for x in line.strip("|").split("|")]
        for k, i in (("동", 3), ("공식LZ", 4), ("구", 6)):
            if c[i]: vals[k].append(float(c[i]))
chk("A6_ranges", [min(vals["동"]), max(vals["동"]), min(vals["공식LZ"]), max(vals["공식LZ"]), min(vals["구"]), max(vals["구"])], [45, 105, 9, 49, 1, 17], 0, "Dong need 45–105 additions against 31–32 available, living zones 9–49 and gu 1–17", "45~105개가, 생활권은 9~49개, 자치구는 1~17개")
S22 = pd.read_csv(RES / "표4.1-22_시간외표본_추가수_민감도_seoul.csv")
def s22(exp, y, way): d = S22[(S22.실험 == exp) & (S22.year.astype(str) == y) & (S22.방식 == way)]; return float(d.완결률.iloc[0])
g = lambda exp, y: s22(exp, y, "COL") / s22(exp, y, "IND") - 1
chk("budget_gain", [P(g("기준", "2020")), P(g("C4b_추가수×0.5", "2020")), P(g("C4b_추가수×0.5", "2025")), P(g("C4b_추가수×2.0", "2025")), P(g("C4b_추가수×2.0", "2020"))], [32, 34, 35, 17, 25], 0.6, "+32% at the observed additions (2020)", "+32%다", note="탐욕 COL/IND − 1")
chk("layers_gain", [P(g("C5_strict_sports", "2025")), P(g("C5_strict_sports", "2020")), P(g("C5_upis_park", "2025")), P(g("C5_no_sports", "2025")), P(g("C5_no_sports", "2020"))], [30, 34, 33, 9, 10], 0.6, "(+30–34%)", "(+30~34%)")
chk("no_childcenter", [P(s22("C5_no_childcenter", y, "COL")) for y in Y] + [P(g("C5_no_childcenter", "2025")), P(g("C5_no_childcenter", "2020"))], [9.8, 10.5, 56, 68], 0.6, "(9.8% and 10.5%)", "(9.8%·10.5%)")
chk("transfer", [P(s22("C4a_조건부전이(2020계획→2025인구·망; 예산=관측순증·시설층 공통)", "2025평가", "COL(2020계획)")), P(s22("C4a_조건부전이(2020계획→2025인구·망; 예산=관측순증·시설층 공통)", "2025평가", "IND(2020계획)"))], [18.0, 13.1], 0.05, "18.0% of residents under the coordinated rule, against 13.1%", "18.0%를 완결시켜 시설별 계획 입지(13.1%)")
J = []
for y in Y:
    t = (RES / f"표4.1-11_교란안정성_{y}.md").read_text(encoding="utf-8")
    for line in t.splitlines():
        if line.startswith("|") and not line.startswith("| 시설") and not line.startswith("|---"):
            c = [x.strip() for x in line.strip("|").split("|")][1:7]; J += [float(x) for x in c if x]
chk("jaccard", [min(J), max(J)], [0.64, 1.0], 0.005, "(median Jaccard 0.64–1.0)", "(Jaccard 중앙값 0.64~1.0)", note="정책 6열(HY~PL_동)")

# ---------------- 8. 저장된 입지로 0명 생활권 다시 세기 ----------------
sys.path.insert(0, str(CODE))
from bundlelib import Ctx, State
def zero_counts(c, picks):
    st = State(c); st.B = {s: 10 ** 6 for s in c.SUB}
    for s, js in (picks or {}).items():
        for j in js: st.apply(int(j), [s])
    compl = (st.cnt == c.NC) & c.popped
    df = pd.DataFrame({"lz": c.Yr.M.lz.to_numpy(), "p": c.pop, "c": c.pop * compl}).groupby("lz").sum(); sh = df.c / df.p
    return int((sh <= 0).sum()), int((sh < 0.05).sum()), float((c.pop * compl).sum() / c.pop.sum())
Ys = {}; Z = {}
for y in Y:
    c = Ctx("seoul", y, years=Ys); Ys = c.Y
    mipj = json.load(open(RES / f"exp16_milp_picks_seoul_{y}.json", encoding="utf-8"))
    p2 = json.load(open(RES / f"exp14_placements_seoul_{y}_p2.json", encoding="utf-8"))["COL_조정_무경계#0"]
    Z[y] = {"before": zero_counts(c, None), "MIP": zero_counts(c, mipj["MIP"]["picks"]), "IND": zero_counts(c, mipj["IND"]["picks"]), "P2": zero_counts(c, p2)}
    for u in ("구", "동", "공식LZ_long"):
        Z[y][u] = zero_counts(c, json.load(open(RES / f"exp20_picks_{y}_{u}_0.05.json", encoding="utf-8"))["picks"])
    m = c.Yr.M; pop = c.pop
    if y == "2025":
        lzp = pd.Series(pop).groupby(m.lz.to_numpy()).sum(); gp = pd.Series(pop).groupby(m.ku.to_numpy()).sum(); dp = pd.Series(pop).groupby(m.dong.to_numpy()).sum()
        chk("pop_2024", [pop.sum() / 1e6, int((pop > 0).sum())], [9.34, 30785], 0.005, "9.34 million residents in 2024", "2024년 인구 934만 명", note="populated cells 30,785")
        chk("units_mean", [gp.mean(), lzp.mean(), lzp.min(), lzp.max(), dp.mean()], [373515, 80499, 21165, 148376, 22023], 0.5, "(mean 80,499; range 21,165–148,376)" if "(mean 80,499; range 21,165–148,376)" in EN_BODY else "average 80,499 (range 21,165–148,376)", "평균 80,499명(21,165~148,376명)")
    else:
        chk("pop_2019", [pop.sum() / 1e6], [9.64], 0.005, "(9.64 million in 2019)", "(2019년 964만 명)")
chk("zero_before", [Z[y]["before"][0] for y in Y] + [Z[y]["before"][1] for y in Y], [50, 38, 91, 73], 0, "In 50 (2020) and 38 (2025) of the 116 living zones", "50개(2020)·38개(2025)에서는")
chk("zero_mip", [Z[y]["MIP"][0] for y in Y] + [Z[y]["MIP"][1] for y in Y], [18, 14, 33, 29], 0, "Yet 18 (2020) and 14 (2025) living zones still have no resident completing the bundle", "18개(2020)·14개(2025) 남고")
chk("zero_ind", [Z[y]["IND"][0] for y in Y], [21, 13], 0, "Facility-by-facility planning leaves 21 and 13", "시설별 계획은 21개와 13개를")
chk("zero_p2", [Z[y]["P2"][0] for y in Y], [21, 19], 0, "but leaves 21 and 19 living zones at zero", "0명 생활권을 21개와 19개")
chk("zero_floor_recount", [Z[y][u][0] for y in Y for u in ("구", "동", "공식LZ_long")], [18, 20, 3, 12, 16, 2], 0, note="exp20 저장 입지를 다시 적용해 센 0명 생활권(구·동·생활권 5%)이 표4.1-23과 같은지")
chk("completion_recount", [P(Z[y]["MIP"][2]) for y in Y] + [P(Z[y]["공식LZ_long"][2]) for y in Y], [22.8, 24.2, 20.0, 22.1], 0.05, note="저장 입지 재적용 완결률")
# ---------------- 8b. 자료 건수 ----------------
HUB = R1.parent; ADD = pd.read_csv(HUB / "시설데이터 구축/시설데이터_패키지/부가층_v1.5후보_20261001/요약.csv")
a = lambda l, y, c: int(ADD[(ADD.layer == l) & (ADD.year == y)][c].iloc[0])
chk("addon_counts", [a("공공체육", "2020_01", "facilities"), a("공공체육", "2025_01", "facilities"), a("지역아동센터", "2025_01", "facilities"), a("공원", "2025_01", "facilities"), a("공원", "2025_01", "grid_cells")], [387, 456, 307, 1886, 17936], 0, "(387 and 456 facilities)", "(387·456곳)")
FAC_ALL = pd.read_parquet(HUB / "시설데이터 구축/시설데이터_패키지/데이터/서울시설_2020_2025_분석용.parquet", columns=["시설"])
chk("facility_records", [len(FAC_ALL), FAC_ALL.시설.nunique()], [584766, 32], 0, "An inventory of 32 facility types", "32개 유형의 시설 목록(584,766건")

# ---------------- 10. 개정판(10-02 검토 반영)에서 더한 수치 ----------------
RC = json.load(open(RES / "재집계_0명생활권_인구_문턱_20261002.json", encoding="utf-8"))
chk("zero_pop_before", [RC[y]["before"]["zero_pop_M"] for y in Y], [3.82, 2.75], 0.005, "home to 3.82 million (2020) and 2.75 million (2025) residents", None)
chk("zero_pop_mip", [RC[y]["MIP"]["zero_pop_M"] for y in Y], [1.13, 0.97], 0.005, "home to 1.13 and 0.97 million residents", None)
chk("zero_pop_lz", [RC[y]["LZ5"]["zero_pop_M"] for y in Y], [0.09, 0.06], 0.005, "from 1.13 to 0.09 million (2020) and from 0.97 to 0.06 million (2025)", None)
chk("zero_pop_grid_about_million", [min(RC[y][r]["zero_pop_M"] for y in Y for r in ("MIP", "IND", "P2")), max(RC[y][r]["zero_pop_M"] for y in Y for r in ("MIP", "IND", "P2"))], [0.77, 1.42], 0.005, "home to about a million residents", None, note="격자 규칙 3종 × 2시점 0.77~1.42백만")
chk("threshold_recount", [RC["T720"]["before"]["zero"], RC["T900"]["before"]["zero"], RC["T720"]["MIP"]["zero"], RC["T900"]["MIP"]["zero"], RC["T720"]["IND"]["zero"], RC["T900"]["IND"]["zero"], RC["T720"]["MIP"]["zero_pop_M"], RC["T900"]["MIP"]["zero_pop_M"]], [18, 11, 7, 3, 5, 3, 0.45, 0.09], 0.005, ["reduces zero-completion living zones before placement to 18 and 11", "7 and 3 living zones remain at zero, home to 0.45 and 0.09 million residents", "facility-by-facility planning leaves 5 and 3"], None)
own = lambda y, u, tau: float(t23(y, u, tau, "단위내_0%권역").iloc[0])
rown = T23["2025"][T23["2025"].단위.str.startswith("rand116") & np.isclose(T23["2025"].τ, 0.05)]["단위내_0%권역"]
chk("own_unit_zero", [rown.min(), rown.max(), own("2025", "Leiden", 0.05), own("2025", "공식LZ_long", 0.05), own("2025", "동", 0.05), own("2020", "동", 0.05)], [0, 1, 3, 2, 155, 176], 0, "155–176 dong with no completer", None)
chk("equal_time_2025", [float(t23("2025", "공식LZ", t, "공식LZ_0%권역").iloc[0]) for t in (0.01, 0.05)] + [float(t23("2025", "공식LZ_long", t, "공식LZ_0%권역").iloc[0]) for t in (0.01, 0.05)], [3, 2, 3, 2], 0, "In 2025 the 1.5-hour and 4-hour runs gave the same counts (3 and 2)", None)
U19 = pd.read_csv(RES / "표4.1-19_정확해_하위20.csv")
chk("mip_used", [float(U19[(U19.묶음 == "seoul") & (U19.year == int(y)) & (U19.해 == "정수계획")].사용.iloc[0]) for y in Y], [177, 283], 0, "uses only 177 (2020) and 283 (2025) of the 381 additions", None)
chk("dong_gaps", [P(float(t23(y, "동", 0.05, "갭").iloc[0])) for y in Y], [117, 102], 1, "large gaps (102–9,797%)", None)
win = {}
for y in Y:
    for line in (RES / f"표4.1-9_시설별_창_{y}.md").read_text(encoding="utf-8").split("## 반사실")[0].splitlines():
        if line.startswith("| ") and not line.startswith("| 시설"):
            c = [x.strip() for x in line.strip("|").split("|")]
            kb = float(c[4]) if c[4] else None; ka = float(c[5])
            win.setdefault(y, []).append((kb, ka))
in116 = [sum(1 for kb, ka in win[y] if kb is not None and kb <= 116 <= ka) for y in Y]
out424 = [sum(1 for kb, ka in win[y] if kb is None or not (kb <= 424 <= ka)) for y in Y]
chk("window", in116 + out424, [4, 3, 6, 6], 0, ["The 116-zone scale lies inside that range for four facilities in 2020", "and three in 2025", "lies outside it for six of seven facilities in both years"], None)
chk("cap_never_bound", [int(T23[y]["구조적상한<τ_권역"].max()) for y in Y], [0, 0], 0, "in practice this cap never bound", None)
# ---------------- 11. 두 단계 증명(exp21, 표4.1-24)과 공공체육 엄격 층 ----------------
T24 = pd.read_csv(RES / "표4.1-24_최저선증명.csv")
def t24(y, u, m, tau): return T24[(T24.year == int(y)) & (T24.단위 == u) & (T24["mode"] == m) & np.isclose(T24.τ, tau)].iloc[0]
proved = [(y, "공식LZ", "zero", 0) for y in Y] + [(y, "공식LZ", "short", t) for y in Y for t in (0.01, 0.05)] + [("2025", u, "zero", 0) for u in ("rand116_1", "rand116_2", "rand116_3", "Leiden")] + [("2025", "구", "short", 0.05)]
chk("proof_feasible", [sum(int(t24(*k).status == 0 and t24(*k).최적값 == 0 and t24(*k)["단위내_0%권역(재평가)"] == 0) for k in proved)], [len(proved)], 0,
    ["it proves for both years that the observed additions can give every official living zone at least one completer", "(gap 0; Table A.2)"], ["모든 생활권을 1%와 5% 최저선 위로 올릴 수 있다는 것이 증명되었다(갭 0, 표 A.2)"], note="1단계 실행이 모두 최적(상태 0)이고 최적값 0, 재평가 0명 구역 0")
lb = [float(t24(y, "공식LZ", "max", t)["최저선비용_%p(하한)"]) for y in Y for t in (0.01, 0.05)]
chk("proof_cost_bound", lb, [1.3, 1.3, 0.6, 1.3], 0.05, ["the cost is at least 1.3 percentage points in both years", "at a cost of at least 1.3 percentage points of completion"], ["비용은 두 시점 모두 1.3%p 이상이다", "완결률 1.3%p(퍼센트포인트) 이상이다"], note="2단계 상한에서 얻은 비용 하한(2020 1%, 2020 5%, 2025 1%, 2025 5%)")
ub = [P(float(t24(y, "공식LZ", "max", 0.05).총량최대_완결률)) - float(t24(y, "공식LZ", "max", 0.05)["최저선비용_%p(하한)"]) for y in Y]
chk("proof_upper_completion", ub, [21.5, 22.9], 0.05, "citywide completion can be at most 21.5% (2020) and 22.9% (2025)", "서울 전체 완결률은 최대 21.5%(2020)와 22.9%(2025)")
chk("proof_best_cost", [float(t24(y, "공식LZ", "max", 0.05)["최저선비용_%p(해)"]) for y in Y], [8.4, 6.9], 0.05, ["cost 8.4 and 6.9 points", "between 1.3 and 8.4 percentage points (5% minimum)"], ["비용은 8.4%p와 6.9%p", "1.3~8.4%p(5% 최저선)"])
chk("proof_best_completion", [P(float(t24(y, "공식LZ", "max", t).완결률)) for y in Y for t in (0.01, 0.05)], [15.6, 14.4, 18.5, 17.3], 0.05, "| 15.6% |", "| 15.6% |", note="표 A.2 2단계 행")
chk("proof_dong", [min(float(t24(y, "동", "zero", 0)["단위내_0%권역(재평가)"]) for y in Y), max(float(t24(y, "동", "zero", 0)["단위내_0%권역(재평가)"]) for y in Y)] + [float(T24[T24.단위 == "동"].하한.max())], [130, 285, 0], 0,
    ["left 130–285 dong without a completer", "the lower bound stayed at zero"], ["행정동 130~285개를 완결 주민 0명으로 남겼고", "하한은 0에서 올라가지 않았다"])
chk("proof_recount", [RC[y]["LZ5_hard"][k] for y in Y for k in ("zero", "below5")] + [P(RC[y]["LZ5_hard"]["completion"]) for y in Y], [0, 0, 0, 0, 14.4, 17.3], 0.05, note="2단계 5% 해(exp21_picks)를 bundlelib.State로 전체 격자에 다시 적용: 0명·5% 미만 생활권 0, 완결률 표 A.2와 같음")
ST = json.load(open(RES / "재집계_공공체육엄격_20261002.json", encoding="utf-8"))
chk("strict_sports_zero", [ST[y][r]["zero"] for r in ("before", "MIP", "LZ5") for y in Y], [55, 41, 21, 15, 5, 2], 0,
    "number 55 and 41 before placement, 21 and 15 after grid bundle maximisation and 5 and 2 under the 5% living-zone minimum", "배치 전 55개와 41개, 격자 묶음 최대화 뒤 21개와 15개, 생활권 5% 최저선 뒤 5개와 2개")
# 표 4b 격자 3행(그림 6 기준값과 같은 원천): 원고 표 CSV가 결과 파일 값과 같은지(검증 S3-5)
T4B = pd.read_csv(SRC / "tables" / "Table4b_bundle_report_cards.csv").set_index("Rule")
def p2row(y): d = B18[y]; return d[d.방식 == "COL_조정_무경계"].iloc[0]
src4 = {"Grid: facility-by-facility (exact)": {y: (low_c("seoul", y, "IND_정확해"), low("seoul", y, "IND_정확해"), RC[y]["IND"]["zero"]) for y in Y},
        "Grid: bundle maximisation (exact)": {y: (low_c("seoul", y, "정수계획"), low("seoul", y, "정수계획"), RC[y]["MIP"]["zero"]) for y in Y},
        "Grid: coordinated (P=2)": {y: (p2row(y).완결률, p2row(y).하위20_완결률, RC[y]["P2"]["zero"]) for y in Y}}
rec4, man4 = [], []
for rule, d in src4.items():
    for y in Y:
        rec4 += [round(P(d[y][0]), 1), round(P(d[y][1]), 1), d[y][2]]
        man4 += [float(T4B.loc[rule, f"{y} completion (%)"]), float(T4B.loc[rule, f"{y} bottom-20 (%)"]), int(T4B.loc[rule, f"{y} zero-completion zones"])]
chk("table4b_grid", rec4, man4, 0, note="표 4b 격자 3행·그림 6 기준값 = 표4.1-19_정확해_하위20, 표4.1-18 p2, 저장 입지 재집계")
chk("fig6_before_zero", [RC[y]["before"]["zero"] for y in Y], [50, 38], 0, note="그림 6 배치 전 막대")
# 부록 표 A.1: 원고 표의 값이 표4.1-23과 같은지
A1 = [l for l in EN_BODY.split("**Table A.1.**")[1].split("\n\n")[1].splitlines() if l.startswith("| 20")]
umap = {"Gu (1.5 h)": "구", "Dong (1.5 h)": "동", "Official living zones (1.5 h)": "공식LZ", "Official living zones (4 h)": "공식LZ_long", "Mobility communities (1.5 h)": "Leiden"}
bad = []
for l in A1:
    c = [x.strip() for x in l.strip("|").split("|")]; y, tau, unit = c[0], float(c[1].rstrip("%")) / 100, c[2]
    if unit not in umap: continue
    r = T23[y][(T23[y].단위 == umap[unit]) & np.isclose(T23[y].τ, tau)].iloc[0]
    ok = int(c[3]) == int(r["공식LZ_0%권역"]) and int(c[4].split(" ")[0]) == int(r["단위내_0%권역"]) and abs(float(c[5]) - round(float(r["최저선비용_%p"]), 2)) < 0.006 and abs(float(c[6].rstrip("%").replace(",", "")) - round(100 * float(r["갭"]), 0 if float(r["갭"]) > 0.005 else 1)) <= 0.6
    if not ok: bad.append(l)
chk("tableA1", [len(bad), len(A1)], [0, 20], 0, note="표 A.1 행(무작위 116 범위 행 제외)과 표4.1-23 대조")
rows[-1]["bad_rows"] = bad
# ---------------- 9. 초록·하이라이트 ----------------
hl = (SRC / "highlights.md").read_text(encoding="utf-8")
chk("highlights", [max(len(l[2:]) for l in hl.splitlines() if l.startswith("- ")), sum(l.startswith("- ") for l in hl.splitlines())], [85, 5], 85, note="하이라이트 최대 글자 수 ≤ 85, 5개")
rows[-1]["value_ok"] = rows[-1]["ok"] = max(len(l[2:]) for l in hl.splitlines() if l.startswith("- ")) <= 85
ab = EN.split("## Abstract")[1].split("**Keywords")[0]
chk("abstract_words", [len(ab.split())], [250], 250, note="초록 ≤ 250단어")
rows[-1]["value_ok"] = rows[-1]["ok"] = len(ab.split()) <= 250

# 개정판 한국어 문구(영문 점검과 짝)
KO_ADD = {"zero_pop_before": "382만 명(2020)과 275만 명(2025)이 산다", "zero_pop_mip": "113만 명과 97만 명이 산다", "zero_pop_lz": "113만 명에서 9만 명(2020)으로, 97만 명에서 6만 명(2025)으로",
          "zero_pop_grid_about_million": "약 100만 명이 산다", "threshold_recount": ["0명 생활권은 18개와 11개로 준다", "0명 생활권이 7개와 3개 남고 그곳에 45만 명과 9만 명이 살며", "시설별 계획은 5개와 3개를"],
          "own_unit_zero": "155~176개를 완결 주민 0명으로", "equal_time_2025": "1.5시간과 4시간 실행의 결과가 같았으므로(3개와 2개)",
          "mip_used": "177개(2020)와 283개(2025)만 쓰는데", "dong_gaps": "(102~9,797%)", "window": ["2020년 4종", "2025년 3종", "7종 가운데 6종에서 범위 밖"], "cap_never_bound": "실제로 이 상한이 걸린 적은 없다"}
for r in rows:
    if r["id"] in KO_ADD and r["ko"] is None:
        r["ko"] = KO_ADD[r["id"]]; r["ko_text_ok"] = all(s in KO_BODY for s in np.atleast_1d(r["ko"])); r["ok"] = r["value_ok"] and r["en_text_ok"] and r["ko_text_ok"]
fails = [r for r in rows if not r["ok"]]
out = {"n_checks": len(rows), "n_fail": len(fails), "fails": [r["id"] for r in fails], "checks": rows}
json.dump(out, open(RES / "claims_check.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"checks {len(rows)}  fail {len(fails)}")
for r in fails: print("FAIL", r["id"], r["recomputed"], r["manuscript"], "val", r["value_ok"], "en", r["en_text_ok"], "ko", r["ko_text_ok"])
sys.exit(1 if fails else 0)
