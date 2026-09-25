# -*- coding: utf-8 -*-
"""
x1_frontier_knee.py — A1 프런티어·등가 개수, C3 무릎점
========================================================
입력: 정본 해상도 스캔 로그(output/leiden/{연도}/resolution_scan_logs), od_daily, 공식 생활권 매핑. 재실행 없음.

A1. 구마다 "Leiden 으로 k개일 때 얻은 최대 IFR" F(k) 를 만들고 (스캔 250개 해상도의 합의 분할 중 커뮤니티 수가 k인 것들의 IFR 최댓값),
    k 가 늘면 IFR 이 줄도록 오른쪽부터 누적최대로 다듬는다: F(k) = max_{k'≥k} IFR(k').
    공식 생활권의 (공식 개수 k0, 공식 IFR) 점을 그 위에 찍고,
      - gap      = F(k0) − IFR_공식            (같은 개수에서 이동 기반이 더 자족적인 정도)
      - 등가 개수 k_eq = F(k) = IFR_공식 이 되는 k (선형 보간)
        k_eq > k0 : 이동 기반이면 더 잘게 나누고도 공식과 같은 자족성 → 공식 경계가 이동 구조를 덜 반영
        k_eq < k0 : 공식이 이동 기반 프런티어보다 자족적
    F(k) 는 Q 로 고른 합의 분할의 IFR 이라 진짜 IFR 최대 분할보다 낮다 → k_eq 는 공식에 유리한(보수적) 추정.

C3. F(k) (k=2..12) 에서 무릎점: 첫 점과 끝 점을 잇는 직선에서 가장 멀리 떨어진 k (Kneedle 방식, 축 정규화).
    Q(k) 곡선의 최대 k 와 함께 보고한다. 개수 = 협의 단위 수(행정 비용), IFR = 자족성.

출력: output/exploration/x1/frontier_{연도}.csv, curves.csv, x1_report.md
실행: python x1_frontier_knee.py
"""
from xcommon import *


def knee(ks, ys):
    """정규화한 곡선에서 첫·끝 점을 잇는 직선과의 거리가 최대인 점 (감소 볼록 곡선용)"""
    ks, ys = np.asarray(ks, float), np.asarray(ys, float)
    if len(ks) < 3:
        return np.nan
    x = (ks - ks.min()) / (ks.max() - ks.min())
    y = (ys - ys.min()) / (ys.max() - ys.min() + 1e-12)
    # 감소 곡선: 직선 (0,1)-(1,0) 아래로 가장 볼록한 점
    d = (1 - x) - y           # 직선 y = 1 - x 와의 수직 차이 (양수면 직선 아래)
    return float(ks[np.argmax(np.abs(d))])


def main():
    lz = load_lz()
    rows, curves = [], []
    for year in YEARS:
        G = all_ku_graphs(year)
        m, met = load_leiden(year)
        for ku in KU_ORDER:
            g = G[ku]; k0 = C.TARGET_COMMUNITIES[ku]
            s = load_scan(year, ku); s = s[s["n_communities"] >= 1]
            cur = s.groupby("n_communities").agg(IFR=("ifr", "max"), Q=("modularity", "max")).sort_index()
            cur = cur[cur.index <= 15]
            F = cur["IFR"][::-1].cummax()[::-1]                    # 오른쪽 누적최대 → 비증가
            lo = g.labels_from_mapping(lz["life_zone_id"])
            ifr_off, q_off = g.ifr(lo), g.q(lo)
            ld = g.labels_from_mapping(m["global_community_id"])
            ifr_ld, q_ld = g.ifr(ld), g.q(ld)
            ks, fv = F.index.values.astype(float), F.values
            if ifr_off > fv.max():
                keq = np.nan
            elif ifr_off < fv.min():
                keq = float(ks.max())                                 # 스캔 범위 끝까지도 공식보다 자족적
            else:
                keq = float(np.interp(-ifr_off, -fv, ks))
            sub = cur[(cur.index >= 2) & (cur.index <= 12)]
            Fs = F.reindex(sub.index)
            rows.append({"year": year, "ku": ku, "구": C.KU_NAME[ku], "공식k": k0,
                         "IFR_공식": ifr_off, "IFR_Leiden정본": ifr_ld, "F(k0)": float(F.get(k0, np.nan)),
                         "gap_F(k0)-공식": float(F.get(k0, np.nan)) - ifr_off, "등가k": keq, "등가k-공식k": keq - k0,
                         "Q_공식": q_off, "Q_Leiden정본": q_ld, "k_Q최대": int(cur["Q"].idxmax()),
                         "무릎k_IFR": knee(Fs.index, Fs.values), "무릎k_Q": knee(sub.index, -sub["Q"].values) if len(sub) > 2 else np.nan})
            for k, r in cur.iterrows():
                curves.append({"year": year, "구": C.KU_NAME[ku], "k": int(k), "IFR_max": r["IFR"], "F": F[k], "Q_max": r["Q"]})
    d = pd.DataFrame(rows)
    for y in YEARS:
        save(d[d.year == y], f"frontier_{y}", "x1")
    save(pd.DataFrame(curves), "curves", "x1")

    L = ["# x1 — A1 프런티어·등가 개수, C3 무릎점", "",
         "F(k) = 해상도 스캔에서 커뮤니티 수 k 인 합의 분할들의 IFR 최댓값(k 에 대해 비증가로 보정). 공식 생활권 점을 이 곡선과 비교한다.", ""]
    for y in YEARS:
        x = d[d.year == y]
        L += [f"## {y}", "",
              f"- 등가 개수 합계 {x['등가k'].sum():.1f} (공식 116). 등가k > 공식k 인 구 {int((x['등가k'] > x['공식k']).sum())}/25, "
              f"등가k < 공식k 인 구 {int((x['등가k'] < x['공식k']).sum())}/25",
              f"- 같은 개수에서 이동 기반 IFR 이 공식보다 높은 구 {int((x['gap_F(k0)-공식'] > 0).sum())}/25, gap 평균 {x['gap_F(k0)-공식'].mean():+.4f}",
              f"- 정본 Leiden(Q 선정) IFR 이 공식보다 높은 구 {int((x['IFR_Leiden정본'] > x['IFR_공식']).sum())}/25, Q 가 높은 구 {int((x['Q_Leiden정본'] > x['Q_공식']).sum())}/25",
              f"- 무릎점(IFR) 개수 합계 {x['무릎k_IFR'].sum():.0f}, Q 최대 개수 합계 {x['k_Q최대'].sum()}", "",
              md_table(x[["구", "공식k", "IFR_공식", "F(k0)", "gap_F(k0)-공식", "등가k", "Q_공식", "Q_Leiden정본", "k_Q최대", "무릎k_IFR"]]), ""]
    (out_dir("x1") / "x1_report.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[:12]))


if __name__ == "__main__":
    main()
