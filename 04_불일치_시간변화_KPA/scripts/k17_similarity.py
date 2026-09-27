# -*- coding: utf-8 -*-
"""
k17 — 재배정 권고 동은 "비슷한 주거지 이웃"과 이어지는가 (중심지–배후지 가설)

배경: 서울생활권계획 백서(2019)는 지역생활권을 "지구중심·역세권 등의 생활중심지와 그 배후주거지를 포함"하도록
      나눴다고 적는다(중심지–배후지 구조). k16에서 재배정 권고 동은 일자리가 적은 옆 생활권 쪽으로 옮겨야 했다.
가설: 권고 동(A)은 자기 생활권(중심지 성격)보다 옮겨 갈 생활권과 주거 특성이 더 비슷하다.
      그 밖의 경계 동(B)은 그렇지 않다.
주거 특성(격자 합산, 해당 연도: 2020→2019, 2025→2024)
  업무성    log(종사자 / 인구)        높을수록 업무·상업 중심
  가구규모  인구 / 가구
  밀도      인구 / 인구 있는 100m 격자 수
  권역 값은 그 동을 뺀 나머지 동의 합으로 계산(자기 자신과의 유사성 제외). 세 특성을 동 전체 기준 표준화 후 유클리드 거리.
사전 판정 기준(계산 전에 고정):
  "옮겨 갈 권역이 자기 권역보다 더 비슷한 동"의 비율이 A에서 B보다 10%p 이상 높고 Fisher p < 0.05 (두 해 모두) → 가설 지지.
  보조: A의 자기 권역이 A 동보다 업무성이 높은가(중심지 쪽에 붙어 있음) — 업무성 차(권역−동) 중앙값 A > B, MW p < 0.05.
출력: output/tables/benchmark/b7_similarity.csv, b7_summary.json
"""
from __future__ import annotations
import json, sys
import numpy as np
import pandas as pd
from scipy import stats
import config as C

OUT = C.TAB / "benchmark"
GRID = C.ACC_DATA / "입력" / "grid" / "grid100_master.parquet"
POPYEAR = {int(C.Y0): 2019, int(C.Y1): 2024}


def main():
    lzm = pd.read_csv(C.LZ_MAP, encoding="utf-8-sig").set_index("Dong"); zid = lzm.life_zone_id
    name2id = dict(zip(lzm.life_zone_name, lzm.life_zone_id))
    att = pd.read_csv(OUT / "b6_dong_attractors.csv", encoding="utf-8-sig")       # A/B 집단과 목표 권역(k16과 같은 정의)
    g = pd.read_parquet(GRID)
    rows = []
    for y in (int(C.Y0), int(C.Y1)):
        py = POPYEAR[y]
        agg = g.groupby("dong424").agg(pop=(f"pop_{py}", "sum"), hh=(f"hh_{py}", "sum"), emp=(f"emp_{py}", "sum"), ncell=(f"pop_pos_{py}", "sum"))
        agg = agg[agg["pop"] > 0]; agg["lz"] = agg.index.map(zid)

        def feats(pop, hh, emp, ncell):
            return np.array([np.log((emp + 1) / pop), pop / max(hh, 1), pop / max(ncell, 1)])
        F = np.vstack([feats(*agg.loc[d, ["pop", "hh", "emp", "ncell"]]) for d in agg.index]); mu, sd = F.mean(0), F.std(0)
        zsum = agg.groupby("lz")[["pop", "hh", "emp", "ncell"]].sum()
        ay = att[att.year == y]
        for r in ay.itertuples():
            d = r.dong
            if d not in agg.index: continue
            own, tgt = zid[d], name2id[r.target_zone]
            me = agg.loc[d, ["pop", "hh", "emp", "ncell"]]
            own_rest = zsum.loc[own] - me
            if own_rest["pop"] <= 0: continue
            fd = (feats(*me) - mu) / sd; fo = (feats(*own_rest) - mu) / sd; ft = (feats(*zsum.loc[tgt]) - mu) / sd
            rows.append({"year": y, "dong": d, "dong_name": r.dong_name, "ku_name": r.ku_name, "group": r.group, "own_zone": r.own_zone, "target_zone": r.target_zone,
                         "dist_own": float(np.linalg.norm(fd - fo)), "dist_tgt": float(np.linalg.norm(fd - ft)),
                         "업무성_동": float(feats(*me)[0]), "업무성_자기권역": float(feats(*own_rest)[0]), "업무성_목표권역": float(feats(*zsum.loc[tgt])[0])})
    df = pd.DataFrame(rows); df["tgt_more_similar"] = df.dist_tgt < df.dist_own
    df["업무성차_자기권역−동"] = df["업무성_자기권역"] - df["업무성_동"]; df["업무성차_목표권역−동"] = df["업무성_목표권역"] - df["업무성_동"]
    df.to_csv(OUT / "b7_similarity.csv", index=False, encoding="utf-8-sig")
    S = {"사전기준": "옮겨 갈 권역이 더 비슷한 동 비율 A−B ≥ 10%p, Fisher p<0.05(두 해 모두). 보조: 업무성차(자기권역−동) A>B, MW p<0.05"}
    res = {}
    for y in (int(C.Y0), int(C.Y1)):
        x = df[df.year == y]; A, B = x[x.group == "A"], x[x.group == "B"]
        a1, b1 = int(A.tgt_more_similar.sum()), int(B.tgt_more_similar.sum())
        p = stats.fisher_exact([[a1, len(A) - a1], [b1, len(B) - b1]])[1]
        pw = stats.mannwhitneyu(A["업무성차_자기권역−동"], B["업무성차_자기권역−동"], alternative="two-sided").pvalue
        res[y] = {"n": {"A": len(A), "B": len(B)},
                  "옮겨갈권역이_더비슷한_비율": {"A": round(a1 / len(A), 3), "B": round(b1 / len(B), 3), "차이_%p": round((a1 / len(A) - b1 / len(B)) * 100, 1), "p": round(float(p), 4)},
                  "업무성차_자기권역−동_중앙(배, exp)": {"A": round(float(np.exp(A["업무성차_자기권역−동"].median())), 2), "B": round(float(np.exp(B["업무성차_자기권역−동"].median())), 2), "p": round(float(pw), 4)},
                  "업무성차_목표권역−동_중앙(배, exp)": {"A": round(float(np.exp(A["업무성차_목표권역−동"].median())), 2), "B": round(float(np.exp(B["업무성차_목표권역−동"].median())), 2)}}
    S["결과"] = res
    S["판정_유사성"] = "지지" if all(res[y]["옮겨갈권역이_더비슷한_비율"]["차이_%p"] >= 10 and res[y]["옮겨갈권역이_더비슷한_비율"]["p"] < 0.05 for y in res) else "지지 안 됨"
    S["판정_중심지쪽_배정"] = "지지" if all(res[y]["업무성차_자기권역−동_중앙(배, exp)"]["A"] > res[y]["업무성차_자기권역−동_중앙(배, exp)"]["B"] and res[y]["업무성차_자기권역−동_중앙(배, exp)"]["p"] < 0.05 for y in res) else "지지 안 됨"
    (OUT / "b7_summary.json").write_text(json.dumps(S, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps(S, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
