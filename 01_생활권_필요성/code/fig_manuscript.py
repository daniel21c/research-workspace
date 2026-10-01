# -*- coding: utf-8 -*-
"""Manuscript figures (English) and tables for the JTG-style draft (2026-10-02).
Fig. 1 Study area; Fig. 2 Analytical framework; Fig. 3 Bundle completion curves and missing domains;
Fig. 4 Shortfall living zones by placement rule (single facilities); Fig. 5 Living-zone completion map (2025);
Fig. 6 Zero-completion living zones by planning unit (bundle).
Tables 1–4 (csv + md) to manuscript/tables/. Figures to manuscript/figures/Fig1..6.png"""
import json
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt, geopandas as gpd
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch, FancyBboxPatch, FancyArrowPatch
from bundlelib import Ctx, State
from r1lib import OUT, X, md
plt.rcParams.update({"font.family": "Arial", "axes.unicode_minus": False, "font.size": 9})
FIG = Path(__file__).parent.parent / "manuscript" / "figures"; TAB = Path(__file__).parent / "manuscript_src" / "tables"; FIG.mkdir(parents=True, exist_ok=True); TAB.mkdir(parents=True, exist_ok=True)
BL, OR, AQ, YE, GR, LG = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#52514e", "#e6e6e3"
def clean(ax, axis="y"): ax.grid(color=LG, linewidth=0.6, axis=axis); ax.spines[["top", "right"]].set_visible(False); ax.set_axisbelow(True)

Ys = {}; ctx = {}
for y in ("2020", "2025"):
    ctx[y] = Ctx("seoul", y, years=Ys); Ys = ctx[y].Y
dong = X.load_dong(); gu = dong.dissolve(by="Ku").reset_index()
lz = gpd.read_file(X.C.DATA_DIR / "seoul_official_livingzone_116.gpkg", layer="epsg5179")

# ---------- Fig. 1 Study area ----------
fig, ax = plt.subplots(figsize=(7.2, 5.6))
dong.boundary.plot(ax=ax, color="#c8c8c4", linewidth=0.25)
lz.boundary.plot(ax=ax, color=BL, linewidth=0.7)
gu.boundary.plot(ax=ax, color=GR, linewidth=1.4)
ax.set_axis_off()
ax.legend(handles=[plt.Line2D([], [], color=GR, lw=1.4, label="Gu (25)"), plt.Line2D([], [], color=BL, lw=0.8, label="Official living zones (116)"),
                   plt.Line2D([], [], color="#c8c8c4", lw=0.6, label="Administrative dong (424)")], loc="lower left", frameon=False)
ax.annotate("", xy=(0.95, 0.95), xytext=(0.95, 0.86), xycoords="axes fraction", arrowprops=dict(arrowstyle="-|>", color=GR)); ax.text(0.95, 0.965, "N", transform=ax.transAxes, ha="center")
x0, y0 = ax.get_xlim()[1] - 12000, ax.get_ylim()[0] + 1500; ax.plot([x0, x0 + 10000], [y0, y0], color=GR, lw=2); ax.text(x0 + 5000, y0 + 500, "10 km", ha="center")
fig.tight_layout(); fig.savefig(FIG / "Fig1_study_area.png", dpi=600); fig.savefig(FIG / "Fig1_study_area.pdf"); plt.close(fig)

# ---------- Fig. 2 Framework ----------
fig, ax = plt.subplots(figsize=(7.2, 3.6)); ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.set_axis_off()
def box(x, y, w, h, t, fc="#ffffff", ec=GR, fs=8.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06", fc=fc, ec=ec, lw=1)); ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", wrap=True)
def arr(x1, y1, x2, y2): ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10, color=GR, lw=1))
box(0.1, 3.6, 2.2, 1.1, "Measure\n100 m grid population\nwalking times (OSM, 4 km/h)\nfacility inventories", fc="#f4f4f2")
box(0.1, 2.1, 2.2, 1.1, "RQ1\nBundle completion\nby living zone", fc="#eaf2fc", ec=BL, bold=True)
box(2.8, 3.6, 2.4, 1.1, "Place\nN facilities = net additions\n2020→2025, same for all rules", fc="#f4f4f2")
box(2.8, 1.75, 2.4, 1.45, "Grid-based rules\n• efficiency (max new access)\n• vulnerability-weighted\n• bundle MCLP (exact)", fc="#fdf3df", ec=YE)
box(2.8, 0.15, 2.4, 1.45, "Zone-based rules\nminimum standard first, then\nefficiency, set by\ngu / living zone / dong", fc="#fbe6dc", ec=OR)
box(5.7, 1.75, 2.0, 2.95, "Score\n(three report cards)\n\n1 Total access\n2 Bottom-20 residents\n3 Living zones below\n   the minimum", fc="#f4f4f2")
box(8.1, 2.75, 1.8, 1.95, "RQ2\nDo grid rules\nfill every\nliving zone?", fc="#eaf2fc", ec=BL, bold=True)
box(8.1, 0.15, 1.8, 2.3, "RQ3\nWhich unit can\nmeet the minimum?\n+ official vs random\n116 boundaries", fc="#eaf2fc", ec=BL, bold=True)
arr(1.2, 3.6, 1.2, 3.2); arr(2.3, 4.15, 2.8, 4.15); arr(4.0, 3.6, 4.0, 3.2); arr(5.2, 2.45, 5.7, 2.6); arr(5.2, 0.85, 5.7, 1.9); arr(7.7, 3.6, 8.1, 3.6); arr(7.7, 2.1, 8.1, 1.6)
fig.tight_layout(); fig.savefig(FIG / "Fig2_framework.png", dpi=600); fig.savefig(FIG / "Fig2_framework.pdf"); plt.close(fig)

# ---------- Fig. 3 Completion curves ----------
DEF = [("logan4_원정의(약국·슈퍼·공원·초등)", "Logan et al. 4 amenities", AQ), ("logan7_최댓값(cat_A 7)", "Everyday functions (7 categories)", GR),
       ("seoul_FULL_6분야(공원·도서관·노인여가·청소년아동·보육·공공체육)", "Planned public services (6 domains)", OR)]
fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.4))
for ax, y in zip(axes[:2], ("2020", "2025")):
    C = pd.read_csv(OUT / f"표4.1-16_묶음정의별_곡선_{y}.csv")
    for key, lab, col in DEF:
        d = C[C.정의 == key]; ax.plot(d.분, d.완결률 * 100, color=col, lw=2, label=lab)
    for v in (10, 15): ax.axvline(v, color=GR, ls=":", lw=0.8)
    ax.set_xlim(0, 20); ax.set_ylim(0, 100); ax.set_xlabel("Walking time (min)"); ax.set_ylabel("Residents completing the bundle (%)"); ax.set_title(f"({'a' if y == '2020' else 'b'}) {y}", loc="left"); clean(ax, "both")
axes[0].legend(frameon=False, fontsize=8, loc="upper left")
ax = axes[2]; Mi = pd.read_csv(OUT / "표4.1-16_결손수분포_2025.csv")
a = Mi[(Mi.정의.str.startswith("logan7")) & (Mi["임계(분)"] == 15)].iloc[0]; b = Mi[(Mi.정의 == "seoul_FULL_6분야") & (Mi["임계(분)"] == 10)].iloc[0]
def dist(r, kmax):
    v = [r.get(f"결손{k}개", 0) for k in range(1, kmax + 1)]; v = [0 if pd.isna(x) else x for x in v]; return [v[0], v[1], v[2], sum(v[3:])]
xs = np.arange(4); w = 0.38
ax.bar(xs - w / 2, np.array(dist(a, 7)) * 100, w, color=GR, label="Everyday functions, 15 min"); ax.bar(xs + w / 2, np.array(dist(b, 6)) * 100, w, color=OR, label="Planned services, 10 min")
ax.set_xticks(xs); ax.set_xticklabels(["1", "2", "3", "4+"]); ax.set_xlabel("Missing domains"); ax.set_ylabel("Share of non-completing residents (%)"); ax.set_title("(c) Missing domains, 2025", loc="left"); ax.legend(frameon=False, fontsize=8); clean(ax)
fig.tight_layout(); fig.savefig(FIG / "Fig3_completion_curves.png", dpi=600); fig.savefig(FIG / "Fig3_completion_curves.pdf"); plt.close(fig)

# ---------- Fig. 4 Single facilities ----------
pol = [("P0", "Grid efficiency", GR), ("PG1", "Grid vulnerability-weighted", YE), ("PL_구", "Gu minimum", OR), ("PL_공식", "Living-zone minimum", BL)]
fac = [("도서관", "Library"), ("국공립유치원10분", "Public kindergarten"), ("공공문화시설", "Cultural facility"), ("국공립어린이집5분", "Public childcare"), ("주민센터", "Community centre"), ("노인이용시설", "Senior facility"), ("청소년수련시설", "Youth centre")]
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.6), sharey=True)
for ax, y, lab in zip(axes, ("2020", "2025"), ("(a) 2020", "(b) 2025")):
    D = pd.read_csv(OUT / f"표4.1-10_정책비교_{y}.csv").groupby(["시설", "정책"])["공식_미달수"].median(); w = 0.2; xs = np.arange(len(fac))
    for i, (k, l, col) in enumerate(pol):
        v = [D.get((f, k), np.nan) for f, _ in fac]; ax.bar(xs + (i - 1.5) * w, v, w, color=col, label=l)
        for xx, vv in zip(xs + (i - 1.5) * w, v):
            if vv == 0: ax.text(xx, 0.2, "0", ha="center", va="bottom", fontsize=7, color=col, fontweight="bold")
    ax.set_xticks(xs); ax.set_xticklabels([f[1] for f in fac], rotation=30, ha="right"); ax.set_title(lab, loc="left"); clean(ax)
axes[0].set_ylabel("Living zones below the minimum (of 116)"); axes[0].legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(FIG / "Fig4_single_facility_shortfall.png", dpi=600); fig.savefig(FIG / "Fig4_single_facility_shortfall.pdf"); plt.close(fig)

# ---------- Fig. 5 Map ----------
def lz_share(c, picks):
    st = State(c); st.B = {s: 10 ** 6 for s in c.SUB}
    for s, js in (picks or {}).items():
        for j in js: st.apply(int(j), [s])
    comp = (st.cnt == c.NC) & c.popped
    df = pd.DataFrame({"lz": c.Yr.M.lz.to_numpy(), "p": c.pop, "c": c.pop * comp}).groupby("lz").sum(); return (df.c / df.p).rename("share")
c = ctx["2025"]
mip = json.load(open(OUT / "exp16_milp_picks_seoul_2025.json", encoding="utf-8"))["MIP"]["picks"]
flo = json.load(open(OUT / "exp20_picks_2025_공식LZ_long_0.05.json", encoding="utf-8"))["picks"]
cmap = ListedColormap(["#7a1f12", "#f0a080", "#f6d7c3", "#cfe0f5", "#2a78d6"]); norm = BoundaryNorm([-1e-9, 1e-9, 0.05, 0.10, 0.25, 1.0], cmap.N)
fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.9))
for ax, (t, picks) in zip(axes, [("(a) Before placement", None), ("(b) Grid-optimised (exact MCLP)", mip), ("(c) Living-zone minimum 5% (MIP)", flo)]):
    sh = lz_share(c, picks); g = lz.merge(sh, left_on="life_zone_id", right_index=True, how="left")
    g.plot(column="share", cmap=cmap, norm=norm, ax=ax, edgecolor="white", linewidth=0.3); gu.boundary.plot(ax=ax, color=GR, linewidth=0.5)
    ax.set_axis_off(); ax.set_title(f"{t}\nZero-completion zones: {int((sh <= 0).sum())}; below 5%: {int((sh < 0.05).sum())}", fontsize=8.5, loc="left")
fig.legend(handles=[Patch(color=cmap(i), label=l) for i, l in enumerate(["0%", "0–5%", "5–10%", "10–25%", "≥25%"])], loc="lower center", ncol=5, frameon=False, title="Residents completing the six-domain bundle within 10 min")
fig.tight_layout(rect=(0, 0.1, 1, 1)); fig.savefig(FIG / "Fig5_living_zone_map_2025.png", dpi=600); fig.savefig(FIG / "Fig5_living_zone_map_2025.pdf"); plt.close(fig)

# ---------- Fig. 6 Zero-completion zones by unit ----------
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), sharex=True)
base = {"2020": {"before": 50, "mip": 18, "p2": 21}, "2025": {"before": 38, "mip": 14, "p2": 19}}
for ax, y, lab in zip(axes, ("2020", "2025"), ("(a) 2020", "(b) 2025")):
    T = pd.read_csv(OUT / f"표4.1-23_권역최저선_{y}.csv")
    def z(u): r = T[(T.단위 == u) & (T.τ == 0.05)]; return float(r["공식LZ_0%권역"].median()) if len(r) else np.nan
    rnd = T[T.단위.str.startswith("rand116") & (T.τ == 0.05)]["공식LZ_0%권역"]
    rows = [("Before placement", base[y]["before"], GR), ("Grid: maximise total (exact)", base[y]["mip"], GR), ("Grid: vulnerability-weighted (P=2)", base[y]["p2"], YE),
            ("Gu minimum 5%", z("구"), OR), ("Dong minimum 5%", z("동"), OR), ("Random 116 minimum 5%", float(rnd.median()) if len(rnd) else np.nan, AQ),
            ("Mobility-community 116 minimum 5%", z("Leiden"), AQ), ("Living-zone minimum 5%", z("공식LZ_long"), BL)]
    ys = np.arange(len(rows)); vals = [r[1] for r in rows]
    ax.barh(ys, vals, color=[r[2] for r in rows])
    for yy, v in zip(ys, vals): ax.text((0 if np.isnan(v) else v) + 0.5, yy, "not run" if np.isnan(v) else f"{v:.0f}", va="center", fontsize=8)
    ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows]); ax.invert_yaxis(); ax.set_title(lab, loc="left"); clean(ax, "x")
    ax.set_xlabel("Zero-completion living zones (of 116)")
fig.tight_layout(); fig.savefig(FIG / "Fig6_zero_completion_by_unit.png", dpi=600); fig.savefig(FIG / "Fig6_zero_completion_by_unit.pdf"); plt.close(fig)

# ---------- Tables ----------
M = ctx["2025"].Yr.M
rows = []
for name, col, g in (("Gu", "ku", gu), ("Official living zone", "lz", lz), ("Administrative dong", "dong", dong)):
    s = M.groupby(col)["pop"].sum(); a = g.geometry.area / 1e6
    rows.append({"Unit": name, "Number": s.size, "Mean population (2024)": f"{s.mean():,.0f}", "Population range": f"{s.min():,.0f}–{s.max():,.0f}", "Mean area (km²)": f"{a.mean():.2f}"})
rows.append({"Unit": "Grid cell (100 m, populated)", "Number": int((M["pop"] > 0).sum()), "Mean population (2024)": f"{M['pop'][M['pop'] > 0].mean():,.0f}", "Population range": "", "Mean area (km²)": "0.01"})
T1 = pd.DataFrame(rows); T1.to_csv(TAB / "Table1_planning_hierarchy.csv", index=False, encoding="utf-8-sig")
nest = f"Each living zone contains {M.groupby('lz').dong.nunique().mean():.1f} dong on average (range {M.groupby('lz').dong.nunique().min()}–{M.groupby('lz').dong.nunique().max()}); each gu contains {M.groupby('ku').lz.nunique().mean():.1f} living zones (range {M.groupby('ku').lz.nunique().min()}–{M.groupby('ku').lz.nunique().max()})."
(TAB / "Table1_planning_hierarchy.md").write_text("# Table 1 Planning hierarchy of Seoul\n\n" + md(T1, "{}") + "\n\n" + nest + "\n", encoding="utf-8")
cn = {"공원": "Park", "도서관": "Public library", "노인여가": "Senior leisure", "청소년아동": "Youth and children", "보육": "Childcare", "공공체육": "Public sports"}
pl = {"도서관": "Public library", "노인이용시설": "Senior facility", "청소년수련시설": "Youth centre", "국공립어린이집5분": "Public childcare centre", "공공체육": "Public sports facility"}
r2 = []
for k, (n, idx, subs) in enumerate(ctx["2025"].CATS):
    n20 = len(ctx["2020"].CATS[k][1]); r2.append({"Domain": cn[n], "Facility cells 2020": n20, "Facility cells 2025": len(idx), "Placed type (N)": "; ".join(f"{pl[s]} ({K})" for s, K in subs) or "fixed (not placed)"})
T2 = pd.DataFrame(r2); T2.to_csv(TAB / "Table2_bundle_domains.csv", index=False, encoding="utf-8-sig")
(TAB / "Table2_bundle_domains.md").write_text("# Table 2 Planned public-service bundle: domains, facility cells and placement budget\n\nN = net increase in facility-occupied 100 m cells, 2020→2025 (total 381). Park layer: 2018 living-zone plan layer, fixed for both years. Youth and children = youth centres ∪ community child centres (2026 list, fixed).\n\n" + md(T2, "{}") + "\n", encoding="utf-8")
W = {y: pd.read_csv(OUT / f"표4.1-16_묶음정의별_완결_{y}.csv") for y in ("2020", "2025")}
def g3(y, key, t): d = W[y]; r = d[(d.정의.str.startswith(key)) & (d["임계(분)"] == t)]; return f"{r.완결률.iloc[0]*100:.1f}" if len(r) else ""
r3 = [{"Bundle": lab, **{f"{y} {t} min": g3(y, key, t) for y in ("2020", "2025") for t in (10, 15)}} for key, lab in (("logan4", "Logan et al. 4 amenities"), ("logan7", "Everyday functions (7 categories)"), ("seoul_FULL_6분야(공원·도서관", "Planned public services (6 domains)"))]
T3 = pd.DataFrame(r3); T3.to_csv(TAB / "Table3_bundle_completion.csv", index=False, encoding="utf-8-sig")
(TAB / "Table3_bundle_completion.md").write_text("# Table 3 Bundle completion rate (% of residents) by walking-time threshold\n\n" + md(T3, "{}") + "\n", encoding="utf-8")
r4 = [("Grid efficiency (single facility)", "P0"), ("Grid vulnerability-weighted (single facility)", "PG1"), ("Gu minimum (single facility)", "PL_구"), ("Living-zone minimum (single facility)", "PL_공식"), ("Living-zone minimum + vulnerability (single facility)", "HY_공식")]
D10 = {y: pd.read_csv(OUT / f"표4.1-10_정책비교_{y}.csv").groupby(["시설", "정책"]).median(numeric_only=True) for y in ("2020", "2025")}
rows = []
for lab, k in r4:
    for f, fl in (("도서관", "Library"), ("국공립유치원10분", "Public kindergarten")):
        rows.append({"Rule": lab, "Facility": fl, **{f"{y} total access (%)": f"{D10[y].loc[(f, k), 'COV']*100:.1f}" for y in ("2020", "2025")},
                     **{f"{y} vulnerable-20 reach (%)": f"{D10[y].loc[(f, k), '취약20_도달률']*100:.1f}" for y in ("2020", "2025")},
                     **{f"{y} living zones below minimum": int(D10[y].loc[(f, k), '공식_미달수']) for y in ("2020", "2025")}})
T4a = pd.DataFrame(rows)
B = [("Grid: facility-by-facility (exact)", "IND", (14.68, 16.51), (0.91, 1.12), (21, 13)), ("Grid: maximise bundle (exact MCLP)", "MIP", (22.80, 24.22), (0.11, 0.24), (18, 14)),
     ("Grid: vulnerability-weighted (P=2)", "P2", (17.59, 18.47), (5.83, 6.31), (21, 19))]
rows = [{"Rule": a, "2020 completion (%)": f"{b[0]:.1f}", "2025 completion (%)": f"{b[1]:.1f}", "2020 bottom-20 (%)": f"{c_[0]:.1f}", "2025 bottom-20 (%)": f"{c_[1]:.1f}", "2020 zero-completion zones": d[0], "2025 zero-completion zones": d[1]} for a, _, b, c_, d in B]
for lab, u in (("Gu minimum 5% (MIP, time-limited)", "구"), ("Dong minimum 5% (MIP, time-limited)", "동"), ("Living-zone minimum 5% (MIP, time-limited)", "공식LZ_long")):
    r = {"Rule": lab}
    for y in ("2020", "2025"):
        T = pd.read_csv(OUT / f"표4.1-23_권역최저선_{y}.csv"); q = T[(T.단위 == u) & (T.τ == 0.05)].iloc[0]
        r[f"{y} completion (%)"] = f"{q.완결률*100:.1f}"; r[f"{y} bottom-20 (%)"] = f"{q.하위20_완결률*100:.1f}"; r[f"{y} zero-completion zones"] = int(q["공식LZ_0%권역"])
    rows.append(r)
T4b = pd.DataFrame(rows)
T4a.to_csv(TAB / "Table4a_single_facility_report_cards.csv", index=False, encoding="utf-8-sig"); T4b.to_csv(TAB / "Table4b_bundle_report_cards.csv", index=False, encoding="utf-8-sig")
(TAB / "Table4_report_cards.md").write_text("# Table 4 Three report cards by placement rule\n\n## (a) Single facilities (library, public kindergarten)\n\n" + md(T4a, "{}") + "\n\n## (b) Six-domain bundle (10 min)\n\nExact solutions: grid rules optimal (gap 0); zone minimums within time limits (living zone 4 h, gap 3–49%; gu and dong 1.5 h).\n\n" + md(T4b, "{}") + "\n", encoding="utf-8")
print(T1.to_string(index=False)); print(nest); print(T2.to_string(index=False)); print(T3.to_string(index=False)); print(T4b.to_string(index=False)); print("done")
