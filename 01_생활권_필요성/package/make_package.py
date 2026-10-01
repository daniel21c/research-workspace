# -*- coding: utf-8 -*-
"""연구1 공동연구자 패키지(Cities 확정본, 2026-10-02). 실행: 허브 루트에서 python 01_생활권_필요성/package/make_package.py
만든 뒤 새 폴더에 풀어 자체 점검(해시 대조, 코드 컴파일, 원고 docx 재생성)을 하고 package_selfcheck.json을 쓴다."""
import os, zipfile, hashlib, csv, io, json, shutil, subprocess, sys, tempfile, py_compile, collections
root = r"D:\Research\00_박사논문_연구체계"; os.chdir(root)
R1 = "01_생활권_필요성"
NAME = "01_생활권_필요성_Cities확정본_공동연구자패키지_20261002.zip"
out = f"{R1}/package/{NAME}"
files = []
def add_tree(d, skip=()):
    for dp, dns, fns in os.walk(d):
        rel = dp.replace("\\", "/")
        dns[:] = [x for x in dns if x != "__pycache__" and not any((rel + "/" + x).startswith(s) for s in skip)]
        for f in fns:
            if f.endswith((".pyc", ".zip")): continue
            files.append(os.path.join(dp, f).replace("\\", "/"))
for f in os.listdir(R1):
    if os.path.isfile(f"{R1}/{f}") and f.endswith(".md"): files.append(f"{R1}/{f}")
for d in ["code", "manuscript", "보고_20261002", "검수기록"]: add_tree(f"{R1}/{d}")
add_tree(f"{R1}/results", skip=(f"{R1}/results/_logs/run0930/v4_synthetic/worlds", f"{R1}/results/_logs/run0930/v4_synthetic/compute_snapshot"))
add_tree("시설데이터 구축/시설데이터_패키지/부가층_v1.5후보_20261001")
files += [f"{R1}/package/README_패키지.md", f"{R1}/package/make_package.py", "README.md", "박사논문_연구설계.md", "데이터_배포목록.md", "공유_안내.md"]
files = sorted(set(files))
rows = [(f, os.path.getsize(f), hashlib.sha256(open(f, "rb").read()).hexdigest()) for f in files]
buf = io.StringIO(); w = csv.writer(buf); w.writerow(["path", "bytes", "sha256"]); w.writerows(rows)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files: z.write(f, f)
    z.writestr("패키지_목록.csv", "\ufeff" + buf.getvalue())
    z.writestr("README_패키지.md", open(f"{R1}/package/README_패키지.md", encoding="utf-8").read())
zsha = hashlib.sha256(open(out, "rb").read()).hexdigest()
# --- self-check in a fresh folder ---
tmp = tempfile.mkdtemp(prefix="r1pkg_")
with zipfile.ZipFile(out) as z: z.extractall(tmp)
mism = [f for f, b, h in rows if hashlib.sha256(open(os.path.join(tmp, f), "rb").read()).hexdigest() != h]
pys = [f for f in files if f.endswith(".py") and f.startswith(f"{R1}/code/")]
comp_err = []
for f in pys:
    try: py_compile.compile(os.path.join(tmp, f), doraise=True)
    except Exception as e: comp_err.append(f"{f}: {e}")
code_dir = os.path.join(tmp, R1, "code")
r = subprocess.run([sys.executable, "cities_docx.py"], cwd=code_dir, capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
wc_new = json.load(open(os.path.join(tmp, R1, "manuscript", "word_count.json"), encoding="utf-8")) if r.returncode == 0 else None
wc_old = json.load(open(f"{R1}/manuscript/word_count.json", encoding="utf-8"))
check = {"zip": NAME, "zip_sha256": zsha, "files": len(files), "raw_MB": round(sum(x[1] for x in rows) / 1e6, 1), "zip_MB": round(os.path.getsize(out) / 1e6, 1),
         "hash_mismatch_after_unzip": mism, "python_files_compiled": len(pys), "compile_errors": comp_err,
         "rebuild_docx_from_sources": {"returncode": r.returncode, "stderr_tail": r.stderr[-500:], "word_count_identical": wc_new == wc_old},
         "by_folder": dict(sorted(collections.Counter("/".join(f.split("/")[:2]) for f in files).items()))}
json.dump(check, open(f"{R1}/package/package_selfcheck.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
shutil.rmtree(tmp, ignore_errors=True)
shutil.copy2(out, f"{R1}/보고_20261002/{NAME}")
print(json.dumps({k: v for k, v in check.items() if k != "by_folder"}, ensure_ascii=False, indent=1))
