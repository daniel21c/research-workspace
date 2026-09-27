# -*- coding: utf-8 -*-
"""
k14 — 경계 동 재배정 시험: "옆 생활권으로 옮기면 실제로 나아지는가?"

k13에서 공식 생활권 동의 약 30%가 자기 생활권보다 옆 생활권으로 더 많이 간다는 결과가 나왔다.
그런데 IFR은 큰 권역에 유리한 크기 편향이 있어(k13), 큰 이웃 쪽으로 동을 옮기면 IFR은 "당연히" 오를 수 있다.
그래서 두 기준을 함께 본다.
  ΔIFR  구 IFR의 변화(출발 통행 중 같은 권역 안에서 끝나는 비율). 크기 편향이 있음
  ΔQ    모듈성 변화. 동의 통행 규모(가중 차수)로 기대되는 통행을 빼고 보므로 크기 편향을 통제함
        (빅데이터 기반 가상경계를 만들 때 쓴 목적함수와 같은 정의: 구 안 무방향 그래프 w_ij + w_ji, 자기 루프 포함)
  → ΔIFR > 0 이고 ΔQ > 0 이면 "크기 효과가 아닌 진짜 개선"으로 본다.

제약: 옮긴 뒤 권역 수 유지(원래 권역이 비지 않음), 원래 권역이 공간적으로 끊기지 않음, 옮겨 갈 권역은 그 동과 인접.

분석
  (1) 한 동씩 옮기기: 공식 생활권의 모든 경계 동 × 인접 권역에 대해 ΔIFR·ΔQ·Δ(가상경계와의 판정차 D)
  (2) 탐욕적 재배정: ΔQ가 가장 큰 이동부터 하나씩 적용, 더 이상 ΔQ > 0인 이동이 없을 때까지
      → 몇 개 동을 옮기면 되는지, IFR·Q·D가 얼마나 바뀌는지, 두 해 모두 권고되는 이동은 무엇인지
출력: output/tables/benchmark/b4_single_moves.csv, b4_greedy_moves.csv, b4_gu_summary.csv, b4_summary.json
"""
from __future__ import annotations
import json, sys
from collections import deque
import numpy as np
import pandas as pd
import config as C
from k01_compute import build_adjacency

OUT = C.TAB / "benchmark"; OUT.mkdir(parents=True, exist_ok=True)


def connected(members, adj_idx):
    members = set(members)
    if len(members) <= 1: return True
    start = next(iter(members)); seen = {start}; q = deque([start])
    while q:
        v = q.popleft()
        for j in adj_idx[v]:
            if j in members and j not in seen: seen.add(j); q.append(j)
    return len(seen) == len(members)


def ifr(W, Tsum, lab):
    return float((W * (lab[:, None] == lab[None, :])).sum() / Tsum)


def modularity(A, lab):
    k = A.sum(1); m2 = A.sum()
    same = lab[:, None] == lab[None, :]
    return float(((A - np.outer(k, k) / m2) * same).sum() / m2)


def dmis(W, Tsum, lz, ld):
    """가상경계와의 판정차 D(구 안 통행만 판정이 갈릴 수 있음; 구 밖 도착은 두 경계 모두 외부)."""
    sz = lz[:, None] == lz[None, :]; sd = ld[:, None] == ld[None, :]
    return float((W * (sz ^ sd)).sum() / Tsum)


def main():
    adj, _ = build_adjacency()
    lzm = pd.read_csv(C.LZ_MAP, encoding="utf-8-sig").set_index("Dong")
    ldm = {y: pd.read_csv(C.ld_map(y), encoding="utf-8-sig").set_index("Dong")["global_community_id"] for y in C.YEARS}
    od = {y: pd.read_parquet(C.od_daily(y), columns=["dong_O", "dong_D", "flow"]) for y in C.YEARS}
    mis = pd.read_csv(OUT / "b3_dong.csv", encoding="utf-8-sig"); mis = mis[mis.boundary == "LZ"].set_index(["year", "dong"])["misassigned"]
    single, greedy, gsum = [], [], []
    for K, grp in lzm.groupby("Ku"):
        nodes = sorted(grp.index.tolist()); pos = {d: i for i, d in enumerate(nodes)}; n = len(nodes)
        adj_idx = [[pos[j] for j in adj[d] if j in pos] for d in nodes]
        zname = grp.loc[nodes, "life_zone_name"].values
        lz0 = pd.factorize(grp.loc[nodes, "life_zone_id"])[0]; zlabel = {int(l): zname[i] for i, l in enumerate(lz0)}
        name = grp["ku_name"].iat[0]
        for y in C.YEARS:
            o = od[y][od[y].dong_O.isin(pos)]; Tsum = float(o.flow.sum())
            w = o[o.dong_D.isin(pos)]; W = np.zeros((n, n))
            np.add.at(W, (w.dong_O.map(pos).values, w.dong_D.map(pos).values), w.flow.values)
            A = W + W.T
            ld = pd.factorize(ldm[y].loc[nodes])[0]
            base = (ifr(W, Tsum, lz0), modularity(A, lz0), dmis(W, Tsum, lz0, ld))

            def moves(lab):
                out = []
                for i in range(n):
                    a = lab[i]; members = np.where(lab == a)[0]
                    if len(members) < 2 or not connected([m for m in members if m != i], adj_idx): continue
                    for b in {lab[j] for j in adj_idx[i]} - {a}:
                        new = lab.copy(); new[i] = b
                        out.append((i, a, b, new))
                return out

            # (1) 한 동씩
            I0, Q0, D0 = base
            for i, a, b, new in moves(lz0):
                d = nodes[i]
                single.append({"year": int(y), "ku_name": name, "dong": d, "dong_name": grp.loc[d, "ADM_NM"], "from_zone": zlabel[a], "to_zone": zlabel[b],
                               "misassigned_k13": bool(mis.get((int(y), d), False)),
                               "dIFR_pp": (ifr(W, Tsum, new) - I0) * 100, "dQ": modularity(A, new) - Q0, "dD_pp": (dmis(W, Tsum, new, ld) - D0) * 100})
            # (2) 탐욕적 재배정 (ΔQ 최대 우선)
            lab = lz0.copy(); step = 0; Qc = Q0
            while True:
                best = None
                for i, a, b, new in moves(lab):
                    q = modularity(A, new)
                    if q - Qc > 1e-12 and (best is None or q - Qc > best[0]): best = (q - Qc, i, a, b, new)
                if best is None or step >= n: break
                dq, i, a, b, new = best; step += 1; d = nodes[i]
                greedy.append({"year": int(y), "ku_name": name, "step": step, "dong": d, "dong_name": grp.loc[d, "ADM_NM"],
                               "from_zone": zlabel[a], "to_zone": zlabel[b], "dQ": dq,
                               "dIFR_pp": (ifr(W, Tsum, new) - ifr(W, Tsum, lab)) * 100})
                lab = new; Qc = modularity(A, lab)
            I1, Q1, D1 = ifr(W, Tsum, lab), Qc, dmis(W, Tsum, lab, ld)
            gsum.append({"year": int(y), "ku_name": name, "n_dong": n, "k": int(lz0.max() + 1), "n_moved": step,
                         "IFR_before": I0, "IFR_after": I1, "dIFR_pp": (I1 - I0) * 100, "Q_before": Q0, "Q_after": Q1,
                         "Q_LD": modularity(A, ld), "IFR_LD": ifr(W, Tsum, ld), "D_before": D0, "D_after": D1, "T": Tsum})
        print(name, "완료", flush=True)
    s = pd.DataFrame(single); g = pd.DataFrame(greedy); gs = pd.DataFrame(gsum)
    s.to_csv(OUT / "b4_single_moves.csv", index=False, encoding="utf-8-sig"); g.to_csv(OUT / "b4_greedy_moves.csv", index=False, encoding="utf-8-sig"); gs.to_csv(OUT / "b4_gu_summary.csv", index=False, encoding="utf-8-sig")
    R = {}
    for y in (int(C.Y0), int(C.Y1)):
        sy = s[s.year == y]
        best_per_dong = sy.sort_values("dQ", ascending=False).drop_duplicates("dong")
        for flag, lab_ in ((True, "옆생활권지향동"), (False, "그밖의_경계동")):
            b = best_per_dong[best_per_dong.misassigned_k13 == flag]
            R[f"{y}_{lab_}"] = {"n": len(b), "ΔIFR>0": int((b.dIFR_pp > 0).sum()), "ΔQ>0": int((b.dQ > 0).sum()), "둘다>0": int(((b.dIFR_pp > 0) & (b.dQ > 0)).sum()),
                                "ΔIFR>0_ΔQ≤0(크기효과)": int(((b.dIFR_pp > 0) & (b.dQ <= 0)).sum())}
        gy = gs[gs.year == y]; TT = gy["T"].sum()
        R[f"{y}_탐욕재배정"] = {"옮긴_동": int(gy.n_moved.sum()), "옮긴_구": int((gy.n_moved > 0).sum()),
                            "서울IFR_전": round(float((gy.IFR_before * gy["T"]).sum() / TT * 100), 2), "서울IFR_후": round(float((gy.IFR_after * gy["T"]).sum() / TT * 100), 2),
                            "서울IFR_가상경계": round(float((gy.IFR_LD * gy["T"]).sum() / TT * 100), 2),
                            "서울D_전": round(float((gy.D_before * gy["T"]).sum() / TT * 100), 2), "서울D_후": round(float((gy.D_after * gy["T"]).sum() / TT * 100), 2),
                            "Q_전_중앙": round(float(gy.Q_before.median()), 4), "Q_후_중앙": round(float(gy.Q_after.median()), 4), "Q_가상경계_중앙": round(float(gy.Q_LD.median()), 4)}
    g20 = set(g[g.year == int(C.Y0)][["dong", "to_zone"]].itertuples(index=False, name=None)); g25 = set(g[g.year == int(C.Y1)][["dong", "to_zone"]].itertuples(index=False, name=None))
    R["두해모두_권고_이동"] = len(g20 & g25); R["2020만"] = len(g20 - g25); R["2025만"] = len(g25 - g20)
    both = g[(g.year == int(C.Y1)) & g.apply(lambda r: (r.dong, r.to_zone) in g20, axis=1)]
    R["두해모두_권고_목록"] = [f"{r.ku_name} {r.dong_name}: {r.from_zone} → {r.to_zone}" for r in both.itertuples()]
    (OUT / "b4_summary.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(R, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
