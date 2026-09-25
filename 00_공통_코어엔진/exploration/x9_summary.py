# -*- coding: utf-8 -*-
"""
x9_summary.py — x1~x8 결과를 한 표·한 문서로 모으기
====================================================
각 탐색 스크립트가 output/exploration/x*/ 에 남긴 csv 를 읽어,
  1) 구·연도별로 "방법마다 데이터가 고른 개수"를 한 표에 모으고 (k_methods.csv)
  2) 방법별 합계·공식과 같은 구 수를 요약하고 (k_totals.csv)
  3) 공식 경계 vs Leiden 정본의 품질 지표(크기 보정 IFR z, Q 등)를 모아
  4) output/exploration/탐색결과_요약.md 로 쓴다. exploration/해석_메모.md 가 있으면 뒤에 붙인다.
없는 결과(아직 안 돌린 스크립트)는 건너뛰고 표에 빈칸으로 둔다.

실행: python x9_summary.py
"""
from xcommon import *

X = OUT


def rd(sub, name):
    p = X / sub / name
    return pd.read_csv(p) if p.exists() else None


def main():
    base = pd.DataFrame([{"year": y, "구": C.KU_NAME[k], "공식k": C.TARGET_COMMUNITIES[k]} for y in YEARS for k in KU_ORDER])
    base["year"] = base["year"].astype(int)
    cols, notes = {}, []

    def add(df, src, dst, label, how="direct"):
        nonlocal base
        if df is None:
            notes.append(f"- {label}: 결과 없음 (스크립트 미실행)")
            return
        df = df.copy(); df["year"] = df["year"].astype(int)
        base = base.merge(df[["year", "구", src]].rename(columns={src: dst}), on=["year", "구"], how="left")
        cols[dst] = label

    f1 = [rd("x1", f"frontier_{y}.csv") for y in YEARS]
    f1 = pd.concat([f for f in f1 if f is not None]) if any(f is not None for f in f1) else None
    if f1 is not None:
        f1["등가k_반올림"] = f1["등가k"].round()
    add(f1, "등가k", "A1_등가k", "A1 프런티어 등가 개수 (공식 IFR 을 Leiden 으로 얻는 최대 개수)")
    add(f1, "무릎k_IFR", "C3_무릎k", "C3 IFR 곡선 무릎점")
    x3 = rd("x3", "q_band_plateau.csv")
    add(x3, "k_Q최대", "B1_Q최대k", "B1 Q 최대 개수 (정본 스캔)")
    add(x3, "범위_ε0.01", "B1_범위ε0.01", "B1 Q 최대에서 0.01 이내 개수 범위")
    add(x3, "평탄k_제한", "B4_평탄k", "B4 해상도 평탄 구간 (공식의 ½~2배 제한; 참고용)")
    add(rd("x4", "null_q_kstar.csv"), "k_z최대", "B3_z최대k", "B3 귀무모형 대비 z 최대 개수")
    add(rd("x5", "sbm_kstar_pp_s310.csv"), "k_SBM", "B2_SBM동류k", "B2 동류 SBM(PPBlockState, 하루 통행/10 단위) MDL 개수")
    add(rd("x5", "sbm_kstar_exp.csv"), "k_SBM", "B2_SBM일반k", "B2 일반 SBM(가중치 지수 공변량) MDL 개수")
    x6 = rd("x6", "ttwa_sweep.csv")
    if x6 is not None:
        x6 = x6[x6["인구하한"] == 0]
        tt = x6.groupby(["year", "SC문턱"])["k"].sum().reset_index()
        pick = tt.loc[tt.groupby("year").apply(lambda t: (t["k"] - C.N_LZ).abs().idxmin(), include_groups=False)]
        thr = dict(zip(pick["year"].astype(str), pick["SC문턱"]))
        x6a = pd.concat([x6[(x6.year == int(y)) & (x6.SC문턱 == t)] for y, t in thr.items()])
        x6b = x6[x6["SC문턱"] == 0.25]
        add(x6a, "k", "C1_TTWA_k(합116)", "C1 TTWA: 합계가 116 에 가장 가까운 자족성 문턱에서의 개수 (" +
            ", ".join(f"{y}: SC*={t}" for y, t in thr.items()) + ")")
        add(x6b, "k", "C1_TTWA_k(SC0.25)", "C1 TTWA: 두 해 같은 문턱 SC*=0.25 에서의 개수")
    else:
        add(None, "", "", "C1 TTWA")
    x7 = rd("x7", "maxp_sweep.csv")
    if x7 is not None:
        tt = x7.groupby(["year", "인구하한"])["k"].sum().reset_index()
        pick = tt.loc[tt.groupby("year").apply(lambda t: (t["k"] - C.N_LZ).abs().idxmin(), include_groups=False)]
        fl = dict(zip(pick["year"].astype(str), pick["인구하한"]))
        x7a = pd.concat([x7[(x7.year == int(y)) & (x7.인구하한 == f)] for y, f in fl.items()])
        add(x7a, "k", "C2_maxp_k", "C2 max-p: 합계가 116 에 가장 가까운 인구 하한에서의 개수 (" +
            ", ".join(f"{y}: {int(f):,}명" for y, f in fl.items()) + ")")
    else:
        add(None, "", "", "C2 max-p")

    # 이동 자료로 개수를 직접 고르는 방법들만 모아 중앙값·방향 투표 (C2 는 인구 규칙, C3·B4·일반 SBM 은 불안정 → 제외)
    direct = [c for c in ["A1_등가k", "B1_Q최대k", "B3_z최대k", "B2_SBM동류k", "C1_TTWA_k(합116)"] if c in base]
    if direct:
        V = np.round(base[direct].astype(float))
        base["제안k_중앙값"] = V.apply(lambda r: np.nanmedian(r), axis=1)
        base["중앙값−공식"] = base["제안k_중앙값"] - base["공식k"]
        base["많다_방법수"] = (V.gt(base["공식k"], axis=0)).sum(axis=1)
        base["적다_방법수"] = (V.lt(base["공식k"], axis=0)).sum(axis=1)
        base["투표방법수"] = V.notna().sum(axis=1)
    save(base, "k_methods", "")

    num = [c for c in base.columns if c not in ("year", "구", "B1_범위ε0.01") and pd.api.types.is_numeric_dtype(base[c])]
    tot = []
    for y, x in base.groupby("year"):
        r = {"year": y}
        for c in num:
            if c in ("많다_방법수", "적다_방법수", "투표방법수"):
                continue
            r[c] = round(float(x[c].sum()), 1) if x[c].notna().all() else np.nan
        tot.append(r)
    tot = pd.DataFrame(tot)
    same = []
    for y, x in base.groupby("year"):
        r = {"year": y}
        for c in num:
            if c in ("공식k", "중앙값−공식", "많다_방법수", "적다_방법수", "투표방법수"):
                continue
            r[c] = int((np.round(x[c]) == x["공식k"]).sum()) if x[c].notna().all() else np.nan
        same.append(r)
    same = pd.DataFrame(same)
    save(tot, "k_totals", "")

    L = ["# 생활권 개수(k) 탐색 결과 요약", "",
         "정본(구별 공식 개수 고정, 3,000회 합의)은 그대로 두고, \"데이터가 스스로 고르면 몇 개인가\"를 여러 방법으로 본 결과.",
         "각 방법의 상세는 output/exploration/x*/x*_report.md.", "",
         "## 방법 목록", ""] + [f"- `{k}`: {v}" for k, v in cols.items()] + notes + ["",
         "## 합계 (25개 구, 공식 116)", "", md_table(tot, "{:.1f}"), "",
         "## 공식 개수와 같은 구의 수 (/25)", "", md_table(same, "{:.0f}"), ""]

    x2 = rd("x2", "excess_ifr.csv")
    if x2 is not None:
        L += ["## 같은 개수의 무작위 경계 대비 자족성 (x2, 인구 균형 귀무)", "",
              "| 연도 | 경계 | 평균 IFR | 평균 z | pct≥0.95 구 | 평균 SCI | 조각 인구 CV |", "|---|---|---|---|---|---|---|"]
        for (y, b), x in x2.groupby(["year", "경계"]):
            L.append(f"| {y} | {b} | {x.IFR.mean():.3f} | {x.z_pop.mean():+.2f} | {int((x.pct_pop >= 0.95).sum())}/25 | "
                     f"{x.SCI_pop.mean():.3f} | {x.pop_cv.mean():.2f} |")
        L.append("")
    x8 = rd("x8", "citywide_scan.csv"); x8r = rd("x8", "citywide_reference.csv")
    if x8 is not None:
        L += ["## 구 경계를 푼 서울 전체 Leiden (x8)", "", "| 연도 | 선택 | γ | k | Q | 서울 IFR | 구에 걸친 커뮤니티 | 그 동 비율 | ARI 공식 | ARI 정본 | ARI 자치구 |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for y, x in x8.groupby("year"):
            x = x.reset_index(drop=True)
            for tag, i in (("Q최대", x.Q.idxmax()), ("k≈116", (x.k - C.N_LZ).abs().idxmin()), ("k≈25", (x.k - 25).abs().idxmin())):
                r = x.loc[i]
                L.append(f"| {y} | {tag} | {r.resolution:.2f} | {int(r.k)} | {r.Q:.3f} | {r['IFR_서울']:.3f} | {int(r['구걸침_커뮤니티'])} | "
                         f"{r['구걸침_동비율']:.0%} | {r.ARI_vs_공식:.3f} | {r.ARI_vs_Leiden:.3f} | {r.ARI_vs_자치구:.3f} |")
            for _, r in x8r[x8r.year == y].iterrows():
                L.append(f"| {y} | {r['경계']} | | {int(r.k)} | {r.Q:.3f} | {r['IFR_서울']:.3f} | {int(r['구걸침_커뮤니티'])} | "
                         f"{r['구걸침_동비율']:.0%} | {r.ARI_vs_공식:.3f} | {r.ARI_vs_Leiden:.3f} | {r.ARI_vs_자치구:.3f} |")
        L.append("")

    if direct:
        L += ["## 방향이 일관된 구 (이동 기반 방법 " + ", ".join(direct) + " 의 과반이 같은 방향)", ""]
        for y in YEARS:
            x = base[base.year == int(y)]
            half = x["투표방법수"] / 2
            up = x[x["많다_방법수"] > half]; dn = x[x["적다_방법수"] > half]
            L.append(f"- {y} 공식보다 많게: " + (", ".join(f"{r.구}({r.공식k}→{r.제안k_중앙값:.0f})" for r in up.itertuples()) or "없음"))
            L.append(f"- {y} 공식보다 적게: " + (", ".join(f"{r.구}({r.공식k}→{r.제안k_중앙값:.0f})" for r in dn.itertuples()) or "없음"))
        L.append("")
    show = ["구", "공식k"] + [c for c in cols if c in base and c != "B4_평탄k"] + [c for c in ("제안k_중앙값", "중앙값−공식", "많다_방법수", "적다_방법수") if c in base]
    for y in YEARS:
        L += [f"## 구별 개수 비교 — {y}", "", md_table(base[base.year == int(y)][show], "{:.1f}"), ""]
    memo = EXP_DIR / "해석_메모.md"
    if memo.exists():
        L += ["---", "", memo.read_text(encoding="utf-8")]
    (OUT / "탐색결과_요약.md").write_text("\n".join(L), encoding="utf-8")
    print("wrote", OUT / "탐색결과_요약.md")
    print(md_table(tot, "{:.1f}"))


if __name__ == "__main__":
    main()
