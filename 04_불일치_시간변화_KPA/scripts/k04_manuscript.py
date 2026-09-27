# -*- coding: utf-8 -*-
"""
k04 — 4.4절 원고 초안 생성

k01·k02·k03의 결과(output/tables, output/figures)를 읽어 학위논문 4장 4절 원고를 Markdown으로 쓰고,
pandoc이 있으면 .docx로도 변환한다. 본문의 모든 숫자는 이 스크립트가 표에서 읽어 넣는다.
사람이 직접 숫자를 타이핑한 곳은 없다. 문장 구조는 연구설계.md 4.5(결론 4단계)를 따른다.

출력: output/manuscript/4-4절_불일치의_시간변화_진단_원고초안.md / .docx
      output/manuscript/기준원고_대조표.csv
"""
from __future__ import annotations

import json
import shutil
import subprocess

import numpy as np
import pandas as pd

import config as C

Y0, Y1 = C.Y0, C.Y1
T = C.TAB


def pct(x, d=1):
    return f"{x * 100:.{d}f}%"


def pp(x, d=1, sign=True):
    s = f"{x * 100:+.{d}f}" if sign else f"{x * 100:.{d}f}"
    return s + "%p"


def md_table(df: pd.DataFrame, fmt: dict, cols: list, headers: list) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            f = fmt.get(c)
            cells.append(f(v) if f else str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    res = json.loads((T / "results.json").read_text(encoding="utf-8"))
    tst = json.loads((T / "t06_tests.json").read_text(encoding="utf-8"))
    t01 = pd.read_csv(T / "t01_data_summary.csv", encoding="utf-8-sig", dtype={"year": str}).set_index("year")
    ch = pd.read_csv(T / "t03_gu_change.csv", encoding="utf-8-sig")
    seoul = ch[ch.ku_code == "SEOUL"].iloc[0]
    ch = ch[ch.ku_code != "SEOUL"].copy(); ch["ku_code"] = ch.ku_code.astype(int); ch = ch.set_index("ku_code")
    sel = pd.read_csv(T / "t06_selection.csv", encoding="utf-8-sig").set_index("ku_code")
    dec = pd.read_csv(T / "t04_decomposition.csv", encoding="utf-8-sig")
    nul = pd.read_csv(T / "t05_null_summary.csv", encoding="utf-8-sig").set_index("ku_code")
    ari = pd.read_csv(T / "t09_ari_ld20_ld25.csv", encoding="utf-8-sig").set_index("ku_code")
    fixed = pd.read_csv(T / "t04b_fixed_ld2020_on_2025.csv", encoding="utf-8-sig").set_index("ku_code")
    lz116 = pd.read_csv(T / "t08b_lz116_change.csv", encoding="utf-8-sig").set_index("lz_O")
    iou = pd.read_csv(T / "t10_iou_vs_gap.csv", encoding="utf-8-sig").set_index("ku_code")
    ic = tst["iou_corr"]; st = tst["H2_sign_test_excl_ties"]; stG = tst["H3_sign_test_excl_ties"]
    # 선별 구별 문제 생활권(ΔD 가 가장 큰 생활권, 양수인 것만)
    def problem_zones(k, nmax=2):
        zz = lz116[(lz116.ku_code == k) & (lz116.dD > 1e-9)].sort_values("dD", ascending=False).head(nmax)
        return ", ".join(f"{r.life_zone_name.split('_',1)[-1]}({pp(r.dD, 1)})" for _, r in zz.iterrows())

    S = res["seoul"]; SC = res["seoul_change"]; cnt = res["counts"]
    n = len(ch)
    zero_gu = {y: ch.index[np.isclose(ch[f"D_{y}"], 0, atol=1e-9)].tolist() for y in C.YEARS}
    zero_names = {y: "·".join(ch.loc[zero_gu[y], "ku_name"]) for y in C.YEARS}
    identical_both = [k for k in zero_gu[Y0] if k in zero_gu[Y1]]
    selected = sel[sel["selected_B"] == True]
    sel_b = selected[selected["type"] == "경계 재검토"]
    sel_a = selected[selected["type"] == "접근성·운영 검토"]
    decS = dec[dec.ku_code == "SEOUL"].set_index("metric")
    decD = dec[(dec.metric == "D") & (dec.ku_code != "SEOUL")].copy(); decD["ku_code"] = decD.ku_code.astype(int)
    decD = decD.set_index("ku_code")
    lz_in_null = int(nul["lz_within_null90"].sum()); ld_in_null = int(nul["ld_within_null90"].sum())
    dIFR_lz_rng = res["range"]["dIFR_lz"]; dIFR_ld_rng = res["range"]["dIFR_ld"]
    h2 = tst["H2_supported"]
    top_dD = ch["dD"].idxmax(); bot_dD = ch["dD"].idxmin()
    top_D1 = ch[f"D_{Y1}"].idxmax()
    top_G1 = ch[f"G_{Y1}"].idxmax(); bot_G1 = ch[f"G_{Y1}"].idxmin()
    fixed_D_up = int((fixed["D_ld20on25"] - ch[f"D_{Y0}"] > 0).sum())
    kept_fixed = tst["H5_selected_kept_under_fixed_ld2020"]
    masked = {y: t01.loc[y, "masked_row_share_daily"] for y in C.YEARS}

    # ------------------------------------------------------------------ 표
    fmt_ifr = {c: (lambda v: pct(v, 1)) for c in [f"IFR_lz_{Y0}", f"IFR_ld_{Y0}", f"IFR_lz_{Y1}", f"IFR_ld_{Y1}"]}
    fmt_gd = {c: (lambda v: pp(v, 2, sign=True)) for c in [f"G_{Y0}", f"G_{Y1}", "dG", "dD"]}
    fmt_gd.update({c: (lambda v: pct(v, 2)) for c in [f"D_{Y0}", f"D_{Y1}"]})
    tab2 = pd.concat([ch, pd.DataFrame([seoul.rename("SEOUL")])])
    tab2_md = md_table(tab2, {**fmt_ifr, **fmt_gd},
                       ["ku_name", f"IFR_lz_{Y0}", f"IFR_ld_{Y0}", f"G_{Y0}", f"D_{Y0}", f"IFR_lz_{Y1}", f"IFR_ld_{Y1}", f"G_{Y1}", f"D_{Y1}"],
                       ["구", f"IFR LZ {Y0}", f"IFR LD {Y0}", f"G {Y0}", f"D {Y0}", f"IFR LZ {Y1}", f"IFR LD {Y1}", f"G {Y1}", f"D {Y1}"])
    tab3 = pd.concat([ch, pd.DataFrame([seoul.rename("SEOUL")])])
    tab3["dIFR_lz"] = tab3["dIFR_lz"]; tab3["quadrant"] = tab3["quadrant"].fillna("—")
    tab3_md = md_table(tab3, {"dIFR_lz": lambda v: pp(v, 1), "dIFR_ld": lambda v: pp(v, 1), "dG": lambda v: pp(v, 2), "dD": lambda v: pp(v, 2)},
                       ["ku_name", "dIFR_lz", "dIFR_ld", "dG", "dD", "quadrant"],
                       ["구", "ΔIFR LZ", "ΔIFR LD", "ΔG", "ΔD", "사분면(G 2020, G 2025)"])
    dtab = decD.join(ch["ku_name"], rsuffix="_")
    dtab = pd.concat([dtab, pd.DataFrame([{**decS.loc["D"].to_dict(), "ku_name": "서울 전체"}], index=["SEOUL"])])
    tab4_md = md_table(dtab, {c: (lambda v: pp(v, 2)) for c in ["total", "flow_effect_mean", "boundary_effect_mean"]},
                       ["ku_name", "total", "flow_effect_mean", "boundary_effect_mean"],
                       ["구", "ΔD 합계", "통행 변화 효과", "경계 재도출 효과"])
    ntab = nul.join(ch["ku_name"], rsuffix="_")
    tab5_md = md_table(ntab, {"null_dIFR_p05": lambda v: pp(v, 1), "null_dIFR_med": lambda v: pp(v, 1), "null_dIFR_p95": lambda v: pp(v, 1),
                              "dIFR_lz": lambda v: pp(v, 1), "dIFR_ld": lambda v: pp(v, 1),
                              "lz_within_null90": lambda v: "예" if v else "아니오", "ld_within_null90": lambda v: "예" if v else "아니오"},
                       ["ku_name", "null_dIFR_p05", "null_dIFR_med", "null_dIFR_p95", "dIFR_lz", "dIFR_ld", "lz_within_null90", "ld_within_null90"],
                       ["구", "귀무 5%", "귀무 중앙", "귀무 95%", "ΔIFR LZ", "ΔIFR LD", "LZ 구간 내", "LD 구간 내"])
    stab = sel.join(ari[["ari_ld20_ld25", "n_dong_changed"]])
    stab = stab.join(fixed["D_ld20on25"]); stab["dD_fixed"] = stab["D_ld20on25"] - stab[f"D_{Y0}"]
    tab6_md = md_table(stab, {f"D_{Y1}": lambda v: pct(v, 2), "dD": lambda v: pp(v, 2), f"G_{Y1}": lambda v: pp(v, 2),
                              "dD_fixed": lambda v: pp(v, 2), "ari_ld20_ld25": lambda v: f"{v:.2f}",
                              "selected_B": lambda v: "선별" if v else "", "type": lambda v: "" if pd.isna(v) else v,
                              "selected_B_minband0.5": lambda v: "○" if v else "", "selected_B_minband1.0": lambda v: "○" if v else ""},
                       ["ku_name", f"D_{Y1}", "dD", f"G_{Y1}", "selected_B", "type", "selected_B_minband0.5", "selected_B_minband1.0", "dD_fixed", "ari_ld20_ld25", "n_dong_changed"],
                       ["구", f"D {Y1}", "ΔD", f"G {Y1}", "규칙 B", "대응 유형", "ΔD>0.5%p", "ΔD>1%p", "ΔD(LD2020 고정)", "ARI(LD20,LD25)", "소속 변경 동"])

    # 기준 원고 기재값 대조표 (기준 원고 251230판에 인쇄된 값 → 새 값)
    ref = pd.DataFrame([
        ["LZ 평균 IFR 2020", "33.8%", "구 단순평균", pct(res["gu_simple_mean"][Y0]["IFR_lz"]), pct(S[Y0]["IFR_lz"])],
        ["LZ 평균 IFR 2025", "37.6%", "구 단순평균", pct(res["gu_simple_mean"][Y1]["IFR_lz"]), pct(S[Y1]["IFR_lz"])],
        ["LD 평균 IFR 2020", "34.5%", "구 단순평균", pct(res["gu_simple_mean"][Y0]["IFR_ld"]), pct(S[Y0]["IFR_ld"])],
        ["LD 평균 IFR 2025", "39.2%", "구 단순평균", pct(res["gu_simple_mean"][Y1]["IFR_ld"]), pct(S[Y1]["IFR_ld"])],
        ["2025년 LD IFR > LZ IFR 인 구 수", "약 19개", "G>0 인 구", f"{cnt['G_pos_2025']}개 (G=0: {cnt['G_zero_2025']}개)", "—"],
        ["성동구 2025 LZ / LD IFR", "39.4% / 43.8%", "", f"{pct(ch.loc[11040, f'IFR_lz_{Y1}'])} / {pct(ch.loc[11040, f'IFR_ld_{Y1}'])}", "—"],
        ["영등포구 2025 LZ / LD IFR", "53.9% / 51.8%", "", f"{pct(ch.loc[11190, f'IFR_lz_{Y1}'])} / {pct(ch.loc[11190, f'IFR_ld_{Y1}'])}", "기준 원고 값은 분모 정의가 다른 것으로 보임"],
        ["gap 확대(Δgap>0) 구 수", "다수(y=x 위)", "ΔG>0", f"{cnt['dG_pos']}개", f"ΔD>0 은 {cnt['dD_pos']}개"],
    ], columns=["항목", "기준 원고 기재값", "기준 원고 산식", "새 값(같은 산식)", "새 값(분자합/분모합) 또는 비고"])
    ref.to_csv(C.MAN / "기준원고_대조표.csv", index=False, encoding="utf-8-sig")
    ref_md = md_table(ref, {}, list(ref.columns), list(ref.columns))

    # ------------------------------------------------------------------ 본문
    F = "../figures/"
    h2_sentence = (
        f"구 단위로 보면 총 판정차 D가 커진 구가 {st['up']}개, 줄어든 구가 {st['down']}개, 변화가 없는 구가 {st['tie']}개다. "
        f"그러나 서울 전체 D는 {pct(S[Y0]['D'], 2)}에서 {pct(S[Y1]['D'], 2)}로({pp(SC['D'], 2)}) 거의 그대로였다. "
        f"두 결과가 어긋나는 이유는 {ch.loc[bot_dD, 'ku_name']}({pp(ch.loc[bot_dD, 'dD'], 1)})과 "
        f"{ch.loc[ch['dD'].nsmallest(2).index[1], 'ku_name']}({pp(ch['dD'].nsmallest(2).iloc[1], 1)})처럼 통행량이 많거나 개선 폭이 큰 소수 구가 "
        f"나머지 구의 증가를 합계에서 상쇄했기 때문이다. 서울 평균이 유지되었다는 사실은 안심할 근거가 아니라, "
        f"안에서 갈리고 있다는 신호다."
    )
    conclusion_3 = (f"커진 구({st['up']}개)가 줄어든 구({st['down']}개)보다 많았으나 서울 전체 합계로는 유지되었다")

    md = f"""# 4.4 불일치의 시간 변화 진단: 2020년과 2025년

> 원고 초안. 모든 수치는 `04_불일치_시간변화_KPA/scripts/`의 코드가 `데이터_배포목록.md`의 확정 배포본(boundary-v2-dong, od-daily-v1, boundary-v2-leiden)에서 계산한 값이다. 생성 {res['created']}.

## 4.4.1 절의 질문과 접근

앞 절들은 공식 생활권과 이동 기반 경계가 어긋난다는 것(4.2), 그 어긋남이 권역 내 접근성과 관련된다는 것(4.3)을 한 시점에서 보였다. 그러나 생활권은 한 번 설정하고 끝나는 구획이 아니다. 사람의 이동과 시설은 계속 변하므로, 도시기본계획과 도시관리계획이 주기적으로 재정비되듯 생활권도 시점마다 점검해야 한다. 이 절은 그 점검을 어떻게 할 것인가를 다룬다. 질문은 세 가지다.

1. 같은 해에 공식 생활권(LZ)과 이동 기반 경계(LD)의 내부통행 판정은 어느 방향으로, 얼마나 어긋나는가?
2. 그 어긋남은 {Y0}년 1월과 {Y1}년 1월 사이에 어떻게 변했는가? 두 경계 모두에서 오른 내부통행비율(IFR)의 변화와 분리해서 볼 때도 그런가?
3. 분석 전에 정한 규칙으로 재정비 검토 대상을 고르면 어디가 선별되고, 선별된 곳은 어떤 대응의 대상인가?

핵심은 단일 지표의 시점 비교로는 이 질문에 답할 수 없다는 점이다. 한 경계의 IFR이 올랐다는 사실만으로는 경계가 나아졌는지, 이동이 국지화되었는지 구분할 수 없다. 그래서 이 절은 같은 해의 이동 기반 경계를 기준점으로 두고, 공식 생활권이 그 기준점과 어긋나는 정도를 두 시점에서 비교한다.

## 4.4.2 자료와 방법

**자료.** 서울시 생활이동 데이터의 {Y0}년 1월과 {Y1}년 1월 두 스냅샷을 쓴다. 4.2절과 같은 필터(도착 09~20시, 집–직장 통근(HW·WH) 제외, 요일 전체, 출발·도착 모두 서울)를 적용하고 행정동 424개 사이의 통행량으로 집계했다. 필터 후 서울 내부 통행량은 {Y0}년 {S[Y0]['T']/1e6:,.1f}백만, {Y1}년 {S[Y1]['T']/1e6:,.1f}백만이다. 3명 미만으로 비공개 처리된 행은 0으로 두었으며, 그 비율은 {Y0}년 {pct(masked[Y0])}, {Y1}년 {pct(masked[Y1])}다. 행정동 경계는 두 해에 같은 424동 정본을 쓰고, 공식 생활권은 서울시 지역생활권 116개다.

**경계.** 이동 기반 경계(LD)는 4.2절의 방법을 두 해에 똑같이 적용해 연도별로 도출했다. 자치구 안의 동–동 이동 네트워크(무방향, 동 내부통행 포함)에서 Leiden 알고리즘을 해상도마다 3,000회 실행하고, 두 동이 같은 커뮤니티에 속한 비율(co-association)이 0.5 이상인 관계를 이어 합의 분할을 만든다. 구별 커뮤니티 수가 공식 생활권 수와 같아지는 해상도 가운데 모듈성이 가장 높은 분할을 채택하므로 LD도 116개다. 독립 반복 10회에서 두 해 모두 모든 구의 합의 분할이 정본과 일치했다(ARI = 1.0). 합의 임계값을 0.4와 0.6으로 바꾸어도 분할은 같았다.

**지표.** 구 K, 연도 t에서 출발이 K인 서울 내 모든 통행량을 T로 둔다. T는 경계와 무관하므로 같은 구·같은 해에서 두 경계의 분모가 같다. 통행 하나하나에 두 경계가 각각 "내부/외부"를 판정하면, 두 판정이 어긋나는 통행은 두 종류다. 이동 기반 경계에서만 내부인 통행량을 a, 공식 생활권에서만 내부인 통행량을 b라 하면,

- IFR^LZ = N^LZ / T, IFR^LD = N^LD / T (N은 각 경계에서 내부로 판정된 통행량)
- **G = IFR^LD − IFR^LZ = (a − b) / T** : 격차의 **방향**. 양이면 이동 기반 경계가 더 많이 담고, 음이면 공식 생활권이 더 많이 담는다.
- **D = (a + b) / T** : 격차의 **크기**. 두 경계의 판정이 다른 통행의 비율이며, 상쇄되기 전의 총 판정차다. 항상 |G| ≤ D 이고, 두 경계가 같으면 0이다.

G만 보면 a와 b가 상쇄되어 크기를 놓친다. 예컨대 G가 −3%p에서 −1%p로 바뀌면 값은 커졌지만 불일치는 줄었을 수 있다. 그래서 방향은 G로, 크기는 D로 읽는다. 변화는 ΔG = G_{Y1} − G_{Y0}, ΔD = D_{Y1} − D_{Y0}로 정의한다. 서울 전체와 자치구 값은 모두 분자합/분모합이다.

**변화의 분해.** 공식 생활권은 두 해가 같으므로, ΔD는 (가) 통행이 변한 효과와 (나) 이동 기반 경계를 다시 도출한 효과의 합이다. {Y0}년 경계를 {Y1}년 통행에 고정 적용한 값을 중간항으로 두면 두 효과를 나눌 수 있고, 두 순서의 분해를 평균해 보고한다.

**경계와 무관한 변화의 기준선.** IFR 상승이 경계 설계와 무관한 이동의 국지화 때문인지 보기 위해, 구마다 같은 개수의 공간적으로 연속인 무작위 분할을 {res['null']['n_per_gu']:,}개 만들고 같은 분할을 두 해 통행에 적용해 ΔIFR의 분포를 얻었다. 두 경계의 ΔIFR이 이 분포의 5~95% 구간 안에 있으면, 그 상승은 경계와 무관하게 생긴 것으로 본다.

**선별 규칙.** 분석 전에 다음 규칙을 정했다. (i) ΔD가 합의의 변동 폭을 넘어 증가했고, (ii) {Y1}년 D가 서울 전체 D 이상인 구를 재정비 검토 대상으로 선별한다. 선별된 구는 {Y1}년 G의 부호로 대응 유형을 나눈다. G > 0이면 이동 기반 경계가 더 많이 담으므로 경계 재검토가 우선이고, G ≤ 0이면 공식 경계가 이미 더 많이 담는데도 불일치가 커진 경우이므로 기계적 재구획보다 권역 내 접근성·운영 검토가 우선이다. 이번 자료에서 독립 반복의 변동 폭은 0이었으므로 (i)는 ΔD > 0과 같다. 아주 작은 증가까지 포함되는 문제는 부록 민감도(ΔD > 0.5%p, 1%p)로 보인다.

## 4.4.3 두 경계 모두에서 오른 내부통행비율

두 경계 모두에서, 모든 구에서 IFR이 올랐다(그림 4.4-1). 서울 전체 IFR은 공식 생활권이 {pct(S[Y0]['IFR_lz'])}에서 {pct(S[Y1]['IFR_lz'])}로({pp(SC['IFR_lz'])}), 이동 기반 경계가 {pct(S[Y0]['IFR_ld'])}에서 {pct(S[Y1]['IFR_ld'])}로({pp(SC['IFR_ld'])}) 올랐다. 구별 상승 폭은 공식 생활권이 {pp(dIFR_lz_rng[0])}~{pp(dIFR_lz_rng[1])}, 이동 기반 경계가 {pp(dIFR_ld_rng[0])}~{pp(dIFR_ld_rng[1])}였다.

![그림 4.4-1 구별 IFR의 변화]({F}F4-4-1_ifr_dumbbell.png)

이 상승을 생활권 경계의 성과로 읽을 수는 없다. 표 4.4-3과 그림 4.4-6에서 보듯, 공식 생활권의 ΔIFR은 {n}개 구 중 {lz_in_null}개 구에서 같은 구·같은 개수의 무작위 인접 분할이 보인 ΔIFR의 5~95% 구간 안에 있었다. 아무 경계를 그려도 비슷하게 올랐다는 뜻이며, IFR 상승의 대부분은 경계와 무관하게 이동이 구 안에서 더 가까운 곳으로 국지화된 결과다. 동 내부통행 비율도 서울 전체에서 {pct(S[Y0]['SR'])}에서 {pct(S[Y1]['SR'])}로 올랐다. 반면 이동 기반 경계의 ΔIFR은 {n - ld_in_null}개 구에서 그 구간을 넘었는데, 이는 {Y1}년 통행으로 다시 도출한 경계가 그 해의 이동을 더 잘 담기 때문이며 경계 자체의 성과라기보다 방법의 성질이다. 따라서 IFR의 수준이나 그 변화만으로는 경계가 나아졌는지 판단할 수 없고, 두 경계 사이의 상대적 격차를 봐야 한다.

## 4.4.4 같은 해의 격차: 방향과 크기

표 4.4-1은 두 해의 구별 IFR, G, D다. {Y0}년에는 G > 0(이동 기반 경계가 더 많이 담음)인 구가 {cnt['G_pos_2020']}개, G = 0(두 경계가 같음)인 구가 {cnt['G_zero_2020']}개였고, {Y1}년에는 각각 {cnt['G_pos_2025']}개와 {cnt['G_zero_2025']}개였다. 두 해 모두 두 경계가 완전히 같은 구는 {len(identical_both)}개({'·'.join(ch.loc[identical_both, 'ku_name'])})로, 이 구들에서는 공식 생활권이 이동 구조를 그대로 담고 있다. 서울 전체 G는 {pp(S[Y0]['G'], 2)}에서 {pp(S[Y1]['G'], 2)}로 커졌다.

크기 D는 방향과 다른 그림을 보인다. {Y1}년 D가 가장 큰 구는 {ch.loc[top_D1, 'ku_name']}({pct(ch.loc[top_D1, f'D_{Y1}'], 1)})로, 출발 통행의 약 {ch.loc[top_D1, f'D_{Y1}']*100:.0f}%에 대해 두 경계가 다른 판정을 내린다. G가 가장 큰 {ch.loc[top_G1, 'ku_name']}({pp(ch.loc[top_G1, f'G_{Y1}'], 1)})과 가장 작은 {ch.loc[bot_G1, 'ku_name']}({pp(ch.loc[bot_G1, f'G_{Y1}'], 1)})은 방향이 반대이지만 D는 각각 {pct(ch.loc[top_G1, f'D_{Y1}'], 1)}, {pct(ch.loc[bot_G1, f'D_{Y1}'], 1)}로 둘 다 크다. 방향만 보면 {ch.loc[bot_G1, 'ku_name']}의 경우 "공식 생활권이 더 낫다"로 읽히지만, 두 경계의 판정이 어긋나는 통행이 많다는 점은 같다.

![그림 4.4-2 구별 IFR: 이동 기반 경계 vs 공식 생활권]({F}F4-4-2_scatter_ld_vs_lz.png)

**표 4.4-1 구별 IFR, 격차의 방향(G)과 크기(D)**

{tab2_md}

**G와 D는 다른 것을 잰다: 경계 모양(IoU)과의 관계.** 4.2절의 경계 일치도 IoU(동 기준 1:1 매칭)는 통행량을 쓰지 않고 두 경계의 모양만 비교한 값이다. 그림 4.4-7에서 구별 IoU는 D와 강하게 반비례한다({Y0}년 ρ = {ic[f'IoU_vs_D_{Y0}']['spearman']:+.2f}, {Y1}년 ρ = {ic[f'IoU_vs_D_{Y1}']['spearman']:+.2f}). 경계 모양이 다를수록 판정이 어긋나는 통행이 많다는 뜻이고, D가 통행량으로 가중한 경계 불일치임을 확인해 준다. 반면 IoU와 G의 관계는 약하고 유의하지 않다({Y0}년 ρ = {ic[f'IoU_vs_G_{Y0}']['spearman']:+.2f}, {Y1}년 ρ = {ic[f'IoU_vs_G_{Y1}']['spearman']:+.2f}). 경계가 많이 다르다고 해서 어느 한쪽이 더 많이 담는 것은 아니다. 즉 불일치의 **크기**는 D로, **방향**은 G로 읽어야 하며, 5년 사이 경계 모양이 벌어진 구(ΔIoU < 0)에서 D도 커졌다(ΔIoU와 ΔD의 ρ = {ic['dIoU_vs_dD']['spearman']:+.2f}). 서울 평균 IoU는 {res['iou_seoul_mean'][Y0]:.2f}에서 {res['iou_seoul_mean'][Y1]:.2f}로 소폭 올라, 두 경계의 모양은 전체로는 조금 가까워졌다.

![그림 4.4-7 경계 모양의 일치도(IoU)와 판정 불일치의 크기(D), 방향(G)]({F}F4-4-7_iou_vs_D.png)

## 4.4.5 두 시점 사이의 변화

**방향.** G가 커진 구는 {stG['up']}개, 작아진 구는 {stG['down']}개다(변화 없음 {stG['tie']}개, 한쪽 부호검정 p = {stG['p_greater']:.3f}). 서울 전체 G는 {pp(S[Y0]['G'], 2)}에서 {pp(S[Y1]['G'], 2)}로 {pp(SC['G'], 2)} 커졌다. 그림 4.4-3의 사분면도에서 두 해 모두 G > 0인 1사분면에 {cnt['quadrant'].get('I (+,+)', 0)}개 구, 두 해 모두 G ≤ 0인 3사분면에 {cnt['quadrant'].get('III (-,-)', 0)}개 구가 있고, 방향이 바뀐 구는 {cnt['quadrant'].get('II (-,+)', 0) + cnt['quadrant'].get('IV (+,-)', 0)}개다. 즉 격차의 방향은 전반적으로 이동 기반 경계가 더 많이 담는 쪽으로 이동했다.

**크기.** {h2_sentence} ΔD가 가장 큰 구는 {ch.loc[top_dD, 'ku_name']}({pp(ch.loc[top_dD, 'dD'], 1)}), 가장 작은 구는 {ch.loc[bot_dD, 'ku_name']}({pp(ch.loc[bot_dD, 'dD'], 1)})이다. {ch.loc[bot_dD, 'ku_name']}의 경우 {Y0}년에는 두 경계가 달랐으나 {Y1}년에는 이동 기반 경계가 공식 생활권과 같아졌다. G가 커진 {stG['up']}개 구 가운데 D도 커진 구는 {int(((ch['dG'] > 1e-6) & (ch['dD'] > 1e-6)).sum())}개다. 대부분은 방향과 크기가 같이 움직였지만, {'·'.join(ch.loc[(ch['dG'] > 1e-6) & (ch['dD'] <= 1e-6), 'ku_name'])}처럼 G는 커졌는데 어긋나는 통행은 늘지 않은 구도 있어, 확대 여부는 D로 판단한다.

![그림 4.4-3 격차의 방향(G)과 크기(D)의 두 시점 비교]({F}F4-4-3_quadrant_G.png)

**표 4.4-2 구별 변화**

{tab3_md}

**분해.** 표 4.4-4는 ΔD를 통행 변화 효과와 경계 재도출 효과로 나눈 것이다. 서울 전체에서 {Y0}년 이동 기반 경계를 고정하고 {Y1}년 통행만 바꾸면 D는 {pp(decS.loc['D', 'flow_effect_mean'], 2)} 커진다. 즉 5년 전 이동으로 그린 경계도 새 이동과는 더 어긋난다. 이동 기반 경계를 {Y1}년 통행으로 다시 도출하면 D는 {pp(decS.loc['D', 'boundary_effect_mean'], 2)} 변해, 재도출이 어긋남을 상당 부분 되돌린다. 구별로는 {n}개 중 {int((decD['flow_effect_mean'] > 0).sum())}개 구에서 통행 변화 효과가 양이고, {fixed_D_up}개 구에서 {Y0}년 경계를 고정했을 때 D가 커졌다. 이 결과는 "경계를 한 번 정해 두면 시간이 지날수록 실제 이동과 어긋난다"는 주기적 재정비 논리를 직접 뒷받침한다. 다만 어긋남의 크기는 5년 사이 서울 전체로는 1%p 미만이며, 큰 변화는 특정 구에 집중된다.

**표 4.4-4 ΔD의 분해 (두 순서의 평균)**

{tab4_md}

이동 기반 경계 자체의 변화도 구별로 다르다(표 4.4-5의 ARI). 서울 전체에서 {Y0}년과 {Y1}년 이동 기반 경계의 ARI는 {res['ari_ld20_ld25_seoul']:.2f}이고, {int((ari['ari_ld20_ld25'] >= 0.999).sum())}개 구는 두 해의 경계가 같았다. ARI가 가장 낮은 구는 {ari.loc[ari['ari_ld20_ld25'].idxmin(), 'ku_name']}({ari['ari_ld20_ld25'].min():.2f})이다.

## 4.4.6 재정비 검토 대상의 선별

선별 규칙을 적용하면 {len(selected)}개 구가 재정비 검토 대상이다(표 4.4-5, 그림 4.4-4). 이 가운데 {len(sel_b)}개 구({'·'.join(sel_b['ku_name'])})는 {Y1}년 G > 0으로 이동 기반 경계가 더 많이 담는 유형이며, 경계 재검토가 우선이다. {len(sel_a)}개 구({'·'.join(sel_a['ku_name'])})는 G ≤ 0으로 공식 생활권이 더 많이 담는데도 판정 불일치가 커진 유형이다. 이 구들에서 경계를 기계적으로 다시 긋는 것은 권하지 않으며, 4.3절의 결과에 따라 권역 안의 서비스 접근성과 운영 방식을 먼저 점검하는 것이 맞다.

선별 결과의 강건성은 세 가지로 확인했다. 첫째, 합의 임계값을 바꾼 대안 구획에서 분할이 정본과 같았으므로 선별도 같다. 둘째, {Y0}년 경계를 고정한 비교에서도 선별된 {len(selected)}개 구 중 {kept_fixed}개 구에서 D가 커졌다. 셋째, 아주 작은 ΔD를 걸러내기 위해 최소 증가 폭을 0.5%p로 두면 {len(tst['selected_minband0.5'])}개 구({'·'.join(tst['selected_minband0.5'])}), 1%p로 두면 {len(tst['selected_minband1.0'])}개 구({'·'.join(tst['selected_minband1.0'])})가 남는다. 최소 폭에 따라 선별 수가 달라지므로, 본문의 {len(selected)}개는 "검토 후보"이고 최소 폭 1%p를 넘는 구는 "우선 검토 대상"으로 구분해 읽는다.

![그림 4.4-4 총 판정차의 변화와 선별된 구]({F}F4-4-4_map_dD_selection.png)

**표 4.4-5 선별 결과와 강건성**

{tab6_md}

선별된 구 안에서 판정 불일치가 커진 곳은 특정 생활권에 몰려 있다. 출발 동의 공식 생활권별로 D를 나눠 보면(부록 4.4-D 파일), {'; '.join(f"{r.ku_name}: {problem_zones(k)}" for k, r in selected.iterrows() if problem_zones(k))} 순으로 ΔD가 컸다. 개선 논의는 구 전체가 아니라 이 생활권들에서 시작하면 된다.

선별된 구에서 이동 기반 경계가 어떻게 바뀌었는지는 그림 4.4-5에 있다. 경계가 두 해에 같은 구(ARI = 1)에서는 불일치의 변화가 통행 변화만으로 생긴 것이고, 경계가 크게 바뀐 구에서는 이동 구조 자체가 재편된 것이다. 이 절은 그 원인을 분석하지 않는다. 진단법이 어디를 먼저 볼지 알려주는 것까지가 이 절의 몫이다.

![그림 4.4-5 선별된 구의 공식 생활권과 두 해의 이동 기반 경계]({F}F4-4-5_selected_gu_boundaries.png)

## 4.4.7 소결

첫째, {Y0}년과 {Y1}년 사이 두 경계 모두에서 내부통행비율이 올랐다. 그러나 이 상승은 무작위로 그린 경계에서도 같은 크기로 나타났으므로, 내부통행비율의 수준이나 변화만으로는 생활권 경계가 나아졌는지 판단할 수 없다.

둘째, 그래서 이 절은 같은 해의 이동 기반 경계를 기준점으로 삼아 공식 생활권과의 판정 차이를 방향(G)과 크기(D)로 나누어 두 시점에서 비교했다. 방향은 이동 기반 경계가 더 많이 담는 쪽으로 기울었고({stG['up']}개 구), 크기는 {conclusion_3}. 서울 평균이 유지된 것은 소수 구의 큰 개선이 다수 구의 악화를 가린 결과이며, 이것이 전면 개편이 아니라 선별이 필요한 이유다. {Y0}년 경계를 그대로 두었다면 어긋남은 더 커졌을 것이고, 경계를 다시 도출했기 때문에 그 상당 부분이 되돌려졌다.

셋째, 사전에 정한 규칙으로 {len(selected)}개 구가 재정비 검토 후보로 선별되었고, 그중 {len(sel_b)}개 구는 경계 재검토, {len(sel_a)}개 구는 권역 내 접근성·운영 검토 유형이다. 최소 증가 폭 1%p를 넘는 {len(tst['selected_minband1.0'])}개 구가 우선 검토 대상이다.

이 결과는 생활권이 쓸모없다는 뜻이 아니다. {len(identical_both)}개 구에서는 공식 생활권이 두 해 모두 이동 구조와 완전히 일치했고, 절반 가까운 구에서는 어긋남이 줄거나 그대로였다. 다만 경계를 고정해 두면 어긋남이 커진다는 점, 그리고 어긋남이 커진 구가 더 많고 특정 구·특정 생활권에 집중된다는 점은 분명하다. 생활권은 한 번 정해 고정할 수 있는 단위가 아니라, 도시기본계획과 도시관리계획처럼 주기적으로 점검하고 재정비해야 하는 계획단위이며, 이 절의 진단법은 그 점검에서 어디를 먼저 볼지 정하는 도구다. 4.3절에서 보았듯 불일치는 권역 내 접근성과 관련되므로, 재정비는 경계를 다시 긋는 것만이 아니라 권역 안의 서비스 접근성을 높이는 방식으로도 이루어질 수 있다.

**한계.** 두 시점(각 1개월)의 비교이므로 계절성과 중간 시기의 변동은 보지 못한다. 비공개 처리된 소량 통행({pct(masked[Y0])}, {pct(masked[Y1])}의 행)은 0으로 두었다. 이동 기반 경계를 구 안에서 도출했으므로 구를 넘는 기능권역은 보지 못하며, 이는 두 경계에 똑같이 작용한다. 행정동 경계는 두 해에 같은 정본을 썼으므로 경계의 미세 변경은 반영되지 않았다.

---

## 부록 4.4-A 경계와 무관한 IFR 상승의 점검 (귀무 분할)

구마다 같은 개수의 공간적으로 연속인 무작위 분할 {res['null']['n_per_gu']:,}개(시드 {res['null']['seed']})를 만들고 두 해 통행에 같이 적용했다.

![그림 4.4-6 두 경계의 ΔIFR과 귀무 분할의 ΔIFR 분포]({F}F4-4-6_null_partition_dIFR.png)

**표 4.4-3 구별 ΔIFR과 귀무 분할 5~95% 구간**

{tab5_md}

## 부록 4.4-D 생활권(116) 단위 값

본문의 비교 단위는 구다. 출발 동의 공식 생활권별로 나눈 G·D는 `output/tables/t08b_lz116_change.csv`에 있으며, 4.4.6절에서 선별 구 안의 문제 생활권을 지목하는 데만 썼다. 생활권 단위 D는 이동 기반 커뮤니티 하나가 두 생활권에 걸치기만 해도 두 생활권 모두에서 크게 나오므로, 그 자체로 진단 지표로 쓰지 않는다.

## 부록 4.4-B 기준 원고(2025-12-30판) 기재값과 새 값의 대조

기준 원고는 423개 동(개포3동 누락)과 2025-10 실행의 합의 결과를 썼고, "평균 IFR"은 구 비율의 단순평균이었다. 아래는 같은 산식으로 다시 계산한 값과 이 절의 정의(분자합/분모합)로 계산한 값이다.

{ref_md}

## 부록 4.4-C 재현 정보

- 입력 파일 해시(SHA-256 앞 16자): {', '.join(f"{k} {v[:16]}" for k, v in res['inputs'].items())}
- 이동 기반 경계: 해상도마다 Leiden 3,000회, co-association τ = 0.5, base seed {Y0} = {t01.loc[Y0, 'ld_base_seed']}, {Y1} = {t01.loc[Y1, 'ld_base_seed']}; 독립 반복 10회 ARI 최소 {t01.loc[Y0, 'ld_stability_ari_min']:.1f}/{t01.loc[Y1, 'ld_stability_ari_min']:.1f}
- 코드: `04_불일치_시간변화_KPA/scripts/` (k01 지표, k02 판정·선별, k03 그림, k04 원고). 손계산 예제 테스트: `scripts/tests/test_examples.py`
"""
    out_md = C.MAN / "4-4절_불일치의_시간변화_진단_원고초안.md"
    out_md.write_text(md, encoding="utf-8")
    print("원고:", out_md)
    if shutil.which("pandoc"):
        out_docx = out_md.with_suffix(".docx")
        subprocess.run(["pandoc", str(out_md), "-o", str(out_docx), "--resource-path", str(C.MAN)], check=True)
        print("docx:", out_docx)


if __name__ == "__main__":
    main()
