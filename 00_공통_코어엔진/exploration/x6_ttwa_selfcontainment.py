# -*- coding: utf-8 -*-
"""
x6_ttwa_selfcontainment.py — C1 자족성 기준으로 개수가 정해지게 하기 (영국 TTWA 방식 단순화)
==============================================================================================
Leiden 은 "개수(또는 해상도)"를 먼저 정한다. TTWA(Travel-To-Work Areas, Coombes & Bond 2008)는 반대로
"모든 권역이 자족성 기준을 넘을 때까지 합친다"는 규칙을 먼저 정하고, 개수는 결과로 나온다.
여기서는 규칙 = 자족성 문턱 SC* (+ 인구 하한) 이고, 문턱마다 나오는 개수를 공식 개수와 비교한다.

절차 (구마다, 구 안에서만, 공간적으로 붙은 동끼리만)
  1. 동 하나하나를 권역으로 시작.
  2. 권역 자족성 SC = min(공급측, 수요측)
       공급측 = 권역 안 통행 / 권역에서 출발한 서울 전체 통행   (= 정본 IFR 의 권역판)
       수요측 = 권역 안 통행 / 권역에 도착한 서울 전체 통행
  3. SC < SC* 이거나 인구 < 하한 인 권역 중 SC 가 가장 낮은 것을 골라, 붙어 있는 이웃 권역 중
     상호작용 T_ab²/(O_a·D_b) + T_ba²/(O_b·D_a) 가 가장 큰 권역과 합친다 (Coombes 계열 척도).
  4. 모든 권역이 기준을 넘거나 한 덩어리가 될 때까지 반복.
문턱 SC* = 0.15~0.50 (0.025 간격) × 인구 하한 0 / 5만 / 8만 / 10만.
참고: 공식 생활권 116개의 권역 SC 중앙값은 약 0.31 (2020).

출력: output/exploration/x6/ttwa_sweep.csv (구·문턱·하한별 k, IFR, Q, ARI), ttwa_labels.csv, x6_report.md
      "합계가 116 에 가장 가까운 문턱" 에서의 구별 개수도 보고한다.
실행: python x6_ttwa_selfcontainment.py
"""
from xcommon import *

THRESH = np.round(np.arange(0.15, 0.5001, 0.025), 3)
FLOORS = (0, 50_000, 80_000, 100_000)


def ttwa(g, sc_star, floor):
    n = g.n
    zones = {i: [i] for i in range(n)}
    zadj = {i: set(g.adj[i]) for i in range(n)}
    W, O, D, P = g.W, g.total_out, g.total_in_from_seoul, g.pop

    def stats(m):
        m = np.asarray(m)
        T = W[np.ix_(m, m)].sum(); o = O[m].sum(); d = D[m].sum()
        return min(T / o if o else 0, T / d if d else 0), P[m].sum()

    cache = {z: stats(m) for z, m in zones.items()}
    while len(zones) > 1:
        bad = [(cache[z][0], z) for z in zones if cache[z][0] < sc_star or cache[z][1] < floor]
        if not bad:
            break
        _, a = min(bad)
        if not zadj[a]:                                   # 이웃 없음(섬) → 더 합칠 수 없음
            cache[a] = (1.0, 1e18); continue
        ma = np.asarray(zones[a])
        best, bb = -1, None
        for b in zadj[a]:
            mb = np.asarray(zones[b])
            Tab = W[np.ix_(ma, mb)].sum(); Tba = W[np.ix_(mb, ma)].sum()
            s = (Tab ** 2 / max(O[ma].sum() * D[mb].sum(), 1e-9) + Tba ** 2 / max(O[mb].sum() * D[ma].sum(), 1e-9))
            if s > best:
                best, bb = s, b
        zones[bb] += zones.pop(a)
        zadj[bb] = (zadj[bb] | zadj.pop(a)) - {a, bb}
        for z in zadj[bb]:
            zadj[z].discard(a); zadj[z].add(bb)
        cache.pop(a); cache[bb] = stats(zones[bb])
    lab = np.empty(n, dtype=int)
    for c, (z, m) in enumerate(zones.items()):
        lab[m] = c
    return lab


def main():
    lz = load_lz()
    rows, labs = [], []
    for year in YEARS:
        G = all_ku_graphs(year, with_pop=True)
        m, _ = load_leiden(year)
        for ku in KU_ORDER:
            g = G[ku]
            off = g.labels_from_mapping(lz["life_zone_id"]); lei = g.labels_from_mapping(m["global_community_id"])
            for fl in FLOORS:
                for t in THRESH:
                    lab = ttwa(g, t, fl)
                    rows.append({"year": year, "구": C.KU_NAME[ku], "공식k": C.TARGET_COMMUNITIES[ku], "SC문턱": t, "인구하한": fl,
                                 "k": int(lab.max()) + 1, "IFR": g.ifr(lab), "Q": g.q(lab),
                                 "ARI_vs_공식": ari(lab, off), "ARI_vs_Leiden": ari(lab, lei)})
                    labs += [{"year": year, "Dong": d, "SC문턱": t, "인구하한": fl, "label": int(l)} for d, l in zip(g.nodes, lab)]
        print(year, "done", flush=True)
    d = pd.DataFrame(rows)
    save(d, "ttwa_sweep", "x6"); save(pd.DataFrame(labs), "ttwa_labels", "x6")

    tot = d.groupby(["year", "인구하한", "SC문턱"]).agg(k합계=("k", "sum"), 공식과같은구=("k", lambda s: 0),
                                                   IFR평균=("IFR", "mean"), ARI공식=("ARI_vs_공식", "mean"),
                                                   ARI_Leiden=("ARI_vs_Leiden", "mean")).reset_index()
    tot["공식과같은구"] = [int((d[(d.year == r.year) & (d.인구하한 == r.인구하한) & (d.SC문턱 == r.SC문턱)].eval("k == 공식k")).sum())
                     for r in tot.itertuples()]
    save(tot, "ttwa_totals", "x6")
    L = ["# x6 — C1 자족성 기준(TTWA 방식)으로 개수가 결과로 나오게", "",
         "구 안에서 동을 권역으로 시작해, 자족성 SC=min(공급측, 수요측)이 문턱 미만(또는 인구 하한 미만)인 권역을 "
         "가장 강하게 연결된 이웃과 합침. 개수는 결과.", ""]
    best = []
    for y in YEARS:
        L += [f"## {y}", ""]
        for fl in FLOORS:
            x = tot[(tot.year == y) & (tot.인구하한 == fl)]
            b = x.iloc[(x["k합계"] - C.N_LZ).abs().argmin()]
            best.append((y, fl, b["SC문턱"]))
            L.append(f"- 인구 하한 {fl:,}: 합계 116 에 가장 가까운 문턱 SC*={b['SC문턱']:.3f} → 합계 {b['k합계']}, "
                     f"공식과 같은 구 {b['공식과같은구']}/25, ARI(공식) {b['ARI공식']:.3f}, ARI(Leiden) {b['ARI_Leiden']:.3f}")
        L += ["", "문턱별 합계 (행 = 인구 하한, 열 = SC 문턱)", "",
              md_table(tot[tot.year == y].pivot(index="인구하한", columns="SC문턱", values="k합계").reset_index(), "{:.0f}"), ""]
    for y, fl, t in best:
        if fl != 0:
            continue
        x = d[(d.year == y) & (d.인구하한 == fl) & (d.SC문턱 == t)]
        L += [f"### {y} 구별 개수 (하한 0, SC*={t:.3f})", "", md_table(x[["구", "공식k", "k", "IFR", "Q", "ARI_vs_공식", "ARI_vs_Leiden"]]), ""]
    (out_dir("x6") / "x6_report.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join([l for l in L if l.startswith("- ") or l.startswith("## ")]))


if __name__ == "__main__":
    main()
