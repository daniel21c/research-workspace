# -*- coding: utf-8 -*-
"""실험 F: 116개 경계 효과의 강건성 — 귀무 3종(인구균형·동수균형·자유), 구별 부호검정, 조각 크기 이질성.
지표: IFR, 경계 제한 손실(도서관·문화·행정안전·유치원10분), 도서관 도달권이 걸치는 단위 수, H_auc(도서관)."""
import time
import numpy as np, pandas as pd
from r1lib import Year, OUT, md, X

R = 100; rng = np.random.default_rng(11)
rows, kurows = [], []; t0 = time.time()
FS = ["도서관", "문화", "행정안전", "유치원10분"]
for y in ("2020", "2025"):
    Yr = Year(y); pop = Yr.pop; ku_g = Yr.units["구"]; kuc = pd.factorize(Yr.M.ku)[1]
    r_none = {f: Yr.reach(f) for f in FS}; C = {f: Yr.cov(r_none[f]) for f in FS}
    def one(s, tag, rep):
        u = Yr.dong_series_to_units(s)
        row = {"year": y, "tag": tag, "rep": rep, "IFR": Yr.ifr(s)}
        den = np.bincount(u, pop); row["pop_cv"] = den[den > 0].std() / den[den > 0].mean()
        nd = s.groupby(s).size(); row["dong_cv"] = nd.std() / nd.mean()
        for f in FS:
            rb = Yr.reach(f, u); row[f"loss_{f}"] = C[f] - Yr.cov(rb)
            # 구별 손실
            lost = r_none[f] & ~rb
            kl = np.bincount(ku_g, pop * lost) / np.bincount(ku_g, pop)
            for i, kc in enumerate(kuc): kurows.append({"year": y, "tag": tag, "rep": rep, "ku": kc, "f": f, "loss": kl[i]})
        row["Hauc_도서관"] = Yr.H_curve(u, r_none["도서관"], C["도서관"]).mean()
        row["span_lib"] = Yr.catchment_spans(u, "도서관")
        # 구별 IFR
        od = Yr.od; a = s.reindex(od.dong_O).to_numpy(); b = s.reindex(od.dong_D).to_numpy(); same = a == b
        kuo = Yr.dong_gdf["Ku"].reindex(od.dong_O).to_numpy()
        for kc in kuc:
            m = kuo == kc; kurows.append({"year": y, "tag": tag, "rep": rep, "ku": kc, "f": "IFR", "loss": (od.flow.to_numpy()[m] * same[m]).sum() / od.flow.to_numpy()[m].sum()})
        rows.append(row)
    one(Yr.lz_map, "공식LZ", 0); one(Yr.ld_map, f"Leiden{y}", 0)
    for rep in range(R):
        one(Yr.random_partition(116, rng, balance="pop"), "rand_pop", rep)
        one(Yr.random_partition(116, rng, balance="dong"), "rand_dong", rep)
        one(Yr.random_partition(116, rng, balance="free"), "rand_free", rep)
        if rep % 20 == 0: print(y, rep, f"{time.time()-t0:.0f}s", flush=True)
D = pd.DataFrame(rows); D.to_csv(OUT / "exp_f_null.csv", index=False, encoding="utf-8-sig")
KU = pd.DataFrame(kurows); KU.to_csv(OUT / "exp_f_ku.csv", index=False, encoding="utf-8-sig")
out = []
metrics = ["IFR", "loss_도서관", "loss_문화", "loss_행정안전", "loss_유치원10분", "span_lib", "Hauc_도서관", "pop_cv", "dong_cv"]
for y in ("2020", "2025"):
    d = D[D.year == y]
    for tag in ("공식LZ", f"Leiden{y}"):
        x = d[d.tag == tag].iloc[0]
        for null in ("rand_pop", "rand_dong", "rand_free"):
            r = d[d.tag == null]; row = {"year": y, "구획": tag, "귀무": null}
            for m in metrics: row[m] = f"{x[m]:.3f} (p{(r[m] < x[m]).mean():.2f}; 귀무중앙 {r[m].median():.3f})"
            out.append(row)
S = pd.DataFrame(out)
# 구별 부호검정: 공식 < 귀무 중앙(rand_pop)
sg = []
for y in ("2020", "2025"):
    k = KU[KU.year == y]
    for tag in ("공식LZ", f"Leiden{y}"):
        for f in ["IFR"] + [f"{x}" for x in FS]:
            off = k[(k.tag == tag) & (k.f == f)].set_index("ku")["loss"]
            med = k[(k.tag == "rand_pop") & (k.f == f)].groupby("ku")["loss"].median()
            better = (off < med) if f != "IFR" else (off > med)
            sg.append({"year": y, "구획": tag, "지표": f, "귀무보다 나은 구": int(better.sum()), "/25": 25})
SG = pd.DataFrame(sg)
s = "## 116개 경계 효과, 귀무 3종\n" + md(S, "{}") + "\n\n## 구별 부호검정(인구균형 귀무 중앙값 대비)\n" + md(SG, "{}")
print(s); open(OUT / "exp_f_summary.md", "w", encoding="utf-8").write(s)
