# -*- coding: utf-8 -*-
"""
k15 — 재배정 권고 동과 접근성(4.3) 연결: "잘못 배정된 동은 왜 생기나"의 실마리

가설: 재배정이 권고된 동은 공식 생활권 경계 때문에 15분 안 시설을 잃는 동이다
      (그 동이 쓰는 시설이 옆 생활권에 있어서, 주민이 옆 생활권으로 다닌다).
사전 판정 기준(계산 전에 고정):
  "겹친다" = 재배정 권고 동(A)의 '경계 비용'(COV_경계없음 − COV_공식생활권, 종합) 중앙값이
            그 밖의 경계 동(B)보다 1%p 이상 크고, Mann–Whitney p < 0.05 가 두 해 모두 성립,
            그리고 10분 임계(sens_T600)에서도 같은 방향.
  보조: 가상경계 쪽 접근성 차 ΔCOV = COV_가상경계 − COV_공식생활권 (4.3의 핵심 변수) 이 A에서 더 큰가.
  MAI는 동 단위 순위 안정성이 낮으므로(접근성 패키지 검증보고서 WARN) 보조로만 본다.

집단
  A  재배정 권고 동: k14 탐욕 재배정에서 옮겨진 동(해당 연도)
  A* 두 해 모두 같은 이동이 권고된 동(49)
  B  그 밖의 경계 동: 옆 생활권과 맞닿아 옮길 수는 있으나 권고되지 않은 동
  C  내부 동: 옆 생활권과 맞닿지 않는 동
입력(읽기 전용): 06_접근성분석/접근성분석_패키지/데이터/결과/{main,sens_T600}/unit_access_{year}_100.csv
출력: output/tables/benchmark/b5_dong_access.csv, b5_group_summary.csv, b5_category.csv, b5_summary.json
"""
from __future__ import annotations
import json, sys
import numpy as np
import pandas as pd
from scipy import stats
import config as C

OUT = C.TAB / "benchmark"
ACC = C.ACC_DATA / "결과"
CATS = ["교육", "보육·복지", "의료", "문화", "체육", "행정·안전", "소매", "생활서비스"]


def access(tag, y):
    d = pd.read_csv(ACC / tag / f"unit_access_{y}_100.csv", encoding="utf-8-sig")
    d = d[(d.unit_level == "dong424") & d.b.isin(["none", "lz116", "ld"])]
    w = d.pivot_table(index="unit_id", columns=["b", "cat"], values=["COV", "MAI"])
    out = pd.DataFrame(index=w.index)
    for m in ("COV", "MAI"):
        for c in ["종합"] + CATS:
            out[f"{m}_cost_lz_{c}"] = w[(m, "none", c)] - w[(m, "lz116", c)]
            out[f"{m}_cost_ld_{c}"] = w[(m, "none", c)] - w[(m, "ld", c)]
            out[f"{m}_dLDLZ_{c}"] = w[(m, "ld", c)] - w[(m, "lz116", c)]
    return out


def mw(a, b):
    a, b = a.dropna(), b.dropna()
    if len(a) < 3 or len(b) < 3: return np.nan
    return float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue)


def main():
    lzm = pd.read_csv(C.LZ_MAP, encoding="utf-8-sig").set_index("Dong")
    greedy = pd.read_csv(OUT / "b4_greedy_moves.csv", encoding="utf-8-sig")
    single = pd.read_csv(OUT / "b4_single_moves.csv", encoding="utf-8-sig")
    g20 = set(greedy[greedy.year == int(C.Y0)][["dong", "to_zone"]].itertuples(index=False, name=None))
    g25 = set(greedy[greedy.year == int(C.Y1)][["dong", "to_zone"]].itertuples(index=False, name=None))
    both = {d for d, _ in g20 & g25}
    rows, summ, cat_rows, S = [], [], [], {"사전기준": __doc__.split("사전 판정 기준(계산 전에 고정):")[1].split("집단")[0].strip()}
    for y in C.YEARS:
        yi = int(y)
        moved = set(greedy[greedy.year == yi].dong)
        boundary = set(single[single.year == yi].dong)
        acc = {tag: access(tag, y) for tag in ("main", "sens_T600")}
        for d in lzm.index:
            grp = "A" if d in moved else ("B" if d in boundary else "C")
            r = {"year": yi, "dong": d, "dong_name": lzm.loc[d, "ADM_NM"], "ku_name": lzm.loc[d, "ku_name"], "zone": lzm.loc[d, "life_zone_name"], "group": grp, "both_years": d in both}
            for tag, a in acc.items():
                if d in a.index:
                    for col in ("COV_cost_lz_종합", "COV_dLDLZ_종합", "MAI_cost_lz_종합", "MAI_dLDLZ_종합"):
                        r[f"{tag}_{col}"] = a.loc[d, col]
            if d in acc["main"].index:
                for c in CATS: r[f"COV_cost_lz_{c}"] = acc["main"].loc[d, f"COV_cost_lz_{c}"]
            rows.append(r)
        df = pd.DataFrame([r for r in rows if r["year"] == yi])
        for tag in ("main", "sens_T600"):
            for col in ("COV_cost_lz_종합", "COV_dLDLZ_종합", "MAI_cost_lz_종합", "MAI_dLDLZ_종합"):
                k = f"{tag}_{col}"
                A, B, Cc = df[df.group == "A"][k], df[df.group == "B"][k], df[df.group == "C"][k]
                As = df[(df.group == "A") & df.both_years][k]
                summ.append({"year": yi, "tag": tag, "지표": col, "A_n": A.notna().sum(), "A_중앙": A.median(), "A*_중앙": As.median(), "B_n": B.notna().sum(), "B_중앙": B.median(), "C_중앙": Cc.median(),
                             "A>0_비율": float((A > 0).mean()), "B>0_비율": float((B > 0).mean()), "A−B_중앙차": A.median() - B.median(), "p_A_vs_B": mw(A, B)})
        for c in CATS:
            k = f"COV_cost_lz_{c}"; A, B = df[df.group == "A"][k], df[df.group == "B"][k]
            cat_rows.append({"year": yi, "cat": c, "A_평균": A.mean(), "B_평균": B.mean(), "A−B": A.mean() - B.mean(), "A>0_비율": float((A > 0).mean()), "B>0_비율": float((B > 0).mean()), "p": mw(A, B)})
    dall = pd.DataFrame(rows); sm = pd.DataFrame(summ); ct = pd.DataFrame(cat_rows)
    dall.to_csv(OUT / "b5_dong_access.csv", index=False, encoding="utf-8-sig"); sm.to_csv(OUT / "b5_group_summary.csv", index=False, encoding="utf-8-sig"); ct.to_csv(OUT / "b5_category.csv", index=False, encoding="utf-8-sig")
    main_cost = sm[(sm.tag == "main") & (sm.지표 == "COV_cost_lz_종합")].set_index("year")
    t6_cost = sm[(sm.tag == "sens_T600") & (sm.지표 == "COV_cost_lz_종합")].set_index("year")
    ok = all(main_cost.loc[int(y), "A−B_중앙차"] >= 0.01 and main_cost.loc[int(y), "p_A_vs_B"] < 0.05 and t6_cost.loc[int(y), "A−B_중앙차"] > 0 for y in C.YEARS)
    S["판정"] = "겹친다(가설 지지)" if ok else "겹치지 않음 또는 불확실"
    S["경계비용_COV_main"] = main_cost[["A_n", "A_중앙", "A*_중앙", "B_n", "B_중앙", "C_중앙", "A−B_중앙차", "p_A_vs_B", "A>0_비율", "B>0_비율"]].round(4).to_dict("index")
    S["경계비용_COV_T600"] = t6_cost[["A_중앙", "B_중앙", "A−B_중앙차", "p_A_vs_B"]].round(4).to_dict("index")
    S["가상경계_접근성차_ΔCOV_main"] = sm[(sm.tag == "main") & (sm.지표 == "COV_dLDLZ_종합")].set_index("year")[["A_중앙", "B_중앙", "A>0_비율", "B>0_비율", "p_A_vs_B"]].round(4).to_dict("index")
    S["MAI_경계비용_main(보조)"] = sm[(sm.tag == "main") & (sm.지표 == "MAI_cost_lz_종합")].set_index("year")[["A_중앙", "B_중앙", "p_A_vs_B"]].round(4).to_dict("index")
    S["카테고리_경계비용_A−B(2025,큰순)"] = ct[ct.year == int(C.Y1)].sort_values("A−B", ascending=False)[["cat", "A_평균", "B_평균", "A−B", "p"]].round(4).to_dict("records")
    (OUT / "b5_summary.json").write_text(json.dumps(S, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps(S, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
