# -*- coding: utf-8 -*-
"""
s02_build_od_tables.py — 서울 생활이동 원자료 CSV → 동×동 OD 집계표
======================================================================
이전 방식(원자료 8천만 행을 3.7GB pkl로 통째 저장) 대신, 원자료를 한 번만 읽어
분석에 필요한 단위까지 줄인 집계표 두 개를 만든다. 이후 모든 계산은 이 표만 쓴다.

입력 (읽기 전용): config.raw_flow_folder(year) 의 시간대별 CSV 24개
  열: 대상연월, 요일, 도착시간, 출발 행정동 코드, 도착 행정동 코드, 성별, 나이, 이동유형, 평균 이동 시간(분), 이동인구(합)

처리 (파일 1개 = 도착시간 1개 단위로 처리하고 부분 결과를 저장 → 중단 후 재실행하면 이어서 함)
  1. 이동인구(합) '*' (3명 미만 비공개) → 0 (config.FLOW_MASKED_VALUE). '*' 행 수는 n_masked 로 따로 센다.
  2. 출발·도착 모두 서울(11xxxxx) 인 행만 남긴다.
  3. (요일, 도착시간, 이동유형, dong_O, dong_D) 로 합산 → od_full  (성별·나이만 접은 표. 필터를 바꿔 다시 쓸 수 있음)
  4. od_full 에서 도착시간 09~20, 이동유형 HW/WH 제외 → (dong_O, dong_D) 합산 → od_daily (구획·IFR 계산 입력)
  5. 동 코드가 정본 424개에 모두 포함되는지 확인.

출력 (data/od/)
  - od_full_{year}01.parquet   열: 요일, 도착시간, 이동유형, dong_O, dong_D, flow, n_rows, n_masked
  - od_daily_{year}01.parquet  열: dong_O, dong_D, flow, n_rows, n_masked
  - od_summary_{year}01.json   단계별 행 수·통행량, '*' 비율, 필터 조건, 파일별 해시
  - data/od/_parts/{year}/     시간대별 부분 집계 (재실행용)

실행:  python s02_build_od_tables.py --years 2020 2025
       python s02_build_od_tables.py --years 2020 --files 0 1 2   (시간대 파일 일부만; 나머지는 나중에)
       python s02_build_od_tables.py --years 2020 --merge-only   (부분 집계가 다 있을 때 합치기만)
"""
import sys, json, argparse, logging, time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("s02")

USECOLS = ["요일", "도착시간", "출발 행정동 코드", "도착 행정동 코드", "이동유형", "이동인구(합)"]
KEYS = ["요일", "도착시간", "이동유형", "dong_O", "dong_D"]


def list_csvs(year: str):
    folder = C.raw_flow_folder(year)
    files = sorted(folder.glob("*.csv"))
    if len(files) != 24:
        log.warning(f"[{year}] CSV 파일 수 {len(files)} (24개 예상): {folder}")
    return files


def aggregate_one_file(path: Path) -> tuple[pd.DataFrame, dict]:
    """시간대 CSV 1개 → (요일,도착시간,이동유형,dong_O,dong_D) 집계와 통계"""
    parts, st = [], {"rows_total": 0, "rows_seoul": 0, "rows_masked_seoul": 0, "flow_seoul": 0.0}
    reader = pd.read_csv(path, encoding=C.CSV_ENCODING, usecols=USECOLS, dtype=str,
                         chunksize=C.CSV_CHUNK_ROWS, engine="c")
    for ch in reader:
        st["rows_total"] += len(ch)
        o = pd.to_numeric(ch["출발 행정동 코드"], errors="coerce")
        d = pd.to_numeric(ch["도착 행정동 코드"], errors="coerce")
        seoul = (o // 100000 == C.FLOW_SEOUL_PREFIX) & (d // 100000 == C.FLOW_SEOUL_PREFIX)
        ch = ch[seoul].copy()
        if ch.empty:
            continue
        ch["dong_O"] = o[seoul].astype(np.int32).values
        ch["dong_D"] = d[seoul].astype(np.int32).values
        flow = pd.to_numeric(ch["이동인구(합)"], errors="coerce")
        masked = flow.isna()                       # '*' 등 숫자가 아닌 값
        ch["n_masked"] = masked.astype(np.int32)
        ch["flow"] = flow.fillna(C.FLOW_MASKED_VALUE).astype(np.float64)
        ch["n_rows"] = 1
        ch["도착시간"] = pd.to_numeric(ch["도착시간"], errors="coerce").astype(np.int8)
        st["rows_seoul"] += len(ch)
        st["rows_masked_seoul"] += int(masked.sum())
        st["flow_seoul"] += float(ch["flow"].sum())
        parts.append(ch.groupby(KEYS, sort=False)[["flow", "n_rows", "n_masked"]].sum().reset_index())
    if not parts:
        return pd.DataFrame(columns=KEYS + ["flow", "n_rows", "n_masked"]), st
    agg = pd.concat(parts, ignore_index=True).groupby(KEYS, sort=False)[["flow", "n_rows", "n_masked"]].sum().reset_index()
    return agg, st


def build_parts(year: str, file_idx=None) -> dict:
    files = list_csvs(year)
    part_dir = C.OD_DIR / "_parts" / year
    part_dir.mkdir(parents=True, exist_ok=True)
    stats_path = part_dir / "_file_stats.json"
    stats = json.loads(stats_path.read_text(encoding="utf-8")) if stats_path.exists() else {}
    todo = [(i, f) for i, f in enumerate(files) if file_idx is None or i in file_idx]
    for i, f in todo:
        out = part_dir / f"part_{i:02d}.parquet"
        if out.exists() and f.name in stats:
            log.info(f"[{year}] {f.name} 이미 처리됨, 건너뜀")
            continue
        t0 = time.time()
        agg, st = aggregate_one_file(f)
        agg.to_parquet(out, index=False)
        st.update({"file": f.name, "sha256": C.sha256_of(f), "n_groups": int(len(agg)), "seconds": round(time.time() - t0, 1)})
        stats[f.name] = st
        stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
        log.info(f"[{year}] {f.name}: 전체 {st['rows_total']:,}행 → 서울 {st['rows_seoul']:,}행, "
                 f"'*' {st['rows_masked_seoul']:,}행, 집계 {len(agg):,}행 ({st['seconds']}s)")
    return stats


def merge_parts(year: str, stats: dict):
    files = list_csvs(year)
    part_dir = C.OD_DIR / "_parts" / year
    missing = [f.name for i, f in enumerate(files) if not (part_dir / f"part_{i:02d}.parquet").exists()]
    if missing:
        raise SystemExit(f"[{year}] 부분 집계가 없는 파일 {len(missing)}개: {missing[:3]} ... 먼저 처리하세요.")
    # 부분 집계(시간대 1개 = 파일 1개)는 키가 서로 겹치지 않으므로 이어 붙이기만 하면 od_full 이다.
    # 메모리를 아끼기 위해 파일 하나씩 읽어 parquet 에 이어 쓰고, 일상통행 필터 집계도 누적한다.
    import pyarrow as pa, pyarrow.parquet as pq
    h0, h1 = C.FLOW_ARRIVAL_HOURS
    writer, daily_parts, codes, types = None, [], set(), set()
    flow_all, rows_after, n_full_rows = 0.0, 0, 0
    for i in range(len(files)):
        p = pd.read_parquet(part_dir / f"part_{i:02d}.parquet")
        p = p.astype({"요일": "string", "이동유형": "string", "도착시간": "int8", "dong_O": "int32", "dong_D": "int32",
                      "flow": "float64", "n_rows": "int64", "n_masked": "int64"})[KEYS + ["flow", "n_rows", "n_masked"]]
        tbl = pa.Table.from_pandas(p, preserve_index=False)
        if writer is None:
            writer = pq.ParquetWriter(C.od_full_path(year), tbl.schema)
        writer.write_table(tbl)
        n_full_rows += len(p)
        flow_all += float(p["flow"].sum())
        codes |= set(p["dong_O"].unique()) | set(p["dong_D"].unique())
        types |= set(p["이동유형"].unique())
        keep = p["도착시간"].between(h0, h1) & ~p["이동유형"].isin(C.FLOW_EXCLUDE_TYPES)
        if keep.any():
            rows_after += int(p.loc[keep, "n_rows"].sum())
            daily_parts.append(p[keep].groupby(["dong_O", "dong_D"], sort=False)[["flow", "n_rows", "n_masked"]].sum().reset_index())
        del p, tbl
    writer.close()
    daily = pd.concat(daily_parts, ignore_index=True).groupby(["dong_O", "dong_D"], sort=True)[["flow", "n_rows", "n_masked"]].sum().reset_index()
    daily.to_parquet(C.od_daily_path(year), index=False)

    # 동 코드 정본 대조
    dong_codes = set(pd.read_csv(C.DONG_LZ_MAP)["Dong"].astype(int)) if C.DONG_LZ_MAP.exists() else None
    unknown = sorted(int(c) for c in codes - dong_codes) if dong_codes else []
    if unknown:
        log.warning(f"[{year}] 정본 {C.N_DONG}개에 없는 동 코드 {len(unknown)}개: {unknown[:10]}")

    summary = {
        "year": year, "env": C.env_info(),
        "source_folder": str(C.raw_flow_folder(year)),
        "files": stats,
        "rows_total_csv": int(sum(s["rows_total"] for s in stats.values())),
        "rows_seoul_internal": int(sum(s["rows_seoul"] for s in stats.values())),
        "rows_masked_seoul": int(sum(s["rows_masked_seoul"] for s in stats.values())),
        "masked_share_of_seoul_rows": round(sum(s["rows_masked_seoul"] for s in stats.values()) / max(1, sum(s["rows_seoul"] for s in stats.values())), 4),
        "flow_seoul_internal_all_hours": flow_all,
        "n_od_full_rows": n_full_rows,
        "filter": {"arrival_hours": list(C.FLOW_ARRIVAL_HOURS), "exclude_types": list(C.FLOW_EXCLUDE_TYPES),
                   "masked_value": C.FLOW_MASKED_VALUE, "days": "all"},
        "rows_after_daily_filter": rows_after,
        "flow_after_daily_filter": float(daily["flow"].sum()),
        "flow_intra_dong_share": float(daily.loc[daily["dong_O"] == daily["dong_D"], "flow"].sum() / daily["flow"].sum()),
        "n_od_pairs_daily": int(len(daily)),
        "n_dong_codes_seen": len(codes), "unknown_dong_codes": unknown,
        "types_seen": sorted(str(t) for t in types),
        "outputs": {p.name: C.sha256_of(p) for p in (C.od_full_path(year), C.od_daily_path(year))},
    }
    C.od_summary_path(year).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"[{year}] od_full {n_full_rows:,}행, od_daily {len(daily):,}행 | 서울 내부 {summary['rows_seoul_internal']:,}행 "
             f"→ 필터 후 {summary['rows_after_daily_filter']:,}행, 통행량 {summary['flow_after_daily_filter']:,.0f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="+", default=list(C.YEARS))
    ap.add_argument("--files", nargs="*", type=int, default=None, help="처리할 시간대 파일 인덱스(0~23). 생략=전부")
    ap.add_argument("--merge-only", action="store_true")
    a = ap.parse_args()
    C.ensure_dirs()
    for y in a.years:
        part_dir = C.OD_DIR / "_parts" / y
        if a.merge_only:
            stats = json.loads((part_dir / "_file_stats.json").read_text(encoding="utf-8"))
        else:
            stats = build_parts(y, set(a.files) if a.files is not None else None)
        n_files = len(list_csvs(y))
        if a.files is None or a.merge_only or all((part_dir / f"part_{i:02d}.parquet").exists() for i in range(n_files)):
            merge_parts(y, stats)
        else:
            log.info(f"[{y}] 부분 집계만 저장. 모두 끝나면 --merge-only 로 합치세요.")


if __name__ == "__main__":
    main()
