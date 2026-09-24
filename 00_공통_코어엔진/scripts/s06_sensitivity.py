# -*- coding: utf-8 -*-
"""
s06_sensitivity.py — 정본 경계의 민감도 점검 (정본을 바꾸지 않는다)
=====================================================================
두 가지를 한다. 결과는 output/sensitivity/ 에만 쓴다.

A. 설정 민감도 (--compare)
   s03 을 다른 설정·같은 시드로 돌린 결과(--tag 폴더)를 정본(output/leiden/{year}/)과 구별로 비교한다.
     python s03_leiden_consensus.py --years 2020 2025 --workers 8 --tau 0.4 --seed canonical --tag _tau0.4
     python s03_leiden_consensus.py --years 2020 2025 --workers 8 --tau 0.6 --seed canonical --tag _tau0.6
     python s03_leiden_consensus.py --years 2020 2025 --workers 8 --primary ifr --seed canonical --tag _ifr
     python s06_sensitivity.py --compare _tau0.4 _tau0.6 _ifr
   --seed canonical 이면 해상도마다 Leiden 3,000회 원시 결과가 정본과 완전히 같다. 그래서 차이는 오직 τ(합의 임계값)
   또는 선정 규칙에서만 나온다.

B. 구별 커뮤니티 개수 진단 (--k-diagnostic, 재실행 불필요)
   정본 실행의 해상도 스캔 로그(250개 해상도 × 25구)만으로, "공식 생활권 수(목표 개수)가 이동 데이터 기준으로도 적절한가"를 본다.
     - k_Qmax      : 표준 Modularity Q 가 가장 높은 커뮤니티 수
     - ΔQ          : Q(k_Qmax) − Q(목표 k). 작으면 목표 개수로 묶어도 이동 구조 설명력 손실이 작다
     - k_near      : Q 가 최댓값에서 0.01 이내인 개수들 (데이터가 개수를 강하게 정해주지 않는 범위)
     - IFR(k)      : 개수별 최대 IFR. 개수가 적을수록 IFR 이 기계적으로 커지는지 확인 (개수를 고정해야 비교가 공정한 이유)

실행:  python s06_sensitivity.py --compare _tau0.4 _tau0.6 _ifr
       python s06_sensitivity.py --k-diagnostic
"""
import sys, json, argparse, datetime, glob
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C
from s03_leiden_consensus import ari

OUT = C.OUTPUT_DIR / "sensitivity"


def md_table(df: pd.DataFrame) -> str:
    """tabulate 없이 마크다운 표"""
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join("" if pd.isna(v) else (f"{v:.4f}" if isinstance(v, float) else str(v)) for v in r) + " |")
    return "\n".join(out)


def load_run(year: str, tag: str = ""):
    d = C.LEIDEN_OUT / (year + tag)
    m = pd.read_csv(d / "metrics" / f"leiden_mapping_{year}.csv").sort_values("Dong").reset_index(drop=True)
    met = pd.read_csv(d / "metrics" / f"leiden_metrics_{year}.csv").set_index("ku_code")
    info = json.loads((d / "run_info.json").read_text(encoding="utf-8"))
    return m, met, info


def moved_dongs(a: np.ndarray, b: np.ndarray, names: list) -> list:
    """두 분할에서 '같은 묶음인 동' 관계가 하나라도 바뀐 동 (라벨 번호와 무관)"""
    sa, sb = a[:, None] == a[None, :], b[:, None] == b[None, :]
    return [names[i] for i in np.where((sa != sb).any(axis=1))[0]]


def compare(tags):
    lines = [f"# 설정 민감도 비교 ({datetime.datetime.now():%Y-%m-%d %H:%M})", "",
             "정본(τ=0.5, Q 최대 선정)과 같은 시드로 설정 하나만 바꿔 다시 돌린 결과를 구별로 비교한다. "
             "ARI=1 이면 동 묶음이 정본과 완전히 같다.", ""]
    summary = []
    for tag in tags:
        for year in C.YEARS:
            try:
                m0, met0, info0 = load_run(year)
                m1, met1, info1 = load_run(year, tag)
            except FileNotFoundError as e:
                lines.append(f"- {tag} {year}: 결과 없음 ({e.filename})"); continue
            p0, p1 = info0["params"], info1["params"]
            same_seed = p0.get("base_seed") == p1.get("base_seed")
            rows = []
            for ku in sorted(C.TARGET_COMMUNITIES):
                s0, s1 = m0[m0["Ku"] == ku], m1[m1["Ku"] == ku]
                a, b = s0["community"].values, s1.set_index("Dong").loc[s0["Dong"], "community"].values
                mv = moved_dongs(a, b, s0["ADM_NM"].tolist())
                r0, r1 = met0.loc[ku], met1.loc[ku]
                rows.append({"구": C.KU_NAME[ku], "γ_정본": r0["resolution"], "γ_변경": r1["resolution"],
                             "k_정본": int(r0["n_communities"]), "k_변경": int(r1["n_communities"]),
                             "Q_정본": r0["modularity"], "Q_변경": r1["modularity"], "IFR_정본": r0["ifr"], "IFR_변경": r1["ifr"],
                             "ARI": round(ari(a, b), 4), "바뀐동수": len(mv), "바뀐동": ", ".join(mv)})
            df = pd.DataFrame(rows)
            OUT.mkdir(parents=True, exist_ok=True)
            df.to_csv(OUT / f"compare{tag}_{year}.csv", index=False, encoding="utf-8-sig")
            city = ari(m0.set_index("Dong")["global_community_id"].values,
                       m1.set_index("Dong").loc[m0["Dong"], "global_community_id"].values)
            n_same = int((df["ARI"] == 1).sum())
            summary.append({"tag": tag, "year": year, "same_seed": same_seed, "tau": p1["tau"], "primary": p1["primary"],
                            "구_동일": n_same, "구_다름": 25 - n_same, "서울ARI": round(city, 4),
                            "바뀐동_합": int(df["바뀐동수"].sum())})
            lines += [f"## {tag} · {year}  (τ={p1['tau']}, 선정={p1['primary']}, 시드 정본과 {'같음' if same_seed else '다름'})", "",
                      f"- 정본과 동일한 구 {n_same}/25, 서울 전체 ARI {city:.4f}", ""]
            diff = df[df["ARI"] < 1]
            if len(diff):
                lines += ["| 구 | γ 정본→변경 | k | Q 정본→변경 | IFR 정본→변경 | ARI | 바뀐 동 |", "|---|---|---|---|---|---|---|"]
                for r in diff.itertuples():
                    lines.append(f"| {r.구} | {r.γ_정본:.3f}→{r.γ_변경:.3f} | {r.k_정본}→{r.k_변경} | {r.Q_정본:.4f}→{r.Q_변경:.4f} | "
                                 f"{r.IFR_정본:.4f}→{r.IFR_변경:.4f} | {r.ARI:.3f} | {r.바뀐동} |")
                lines.append("")
    if summary:
        s = pd.DataFrame(summary)
        s.to_csv(OUT / "compare_summary.csv", index=False, encoding="utf-8-sig")
        lines = lines[:4] + ["## 요약", "", md_table(s), ""] + lines[4:]
    path = OUT / f"sensitivity_compare_{datetime.datetime.now():%Y%m%d_%H%M%S}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines)); print(f"\n→ {path}")


def k_diagnostic():
    rows, curves = [], []
    for year in C.YEARS:
        for ku in sorted(C.TARGET_COMMUNITIES):
            f = glob.glob(str(C.LEIDEN_OUT / year / "resolution_scan_logs" / f"{ku}_*_{year}.csv"))
            if not f:
                continue
            s = pd.read_csv(f[0])
            s = s[s["n_communities"] >= 2]
            g = s.groupby("n_communities").agg(Q=("modularity", "max"), IFR=("ifr", "max"), n_res=("resolution", "size"))
            tgt = C.TARGET_COMMUNITIES[ku]
            kq = int(g["Q"].idxmax())
            near = [int(k) for k in g.index if g.loc[k, "Q"] >= g["Q"].max() - 0.01]
            rows.append({"year": year, "구": C.KU_NAME[ku], "목표k": tgt, "k_Qmax": kq,
                         "Q_목표": round(g["Q"].get(tgt, np.nan), 4), "Q_최대": round(g["Q"].max(), 4),
                         "ΔQ": round(g["Q"].max() - g["Q"].get(tgt, np.nan), 4),
                         "Q최대0.01이내_k": ",".join(map(str, near)), "목표k_포함": tgt in near,
                         "목표k_해상도수": int(g["n_res"].get(tgt, 0))})
            for k, r in g.iterrows():
                curves.append({"year": year, "구": C.KU_NAME[ku], "k": int(k), "k/목표": k / tgt, "Q": r["Q"], "IFR": r["IFR"]})
    d, cv = pd.DataFrame(rows), pd.DataFrame(curves)
    OUT.mkdir(parents=True, exist_ok=True)
    d.to_csv(OUT / "k_diagnostic.csv", index=False, encoding="utf-8-sig")
    cv.to_csv(OUT / "k_curves_Q_IFR.csv", index=False, encoding="utf-8-sig")
    # 개수가 늘면 IFR 이 줄어드는가 (구 안에서의 순위상관, 구별 평균)
    sub = cv[cv["k"] <= 12]
    rho = pd.Series({y: np.nanmean([g["k"].corr(g["IFR"], method="spearman") for _, g in sub[sub.year == y].groupby("구")])
                     for y in sub["year"].unique()})
    lines = [f"# 구별 커뮤니티 개수 진단 ({datetime.datetime.now():%Y-%m-%d %H:%M})", "",
             "정본 실행의 해상도 스캔 로그(구별 250개 해상도)에서 개수별 최대 Q·IFR 을 모았다. 재실행 없음.", ""]
    for year in C.YEARS:
        x = d[d.year == year]
        lines += [f"## {year}", "",
                  f"- 목표(공식 생활권) 합계 {x['목표k'].sum()} / Q 최대 개수 합계 {x['k_Qmax'].sum()}",
                  f"- 목표 k 가 Q 최대 개수와 같은 구 {int((x['목표k'] == x['k_Qmax']).sum())}/25, "
                  f"Q 최대에서 0.01 이내에 목표 k 가 드는 구 {int(x['목표k_포함'].sum())}/25",
                  f"- ΔQ 중앙값 {x['ΔQ'].median():.4f}, 최대 {x['ΔQ'].max():.4f} ({x.loc[x['ΔQ'].idxmax(), '구']})",
                  f"- 개수 k 와 IFR 의 순위상관(구별 평균, k≤12): {rho.get(year, np.nan):.3f}  (음수면 개수가 적을수록 IFR 이 큼)", "",
                  md_table(x.drop(columns="year")), ""]
    path = OUT / "k_diagnostic.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines)); print(f"\n→ {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", nargs="*", default=None, help="비교할 s03 --tag 값들 (예: _tau0.4 _tau0.6 _ifr)")
    ap.add_argument("--k-diagnostic", action="store_true")
    a = ap.parse_args()
    if a.compare:
        compare(a.compare)
    if a.k_diagnostic:
        k_diagnostic()
    if not a.compare and not a.k_diagnostic:
        ap.print_help()


if __name__ == "__main__":
    main()
