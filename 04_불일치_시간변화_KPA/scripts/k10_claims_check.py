# -*- coding: utf-8 -*-
"""k10 — 투고 초본 본문의 수치 주장을 결과 파일과 대조하고, 인용–참고문헌을 대조한다.
실행: python k10_claims_check.py  → output/manuscript_kpa/수치대조_기록.json"""
import json, re, sys
from pathlib import Path
import pandas as pd
import config as C
sys.stdout.reconfigure(encoding="utf-8")
T = C.TAB; MK = C.OUT / "manuscript_kpa"
rc = lambda n: pd.read_csv(T / n, encoding="utf-8-sig")
res = json.loads((T / "results.json").read_text(encoding="utf-8")); tst = json.loads((T / "t06_tests.json").read_text(encoding="utf-8"))
sel = rc("t06_selection.csv").set_index("ku_code"); ari = rc("t09_ari_ld20_ld25.csv").set_index("ku_code")
dec = rc("t04_decomposition.csv"); decD = dec[(dec.metric == "D") & (dec.ku_code != "SEOUL")].copy(); decD["ku_code"] = decD.ku_code.astype(int); decD = decD.set_index("ku_code")
lz = rc("t08b_lz116_change.csv").set_index("life_zone_name"); t01 = rc("t01_data_summary.csv"); rob = rc("t07_robustness.csv")
md = sorted(MK.glob("국토계획_투고초본_v*.md"))[-1].read_text(encoding="utf-8")
S = res["seoul"]; ic = tst["iou_corr"]; h2 = tst["H2_sign_test_excl_ties"]; h3 = tst["H3_sign_test_excl_ties"]; q = res["counts"]["quadrant"]
r1 = lambda x: round(x * 100, 1); r2 = lambda x: round(x * 100, 2)
C_ = []
def chk(name, cond, detail=""): C_.append({"항목": name, "일치": bool(cond), "비고": detail})
chk("서울 IFR LZ 34.1→37.9", r1(S["2020"]["IFR_lz"]) == 34.1 and r1(S["2025"]["IFR_lz"]) == 37.9)
chk("서울 IFR LD 34.8→39.4", r1(S["2020"]["IFR_ld"]) == 34.8 and r1(S["2025"]["IFR_ld"]) == 39.4)
chk("ΔIFR LZ +3.7, LD +4.6", r1(res["seoul_change"]["IFR_lz"]) == 3.7 and r1(res["seoul_change"]["IFR_ld"]) == 4.6)
chk("구별 상승 LZ 1.6~7.4, LD 2.3~9.2", [r1(x) for x in res["range"]["dIFR_lz"]] == [1.6, 7.4] and [r1(x) for x in res["range"]["dIFR_ld"]] == [2.3, 9.2])
chk("LZ ΔIFR 귀무 구간 내 23/25", res["null"]["lz_within_null90_n"] == 23)
chk("LD ΔIFR 귀무 구간 밖 13", 25 - res["null"]["ld_within_null90_n"] == 13)
chk("동 내부통행 18.4→21.1", r1(S["2020"]["SR"]) == 18.4 and r1(S["2025"]["SR"]) == 21.1)
chk("G>0 15/16, G=0 4/5", (res["counts"]["G_pos_2020"], res["counts"]["G_pos_2025"], res["counts"]["G_zero_2020"], res["counts"]["G_zero_2025"]) == (15, 16, 4, 5))
both0 = sorted(sel[(sel.D_2020 == 0) & (sel.D_2025 == 0)].ku_name); chk("두 해 모두 LZ=LD: 중구·구로·금천·서초", both0 == sorted(["중구", "구로구", "금천구", "서초구"]), str(both0))
chk("서울 G +0.67→+1.50", r2(S["2020"]["G"]) == 0.67 and r2(S["2025"]["G"]) == 1.5)
top = sel.D_2025.idxmax(); chk("D 2025 최대 광진 19.5%", sel.loc[top, "ku_name"] == "광진구" and r1(sel.loc[top, "D_2025"]) == 19.5)
gmax, gmin = sel.G_2025.idxmax(), sel.G_2025.idxmin()
chk("G 최대 송파 +5.9(D 14.6), 최소 영등포 −2.4(D 8.7)", sel.loc[gmax, "ku_name"] == "송파구" and r1(sel.loc[gmax, "G_2025"]) == 5.9 and r1(sel.loc[gmax, "D_2025"]) == 14.6 and sel.loc[gmin, "ku_name"] == "영등포구" and r1(sel.loc[gmin, "G_2025"]) == -2.4 and r1(sel.loc[gmin, "D_2025"]) == 8.7)
chk("IoU–D ρ −0.92/−0.87, IoU–G −0.30/−0.30, ΔIoU–ΔD −0.61", round(ic["IoU_vs_D_2020"]["spearman"], 2) == -0.92 and round(ic["IoU_vs_D_2025"]["spearman"], 2) == -0.87 and round(ic["IoU_vs_G_2020"]["spearman"], 2) == -0.3 and round(ic["IoU_vs_G_2025"]["spearman"], 2) == -0.3 and round(ic["dIoU_vs_dD"]["spearman"], 2) == -0.61)
chk("IoU–G p>0.05", ic["IoU_vs_G_2020"]["p_spearman"] > 0.05 and ic["IoU_vs_G_2025"]["p_spearman"] > 0.05)
chk("평균 IoU 0.67→0.71", round(res["iou_seoul_mean"]["2020"], 2) == 0.67 and round(res["iou_seoul_mean"]["2025"], 2) == 0.71)
chk("G 커진 16·작아진 5·불변 4, p=0.013", (h3["up"], h3["down"], h3["tie"]) == (16, 5, 4) and round(h3["p_greater"], 3) == 0.013)
chk("사분면 I 14, III 8, 부호 바뀜 3", q["I (+,+)"] == 14 and q["III (-,-)"] == 8 and q["II (-,+)"] + q["IV (+,-)"] == 3)
chk("D 커진 13·줄어든 8·불변 4, p=0.19", (h2["up"], h2["down"], h2["tie"]) == (13, 8, 4) and round(h2["p_greater"], 2) == 0.19)
chk("서울 D 8.55→8.33(−0.22)", r2(S["2020"]["D"]) == 8.55 and r2(S["2025"]["D"]) == 8.33 and r2(res["seoul_change"]["D"]) == -0.22)
chk("강북 −11.5, 강남 −4.8, 강북 2025 D=0", r1(sel.loc[11090, "dD"]) == -11.5 and r1(sel.loc[11230, "dD"]) == -4.8 and sel.loc[11090, "D_2025"] == 0)
gup = sel[sel.dG > 1e-12]; chk("G 커진 16 중 D도 커진 13", len(gup) == 16 and (gup.dD > 1e-12).sum() == 13)
ex = sorted(gup[gup.dD <= 1e-12].ku_name); chk("G↑인데 D 안 커진 구 = 용산·관악·송파", ex == sorted(["용산구", "관악구", "송파구"]), str(ex))
d = res["decomposition_seoul"]["D"]; chk("분해(서울) 통행 +0.49, 경계 −0.70", r2(d["flow_effect_mean"]) == 0.49 and r2(d["boundary_effect_mean"]) == -0.7)
chk("통행 효과 양 15개", (decD.flow_effect_mean > 1e-9).sum() == 15); chk("LD2020 고정 시 D 증가 15개", int(sel.D_increase_fixed_ld2020.sum()) == 15)
chk("서울 ARI 0.85, 경계 불변 구 10, 최저 강북 0.42", round(res["ari_ld20_ld25_seoul"], 2) == 0.85 and (ari.ari_ld20_ld25 >= 0.9999).sum() == 10 and ari.ari_ld20_ld25.idxmin() == 11090 and round(ari.ari_ld20_ld25.min(), 2) == 0.42)
s8 = sel[sel.selected_B]; chk("선별 8개", len(s8) == 8)
chk("경계 재검토 6 = 광진·성북·도봉·은평·마포·강동", sorted(s8[s8.type == "경계 재검토"].ku_name) == sorted(["광진구", "성북구", "도봉구", "은평구", "마포구", "강동구"]))
chk("운영 검토 2 = 종로·양천", sorted(s8[s8.type != "경계 재검토"].ku_name) == sorted(["종로구", "양천구"]))
chk("고정 비교에서 선별 8 중 6", int(s8.D_increase_fixed_ld2020.sum()) == 6)
chk("0.5%p → 성북·도봉·마포·양천·강동", sorted(sel[sel["selected_B_minband0.5"]].ku_name) == sorted(["성북구", "도봉구", "마포구", "양천구", "강동구"]))
chk("1%p → 성북·양천·강동", sorted(sel[sel["selected_B_minband1.0"]].ku_name) == sorted(["성북구", "양천구", "강동구"]))
chk("종로 +0.09, 광진 +0.01", r2(sel.loc[11010, "dD"]) == 0.09 and r2(sel.loc[11050, "dD"]) == 0.01)
chk("τ 0.4/0.6 선별 동일", bool(rob[rob.run.isin(["tau0.4", "tau0.6"])].agree_with_main.all()))
chk("합의 변동 폭 0", bool(tst["band_all_zero"]))
for nm, v in [("성북구_정릉", 11.4), ("성북구_길음", 11.2), ("양천구_목동", 13.0), ("강동구_길동둔촌", 9.9), ("강동구_암사", 9.7), ("마포구_용강생활권", 7.1), ("은평구_연신내생활", 5.4), ("은평구_수색생활권", 5.1)]:
    m = [i for i in lz.index if str(i) == nm or (str(i).startswith(nm) and nm != "양천구_목동")]
    chk(f"생활권 {nm} ΔD +{v}", bool(m) and r1(lz.loc[m[0], "dD"]) == v, str([(i, r1(lz.loc[i, "dD"])) for i in m]))

dg = res["decomposition_seoul"]["G"]; chk("ΔG 분해 통행 +0.44, 경계 +0.39", r2(dg["flow_effect_mean"]) == 0.44 and r2(dg["boundary_effect_mean"]) == 0.39)
fx = rc("t04b_fixed_ld2020_on_2025.csv").set_index("ku_code"); dGf = fx.G_ld20on25 - sel.G_2020
chk("LD2020 고정 시 G 커진 구 13, 작아진 구 8", (dGf > 1e-9).sum() == 13 and (dGf < -1e-9).sum() == 8)
chk("D 재도출 효과 양 8·음 7·0 10", (decD.boundary_effect_mean > 1e-9).sum() == 8 and (decD.boundary_effect_mean < -1e-9).sum() == 7 and (decD.boundary_effect_mean.abs() <= 1e-9).sum() == 10)
chk("대안 규칙: 사분면 16, 상위25% 7, B⊂A, B∩C 5", int(sel.selected_A_quadrant.sum()) == 16 and int(sel.selected_C_top25.sum()) == 7 and bool((sel.selected_B <= sel.selected_A_quadrant).all()) and sorted(sel[sel.selected_B & sel.selected_C_top25].ku_name) == sorted(["광진구", "도봉구", "은평구", "양천구", "강동구"]))
chk("양천 G_2025 −0.05%p", r2(sel.loc[11150, "G_2025"]) == -0.05)
chk("통행량 269.0/286.0백만, 비공개 22.9/22.4%", [round(x / 1e6, 1) for x in t01.flow_daily_seoul] == [269.0, 286.0] and [r1(x) for x in t01.masked_row_share_daily] == [22.9, 22.4])
# 인용 ↔ 참고문헌
body, refs = md.split("# 인용문헌")[0], md.split("# 인용문헌")[1].split("# 부록")[0]
cite_keys = set()
for c in re.findall(r"\(([^()]*?(?:19|20)\d{2}[^()]*?)\)", body):
    for part in c.split(";"):
        m = re.search(r"([A-Za-z가-힣][A-Za-z가-힣·\s\-\.]*?)(?:\s*et al\.|\s*외)?,?\s*((?:19|20)\d{2})", part.strip())
        if m: cite_keys.add((m.group(1).strip(), m.group(2)))
ref_lines = [l for l in refs.splitlines() if l.strip()]
unmatched = [k for k in cite_keys if not any(k[1] in l and (k[0].split(" and ")[0].split()[0][:3] in l) for l in ref_lines)]
uncited = [l[:40] for l in ref_lines if not any(y in l for (_, y) in cite_keys) or not any((k[0].split(" and ")[0].split()[0][:3] in l and k[1] in l) for k in cite_keys)]
out = {"본문 수치 대조": C_, "실패": [c["항목"] for c in C_ if not c["일치"]], "인용키": sorted(f"{a} {b}" for a, b in cite_keys), "참고문헌에 없는 인용": [f"{a} {b}" for a, b in unmatched], "본문에 인용되지 않은 참고문헌": uncited, "참고문헌 수": len(ref_lines)}
(MK / "수치대조_기록.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
for c in C_: print(("OK  " if c["일치"] else "FAIL"), c["항목"], "" if c["일치"] else c["비고"])
print("총", len(C_), "실패", len(out["실패"])); print("참고문헌에 없는 인용:", out["참고문헌에 없는 인용"]); print("인용되지 않은 참고문헌:", out["본문에 인용되지 않은 참고문헌"])
