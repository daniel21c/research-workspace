# -*- coding: utf-8 -*-
"""S5-0: 9/29 재분석 패키지의 검증된 결과표 중 4.2 원고가 인용하는 것을 해시와 함께 results/reused_20260929/ 에 복사한다. 새로 계산하지 않는다."""
import hashlib, json, shutil
from pathlib import Path
PKG = Path(__file__).resolve().parents[1]
# 9/29 패키지는 2026-10-02 정리 때 D:\Research\_archive\연구2_정리_20261002\ 로 옮겼다. 옛 자리를 먼저 보고 없으면 아카이브를 본다.
SRC = next((p for p in (PKG.parent / "연구2_재분석_패키지_20260929", PKG.parents[2] / "_archive" / "연구2_정리_20261002" / "연구2_재분석_패키지_20260929")
            if p.exists()), PKG.parent / "연구2_재분석_패키지_20260929") / "results"
DST = PKG / "results" / "reused_20260929"
FILES = ["tables/T1_input_overview.csv", "tables/T2_city_summary.csv", "tables/T3_district_2025.csv", "tables/T6_sensitivity.csv", "tables/T7_connected_reference_2025.csv",
         "tables/T8_correlations_2025.csv", "tables/A1_district_2020.csv", "tables/A2_fixed2025_on2020.csv", "tables/A3_contiguity.csv", "summary.json"]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
DST.mkdir(parents=True, exist_ok=True)
rec = []
for rel in FILES:
    s = SRC / rel; d = DST / Path(rel).name
    shutil.copyfile(s, d)
    assert sha(s) == sha(d)
    rec.append({"file": Path(rel).name, "source": str(s), "sha256": sha(d)})
(PKG / "audit" / "s5_reused_inputs.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
print(len(rec), "개 복사·해시 기록")
