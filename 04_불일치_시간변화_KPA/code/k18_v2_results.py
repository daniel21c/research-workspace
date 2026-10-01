# -*- coding: utf-8 -*-
"""
k18 — KPA v2(경계 동 진단·재배정) 원고용 표·그림 사양과 재배정 결과 검증

1) 검증: k14 탐욕 재배정의 최종 분할을 이동 기록으로 다시 만들어
   (a) 권역 수 유지 (b) 모든 권역 공간 연속 (c) IFR·Q·D가 b4_gu_summary와 같은지 확인 → benchmark/b8_verify.json
2) 그림: Fv2_1 분석 틀, Fv2_2 크기 편향(구별 백분위 N0 vs N1), Fv2_3 동 진단 지도(2025),
         Fv2_4 구별 재배정 전후 IFR(2025), Fv2_5 사례 구(광진구) 공식/재배정/커뮤니티 지도,
         Fv2_A1 부록 ΔIFR vs 무작위 경계
3) 표 사양 build_tables_v2(), 그림 사양 FIGS_V2 — k19(docx)·k09(hwp)가 가져다 쓴다.
"""
from __future__ import annotations
import json, sys
from collections import deque
import numpy as np
import pandas as pd
import config as C

B = C.TAB / "benchmark"; FIG = C.FIG
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
    fig, ax = plt.subplots(figsize=(10, 3.4)); ax.set_xlim(0, 10); ax.set_ylim(0.1, 4.3); ax.axis("off")
    top = [(0.15, "기존 생활권 116\n(평가 대상)"), (3.55, "무작위 경계\n자치구마다 1,000번 추출\n(최소 기준)"), (6.95, "데이터 기반 커뮤니티\n같은 해 생활이동으로 도출\n(비교 기준)")]
    for x, t in top:
        ax.add_patch(FancyBboxPatch((x, 3.1), 2.9, 1.05, boxstyle="round,pad=0.04", fc="#eef2f7", ec="black", lw=0.8)); ax.text(x + 1.45, 3.62, t, ha="center", va="center", fontsize=9)
    steps = ["① 내부통행률 상승이\n경계 덕분인지 판별\n무작위 경계 대비, 유형·평일/주말 분해", "② 불일치의 추적\n불일치 D·격차 G\nG 변화의 분해", "③ 전반적 적합성\n크기를 맞춘\n무작위 대비 백분위",
             "④ 경계 동 진단\n한 동씩 옮겨 보기\nIFR·모듈러리티 동시 개선", "⑤ 재배정과 지속성\n단계적 재배정·두 해 비교\n2020 경계의 2025 적용"]
    for k, t in enumerate(steps):
        x = 0.1 + k * 1.98
        ax.add_patch(FancyBboxPatch((x, 0.8), 1.8, 1.45, boxstyle="round,pad=0.04", fc="white", ec="black", lw=0.8)); ax.text(x + 0.9, 1.52, t, ha="center", va="center", fontsize=8)
        if k < 4: ax.add_patch(FancyArrowPatch((x + 1.82, 1.52), (x + 1.96, 1.52), arrowstyle="-|>", mutation_scale=8, lw=0.8))
    ax.text(5, 0.35, "자료: 서울 생활이동 OD 2020년 1월·2025년 1월(행정동 424) · 기존 생활권 116 · 행정동 인접 관계", ha="center", fontsize=7.6)
    for x in (1.6, 5.0, 8.4): ax.add_patch(FancyArrowPatch((x, 3.08), (x, 2.28), arrowstyle="-|>", mutation_scale=8, lw=0.6, ls="--"))
    fig.tight_layout(); fig.savefig(FIG / "Fv2_1_framework.png", dpi=220); plt.close()


def fig_size_bias():
    plt = _plt(); g = pd.read_csv(B / "b1_gu.csv", encoding="utf-8-sig"); g = g[(g.boundary == "LZ") & (g.year == int(C.Y1))].sort_values("pct_N1")
    fig, ax = plt.subplots(figsize=(7.2, 6.4)); y = np.arange(len(g))
    ax.hlines(y, g.pct_N0 * 100, g.pct_N1 * 100, color="#bbbbbb", lw=1.4)
    ax.scatter(g.pct_N0 * 100, y, s=26, facecolor="white", edgecolor="#555", label="크기 제약 없는 무작위(N0) 대비", zorder=3)
    ax.scatter(g.pct_N1 * 100, y, s=30, color="#1f4e79", label="동 수를 맞춘 무작위(N1) 대비", zorder=3)
    ax.axvline(50, color="#c0392b", ls="--", lw=0.8); ax.text(50.5, len(g) - 0.6, "무작위와 같음", color="#c0392b", fontsize=7.5)
    ax.set_yticks(y); ax.set_yticklabels(g.ku_name, fontsize=8); ax.set_xlabel("기존 생활권 IFR의 백분위(무작위 경계 중 몇 %보다 높은가, 2025)")
    ax.set_xlim(0, 101); ax.legend(loc="lower right", fontsize=8, frameon=False); ax.grid(axis="x", alpha=0.3)
    fig.tight_layout(); fig.savefig(FIG / "Fv2_2_size_bias.png", dpi=220); plt.close()


def _dong_gdf():
    import geopandas as gpd
    g = gpd.read_file(C.DONG_GPKG, layer="epsg5179")[["Dong", "Ku", "geometry"]]; g["Dong"] = g.Dong.astype(int); return g


def fig_dong_map():
    plt = _plt(); g = _dong_gdf(); lz = _lz(); d = pd.read_csv(B / "b3_dong.csv", encoding="utf-8-sig"); gm = pd.read_csv(B / "b4_greedy_moves.csv", encoding="utf-8-sig")
    m20 = set(gm[gm.year == int(C.Y0)].dong); m25 = set(gm[gm.year == int(C.Y1)].dong)
    from k14_reassign import final_changes
    f20, f25 = final_changes(gm, lz, int(C.Y0)), final_changes(gm, lz, int(C.Y1))
    m20 = {d for d, _, _ in f20}; m25 = {d for d, _, _ in f25}; both = {d for d, _, _ in f20 & f25}
    nb = set(d[(d.boundary == "LZ") & (d.year == int(C.Y1)) & d.misassigned].dong)
    cat = pd.Series("그 밖의 동", index=g.Dong)
    cat[cat.index.isin(nb)] = "옆 생활권 지향(크기 효과 포함)"; cat[cat.index.isin(m25 | m20)] = "재배정(한 해만 또는 두 해 목적지 다름)"; cat[cat.index.isin(both)] = "재배정(두 해 같은 생활권으로)"
    g["cat"] = cat.values; g["lz"] = g.Dong.map(lz.life_zone_id)
    col = {"그 밖의 동": "#f2f2f2", "옆 생활권 지향(크기 효과 포함)": "#cfe2f3", "재배정(한 해만 또는 두 해 목적지 다름)": "#f6b26b", "재배정(두 해 같은 생활권으로)": "#c0392b"}
    fig, ax = plt.subplots(figsize=(8.6, 7.0))
    for k, c in col.items(): g[g.cat == k].plot(ax=ax, color=c, edgecolor="white", linewidth=0.3)
    g.dissolve("lz").boundary.plot(ax=ax, color="#333", linewidth=0.7); g.dissolve("Ku").boundary.plot(ax=ax, color="black", linewidth=1.3)
    import matplotlib.patches as mp
    ax.legend(handles=[mp.Patch(color=c, label=f"{k} ({int((g.cat == k).sum())})") for k, c in col.items()], loc="lower left", fontsize=7.5, frameon=False)
    ax.set_axis_off(); fig.tight_layout(); fig.savefig(FIG / "Fv2_3_dong_diagnosis_map.png", dpi=220); plt.close()


def fig_gu_bars():
    plt = _plt(); s = pd.read_csv(B / "b4_gu_summary.csv", encoding="utf-8-sig"); s = s[s.year == int(C.Y1)].sort_values("dIFR_pp")
    fig, ax = plt.subplots(figsize=(7.2, 6.6)); y = np.arange(len(s))
    ax.scatter(s.IFR_before * 100, y, s=24, facecolor="white", edgecolor="#555", label="기존 생활권", zorder=3)
    ax.scatter(s.IFR_after * 100, y, s=26, color="#c0392b", label="경계 동 재배정 후", zorder=3)
    ax.scatter(s.IFR_LD * 100, y, marker="|", s=110, color="#1f4e79", label="데이터 기반 커뮤니티", zorder=4)
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
    for ax, col, t in zip(axes, ("LZ", "RE", "LD"), ("기존 생활권", f"경계 동 재배정 후({len(gm)}개 동)", "데이터 기반 커뮤니티")):
        codes = pd.factorize(gk[col])[0]; gk.assign(c=codes).plot(column="c", cmap=cmap, categorical=True, edgecolor="white", linewidth=0.6, ax=ax)
        gk.dissolve(col).boundary.plot(ax=ax, color="#222", linewidth=1.1)
        if col == "RE": gk[gk.Dong.isin(gm.dong)].boundary.plot(ax=ax, color="#c0392b", linewidth=1.8, linestyle="--")
        for r in gk.itertuples():
            c = r.geometry.representative_point(); ax.text(c.x, c.y, names[r.Dong], fontsize=5.8, ha="center")
        ax.set_axis_off(); ax.set_title(t, fontsize=10, loc="center", pad=6)
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.02, top=0.90, wspace=0.04)
    fig.savefig(FIG / "Fv2_5_case_gwangjin.png", dpi=220); plt.close()


def fig_null_dIFR():
    """부록 그림 A1: 구별 두 경계의 ΔIFR과 무작위 경계(N0, 구마다 1,000번 추출) ΔIFR의 5~95% 구간(k01 결과 t05_null_summary)."""
    plt = _plt(); import matplotlib.ticker as mt
    d = pd.read_csv(C.TAB / "t05_null_summary.csv", encoding="utf-8-sig").sort_values("null_dIFR_med"); y = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(6.8, 7.4))
    ax.hlines(y, d.null_dIFR_p05, d.null_dIFR_p95, color="#d0d0d0", lw=6, label="무작위 경계 ΔIFR 5~95% (구마다 1,000번 추출)")
    ax.scatter(d.null_dIFR_med, y, marker="|", s=120, color="#666", label="무작위 경계 중앙값", zorder=3)
    ax.scatter(d.dIFR_lz, y, s=26, color="#1f4e79", zorder=4, label="기존 생활권")
    ax.scatter(d.dIFR_ld, y, s=26, color="#c0392b", zorder=4, label="데이터 기반 커뮤니티")
    ax.set_yticks(y); ax.set_yticklabels(d.ku_name, fontsize=8); ax.axvline(0, color="#999", lw=0.8)
    ax.xaxis.set_major_formatter(mt.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel(f"ΔIFR = IFR {C.Y1} - IFR {C.Y0}"); ax.legend(frameon=False, fontsize=7.5, loc="lower right"); ax.grid(axis="x", alpha=0.3)
    fig.tight_layout(); fig.savefig(FIG / "Fv2_A1_null_dIFR.png", dpi=220); plt.close()


# ---------------- 표 사양 ----------------
p1 = lambda x: f"{x * 100:.1f}"; p0 = lambda x: f"{x * 100:.0f}"


def _null_note():
    """표 2 Note: 무작위 경계의 실제 표본(추출 횟수, 서로 다른 분할 수, N2 표본 수·허용치)을 b_null_meta에서 적는다(KPA 관행에 따라 영문)."""
    mt = pd.read_csv(B / "b_null_meta.csv", encoding="utf-8-sig"); lz = mt[mt.boundary == "LZ"]
    n2_small = lz[lz.N2_n < 1000].sort_values("N2_n")
    relax = mt[mt.N2_tol > 0.05]
    ken = lambda ku: {"금천구": "Geumcheon-gu", "영등포구": "Yeongdeungpo-gu", "강남구": "Gangnam-gu"}.get(ku, ku)
    from k13_benchmark import SEED as K13_SEED
    txt = ("N0 and N1 are drawn 1,000 times per district with replacement (1,000 is the number of draws, not of dongs). "
           f"N0 was drawn twice: the sample for the rise in IFR (Figure A1) uses seed {C.NULL_SEED}, and the sample for percentiles and the size effect (Figure 2, Table A2) uses seed {K13_SEED}. "
           f"Distinct N1 partitions for the existing zones: {int(lz.N1_distinct.min())}~{int(lz.N1_distinct.max())} (small districts allow few partitions). "
           f"N2 keeps up to 1,000 N1 draws that meet the share condition; for the existing zones {len(n2_small)} districts have fewer than 1,000"
           + (f" (minimum {ken(n2_small.ku_name.iat[0])}, {int(n2_small.N2_n.iat[0])})" if len(n2_small) else "") + ", all with tolerance 0.05. "
           f"Distinct N2 partitions: {int(lz.N2_distinct.min())}~{int(lz.N2_distinct.max())} (minimum {ken(lz.sort_values('N2_distinct').ku_name.iat[0])}); because the same partition is drawn repeatedly in some districts, N2 is used only as a supplementary analysis. ")
    if len(relax): txt += "For the communities the tolerance was relaxed in " + ", ".join(f"{ken(r.ku_name)} {r.boundary} {r.N2_tol:g} ({int(r.N2_n)})" for r in relax.itertuples()) + "."
    return txt


def _min_overlap() -> float:
    """행정동→공식 생활권 대응의 겹침 비율 최솟값(코어 배포본 매핑 파일에서 읽음; 원고 본문의 0.51과 k24가 대조)."""
    return float(pd.read_csv(C.LZ_MAP, encoding="utf-8-sig").overlap_ratio.min())


def build_tables_v2():
    t01 = pd.read_csv(C.TAB / "t01_data_summary.csv", encoding="utf-8-sig", dtype={"year": str}).set_index("year")
    g = pd.read_csv(B / "b1_gu.csv", encoding="utf-8-sig"); s = json.loads((B / "b4_summary.json").read_text(encoding="utf-8"))
    gs = pd.read_csv(B / "b4_gu_summary.csv", encoding="utf-8-sig"); gm = pd.read_csv(B / "b4_greedy_moves.csv", encoding="utf-8-sig")
    S9 = json.loads((B / "b9_change_story.json").read_text(encoding="utf-8")); t9 = pd.read_csv(B / "b9_type_decomp.csv", encoding="utf-8-sig")
    S1 = json.loads((B / "b_summary.json").read_text(encoding="utf-8"))
    nb20, nb25 = (S1[f"동_LZ_{y}"]["이웃권역이_더_담는_동수"] for y in (C.Y0, C.Y1))      # 표 5 집단에서 옮길 수 없는 동을 빼기 전의 수(원고 Ⅳ.4 2))
    T = {}
    T["T1"] = dict(ko="1. 분석 자료", en="1. Data", headers=["자료", "시점·범위", "처리", "역할"], widths=[3.2, 3.6, 6.4, 3.0],
                   rows=[["서울 생활이동 OD", "2020년 1월, 2025년 1월", "도착 09:00~20:59, 통근(HW·WH) 제외, 요일 전체, 서울 내부, 비공개 행 0", "IFR·모듈러리티 계산"],
                         ["행정동 경계·인접", "424개(두 해 공통 정본)", "2021년 코드표 코드, 통계청 2023년 7월 경계 형상, 경계나 꼭짓점을 공유하면 이웃으로 봄", "집계·재배정 단위"],
                         ["기존 지역생활권", "116개(2030 서울생활권계획)", f"행정동→생활권 면적 최대 중첩(최솟값 {_min_overlap():.2f})", "평가 대상"],
                         ["데이터 기반 커뮤니티", "연도별 116개", "자치구 내 Leiden 합의(3,000회, τ = 0.5), 개수 = 기존 생활권", "이동 기반 비교 기준"],
                         ["필터 후 통행량", f"{t01.loc['2020','flow_daily_seoul']/1e6:,.1f}백만 / {t01.loc['2025','flow_daily_seoul']/1e6:,.1f}백만", f"비공개 행 {t01.loc['2020','masked_row_share_daily']*100:.1f}% / {t01.loc['2025','masked_row_share_daily']*100:.1f}%", "—"]],
                   note="Seoul living-movement data are travel estimates by the Seoul Metropolitan Government and KT; cells with fewer than three persons are not released and were set to zero.")
    T["T2"] = dict(ko="2. 무작위 경계와 평가 지표", en="2. Random Boundaries and Measures", headers=["구분", "정의", "용도"], widths=[3.0, 9.4, 3.8],
                   rows=[["무작위 경계 N0", "같은 구 안에서 인접한 동끼리 무작위로 묶은 경계, 권역 수 = 비교 대상, 크기 제약 없음", "크기 편향 확인"],
                         ["무작위 경계 N1", "N0 + 권역별 동 수를 비교 대상과 똑같이", "주 기준"],
                         ["무작위 경계 N2", "N1 표본 중 권역별 출발 통행량 비중(두 해 평균)이 비슷한 것만 남김: 정렬 비중의 최대 차 ≤ 0.05, 만족 표본이 200개 미만이면 0.08·0.12로 완화", "보조 분석"],
                         ["IFR", "동에서 출발한 서울 내부 통행(동 내부통행 포함) 중 같은 권역 안에서 끝나는 비율. 구를 넘는 통행은 분모에만 들어감(구 단위 분자합/분모합)", "전체 평가"],
                         ["백분위", "무작위 경계 표본 중 IFR이 더 낮은 비율(같으면 절반). 50% = 무작위 수준", "전체 평가"],
                         ["모듈러리티 Q", "구 안의 통행 네트워크(방향 구분 없음)에서 동의 통행 규모로 기대되는 값을 뺀 권역 내부 통행. 크기 효과를 바로잡음(완전히 없애지는 않음)", "동 진단·재배정"],
                         ["내부통행률 격차 G", "커뮤니티의 IFR − 기존 생활권의 IFR", "불일치 추적"],
                         ["불일치 D", "기존 생활권과 커뮤니티가 권역 안/밖을 다르게 분류한 통행의 비율", "불일치 추적·재배정 검증"]],
                   note=_null_note())
    rows = []
    for r in g[g.boundary == "LZ"].pivot(index="ku_name", columns="year", values=["pct_N0", "pct_N1", "pct_N2"]).sort_values(("pct_N1", int(C.Y1))).itertuples():
        rows.append([r.Index, p0(r[1]), p0(r[2]), p0(r[3]), p0(r[4]), p0(r[5]), p0(r[6])])
    ld = g[g.boundary == "LD"].groupby("year")[["pct_N0", "pct_N1", "pct_N2"]].median(); lzmed = g[g.boundary == "LZ"].groupby("year")[["pct_N0", "pct_N1", "pct_N2"]].median()
    rows.append(["중앙값(기존 생활권)", p0(lzmed.loc[int(C.Y0), "pct_N0"]), p0(lzmed.loc[int(C.Y1), "pct_N0"]), p0(lzmed.loc[int(C.Y0), "pct_N1"]), p0(lzmed.loc[int(C.Y1), "pct_N1"]), p0(lzmed.loc[int(C.Y0), "pct_N2"]), p0(lzmed.loc[int(C.Y1), "pct_N2"])])
    rows.append(["중앙값(커뮤니티)", p0(ld.loc[int(C.Y0), "pct_N0"]), p0(ld.loc[int(C.Y1), "pct_N0"]), p0(ld.loc[int(C.Y0), "pct_N1"]), p0(ld.loc[int(C.Y1), "pct_N1"]), p0(ld.loc[int(C.Y0), "pct_N2"]), p0(ld.loc[int(C.Y1), "pct_N2"])])
    T["TA2"] = dict(ko="A2. 기존 생활권 IFR의 무작위 경계 대비 백분위", en="A2. Percentile of Existing Living-Zone IFR against Random Boundaries",
                   headers=["구", "N0 2020", "N0 2025", "N1 2020", "N1 2025", "N2 2020", "N2 2025"], widths=[3.2] + [2.0] * 6, rows=rows, bold_last=True,
                   note="Each boundary is compared with random boundaries matched to its own zone sizes; 50 means the random level.")
    k = lambda y, n: s[f"{y}_{n}"]
    T["T5"] = dict(ko="5. 경계 동을 한 개씩 옮겨 본 결과", en="5. Results of Moving One Boundary Dong at a Time", headers=["집단", "연도", "동 수", "IFR 개선", "모듈러리티 개선", "둘 다 개선", "IFR만 개선(크기 효과)"], widths=[4.4, 1.3, 1.5, 1.8, 2.0, 1.9, 2.8],
                   rows=[["옆 생활권 지향 동", y, k(y, "옆생활권지향동")["n"], k(y, "옆생활권지향동")["ΔIFR>0"], k(y, "옆생활권지향동")["ΔQ>0"], k(y, "옆생활권지향동")["둘다>0"], k(y, "옆생활권지향동")["ΔIFR>0_ΔQ≤0(크기효과)"]] for y in (C.Y0, C.Y1)] +
                        [["그 밖의 경계 동", y, k(y, "그밖의_경계동")["n"], k(y, "그밖의_경계동")["ΔIFR>0"], k(y, "그밖의_경계동")["ΔQ>0"], k(y, "그밖의_경계동")["둘다>0"], k(y, "그밖의_경계동")["ΔIFR>0_ΔQ≤0(크기효과)"]] for y in (C.Y0, C.Y1)],
                   note=f"Dongs oriented to a neighbouring zone send more trips to it than to their own zone, excluding trips within the dong. Each dong is counted by its single move with the largest modularity gain (the same rule as the reassignment). Counting any move that raises both measures gives {k(C.Y0, '옆생활권지향동')['둘다>0_아무이동']} and {k(C.Y1, '옆생활권지향동')['둘다>0_아무이동']} neighbour-oriented dongs and {k(C.Y0, '그밖의_경계동')['둘다>0_아무이동']} and {k(C.Y1, '그밖의_경계동')['둘다>0_아무이동']} other boundary dongs (2020, 2025). Zone counts and spatial contiguity are kept after each move, so dongs whose move would empty or split their zone are not in these groups (the counts in the text before this exclusion are {nb20} and {nb25}).")
    rows = []
    for y in (C.Y0, C.Y1):
        q = k(y, "탐욕재배정"); rows.append([y, q["옮긴_동"], q["옮긴_구"], f"{q['서울IFR_전']:.1f}", f"{q['서울IFR_후']:.1f}", f"{q['서울IFR_가상경계']:.1f}", f"{q['서울D_전']:.1f}", f"{q['서울D_후']:.1f}", f"{q['Q_전_중앙']:.3f}", f"{q['Q_후_중앙']:.3f}", f"{q['Q_가상경계_중앙']:.3f}"])
    T["T6"] = dict(ko="6. 경계 동 단계적 재배정 결과", en="6. Results of Step-by-Step Boundary-Dong Reassignment", headers=["연도", "옮긴 동", "해당 구", "IFR 전(%)", "IFR 후(%)", "IFR 커뮤니티(%)", "D 전(%)", "D 후(%)", "Q 전", "Q 후", "Q 커뮤니티"],
                   widths=[1.2, 1.4, 1.4, 1.5, 1.5, 1.9, 1.3, 1.3, 1.3, 1.3, 1.7], rows=rows,
                   note=f"Moves were applied one at a time in order of modularity gain until no move raised modularity. Moved dongs are those whose final zone changed ({k(C.Y0, '탐욕재배정')['이동_횟수']} and {k(C.Y1, '탐욕재배정')['이동_횟수']} moves). IFR and D are Seoul totals (sum of numerators over sum of denominators); Q is the district median. Dongs with the same original-to-new zone pair in both years: {s['두해모두_권고_이동']} ({s['2020만']} in 2020 only, {s['2025만']} in 2025 only). Applying the 2020 reassigned boundaries to 2025 travel improved Q in {S9['고정경계_부호검정']['Q개선']} and reduced D in {S9['고정경계_부호검정']['D감소']} of {S9['고정경계_부호검정']['n']} districts.")
    f1 = lambda x: f"{x * 100:.1f}"; f2 = lambda x: f"{x * 100:.2f}"
    rows = [[r.유형, f1(r.비중2020), f1(r.비중2025), f1(r.IFR2020), f1(r.IFR2025), f1(r.ΔIFR), f1(r.유형내기여), f1(r.구성기여)] for r in t9.itertuples()]
    W = S9["평일주말"]; U = S9["유형분해"]
    rows += [["평일 통행", "—", "—", f1(W["IFR2020_평일"]), f1(W["IFR2025_평일"]), f1(W["ΔIFR_평일"]), "—", "—"],
             ["주말 통행", "—", "—", f1(W["IFR2020_주말"]), f1(W["IFR2025_주말"]), f1(W["ΔIFR_주말"]), "—", "—"],
             ["전체", "100.0", "100.0", f1(U["IFR2020"]), f1(U["IFR2025"]), f1(U["ΔIFR"]), f1(U["유형내효과"]), f1(U["구성효과"])]]
    T["T3"] = dict(ko="3. 기존 생활권 IFR 변화의 이동 유형별 분해", en="3. Decomposition of the Change in Existing Living-Zone IFR by Trip Type",
                   headers=["이동 유형", "비중 2020(%)", "비중 2025(%)", "IFR 2020(%)", "IFR 2025(%)", "ΔIFR(%p)", "유형 내 기여(%p)", "구성 기여(%p)"],
                   widths=[2.6, 1.8, 1.8, 1.8, 1.8, 1.8, 2.2, 2.0], rows=rows, bold_last=True,
                   note=(f"Seoul totals (sum of numerators over sum of denominators). Within-type contribution = mean share of the two years × change in IFR by type; composition contribution = change in share × mean IFR of the two years (symmetric decomposition). "
                         f"The within-type effect is {U['유형내_비중'] * 100:.0f}% of the change in IFR. Districts where the weekend rise exceeded the weekday rise: {W['구수_주말>평일']}/{W['n']} (sign test p {'< 0.001' if W['p_양측'] < 0.001 else '= ' + format(W['p_양측'], '.3f')}). Home-to-work and work-to-home trips (HW·WH) are excluded. Weekend = Saturday and Sunday; public holidays cannot be identified in the data and are counted as weekdays."))

    Dv, Gv = S9["D변화"], S9["G확대"]; Sd = json.loads((C.TAB / "results.json").read_text(encoding="utf-8"))["seoul"]
    T["T4"] = dict(ko="4. 기존 생활권과 커뮤니티의 불일치 변화", en="4. Change in Mismatch between Existing Living Zones and Mobility Communities",
                   headers=["지표", "서울 2020", "서울 2025", "변화", "구: 증가 / 감소 / 같음", "부호검정 p"], widths=[4.6, 1.9, 1.9, 1.8, 3.2, 2.0],
                   rows=[["불일치 D(%)", f1(Sd["2020"]["D"]), f1(Sd["2025"]["D"]), f"{(Sd['2025']['D'] - Sd['2020']['D']) * 100:+.1f}", f"{Dv['증가']} / {Dv['감소']} / {Dv['변화없음']}", f"{Dv['p_부호_양측']:.2f}"],
                         ["내부통행률 격차 G(%p)", f2(Gv["G2020"]), f2(Gv["G2025"]), f"{Gv['ΔG'] * 100:+.2f}", f"{Gv['구_증가']} / {Gv['구_감소']} / {Gv['구_변화없음']}", f"{Gv['p_부호_양측']:.3f}"],
                         ["  G 변화 중 통행이 바뀐 부분(%p)", "—", "—", f"{Gv['통행_평균'] * 100:+.2f}", f"{Gv['구_통행몫양수']} / {Gv['구_통행몫음수']} / {25 - Gv['구_통행몫양수'] - Gv['구_통행몫음수']}", f"{Gv['p_통행몫_양측']:.3f}"],
                         ["  G 변화 중 커뮤니티를 새로 만든 부분(%p)", "—", "—", f"{Gv['재도출_평균'] * 100:+.2f}", "—", "—"]],
                   note=(f"Seoul values are sums of numerators over sums of denominators. 'Same' = districts where the two boundaries are identical in both years (no change in D or G). The two-sided sign test excludes 'same'. "
                         f"The decomposition of the change in G averages the two orders (travel first, boundary first); the travel part is {Gv['통행몫_순서1'] * 100:.0f}~{Gv['통행몫_순서2'] * 100:.0f}% depending on the order (mean {Gv['통행몫_평균'] * 100:.0f}%)."))

    from k14_reassign import final_changes
    lzm = _lz(); common = sorted(final_changes(gm, lzm, int(C.Y0)) & final_changes(gm, lzm, int(C.Y1)), key=lambda t: (lzm.ku_name[t[0]], lzm.ADM_NM[t[0]]))
    T["TA1"] = dict(ko="A1. 두 해 모두 권고된 경계 동 재배정", en="A1. Reassignments Recommended in Both Years", headers=["구", "동", "현재 생활권", "옮겨 갈 생활권"], widths=[2.4, 3.4, 5.0, 5.0],
                    rows=[[lzm.ku_name[d], lzm.ADM_NM[d], a.split("_", 1)[1], z.split("_", 1)[1]] for d, a, z in common],
                    note="Dongs whose final zone changed in the step-by-step reassignment of both years with the same original-to-new zone pair in 2020 and 2025. A travel-only review priority; school districts, administrative jurisdiction and local identity are not considered.")
    return T


FIGS_V2 = {
    "F1": ("1. 분석의 틀", "1. Analytical Framework", "Fv2_1_framework.png", 15.0, "Random boundaries serve as the minimum reference and data-based communities, built from the same data, as the comparison reference."),
    "F2": ("2. 크기 효과: 기존 생활권 IFR의 무작위 경계 대비 백분위(2025)", "2. Size Effect: Percentile of Existing Living-Zone IFR against Random Boundaries, 2025", "Fv2_2_size_bias.png", 12.0, "Hollow dots: random boundaries without a size constraint (N0); filled dots: random boundaries with the same number of dongs per zone (N1); dashed line: random level (50)."),
    "F3": ("3. 동 진단 결과(2025)", "3. Dong-Level Diagnosis, 2025", "Fv2_3_dong_diagnosis_map.png", 14.0, "Thin lines: existing living zones; thick lines: district boundaries. Numbers in parentheses are dong counts."),
    "F4": ("4. 구별 경계 동 재배정 전후 IFR(2025)", "4. District IFR before and after Boundary-Dong Reassignment, 2025", "Fv2_4_gu_reassign_ifr.png", 12.0, "Vertical bars show the IFR of the data-based communities."),
    "F5": ("5. 사례: 광진구의 기존 생활권·재배정 후·커뮤니티(2025)", "5. Case: Gwangjin-gu, 2025", "Fv2_5_case_gwangjin.png", 15.5, "Red dashed outlines mark the moved dongs."),
    "FA1": ("A1. 두 경계의 IFR 변화와 무작위 경계의 IFR 변화 분포", "A1. Change in IFR of the Two Boundaries against Random Boundaries", "Fv2_A1_null_dIFR.png", 13.0, "Grey boxes show the 5~95% range of 1,000 random boundaries."),
}


def draw_all():
    fig_framework(); fig_size_bias(); fig_dong_map(); fig_gu_bars(); fig_case(); fig_null_dIFR()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(verify(), ensure_ascii=False, indent=1)); draw_all(); t = build_tables_v2(); print("표", list(t), "| 그림 생성 완료")
