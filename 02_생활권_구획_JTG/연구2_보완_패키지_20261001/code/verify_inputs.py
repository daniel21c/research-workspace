# -*- coding: utf-8 -*-
"""inputs/ 의 파일 해시를 audit/source_manifest.json 의 기록과 대조한다. 공통 코어엔진이 없는 환경(별도 해제 폴더)에서도 동작한다."""
import hashlib, json, sys
from pathlib import Path
PKG = Path(__file__).resolve().parents[1]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def main():
    man = json.loads((PKG / "audit" / "source_manifest.json").read_text(encoding="utf-8"))
    rows, ok = [], True
    for r in man["inputs"]:
        if not r["used_in_calculation"]:
            continue
        got = sha(PKG / "inputs" / r["file"]); same = got == r["sha256"]; ok &= same
        rows.append({"file": r["file"], "sha256": got, "matches_manifest": same})
    print(json.dumps({"all_inputs_match": ok, "files": rows}, ensure_ascii=False, indent=1))
    return ok
if __name__ == "__main__":
    sys.exit(0 if main() else 1)
