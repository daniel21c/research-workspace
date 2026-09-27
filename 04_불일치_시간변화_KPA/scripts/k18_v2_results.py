# -*- coding: utf-8 -*-
"""
k18 — KPA v2(경계 동 진단·재배정) 원고용 표·그림 사양과 재배정 결과 검증

1) 검증: k14 탐욕 재배정의 최종 분할을 이동 기록으로 다시 만들어
   (a) 권역 수 유지 (b) 모든 권역 공간 연속 (c) IFR·Q·D가 b4_gu_summary와 같은지 확인 → benchmark/b8_verify.json
2) 그림: Fv2_1 분석 틀, Fv2_2 크기 편향(구별 백분위 N0 vs N1), Fv2_3 동 진단 지도(2025),
         Fv2_4 구별 재배정 전후 IFR(2025), Fv2_5 사례 구(광진구) 공식/재배정/가상경계 지도
3) 표 사양 build_tables_v2(), 그림 사양 FIGS_V2 — k19(docx)·k09(hwp)가 가져다 쓴다.
"""
from __future__ import annotations
import json, sys
from collections import deque
import numpy as np
import pandas as pd
import config as C

B = C.TAB / "benchmark"; FIG = C.OUT / "figures"
CASE_KU = "광진구"


def _lz():
    return pd.read_csv(C.LZ_MAP, encoding="utf-8-sig").set_index("Dong")


def final_partitions():
    """이동 기록으로 연도별 재배정 후 권역(생활권 이름)을 동마다 복원."""
    lz = _lz(); g = pd.read_csv(B / "b4_greedy_moves.csv", encoding="utf-8-sig")
    out = {}
    for y in (int(C.Y0), int(C.Y1)):
        lab = lz.life_zone_name.copy()
        for r in g[g.year == y].sort_values(["ku_name", "step"]).itertuples():
            assert lab[r.dong] == r.from_zone, (y, r.dong_name, lab[r.dong], r.from_zone)
            lab[r.dong] = r.to_zone
        out[y] = lab
    return out


def verify():
    from k01_compute import build_adjacency
    from k14_reassign import ifr, modularity, dmis
    adj, _ = build_adjacency(); lz = _lz(); fin = final_partitions()
    ldm = {y: pd.read_csv(C.ld_map(str(y)), encoding="utf-8-sig").set_index("Dong")["global_community_id"] for y in fin}
    gs = pd.read_csv(B / "b4_gu_summary.csv", encoding="utf-8-sig").set_index(["year", "ku_name"])
    R = {"권역수_유지": True, "공간연속": True, "비연속_권역": [], "요약값_최대차": 0.0}
    for y, lab in fin.items():
        od = pd.read_parquet(C.od_daily(str(y)), columns=["dong_O", "dong_D", "flow"])
        for K, grp in lz.groupby("Ku"):
            nodes = sorted(grp.index); pos = {d: i for i, d in enumerate(nodes)}; n = len(nodes)
            before, after = grp.loc[nodes, "life_zone_name"], lab.loc[nodes]
            if after.nunique() != before.nunique(): R["권역수_유지"] = False
            for z, mem in after.groupby(after):
                ms = set(mem.index); st = next(iter(ms)); seen = {st}; q = deque([st])
                while q:
                    v = q.popleft()
                    for j in adj[v]:
                        if j in ms and j not in seen: seen.add(j); q.append(j)
                if seen != ms: R["공간연속"] = False; R["비연속_권역"].append(f"{y} {z}")
            o = od[od.dong_O.isin(pos)]; Tsum = float(o.flow.sum()); w = o[o.dong_D.isin(pos)]; W = np.zeros((n, n))
            np.add.at(W, (w.dong_O.map(pos).values, w.dong_D.map(pos).values), w.flow.values)
            labv = pd.factorize(after)[0]; ldv = pd.factorize(ldm[y].loc[nodes])[0]
            ref = gs.loc[(y, grp.ku_name.iat[0])]
            for mine, key in ((ifr(W, Tsum, labv), "IFR_after"), (modularity(W + W.T, labv), "Q_after"), (dmis(W, Tsum, labv, ldv), "D_after")):
                R["요약값_최대차"] = max(R["요약값_최대차"], abs(mine - ref[key]))
    R["판정"] = "통과" if R["권역수_유지"] and R["공간연속"] and R["요약값_최대차"] < 1e-9 else "실패"
    (B / "b8_verify.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    return R


# ---------------- 그림 ----------------
def _plt():
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False
    return plt


def fig_framework():
    plt = _plt(); from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    fig, ax = plt.subplots(figsize=(10, 3.3)); ax.set_xlim(0, 10); ax.set_ylim(0.1, 4.25); ax.axis("off")
    top = [(0.15, "공식 생활권 116\n(평가 대상)"), (3.55, "무작위 비교경계\n구마다 1,000가지\n(바닥 기준선)"), (6.95, "빅데이터 기반 가상경계\n생활이동으로 도출\n(천장·목표점)")]
    for x, s in top:
        ax.add_patch(FancyBboxPatch((x, 3.1), 2.9, 1.0, boxstyle="round,pad=0.04", fc="#eef2f7", ec="black", lw=0.8)); ax.text(x + 1.45, 3.6, s, ha="center", va="center", fontsize=9)
    steps = ["① 착시 확인\nIFR 상승·크기 편향", "② 전체 평가\n크기를 맞춘 무작위 대비\n(구·생활권)", "③ 동 진단\n옮기면 IFR과 모듈성이\n모두 나아지는가", "④ 재배정\n나아지는 이동을 차례로\n→ 천장 도달", "⑤ 반복 확인\n2020·2025 독립 계산", "⑥ 원인 탐색\n접근성·역·상업·\n일자리·주거 특성"]
    for i, s in enumerate(steps):
        x = 0.1 + i * 1.65
        ax.add_patch(FancyBboxPatch((x, 0.85), 1.5, 1.35, boxstyle="round,pad=0.04", fc="white", ec="black", lw=0.8)); ax.text(x + 0.75, 1.52, s, ha="center", va="center", fontsize=8)
        if i < 5: ax.add_patch(FancyArrowPatch((x + 1.52, 1.52), (x + 1.63, 1.52), arrowstyle="-|>", mutation_scale=8, lw=0.8))
    ax.text(5, 0.4, "자료: 서울 생활이동 OD 2020-01·2025-01(행정동 424) · 공식 생활권 116 · 동 인접 관계   (원인 탐색) 시설 33종 · 격자 인구·가구·종사자", ha="center", fontsize=7.4)
    for x in (1.6, 5.0, 8.4): ax.add_patch(FancyArrowPatch((x, 3.08), (x, 2.23), arrowstyle="-|>", mutation_scale=8, lw=0.6, ls="--"))
    fig.tight_layout(); fig.savefig(FIG / "Fv2_1_framework.png", dpi=220); plt.close()


def fig_size_bias():
    plt = _plt(); g = pd.read_csv(B / "b1_gu.csv", encoding="utf-8-sig"); g = g[(g.boundary == "LZ") & (g.year == int(C.Y1))].sort_values("pct_N1")
    fig, ax = plt.subplots(figsize=(7.2, 6.4)); y = np.arange(len(g))
    ax.hlines(y, g.pct_N0 * 100, g.pct_N1 * 100, color="#bbbbbb", lw=1.4)
    ax.scatter(g.pct_N0 * 100, y, s=26, facecolor="white", edgecolor="#555", label="크기 제약 없는 무작위(N0) 대비", zorder=3)
    ax.scatter(g.pct_N1 * 100, y, s=30, color="#1f4e79", label="동 수를 맞춘 무작위(N1) 대비", zorder=3)
    ax.axvline(50, color="#c0392b", ls="--", lw=0.8); ax.text(50.5, len(g) - 0.6, "무작위와 같음", color="#c0392b", fontsize=7.5)
    ax.set_yticks(y); ax.set_yticklabels(g.ku_name, fontsize=8); ax.set_xlabel("공식 생활권 IFR의 백분위(무작위 비교경계 중 몇 %보다 높은가, 2025)")
    ax.set_xlim(0, 101); ax.legend(loc="lower right", fontsize=8, frameon=False); ax.grid(axis="x", alpha=0.3)
    fig.tight_layout(); fig.savefig(FIG / "Fv2_2_size_bias.png", dpi=220); plt.close()


def _dong_gdf():
    import geopandas as gpd
    g = gpd.read_file(C.DONG_GPKG, layer="epsg5179")[["Dong", "Ku", "geometry"]]; g["Dong"] = g.Dong.astype(int); return g


def fig_dong_map():
    plt = _plt(); g = _dong_gdf(); lz = _lz(); d = pd.read_csv(B / "b3_dong.csv", encoding="utf-8-sig"); gm = pd.read_csv(B / "b4_greedy_moves.csv", encoding="utf-8-sig")
    m20 = set(gm[gm.year == int(C.Y0)].dong); m25 = set(gm[gm.year == int(C.Y1)].dong)
    s20 = set(zip(gm[gm.year == int(C.Y0)].dong, gm[gm.year == int(C.Y0)].to_zone)); s25 = set(zip(gm[gm.year == int(C.Y1)].dong, gm[gm.year == int(C.Y1)].to_zone))
    both = {x for x, _ in s20 & s25}
    nb = set(d[(d.boundary == "LZ") & (d.year == int(C.Y1)) & d.misassigned].dong)
    cat = pd.Series("그 밖의 동", index=g.Dong)
    cat[cat.index.isin(nb)] = "옆 생활권 지향(크기 효과 포함)"; cat[cat.index.isin(m25 | m20)] = "재배정 권고(한 해)"; cat[cat.index.isin(both)] = "재배정 권고(두 해 모두)"
    g["cat"] = cat.values; g["lz"] = g.Dong.map(lz.life_zone_id)
    col = {"그 밖의 동": "#f2f2f2", "옆 생활권 지향(크기 효과 포함)": "#cfe2f3", "재배정 권고(한 해)": "#f6b26b", "재배정 권고(두 해 모두)": "#c0392b"}
    fig, ax = plt.subplots(figsize=(8.6, 7.0))
    for k, c in col.items(): g[g.cat == k].plot(ax=ax, color=c, edgecolor="white", linewidth=0.3)
    g.dissolve("lz").boundary.plot(ax=ax, color="#333", linewidth=0.7); g.dissolve("Ku").boundary.plot(ax=ax, color="black", linewidth=1.3)
    import matplotlib.patches as mp
    ax.legend(handles=[mp.Patch(color=c, label=f"{k} ({int((g.cat == k).sum())})") for k, c in col.items()], loc="lower left", fontsize=7.5, frameon=False)
    ax.set_axis_off(); fig.tight_layout(); fig.savefig(FIG / "Fv2_3_dong_diagnosis_map.png", dpi=220); plt.close()


def fig_gu_bars():
    plt = _plt(); s = pd.read_csv(B / "b4_gu_summary.csv", encoding="utf-8-sig"); s = s[s.year == int(C.Y1)].sort_values("dIFR_pp")
    fig, ax = plt.subplots(figsize=(7.2, 6.6)); y = np.arange(len(s))
    ax.scatter(s.IFR_before * 100, y, s=24, facecolor="white", edgecolor="#555", label="공식 생활권", zorder=3)
    ax.scatter(s.IFR_after * 100, y, s=26, color="#c0392b", label="경계 동 재배정 후", zorder=3)
    ax.scatter(s.IFR_LD * 100, y, marker="|", s=110, color="#1f4e79", label="빅데이터 기반 가상경계", zorder=4)
    ax.hlines(y, s.IFR_before * 100, s.IFR_after * 100, color="#dddddd", lw=1.2)
    ax.set_yticks(y); ax.set_yticklabels([f"{r.ku_name} ({int(r.n_moved)})" for r in s.itertuples()], fontsize=8)
    ax.set_xlabel("구 IFR (%) — 괄호는 옮긴 동 수, 2025"); ax.legend(loc="lower right", fontsize=8, frameon=False); ax.grid(axis="x", alpha=0.3)
    fig.tight_layout(); fig.savefig(FIG / "Fv2_4_gu_reassign_ifr.png", dpi=220); plt.close()


def fig_case():
    plt = _plt(); g = _dong_gdf(); lz = _lz(); fin = final_partitions()[int(C.Y1)]
    ld = pd.read_csv(C.ld_map(C.Y1), encoding="utf-8-sig").set_index("Dong")["global_community_id"]
    gm = pd.read_csv(B / "b4_greedy_moves.csv", encoding="utf-8-sig"); gm = gm[(gm.year == int(C.Y1)) & (gm.ku_name == CASE_KU)]
    K = lz[lz.ku_name == CASE_KU].Ku.iat[0]; gk = g[g.Ku == K].copy()
    gk["LZ"] = gk.Dong.map(lz.life_zone_name); gk["RE"] = gk.Dong.map(fin); gk["LD"] = gk.Dong.map(ld)
    names = dict(zip(lz.index, lz.ADM_NM))
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.2)); cmap = plt.get_cmap("Set2")
    for ax, col, t in zip(axes, ("LZ", "RE", "LD"), ("공식 생활권", f"경계 동 재배정 후({len(gm)}개 동)", "빅데이터 기반 가상경계")):
        codes = pd.factorize(gk[col])[0]; gk.assign(c=codes).plot(column="c", cmap=cmap, categorical=True, edgecolor="white", linewidth=0.6, ax=ax)
        gk.dissolve(col).boundary.plot(ax=ax, color="#222", linewidth=1.1)
        if col == "RE": gk[gk.Dong.isin(gm.dong)].boundary.plot(ax=ax, color="#c0392b", linewidth=1.8, linestyle="--")
        for r in gk.itertuples():
            c = r.geometry.representative_point(); ax.text(c.x, c.y, names[r.Dong], fontsize=5.8, ha="center")
        ax.set_axis_off(); ax.set_title(t, fontsize=10, loc="center", pad=6)
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.02, top=0.90, wspace=0.04)
    fig.savefig(FIG / "Fv2_5_case_gwangjin.png", dpi=220); plt.close()


# ---------------- 표 사양 ----------------
p1 = lambda x: f"{x * 100:.1f}"; p0 = lambda x: f"{x * 100:.0f}"


def build_tables_v2():
    t01 = pd.read_csv(C.TAB / "t01_data_summary.csv", encoding="utf-8-sig", dtype={"year": str}).set_index("year")
    g = pd.read_csv(B / "b1_gu.csv", encoding="utf-8-sig"); s = json.loads((B / "b4_summary.json").read_text(encoding="utf-8"))
    gs = pd.read_csv(B / "b4_gu_summary.csv", encoding="utf-8-sig"); gm = pd.read_csv(B / "b4_greedy_moves.csv", encoding="utf-8-sig")
    b5 = json.loads((B / "b5_summary.json").read_text(encoding="utf-8")); b6 = json.loads((B / "b6_summary.json").read_text(encoding="utf-8")); b7 = json.loads((B / "b7_summary.json").read_text(encoding="utf-8"))
    T = {}
    T["T1"] = dict(ko="1. 분석 자료", en="1. Data", headers=["자료", "시점·범위", "처리", "역할"], widths=[3.2, 3.6, 6.4, 3.0],
                   rows=[["서울 생활이동 OD", "2020년 1월, 2025년 1월", "도착 09:00~20:59, 통근(HW·WH) 제외, 요일 전체, 서울 내부, 비공개 행 0", "IFR·모듈성 계산"],
                         ["행정동 경계·인접", "424개(두 해 공통 정본)", "2021년 코드표 기준 통일, 경계 공유로 인접 판정", "집계·재배정 단위"],
                         ["공식 지역생활권", "116개(2030 서울생활권계획)", "행정동→생활권 면적 최대 중첩(최솟값 0.51)", "평가 대상"],
                         ["빅데이터 기반 가상경계", "연도별 116개", "자치구 내 Leiden 합의(3,000회, τ = 0.5), 개수 = 공식 생활권", "천장·목표점"],
                         ["필터 후 통행량", f"{t01.loc['2020','flow_daily_seoul']/1e6:,.1f}백만 / {t01.loc['2025','flow_daily_seoul']/1e6:,.1f}백만", f"비공개 행 {t01.loc['2020','masked_row_share_daily']*100:.1f}% / {t01.loc['2025','masked_row_share_daily']*100:.1f}%", "—"],
                         ["(원인 탐색) 시설·격자", "2019-12-31 / 2024-12-31", "시설 33종, 100 m 격자 인구·가구·종사자", "Ⅳ.5에서만 사용"]],
                   note="생활이동 자료는 서울시·KT의 추정 이동량이며 3명 미만 셀은 비공개 처리되어 0으로 두었다.")
    T["T2"] = dict(ko="2. 무작위 비교경계와 평가 지표", en="2. Random Comparison Boundaries and Measures", headers=["구분", "정의", "용도"], widths=[3.0, 9.4, 3.8],
                   rows=[["무작위 비교경계 N0", "같은 구 안에서 인접한 동끼리 무작위로 묶은 경계, 권역 수 = 비교 대상, 크기 제약 없음", "크기 편향 확인"],
                         ["무작위 비교경계 N1", "N0 + 권역별 동 수를 비교 대상과 똑같이", "주 기준"],
                         ["무작위 비교경계 N2", "N1 + 권역별 출발 통행량 비중을 비슷하게(정렬 비중의 최대 차 ≤ 0.05)", "강건성"],
                         ["IFR", "출발 통행 중 같은 권역 안에서 끝나는 비율(구 단위 분자합/분모합)", "착시·전체 평가"],
                         ["백분위", "무작위 비교경계 1,000가지 중 IFR이 더 낮은 비율(같으면 절반). 50% = 무작위 수준", "전체 평가"],
                         ["모듈성 Q", "구 안 무방향 통행망에서 동의 통행 규모로 기대되는 몫을 뺀 권역 내부 통행. 크기 편향을 통제", "동 진단·재배정"],
                         ["판정 차이 D", "공식 생활권과 가상경계가 권역 안/밖을 다르게 판정한 통행의 비율", "재배정 검증"]],
                   note="무작위 비교경계는 구마다 1,000가지를 만든다. 1,000은 동 수가 아니라 서로 다른 경계의 가짓수다.")
    rows = []
    for r in g[g.boundary == "LZ"].pivot(index="ku_name", columns="year", values=["pct_N0", "pct_N1", "pct_N2"]).sort_values(("pct_N1", int(C.Y1))).itertuples():
        rows.append([r.Index, p0(r[1]), p0(r[2]), p0(r[3]), p0(r[4]), p0(r[5]), p0(r[6])])
    ld = g[g.boundary == "LD"].groupby("year")[["pct_N0", "pct_N1", "pct_N2"]].median(); lzmed = g[g.boundary == "LZ"].groupby("year")[["pct_N0", "pct_N1", "pct_N2"]].median()
    rows.append(["중앙값(공식 생활권)", p0(lzmed.loc[int(C.Y0), "pct_N0"]), p0(lzmed.loc[int(C.Y1), "pct_N0"]), p0(lzmed.loc[int(C.Y0), "pct_N1"]), p0(lzmed.loc[int(C.Y1), "pct_N1"]), p0(lzmed.loc[int(C.Y0), "pct_N2"]), p0(lzmed.loc[int(C.Y1), "pct_N2"])])
    rows.append(["중앙값(가상경계)", p0(ld.loc[int(C.Y0), "pct_N0"]), p0(ld.loc[int(C.Y1), "pct_N0"]), p0(ld.loc[int(C.Y0), "pct_N1"]), p0(ld.loc[int(C.Y1), "pct_N1"]), p0(ld.loc[int(C.Y0), "pct_N2"]), p0(ld.loc[int(C.Y1), "pct_N2"])])
    T["T3"] = dict(ko="3. 공식 생활권 IFR의 무작위 비교경계 대비 백분위(%)", en="3. Percentile of Official Living-Zone IFR against Random Comparison Boundaries (%)",
                   headers=["구", "N0 2020", "N0 2025", "N1 2020", "N1 2025", "N2 2020", "N2 2025"], widths=[3.2] + [2.0] * 6, rows=rows, bold_last=True,
                   note="가상경계는 자기 권역 크기에 맞춘 무작위 비교경계와 비교했다. 50%는 무작위 수준.")
    k = lambda y, n: s[f"{y}_{n}"]
    T["T4"] = dict(ko="4. 경계 동 한 개씩 옮기기 시험", en="4. Single-Dong Move Test", headers=["집단", "연도", "동 수", "IFR 개선", "모듈성 개선", "둘 다 개선", "IFR만 개선(크기 효과)"], widths=[4.4, 1.3, 1.5, 1.8, 2.0, 1.9, 2.8],
                   rows=[["옆 생활권 지향 동", y, k(y, "옆생활권지향동")["n"], k(y, "옆생활권지향동")["ΔIFR>0"], k(y, "옆생활권지향동")["ΔQ>0"], k(y, "옆생활권지향동")["둘다>0"], k(y, "옆생활권지향동")["ΔIFR>0_ΔQ≤0(크기효과)"]] for y in (C.Y0, C.Y1)] +
                        [["그 밖의 경계 동", y, k(y, "그밖의_경계동")["n"], k(y, "그밖의_경계동")["ΔIFR>0"], k(y, "그밖의_경계동")["ΔQ>0"], k(y, "그밖의_경계동")["둘다>0"], k(y, "그밖의_경계동")["ΔIFR>0_ΔQ≤0(크기효과)"]] for y in (C.Y0, C.Y1)],
                   note="옆 생활권 지향 동 = 자기 동 내부통행을 빼고 옆 생활권으로 더 많이 보내는 동. 동마다 가장 나은 이동 하나로 셌다. 옮긴 뒤에도 권역 수 유지·공간 연속.")
    rows = []
    for y in (C.Y0, C.Y1):
        q = k(y, "탐욕재배정"); rows.append([y, q["옮긴_동"], q["옮긴_구"], f"{q['서울IFR_전']:.1f}", f"{q['서울IFR_후']:.1f}", f"{q['서울IFR_가상경계']:.1f}", f"{q['서울D_전']:.1f}", f"{q['서울D_후']:.1f}", f"{q['Q_전_중앙']:.3f}", f"{q['Q_후_중앙']:.3f}", f"{q['Q_가상경계_중앙']:.3f}"])
    T["T5"] = dict(ko="5. 경계 동 재배정 결과", en="5. Results of Boundary-Dong Reassignment", headers=["연도", "옮긴 동", "해당 구", "IFR 전(%)", "IFR 후(%)", "IFR 가상경계(%)", "D 전(%)", "D 후(%)", "Q 전", "Q 후", "Q 가상경계"],
                   widths=[1.2, 1.4, 1.4, 1.5, 1.5, 1.9, 1.3, 1.3, 1.3, 1.3, 1.7], rows=rows,
                   note=f"모듈성이 가장 많이 오르는 이동부터 하나씩 적용하고 더 오르는 이동이 없을 때 멈췄다. IFR·D는 서울 전체(분자합/분모합), Q는 구 중앙값. 두 해 모두 같은 이동 {s['두해모두_권고_이동']}개(2020만 {s['2020만']}, 2025만 {s['2025만']}).")
    A = lambda y, key, grp: b5["경계비용_COV_main"][str(y)][key]
    r6 = lambda y, kk, g_: b6["결과"][str(y)][kk][g_]
    T["T6"] = dict(ko="6. 재배정 권고 동은 왜 옆 생활권으로 가는가", en="6. Why Do Reassigned Dongs Lean toward Neighbouring Zones?", headers=["후보 요인", "지표", "권고 동 2020/2025", "그 밖의 경계 동 2020/2025", "p 2020/2025", "판정"],
                   widths=[2.6, 4.4, 2.6, 2.8, 2.2, 1.6],
                   rows=[["기초 생활시설", "경계 때문에 잃는 15분 Coverage(%p, 중앙값)", f"{A(2020,'A_중앙','')*100:.1f} / {A(2025,'A_중앙','')*100:.1f}", f"{A(2020,'B_중앙','')*100:.1f} / {A(2025,'B_중앙','')*100:.1f}", f"{A(2020,'p_A_vs_B',''):.2f} / {A(2025,'p_A_vs_B',''):.2f}", "관계없음"],
                         ["지하철역", "옆 권역 역이 더 가까운 동 비율(%)", f"{r6(2020,'역','A_옆이더가까움_비율')*100:.0f} / {r6(2025,'역','A_옆이더가까움_비율')*100:.0f}", f"{r6(2020,'역','B_비율')*100:.0f} / {r6(2025,'역','B_비율')*100:.0f}", f"{r6(2020,'역','p'):.3f} / {r6(2025,'역','p'):.3f}", "약한 신호"],
                         ["대형 상업시설", "옆 권역 대규모점포가 더 가까운 동 비율(%)", f"{r6(2020,'대형상업','A_옆이더가까움_비율')*100:.0f} / {r6(2025,'대형상업','A_옆이더가까움_비율')*100:.0f}", f"{r6(2020,'대형상업','B_비율')*100:.0f} / {r6(2025,'대형상업','B_비율')*100:.0f}", f"{r6(2020,'대형상업','p'):.2f} / {r6(2025,'대형상업','p'):.2f}", "관계없음"],
                         ["문화시설", "옆 권역 문화시설이 더 가까운 동 비율(%)", f"{r6(2020,'문화','A_옆이더가까움_비율')*100:.0f} / {r6(2025,'문화','A_옆이더가까움_비율')*100:.0f}", f"{r6(2020,'문화','B_비율')*100:.0f} / {r6(2025,'문화','B_비율')*100:.0f}", f"{r6(2020,'문화','p'):.2f} / {r6(2025,'문화','p'):.2f}", "관계없음"],
                         ["주거 특성", "옮겨 갈 권역이 더 비슷한 동 비율(%)", f"{b7['결과']['2020']['옮겨갈권역이_더비슷한_비율']['A']*100:.0f} / {b7['결과']['2025']['옮겨갈권역이_더비슷한_비율']['A']*100:.0f}", f"{b7['결과']['2020']['옮겨갈권역이_더비슷한_비율']['B']*100:.0f} / {b7['결과']['2025']['옮겨갈권역이_더비슷한_비율']['B']*100:.0f}", f"{b7['결과']['2020']['옮겨갈권역이_더비슷한_비율']['p']:.2f} / {b7['결과']['2025']['옮겨갈권역이_더비슷한_비율']['p']:.2f}", "관계없음"],
                         ["중심 권역 편입", "자기 권역 인구당 종사자 ÷ 동(배, 중앙값)", f"{b7['결과']['2020']['업무성차_자기권역−동_중앙(배, exp)']['A']:.2f} / {b7['결과']['2025']['업무성차_자기권역−동_중앙(배, exp)']['A']:.2f}", f"{b7['결과']['2020']['업무성차_자기권역−동_중앙(배, exp)']['B']:.2f} / {b7['결과']['2025']['업무성차_자기권역−동_중앙(배, exp)']['B']:.2f}", f"{b7['결과']['2020']['업무성차_자기권역−동_중앙(배, exp)']['p']:.3f} / {b7['결과']['2025']['업무성차_자기권역−동_중앙(배, exp)']['p']:.3f}", "약한 신호"]],
                   note="권고 동 = 재배정된 동 중 원래 공식 생활권에서 바로 옮길 수 있던 동(2020 56, 2025 57개). 사전 기준: 차이 10%p 이상(또는 방향 일치)·p < 0.05가 두 해 모두 성립해야 '관계 있음'. 거리는 격자 인구가중 중심에서의 직선거리.")
    common = gm[gm.year == int(C.Y1)].merge(gm[gm.year == int(C.Y0)][["dong", "to_zone"]], on=["dong", "to_zone"])
    T["TA1"] = dict(ko="A1. 두 해 모두 권고된 경계 동 재배정", en="A1. Reassignments Recommended in Both Years", headers=["구", "동", "현재 생활권", "옮겨 갈 생활권"], widths=[2.4, 3.4, 5.0, 5.0],
                    rows=[[r.ku_name, r.dong_name, r.from_zone.split("_", 1)[1], r.to_zone.split("_", 1)[1]] for r in common.sort_values(["ku_name", "dong_name"]).itertuples()],
                    note="통행만으로 본 검토 우선순위이며, 학군·행정 관할·지역 정체성 등은 반영하지 않았다.")
    return T


FIGS_V2 = {
    "F1": ("1. 분석의 틀", "1. Analytical Framework", "Fv2_1_framework.png", 15.0, "무작위 비교경계는 바닥 기준선, 빅데이터 기반 가상경계는 천장(목표점)으로 쓴다."),
    "F2": ("2. 크기 편향: 공식 생활권 IFR의 무작위 비교경계 대비 백분위(2025)", "2. Size Bias: Percentile of Official-Zone IFR against Random Boundaries, 2025", "Fv2_2_size_bias.png", 12.0, "빈 점은 크기 제약 없는 무작위, 찬 점은 동 수를 맞춘 무작위 대비. 붉은 선은 무작위 수준(50%)."),
    "F3": ("3. 동 진단 결과(2025)", "3. Dong-Level Diagnosis, 2025", "Fv2_3_dong_diagnosis_map.png", 14.0, "가는 선은 공식 생활권, 굵은 선은 자치구 경계. 괄호는 동 수."),
    "F4": ("4. 구별 경계 동 재배정 전후 IFR(2025)", "4. District IFR before and after Boundary-Dong Reassignment, 2025", "Fv2_4_gu_reassign_ifr.png", 12.0, "세로 막대는 빅데이터 기반 가상경계의 IFR."),
    "F5": ("5. 사례: 광진구의 공식 생활권·재배정 후·가상경계(2025)", "5. Case: Gwangjin-gu, 2025", "Fv2_5_case_gwangjin.png", 15.5, "붉은 점선은 옮겨진 동."),
    "FA1": ("A1. 두 경계의 ΔIFR과 무작위 비교경계의 ΔIFR 분포", "A1. ΔIFR of the Two Boundaries against Random Comparison Boundaries", "F4-4-6_null_partition_dIFR.png", 15.5, "회색 상자는 무작위 비교경계 1,000가지의 5~95% 구간."),
}


def draw_all():
    fig_framework(); fig_size_bias(); fig_dong_map(); fig_gu_bars(); fig_case()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(verify(), ensure_ascii=False, indent=1)); draw_all(); t = build_tables_v2(); print("표", list(t), "| 그림 생성 완료")
