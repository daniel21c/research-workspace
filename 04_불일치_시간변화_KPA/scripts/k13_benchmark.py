# -*- coding: utf-8 -*-
"""
k13 — 무작위 비교경계 대비 평가: 구 → 생활권 → 동 세 단위, 크기 통제 3종

질문: 공식 생활권(LZ)과 빅데이터 기반 가상경계(LD)는 "이동 정보 없이 붙어 있는 동끼리 무작위로 묶은 경계"보다
통행을 얼마나 더 잘 담는가? 그리고 그 결과는 권역 크기 차이 때문인가?

무작위 비교경계(모두 같은 구 안, 공간적으로 연속, 권역 개수 = 비교 대상 경계의 개수)
  N0  크기 제약 없음 (기존 k01의 귀무 분할과 같은 방식)
  N1  권역별 동 수를 비교 대상 경계와 똑같이 맞춤 (예: 공식 생활권이 5·4·4동이면 무작위도 5·4·4동)
  N2  N1 + 권역별 출발 통행량 비중까지 비슷하게 맞춤 (정렬한 비중 벡터의 최대 차이 ≤ 허용치)
  LZ와 LD는 크기 구성이 다르므로 각자 자기 크기에 맞춘 N1·N2와 비교한다.

평가 단위
  (1) 구 단위: 구 IFR = 구 안 모든 권역의 내부 통행 합 / 구 출발 통행 합  → 무작위 대비 백분위
  (2) 생활권 단위: 권역 z의 IFR_z = z 출발 통행 중 z 안에서 끝나는 비율 → 같은 구·같은 동 수의 무작위 연속 동 집합 대비 백분위
  (3) 동 단위: 동 d의 포착률 c_d = d 출발 통행 중 d가 속한 권역 안에서 끝나는 비율 → N1 분할에서 같은 동의 c_d 분포 대비 백분위
      + "이웃 권역이 더 많이 담는 동": 자기 동 내부통행을 빼고, 같은 구 안에서 가장 많이 가는 권역이 자기 권역이 아닌 동
백분위 = (무작위 값 < 경계 값인 비율) + 0.5 × (같은 비율). 0.5 = 무작위와 같음, 1 = 무작위보다 항상 나음.

출력: output/tables/benchmark/b1_gu.csv, b2_zone.csv, b3_dong.csv, b3_dong_misassigned.csv, b_summary.json, b_null_meta.csv
실행: python k13_benchmark.py
"""
from __future__ import annotations
import json, sys, time
from collections import defaultdict
import numpy as np
import pandas as pd
import config as C
from k01_compute import build_adjacency

OUT = C.TAB / "benchmark"; OUT.mkdir(parents=True, exist_ok=True)
N_NULL = 1000; SEED = 20260927; N2_TOL = (0.05, 0.08, 0.12); N2_MAX_TRY = 40000
rng = np.random.default_rng(SEED)


TIE_ATOL = 1e-12      # 동률 판정 절대허용오차: 같은 구성원 권역을 다른 합산 순서로 계산할 때의 부동소수 오차(~1e-16)만 동률로 본다


def pct(v, arr):
    """백분위 = (v보다 작은 비교값 수 + 0.5 × 동률 수) / 비교값 수. '작음'과 '동률'은 겹치지 않는다(2026-09-28 수정:
    이전 식은 arr<v 이면서 isclose인 값을 1.5번 세었다)."""
    arr = np.asarray(arr, float)
    if not len(arr): return np.nan
    eq = np.abs(arr - v) <= TIE_ATOL
    lower = (arr < v) & ~eq
    return float((lower.sum() + 0.5 * eq.sum()) / len(arr))


def n_distinct(parts):
    """분할 목록 중 서로 다른 분할 수(권역 번호를 첫 등장 순으로 다시 매겨 비교)."""
    seen = set()
    for p in parts:
        m = {}; seen.add(tuple(m.setdefault(x, len(m)) for x in p))
    return len(seen)


def grow(nodes, adj, sizes, rng, max_attempt=400):
    """권역별 동 수(sizes)를 정확히 맞춘 공간 연속 무작위 분할. 실패하면 None."""
    n = len(nodes); pos = {v: i for i, v in enumerate(nodes)}
    nb = [[pos[j] for j in adj[v] if j in pos] for v in nodes]
    k = len(sizes)
    for _ in range(max_attempt):
        lab = -np.ones(n, int); cap = np.array(rng.permutation(sizes)); cnt = np.zeros(k, int)
        seeds = rng.choice(n, k, replace=False)
        lab[seeds] = np.arange(k); cnt[:] = 1
        ok = True
        while (lab < 0).any():
            cand = []
            for z in range(k):
                if cnt[z] >= cap[z]: continue
                members = np.where(lab == z)[0]
                fr = {j for i in members for j in nb[i] if lab[j] < 0}
                if fr: cand.append((z, list(fr)))
            if not cand: ok = False; break
            z, fr = cand[rng.integers(len(cand))]
            j = fr[rng.integers(len(fr))]; lab[j] = z; cnt[z] += 1
        if ok and (cnt == cap).all():
            return lab
    return None


def grow_free(nodes, adj, k, rng):
    """크기 제약 없는 공간 연속 무작위 분할(N0, k01과 같은 방식)."""
    n = len(nodes); pos = {v: i for i, v in enumerate(nodes)}
    nb = [[pos[j] for j in adj[v] if j in pos] for v in nodes]
    lab = -np.ones(n, int); seeds = rng.choice(n, k, replace=False); lab[seeds] = np.arange(k)
    frontier = [(int(s), int(z)) for s, z in zip(seeds, range(k))]
    while (lab < 0).any() and frontier:
        p = rng.integers(len(frontier)); node, z = frontier.pop(p)
        free = [j for j in nb[node] if lab[j] < 0]
        if not free: continue
        j = free[rng.integers(len(free))]; lab[j] = z; frontier += [(j, z), (node, z)]
    if (lab < 0).any(): lab[lab < 0] = rng.integers(k, size=(lab < 0).sum())
    return lab


def random_zone(nodes, adj, s, rng):
    """같은 구 안의 공간 연속 무작위 동 집합(크기 s)."""
    pos = {v: i for i, v in enumerate(nodes)}; nb = [[pos[j] for j in adj[v] if j in pos] for v in nodes]
    for _ in range(200):
        start = rng.integers(len(nodes)); S = {start}
        while len(S) < s:
            fr = list({j for i in S for j in nb[i]} - S)
            if not fr: break
            S.add(fr[rng.integers(len(fr))])
        if len(S) == s: return np.array(sorted(S))
    return None


def ifr_gu(W, T, lab):
    same = lab[:, None] == lab[None, :]
    return float((W * same).sum() / T.sum())


def capture(W, T, lab):
    same = lab[:, None] == lab[None, :]
    return (W * same).sum(1) / T


def zone_shares(T, lab, k):
    return np.sort(np.bincount(lab, weights=T, minlength=k) / T.sum())


def main():
    t0 = time.time()
    adj, _ = build_adjacency()
    lzm = pd.read_csv(C.LZ_MAP, encoding="utf-8-sig").set_index("Dong")
    ld = {y: pd.read_csv(C.ld_map(y), encoding="utf-8-sig").set_index("Dong")["global_community_id"] for y in C.YEARS}
    od = {y: pd.read_parquet(C.od_daily(y), columns=["dong_O", "dong_D", "flow"]) for y in C.YEARS}
    rows_gu, rows_zone, rows_dong, rows_mis, meta = [], [], [], [], []
    for K, grp in lzm.groupby("Ku"):
        nodes = sorted(grp.index.tolist()); pos = {d: i for i, d in enumerate(nodes)}; n = len(nodes)
        name = grp["ku_name"].iat[0]
        W, T = {}, {}
        for y in C.YEARS:
            o = od[y][od[y].dong_O.isin(pos)]
            T[y] = o.groupby("dong_O").flow.sum().reindex(nodes).fillna(0).values
            w = o[o.dong_D.isin(pos)]; M = np.zeros((n, n))
            np.add.at(M, (w.dong_O.map(pos).values, w.dong_D.map(pos).values), w.flow.values); W[y] = M
        labs = {"LZ": pd.factorize(grp.loc[nodes, "life_zone_id"])[0]}
        for y in C.YEARS: labs[f"LD{y}"] = pd.factorize(ld[y].loc[nodes])[0]
        # 무작위 비교경계 생성
        nulls = {}
        k = labs["LZ"].max() + 1
        nulls["N0"] = [grow_free(nodes, adj, k, rng) for _ in range(N_NULL)]
        Tavg = (T[C.Y0] / T[C.Y0].sum() + T[C.Y1] / T[C.Y1].sum()) / 2
        for b, lab in labs.items():
            sizes = np.bincount(lab); kk = len(sizes)
            pool, tries = [], 0
            while len(pool) < N2_MAX_TRY // 4 and tries < N2_MAX_TRY:
                p = grow(nodes, adj, sizes, rng); tries += 1
                if p is not None: pool.append(p)
            nulls[f"N1_{b}"] = pool[:N_NULL]
            target = zone_shares(Tavg, lab, kk); acc, tol_used = [], None
            for tol in N2_TOL:
                acc = [p for p in pool if np.abs(zone_shares(Tavg, p, kk) - target).max() <= tol]
                tol_used = tol
                if len(acc) >= 200: break
            nulls[f"N2_{b}"] = acc[:N_NULL]
            meta.append({"ku": K, "ku_name": name, "boundary": b, "n_dong": n, "k": kk, "sizes": "-".join(map(str, sorted(sizes, reverse=True))),
                         "N1_n": len(nulls[f"N1_{b}"]), "N1_pool": len(pool), "N2_n": len(acc[:N_NULL]), "N2_tol": tol_used,
                         "N0_distinct": n_distinct(nulls["N0"]), "N1_distinct": n_distinct(nulls[f"N1_{b}"]), "N2_distinct": n_distinct(nulls[f"N2_{b}"])})
        # (1) 구 단위
        for y in C.YEARS:
            for b in ("LZ", f"LD{y}"):
                v = ifr_gu(W[y], T[y], labs[b]); bkey = "LZ" if b == "LZ" else "LD"
                row = {"ku": K, "ku_name": name, "year": y, "boundary": bkey, "IFR": v}
                for nk, nlist in (("N0", nulls["N0"]), ("N1", nulls[f"N1_{b}"]), ("N2", nulls[f"N2_{b}"])):
                    arr = [ifr_gu(W[y], T[y], p) for p in nlist]
                    row[f"pct_{nk}"] = pct(v, arr); row[f"med_{nk}"] = float(np.median(arr)) if arr else np.nan; row[f"n_{nk}"] = len(arr)
                rows_gu.append(row)
        # (2) 생활권 단위: 같은 구·같은 동 수의 무작위 연속 동 집합
        zpool = defaultdict(list)
        for b in labs:
            for s in set(np.bincount(labs[b])):
                if s not in zpool:
                    zs = [random_zone(nodes, adj, s, rng) for _ in range(N_NULL)]
                    zpool[s] = [z for z in zs if z is not None]
        for y in C.YEARS:
            for b in ("LZ", f"LD{y}"):
                lab = labs[b]; bkey = "LZ" if b == "LZ" else "LD"
                for z in range(lab.max() + 1):
                    idx = np.where(lab == z)[0]; s = len(idx)
                    v = W[y][np.ix_(idx, idx)].sum() / T[y][idx].sum()
                    arr = [W[y][np.ix_(zz, zz)].sum() / T[y][zz].sum() for zz in zpool[s]]
                    zid = grp.loc[nodes[idx[0]], "life_zone_name"] if b == "LZ" else f"LD{y}_{ld[y].loc[nodes[idx[0]]]}"
                    rows_zone.append({"ku": K, "ku_name": name, "year": y, "boundary": bkey, "zone": zid, "n_dong": s, "IFR_z": v, "pct": pct(v, arr), "med_null": float(np.median(arr)), "n_null": len(arr)})
        # (3) 동 단위
        for y in C.YEARS:
            self_share = np.diag(W[y]) / T[y]
            for b in ("LZ", f"LD{y}"):
                lab = labs[b]; bkey = "LZ" if b == "LZ" else "LD"; c = capture(W[y], T[y], lab)
                N1 = np.array([capture(W[y], T[y], p) for p in nulls[f"N1_{b}"]])
                Wn = W[y].copy(); np.fill_diagonal(Wn, 0)
                kk = lab.max() + 1; to_zone = np.stack([Wn[:, lab == z].sum(1) for z in range(kk)], 1)
                for i, d in enumerate(nodes):
                    best = int(to_zone[i].argmax()); own = to_zone[i, lab[i]]
                    rows_dong.append({"ku": K, "ku_name": name, "year": y, "boundary": bkey, "dong": d, "dong_name": grp.loc[d, "ADM_NM"],
                                      "zone": grp.loc[d, "life_zone_name"] if b == "LZ" else f"LD{y}_{ld[y].loc[d]}",
                                      "capture": c[i], "self_share": self_share[i], "pct_N1": pct(c[i], N1[:, i]) if len(N1) else np.nan,
                                      "misassigned": bool(best != lab[i] and to_zone[i, best] > own), "own_zone_share_ex_self": own / T[y][i],
                                      "best_zone_share_ex_self": to_zone[i, best] / T[y][i]})
                    if best != lab[i] and to_zone[i, best] > own:
                        tgt = [nodes[j] for j in np.where(lab == best)[0]]
                        rows_mis.append({"ku_name": name, "year": y, "boundary": bkey, "dong_name": grp.loc[d, "ADM_NM"],
                                         "own_zone": grp.loc[d, "life_zone_name"] if b == "LZ" else f"LD{y}_{ld[y].loc[d]}",
                                         "better_zone_members": "·".join(grp.loc[tgt, "ADM_NM"]),
                                         "own_share": round(own / T[y][i], 4), "better_share": round(to_zone[i, best] / T[y][i], 4)})
        print(f"{name}: n={n}, k={k} 완료 ({time.time()-t0:.0f}s)", flush=True)
    g = pd.DataFrame(rows_gu); z = pd.DataFrame(rows_zone); d = pd.DataFrame(rows_dong); m = pd.DataFrame(rows_mis); mt = pd.DataFrame(meta)
    for df, nm in ((g, "b1_gu"), (z, "b2_zone"), (d, "b3_dong"), (m, "b3_dong_misassigned"), (mt, "b_null_meta")):
        df.to_csv(OUT / f"{nm}.csv", index=False, encoding="utf-8-sig")
    S = {}
    for (y, b), gg in g.groupby(["year", "boundary"]):
        S[f"구_{b}_{y}"] = {f"pct_{nk}_중앙": round(float(gg[f"pct_{nk}"].median()), 3) for nk in ("N0", "N1", "N2")} | {f"pct_{nk}>=0.9_구수": int((gg[f"pct_{nk}"] >= 0.9).sum()) for nk in ("N0", "N1", "N2")} | {f"pct_{nk}<0.5_구수": int((gg[f"pct_{nk}"] < 0.5).sum()) for nk in ("N0", "N1", "N2")}
    for (y, b), zz in z.groupby(["year", "boundary"]):
        S[f"생활권_{b}_{y}"] = {"n": len(zz), "pct_중앙": round(float(zz.pct.median()), 3), "무작위보다_나은_비율(pct>0.5)": round(float((zz.pct > 0.5).mean()), 3), "pct>=0.9_비율": round(float((zz.pct >= 0.9).mean()), 3), "pct<0.1_비율": round(float((zz.pct < 0.1).mean()), 3)}
    for (y, b), dd in d.groupby(["year", "boundary"]):
        S[f"동_{b}_{y}"] = {"n": len(dd), "포착률_중앙": round(float(dd.capture.median()), 3), "동내부비중_중앙": round(float(dd.self_share.median()), 3), "pct_N1_중앙": round(float(dd.pct_N1.median()), 3), "pct_N1<0.25_동수": int((dd.pct_N1 < 0.25).sum()), "이웃권역이_더_담는_동수": int(dd.misassigned.sum())}
    S["N2_허용치_사용"] = mt.groupby("boundary").N2_tol.value_counts().to_dict().__repr__()
    lzm_ = mt[mt.boundary == "LZ"]
    S["무작위_비교경계_표본"] = {"추출": "구마다 N0 1,000번, N1 1,000번(중복 허용), N2는 N1 후보 풀(최대 10,000개)에서 통행량 비중 조건을 만족하는 것 최대 1,000개",
                          "N0_고유분할_최소": int(mt.N0_distinct.min()), "N1_고유분할_최소(공식)": int(lzm_.N1_distinct.min()),
                          "N2_표본_1000미만_구(공식)": {r.ku_name: int(r.N2_n) for r in lzm_.itertuples() if r.N2_n < N_NULL},
                          "N2_허용치_완화(0.05초과)": [f"{r.ku_name} {r.boundary} {r.N2_tol} ({int(r.N2_n)}개)" for r in mt.itertuples() if r.N2_tol > 0.05]}
    S["seconds"] = round(time.time() - t0)
    (OUT / "b_summary.json").write_text(json.dumps(S, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(S, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
