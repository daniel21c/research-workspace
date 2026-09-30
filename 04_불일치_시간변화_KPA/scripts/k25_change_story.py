# -*- coding: utf-8 -*-
"""
k25 — 자족성 상승의 실체와 불일치의 지속 (KPA 확정본 Ⅳ.1·Ⅳ.2)

1) 자족성(IFR) 상승: 25개 구·두 경계의 상승 여부, 이동 유형(EE·EH·EW·HE·HH·WE·WW) 대칭 분해(구성 효과 / 유형 내 효과),
   평일·주말 비교(구별 부호검정)
2) 불일치 지속: 판정 불일치 D의 구별 변화(부호검정·Wilcoxon), IFR 격차 G = IFR_가상경계 − IFR_공식의 확대와
   통행 변화 / 가상경계 재도출 분해(두 순서와 평균)
3) 고정경계 평가의 부호검정(2020 재배정 경계를 2025 통행에: 모듈성·D 개선 구 수)
판정 기준은 계산 전에 정했다: 2026-09-29 사전 등록(C1: 유형 내 효과 > 50%, C3: 주말 > 평일 구별 부호검정 p < 0.05),
V0 규칙(부호검정은 두 해 모두 G = 0인 구를 뺀 증가:감소).
입력: od_full_{2020,2025}01.parquet(요일·도착시간·이동유형), od_daily, 경계 대응표, k01 t03, k14 b4
출력: output/tables/benchmark/b9_change_story.json, b9_type_decomp.csv, b9_gap_gu.csv
"""
from __future__ import annotations
import json, sys
import duckdb
import numpy as np
import pandas as pd
from scipy.stats import binomtest, wilcoxon
import config as C

OUT = C.TAB / "benchmark"
LZM = pd.read_csv(C.LZ_MAP, encoding="utf-8-sig").set_index("Dong")
TYPES = ["EE", "EH", "EW", "HE", "HH", "WE", "WW"]            # HW·WH(집↔직장 통근)는 분석 필터에서 제외
TYPE_KO = {"EE": "기타→기타", "EH": "기타→집", "EW": "기타→직장", "HE": "집→기타", "HH": "집→집", "WE": "직장→기타", "WW": "직장→직장"}


def sign2(k, n):
    return float(binomtest(k, n, 0.5).pvalue) if n else float("nan")


def type_table():
    """구 × 이동유형 × 평일/주말 집계. od_full이 있으면 계산해 집계표(b9_type_agg_{y}.csv)로 남기고,
    없으면(공동연구자 패키지: od_full 미포함) 패키지 data/od/의 같은 집계표를 읽는다."""
    con = duckdb.connect(); con.execute("SET threads TO 1")   # 단일 스레드: 합산 순서를 고정해 재실행 시 바이트 단위로 같게
    con.register("lz", LZM.reset_index()[["Dong", "ku_name", "life_zone_id"]])
    out = {}
    for y in C.YEARS:
        full = C.CORE_DATA / "od" / f"od_full_{y}01.parquet"
        if not full.exists():
            out[y] = pd.read_csv(C.CORE_DATA / "od" / f"b9_type_agg_{y}.csv", encoding="utf-8-sig"); continue
        p = str(full).replace("\\", "/")
        out[y] = con.execute(f"""
            SELECT o.ku_name, f.이동유형 AS typ, CASE WHEN f.요일 IN ('토','일') THEN '주말' ELSE '평일' END AS wk,
                   round(sum(f.flow), 6) AS T, round(sum(CASE WHEN o.life_zone_id = d.life_zone_id THEN f.flow ELSE 0 END), 6) AS inz
            FROM read_parquet('{p}') f JOIN lz o ON f.dong_O = o.Dong JOIN lz d ON f.dong_D = d.Dong
            WHERE f.도착시간 BETWEEN 9 AND 20 AND f.이동유형 NOT IN ('HW','WH')
            GROUP BY 1,2,3 ORDER BY 1,2,3""").df()
        out[y].to_csv(OUT / f"b9_type_agg_{y}.csv", index=False, encoding="utf-8-sig")
    return out


def main():
    R = {}
    t3 = pd.read_csv(C.TAB / "t03_gu_change.csv", encoding="utf-8-sig"); t3 = t3[t3.ku_code.astype(str).str.isdigit()].set_index("ku_name")
    R["IFR상승_구수"] = {"공식": int((t3.dIFR_lz > 0).sum()), "가상경계": int((t3.dIFR_ld > 0).sum()), "n": len(t3),
                       "p_공식": sign2(int((t3.dIFR_lz > 0).sum()), len(t3)), "p_가상경계": sign2(int((t3.dIFR_ld > 0).sum()), len(t3))}
    # 1) 이동 유형 분해 · 평일/주말
    od = type_table(); a, b = od[C.Y0], od[C.Y1]
    g = lambda df, k: df.groupby(k)[["T", "inz"]].sum().assign(IFR=lambda x: x.inz / x["T"])
    I0, I1 = a.inz.sum() / a["T"].sum(), b.inz.sum() / b["T"].sum()
    t0, t1 = g(a, "typ").loc[TYPES], g(b, "typ").loc[TYPES]
    s0, s1 = t0["T"] / t0["T"].sum(), t1["T"] / t1["T"].sum()
    contrib_within = (s0 + s1) / 2 * (t1.IFR - t0.IFR); contrib_comp = (s1 - s0) * (t0.IFR + t1.IFR) / 2
    tab = pd.DataFrame({"유형": [TYPE_KO[k] for k in TYPES], "코드": TYPES, "비중2020": s0.values, "비중2025": s1.values, "IFR2020": t0.IFR.values, "IFR2025": t1.IFR.values,
                        "ΔIFR": (t1.IFR - t0.IFR).values, "유형내기여": contrib_within.values, "구성기여": contrib_comp.values})
    tab.to_csv(OUT / "b9_type_decomp.csv", index=False, encoding="utf-8-sig")
    within, comp = float(contrib_within.sum()), float(contrib_comp.sum())
    R["유형분해"] = {"IFR2020": float(I0), "IFR2025": float(I1), "ΔIFR": float(I1 - I0), "유형내효과": within, "구성효과": comp, "유형내_비중": within / (I1 - I0),
                   "IFR상승_유형수": int((tab.ΔIFR > 0).sum()), "판정(유형내>50%)": "통과" if within / (I1 - I0) > 0.5 else "기각"}
    w0, w1 = g(a, "wk"), g(b, "wk"); gw = g(b, ["ku_name", "wk"]).IFR.unstack() - g(a, ["ku_name", "wk"]).IFR.unstack()
    kw = int((gw["주말"] > gw["평일"]).sum())
    R["평일주말"] = {"IFR2020_평일": float(w0.IFR["평일"]), "IFR2025_평일": float(w1.IFR["평일"]), "IFR2020_주말": float(w0.IFR["주말"]), "IFR2025_주말": float(w1.IFR["주말"]),
                   "ΔIFR_평일": float(w1.IFR["평일"] - w0.IFR["평일"]), "ΔIFR_주말": float(w1.IFR["주말"] - w0.IFR["주말"]),
                   "구수_주말>평일": kw, "n": len(gw), "p_양측": sign2(kw, len(gw)), "판정": "통과" if sign2(kw, len(gw)) < 0.05 and w1.IFR["주말"] - w0.IFR["주말"] > w1.IFR["평일"] - w0.IFR["평일"] else "기각"}
    # 2) 불일치 지속: D·G
    tie = (t3.G_2020.abs() < 1e-12) & (t3.G_2025.abs() < 1e-12)
    dUp, dDn = int((t3.dD > 1e-12).sum()), int((t3.dD < -1e-12).sum())
    R["D변화"] = {"증가": dUp, "감소": dDn, "변화없음": len(t3) - dUp - dDn, "p_부호_양측": sign2(dUp, dUp + dDn), "Wilcoxon_p": float(wilcoxon(t3.dD).pvalue),
                "D>0_구수_2020": int((t3.D_2020 > 1e-9).sum()), "D>0_구수_2025": int((t3.D_2025 > 1e-9).sum()), "중앙_2020": float(t3.D_2020.median()), "중앙_2025": float(t3.D_2025.median())}
    # G 분해: OD에서 직접(경계 × 연도 조합)
    LD = {y: pd.read_csv(C.ld_map(y), encoding="utf-8-sig").set_index("Dong")["global_community_id"] for y in C.YEARS}
    bound = {"LZ": LZM.life_zone_id, "LD20": LD[C.Y0], "LD25": LD[C.Y1]}
    P = {}
    for y in C.YEARS:
        d = pd.read_parquet(C.od_daily(y), columns=["dong_O", "dong_D", "flow"]); d["ku"] = d.dong_O.map(LZM.ku_name)
        for bk, lab in bound.items():
            same = d.dong_O.map(lab).values == d.dong_D.map(lab).values
            P[(bk, y)] = d.assign(inz=np.where(same, d.flow, 0.0)).groupby("ku")[["inz", "flow"]].sum()
    def I(bk, y, ku=None):
        x = P[(bk, y)]; return float(x.inz.sum() / x.flow.sum()) if ku is None else float(x.loc[ku, "inz"] / x.loc[ku, "flow"])
    def dec(ku=None):
        dLZ = I("LZ", C.Y1, ku) - I("LZ", C.Y0, ku)
        dG = (I("LD25", C.Y1, ku) - I("LZ", C.Y1, ku)) - (I("LD20", C.Y0, ku) - I("LZ", C.Y0, ku))
        f1 = (I("LD20", C.Y1, ku) - I("LD20", C.Y0, ku)) - dLZ; f2 = (I("LD25", C.Y1, ku) - I("LD25", C.Y0, ku)) - dLZ
        return {"G2020": I("LD20", C.Y0, ku) - I("LZ", C.Y0, ku), "G2025": I("LD25", C.Y1, ku) - I("LZ", C.Y1, ku), "ΔG": dG,
                "통행_순서1": f1, "통행_순서2": f2, "통행_평균": (f1 + f2) / 2, "재도출_평균": dG - (f1 + f2) / 2}
    s = dec(); gu = pd.DataFrame({ku: dec(ku) for ku in t3.index}).T; gu.to_csv(OUT / "b9_gap_gu.csv", encoding="utf-8-sig")
    gUp, gDn = int(((gu.ΔG > 1e-12) & ~tie).sum()), int(((gu.ΔG < -1e-12) & ~tie).sum())
    fUp, fDn = int((gu.통행_평균 > 1e-12).sum()), int((gu.통행_평균 < -1e-12).sum())
    R["G확대"] = {**s, "통행몫_평균": s["통행_평균"] / s["ΔG"], "통행몫_순서1": s["통행_순서1"] / s["ΔG"], "통행몫_순서2": s["통행_순서2"] / s["ΔG"],
                "구_증가": gUp, "구_감소": gDn, "구_변화없음": int(tie.sum()), "p_부호_양측": sign2(gUp, gUp + gDn), "Wilcoxon_p": float(wilcoxon(gu.ΔG[~tie]).pvalue),
                "구_통행몫양수": fUp, "구_통행몫음수": fDn, "p_통행몫_양측": sign2(fUp, fUp + fDn)}
    # 3) 고정경계 평가 부호검정
    h = json.loads((OUT / "b4_summary.json").read_text(encoding="utf-8"))["보류검증_2020경계를_2025에"]; n = h["재배정있는_구"]
    R["고정경계_부호검정"] = {"n": n, "Q개선": h["구_Q_개선"], "p_Q": sign2(h["구_Q_개선"], n), "D감소": h["구_D_감소"], "p_D": sign2(h["구_D_감소"], n)}
    # 크기를 맞춘 비교에서 무작위보다 나은 구 수
    b1 = pd.read_csv(OUT / "b1_gu.csv", encoding="utf-8-sig"); lz = b1[b1.boundary == "LZ"]
    R["N1_무작위보다나은구"] = {str(y): int((lz[lz.year == y].pct_N1 > 0.5).sum()) for y in (2020, 2025)}
    R["N1_무작위보다나은구_p"] = {str(y): sign2(int((lz[lz.year == y].pct_N1 > 0.5).sum()), 25) for y in (2020, 2025)}
    (OUT / "b9_change_story.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(R, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
