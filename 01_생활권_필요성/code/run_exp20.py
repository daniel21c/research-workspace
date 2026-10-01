# -*- coding: utf-8 -*-
"""exp20 일괄 실행: 최대 동시 실행 수를 지키며 설정 목록을 차례로 돌린다. 로그는 results/run1002/exp20_*.log.
사용: python run_exp20.py [동시실행=5] [시간제한초=5400]"""
import subprocess, sys, time, os
from pathlib import Path
PAR = int(sys.argv[1]) if len(sys.argv) > 1 else 5; TL = sys.argv[2] if len(sys.argv) > 2 else "5400"
L = Path(__file__).parent.parent / "results" / "run1002"; L.mkdir(parents=True, exist_ok=True)
jobs = []
for tau in ("0.01", "0.05"):
    for unit in ("공식LZ", "구", "동", "Leiden", "rand116_1", "rand116_2", "rand116_3"): jobs.append(("2025", unit, tau))
    for unit in ("공식LZ", "구", "동"): jobs.append(("2020", unit, tau))
env = dict(os.environ, PYTHONIOENCODING="utf-8")
run = []; status = open(L / "exp20.status", "a", encoding="utf-8")
while jobs or run:
    while jobs and len(run) < PAR:
        y, u, t = jobs.pop(0); log = open(L / f"exp20_{y}_{u}_{t}.log", "w", encoding="utf-8")
        p = subprocess.Popen([sys.executable, "-u", "exp20_bundle_floor.py", y, u, t, TL], cwd=Path(__file__).parent, stdout=log, stderr=subprocess.STDOUT, env=env)
        run.append((p, y, u, t, time.time())); status.write(f"START {y} {u} {t}\n"); status.flush()
    for item in list(run):
        p, y, u, t, ts = item
        if p.poll() is not None:
            run.remove(item); status.write(f"END({p.returncode}) {y} {u} {t} {time.time()-ts:.0f}s\n"); status.flush()
    time.sleep(10)
status.write("ALLDONE\n"); status.close()
