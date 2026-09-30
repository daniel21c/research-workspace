# -*- coding: utf-8 -*-
"""
k23 — 확정본 분석(k13·k14·k25·k18) 재실행 재현성 확인

현재 output/tables/benchmark/의 결과를 기록해 두고 k13·k14·k25·k18을 다시 실행한 뒤 파일별로 비교한다.
csv는 바이트 단위, json은 실행 시간('seconds') 항목을 빼고 키를 정렬해 비교한다(정규화 비교).
출력: output/_repro_result_benchmark.json  {"비교파일": n, "달라진파일": [...]}
실행: python k23_repro_check.py   (약 30분)
"""
import hashlib, json, subprocess, sys, time, os
from pathlib import Path
import config as C

B = C.TAB / "benchmark"


def digest(p: Path) -> str:
    if p.suffix == ".json":
        d = json.loads(p.read_text(encoding="utf-8"))
        def strip(x):
            if isinstance(x, dict): return {k: strip(v) for k, v in x.items() if k != "seconds"}
            if isinstance(x, list): return [strip(v) for v in x]
            return x
        return hashlib.sha256(json.dumps(strip(d), ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    t0 = time.time()
    before = {p.name: digest(p) for p in sorted(B.glob("*.*"))}
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for s in ("k13_benchmark.py", "k14_reassign.py", "k25_change_story.py", "k18_v2_results.py"):   # k18 = 재배정 분할 검증(b8_verify)
        r = subprocess.run([sys.executable, s], cwd=C.HERE, env=env, capture_output=True, text=True, encoding="utf-8")
        if r.returncode: raise SystemExit(f"{s} 실패: {r.stderr[-400:]}")
    after = {p.name: digest(p) for p in sorted(B.glob("*.*"))}
    diff = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    R = {"생성": time.strftime("%Y-%m-%d %H:%M:%S"), "비교파일": len(after), "달라진파일": diff, "초": round(time.time() - t0)}
    (C.OUT / "_repro_result_benchmark.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(R, ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
