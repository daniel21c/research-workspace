# -*- coding: utf-8 -*-
"""
x12_scorecard.py — 시나리오별 점수표 (설계 §3의 잣대) — 5~10분
================================================================
입력: output/proposal/partitions.csv (x11), output/leiden/{year}_qmax (P1, s03 --targets), x2 random_curve, x4 null_q_curves
출력: output/proposal/scorecard_ku.csv (시나리오 × 연도 × 구), scorecard_seoul.csv, scorecard.md

잣대
  k, IFR, Q                          — 원값
  z_pop, SCI_pop                     — 같은 k 의 인구 균형 무작위 분할 500개 대비 초과 자족성 (x2 기준선; 없는 k 는 같은 방식으로 생성)
  z_Q                                — 귀무 그래프(통행 총량 보존) 대비 Q 의 z (x4 기준선; k 2~? 범위 밖은 빈칸)
  pop_cv, pop_min, pop_max, n_single — 권역 인구 균형, 동 1개짜리 권역 수
  n_noncontig                        — 공간적으로 끊긴 권역 수
  ARI_P0, ARI_P0c, moved_P0          — 공식·정본과의 거리, 공식 대비 묶음 관계가 바뀐 동 수
서울: k 합, 서울 IFR(분자합/분모합), z 평균, Q 평균, 권역 인구 CV(서울 전체 권역), 서울 ARI(공식·정본), 2020→2025 변화
"""
import argparse
import pandas as pd
from xcommon import *
from x2_size_corrected_ifr import cv_pop

PROP = C.OUTPUT_DIR / "proposal"
SCEN_ORDER = ["P0", "P0c", "P1", "P2", "P2a", "P2b", "P3", "P5", "P5_30k", "P5_50k", "P4"]


def moved_dongs(a, b):
    sa, sb = a[:, None] == a[None, :], b[:, None] == b[None, :]
    return np.where((sa != sb).any(axis=1))[0]


def n_noncontig(labels, adj):
    bad = 0
    for c in np.unique(labels):
        idx = [i for i in range(len(labels)) if labels[i] == c]
        seen, stack = {idx[0]}, [idx[0]]
        while stack:
            i = stack.pop()
            for j in adj[i]:
                if labels[j] == c and j not in seen:
                    seen.add(j); stack.append(j)
        bad += len(seen) < len(idx)
    return bad


def load_partitions():
    d = pd.read_csv(PROP / "partitions.csv", encoding="utf-8-sig")
    d["year"] = d["year"].astype(str)
    for year in YEARS:
        f = C.LEIDEN_OUT / f"{year}_qmax" / "metrics" / f"leiden_mapping_{year}.csv"
        if f.exists():
            m = pd.read_csv(f)
            d = pd.concat([d, pd.DataFrame({"year": year, "Dong": m["Dong"].astype(int), "Ku": m["Ku"].astype(int),
                                            "scenario": "P1", "label": m["community"].astype(int)})], ignore_index=True)
        else:
            print(f"[경고] P1 결과 없음: {f} — s03 --targets 를 먼저 돌리세요. P1 없이 계속.")
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500, help="기준선이 없는 k 의 무작위 분할 수")
    ap.add_argument("--seed", type=int, default=20260924)
    a = ap.parse_args()
    parts = load_partitions()
    scen_all = [s for s in SCEN_ORDER if s in set(parts.scenario)]
    curve = pd.read_csv(OUT / "x2" / "random_curve.csv", encoding="utf-8-sig")
    curve = curve[curve["null"] == "pop"]
    base = {(str(r.year), r.구, int(r.k)): (r.rand_mean, r.rand_sd) for r in curve.itertuples()}
    qn = pd.read_csv(OUT / "x4" / "null_q_curves.csv", encoding="utf-8-sig")
    qbase = {(str(r.year), int(r.ku), int(r.k)): (r.Q_null_mean, r.Q_null_sd) for r in qn.itertuples()}
    extra = []
    rows, seoul = [], []
    dong = load_dong()
    for year in YEARS:
        G = all_ku_graphs(year, with_pop=True)
        od = load_od(year)
        P = parts[parts.year == year]
        scen_y = [s for s in scen_all if s in set(P.scenario)]
        lab = {s: P[P.scenario == s].set_index("Dong")["label"] for s in scen_y}
        # 서울 IFR (od 기반, 모든 시나리오 공통 정의) 와 서울 전체 라벨(ARI 용)
        # 2026-09-25 수정: 시나리오 라벨은 구마다 0부터 다시 매기므로 원 라벨로 비교하면 다른 구의 같은 번호 권역 사이 통행이
        # 내부통행으로 잡혀 서울 IFR 이 부풀었다(P1·P2·P3·P5). 구 접두 라벨(glab)로 비교한다. 이전 값은 결정기록 §16.
        def seoul_ifr(s):
            series = pd.Series(glab[s], index=dong["Dong"].astype(int).values)
            lo = series.reindex(od["dong_O"].astype(int)).values; ld = series.reindex(od["dong_D"].astype(int)).values
            return float(od["flow"].values[lo == ld].sum() / od["flow"].sum())
        def global_labels(s):
            ser = lab[s].reindex(dong["Dong"])
            if s == "P4":
                return ser.values
            return pd.factorize(dong["Ku"].astype(str).values + "_" + ser.astype(int).astype(str).values)[0]
        glab = {s: np.asarray(global_labels(s)) for s in scen_y}
        for s in scen_y:
            if s == "P4":
                continue
            for ku in KU_ORDER:
                g = G[ku]
                l0 = g.labels_from_mapping(lab["P0"]); lc = g.labels_from_mapping(lab["P0c"]); l = g.labels_from_mapping(lab[s])
                k = int(l.max()) + 1
                v, q = g.ifr(l), g.q(l)
                pops = np.bincount(l, weights=g.pop)
                key = (year, C.KU_NAME[ku], k)
                if key not in base and 2 <= k <= g.n - 1:
                    rng = np.random.default_rng(a.seed + ku + int(year) + 1000 * k)
                    vals = [g.ifr(x) for x in (random_balanced_partition(g.adj, k, rng, g.pop) for _ in range(a.n)) if x is not None]
                    base[key] = (float(np.mean(vals)), float(np.std(vals)))
                    extra.append({"year": year, "구": C.KU_NAME[ku], "k": k, "null": "pop", "rand_mean": base[key][0], "rand_sd": base[key][1], "n": len(vals)})
                mu, sd = base.get(key, (np.nan, np.nan))
                qm, qs = qbase.get((year, ku, k), (np.nan, np.nan))
                rows.append({"year": year, "scenario": s, "ku": ku, "구": C.KU_NAME[ku], "k_공식": int(l0.max()) + 1, "k": k, "k−공식": k - int(l0.max()) - 1,
                             "IFR": v, "Q": q, "z_pop": (v - mu) / sd if sd and sd > 0 else np.nan, "SCI_pop": (v - mu) / (1 - mu) if mu == mu else np.nan,
                             "z_Q": (q - qm) / qs if qs and qs > 0 else np.nan,
                             "pop_cv": cv_pop(l, g.pop), "pop_min": pops.min(), "pop_max": pops.max(),
                             "n_single": int((np.bincount(l) == 1).sum()), "n_noncontig": n_noncontig(l, g.adj),
                             "ARI_P0": ari(l0, l), "ARI_P0c": ari(lc, l), "moved_P0": len(moved_dongs(l0, l))})
        R = pd.DataFrame([r for r in rows if r["year"] == year])
        pop_all = load_pop(year).reindex(dong["Dong"]).values
        for s in scen_y:
            x = R[R.scenario == s]
            zone_pop = np.bincount(pd.factorize(glab[s])[0], weights=pop_all)
            rec = {"year": year, "scenario": s, "k합": int(len(np.unique(glab[s]))), "서울IFR": seoul_ifr(s),
                   "권역인구CV": float(zone_pop.std() / zone_pop.mean()), "권역인구_최소": zone_pop.min(), "권역인구_중앙": float(np.median(zone_pop)),
                   "인구3만미만_권역": int((zone_pop < 30000).sum()), "인구15만이상_권역": int((zone_pop >= 150000).sum()),
                   "ARI_P0": ari(glab["P0"], glab[s]), "ARI_P0c": ari(glab["P0c"], glab[s])}
            if len(x):
                rec.update({"z_pop평균": x.z_pop.mean(), "z_pop>1.64_구": int((x.z_pop > 1.64).sum()), "Q평균": x.Q.mean(), "z_Q평균": x.z_Q.mean(),
                            "구별popCV평균": x.pop_cv.mean(), "동1개권역": int(x.n_single.sum()), "끊긴권역": int(x.n_noncontig.sum()),
                            "공식대비_바뀐동": int(x.moved_P0.sum()), "공식과_같은구": int((x.ARI_P0 == 1).sum())})
            seoul.append(rec)
    K = pd.DataFrame(rows); S = pd.DataFrame(seoul)
    PROP.mkdir(parents=True, exist_ok=True)
    K.to_csv(PROP / "scorecard_ku.csv", index=False, encoding="utf-8-sig")
    S.to_csv(PROP / "scorecard_seoul.csv", index=False, encoding="utf-8-sig")
    if extra:
        pd.DataFrame(extra).to_csv(PROP / "random_curve_extra.csv", index=False, encoding="utf-8-sig")
    # 연도 변화
    ch = []
    for s in scen_all:
        a0, a1 = S[(S.scenario == s) & (S.year == "2020")], S[(S.scenario == s) & (S.year == "2025")]
        if len(a0) and len(a1):
            g0 = parts[(parts.year == "2020") & (parts.scenario == s)].set_index("Dong")["label"].reindex(dong["Dong"])
            g1 = parts[(parts.year == "2025") & (parts.scenario == s)].set_index("Dong")["label"].reindex(dong["Dong"])
            if s == "P1":
                g0 = g0.fillna(-1); g1 = g1.fillna(-1)
            kus = dong["Ku"].astype(str).values
            key0 = pd.factorize(kus + "_" + g0.astype(int).astype(str).values)[0] if s != "P4" else g0.values
            key1 = pd.factorize(kus + "_" + g1.astype(int).astype(str).values)[0] if s != "P4" else g1.values
            ch.append({"scenario": s, "k합 2020→2025": f"{int(a0.k합.iloc[0])}→{int(a1.k합.iloc[0])}",
                       "서울IFR 2020": a0.서울IFR.iloc[0], "서울IFR 2025": a1.서울IFR.iloc[0], "ΔIFR": a1.서울IFR.iloc[0] - a0.서울IFR.iloc[0],
                       "z_pop평균 2020": a0.get("z_pop평균", pd.Series([np.nan])).iloc[0], "z_pop평균 2025": a1.get("z_pop평균", pd.Series([np.nan])).iloc[0],
                       "두해_경계ARI": ari(np.asarray(key0), np.asarray(key1))})
    CH = pd.DataFrame(ch)
    CH.to_csv(PROP / "scorecard_change.csv", index=False, encoding="utf-8-sig")
    desc = pd.read_csv(PROP / "scenarios.csv", encoding="utf-8-sig").set_index("scenario")["설명"].to_dict(); desc["P1"] = "Q 최대 개수 Leiden"
    L = ["# 최적화 검증 점수표", "", "설계: exploration/최적화검증_설계.md. z_pop = 같은 개수의 인구 균형 무작위 분할 대비 초과 자족성(주 지표). "
         "IFR 원값은 개수가 다르면 비교하지 않는다.", "", "| 코드 | 시나리오 |", "|---|---|"] + [f"| {s} | {desc.get(s, '')} |" for s in scen_all] + [""]
    for year in YEARS:
        x = S[S.year == year].drop(columns="year")
        L += [f"## {year} 서울", "", md_table(x), ""]
    L += ["## 2020 → 2025", "", md_table(CH), ""]
    for year in YEARS:
        x = K[K.year == year]
        piv = x.pivot(index="구", columns="scenario", values="k")[[s for s in scen_all if s in x.scenario.unique()]]
        piv.insert(0, "공식k", x[x.scenario == "P0"].set_index("구")["k"])
        L += [f"## {year} 구별 개수", "", md_table(piv.reset_index()), ""]
        pz = x.pivot(index="구", columns="scenario", values="z_pop")[[s for s in scen_all if s in x.scenario.unique()]]
        L += [f"## {year} 구별 초과 자족성 z_pop", "", md_table(pz.reset_index()), ""]
        pc = x.pivot(index="구", columns="scenario", values="pop_cv")[[s for s in scen_all if s in x.scenario.unique()]]
        L += [f"## {year} 구별 권역 인구 CV", "", md_table(pc.reset_index()), ""]
    (PROP / "scorecard.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[:60])); print(f"→ {PROP / 'scorecard.md'}")


if __name__ == "__main__":
    main()
