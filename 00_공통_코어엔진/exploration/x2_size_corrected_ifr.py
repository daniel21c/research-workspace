# -*- coding: utf-8 -*-
"""
x2_size_corrected_ifr.py — A2 크기 보정 IFR (초과 자족성)
===========================================================
IFR 은 커뮤니티를 크게(개수를 적게) 할수록 커진다. "잘 그어서" 높은지를 보려면 같은 개수로 무작위로 그은
경계와 비교해야 한다. 구마다, 개수 k(2~10)마다 공간적으로 연결된 무작위 분할을 N 개(기본 500) 만든다.

무작위 분할(귀무) 세 종류
  - free   : 무작위 씨앗 k개에서 무작위로 인접 동을 붙여 나감. 한 조각이 거대해지기 쉬워 IFR 이 부풀려진다(참고용).
  - dong   : 매 단계 동 수가 가장 적은 조각이 인접 동을 가져감 → 동 수가 고른 분할.
  - pop    : 매 단계 인구가 가장 적은 조각이 가져감 → 인구가 고른 분할. **주 비교 기준** (생활권은 인구 균형을 전제로 한 계획단위).
각 귀무 분포에 대해 공식 생활권과 Leiden 정본의
  excess = IFR − 귀무 평균,  z = excess / 귀무 sd,  pct = 귀무 분할 중 IFR 이 이보다 낮은 비율,
  SCI = (IFR − 귀무 평균) / (1 − 귀무 평균)   (정규화 초과자족성, 개수가 달라도 비교 가능)
을 계산한다. 조각 인구의 변동계수(CV)도 함께 적어, 크기 균형이 IFR 에 미치는 영향을 볼 수 있게 한다.

출력: output/exploration/x2/excess_ifr.csv, random_curve.csv, x2_report.md
실행: python x2_size_corrected_ifr.py [--n 500] [--seed 20260924]
"""
import argparse
from xcommon import *

NULLS = ("free", "dong", "pop")


def cv_pop(lab, pop):
    s = np.bincount(lab, weights=pop)
    return float(s.std() / s.mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20260924)
    a = ap.parse_args()
    lz = load_lz()
    rows, curve = [], []
    for year in YEARS:
        G = all_ku_graphs(year, with_pop=True)
        m, _ = load_leiden(year)
        for ku in KU_ORDER:
            g = G[ku]
            rng = np.random.default_rng(a.seed + ku + int(year))
            dist, cvs = {}, {}
            for k in range(2, min(10, g.n - 1) + 1):
                for nul in NULLS:
                    vals, cv = [], []
                    for _ in range(a.n):
                        if nul == "free":
                            lab = random_connected_partition(g.adj, k, rng)
                        else:
                            lab = random_balanced_partition(g.adj, k, rng, None if nul == "dong" else g.pop)
                        if lab is not None:
                            vals.append(g.ifr(lab)); cv.append(cv_pop(lab, g.pop))
                    vals = np.asarray(vals)
                    dist[(k, nul)], cvs[(k, nul)] = vals, float(np.mean(cv))
                    curve.append({"year": year, "구": C.KU_NAME[ku], "k": k, "null": nul, "rand_mean": vals.mean(),
                                  "rand_sd": vals.std(), "rand_pop_cv": cvs[(k, nul)], "n": len(vals)})
            for name, series in (("공식", lz["life_zone_id"]), ("Leiden", m["global_community_id"])):
                lab = g.labels_from_mapping(series)
                k = int(lab.max()) + 1
                v = g.ifr(lab)
                row = {"year": year, "구": C.KU_NAME[ku], "경계": name, "k": k, "IFR": v, "pop_cv": cv_pop(lab, g.pop)}
                for nul in NULLS:
                    r = dist[(k, nul)]
                    row.update({f"mean_{nul}": r.mean(), f"excess_{nul}": v - r.mean(), f"z_{nul}": (v - r.mean()) / r.std(),
                                f"pct_{nul}": float((r < v).mean()), f"SCI_{nul}": (v - r.mean()) / (1 - r.mean()),
                                f"popcv_{nul}": cvs[(k, nul)]})
                rows.append(row)
    d = pd.DataFrame(rows)
    save(d, "excess_ifr", "x2"); save(pd.DataFrame(curve), "random_curve", "x2")
    L = ["# x2 — A2 크기 보정 IFR (초과 자족성)", "",
         f"구·개수마다 공간 연결 무작위 분할 {a.n}개(귀무 3종)와 비교. 주 기준은 인구 균형 귀무(pop).", "",
         "| 귀무 | 설명 |", "|---|---|", "| free | 무작위 성장. 거대 조각이 생겨 IFR 이 부풀려짐 (참고) |",
         "| dong | 동 수 균형 |", "| pop | 인구 균형 (주 기준) |", ""]
    for y in YEARS:
        x = d[d.year == y]; off, ld = x[x.경계 == "공식"].set_index("구"), x[x.경계 == "Leiden"].set_index("구")
        L += [f"## {y}", ""]
        for nul in NULLS:
            L.append(f"- [{nul}] 공식: pct≥0.95 {int((off[f'pct_{nul}'] >= 0.95).sum())}/25, 평균 z {off[f'z_{nul}'].mean():+.2f}, "
                     f"평균 excess {off[f'excess_{nul}'].mean():+.4f} | Leiden: pct≥0.95 {int((ld[f'pct_{nul}'] >= 0.95).sum())}/25, "
                     f"평균 z {ld[f'z_{nul}'].mean():+.2f}, 평균 excess {ld[f'excess_{nul}'].mean():+.4f} | "
                     f"Leiden>공식 {int((ld[f'excess_{nul}'] > off[f'excess_{nul}']).sum())}/25")
        L.append(f"- 조각 인구 CV 평균: 공식 {off.pop_cv.mean():.2f}, Leiden {ld.pop_cv.mean():.2f}, "
                 f"무작위 free {off.popcv_free.mean():.2f} / dong {off.popcv_dong.mean():.2f} / pop {off.popcv_pop.mean():.2f}")
        L += ["", md_table(pd.DataFrame({"구": off.index, "k": off.k.values, "IFR_공식": off.IFR.values, "IFR_Leiden": ld.IFR.values,
                                          "귀무평균(pop)": off.mean_pop.values, "z_공식": off.z_pop.values, "z_Leiden": ld.z_pop.values,
                                          "SCI_공식": off.SCI_pop.values, "SCI_Leiden": ld.SCI_pop.values,
                                          "popCV_공식": off.pop_cv.values, "popCV_Leiden": ld.pop_cv.values})), ""]
    (out_dir("x2") / "x2_report.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join([l for l in L if l.startswith("- ") or l.startswith("## ")]))


if __name__ == "__main__":
    main()
