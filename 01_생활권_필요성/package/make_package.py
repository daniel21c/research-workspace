import os, zipfile, hashlib, csv, io
root = r"D:\Research\00_박사논문_연구체계"
os.chdir(root)
R1 = "01_생활권_필요성"  # 실행: 허브 루트에서 python 01_생활권_필요성/package/make_package.py
out = f"{R1}/package/01_생활권_필요성_공동연구자검토본_20261002.zip"
files = []
def add_tree(d, skip_dirs=()):
    for dp, dns, fns in os.walk(d):
        rel = dp.replace("\\", "/")
        dns[:] = [x for x in dns if x != "__pycache__" and not any((rel + "/" + x).startswith(s) for s in skip_dirs)]
        for f in fns:
            if f.endswith((".pyc", ".pdf")): continue
            files.append(os.path.join(dp, f).replace("\\", "/"))
# 01 루트 md 전부(README·연구설계·작업기록·대응표·대조표)
for f in os.listdir(R1):
    p = f"{R1}/{f}"
    if os.path.isfile(p) and f.endswith(".md"):
        files.append(p)
for d in ["code", "manuscript", "검수기록", "보고_20261002"]:
    add_tree(f"{R1}/{d}")
for f in os.listdir(f"{R1}/results"):
    p = f"{R1}/results/{f}"
    if os.path.isfile(p): files.append(p)
add_tree(f"{R1}/results/run0930", skip_dirs=(f"{R1}/results/run0930/v4_synthetic/worlds", f"{R1}/results/run0930/v4_synthetic/compute_snapshot")); add_tree(f"{R1}/results/run1002")
add_tree("시설데이터 구축/시설데이터_패키지/부가층_v1.5후보_20261001")
files += [f"{R1}/package/README_패키지.md", f"{R1}/package/공동연구자_검토요청_20261002.md", "00_선행연구/pdf/2026_JassoChavez_sufficientarianism_accessibility_poverty.md",
          "README.md", "박사논문_연구설계.md", "데이터_배포목록.md", "공유_안내.md"]
files = sorted(set(files))
big = [(f, os.path.getsize(f)) for f in files if os.path.getsize(f) > 5_000_000]
rows = []
for f in files:
    b = open(f, "rb").read()
    rows.append((f, len(b), hashlib.sha256(b).hexdigest()))
buf = io.StringIO(); w = csv.writer(buf); w.writerow(["path", "bytes", "sha256"]); w.writerows(rows)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files: z.write(f, f)
    z.writestr("검토본_목록.csv", "\ufeff" + buf.getvalue())
    z.writestr("README_검토본.md", open(f"{R1}/package/README_패키지.md", encoding="utf-8").read()); z.writestr("GPTPro_검토프롬프트_2차.md", open(f"{R1}/검수기록/GPTPro_검토프롬프트_2차_20261002.md", encoding="utf-8").read())
tot = sum(r[1] for r in rows)
h = hashlib.sha256(open(out, "rb").read()).hexdigest()
print("files", len(files), "raw MB", round(tot/1e6, 1), "zip MB", round(os.path.getsize(out)/1e6, 1))
print("big>5MB", big)
print("sha256", h)
import collections
c = collections.Counter("/".join(f.split("/")[:3]) for f in files)
for k, v in sorted(c.items()): print(v, k)
