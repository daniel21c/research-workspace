# -*- coding: utf-8 -*-
"""
k11 — 공동연구자 확인 항목의 독립 재계산 (README 7절)

1) a·b·T·IFR을 kpa_metrics/pandas 없이 두 가지 다른 도구로 다시 계산해 표 3과 대조
   - 순수 파이썬 루프(pyarrow로 읽기만), - DuckDB SQL (설치돼 있으면)
2) 손대조 예시: 동 수가 적고 D>0인 동대문구 2025의 권역 구성과 a·b 기여 동 쌍
3) docx·hwp에 들어간 표 6개의 셀을 결과 파일에서 만든 표와 대조(hwp는 한글 2022 자동화가 있을 때만)
출력: output/manuscript_kpa/독립재계산_기록.json
실행: python k11_independent_check.py
"""
from __future__ import annotations
import csv, json, os, sys, time
from pathlib import Path
import pyarrow.parquet as pq
import config as C
sys.stdout.reconfigure(encoding="utf-8")
MK = C.OUT / "manuscript_kpa"; CORE = C.CORE_DATA
rec = {"생성": time.strftime("%Y-%m-%d %H:%M:%S")}


def read_map(fn, col):
    d = {}
    with open(CORE / fn, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            d[int(r["Dong"])] = (int(r["Ku"]), r[col], r["ADM_NM"])
    return d


def table3():
    import pandas as pd
    d = pd.read_csv(C.TAB / "t02_gu_metrics_long.csv", encoding="utf-8-sig")
    return d[d.ku_code.astype(str) != "SEOUL"]


# ---------- 1a 순수 파이썬 ----------
lz = read_map("dong_to_official_livingzone_mapping_424.csv", "life_zone_id")
long = table3(); worst = 0.0; pure = {}
for y in C.YEARS:
    ld = read_map(f"dong_to_leiden_{y}_mapping_424.csv", "global_community_id")
    acc = {}
    for r in pq.read_table(C.od_daily(y), columns=["dong_O", "dong_D", "flow"]).to_pylist():
        o, d, f = r["dong_O"], r["dong_D"], r["flow"]; k = lz[o][0]
        a = acc.setdefault(k, [0.0, 0.0, 0.0, 0.0, 0.0])          # T, N_lz, N_ld, a, b
        inlz = lz[o][1] == lz[d][1]; inld = ld[o][1] == ld[d][1]
        a[0] += f; a[1] += f * inlz; a[2] += f * inld; a[3] += f * (inld and not inlz); a[4] += f * (inlz and not inld)
    pure[y] = acc
    for k, (T, Nlz, Nld, a, b) in acc.items():
        r = long[(long.ku_code.astype(str) == str(k)) & (long.year.astype(int) == int(y))].iloc[0]
        for mine, ref in [(T, r["T"]), (a, r["a"]), (b, r["b"]), (Nlz / T, r["IFR_lz"]), (Nld / T, r["IFR_ld"]), ((a - b) / T, r["G"]), ((a + b) / T, r["D"])]:
            worst = max(worst, abs(mine - ref) / max(abs(ref), 1e-12))
rec["1a_순수파이썬_vs_표3_최대상대오차"] = worst
print("1a 순수 파이썬 루프 vs 표 3 (25구×2년×7값): 최대 상대오차", f"{worst:.2e}")

# ---------- 1b DuckDB ----------
try:
    import duckdb
    w2 = 0.0
    for y in C.YEARS:
        q = f"""select o.Ku ku, sum(f.flow) T,
          sum(f.flow*(o.life_zone_id=d.life_zone_id)::int) N_lz,
          sum(f.flow*(lo.global_community_id=ldd.global_community_id)::int) N_ld,
          sum(f.flow*(lo.global_community_id=ldd.global_community_id and o.life_zone_id<>d.life_zone_id)::int) a,
          sum(f.flow*(o.life_zone_id=d.life_zone_id and lo.global_community_id<>ldd.global_community_id)::int) b
          from read_parquet('{C.od_daily(y).as_posix()}') f
          join read_csv_auto('{(CORE / "dong_to_official_livingzone_mapping_424.csv").as_posix()}') o on o.Dong=f.dong_O
          join read_csv_auto('{(CORE / "dong_to_official_livingzone_mapping_424.csv").as_posix()}') d on d.Dong=f.dong_D
          join read_csv_auto('{(CORE / f"dong_to_leiden_{y}_mapping_424.csv").as_posix()}') lo on lo.Dong=f.dong_O
          join read_csv_auto('{(CORE / f"dong_to_leiden_{y}_mapping_424.csv").as_posix()}') ldd on ldd.Dong=f.dong_D
          group by o.Ku order by o.Ku"""
        sub = long[long.year.astype(int) == int(y)].copy(); sub["ku_code"] = sub.ku_code.astype(int)
        df = duckdb.query(q).df().merge(sub[["ku_code", "T", "a", "b", "IFR_lz", "IFR_ld"]], left_on="ku", right_on="ku_code")
        for c1, c2 in [("T_x", "T_y"), ("a_x", "a_y"), ("b_x", "b_y")]:
            w2 = max(w2, ((df[c1] - df[c2]).abs() / df[c2].clip(lower=1)).max())
        w2 = max(w2, (df.N_lz / df.T_x - df.IFR_lz).abs().max(), (df.N_ld / df.T_x - df.IFR_ld).abs().max())
    rec["1b_DuckDB_SQL_vs_표3_최대상대오차"] = float(w2); print("1b DuckDB SQL vs 표 3: 최대 상대오차", f"{w2:.2e}")
except Exception as e:
    rec["1b_DuckDB"] = f"미실행: {e!r}"[:120]; print("1b DuckDB 미실행:", repr(e)[:80])

# ---------- 2 손대조 예시 (동대문구 2025) ----------
y, k = 2025, 11060
ld = read_map(f"dong_to_leiden_{y}_mapping_424.csv", "global_community_id")
pairs = {}
T = a = b = 0.0
for r in pq.read_table(C.od_daily(y), columns=["dong_O", "dong_D", "flow"]).to_pylist():
    o, d, f = r["dong_O"], r["dong_D"], r["flow"]
    if lz[o][0] != k: continue
    T += f; inlz = lz[o][1] == lz[d][1]; inld = ld[o][1] == ld[d][1]
    if inld and not inlz: a += f; pairs[(o, d)] = pairs.get((o, d), [0, 0]); pairs[(o, d)][0] += f
    if inlz and not inld: b += f; pairs[(o, d)] = pairs.get((o, d), [0, 0]); pairs[(o, d)][1] += f
grp = lambda m: {g: sorted(v[2] for v in m.values() if v[0] == k and v[1] == g) for g in {v[1] for v in m.values() if v[0] == k}}
top = sorted(pairs.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))[:8]
rec["2_손대조_동대문구_2025"] = {"T": round(T), "a": round(a), "b": round(b), "D_pct": round((a + b) / T * 100, 2), "G_pp": round((a - b) / T * 100, 2),
                              "LZ_권역": grp(lz), "LD2025_권역": grp(ld),
                              "기여_상위_동쌍(a=LD만 내부, b=LZ만 내부)": [{"O": lz[o][2], "D": lz[d][2], "a": round(v[0]), "b": round(v[1])} for (o, d), v in top]}
print("2 동대문구 2025: T", round(T), "a", round(a), "b", round(b), "D%", round((a + b) / T * 100, 2), "G%p", round((a - b) / T * 100, 2))

# ---------- 3 docx·hwp 표 대조 ----------
sys.path.insert(0, str(C.HERE))
from docx import Document
docx = sorted(p for p in MK.glob("국토계획_투고초본_v*.docx") if "2단" not in p.stem)[-1]
if "_v2_" in docx.name:
    from k18_v2_results import build_tables_v2
    tabs = build_tables_v2(); keys = ["T1", "T2", "T3", "T4", "T5", "T6", "TA1"]
else:
    import k06_kpa_submission as k6
    tabs = k6.build_tables(); keys = ["T1", "T2", "T3", "T4", "T5", "TA1"]
exp = {kk: [tabs[kk]["headers"]] + [[str(x) for x in r] for r in tabs[kk]["rows"]] for kk in keys}
rec["3_대조_원고"] = docx.name
d = Document(str(docx)); mism = [kk for t, kk in zip(d.tables, keys) if [[c.text for c in r.cells] for r in t.rows] != exp[kk]]
rec["3_docx_표_불일치"] = mism; print(f"3 docx 표 {len(keys)}개 대조: 불일치", mism)
try:
    from pyhwpx import Hwp
    os.system("taskkill /F /IM Hwp.exe >nul 2>&1")
    hwp = Hwp(visible=False); hwp.open(str(docx.with_suffix(".hwp"))); mism_h = []
    for i, kk in enumerate(keys):
        hwp.get_into_nth_table(i); df = hwp.table_to_df()
        got = [list(map(str, df.columns))] + [[str(x) for x in r] for r in df.values.tolist()]
        if got != exp[kk]: mism_h.append(kk)
    hwp.quit(); rec["3_hwp_표_불일치"] = mism_h; print(f"3 hwp 표 {len(keys)}개 대조: 불일치", mism_h)
except Exception as e:
    rec["3_hwp"] = f"미실행: {e!r}"[:120]; print("3 hwp 미실행:", repr(e)[:80])

(MK / "독립재계산_기록.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
print("기록:", MK / "독립재계산_기록.json")
