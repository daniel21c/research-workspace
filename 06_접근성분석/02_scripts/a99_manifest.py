# -*- coding: utf-8 -*-
"""04_구축기록/manifest_sha256.csv 갱신 도구 (기존 행의 글자를 그대로 보존).

열: file,sha256,bytes,created,script,rows. 같은 file 행은 교체, 새 file 은 끝에 추가.
pandas 로 다시 쓰면 rows 열이 338915.0 처럼 바뀌므로 csv 모듈로 문자열 그대로 읽고 쓴다.

모듈 사용:  import a99_manifest as M; M.update([M.row(path, script='a06_engine.py', rows=123)])
명령 사용:  python a99_manifest.py --script a07_study3_outputs.py 03_output/tables/T5_*.csv ...
"""
import argparse, csv, datetime as dt, glob, hashlib, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a00_config as C  # noqa: E402

MF = C.REC / 'manifest_sha256.csv'
COLS = ['file', 'sha256', 'bytes', 'created', 'script', 'rows']


def sha256(p, buf=1 << 24):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(buf), b''):
            h.update(b)
    return h.hexdigest()


def rel(p):
    return str(Path(p).resolve().relative_to(C.ROOT.resolve())).replace('\\', '/')


def row(path, script='', rows='', created=None):
    p = Path(path)
    return {'file': rel(p), 'sha256': sha256(p), 'bytes': str(p.stat().st_size),
            'created': created or dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'script': script,
            'rows': '' if rows in ('', None) else str(int(rows))}


def read():
    if not MF.exists():
        return []
    with open(MF, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def update(new_rows):
    old = read()
    idx = {r['file']: i for i, r in enumerate(old)}
    for r in new_rows:
        r = {k: r.get(k, '') for k in COLS}
        if r['file'] in idx:
            old[idx[r['file']]] = r
        else:
            idx[r['file']] = len(old); old.append(r)
    with open(MF, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator='\n')
        w.writeheader(); w.writerows(old)
    return len(new_rows)


def count_rows(p):
    p = Path(p)
    if p.suffix == '.csv':
        with open(p, encoding='utf-8-sig') as f:
            return max(sum(1 for _ in f) - 1, 0)
    if p.suffix == '.parquet':
        import pyarrow.parquet as pq
        return pq.read_metadata(p).num_rows
    return ''


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--script', default='')
    ap.add_argument('paths', nargs='+')
    a = ap.parse_args()
    files = [Path(q) for pat in a.paths for q in sorted(glob.glob(pat))]
    n = update([row(p, a.script, count_rows(p)) for p in files if p.is_file()])
    print(f'manifest: {n}행 갱신/추가')
