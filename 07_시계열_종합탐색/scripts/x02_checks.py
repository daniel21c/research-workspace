# -*- coding: utf-8 -*-
"""x02_checks.py — 패널 결합 점검 (한 구 손대조 + 항등식)

C1 격자 인구 합(구) = 엔진 pop_total(구, b=none, 종합)
C2 동 OD 집계를 구로 합친 a·b·T = KPA t02(구)  → 동 단위 이동 지표가 KPA와 같은 정의인지
C3 종로구 2025: 시설 수(cat_A)를 원본 parquet에서 직접 세어 패널과 대조
C4 |G| ≤ D, 0 ≤ COV ≤ 1, 구 COV 재구성(동 pop_reach 합/pop_total 합) = 구 값
"""
import sys, json
from pathlib import Path
import pandas as pd, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parents[1]; ROOT = HERE.parent
T = HERE / "output/tables"
ku = pd.read_csv(T / "panel_ku.csv", encoding="utf-8-sig")
dg = pd.read_csv(T / "panel_dong424.csv", encoding="utf-8-sig")
res = {}
# C1
d = (ku["pop"] - ku["acc_pop_total_none_종합"]).abs().max()
res["C1_pop_grid_vs_engine_maxabs"] = float(d)
# C2
agg = dg.groupby(["ku", "year"])[["mob_a", "mob_b", "mob_T"]].sum().reset_index().rename(columns={"ku": "unit_id"})
m = ku[["unit_id", "year", "mob_a", "mob_b", "mob_T"]].merge(agg, on=["unit_id", "year"], suffixes=("_kpa", "_od"))
res["C2_ab_T_maxrel"] = float(max((m.mob_a_kpa - m.mob_a_od).abs().max() / m.mob_a_kpa.max(), (m.mob_b_kpa - m.mob_b_od).abs().max() / m.mob_b_kpa.max(), (m.mob_T_kpa - m.mob_T_od).abs().max() / m.mob_T_kpa.max()))
# C3
f = pd.read_parquet(ROOT / "06_접근성분석/접근성분석_패키지/데이터/입력/facility/facility_2020_2025_units.parquet")
f = f[f["분석가능"] & f.dong424.notna() & (f.year == 2025) & (f.ku == 11010) & (f.cat_A != "control")]
direct = f.groupby("cat_A").size().to_dict()
row = ku[(ku.unit_id == 11010) & (ku.year == 2025)].iloc[0]
res["C3_jongno_2025"] = {c: [int(direct.get(c, 0)), int(row[f"fac_{c}"])] for c in direct}
res["C3_ok"] = all(int(direct[c]) == int(row[f"fac_{c}"]) for c in direct)
# C4
res["C4_absG_le_D"] = bool((ku.mob_G.abs() <= ku.mob_D + 1e-12).all() and (dg.mob_G.abs() <= dg.mob_D + 1e-12).all())
res["C4_COV_range"] = bool(((ku.filter(like="acc_COV_") >= 0) & (ku.filter(like="acc_COV_") <= 1)).all().all())
rec = dg.groupby(["ku", "year"]).apply(lambda x: x["acc_pop_reach_lz116_교육"].sum() / x["acc_pop_total_lz116_교육"].sum(), include_groups=False).reset_index(name="rec")
mm = ku[["unit_id", "year", "acc_COV_lz116_교육"]].merge(rec.rename(columns={"ku": "unit_id"}), on=["unit_id", "year"])
res["C4_ku_COV_reconstruct_maxabs"] = float((mm["acc_COV_lz116_교육"] - mm.rec).abs().max())
(T / "checks.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
