# -*- coding: utf-8 -*-
"""
x10_k_targets.py — 개수 민감도 실행용 구별 목표 개수 파일 만들기 (계산 가벼움, 수초)
=====================================================================================
x9 가 만든 output/exploration/k_methods.csv 에서, 이동 기반 4개 방법의 구별 개수 중앙값을 목표 개수로 쓴다.
  방법: A1_등가k(반올림), B1_Q최대k, B2_SBM동류k, C1_TTWA_k(합116)
  B3(귀무모형 z)은 작은 개수(2)로 치우쳐 개수 선택보다 진단용으로 쓰기로 해 뺐다(해석_메모 §5).
중앙값이 .5 로 떨어지는 구가 많아(2020 9곳, 2025 12곳) 두 가지로 반올림해 범위를 본다.
  kmob_lo : .5 를 공식 개수 쪽으로   → 2020 합 120, 2025 합 125 (공식과 다른 구 8, 9곳)
  kmob_hi : .5 를 공식에서 먼 쪽으로 → 2020 합 123, 2025 합 133 (공식과 다른 구 14, 19곳)
결과: output/exploration/k_targets_kmob_lo.csv, k_targets_kmob_hi.csv  (열: year, ku_code, ku_name, official_k, median4, target)
이 파일을 s03 --targets 에 준다 (scripts/s06_sensitivity.py 머리말 참고). 정본은 바꾸지 않는다.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import config as C  # noqa: E402

M4 = ["A1_등가k", "B1_Q최대k", "B2_SBM동류k", "C1_TTWA_k(합116)"]
OUT = C.OUTPUT_DIR / "exploration"


def main():
    d = pd.read_csv(OUT / "k_methods.csv", encoding="utf-8-sig")
    d["A1_등가k"] = d["A1_등가k"].round()
    code = {v: k for k, v in C.KU_NAME.items()}
    d["ku_code"] = d["구"].map(code)
    assert d["ku_code"].notna().all()
    d["median4"] = d[M4].median(axis=1)
    half = (d["median4"] % 1) == 0.5
    up = d["median4"] > d["공식k"]
    toward = np.where(half, np.where(up, np.floor(d["median4"]), np.ceil(d["median4"])), d["median4"])
    away = np.where(half, np.where(up, np.ceil(d["median4"]), np.floor(d["median4"])), d["median4"])
    for name, t in [("kmob_lo", toward), ("kmob_hi", away)]:
        x = pd.DataFrame({"year": d["year"].astype(str), "ku_code": d["ku_code"].astype(int), "ku_name": d["구"],
                          "official_k": d["공식k"].astype(int), "median4": d["median4"], "target": t.astype(int)})
        x.to_csv(OUT / f"k_targets_{name}.csv", index=False, encoding="utf-8-sig")
        for y, g in x.groupby("year"):
            diff = g[g["target"] != g["official_k"]]
            print(f"{name} {y}: 합 {g['target'].sum()} (공식 {g['official_k'].sum()}), 다른 구 {len(diff)}: "
                  + ", ".join(f"{r.ku_name} {r.official_k}->{r.target}" for r in diff.itertuples()))
    print(f"wrote {OUT / 'k_targets_kmob_lo.csv'}, {OUT / 'k_targets_kmob_hi.csv'}")


if __name__ == "__main__":
    main()
