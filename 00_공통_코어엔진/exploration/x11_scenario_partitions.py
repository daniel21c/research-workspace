# -*- coding: utf-8 -*-
"""
x11_scenario_partitions.py — 최적화 검증 시나리오의 동별 라벨 모으기 (수초)
==========================================================================
설계: exploration/최적화검증_설계.md. 정본은 읽기만 하고, 결과는 output/proposal/ 에 쓴다.

시나리오 (라벨은 구 안에서만 의미가 있는 정수; P4 만 서울 전체 라벨)
  P0   공식 생활권                       data/dong_to_official_livingzone_mapping (life_zone_id)
  P0c  정본 Leiden (116)                 output/leiden/{year}/metrics/leiden_mapping
  P1   구별 Q 최대 개수 Leiden           output/leiden/{year}_qmax  ← s03 --targets 로 만든 뒤 x12 가 읽는다 (여기서는 목표 파일만 만든다)
  P2   TTWA 자족성 문턱 0.25 (두 해 같음)  output/exploration/x6/ttwa_labels.csv  (인구하한 0)
  P2a  TTWA 문턱 0.20, P2b 문턱 0.30       같은 파일 (문턱 민감도)
  P3   max-p 인구 하한 70,000              output/exploration/x7/maxp_labels.csv
  P4   서울 전체 Leiden k≈116 (구 경계 없음) output/exploration/x8/citywide_labels.csv (참고용, 서울 지표만)

출력: output/proposal/partitions.csv (year, Dong, Ku, scenario, label), k_targets_qmax.csv (year, ku_code, ku_name, official_k, target)
"""
import pandas as pd
from xcommon import *

PROP = C.OUTPUT_DIR / "proposal"
SCEN_DESC = {"P0": "공식 생활권", "P0c": "정본 Leiden(116)", "P1": "Q 최대 개수 Leiden", "P2": "TTWA 문턱 0.25",
             "P2a": "TTWA 문턱 0.20", "P2b": "TTWA 문턱 0.30", "P3": "max-p 인구 하한 7만", "P4": "서울 전체 Leiden k≈116",
             "P5": "이중 목표: Q 최대 + 권역 인구 ≥ 2만 (공식 개수)", "P5_30k": "이중 목표: 인구 ≥ 3만", "P5_50k": "이중 목표: 인구 ≥ 5만"}


def main():
    PROP.mkdir(parents=True, exist_ok=True)
    dong = load_dong()[["Dong", "Ku"]]
    lz = load_lz()
    rows = []
    def add(year, scen, series):
        s = pd.Series(series).reindex(dong["Dong"])
        if s.isna().any():
            raise SystemExit(f"{scen} {year}: 라벨 없는 동 {int(s.isna().sum())}개")
        for d, k, l in zip(dong["Dong"], dong["Ku"], s.values):
            rows.append({"year": year, "Dong": int(d), "Ku": int(k), "scenario": scen, "label": int(l)})
    ttwa = pd.read_csv(OUT / "x6" / "ttwa_labels.csv", encoding="utf-8-sig")
    maxp = pd.read_csv(OUT / "x7" / "maxp_labels.csv", encoding="utf-8-sig")
    city = pd.read_csv(OUT / "x8" / "citywide_labels.csv", encoding="utf-8-sig")
    for year in YEARS:
        y = int(year)
        add(year, "P0", lz["life_zone_id"])
        m, _ = load_leiden(year)
        add(year, "P0c", m["global_community_id"])
        for scen, t in (("P2", 0.25), ("P2a", 0.20), ("P2b", 0.30)):
            x = ttwa[(ttwa.year == y) & (ttwa["인구하한"] == 0) & (abs(ttwa["SC문턱"] - t) < 1e-9)]
            add(year, scen, x.set_index("Dong")["label"])
        x = maxp[(maxp.year == y) & (maxp["인구하한"] == 70000)]
        add(year, "P3", x.set_index("Dong")["label"])
        x = city[(city.year == y) & (city["선택"] == "k≈116")]
        add(year, "P4", x.set_index("Dong")["label"])
    d = pd.DataFrame(rows)
    p5 = PROP / "p5_partitions.csv"          # x14 결과 (있으면 합친다)
    if p5.exists():
        x = pd.read_csv(p5, encoding="utf-8-sig"); x["year"] = x["year"].astype(str)
        d["year"] = d["year"].astype(str)
        d = pd.concat([d, x[["year", "Dong", "Ku", "scenario", "label"]]], ignore_index=True)
        print(f"P5 계열 합침: {sorted(x.scenario.unique())}")
    d.to_csv(PROP / "partitions.csv", index=False, encoding="utf-8-sig")
    # 구 안에서 라벨을 0..k-1 로 정리했는지와 개수 요약
    summ = d[d.scenario != "P4"].groupby(["year", "scenario", "Ku"])["label"].nunique().groupby(level=[0, 1]).sum().unstack()
    print("구별 개수 합계:\n", summ.to_string())
    # P1 목표 개수: x9 의 B1_Q최대k
    km = pd.read_csv(OUT / "k_methods.csv", encoding="utf-8-sig")
    code = {v: k for k, v in C.KU_NAME.items()}
    t = pd.DataFrame({"year": km["year"].astype(str), "ku_code": km["구"].map(code).astype(int), "ku_name": km["구"],
                      "official_k": km["공식k"].astype(int), "target": km["B1_Q최대k"].astype(int)})
    t.to_csv(PROP / "k_targets_qmax.csv", index=False, encoding="utf-8-sig")
    for y, g in t.groupby("year"):
        print(f"P1 목표 {y}: 합 {g.target.sum()} (공식 {g.official_k.sum()}), 다른 구 {(g.target != g.official_k).sum()}")
    pd.Series(SCEN_DESC).rename("설명").to_csv(PROP / "scenarios.csv", encoding="utf-8-sig", index_label="scenario")
    print(f"wrote {PROP / 'partitions.csv'}, {PROP / 'k_targets_qmax.csv'}")


if __name__ == "__main__":
    main()
