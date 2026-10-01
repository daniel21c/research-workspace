# -*- coding: utf-8 -*-
"""S0 고정: 입력 파일의 SHA-256을 계산해 공통 배포 기록과 대조하고, 사본을 inputs/ 에 만든 뒤 audit/source_manifest.json 에 기록한다.

- 공통 코어엔진 data/ 는 읽기만 한다. 수정하지 않는다.
- 확인 3가지: (1) 값이 코어 data/manifest.json(또는 od_summary)의 해시와 같다,
              (2) 앞 16자가 데이터_배포목록.md 에 적혀 있다, (3) 9/29 재분석 패키지 inputs/ 사본과 같다.
- 하나라도 어긋나면 inputs/ 를 만들지 않고 멈춘다.
"""
from __future__ import annotations
import hashlib, json, platform, shutil, sys, datetime
from pathlib import Path
import importlib.metadata as md

PACKAGE = Path(__file__).resolve().parents[1]
HUB = PACKAGE.parents[1]                                   # 00_박사논문_연구체계
CORE = HUB / "00_공통_코어엔진"
ARCHIVE = HUB.parent / "_archive" / "연구2_정리_20261002"     # 2026-10-02 정리 때 이전 판(9/29 패키지·이전 설계)을 옮긴 곳
OLD_PKG = next((p for p in (HUB / "02_생활권_구획_JTG" / "연구2_재분석_패키지_20260929", ARCHIVE / "연구2_재분석_패키지_20260929") if p.exists()),
               ARCHIVE / "연구2_재분석_패키지_20260929")
DIST_LIST = HUB / "데이터_배포목록.md"

# (릴리스 ID, 코어 data/ 기준 상대경로, 계산 입력 여부)
FILES = [
    ("boundary-v2-dong", "seoul_dong_424_dissolved.gpkg", True),
    ("boundary-v2-dong", "dong_to_official_livingzone_mapping_424.csv", True),
    ("boundary-v2-leiden", "dong_to_leiden_2025_mapping_424.csv", True),
    ("boundary-v2-leiden", "seoul_boundaries_all.gpkg", True),
    ("od-daily-v1", "od/od_daily_202501.parquet", True),
    ("od-daily-v1", "od/od_summary_202501.json", False),    # 출처·건수 기록용, 수치 계산에는 쓰지 않음
    # 보조 입력(2026-10-01 추가): 2025 Leiden 정본을 만든 같은 실행의 지표표. 배포목록에 따로 등록된 파일이 아니라 코어 산출물이므로
    # 코어 기록 해시 대조는 없고, 사용 전에 s4_compare 가 정본 매핑에서 다시 계산한 Q·IFR 과 구별로 일치하는지 검증한다.
    ("boundary-v2-leiden (같은 실행의 지표표, 보조)", "../output/leiden/2025/metrics/leiden_metrics_2025.csv", True),
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    data = CORE / "data"
    core_manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    od_summary = json.loads((data / "od" / "od_summary_202501.json").read_text(encoding="utf-8"))
    expected = {k: v["sha256"] for k, v in core_manifest["files"].items()}
    expected["od_daily_202501.parquet"] = od_summary["outputs"]["od_daily_202501.parquet"]
    dist_text = DIST_LIST.read_text(encoding="utf-8").lower()

    rows, problems = [], []
    for release, rel, used in FILES:
        src = data / rel
        name = Path(rel).name
        got = sha(src)
        exp = expected.get(name)
        in_list = got[:16] in dist_text if exp else None
        old = OLD_PKG / "inputs" / name
        old_same = (sha(old) == got) if old.exists() else None
        if exp is not None and got != exp:
            problems.append(f"{name}: 코어 기록 해시와 다름")
        if exp is not None and not in_list:
            problems.append(f"{name}: 앞 16자가 데이터_배포목록.md 에 없음")
        if old_same is False:
            problems.append(f"{name}: 9/29 패키지 사본과 다름")
        rows.append({"release": release, "file": name, "source": str(src), "bytes": src.stat().st_size, "sha256": got,
                     "used_in_calculation": used, "core_recorded_sha256": exp, "matches_core_record": (got == exp) if exp else None,
                     "prefix16_in_distribution_list": in_list, "same_as_20260929_package_copy": old_same})
    if problems:
        print("중단:", *problems, sep="\n  ")
        sys.exit(1)

    (PACKAGE / "inputs").mkdir(exist_ok=True)
    for r in rows:
        if not r["used_in_calculation"]:
            continue
        dst = PACKAGE / "inputs" / r["file"]
        shutil.copyfile(r["source"], dst)
        assert sha(dst) == r["sha256"], f"복사본 해시 불일치: {dst}"

    code_files = {
        "core_s03_leiden_consensus.py": CORE / "scripts" / "s03_leiden_consensus.py",
        "core_config.py": CORE / "scripts" / "config.py",
        "package_20260929_analyze.py": OLD_PKG / "code" / "analyze.py",
        # S0 실행(2026-10-01) 때는 02 폴더의 연구설계.md(9/29판)·연구설계_재현판_20261001.md 였다. 지금은 아카이브의 보존본을 가리킨다.
        # 9/29판은 같은 해시의 보존본이다. 재현판은 S0 시점(1f696c04…) 보존본이 없어 그 뒤 v3 보존본(e02cb232…)을 가리킨다(audit/source_manifest.json 'reason').
        "design_20260929_연구설계.md": ARCHIVE / "설계_이전판" / "연구설계_R2-DESIGN-20260929-v2.md",
        "design_20261001_연구설계_재현판.md": ARCHIVE / "설계_이전판" / "연구설계_재현판_R2R-DESIGN-20261001-v3.md",
        "distribution_list": DIST_LIST,
    }
    seed_file = CORE / "output" / "leiden" / "2025" / "run_seed.json"
    info_file = CORE / "output" / "leiden" / "2025" / "run_info.json"
    run_info = json.loads(info_file.read_text(encoding="utf-8")) if info_file.exists() else {}
    manifest = {
        "stage": "S0",
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "design": "R2R-DESIGN-20261001-v3",
        "inputs": rows,
        "code_and_documents": {k: {"path": str(v), "sha256": sha(v)} for k, v in code_files.items() if v.exists()},
        "leiden_canonical_2025": {"base_seed": json.loads(seed_file.read_text(encoding="utf-8")).get("base_seed") if seed_file.exists() else None,
                                  "run_info_input_od": run_info.get("input_od"), "run_info_input_dong": run_info.get("input_dong"),
                                  "run_info_params": run_info.get("params")},
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                        **{p: md.version(p) for p in ("pandas", "numpy", "pyarrow", "geopandas", "shapely", "igraph", "leidenalg",
                                                      "networkx", "python-louvain", "scipy", "scikit-learn")}},
        "note": "공통 코어엔진은 읽기만 했다. inputs/ 는 계산에 쓰는 사본(6개)이다. 마지막 파일(Leiden 지표표)은 2026-10-01 S4 확장 때 추가했다.",
    }
    out = PACKAGE / "audit" / "source_manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"완료: 입력 {len(rows)}개 대조, 사본 {sum(r['used_in_calculation'] for r in rows)}개, 기록 {out}")
    for r in rows:
        print(f"  {r['sha256'][:16]}  core={r['matches_core_record']}  list={r['prefix16_in_distribution_list']}  old={r['same_as_20260929_package_copy']}  {r['file']}")


if __name__ == "__main__":
    main()
