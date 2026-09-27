# -*- coding: utf-8 -*-
"""
k02 — 변화 판정, 선별, 강건성 (연구설계 3절 H1·H2·H3·H5, 4.4 ④⑦⑧, 9절 D3·D5)

입력: k01의 표 + 코어엔진 안정성 결과(독립 합의 10회) + 대안 구획(τ=0.4/0.6, IFR 우선)
출력: output/tables/
  t06_selection.csv     구별 판정·선별·대응 유형·강건성
  t06_tests.json        부호검정, 합의 변동 폭, 가설 판정
  t07_robustness.csv    대안 구획으로 다시 계산한 G·D·선별 여부

선별 규칙 D3-B (분석 전에 고정):
  (i)  ΔD_K > band_K            … 불일치 크기가 합의 변동 폭을 넘어 커졌다
  (ii) D_K,2025 >= D_Seoul,2025 … 2025년 불일치 크기가 서울 전체 이상
  대응 유형: G_K,2025 > 0 → '경계 재검토',  G_K,2025 <= 0 → '접근성·운영 검토'
부록 민감도: A(사분면: G_2025 > G_2020), C(D_2025 상위 25%)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

import config as C
import kpa_metrics as km


def consensus_band():
    """
    독립 합의 10회의 구별 ARI(정본 대비)를 읽는다. 모두 1.0이면 10회의 분할이 정본과 같으므로
    G·D의 합의 변동 폭은 0이다. 1 미만인 구가 있으면 그 구의 폭은 매핑(K1)이 있어야 계산할 수 있다.
    """
    rows = []
    for y in C.YEARS:
        for f in sorted(C.stability_dir(y).glob("*.json")):
            j = json.loads(f.read_text(encoding="utf-8"))
            aris = [t["ari_vs_final"] for t in j["trials"]]
            rows.append({"ku_code": int(j["ku_code"]), "year": y, "n_trials": len(aris),
                         "ari_min": min(aris), "n_dongs_changed": len(j.get("dongs_changed", []))})
    s = pd.DataFrame(rows)
    band = pd.Series(0.0, index=sorted(C.KU_NAME), name="band_pp")
    unknown = s[s["ari_min"] < 1 - 1e-12]["ku_code"].unique().tolist()
    band.loc[unknown] = np.nan
    return s, band, unknown


def selection(ch: pd.DataFrame, band: pd.Series, seoul_D1: float) -> pd.DataFrame:
    out = ch[["ku_name", "ku_name_en", f"G_{C.Y0}", f"G_{C.Y1}", f"D_{C.Y0}", f"D_{C.Y1}", "dG", "dD", "quadrant"]].copy()
    out["band"] = band.reindex(out.index).fillna(0).values / 100.0 + C.MIN_BAND_PP / 100.0
    out["D_increase_beyond_band"] = out["dD"] > out["band"]
    out["D_decrease_beyond_band"] = out["dD"] < -out["band"]
    out["D2025_ge_seoul"] = out[f"D_{C.Y1}"] >= seoul_D1
    out["selected_B"] = out["D_increase_beyond_band"] & out["D2025_ge_seoul"]
    out["type"] = np.where(~out["selected_B"], "",
                           np.where(out[f"G_{C.Y1}"] > C.FLOAT_TOL, "경계 재검토", "접근성·운영 검토"))
    # 부록 민감도: 합의 변동 폭이 0일 때 아주 작은 ΔD(예: 0.01%p)도 '증가'가 되므로 최소 폭을 둔 경우
    for pp in (0.5, 1.0):
        out[f"selected_B_minband{pp}"] = (out["dD"] > pp / 100) & out["D2025_ge_seoul"]
    # 부록 민감도 규칙
    out["selected_A_quadrant"] = out[f"G_{C.Y1}"] > out[f"G_{C.Y0}"]
    out["selected_C_top25"] = out[f"D_{C.Y1}"] >= out[f"D_{C.Y1}"].quantile(0.75)
    return out


def robustness(ch: pd.DataFrame, sel: pd.DataFrame, seoul_D1_main: float):
    """대안 구획(τ 0.4/0.6, IFR 우선)으로 G·D·선별을 다시 계산. 두 해 매핑이 모두 있는 경우만."""
    lz = pd.read_csv(C.LZ_MAP, encoding="utf-8-sig").set_index("Dong")
    ku = lz["Ku"].astype(int); lz_zone = lz["life_zone_id"].astype(int)
    od = {y: pd.read_parquet(C.od_daily(y)) for y in C.YEARS}
    rows = []
    for name, fn in C.ALT_RUNS.items():
        paths = {y: fn(y) for y in C.YEARS}
        if not all(p.exists() for p in paths.values()):
            rows.append({"run": name, "available": False}); continue
        ld = {y: pd.read_csv(paths[y], encoding="utf-8-sig").set_index("Dong")["global_community_id"].astype(int)
              for y in C.YEARS}
        gu = {y: km.metrics_by_gu(km.tag_flows(od[y], lz_zone, ld[y], ku)) for y in C.YEARS}
        seoul_D1 = km.metrics_total(gu[C.Y1])["D"]
        for k in gu[C.Y0].index:
            dD = gu[C.Y1].loc[k, "D"] - gu[C.Y0].loc[k, "D"]
            sel_alt = (dD > 0) and (gu[C.Y1].loc[k, "D"] >= seoul_D1)
            rows.append({"run": name, "available": True, "ku_code": k, "ku_name": C.KU_NAME[k],
                         f"G_{C.Y0}": gu[C.Y0].loc[k, "G"], f"G_{C.Y1}": gu[C.Y1].loc[k, "G"],
                         f"D_{C.Y0}": gu[C.Y0].loc[k, "D"], f"D_{C.Y1}": gu[C.Y1].loc[k, "D"],
                         "dD": dD, "selected_B": sel_alt, "selected_B_main": bool(sel.loc[k, "selected_B"]),
                         "agree_with_main": sel_alt == bool(sel.loc[k, "selected_B"])})
    return pd.DataFrame(rows)


def main():
    ch = pd.read_csv(C.TAB / "t03_gu_change.csv", encoding="utf-8-sig")
    seoul = ch[ch["ku_code"] == "SEOUL"].iloc[0]
    ch = ch[ch["ku_code"] != "SEOUL"].copy()
    ch["ku_code"] = ch["ku_code"].astype(int); ch = ch.set_index("ku_code")
    res = json.loads((C.TAB / "results.json").read_text(encoding="utf-8"))

    stab, band, unknown = consensus_band()
    stab.to_csv(C.TAB / "t06_consensus_stability.csv", index=False, encoding="utf-8-sig")

    sel = selection(ch, band, float(seoul[f"D_{C.Y1}"]))
    # LD2020 고정 비교에서도 D가 커졌는가 (H5)
    fixed = pd.read_csv(C.TAB / "t04b_fixed_ld2020_on_2025.csv", encoding="utf-8-sig").set_index("ku_code")
    sel["dD_fixed_ld2020"] = fixed["D_ld20on25"] - ch[f"D_{C.Y0}"]
    sel["D_increase_fixed_ld2020"] = sel["dD_fixed_ld2020"] > sel["band"]
    sel.to_csv(C.TAB / "t06_selection.csv", encoding="utf-8-sig")

    # 검정 (H1, H2, H3). 부호검정은 변화가 없는 구(두 해 모두 LD=LZ 등)를 빼고 증가:감소만 비교한다.
    n = len(ch)
    def sign_test(s):
        up = int((s > C.FLOAT_TOL).sum()); dn = int((s < -C.FLOAT_TOL).sum()); tie = int(n - up - dn)
        p = float(binomtest(up, up + dn, 0.5, alternative="greater").pvalue) if up + dn else None
        return {"up": up, "down": dn, "tie": tie, "p_greater": p}
    st_dD, st_dG = sign_test(ch["dD"]), sign_test(ch["dG"])
    # IoU(경계 모양)와 G·D의 상관 — D가 크기, G가 방향임을 외부 지표로 확인
    from scipy.stats import spearmanr, pearsonr
    iou = pd.read_csv(C.TAB / "t10_iou_vs_gap.csv", encoding="utf-8-sig").set_index("ku_code")
    def corr(x, y):
        rs, ps = spearmanr(iou[x], iou[y]); rp, pp_ = pearsonr(iou[x], iou[y])
        return {"spearman": float(rs), "p_spearman": float(ps), "pearson": float(rp), "p_pearson": float(pp_)}
    iou_corr = {f"IoU_vs_G_{y}": corr(f"IoU_{y}", f"G_{y}") for y in C.YEARS}
    iou_corr.update({f"IoU_vs_D_{y}": corr(f"IoU_{y}", f"D_{y}") for y in C.YEARS})
    iou_corr["dIoU_vs_dD"] = corr("dIoU", "dD"); iou_corr["dIoU_vs_dG"] = corr("dIoU", "dG")
    k_dD = int((ch["dD"] > 0).sum()); k_dG = int((ch["dG"] > 0).sum())
    k_absG = int((ch[f"G_{C.Y1}"].abs() > ch[f"G_{C.Y0}"].abs()).sum())
    test = {
        "n_gu": n,
        "band_all_zero": len(unknown) == 0,
        "band_unknown_gu": [C.KU_NAME[k] for k in unknown],
        "H1_D_seoul": {y: float(seoul[f"D_{y}"]) for y in C.YEARS},
        "H1_gu_D_beyond_band_2025": int((ch[f"D_{C.Y1}"] > band.reindex(ch.index).fillna(0) / 100).sum()),
        "H2_dD_pos_n": k_dD, "H2_sign_test_p_greater_all25": float(binomtest(k_dD, n, 0.5, alternative="greater").pvalue),
        "H2_sign_test_excl_ties": st_dD, "H3_sign_test_excl_ties": st_dG,
        "H2_dD_seoul": float(seoul["dD"]),
        "H2_seoul_supported": bool(seoul["dD"] > 0),
        "H2_gu_more_up_than_down": bool(st_dD["up"] > st_dD["down"]),
        "H2_supported": bool(st_dD["up"] > st_dD["down"] and (st_dD["p_greater"] or 1) < C.ALPHA),
        "iou_corr": iou_corr,
        "H3_dG_seoul": float(seoul["dG"]), "H3_dG_pos_n": k_dG,
        "H3_sign_test_p_greater": float(binomtest(k_dG, n, 0.5, alternative="greater").pvalue),
        "H3_selected_with_Gpos_share": float((sel.loc[sel["selected_B"], f"G_{C.Y1}"] > 0).mean()) if sel["selected_B"].any() else None,
        "absG_grew_n": k_absG,
        "selection_rule": C.SELECTION_RULE,
        "selected_n": int(sel["selected_B"].sum()),
        "selected": sel.loc[sel["selected_B"], ["ku_name", "type"]].reset_index().to_dict("records"),
        "selected_A_n": int(sel["selected_A_quadrant"].sum()), "selected_C_n": int(sel["selected_C_top25"].sum()),
        "overlap_B_A": int((sel["selected_B"] & sel["selected_A_quadrant"]).sum()),
        "overlap_B_C": int((sel["selected_B"] & sel["selected_C_top25"]).sum()),
        "selected_minband0.5": sel.loc[sel["selected_B_minband0.5"], "ku_name"].tolist(),
        "selected_minband1.0": sel.loc[sel["selected_B_minband1.0"], "ku_name"].tolist(),
        "H5_selected_kept_under_fixed_ld2020": int((sel["selected_B"] & sel["D_increase_fixed_ld2020"]).sum()),
    }
    test["H3_supported"] = bool(seoul["dG"] > 0 and (test["H3_selected_with_Gpos_share"] or 0) > 0.5)

    rob = robustness(ch, sel, float(seoul[f"D_{C.Y1}"]))
    rob.to_csv(C.TAB / "t07_robustness.csv", index=False, encoding="utf-8-sig")
    if "agree_with_main" in rob:
        avail = rob[rob["available"] == True].copy()
        for c in ("agree_with_main", "selected_B"):
            avail[c] = avail[c].astype(bool)
        test["robustness"] = {r: {"agree_n": int(g["agree_with_main"].sum()), "n": int(len(g)),
                                  "selected_n": int(g["selected_B"].sum()),
                                  "identical_partition_to_main": bool(np.allclose(
                                      g.set_index("ku_code")[f"D_{C.Y1}"].sort_index(),
                                      ch[f"D_{C.Y1}"].sort_index()) and np.allclose(
                                      g.set_index("ku_code")[f"D_{C.Y0}"].sort_index(),
                                      ch[f"D_{C.Y0}"].sort_index()))}
                              for r, g in avail.groupby("run")}
    test["robustness_unavailable"] = rob.loc[rob["available"] == False, "run"].tolist()

    (C.TAB / "t06_tests.json").write_text(json.dumps(test, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(test, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
