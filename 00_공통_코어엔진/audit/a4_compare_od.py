# -*- coding: utf-8 -*-
"""원자료 독립 재계산(a1) vs s02 산출물(od_full, od_daily, od_summary)"""
import json
from pathlib import Path
import numpy as np, pandas as pd

A = Path(__file__).resolve().parents[1] / "output" / "audit_20260925" / "recount"
D = Path(__file__).resolve().parents[1] / "data" / "od"
K = ["wd", "arr", "typ", "O", "D"]
for year in ("2020", "2025"):
    st = [json.loads((A / f"{year}_{i:02d}.json").read_text(encoding="utf-8")) for i in range(24)]
    print(f"== {year}")
    print(" raw rows", sum(s["rows"] for s in st), "| seoul rows", sum(s["rows_seoul"] for s in st), "| masked", sum(s["masked"] for s in st),
          "| other non-numeric", sum(s["other_nonnum"] for s in st), "| bad code len", sum(s["code_len_bad"] for s in st), "| negative", sum(s["flow_neg"] for s in st))
    print(" arrival hour per file:", [s["arr_vals"] for s in st] == [[f"{h:02d}"] for h in range(24)] or [s["arr_vals"] for s in st])
    print(" ym:", sorted({v for s in st for v in s["ym_vals"]}), "| types:", sorted({v for s in st for v in s["typ_vals"]}))
    a = pd.concat([pd.read_parquet(A / f"{year}_{i:02d}.parquet") for i in range(24)], ignore_index=True)
    a = a.groupby(K, sort=False)[["flow", "n_masked", "n_rows"]].sum().reset_index()
    f = pd.read_parquet(D / f"od_full_{year}01.parquet"); f.columns = ["wd", "arr", "typ", "O", "D", "flow", "n_rows", "n_masked"]
    for c in ("wd", "typ"): f[c] = f[c].astype(str)
    for c in ("arr", "O", "D"): f[c] = f[c].astype(np.int64)
    m = a.merge(f, on=K, how="outer", suffixes=("_a", "_s"), indicator=True)
    print(" od_full cells: mine", len(a), "s02", len(f), m["_merge"].value_counts().to_dict())
    for c in ("flow", "n_rows", "n_masked"):
        print(f"  {c}: max|diff| {(m[c+'_a'].fillna(0)-m[c+'_s'].fillna(0)).abs().max():.3e}  sum mine {m[c+'_a'].sum():,.2f}  sum s02 {m[c+'_s'].sum():,.2f}")
    # od_daily 독립 파생
    keep = a.arr.between(9, 20) & ~a.typ.isin(["HW", "WH"])
    dmine = a[keep].groupby(["O", "D"])[["flow", "n_rows", "n_masked"]].sum().reset_index()
    d = pd.read_parquet(D / f"od_daily_{year}01.parquet"); d = d.rename(columns={"dong_O": "O", "dong_D": "D"})
    d["O"] = d.O.astype(np.int64); d["D"] = d.D.astype(np.int64)
    mm = dmine.merge(d, on=["O", "D"], how="outer", suffixes=("_a", "_s"), indicator=True)
    print(" od_daily pairs: mine", len(dmine), "s02", len(d), mm["_merge"].value_counts().to_dict())
    for c in ("flow", "n_rows", "n_masked"):
        print(f"  {c}: max|diff| {(mm[c+'_a'].fillna(0)-mm[c+'_s'].fillna(0)).abs().max():.3e}  sum mine {mm[c+'_a'].sum():,.2f}")
    print(" od_daily rows after filter (raw-row count):", int(dmine.n_rows.sum()), "| masked share of rows", round(dmine.n_masked.sum() / dmine.n_rows.sum(), 4))
    print(" dong codes in od_daily:", len(set(dmine.O) | set(dmine.D)))
    sm = json.loads((D / f"od_summary_{year}01.json").read_text(encoding="utf-8"))
    flat = {k: v for k, v in sm.items() if not isinstance(v, (dict, list))}
    print(" od_summary scalars:", flat)
