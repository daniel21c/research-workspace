# -*- coding: utf-8 -*-
"""
k16 — 재배정 권고 동은 왜 옆 생활권으로 가나: 역세권·상권·문화시설·일자리 가설 확인

가설: 재배정 권고 동(A)은 지하철역·대형 상업시설·문화시설·일자리가 자기 생활권보다
      옮겨 갈 생활권(목표 권역) 쪽에 더 가까이·더 많이 있다.
비교 집단: 그 밖의 경계 동(B) — 옆 생활권과 맞닿아 있으나 재배정이 권고되지 않은 동.
           B의 비교 권역은 맞닿은 옆 생활권 중 (자기 동 내부통행 제외) 통행을 가장 많이 보내는 권역.

동의 위치 = 격자 인구가중 중심(해당 연도 인구: 2020→2019, 2025→2024). 거리는 EPSG:5179 직선거리(m).
끌개(attractor):
  역     지하철역
  대형상업 대규모점포(주요4업태)
  문화    문화 카테고리(공공도서관·문화기반시설·등록공연장)
  일자리  격자 종사자 수(권역 합) — 상권·업무 중심의 대리 지표
지표(동마다):
  closer_nb[x] = 옆(목표) 권역의 가장 가까운 x가 자기 권역의 가장 가까운 x보다 가까운가(자기 권역에 x가 없으면 옆 권역에 있을 때 참)
  gap_m[x]     = 자기 권역 최근접 거리 − 옆 권역 최근접 거리 (양수 = 옆이 더 가까움)
  emp_ratio    = 옆 권역 종사자 / 자기 권역 종사자 (로그)
사전 판정 기준(계산 전에 고정):
  어떤 끌개 x에 대해 "A에서 closer_nb 비율이 B보다 10%p 이상 높고 Fisher p < 0.05"가 두 해 모두 성립하면 x 가설 지지.
  일자리는 log(emp_ratio) 중앙값이 A > B, Mann–Whitney p < 0.05 가 두 해 모두 성립하면 지지.
출력: output/tables/benchmark/b6_dong_attractors.csv, b6_summary.json
"""
from __future__ import annotations
import json, sys
import numpy as np
import pandas as pd
from scipy import stats
import config as C

OUT = C.TAB / "benchmark"
PKG = C.ACC_DATA / "입력"
FAC = PKG / "facility" / "facility_2020_2025_units.parquet"; GRID = PKG / "grid" / "grid100_master.parquet"
POPYEAR = {int(C.Y0): 2019, int(C.Y1): 2024}


def main():
    lzm = pd.read_csv(C.LZ_MAP, encoding="utf-8-sig").set_index("Dong"); zname = lzm.life_zone_name; zid = lzm.life_zone_id
    name2id = dict(zip(lzm.life_zone_name, lzm.life_zone_id))
    greedy = pd.read_csv(OUT / "b4_greedy_moves.csv", encoding="utf-8-sig")
    single = pd.read_csv(OUT / "b4_single_moves.csv", encoding="utf-8-sig")
    g = pd.read_parquet(GRID, columns=["x_c", "y_c", "dong424", "lz116", "pop_2019", "pop_2024", "emp_2019", "emp_2024"])
    f = pd.read_parquet(FAC, columns=["year", "시설", "cat_A", "분석가능", "x_5179", "y_5179", "dong424"])
    f = f[f["분석가능"] & f.dong424.notna()].copy(); f["dong424"] = f.dong424.astype(int); f["lz"] = f.dong424.map(zid)
    rows = []; S = {"사전기준": "끌개 x: A의 closer_nb 비율이 B보다 10%p 이상 높고 Fisher p<0.05(두 해 모두). 일자리: log(emp_ratio) A>B, MW p<0.05(두 해 모두)"}
    for y in (int(C.Y0), int(C.Y1)):
        py = POPYEAR[y]
        gg = g[g[f"pop_{py}"] > 0]
        cen = gg.groupby("dong424").apply(lambda d: pd.Series({"x": np.average(d.x_c, weights=d[f"pop_{py}"]), "y": np.average(d.y_c, weights=d[f"pop_{py}"])}), include_groups=False)
        emp_z = g.groupby("lz116")[f"emp_{py}"].sum()
        fy = f[f.year == y]
        att = {"역": fy[fy["시설"] == "지하철역"], "대형상업": fy[fy["시설"] == "대규모점포(주요4업태)"], "문화": fy[fy.cat_A == "문화"]}
        od = pd.read_parquet(C.od_daily(str(y)), columns=["dong_O", "dong_D", "flow"]); od = od[od.dong_O != od.dong_D]
        od["zD"] = od.dong_D.map(zid)
        moved = greedy[greedy.year == y].set_index("dong")["to_zone"].to_dict()
        cand = single[single.year == y].groupby("dong").to_zone.apply(lambda s: sorted(set(s))).to_dict()
        for d, zs in cand.items():
            own = zid[d]
            if d in moved: grp, tgt = "A", name2id[moved[d]]
            else:
                grp = "B"; out = od[od.dong_O == d].groupby("zD").flow.sum()
                ids = [name2id[z] for z in zs]; tgt = max(ids, key=lambda z: out.get(z, 0.0))
            if d not in cen.index: continue
            cx, cy = cen.loc[d, "x"], cen.loc[d, "y"]
            r = {"year": y, "dong": d, "dong_name": lzm.loc[d, "ADM_NM"], "ku_name": lzm.loc[d, "ku_name"], "group": grp, "own_zone": zname[d], "target_zone": lzm[lzm.life_zone_id == tgt].life_zone_name.iat[0]}
            for k, a in att.items():
                def nearest(z):
                    s = a[a.lz == z]
                    return float(np.hypot(s.x_5179 - cx, s.y_5179 - cy).min()) if len(s) else np.inf
                do, dn = nearest(own), nearest(tgt)
                r[f"dist_own_{k}"] = do; r[f"dist_nb_{k}"] = dn
                r[f"closer_nb_{k}"] = bool(dn < do); r[f"gap_m_{k}"] = (do - dn) if np.isfinite(do) and np.isfinite(dn) else np.nan
                r[f"n_own_{k}"] = int((a.lz == own).sum()); r[f"n_nb_{k}"] = int((a.lz == tgt).sum())
            r["log_emp_ratio"] = float(np.log((emp_z.get(tgt, 0) + 1) / (emp_z.get(own, 0) + 1)))
            rows.append(r)
    df = pd.DataFrame(rows); df.to_csv(OUT / "b6_dong_attractors.csv", index=False, encoding="utf-8-sig")
    res = {}
    for y in (int(C.Y0), int(C.Y1)):
        dy = df[df.year == y]; A, B = dy[dy.group == "A"], dy[dy.group == "B"]; res[y] = {}
        for k in ("역", "대형상업", "문화"):
            a1, b1 = int(A[f"closer_nb_{k}"].sum()), int(B[f"closer_nb_{k}"].sum())
            p = stats.fisher_exact([[a1, len(A) - a1], [b1, len(B) - b1]])[1]
            res[y][k] = {"A_옆이더가까움_비율": round(a1 / len(A), 3), "B_비율": round(b1 / len(B), 3), "차이_%p": round((a1 / len(A) - b1 / len(B)) * 100, 1), "p": round(float(p), 4),
                         "A_거리차_중앙_m": round(float(A[f"gap_m_{k}"].median()), 0), "B_거리차_중앙_m": round(float(B[f"gap_m_{k}"].median()), 0)}
        pe = stats.mannwhitneyu(A.log_emp_ratio, B.log_emp_ratio, alternative="two-sided").pvalue
        res[y]["일자리"] = {"A_옆/자기_종사자비_중앙": round(float(np.exp(A.log_emp_ratio.median())), 2), "B": round(float(np.exp(B.log_emp_ratio.median())), 2), "p": round(float(pe), 4)}
        res[y]["n"] = {"A": len(A), "B": len(B)}
    S["결과"] = res
    verdict = {}
    for k in ("역", "대형상업", "문화"):
        verdict[k] = "지지" if all(res[y][k]["차이_%p"] >= 10 and res[y][k]["p"] < 0.05 for y in res) else "지지 안 됨"
    verdict["일자리"] = "지지" if all(res[y]["일자리"]["A_옆/자기_종사자비_중앙"] > res[y]["일자리"]["B"] and res[y]["일자리"]["p"] < 0.05 for y in res) else "지지 안 됨"
    S["판정"] = verdict
    both = set(greedy[greedy.year == int(C.Y0)].dong) & set(greedy[greedy.year == int(C.Y1)].dong)
    d25 = df[(df.year == int(C.Y1)) & df.dong.isin(both)]
    S["두해공통_권고동(2025)_옆이더가까운비율"] = {k: round(float(d25[f"closer_nb_{k}"].mean()), 3) for k in ("역", "대형상업", "문화")} | {"n": len(d25), "종사자비_중앙": round(float(np.exp(d25.log_emp_ratio.median())), 2)}
    (OUT / "b6_summary.json").write_text(json.dumps(S, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps(S, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
