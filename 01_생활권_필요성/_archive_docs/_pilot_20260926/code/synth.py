# -*- coding: utf-8 -*-
"""실험 A·B 종합표"""
import numpy as np, pandas as pd, json
from r1lib import OUT, md
A = pd.read_csv(OUT / "exp_a_partitions.csv"); A["year"] = A["year"].astype(str)
meta = json.load(open(OUT / "exp_a_meta.json"))
L = open(OUT / "synth.md", "w", encoding="utf-8")
def P(s=""): print(s); L.write(s + "\n")

P("# 종합 — 실험 A (단위 크기 연속축, 무작위 연접 구획)\n")
P(f"C_none: {json.dumps({y:{f:round(v,3) for f,v in d.items()} for y,d in meta['C_none'].items()}, ensure_ascii=False)}\n")
cols_show = ["IFR", "Hauc_도서관", "H10_도서관", "loss_도서관", "loss_문화", "loss_행정안전", "Hauc_문화", "Hauc_유치원10분",
             "Kmin_0.8", "Kmin_1.0", "Reff_0.8", "Reff_1.0", "dong_below_1.0", "sfca_H", "sfca_units_zero", "span_lib", "stab_rho", "stab_jac10"]
for y in ("2020", "2025"):
    d = A[A.year == y]
    P(f"\n## {y} — 크기축 (무작위 구획은 중앙값 [5~95 분위])\n")
    rows = []
    for tag, k in [("구", 25), ("rand50", 50), ("rand80", 80), ("rand116", 116), ("공식LZ", 116), ("Leiden2020", 116), ("Leiden2025", 116), ("rand160", 160), ("rand250", 250), ("동", 424)]:
        g = d[d.tag == tag]
        if g.empty: continue
        row = {"구획": tag, "k": k, "n": len(g)}
        for c in cols_show:
            if c not in g: continue
            v = g[c].astype(float)
            row[c] = f"{v.median():.3f}" if len(g) == 1 else f"{v.median():.3f} [{v.quantile(.05):.3f}~{v.quantile(.95):.3f}]"
        rows.append(row)
    P(md(pd.DataFrame(rows), "{}"))
    # 치환검정 116
    P(f"\n### {y} — 116개 치환 검정 (무작위 {len(d[d.tag=='rand116'])}회 대비 분위; 1.0 = 무작위 전부보다 큼)\n")
    r = d[d.tag == "rand116"]
    rows = []
    for tag in ("공식LZ", "Leiden2020", "Leiden2025"):
        g = d[d.tag == tag]
        if g.empty: continue
        row = {"구획": tag}
        for c in cols_show:
            if c not in g: continue
            x = float(g[c].iloc[0]); rv = r[c].astype(float).to_numpy()
            if np.isnan(x): row[c] = "nan"; continue
            row[c] = f"{x:.3f} (p{(rv < x).mean():.2f})"
        rows.append(row)
    P(md(pd.DataFrame(rows), "{}"))

# 실험 B
try:
    T = pd.read_csv(OUT / "exp_b_tau.csv"); K = pd.read_csv(OUT / "exp_b_kcurve.csv"); AC = pd.read_csv(OUT / "exp_b_actual.csv")
    P("\n# 종합 — 실험 B (도서관 배치)\n")
    for y in ("2020", "2025"):
        t = T[T.year == int(y)]
        P(f"\n## {y} — τ(서울 Coverage 배수)별 K_min\n")
        piv = t.pivot_table(index="tau_mult", columns="level", values="Kmin", aggfunc="first")
        P(md(piv.reset_index(), "{:.0f}"))
        P(f"\n## {y} — τ별 K=32에서의 효율 유지율 / 하한 미달 동 수 / 취약 귀속\n")
        piv = t.pivot_table(index="tau_mult", columns="level", values=["Reff@32", "dong_below@32", "vuln_share@32"], aggfunc="first")
        P(md(piv.round(3).reset_index(), "{}"))
        k = K[(K.year == int(y)) & (K.K.isin([8, 16, 32, 48, 64]))]
        P(f"\n## {y} — K 곡선 (τ=1.0): 효율 유지율 / 미달 동 수\n")
        P(md(k[k.tau.astype(str).isin(["-", "1.0"])].pivot_table(index="K", columns="rule", values="Reff").round(3).reset_index(), "{}"))
        P(md(k[k.tau.astype(str).isin(["-", "1.0"])].pivot_table(index="K", columns="rule", values="dong_below").reset_index(), "{}"))
    P("\n## 실제 배치 2020→2025 대조\n"); P(md(AC.round(3), "{}"))
except FileNotFoundError as e:
    P(f"\n(실험 B 미완: {e})")
L.close()
