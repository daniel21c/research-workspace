# -*- coding: utf-8 -*-
"""9/29 재분석 결과표 10개(results/reused_20260929/)를 등록 배포본 입력 6개만으로 다시 만들고, 지금 사본과 SHA-256이 같은지 확인한다.

코드: 9/29 패키지 code/analyze.py 의 사본 analyze_20260929.py(SHA-256 20c8d856…)를 그대로 불러 쓴다.
  analyze() 안에서 바꾸는 곳은 아래 세 군데뿐이고, 계산 부분(경계·OD 읽기부터 summary.json 쓰기까지)은 한 글자도 바꾸지 않는다.
  (1) 앞부분 '설정·계약 문서 검사': 9/29 패키지 안의 설정 파일·설계 문서·허브 문서 사본(수치 입력 아님)의 해시를 확인하던 부분이다.
      이 패키지에는 그 문서들이 없으므로, 9/29 패키지가 계산에 쓴 입력 6개의 해시 확인으로 바꾼다. 설정값(연도, 재표집 횟수)은 그대로 넣는다.
  (2) 그림 만들기(make_figures): 원고 그림은 code/s5_figures.py 가 따로 만들므로 부르지 않는다.
  (3) 실행 기록(execution.json) 쓰기: 지우고, 대신 이 스크립트가 audit/reuse_20260929_rebuild.json 을 쓴다.
입력(inputs/): seoul_boundaries_all.gpkg, dong_to_official_livingzone_mapping_424.csv, dong_to_leiden_2020·2025_mapping_424.csv,
              od_daily_202001·202501.parquet (배포 ID boundary-v2-dong, boundary-v2-leiden, od-daily-v1)
출력: 임시 폴더에 만든 뒤 10개 파일만 대조하고 지운다. 결과 사본(results/reused_20260929/)은 바꾸지 않는다.
  python code/reuse_20260929/rebuild_reused.py            # 대조만
"""
from __future__ import annotations
import hashlib, json, sys, tempfile, time, types
from pathlib import Path

PKG = Path(__file__).resolve().parents[2]
SRC = Path(__file__).resolve().parent / "analyze_20260929.py"
SRC_SHA = "20c8d856bad6975c5419d1a17f8277f9b9a2247e5ecac84c8563a637420855a1"
COPIES = PKG / "results" / "reused_20260929"
FILES = ["tables/T1_input_overview.csv", "tables/T2_city_summary.csv", "tables/T3_district_2025.csv", "tables/T6_sensitivity.csv",
         "tables/T7_connected_reference_2025.csv", "tables/T8_correlations_2025.csv", "tables/A1_district_2020.csv",
         "tables/A2_fixed2025_on2020.csv", "tables/A3_contiguity.csv", "summary.json"]
# 9/29 패키지 audit/source_manifest.json 의 'analysis input' 6개(그 패키지가 계산에 쓴 파일의 해시)
INPUTS_0929 = {
    "dong_to_official_livingzone_mapping_424.csv": "4c75ebfaba8e644d",
    "dong_to_leiden_2020_mapping_424.csv": "d03ba1a05a17e875",
    "dong_to_leiden_2025_mapping_424.csv": "19c35263178c7779",
    "seoul_boundaries_all.gpkg": "ec8467ec3e9bebfc",
    "od_daily_202001.parquet": "4533810ebd4c68fd",
    "od_daily_202501.parquet": "7ee0183b2544a8dd",
}
# 9/29 패키지 analysis_config.json 에서 계산에 쓰이는 값(그 밖의 항목은 문서 검사·기록용)
CFG = {"years": [2020, 2025], "bootstrap_draws": 5000, "null_draws_per_district": 1000, "seed": 20260929}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def load_rebuild():
    """원본 소스를 읽어 위 세 군데만 바꾼 rebuild(input_dir, output) 함수를 만든다. 바꿀 원문이 정확히 있는지 먼저 확인한다."""
    assert sha(SRC) == SRC_SHA, "analyze_20260929.py 가 9/29 원본과 다르다"
    text = SRC.read_text(encoding="utf-8")
    mod = types.ModuleType("analyze_20260929"); mod.__file__ = str(SRC)
    exec(compile(text, str(SRC), "exec"), mod.__dict__)                       # 도움 함수(overlap, flow_stats 등)와 SEED
    assert mod.SEED == CFG["seed"]
    body = text[text.index("def analyze(input_dir,output,null_draws=1000):"):text.index("def make_figures(")]
    head_old = body[body.index("    start=time.perf_counter()\n"):body.index("    gpkg=input_dir/'seoul_boundaries_all.gpkg'\n")]
    assert "assert sha(PACKAGE/cfg['design_path'])" in head_old and "for r in sources:" in head_old and head_old.count("\n") == 24
    head_new = ("    start=time.perf_counter()\n"
                "    cfg=CFG\n"
                "    output.mkdir(parents=True,exist_ok=True)\n"
                "    for sub in ['tables','figures','audit']: (output/sub).mkdir(exist_ok=True)\n"
                "    checks=[]\n"
                "    def check(name,condition,detail):\n"
                "        checks.append(dict(check=name,passed=bool(condition),detail=detail))\n"
                "        if not condition: raise AssertionError(f'{name}: {detail}')\n"
                "    for name,prefix in INPUTS_0929.items():\n"
                "        check('hash_'+name,sha(input_dir/name)[:16]==prefix,sha(input_dir/name))\n")
    fig_old = "    make_figures(d,main,outputs,output/'figures')\n"
    tail_old = body[body.index("    run=dict("):]
    assert body.count(fig_old) == 1 and tail_old.startswith("    run=dict(") and "dump(run,output/'audit/execution.json')" in tail_old
    tail_new = "    return checks\n\n"
    new = body.replace(head_old, head_new, 1).replace(fig_old, "", 1).replace(tail_old, tail_new, 1)
    new = new.replace("def analyze(input_dir,output,null_draws=1000):", "def rebuild(input_dir,output,null_draws=1000):", 1)
    mod.CFG = CFG; mod.INPUTS_0929 = INPUTS_0929
    exec(compile(new, str(SRC) + " [rebuild]", "exec"), mod.__dict__)
    return mod.rebuild, {"head_lines_replaced": head_old.count("\n"), "make_figures_removed": True, "execution_record_removed": True}


def main():
    t0 = time.time()
    rebuild, changes = load_rebuild()
    with tempfile.TemporaryDirectory(prefix="reuse_20260929_") as td:
        out = Path(td)
        checks = rebuild(PKG / "inputs", out, CFG["null_draws_per_district"])
        rows = []
        for rel in FILES:
            new, old = out / rel, COPIES / Path(rel).name
            rows.append({"file": Path(rel).name, "rebuilt_sha256": sha(new), "copy_sha256": sha(old), "same": sha(new) == sha(old)})
    rec = json.loads((PKG / "audit" / "s5_reused_inputs.json").read_text(encoding="utf-8"))
    rec_sha = {r["file"]: r["sha256"] for r in rec}
    report = {"created": time.strftime("%Y-%m-%dT%H:%M:%S"), "code": "code/reuse_20260929/analyze_20260929.py (9/29 analyze.py 사본, SHA-256 " + SRC_SHA + ")",
              "changes_to_original": changes, "inputs": {k: sha(PKG / "inputs" / k) for k in INPUTS_0929}, "checks_passed": f"{sum(c['passed'] for c in checks)}/{len(checks)}",
              "files": rows, "same_as_copies": all(r["same"] for r in rows),
              "same_as_s5_reused_record": all(r["rebuilt_sha256"] == rec_sha.get(r["file"]) for r in rows), "seconds": round(time.time() - t0, 1)}
    report["pass"] = report["same_as_copies"] and report["same_as_s5_reused_record"]
    (PKG / "audit" / "reuse_20260929_rebuild.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"9/29 결과표 재생성: 검사 {report['checks_passed']}, 10개 중 같은 SHA {sum(r['same'] for r in rows)}개, {report['seconds']}s")
    for r in rows:
        if not r["same"]:
            print("  다름:", r["file"])
    sys.exit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
