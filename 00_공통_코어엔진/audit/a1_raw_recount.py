# -*- coding: utf-8 -*-
"""독립 재계산: 원자료 CSV → 서울 내부 OD (s02 코드를 쓰지 않음). 사용: python a1_raw_recount.py 2020 [파일번호...]"""
import sys, json, time, re
from pathlib import Path
import numpy as np, pandas as pd
import pyarrow as pa, pyarrow.csv as pacsv, pyarrow.compute as pc

RAW = Path(r"D:\Research\0_RAW\2401-2406_SEOUL_MOVING_CSV")
OUT = Path(__file__).resolve().parents[1] / "output" / "audit_20260925" / "recount"   # 원자료 재집계 (약 5GB → 수백 MB)
OUT.mkdir(exist_ok=True)
year = sys.argv[1]
only = [int(x) for x in sys.argv[2:]] or None
files = sorted((RAW / f"생활이동_행정동_{year}01").glob("*.csv"))
assert len(files) == 24, len(files)
COLS = ["ym", "wd", "arr", "O", "D", "sex", "age", "typ", "tmin", "flow"]

for i, f in enumerate(files):
    if only is not None and i not in only:
        continue
    outp = OUT / f"{year}_{i:02d}.parquet"
    if outp.exists() and only is None:
        continue
    t0 = time.time()
    rd = pacsv.open_csv(f, read_options=pacsv.ReadOptions(encoding="cp949", block_size=1 << 26, skip_rows=1, column_names=COLS),
                        convert_options=pacsv.ConvertOptions(column_types={c: pa.string() for c in COLS}, strings_can_be_null=False))
    st = dict(file=f.name, rows=0, rows_seoul=0, masked=0, other_nonnum=0, other_examples=[], arr_vals=set(), ym_vals=set(),
              typ_vals=set(), code_len_bad=0, flow_neg=0)
    parts = []
    for b in rd:
        t = pa.Table.from_batches([b])
        st["rows"] += t.num_rows
        O = pc.utf8_trim_whitespace(t["O"]); D = pc.utf8_trim_whitespace(t["D"])
        keep = pc.and_(pc.starts_with(O, "11"), pc.starts_with(D, "11"))
        t = t.filter(keep); O = O.filter(keep); D = D.filter(keep)
        st["rows_seoul"] += t.num_rows
        df = pd.DataFrame({"arr": t["arr"].to_numpy(zero_copy_only=False), "typ": t["typ"].to_numpy(zero_copy_only=False),
                           "wd": t["wd"].to_numpy(zero_copy_only=False),
                           "O": O.to_numpy(zero_copy_only=False), "D": D.to_numpy(zero_copy_only=False),
                           "flow_s": pc.utf8_trim_whitespace(t["flow"]).to_numpy(zero_copy_only=False),
                           "ym": t["ym"].to_numpy(zero_copy_only=False)})
        st["arr_vals"] |= set(df["arr"].unique()); st["ym_vals"] |= set(df["ym"].unique()); st["typ_vals"] |= set(df["typ"].unique())
        st["code_len_bad"] += int(((df["O"].str.len() != 7) | (df["D"].str.len() != 7)).sum())
        m = df["flow_s"] == "*"
        num = pd.to_numeric(df["flow_s"], errors="coerce")
        bad = num.isna() & ~m
        st["masked"] += int(m.sum()); st["other_nonnum"] += int(bad.sum())
        if bad.any() and len(st["other_examples"]) < 5:
            st["other_examples"] += list(df.loc[bad, "flow_s"].unique()[:5])
        st["flow_neg"] += int((num < 0).sum())
        df["flow"] = num.fillna(0.0); df["n_masked"] = m.astype(np.int64); df["n_rows"] = np.int64(1)
        df["O"] = df["O"].astype(np.int64); df["D"] = df["D"].astype(np.int64); df["arr"] = df["arr"].astype(np.int64)
        parts.append(df.groupby(["wd", "arr", "typ", "O", "D"], sort=False)[["flow", "n_masked", "n_rows"]].sum().reset_index())
    agg = pd.concat(parts).groupby(["wd", "arr", "typ", "O", "D"], sort=False)[["flow", "n_masked", "n_rows"]].sum().reset_index()
    agg.to_parquet(outp, index=False)
    for k in ("arr_vals", "ym_vals", "typ_vals"):
        st[k] = sorted(st[k])
    st["seconds"] = round(time.time() - t0, 1)
    (OUT / f"{year}_{i:02d}.json").write_text(json.dumps(st, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(st, ensure_ascii=False, default=str), flush=True)
