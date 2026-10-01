# -*- coding: utf-8 -*-
"""results/manifest.json: 결과 파일마다 생성 스크립트, 입력 파일 SHA-256, 데이터 판을 기록한다(2026-10-02 검증 S3-13).
- 생성 스크립트: code/*.py 안의 출력 파일명 문자열(f-string의 {…}는 임의 문자열)과 결과 파일명을 맞춰 찾는다.
- 입력: r1lib·bundlelib를 쓰는 스크립트는 모두 같은 입력 묶음(격자·보행 TTM·시설·부가층·경계·OD·무작위 구획용 인구 캐시)을 읽는다.
  그 밖의 결과 파일을 읽는 스크립트(claims_check, fig_manuscript 등)는 "results/ 안의 결과 파일"을 함께 적는다.
- exp20 실행 판(S3-8): 10-01 12:42 코드 수정(결과 행에 시간제한 필드 추가) 전후로 실행이 섞여 있다. 실행마다 판을 적는다.
실행: python build_manifest.py"""
import hashlib, json, re, datetime
from pathlib import Path
from r1lib import ROOT, PKG, OUT as RES
CODE = Path(__file__).parent

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def sha_dir(d):   # 폴더(파티션 parquet): 상대 경로와 각 파일 SHA를 이어 붙인 SHA
    h = hashlib.sha256()
    for p in sorted(d.rglob("*")):
        if p.is_file(): h.update(f"{p.relative_to(d).as_posix()}:{sha(p)}\n".encode())
    return h.hexdigest()

CORE = ROOT / "00_공통_코어엔진"; ADD = ROOT / "시설데이터 구축" / "시설데이터_패키지" / "부가층_v1.5후보_20261001"
INPUTS = {   # 키: (경로, 데이터 판)
    "grid100_master": (PKG / "입력/grid/grid100_master.parquet", "pop-grid-100m-v1 (= grid-master-100m-v1)"),
    "ttm100_2020": (PKG / "입력/ttm/ttm100_2020", "ttm-walk-v1"), "ttm100_2025": (PKG / "입력/ttm/ttm100_2025", "ttm-walk-v1"),
    "facility_units": (PKG / "입력/facility/facility_2020_2025_units.parquet", "facility-v1.4"),
    **{f"addon_{p.stem}": (p, "부가층 v1.5 후보 20261001(배포목록 미등록, S3-1)") for p in sorted(ADD.glob("부가층_*.parquet"))},
    "dong424_gpkg": (CORE / "data/seoul_dong_424_dissolved.gpkg", "boundary-v2-dong"),
    "dong_to_lz116": (CORE / "data/dong_to_official_livingzone_mapping_424.csv", "boundary-v2-dong"),
    "dong_to_leiden_2020": (CORE / "data/dong_to_leiden_2020_mapping_424.csv", "boundary-v2-leiden"),
    "dong_to_leiden_2025": (CORE / "data/dong_to_leiden_2025_mapping_424.csv", "boundary-v2-leiden"),
    "od_daily_202001": (CORE / "data/od/od_daily_202001.parquet", "od-daily-v1"), "od_daily_202501": (CORE / "data/od/od_daily_202501.parquet", "od-daily-v1"),
    "pop_dong424_2020_cache": (CORE / "output/exploration/_cache/pop_dong424_2020.csv", "코어 캐시(SGIS 행정구역 총인구, 미등록; 무작위 구획 인구 균형용, S3-7)"),
    "pop_dong424_2025_cache": (CORE / "output/exploration/_cache/pop_dong424_2025.csv", "코어 캐시(SGIS 행정구역 총인구, 미등록; 무작위 구획 인구 균형용, S3-7)"),
}
inputs = {}
for k, (p, tag) in INPUTS.items():
    inputs[k] = {"path": p.relative_to(ROOT).as_posix(), "data_version": tag, "sha256": (sha_dir(p) if p.is_dir() else sha(p)) if p.exists() else None,
                 "kind": "dir(파일별 SHA의 SHA)" if p.is_dir() else "file"}

# 스크립트별 출력 파일명 패턴
pat = {}
for py in sorted(CODE.glob("*.py")):
    if py.name == "build_manifest.py": continue
    # 쓰기 호출이 있는 줄의 파일명만 본다(읽기만 하는 스크립트는 생성 스크립트가 아니다). 변수에 담아 쓰는 경우를 위해 f = OUT / "…" 대입 줄도 본다
    wl = [l for l in py.read_text(encoding="utf-8").splitlines()
          if re.search(r"to_csv\(|json\.dump\(|write_text\(|savefig\(|to_parquet\(|open\([^)]*[\"']w[\"']|^\s*\w+ = (OUT|RES) / f?\"", l)]
    for s in re.findall(r'f?"([^"\n]+\.(?:csv|json|md|png|pdf|parquet))"', "\n".join(wl)):
        name = s.split("/")[-1]
        if len(re.findall(r"[가-힣A-Za-z]", re.sub(r"\{[^}]*\}", "", name.rsplit(".", 1)[0]))) < 3: continue   # "{tag}.csv" 같은 빈 패턴 제외
        rx = "^" + re.sub(r"\\\{[^}]*\\\}", ".*", re.escape(name)) + "$"
        pat.setdefault(rx, set()).add(py.name)
uses_engine = {py.name for py in CODE.glob("*.py") if re.search(r"^from (r1lib|bundlelib) import|^import (r1lib|bundlelib)", py.read_text(encoding="utf-8"), re.M)}
reads_results = {py.name for py in CODE.glob("*.py") if re.search(r"read_csv\(\s*(RES|OUT)|json\.load\(open\(\s*(RES|OUT)|load\(f\"exp", py.read_text(encoding="utf-8"))}

# exp20 실행 판(S3-8): 로그에 "시간제한" 필드가 있으면 수정 후(B), 없으면 수정 전(A)
exp20 = {}
for lg in sorted((RES / "_logs" / "run1002").glob("exp20_*.log")):
    if lg.name == "exp20_runner.log": continue
    t = lg.read_text(encoding="utf-8", errors="ignore")
    exp20[lg.stem] = {"code_version": "B(10-01 12:42 수정 후: 결과 행에 시간제한·EXP20_TAG)" if "시간제한" in t else "A(10-01 12:42 수정 전 시작)",
                      "log_mtime": datetime.datetime.fromtimestamp(lg.stat().st_mtime).isoformat(timespec="minutes")}

MANUAL = {"결과총람_20261002.md": "수작업 문서(결과 표 요약)", "표4.1-23_권역최저선_요약.md": "수작업 요약(표4.1-23_권역최저선_{2020,2025}.csv에서 옮김)"}
files = {}
for p in sorted(RES.iterdir()):
    if not p.is_file() or p.name == "manifest.json": continue
    scripts = sorted({s for rx, ss in pat.items() if re.match(rx, p.name) for s in ss} - {"claims_check.py"} | ({"claims_check.py"} if p.name == "claims_check.json" else set()))
    if p.name.startswith("표4.1-1_4단위비교행렬_"): scripts = ["exp1_matrix.py"]   # 파일명을 변수(name)에 담아 쓴다
    if p.name in MANUAL: scripts = [MANUAL[p.name]]
    ins = sorted(inputs) if any(s in uses_engine for s in scripts) else []
    rec = {"sha256": sha(p), "mtime": datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="minutes"), "scripts": scripts,
           "inputs": ins, "also_reads_results": any(s in reads_results for s in scripts),
           "data_versions": sorted({inputs[k]["data_version"] for k in ins})}
    m = re.match(r"exp20_picks_(\d{4})_(.+)_(0\.0\d)\.json$", p.name)
    if m:
        y, u, tau = m.groups(); key = f"exp20_long_{y}_{tau}" if u.endswith("_long") else f"exp20_{y}_{u}_{tau}"
        rec["exp20_run"] = exp20.get(key)
    files[p.name] = rec
man = {"generated": datetime.datetime.now().isoformat(timespec="minutes"), "note": "결과 파일 SHA·생성 스크립트·입력 SHA·데이터 판. 입력 SHA는 이 manifest를 만든 시점의 값이다(결과를 만든 시점의 입력과 같다는 확인은 감사 lineage와 v1.4 재실행 기록에 기댄다).",
       "inputs": inputs, "exp20_runs": exp20,
       "exp20_note": "exp20 24건은 코드 판 A·B가 섞여 있다. 두 판의 차이는 결과 행 필드(시간제한·EXP20_TAG)뿐이고, 검증 세션이 저장 입지를 다시 평가해 표4.1-23과 일치함을 확인했다(2026-10-02). 다시 풀지 않았다.",
       "files": files, "unmatched": sorted(k for k, v in files.items() if not v["scripts"])}
json.dump(man, open(RES / "manifest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(files), "files;", len(man["unmatched"]), "without script:", man["unmatched"][:40])
