# -*- coding: utf-8 -*-
"""공동연구자용 ZIP을 만든다. 포함 파일의 SHA-256 목록(audit/package_manifest.json)을 먼저 쓰고, 중간 산출물은 제외한다.
산출: ../연구2_보완_패키지_20261001.zip, ../연구2_보완_패키지_20261001.zip.sha256"""
import hashlib, json, time, zipfile
from pathlib import Path
PKG = Path(__file__).resolve().parents[1]
ZIP = PKG.parent / f"{PKG.name}.zip"
SKIP_DIRS = {"__pycache__", "_partial", "2025_repro", "render", "_reference_copy", "progress"}
SKIP_SUFFIX = {".pyc"}

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def files():
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and not (set(p.relative_to(PKG).parts) & SKIP_DIRS) and p.suffix not in SKIP_SUFFIX and p.name != "package_manifest.json":
            yield p

def main():
    fl = list(files())
    man = {"created": time.strftime("%Y-%m-%dT%H:%M:%S"), "package": PKG.name,
           "files": [{"path": p.relative_to(PKG).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)} for p in fl]}
    (PKG / "audit" / "package_manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    fl.append(PKG / "audit" / "package_manifest.json")
    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in fl:
            z.write(p, Path(PKG.name) / p.relative_to(PKG))
    (ZIP.parent / (ZIP.name + ".sha256")).write_text(f"{sha(ZIP)}  {ZIP.name}\n", encoding="utf-8")
    print(f"ZIP {ZIP.name}: 파일 {len(fl)}개, {ZIP.stat().st_size / 1e6:.1f} MB, SHA-256 {sha(ZIP)[:16]}…")

if __name__ == "__main__":
    main()
