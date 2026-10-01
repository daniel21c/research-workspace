# -*- coding: utf-8 -*-
"""S0 보완(2026-10-02): audit/source_manifest.json 에 두 가지를 더한다. S0 때 적은 값(해시·시각)은 바꾸지 않는다.

1) 입력 추가: 9/29 결과표(results/reused_20260929/)를 이 패키지에서 다시 만들 수 있도록(code/reuse_20260929/rebuild_reused.py)
   2020년 1월 OD와 Leiden 2020 매핑을 inputs/ 에 복사한다. 확인은 S0와 같다:
   코어 기록 해시(manifest.json·od_summary) 일치, 앞 16자가 데이터_배포목록.md 에 있음, 9/29 패키지가 쓴 입력 해시와 일치.
2) 문서 경로 정정: S0 때 02 폴더에 있던 설계 문서·9/29 코드는 2026-10-02 정리 때 아카이브로 옮겼다.
   같은 해시의 보존본이 있으면 그 경로를 적고, 없으면 '보존본 없음'과 이유를 적는다.

허브의 공통 코어엔진은 읽기만 한다. 허브가 있는 환경에서만 실행된다(별도 해제 폴더에서는 code/verify_inputs.py).
"""
from __future__ import annotations
import hashlib, json, shutil, sys, datetime
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
HUB = PACKAGE.parents[1]
CORE = HUB / "00_공통_코어엔진"
ARCHIVE = HUB.parent / "_archive" / "연구2_정리_20261002"
DIST_LIST = HUB / "데이터_배포목록.md"
MAN = PACKAGE / "audit" / "source_manifest.json"
# 9/29 패키지 audit/source_manifest.json 의 'analysis input' 기록(그 패키지가 계산에 쓴 해시)
USED_0929 = {"od_daily_202001.parquet": "4533810ebd4c68fd", "dong_to_leiden_2020_mapping_424.csv": "d03ba1a05a17e875"}
ADD = [("od-daily-v1", "od/od_daily_202001.parquet"), ("boundary-v2-leiden", "dong_to_leiden_2020_mapping_424.csv")]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    man = json.loads(MAN.read_text(encoding="utf-8"))
    data = CORE / "data"
    core = {k: v["sha256"] for k, v in json.loads((data / "manifest.json").read_text(encoding="utf-8"))["files"].items()}
    core["od_daily_202001.parquet"] = json.loads((data / "od" / "od_summary_202001.json").read_text(encoding="utf-8"))["outputs"]["od_daily_202001.parquet"]
    dist = DIST_LIST.read_text(encoding="utf-8").lower()
    have = {r["file"] for r in man["inputs"]}
    for release, rel in ADD:
        src = data / rel; name = Path(rel).name
        got = sha(src); exp = core.get(name)
        checks = {"matches_core_record": got == exp, "prefix16_in_distribution_list": got[:16] in dist, "same_as_20260929_analysis_input": got[:16] == USED_0929[name]}
        if not all(checks.values()):
            print("중단:", name, checks); sys.exit(1)
        dst = PACKAGE / "inputs" / name
        shutil.copyfile(src, dst); assert sha(dst) == got
        if name not in have:
            man["inputs"].append({"release": release, "file": name, "source": str(src), "bytes": src.stat().st_size, "sha256": got,
                                  "used_in_calculation": True, "core_recorded_sha256": exp, **checks,
                                  "added": "2026-10-02 (S0 보완). 9/29 결과표 재생성(code/reuse_20260929/rebuild_reused.py)에만 쓴다"})
        print(f"  입력 {got[:16]}  {name}  {checks}")

    docs = man["code_and_documents"]
    docs["package_20260929_analyze.py"].update({
        "path_at_S0": docs["package_20260929_analyze.py"].get("path_at_S0", docs["package_20260929_analyze.py"]["path"]),
        "path": str(ARCHIVE / "연구2_재분석_패키지_20260929" / "code" / "analyze.py"),
        "package_copy": "code/reuse_20260929/analyze_20260929.py (같은 해시)"})
    docs["design_20260929_연구설계.md"].update({
        "path_at_S0": docs["design_20260929_연구설계.md"].get("path_at_S0", docs["design_20260929_연구설계.md"]["path"]),
        "path": str(ARCHIVE / "설계_이전판" / "연구설계_R2-DESIGN-20260929-v2.md"),
        "note": "S0 때 02 폴더의 연구설계.md(9/29 v2). 그 자리는 지금 v4다. 같은 해시의 보존본 경로로 고쳤다"})
    d3 = docs["design_20261001_연구설계_재현판.md"]
    d3.update({"path_at_S0": d3.get("path_at_S0", d3["path"]), "path": None, "preserved_copy": "보존본 없음",
               "reason": ("S0(2026-10-01 23:13) 뒤에 같은 파일(v3)을 계속 고쳐 쓰면서 S0 시점 내용을 따로 저장하지 않았다. "
                          "아카이브에는 그 뒤 판 두 개만 있다: 설계_이전판/연구설계_재현판_R2R-DESIGN-20261001-v3.md(e02cb232…, 10/02 v3 보존본), "
                          "설계_이전판/연구설계_재현판_20261001_대체표시판.md(da7c44c8…). 둘 다 이 해시와 다르다. 계산 입력이 아닌 설계 문서라 결과에는 영향이 없다")})
    dl = docs["distribution_list"]
    if sha(ARCHIVE / "연구2_재분석_패키지_20260929" / "references" / "shared_contract" / "데이터_배포목록.md") == dl["sha256"]:
        dl.update({"preserved_copy": str(ARCHIVE / "연구2_재분석_패키지_20260929" / "references" / "shared_contract" / "데이터_배포목록.md"),
                   "note": "허브 데이터_배포목록.md 는 그 뒤 갱신될 수 있다. S0 시점과 같은 해시의 사본이 9/29 패키지 references 에 있다"})
    man["amended"] = {"date": datetime.datetime.now().isoformat(timespec="seconds"), "script": "code/s0b_amend_20261002.py",
                      "what": "2020년 입력 2개 추가(9/29 결과표 재생성용), 아카이브로 옮긴 문서의 경로 정정. S0 때 적은 해시·시각은 그대로"}
    MAN.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print("완료:", MAN)


if __name__ == "__main__":
    main()
