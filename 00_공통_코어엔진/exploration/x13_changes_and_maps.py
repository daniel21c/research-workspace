# -*- coding: utf-8 -*-
"""
x13_changes_and_maps.py — 공식 생활권 대비 "무엇이 바뀌나" + 확실한 제안 + 지도 (1~3분)
=======================================================================================
입력: output/proposal/partitions.csv, scorecard_ku.csv (x12), output/leiden/{year}_qmax (P1)
출력: output/proposal/changes_{year}.md      구별 × 시나리오: 공식 권역이 유지/분할/병합/재배치되는지, 묶음이 바뀐 동
      output/proposal/robust_changes.md     설계 §6 규칙으로 판정한 구별 제안(두 해 모두 같은 판정 = 확실)
      output/proposal/maps/{ku}_{name}.png  구별 소지도 (행: 연도, 열: 공식 | 정본 | P1 | P2 | P3), 굵은 선 = 공식 경계
      output/proposal/maps/seoul.png        서울 전체

판정 규칙 (설계 §6, 결과를 보고 바꾸지 않음)
  더 나눠야  : k_P1 > k_P0 이고 k_P2 > k_P0 이고 z_P1 > z_P0 이고 z_P2 > z_P0
  합쳐도 됨  : k_P1 < k_P0 이고 k_P2 < k_P0 이고 min(z_P1, z_P2) ≥ z_P0
  개수 유지  : 그 외 → 개선점은 개수가 아니라 경계 모양 (정본 vs 공식 ARI 로 크기 표시)
  인구 주의  : 제안 시나리오(P1·P2)에서 권역 인구 CV > 0.4 또는 동 1개 권역이 생기면 표시
"""
import pandas as pd
from xcommon import *

PROP = C.OUTPUT_DIR / "proposal"
MAPS = PROP / "maps"
SHOW = ["P0", "P0c", "P5", "P1", "P2", "P3"]
NAME = {"P0": "공식", "P0c": "정본(116)", "P1": "P1 Q최대k", "P2": "P2 TTWA 0.25", "P3": "P3 인구7만", "P2a": "TTWA 0.20", "P2b": "TTWA 0.30",
        "P5": "P5 Q+인구2만", "P5_30k": "P5 인구3만", "P5_50k": "P5 인구5만"}


def classify(l0, l1):
    """공식 라벨 l0 → 시나리오 라벨 l1. 공식 권역별 유지/분할/병합/재배치"""
    res = {}
    T = {o: set(l1[l0 == o]) for o in np.unique(l0)}
    U = {s: set(l0[l1 == s]) for s in np.unique(l1)}
    for o, ts in T.items():
        if len(ts) == 1 and U[next(iter(ts))] == {o}:
            res[o] = "유지"
        elif all(U[s] == {o} for s in ts):
            res[o] = f"분할({len(ts)})"
        elif len(ts) == 1:
            res[o] = "병합"
        else:
            res[o] = "재배치"
    return res


def moved(l0, l1):
    sa, sb = l0[:, None] == l0[None, :], l1[:, None] == l1[None, :]
    return np.where((sa != sb).any(axis=1))[0]


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for f in ("Malgun Gothic", "NanumGothic", "AppleGothic"):
        if any(x.name == f for x in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = f; break
    plt.rcParams["axes.unicode_minus"] = False

    parts = pd.read_csv(PROP / "partitions.csv", encoding="utf-8-sig"); parts["year"] = parts["year"].astype(str)
    for year in YEARS:
        f = C.LEIDEN_OUT / f"{year}_qmax" / "metrics" / f"leiden_mapping_{year}.csv"
        if f.exists():
            m = pd.read_csv(f)
            parts = pd.concat([parts, pd.DataFrame({"year": year, "Dong": m["Dong"].astype(int), "Ku": m["Ku"].astype(int), "scenario": "P1", "label": m["community"].astype(int)})])
    K = pd.read_csv(PROP / "scorecard_ku.csv", encoding="utf-8-sig"); K["year"] = K["year"].astype(str)
    dong = load_dong(); lz = load_lz()
    lzname = lz.groupby("life_zone_id")["life_zone_name"].first()
    MAPS.mkdir(parents=True, exist_ok=True)

    # ── 1. 변화 분류 ─────────────────────────────────────────────────────────
    for year in YEARS:
        P = parts[parts.year == year]
        scen = [s for s in SHOW + ["P2a", "P2b", "P5_30k", "P5_50k"] if s in set(P.scenario) and s != "P0"]
        lab = {s: P[P.scenario == s].set_index("Dong")["label"] for s in ["P0"] + scen}
        L = [f"# {year} 공식 생활권 대비 변화", "", "공식 권역별: 유지 / 분할(n) / 병합 / 재배치. '바뀐 동' = 공식 대비 같은 권역 관계가 하나라도 달라진 동.", ""]
        for ku in KU_ORDER:
            g = dong[dong.Ku == ku].sort_values("Dong")
            nodes, names = g["Dong"].tolist(), g["ADM_NM"].tolist()
            l0raw = lab["P0"].reindex(nodes).values
            l0 = pd.factorize(l0raw)[0]
            zone_name = {c: lzname.get(v, str(v)).split("_")[-1] for c, v in zip(l0, l0raw)}
            L += [f"## {C.KU_NAME[ku]} (공식 {l0.max() + 1}개: {', '.join(zone_name[c] for c in sorted(zone_name))})", "",
                  "| 시나리오 | k | 공식 권역별 | 바뀐 동 |", "|---|---|---|---|"]
            for s in scen:
                l1 = pd.factorize(lab[s].reindex(nodes).values)[0]
                cl = classify(l0, l1)
                desc = ", ".join(f"{zone_name[o]}:{v}" for o, v in cl.items() if v != "유지") or "전부 유지"
                mv = [names[i] for i in moved(l0, l1)]
                L.append(f"| {NAME.get(s, s)} | {l1.max() + 1} | {desc} | {len(mv)}: {', '.join(mv)} |")
            L.append("")
        (PROP / f"changes_{year}.md").write_text("\n".join(L), encoding="utf-8")

    # ── 2. 확실한 제안 (설계 §6) ─────────────────────────────────────────────
    R = []
    for year in YEARS:
        x = K[K.year == year]
        have = set(x.scenario)
        if not {"P0", "P1", "P2"} <= have:
            print(f"[경고] {year}: P1 또는 P2 없음 → 판정 생략"); continue
        for ku in KU_ORDER:
            r = {s: x[(x.scenario == s) & (x.ku == ku)].iloc[0] for s in ("P0", "P0c", "P1", "P2", "P3") if s in have}
            k0, z0 = int(r["P0"].k), r["P0"].z_pop
            k1, z1, k2, z2 = int(r["P1"].k), r["P1"].z_pop, int(r["P2"].k), r["P2"].z_pop
            if k1 > k0 and k2 > k0 and z1 > z0 and z2 > z0:
                j = "더 나눠야"
            elif k1 < k0 and k2 < k0 and np.nanmin([z1, z2]) >= z0:
                j = "합쳐도 됨"
            else:
                j = "개수 유지"
            warn = []
            for s in ("P1", "P2"):
                if r[s].pop_cv > 0.4: warn.append(f"{s} 인구CV {r[s].pop_cv:.2f}")
                if r[s].n_single > 0: warn.append(f"{s} 동1개권역 {int(r[s].n_single)}")
            R.append({"year": year, "구": C.KU_NAME[ku], "k_공식": k0, "k_P1": k1, "k_P2": k2, "k_P3": int(r["P3"].k) if "P3" in r else np.nan,
                      "z_공식": z0, "z_정본": r["P0c"].z_pop if "P0c" in r else np.nan, "z_P1": z1, "z_P2": z2,
                      "정본vs공식_ARI": r["P0c"].ARI_P0 if "P0c" in r else np.nan, "판정": j, "인구주의": "; ".join(warn)})
    if R:
        D = pd.DataFrame(R)
        D.to_csv(PROP / "robust_changes.csv", index=False, encoding="utf-8-sig")
        both = D.groupby("구")["판정"].agg(lambda v: v.iloc[0] if len(set(v)) == 1 and len(v) == 2 else "")
        L = ["# 확실한 제안 후보 (설계 §6 규칙)", "",
             "판정은 P1(Q 최대 개수)·P2(TTWA 0.25) 두 시나리오가 개수 방향과 초과 자족성(z_pop)에서 모두 공식보다 나을 때만 '더 나눠야/합쳐도 됨'. "
             "P3(인구 규칙)은 방향 판정에 쓰지 않고 개수만 참고로 적는다.", ""]
        for j in ("더 나눠야", "합쳐도 됨", "개수 유지"):
            gs = [g for g, v in both.items() if v == j]
            L.append(f"- **두 해 모두 '{j}'**: {', '.join(gs) if gs else '없음'} ({len(gs)}개 구)")
        mixed = [f"{g}({'/'.join(D[D.구 == g].sort_values('year').판정)})" for g, v in both.items() if v == ""]
        L += [f"- 두 해 판정이 다른 구: {', '.join(mixed) if mixed else '없음'}", ""]
        keep = D[D.판정 == "개수 유지"]
        L += ["개수 유지 구의 개선점은 경계 모양이다. 정본(같은 개수 Leiden) vs 공식 ARI 가 낮을수록 모양 차이가 크다:", ""]
        for year in YEARS:
            kk = keep[keep.year == year].sort_values("정본vs공식_ARI")
            L.append(f"- {year}: " + ", ".join(f"{r.구} {r.정본vs공식_ARI:.2f}" for r in kk.itertuples()))
        L += [""]
        for year in YEARS:
            L += [f"## {year}", "", md_table(D[D.year == year].drop(columns="year")), ""]
        (PROP / "robust_changes.md").write_text("\n".join(L), encoding="utf-8")
        print("\n".join(L[:12]))

    # ── 2b. 이중 목표 제안 경계 판정 (설계 §5, 사전 고정) ──────────────────────
    #   P5 채택: z_P5 > z_공식  (P5 는 인구 하한을 지키므로 계획단위 조건 충족)
    #   현행 유지: z_P5 ≤ z_공식
    #   두 해 모두 같은 판정만 '확실'. 제안 경계 = 채택 구는 P5, 나머지는 공식.
    if "P5" in set(K.scenario):
        import geopandas as gpd
        Q = []
        for year in YEARS:
            x = K[K.year == year]
            for ku in KU_ORDER:
                r0 = x[(x.scenario == "P0") & (x.ku == ku)].iloc[0]; r5 = x[(x.scenario == "P5") & (x.ku == ku)].iloc[0]
                rc = x[(x.scenario == "P0c") & (x.ku == ku)].iloc[0]
                Q.append({"year": year, "ku": ku, "구": C.KU_NAME[ku], "k": int(r0.k), "z_공식": r0.z_pop, "z_정본": rc.z_pop, "z_P5": r5.z_pop,
                          "popCV_공식": r0.pop_cv, "popCV_P5": r5.pop_cv, "최소인구_공식": r0.pop_min, "최소인구_P5": r5.pop_min,
                          "ARI_P5_공식": r5.ARI_P0, "바뀐동_공식대비": int(r5.moved_P0),
                          "판정": "P5 채택" if r5.z_pop > r0.z_pop else "현행 유지"})
        Q = pd.DataFrame(Q)
        Q.to_csv(PROP / "p5_adoption.csv", index=False, encoding="utf-8-sig")
        both = Q.groupby("구")["판정"].agg(lambda v: v.iloc[0] if len(set(v)) == 1 else "")
        L = ["# 이중 목표 제안 경계 — 구별 채택 판정", "",
             "P5 = 공식 개수, Q 최대, 권역 인구 ≥ 2만. 판정: z_pop(같은 개수 무작위 인구 균형 경계 대비 초과 자족성)이 공식보다 높으면 'P5 채택'.", ""]
        for j in ("P5 채택", "현행 유지"):
            gs = [g for g, v in both.items() if v == j]
            L.append(f"- **두 해 모두 '{j}'**: {', '.join(gs) if gs else '없음'} ({len(gs)}개 구)")
        mixed = [g for g, v in both.items() if v == ""]
        L += [f"- 두 해 판정이 다른 구: {', '.join(mixed) if mixed else '없음'}", ""]
        for year in YEARS:
            x = Q[Q.year == year]
            L += [f"## {year}", "", md_table(x.drop(columns=["year", "ku"])), ""]
        (PROP / "p5_adoption.md").write_text("\n".join(L), encoding="utf-8")
        print("\n".join(L[:8]))
        # 제안 경계 gpkg: 두 해 모두 채택인 구는 P5, 그 외는 공식 (연도별 P5 라벨 사용)
        sure = {C.KU_NAME[k]: (both.get(C.KU_NAME[k]) == "P5 채택") for k in KU_ORDER}
        for year in YEARS:
            P = parts[parts.year == year]
            l0 = P[P.scenario == "P0"].set_index("Dong")["label"].reindex(dong["Dong"]).values
            l5 = P[P.scenario == "P5"].set_index("Dong")["label"].reindex(dong["Dong"]).values
            use5 = np.array([sure[C.KU_NAME[k]] for k in dong["Ku"]])
            lab = np.where(use5, l5, l0)
            g = dong.assign(scheme=np.where(use5, "P5", "공식"), zone=[f"{k}_{s}_{int(v)}" for k, s, v in zip(dong["Ku"], np.where(use5, "P5", "LZ"), lab)])
            zones = g.dissolve(by="zone", aggfunc={"Ku": "first", "scheme": "first"}, as_index=False)
            pop = load_pop(year).reindex(g["Dong"]).values
            zones["pop"] = g.assign(p=pop).groupby("zone")["p"].sum().reindex(zones["zone"]).values
            zones["n_dongs"] = g.groupby("zone").size().reindex(zones["zone"]).values
            C.save_gpkg_layers(PROP / f"proposal_boundary_{year}.gpkg", {"zones_epsg5179": zones, "dongs_epsg5179": g})
        print(f"→ {PROP / 'p5_adoption.md'}, proposal_boundary_{{연도}}.gpkg")

    # ── 3. 지도 ─────────────────────────────────────────────────────────────
    cmap = plt.get_cmap("tab20")
    def draw(ax, gdf, labels, title, official_bd=None, edge=0.3):
        gdf = gdf.assign(lab=pd.factorize(labels)[0])
        gdf.plot(ax=ax, color=[cmap(i % 20) for i in gdf["lab"]], edgecolor="white", linewidth=edge)
        if official_bd is not None:
            official_bd.boundary.plot(ax=ax, color="black", linewidth=1.3)
        ax.set_title(title, fontsize=9); ax.set_axis_off()
    for ku in KU_ORDER:
        g = dong[dong.Ku == ku].sort_values("Dong").reset_index(drop=True)
        scen_cols = [s for s in SHOW if s in set(parts.scenario)]
        fig, axes = plt.subplots(len(YEARS), len(scen_cols), figsize=(2.6 * len(scen_cols), 2.8 * len(YEARS)))
        axes = np.atleast_2d(axes)
        for i, year in enumerate(YEARS):
            P = parts[parts.year == year]
            l0 = P[P.scenario == "P0"].set_index("Dong")["label"].reindex(g["Dong"]).values
            bd = g.assign(z=l0).dissolve(by="z")
            for j, s in enumerate(scen_cols):
                ls = P[P.scenario == s].set_index("Dong")["label"].reindex(g["Dong"]).values
                if pd.isna(ls).any():
                    axes[i, j].set_axis_off(); axes[i, j].set_title(f"{NAME[s]} (없음)", fontsize=9); continue
                k = len(np.unique(ls))
                kk = K[(K.year == year) & (K.ku == ku) & (K.scenario == s)]
                sub = f"  z={kk.z_pop.iloc[0]:+.1f}" if len(kk) and kk.z_pop.notna().iloc[0] else ""
                draw(axes[i, j], g, ls, f"{year} {NAME[s]} k={k}{sub}", None if s == "P0" else bd)
        fig.suptitle(f"{C.KU_NAME[ku]} — 굵은 선: 공식 생활권 경계", fontsize=11)
        fig.tight_layout()
        fig.savefig(MAPS / f"{ku}_{C.KU_NAME_EN[ku]}.png", dpi=130); plt.close(fig)
    # 서울 전체
    scen_cols = [s for s in ("P0", "P0c", "P1", "P2", "P4") if s in set(parts.scenario)]
    fig, axes = plt.subplots(len(YEARS), len(scen_cols), figsize=(4.2 * len(scen_cols), 4.2 * len(YEARS)))
    axes = np.atleast_2d(axes)
    kubd = dong.dissolve(by="Ku")
    for i, year in enumerate(YEARS):
        P = parts[parts.year == year]
        for j, s in enumerate(scen_cols):
            ls = P[P.scenario == s].set_index("Dong")["label"].reindex(dong["Dong"]).values
            if pd.isna(ls).any():
                axes[i, j].set_axis_off(); continue
            key = ls if s == "P4" else (dong["Ku"].astype(str).values + "_" + pd.Series(ls).astype(int).astype(str).values)
            draw(axes[i, j], dong, key, f"{year} {NAME.get(s, '서울 전체 Leiden')} k={len(np.unique(key))}", kubd, edge=0.15)
    fig.suptitle("서울 — 굵은 선: 자치구 경계", fontsize=12); fig.tight_layout()
    fig.savefig(MAPS / "seoul.png", dpi=130); plt.close(fig)
    print(f"→ {PROP}: changes_*.md, robust_changes.md, maps/ ({len(list(MAPS.glob('*.png')))}장)")


if __name__ == "__main__":
    main()
