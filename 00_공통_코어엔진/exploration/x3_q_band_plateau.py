# -*- coding: utf-8 -*-
"""
x3_q_band_plateau.py — B1 ΔQ 허용 범위, B4 다해상도 평탄 구간
==============================================================
입력: 정본 해상도 스캔 로그만 (재실행 없음).

B1. 커뮤니티 수 k 별 최대 Q. Q 최댓값에서 ε 이내인 k 들을 "데이터가 받아들이는 개수 범위"로 본다. ε = 0.005 / 0.01 / 0.02.
    공식 개수가 그 범위에 드는지, ΔQ = Q_max − Q(공식 k).
B4. 해상도 γ 격자(0.01 간격 250개)에서 같은 k 가 연속으로 유지되는 가장 긴 구간(평탄 구간)의 k.
    전체(k≥2)와, 공식 개수의 절반~두 배 범위로 제한한 경우 둘 다 보고한다.
    참고: 구 그래프가 작아(동 10~30개) 높은 γ 에서 잘게 쪼갠 상태가 오래 유지되는 경향이 있다.

출력: output/exploration/x3/q_band_plateau.csv, x3_report.md
실행: python x3_q_band_plateau.py
"""
from xcommon import *

EPS = (0.005, 0.01, 0.02)


def longest_run(ks):
    """연속 격자에서 같은 값이 가장 길게 이어지는 값과 길이"""
    best_k, best_len, cur_k, cur_len = None, 0, None, 0
    for k in ks:
        if k == cur_k:
            cur_len += 1
        else:
            cur_k, cur_len = k, 1
        if cur_len > best_len:
            best_k, best_len = cur_k, cur_len
    return best_k, best_len


def main():
    rows = []
    for year in YEARS:
        for ku in KU_ORDER:
            k0 = C.TARGET_COMMUNITIES[ku]
            s = load_scan(year, ku)
            s = s[s["stage"] == "grid"].sort_values("resolution")
            q = s[s["n_communities"] >= 2].groupby("n_communities")["modularity"].max()
            r = {"year": year, "구": C.KU_NAME[ku], "공식k": k0, "k_Q최대": int(q.idxmax()),
                 "Q_max": q.max(), "Q_공식k": q.get(k0, np.nan), "ΔQ": q.max() - q.get(k0, np.nan)}
            for e in EPS:
                band = sorted(int(k) for k in q.index if q[k] >= q.max() - e)
                r[f"범위_ε{e}"] = f"{min(band)}~{max(band)}" if band else ""
                r[f"공식포함_ε{e}"] = k0 in band
            seq = s["n_communities"].tolist()
            kp, lp = longest_run([k for k in seq if k >= 2])
            seq_r = [k if (k0 / 2 <= k <= 2 * k0) else -1 for k in seq]
            kr, lr = longest_run([k for k in seq_r if k >= 2])
            r.update({"평탄k_전체": kp, "평탄폭_전체": lp, "평탄k_제한": kr, "평탄폭_제한": lr})
            rows.append(r)
    d = pd.DataFrame(rows)
    save(d, "q_band_plateau", "x3")
    L = ["# x3 — B1 ΔQ 허용 범위, B4 평탄 구간", "", "정본 스캔 로그(구별 해상도 250개)로 계산. 재실행 없음.", ""]
    for y in YEARS:
        x = d[d.year == y]
        L += [f"## {y}", "",
              f"- Q 최대 개수 합계 {x['k_Q최대'].sum()} (공식 116). ΔQ 중앙값 {x['ΔQ'].median():.4f}, 최대 {x['ΔQ'].max():.4f}",
              "- 공식 개수가 허용 범위 안인 구: " + ", ".join(f"ε={e} {int(x[f'공식포함_ε{e}'].sum())}/25" for e in EPS),
              f"- 평탄 구간 개수 합계: 전체 {x['평탄k_전체'].sum()}, 공식의 절반~두 배로 제한 {x['평탄k_제한'].sum()}", "",
              md_table(x[["구", "공식k", "k_Q최대", "Q_공식k", "Q_max", "ΔQ", "범위_ε0.01", "평탄k_전체", "평탄폭_전체", "평탄k_제한", "평탄폭_제한"]]), ""]
    (out_dir("x3") / "x3_report.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join([l for l in L if l.startswith("- ") or l.startswith("## ")]))


if __name__ == "__main__":
    main()
