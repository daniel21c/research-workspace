# -*- coding: utf-8 -*-
"""결과표에서 빈 집합 시설(생활체육10분 = 체육시설업, facility-v1.4에서 격자 0개) 값을 지운다(2026-10-02 검증 S3-4).
r1lib FACSETS·DIAG_SETS와 exp3 LOSS_SETS에서는 이미 뺐으므로, exp2·exp3을 다시 돌리면 같은 표가 나온다. 다시 돌리는 대신 이 행·열만 지운다(다른 값은 그대로).
실행: python clean_empty_sets.py"""
import pandas as pd
from r1lib import OUT as RES
BAD = "생활체육10분"
for f in ("표4.1-2_은폐_H.csv", "표4.1-2_은폐_H곡선.csv"):
    d = pd.read_csv(RES / f); n = len(d); d = d[d["시설"] != BAD]; d.to_csv(RES / f, index=False, encoding="utf-8-sig"); print(f, n, "->", len(d))
f = "표4.1-3_크기축_구획별.csv"; d = pd.read_csv(RES / f); cols = [c for c in d.columns if BAD in c]
d.drop(columns=cols).to_csv(RES / f, index=False, encoding="utf-8-sig"); print(f, "drop", cols)
f = RES / "표4.1-2_은폐_H.md"; L = f.read_text(encoding="utf-8").splitlines(); K = [l for l in L if f"| {BAD} |" not in l]
f.write_text("\n".join(K) + "\n", encoding="utf-8"); print(f.name, len(L), "->", len(K))
