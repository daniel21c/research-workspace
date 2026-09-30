# -*- coding: utf-8 -*-
"""
k21 — 원자료 무결성 전수 검증 (원자료 CSV → 배포 OD)

1. 원자료 시간대 CSV 48개(2020·2025 각 24개)의 SHA-256을 모두 다시 계산해 od_summary_{y}01.json의 기록과 대조한다.
2. 배포 OD(od_full·od_daily parquet)의 SHA-256을 od_summary 기록과, 코어 배포본 전체를 manifest.json과 대조한다.
3. 코어엔진 s02(pandas)와 다른 방식(DuckDB SQL, 열 위치로 읽기)으로 원자료에서 od_daily를 처음부터 다시 만들고
   배포본과 행 단위로 비교한다(통행량·행 수·'*' 행 수).
결과: results/integrity/raw_integrity.json. 원자료가 없는 환경(공동연구자 패키지)에서는 1·3을 건너뛴다.

원자료 위치: 환경변수 SEOUL_FLOW_RAW_DIR 또는 D:\\Research\\0_RAW\\2401-2406_SEOUL_MOVING_CSV
"""
import hashlib, json, os, sys, time
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

RAW = Path(os.environ.get("SEOUL_FLOW_RAW_DIR", r"D:\Research\0_RAW\2401-2406_SEOUL_MOVING_CSV"))
OUT = C.ROOT / "output" / "tables" / "integrity"
OUT.mkdir(parents=True, exist_ok=True)
H0, H1 = 9, 20                      # 도착시간 09~20시(=09:00~20:59), 코어 config FLOW_ARRIVAL_HOURS
EXCL = ("HW", "WH")                 # 코어 config FLOW_EXCLUDE_TYPES


def sha256(p: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def check_raw_hashes(year: str, summ: dict) -> dict:
    folder = RAW / f"생활이동_행정동_{year}01"
    files = sorted(folder.glob("*.csv"))
    rec = summ["files"]
    res = {"folder_files": len(files), "summary_files": len(rec), "match": 0, "mismatch": [], "missing": [], "extra": []}
    names = {f.name for f in files}
    res["missing"] = sorted(set(rec) - names)
    res["extra"] = sorted(names - set(rec))
    for f in files:
        if f.name not in rec:
            continue
        if sha256(f) == rec[f.name]["sha256"]:
            res["match"] += 1
        else:
            res["mismatch"].append(f.name)
    return res


def rebuild_daily(year: str) -> tuple[pd.DataFrame, dict]:
    """열 위치로 읽는다(cp949 머리글·요일은 쓰지 않으므로 latin-1로 읽어도 숫자·코드 열은 그대로다).
    머리글 줄만 CRLF, 자료 줄은 LF라 자동 탐지·병렬 읽기를 끄고 구분자를 지정한다."""
    glob = str(RAW / f"생활이동_행정동_{year}01" / "*.csv").replace("\\", "/")
    con = duckdb.connect()
    con.execute("PRAGMA threads=16")
    src = (f"read_csv('{glob}', header=false, skip=1, auto_detect=false, delim=',', quote='\"', strict_mode=false, parallel=false, encoding='latin-1', "
           f"columns={{'ym':'VARCHAR','wd':'VARCHAR','hr':'VARCHAR','o':'VARCHAR','d':'VARCHAR','sex':'VARCHAR',"
           f"'age':'VARCHAR','typ':'VARCHAR','mins':'VARCHAR','flow':'VARCHAR'}}, filename=true)")
    con.execute(f"""
        CREATE TEMP TABLE s AS
        SELECT filename, CAST(o AS INTEGER) o, CAST(d AS INTEGER) d, CAST(hr AS INTEGER) hr, typ,
               TRY_CAST(flow AS DOUBLE) f
        FROM {src}
        WHERE CAST(o AS INTEGER) // 100000 = 11 AND CAST(d AS INTEGER) // 100000 = 11
    """)
    stats = {
        "rows_total_csv": con.execute(f"SELECT count(*) FROM {src}").fetchone()[0],
        "rows_seoul_internal": con.execute("SELECT count(*) FROM s").fetchone()[0],
        "rows_masked_seoul": con.execute("SELECT count(*) FROM s WHERE f IS NULL").fetchone()[0],
        "flow_seoul_internal_all_hours": con.execute("SELECT sum(coalesce(f,0)) FROM s").fetchone()[0],
    }
    daily = con.execute(f"""
        SELECT o AS dong_O, d AS dong_D, sum(coalesce(f,0)) AS flow, count(*) AS n_rows,
               sum(CASE WHEN f IS NULL THEN 1 ELSE 0 END) AS n_masked
        FROM s WHERE hr BETWEEN {H0} AND {H1} AND typ NOT IN {EXCL}
        GROUP BY 1,2 ORDER BY 1,2
    """).df()
    con.close()
    return daily, stats


def compare_daily(new: pd.DataFrame, old: pd.DataFrame) -> dict:
    m = new.merge(old, on=["dong_O", "dong_D"], how="outer", suffixes=("_new", "_rel"), indicator=True)
    both = m[m["_merge"] == "both"]
    return {
        "pairs_rebuilt": int(len(new)), "pairs_release": int(len(old)),
        "only_rebuilt": int((m["_merge"] == "left_only").sum()), "only_release": int((m["_merge"] == "right_only").sum()),
        "flow_max_abs_diff": float((both["flow_new"] - both["flow_rel"]).abs().max()),
        "flow_total_rebuilt": float(new["flow"].sum()), "flow_total_release": float(old["flow"].sum()),
        "n_rows_equal": bool((both["n_rows_new"] == both["n_rows_rel"]).all()),
        "n_masked_equal": bool((both["n_masked_new"] == both["n_masked_rel"]).all()),
    }


def main():
    t0 = time.time()
    res = {"raw_dir": str(RAW), "raw_available": RAW.exists()}
    # 2) 배포본 해시
    man = json.loads(C.MANIFEST.read_text(encoding="utf-8"))
    ent = man.get("files", man)
    rel = {"checked": 0, "match": 0, "mismatch": []}
    items = ent.items() if isinstance(ent, dict) else [(e.get("path") or e.get("file"), e) for e in ent]
    for name, e in items:
        h = e.get("sha256") if isinstance(e, dict) else e
        p = C.CORE_DATA / name
        if not h or not p.exists():
            continue
        rel["checked"] += 1
        if sha256(p) == h:
            rel["match"] += 1
        else:
            rel["mismatch"].append(name)
    res["release_manifest"] = rel
    for y in C.YEARS:
        summ = json.loads(C.od_summary(y).read_text(encoding="utf-8"))
        r = {"od_outputs": {k: sha256(C.CORE_DATA / "od" / k) == v for k, v in summ["outputs"].items()
                            if (C.CORE_DATA / "od" / k).exists()}}
        if res["raw_available"]:
            r["raw_hash"] = check_raw_hashes(y, summ)
            print(f"[{y}] 원자료 해시 {r['raw_hash']['match']}/{r['raw_hash']['summary_files']} 일치", flush=True)
            daily, st = rebuild_daily(y)
            r["rebuild_stats"] = {k: {"rebuilt": v, "summary": summ[k],
                                      "equal": abs(v - summ[k]) < (1e-6 * max(1, abs(summ[k])))} for k, v in st.items()}
            old = pd.read_parquet(C.od_daily(y))
            r["rebuild_daily"] = compare_daily(daily, old)
            print(f"[{y}] 재구성 od_daily: {json.dumps(r['rebuild_daily'], ensure_ascii=False)}", flush=True)
        res[y] = r
    res["seconds"] = round(time.time() - t0, 1)
    ok = rel["match"] == rel["checked"] and all(all(res[y]["od_outputs"].values()) for y in C.YEARS)
    if res["raw_available"]:
        for y in C.YEARS:
            rh, rd = res[y]["raw_hash"], res[y]["rebuild_daily"]
            ok &= rh["match"] == rh["summary_files"] == 24 and not rh["missing"] and not rh["extra"]
            ok &= all(v["equal"] for v in res[y]["rebuild_stats"].values())
            ok &= rd["only_rebuilt"] == rd["only_release"] == 0 and rd["flow_max_abs_diff"] < 1e-6
            ok &= rd["n_rows_equal"] and rd["n_masked_equal"]
    res["all_pass"] = bool(ok)
    (OUT / "raw_integrity.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("전체 통과" if ok else "불일치 있음", f"({res['seconds']}s)")


if __name__ == "__main__":
    main()
