# -*- coding: utf-8 -*-
"""
k24 — 원고 본문 수치 대조: 원고(md)에 실제로 적힌 숫자를 결과 파일에서 계산한 값과 문맥 단위로 대조한다.

(2026-09-29 외부 재점검 지적: 이전 k19는 결과 파일 ↔ 코드 속 기대값만 비교해, 원고 숫자가 틀려도 통과했다.)
- 값: 결과 파일의 원정밀도 값에서 표시 단계에서만 한 번 반올림한다(중간 반올림 금지).
- 주장: (ID, 원고 절, 기대 문구). 기대 문구는 값으로 만든 문장 조각이며, 해당 절 안에 그대로 있어야 통과한다.
  같은 숫자가 다른 문맥에 있어도 통과하지 않도록 절과 앞뒤 문구를 함께 묶는다.
- 변조 시험(mutation_test): 주장마다 원고의 해당 숫자를 다른 값으로 바꾸거나 문장을 지우면 그 주장이 반드시 실패해야 한다.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import pandas as pd
import config as C

B = C.TAB / "benchmark"
ROMAN = "ⅠⅡⅢⅣⅤⅥ"


def sections(md: str) -> dict:
    """원고를 절 단위로 나눈다: ABS_EN, ABS_KO, Ⅰ…Ⅵ, Ⅳ.1 같은 절, AI(진술문)."""
    out, h1, h2 = {}, None, None
    for line in md.splitlines():
        m = re.match(r"^%(ABSTRACT_EN|ABSTRACT_KO): (.*)$", line)
        if m: out["ABS_EN" if m.group(1).endswith("EN") else "ABS_KO"] = m.group(2); continue
        if line.startswith("# "):
            t = line[2:].strip(); h2 = None
            h1 = t[0] if t and t[0] in ROMAN else ("AI" if t.startswith("AI") else t)
            continue
        if line.startswith("## "):
            m = re.match(r"^##\s+(\d+)\.", line); h2 = m.group(1) if m else None
            continue
        if h1 is None or line.startswith("[["): continue
        for key in ([h1] + ([f"{h1}.{h2}"] if h2 else [])):
            out[key] = out.get(key, "") + line + "\n"
    return out


def values() -> dict:
    """원고에 쓰는 값을 결과 파일에서 계산(원정밀도 → 표시 반올림 한 번)."""
    rj = lambda n: json.loads((B / n).read_text(encoding="utf-8"))
    rc = lambda p: pd.read_csv(p, encoding="utf-8-sig")
    res = json.loads((C.TAB / "results.json").read_text(encoding="utf-8")); Sd = res["seoul"]
    g = rc(B / "b1_gu.csv"); z = rc(B / "b2_zone.csv"); S1 = rj("b_summary.json"); S4 = rj("b4_summary.json")
    S9 = rj("b9_change_story.json")
    gs = rc(B / "b4_gu_summary.csv"); gm = rc(B / "b4_greedy_moves.csv")
    f1 = lambda x: f"{x:.1f}"; pc = lambda x: f"{x * 100:.1f}"; p0 = lambda x: f"{x * 100:.0f}"
    V = {}
    for y in ("2020", "2025"):
        V[f"ifr_lz_{y}"] = pc(Sd[y]["IFR_lz"]); V[f"ifr_ld_{y}"] = pc(Sd[y]["IFR_ld"]); V[f"sr_{y}"] = pc(Sd[y]["SR"])
    V["within_n"] = str(res["null"]["lz_within_null90_n"])
    lz, ld = g[g.boundary == "LZ"], g[g.boundary == "LD"]
    med = lz.groupby("year")[["pct_N0", "pct_N1", "pct_N2", "med_N0", "med_N1"]].median(); medld = ld.groupby("year")[["pct_N1"]].median()
    for y in (2020, 2025):
        for n in ("N0", "N1", "N2"): V[f"p{n}_{y}"] = p0(med.loc[y, f"pct_{n}"])
        V[f"pLD_N1_{y}"] = p0(medld.loc[y, "pct_N1"])
    V["medN0_25"] = f"{med.loc[2025, 'med_N0']:.3f}"; V["medN1_25"] = f"{med.loc[2025, 'med_N1']:.3f}"
    pv1 = lz.pivot(index="ku_name", columns="year", values="pct_N1"); pv2 = lz.pivot(index="ku_name", columns="year", values="pct_N2")
    for ku, key in (("은평구", "ep"), ("강동구", "gd")):
        V[f"{key}_N1_2020"], V[f"{key}_N1_2025"] = p0(pv1.loc[ku, 2020]), p0(pv1.loc[ku, 2025])
        V[f"{key}_N2_2020"], V[f"{key}_N2_2025"] = p0(pv2.loc[ku, 2020]), p0(pv2.loc[ku, 2025])
    zl = z[z.boundary == "LZ"]
    for y in (2020, 2025):
        V[f"zone_better_{y}"] = p0((zl[zl.year == y].pct > 0.5).mean()); V[f"zone_worse_{y}"] = str(int((zl[zl.year == y].pct < 0.5).sum()))
    V["nb_2020"], V["nb_2025"] = str(S1["동_LZ_2020"]["이웃권역이_더_담는_동수"]), str(S1["동_LZ_2025"]["이웃권역이_더_담는_동수"])
    V["cand_2020"], V["cand_2025"] = str(S4["2020_옆생활권지향동"]["둘다>0"]), str(S4["2025_옆생활권지향동"]["둘다>0"])
    V["any_2025"] = str(S4["2025_옆생활권지향동"]["둘다>0_아무이동"])
    V["cand_share"] = f"{int(S4['2020_옆생활권지향동']['둘다>0'] / 424 * 100)}~{int(S4['2025_옆생활권지향동']['둘다>0'] / 424 * 100)}%"
    q0, q5, h = S4["2020_탐욕재배정"], S4["2025_탐욕재배정"], S4["보류검증_2020경계를_2025에"]
    V.update({"m25": str(q5["옮긴_동"]), "k25": str(q5["옮긴_구"]), "m25_share": f"{q5['옮긴_동'] / 424 * 100:.0f}%", "m20": str(q0["옮긴_동"]), "e20": str(q0["이동_횟수"]),
              "i25b": f1(q5["서울IFR_전"]), "i25a": f1(q5["서울IFR_후"]), "i25l": f1(q5["서울IFR_가상경계"]), "d25b": f1(q5["서울D_전"]), "d25a": f1(q5["서울D_후"]),
              "q25b": f"{q5['Q_전_중앙']:.3f}", "q25a": f"{q5['Q_후_중앙']:.3f}", "q25l": f"{q5['Q_가상경계_중앙']:.3f}",
              "i20b": f1(q0["서울IFR_전"]), "i20a": f1(q0["서울IFR_후"]), "i20l": f1(q0["서울IFR_가상경계"]), "d20b": f1(q0["서울D_전"]), "d20a": f1(q0["서울D_후"]),
              "dred": "60% 넘게" if (q5["서울D_전"] - q5["서울D_후"]) / q5["서울D_전"] > 0.6 else "?",
              "common": str(S4["두해모두_권고_이동"]), "only20": str(S4["2020만"]), "only25": str(S4["2025만"]),
              "fix_i": f1(h["서울IFR_2020재배정경계"]), "fix_ib": f1(h["서울IFR_공식"]), "fix_d": f1(h["서울D_2020재배정경계"]), "fix_db": f1(h["서울D_공식"]),
              "fix_qb": f"{h['Q_공식_중앙']:.3f}", "fix_q": f"{h['Q_2020재배정경계_중앙']:.3f}",
              "fix_k": str(h["재배정있는_구"]), "fix_ki": str(h["구_IFR_개선"]), "fix_kq": str(h["구_Q_개선"]), "fix_kd": str(h["구_D_감소"])})
    V["neg20"] = str(int((gm[gm.year == 2020].dIFR_pp < 0).sum())); V["neg25"] = str(int((gm[gm.year == 2025].dIFR_pp < 0).sum()))
    gj = gs[(gs.year == 2025) & (gs.ku_name == "광진구")].iloc[0]; V["gj_n"] = str(int(gj.n_moved)); V["gj_d"] = f1(gj.dIFR_pp)
    # 단일 이동 후보와 순차 재배정의 겹침(2025)
    from k14_reassign import final_changes
    lzm = pd.read_csv(C.LZ_MAP, encoding="utf-8-sig").set_index("Dong"); sm = rc(B / "b4_single_moves.csv"); sm = sm[sm.year == 2025]
    bp = sm.sort_values("dQ", ascending=False).drop_duplicates("dong"); cand = set(bp[bp.misassigned_k13 & (bp.dIFR_pp > 0) & (bp.dQ > 0)].dong)
    fin = {d for d, _, _ in final_changes(gm, lzm, 2025)}; oth = bp.set_index("dong").reindex(sorted(fin - cand))
    V.update({"ov": str(len(cand & fin)), "oth": str(len(oth)), "oth_na": str(int(oth.dQ.isna().sum())), "oth_qi": str(int(((oth.dQ > 0) & (oth.dIFR_pp <= 0)).sum())), "oth_q0": str(int((oth.dQ <= 0).sum()))})
    # 자족성 상승·불일치 지속(k25)
    U, W, Dv, Gv, Fx = S9["유형분해"], S9["평일주말"], S9["D변화"], S9["G확대"], S9["고정경계_부호검정"]
    pp = lambda p: "< 0.001" if p < 0.001 else f"= {p:.3f}"
    V.update({"up_lz": str(S9["IFR상승_구수"]["공식"]), "up_ld": str(S9["IFR상승_구수"]["가상경계"]), "up_p": pp(max(S9["IFR상승_구수"]["p_공식"], S9["IFR상승_구수"]["p_가상경계"])),
              "within": f"{U['유형내_비중'] * 100:.0f}%", "comp": f"{(1 - U['유형내_비중']) * 100:.0f}%", "ntype_up": str(U["IFR상승_유형수"]),
              "wk0": pc(W["IFR2020_주말"]), "wk1": pc(W["IFR2025_주말"]), "wd0": pc(W["IFR2020_평일"]), "wd1": pc(W["IFR2025_평일"]), "wk_k": str(W["구수_주말>평일"]), "wk_p": pp(W["p_양측"]),
              "d_up": str(Dv["증가"]), "d_dn": str(Dv["감소"]), "d_p": f"{Dv['p_부호_양측']:.2f}", "d_same": str(Dv["변화없음"]),
              "g0": f1(Gv["G2020"] * 100), "g1": f1(Gv["G2025"] * 100), "g_up": str(Gv["구_증가"]), "g_dn": str(Gv["구_감소"]), "g_p": f"{Gv['p_부호_양측']:.3f}",
              "g_f": f"{Gv['통행몫_평균'] * 100:.0f}%", "g_f1": f"{Gv['통행몫_순서1'] * 100:.0f}", "g_f2": f"{Gv['통행몫_순서2'] * 100:.0f}",
              "gf_up": str(Gv["구_통행몫양수"]), "gf_dn": str(Gv["구_통행몫음수"]), "gf_p": f"{Gv['p_통행몫_양측']:.3f}",
              "fx_n": str(Fx["n"]), "fx_q": str(Fx["Q개선"]), "fx_qp": pp(Fx["p_Q"]), "fx_d": str(Fx["D감소"]), "fx_dp": pp(Fx["p_D"]),
              "n1_better": str(S9["N1_무작위보다나은구"]["2025"]) if S9["N1_무작위보다나은구"]["2020"] == S9["N1_무작위보다나은구"]["2025"] else "?", "n1_p": pp(max(S9["N1_무작위보다나은구_p"].values()))})
    for y in ("2020", "2025"):
        alt = S4[f"{y}_대안분모_같은구_자기동제외"]
        V[f"alt_lz_{y}"], V[f"alt_ld_{y}"], V[f"alt_re_{y}"] = f1(alt["서울IFR_공식"]), f1(alt["서울IFR_가상경계"]), f1(alt["서울IFR_재배정"])
    return V


def spec(v: dict) -> list[tuple[str, str, str]]:
    """(주장 ID, 원고 절, 기대 문구). 초록은 숫자를 쓰지 않으므로 대조하지 않는다."""
    return [
        # Ⅲ 자료
        ("m_flow", "Ⅲ.1", "필터를 적용한 서울 내부 통행량은 2020년 2억 6,904만, 2025년 2억 8,596만이다"),
        # Ⅳ.1 자족성 수준 / Ⅳ.2 상승의 판별(구성 변경 2026-09-30: 절 번호는 새 목차 기준)
        ("r1_ifr", "Ⅳ.1", f"공식 생활권이 {v['ifr_lz_2020']}%에서 {v['ifr_lz_2025']}%로, 빅데이터 기반 가상경계가 {v['ifr_ld_2020']}%에서 {v['ifr_ld_2025']}%로"),
        ("r1_all", "Ⅳ.2", f"두 경계 모두 {v['up_lz']}개 자치구 전부에서 나타났다(부호검정 p {v['up_p']})" if v['up_lz'] == v['up_ld'] == "25" else "상승 구 수 확인"),
        ("r1_within", "Ⅳ.2", f"25개 구 중 {v['within_n']}개 구에서 무작위 비교경계가 보인 상승의 5~95% 범위 안"),
        ("r1_sr", "Ⅳ.1", f"동 안에서 끝나는 통행의 비율도 {v['sr_2020']}%에서 {v['sr_2025']}%로"),
        ("r1_type", "Ⅳ.2", f"유형 내 효과가 {v['within']}를 차지하였고"),
        ("r1_comp", "Ⅳ.2", f"구성 효과는 {v['comp']}에 그쳤다"),
        ("r1_ntype", "Ⅳ.2", f"{v['ntype_up']}개 이동 유형 모두에서 IFR이 올랐다"),
        ("r1_week", "Ⅳ.2", f"주말 통행의 IFR은 {v['wk0']}%에서 {v['wk1']}%로, 평일 통행의 IFR은 {v['wd0']}%에서 {v['wd1']}%로"),
        ("r1_week_k", "Ⅳ.2", f"25개 구 중 {v['wk_k']}개 구에서 주말의 상승 폭이 더 컸다(부호검정 p {v['wk_p']})"),
        # Ⅳ.2 불일치의 지속
        ("r2_d", "Ⅳ.3", f"판정 불일치 D는 2020년 {v['d20b']}%, 2025년 {v['d25b']}%로"),
        ("r2_d_gu", "Ⅳ.3", f"D가 늘어난 구가 {v['d_up']}개, 줄어든 구가 {v['d_dn']}개로 뚜렷한 방향이 없었다(부호검정 p = {v['d_p']})"),
        ("r2_d_same", "Ⅳ.3", f"두 경계가 완전히 같은 {v['d_same']}개 구를 제외하면"),
        ("r2_g", "Ⅳ.3", f"서울 전체의 G는 {v['g0']}%p에서 {v['g1']}%p로 커졌고, 격차가 커진 구가 {v['g_up']}개, 줄어든 구가 {v['g_dn']}개였다(부호검정 p = {v['g_p']})"),
        ("r2_gf", "Ⅳ.3", f"(대칭 분해 {v['g_f']}, 분해 순서에 따라 {v['g_f1']}~{v['g_f2']}%)"),
        ("r2_gf_gu", "Ⅳ.3", f"통행 변화의 몫이 격차를 키운 구가 {v['gf_up']}개로 줄인 구 {v['gf_dn']}개보다 많았다(부호검정 p = {v['gf_p']})"),
        # Ⅳ.3 전반적 적합성
        ("r3_size", "Ⅳ.4", f"구 IFR 중앙값은 2025년 {v['medN0_25']}이었으나 권역별 동 수까지 맞춘 무작위 비교경계(N1)는 {v['medN1_25']}였다"),
        ("r3_N0", "Ⅳ.4", f"N0와 비교하면 2020년 {v['pN0_2020']}, 2025년 {v['pN0_2025']}로"),
        ("r3_N1", "Ⅳ.4", f"N1과 비교하면 두 해 모두 {v['pN1_2025']}이고 통행량 비중까지 맞춘 N2와 비교해도 {v['pN2_2020']}~{v['pN2_2025']}이다" if v['pN1_2020'] == v['pN1_2025'] else "N1 두 해 값 확인"),
        ("r3_better", "Ⅳ.4", f"무작위 비교경계의 중앙보다 나은 자치구는 두 해 모두 25개 중 {v['n1_better']}개였다(부호검정 p {v['n1_p']})"),
        ("r3_ep", "Ⅳ.4", f"N1과 비교하면 2020년 {v['ep_N1_2020']}, 2025년 {v['ep_N1_2025']}에 그치지만 N2와 비교하면 {v['ep_N2_2020']}, {v['ep_N2_2025']}로"),
        ("r3_zone", "Ⅳ.4", f"116개 생활권 가운데 2020년 {v['zone_better_2020']}%, 2025년 {v['zone_better_2025']}%가"),
        # Ⅳ.4 경계 동
        ("r4_nb", "Ⅳ.4", f"옆 생활권으로 통행을 더 많이 보내는 동은 2020년 {v['nb_2020']}개, 2025년 {v['nb_2025']}개였다"),
        ("r4_cand", "Ⅳ.4", f"2020년 {v['cand_2020']}개, 2025년 {v['cand_2025']}개로 전체 424개 동의 {v['cand_share']}였다"),
        ("r4_any", "Ⅳ.4", f"2025년은 {v['any_2025']}개이다"),
        # Ⅳ.5 재배정과 지속성
        ("r5_m25", "Ⅳ.4", f"2025년에는 {v['k25']}개 구의 {v['m25']}개 동(전체의 {v['m25_share']})의 소속이 바뀌었다"),
        ("r5_overlap", "Ⅳ.4", f"40개에 속하는 동은 {v['ov']}개이다. 나머지 {v['oth']}개는 처음에는 옮길 수 없었거나({v['oth_na']}개), 처음부터 모듈성은 오르지만 IFR은 오르지 않았거나({v['oth_qi']}개), 앞선 이동으로 권역 구성이 바뀐 뒤 모듈성이 오르게 된 동({v['oth_q0']}개)"),
        ("r5_ifr25", "Ⅳ.4", f"서울 전체 IFR은 {v['i25b']}%에서 {v['i25a']}%로 올라 빅데이터 기반 가상경계({v['i25l']}%)와 비슷해졌고, 판정 불일치 D는 {v['d25b']}%에서 {v['d25a']}%로 {v['dred']} 줄었다"),
        ("r5_q25", "Ⅳ.4", f"모듈성 중앙값도 {v['q25b']}에서 {v['q25a']}로 올라 가상경계({v['q25l']})"),
        ("r5_2020", "Ⅳ.4", f"2020년에는 {v['m20']}개 동의 소속이 바뀌었으며(이동 {v['e20']}회), IFR은 {v['i20b']}%에서 {v['i20a']}%로 가상경계({v['i20l']}%)를 넘었고 D는 {v['d20b']}%에서 {v['d20a']}%로"),
        ("r5_gj", "Ⅳ.4", f"{v['gj_n']}개 동을 옮기면 구 IFR이 {v['gj_d']}%p 오르고"),
        ("r5_common", "Ⅳ.4", f"조합까지 같은 동이 {v['common']}개였다(2020년에만 {v['only20']}개, 2025년에만 {v['only25']}개"),
        ("r5_fixed_ku", "Ⅳ.4", f"재배정이 있던 {v['fx_n']}개 구 가운데 모듈성은 {v['fx_q']}개 구(부호검정 p {v['fx_qp']}), 판정 불일치 D는 {v['fx_d']}개 구에서 개선되었다(p {v['fx_dp']})"),
        ("r5_fixed", "Ⅳ.4", f"IFR이 {v['fix_ib']}%에서 {v['fix_i']}%로 오르고 D가 {v['fix_db']}%에서 {v['fix_d']}%로 줄었다"),
        # Ⅴ·Ⅵ
        ("d4_alt", "Ⅴ.5", f"(2025년 공식 생활권 {v['alt_lz_2025']}%, 가상경계 {v['alt_ld_2025']}%, 재배정 {v['alt_re_2025']}%)"),
        ("c_share", "Ⅵ", f"전체 행정동의 {v['cand_share']}에 해당하는 일부 경계 동"),
        ("c_seq", "Ⅵ", f"2025년 {v['m25']}개 동의 소속을 바꾸면"),
        ("c_dred", "Ⅵ", f"판정 불일치는 {v['dred']} 줄었다"),
        ("c_common", "Ⅵ", f"{v['common']}개 동의 재배정은 두 해에 같았고"),
    ]

def check(md: str, v: dict | None = None) -> list[dict]:
    v = v or values(); sec = sections(md); out = []
    for cid, where, exp in spec(v):
        txt = sec.get(where, "")
        out.append({"ID": cid, "절": where, "기대": exp, "일치": exp in txt, "절_있음": bool(txt)})
    return out


def mutation_test(md: str, v: dict | None = None) -> dict:
    """주장마다 (1) 기대 문구의 첫 숫자를 바꾼 원고, (2) 기대 문구를 지운 원고에서 그 주장이 실패하는지 확인."""
    v = v or values(); res = {"숫자변조": 0, "숫자변조_감지": 0, "삭제": 0, "삭제_감지": 0, "감지못함": []}
    for cid, where, exp in spec(v):
        if exp not in md: continue
        m = re.search(r"\d+(?:\.\d+)?", exp)
        if m:
            num = m.group(0); alt = "999" if num != "999" else "998"
            bad = md.replace(exp, exp[:m.start()] + alt + exp[m.end():])
            r = {c["ID"]: c["일치"] for c in check(bad, v)}; res["숫자변조"] += 1
            if not r[cid]: res["숫자변조_감지"] += 1
            else: res["감지못함"].append(f"{cid}: 숫자")
        bad = md.replace(exp, ""); r = {c["ID"]: c["일치"] for c in check(bad, v)}; res["삭제"] += 1
        if not r[cid]: res["삭제_감지"] += 1
        else: res["감지못함"].append(f"{cid}: 삭제")
    return res


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    md = sorted((C.MK).glob("국토계획_투고초본_v2_*.md"))[-1].read_text(encoding="utf-8")
    r = check(md); bad = [c for c in r if not c["일치"]]
    for c in bad: print("불일치", c["ID"], c["절"], "|", c["기대"])
    print(f"원고 수치 대조 {len(r) - len(bad)}/{len(r)}"); print("변조 시험", mutation_test(md))
