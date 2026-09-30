# -*- coding: utf-8 -*-
"""연구1 사전 점검(파일럿): 확정 자료로 실험 1·2·3이 의미 있는 차이를 내는지 본다. 설계 검토용, 논문 수치 아님."""
import sys, heapq, json, time
from pathlib import Path
import numpy as np, pandas as pd, pyarrow.dataset as ds

ROOT = Path(r"D:\Research\00_박사논문_연구체계")
PKG = ROOT / "06_접근성분석" / "접근성분석_패키지" / "데이터"
sys.path.insert(0, str(ROOT / "00_공통_코어엔진" / "exploration"))
import xcommon as X  # noqa

OUT = Path(__file__).parent / "pilot_out"; OUT.mkdir(exist_ok=True)
YEAR, PY = "2020", "2019"
T = 900
rng = np.random.default_rng(20260926)
log = open(OUT / "pilot2_log.md", "w", encoding="utf-8")
def P(*a):
    s = " ".join(str(x) for x in a); print(s); log.write(s + "\n"); log.flush()

# ── 격자·단위 ────────────────────────────────────────────────────────────────
M = pd.read_parquet(PKG / "입력/grid/grid100_master.parquet")
M = M[["grid_cd", "dong424", "lz116", "ld2020", "ku", f"pop_{PY}", f"biz_{PY}"]].rename(columns={f"pop_{PY}": "pop", f"biz_{PY}": "biz"})
M = M.reset_index(drop=True)
gix = pd.Series(np.arange(len(M)), index=M.grid_cd)
pop = M["pop"].to_numpy(float)
LEV = {"동": "dong424", "공식LZ": "lz116", "Leiden": "ld2020", "구": "ku"}
uid = {k: pd.factorize(M[c])[0] for k, c in LEV.items()}
popped = pop > 0
P(f"# 연구1 파일럿 ({YEAR}, 인구 {PY})\n\n격자 {len(M):,}, 인구>0 {popped.sum():,}, 인구 {pop.sum():,.0f}")

# ── 도서관 도달 ──────────────────────────────────────────────────────────────
F = pd.read_parquet(PKG / "입력/facility/facility_2020_2025_units.parquet",
                    columns=["year", "시설", "분석가능", "grid100_cd"])
lib = F[(F["시설"] == "공공도서관") & F["분석가능"]]
L20 = set(lib[lib.year == 2020].grid100_cd.dropna()); L25 = set(lib[lib.year == 2025].grid100_cd.dropna())
P(f"도서관 격자 2020 {len(L20)} / 2025 {len(L25)} (행 {sum(lib.year==2020)} / {sum(lib.year==2025)})")

t0 = time.time()
tt = ds.dataset(PKG / "입력/ttm/ttm100_2020", format="parquet", partitioning="hive").to_table(
    columns=["o_grid", "d_grid", "t_sec"], filter=ds.field("t_sec") <= T).to_pandas()
tt["o"] = gix.reindex(tt.o_grid).to_numpy(); tt["d"] = gix.reindex(tt.d_grid).to_numpy()
tt = tt.dropna(subset=["o", "d"]); tt["o"] = tt.o.astype(np.int64); tt["d"] = tt.d.astype(np.int64)
P(f"소요시간 ≤{T}s 쌍 {len(tt):,} ({time.time()-t0:.0f}s)")
tt = tt.sort_values("d"); d_arr = tt.d.to_numpy(); o_arr = tt.o.to_numpy()
starts = np.searchsorted(d_arr, np.arange(len(M))); ends = np.searchsorted(d_arr, np.arange(len(M)), side="right")
def cover_of(j): return o_arr[starts[j]:ends[j]]

def reach_from(gridset):
    r = np.zeros(len(M), bool)
    for g in gridset:
        j = gix.get(g)
        if j is not None: r[cover_of(j)] = True
    return r
r_lib = reach_from(L20)
C0 = (pop * r_lib).sum() / pop.sum()
P(f"도서관 15분 Coverage 서울 {C0:.4f}")

# ── 8개 카테고리 도달(b=none) ─────────────────────────────────────────────────
G = ds.dataset(PKG / "결과/main/grid_access_2020_100.parquet").to_table(filter=ds.field("b") == "none",
                                                                     columns=["grid_cd", "cat", "r"]).to_pandas()
G["cat"] = G["cat"].astype(str)
reach = {"도서관": r_lib}
for c, sub in G.groupby("cat", observed=True):
    r = np.zeros(len(M), bool); ix = gix.reindex(sub.grid_cd).to_numpy()
    ok = ~np.isnan(ix); r[ix[ok].astype(int)] = sub.r.to_numpy()[ok] > 0; reach[c] = r

# ── 실험 1: 은폐 H ───────────────────────────────────────────────────────────
def unit_cov(u, r):
    num = np.bincount(u, pop * r); den = np.bincount(u, pop)
    return np.divide(num, den, out=np.zeros_like(num), where=den > 0)
def H_of(u, r, tau):
    Cu = unit_cov(u, r)[u]; un = (~r) & popped
    return (pop[un] * (Cu[un] >= tau)).sum() / pop[un].sum()
def within_share(u, r):  # 인구가중 분산 중 단위 내 몫
    x = r.astype(float); mu = (pop * x).sum() / pop.sum()
    tot = (pop * (x - mu) ** 2).sum(); Cu = unit_cov(u, r)[u]
    return 1 - (pop * (Cu - mu) ** 2).sum() / tot
rows = []
for f, r in reach.items():
    Cs = (pop * r).sum() / pop.sum()
    for m in (0.8, 1.0, 1.2):
        tau = min(Cs * m, 0.999)
        row = {"시설": f, "서울C": round(Cs, 4), "τ배수": m}
        for k in LEV: row[f"H_{k}"] = round(H_of(uid[k], r, tau), 3)
        rows.append(row)
H = pd.DataFrame(rows); H.to_csv(OUT / "exp1_H.csv", index=False, encoding="utf-8-sig")
P("\n## 실험 1 — H (하한을 충족한 단위 안에 사는 미도달 인구 비율)\n"); P(X.md_table(H, "{:.3f}"))
W = pd.DataFrame([{"시설": f, **{k: round(within_share(uid[k], r), 3) for k in LEV}} for f, r in reach.items()])
P("\n### 도달 분산 중 단위 내 몫\n"); P(X.md_table(W, "{:.3f}"))

# ── 실험 3: IFR (서울 합) ─────────────────────────────────────────────────────
od = X.load_od(YEAR)
lz = X.load_lz(); ldm, _ = X.load_leiden(YEAR)
dmap = pd.DataFrame({"Dong": sorted(set(od.dong_O) | set(od.dong_D))}).set_index("Dong")
dong = X.load_dong().set_index("Dong")
lab = {"동": pd.Series(dong.index, index=dong.index), "공식LZ": lz["life_zone_id"],
       "Leiden": ldm["global_community_id"], "구": dong["Ku"]}
P(f"\nlz cols {list(lz.columns)}, leiden cols {list(ldm.columns)}")
def seoul_ifr(s):
    a = s.reindex(od.dong_O).to_numpy(); b = s.reindex(od.dong_D).to_numpy()
    return (od.flow.to_numpy() * (a == b)).sum() / od.flow.sum()
ifr = {k: seoul_ifr(v) for k, v in lab.items()}
P("\n## 실험 3 — 서울 IFR: " + ", ".join(f"{k} {v:.3f}" for k, v in ifr.items()))

# 경계 제한 Coverage 손실(b=단위 vs none)
U = pd.read_csv(PKG / "결과/main/unit_access_2020_100.csv")
s = U[(U.unit_level == "seoul")]
piv = s.pivot_table(index="cat", columns="b", values="COV")
piv = piv[["none", "dong424", "lz116", "ld", "ku"]]
loss = (piv["none"].to_numpy()[:, None] - piv.to_numpy())
P("\n### 경계 제한 Coverage 손실 (none − b)\n")
P(X.md_table(pd.DataFrame(loss, index=piv.index, columns=piv.columns).reset_index().round(4)))

# ── 무작위 연접 구획 기준선 (구별 공식 개수, 인구 균형) ─────────────────────
kg = X.all_ku_graphs(YEAR, with_pop=True)
off_k = lab["공식LZ"].groupby(dong["Ku"]).nunique()
R = 0
dong_order = dong.index.to_numpy()
tau_lib = C0
res = []
for rep in range(R):
    s_rand = pd.Series(index=dong_order, dtype=np.int64)
    for ku, g in kg.items():
        labs = X.random_balanced_partition(g.adj, int(off_k[ku]), rng, size=g.pop)
        s_rand.loc[g.nodes] = labs + ku * 100
    u = pd.factorize(s_rand.reindex(M.dong424).to_numpy())[0]
    res.append({"rep": rep, "IFR": seoul_ifr(s_rand), "H_lib": H_of(u, r_lib, tau_lib),
                "H_의료": H_of(u, reach.get("의료", r_lib), (pop * reach.get("의료", r_lib)).sum() / pop.sum())})
# ── 실험 2: 도서관 예산 배치(탐욕법) ──────────────────────────────────────────
libix = {gix[g] for g in L20 if g in gix.index}
cand = np.where(((M["pop"] > 0) | (M["biz"] > 0)).to_numpy() & (ends > starts))[0]
cand = np.array([j for j in cand if j not in libix])
P(f"\n## 실험 2 — 도서관 배치 (후보 {len(cand):,}, K=32, 탐욕법)")
units_all = dict(uid); units_all["격자"] = np.where(popped, np.arange(len(M)), len(M))  # 무인구 격자는 더미 단위

def run(level, tau, K, kmin_cap=4000):
    cov = r_lib.copy()
    u = units_all[level] if level else None
    if u is not None:
        den = np.bincount(u, pop); cnum = np.bincount(u, pop * cov, minlength=len(den))
        valid = den > 0
        if level == "격자": valid[-1] = False if len(den) > len(M) else valid[-1]
    def shortfall():
        Cu = np.divide(cnum, den, out=np.zeros_like(cnum), where=den > 0)
        return np.maximum(0, tau - Cu)[valid].sum()
    def gain(j):
        idx = cover_of(j); new = idx[~cov[idx]]
        g = pop[new].sum()
        if u is None: return g, g
        if len(new) == 0: return 0.0, 0.0
        uu = u[new]; add = np.bincount(uu, pop[new], minlength=len(den))
        nz = np.nonzero(add)[0]
        C_old = cnum[nz] / den[nz]; C_new = (cnum[nz] + add[nz]) / den[nz]
        dS = (np.minimum(tau, C_new) - np.minimum(tau, C_old))[valid[nz]].sum()
        return dS, g
    picks = []; kmin = None
    phase1 = u is not None and shortfall() > 1e-12
    heap = []
    for j in cand:
        dS, g = gain(j); key = (dS * 1e12 + g) if phase1 else g
        heap.append((-key, j))
    heapq.heapify(heap)
    limit = kmin_cap if phase1 else K
    while heap and len(picks) < max(limit, K):
        negk, j = heapq.heappop(heap)
        dS, g = gain(j); key = (dS * 1e12 + g) if phase1 else g
        if heap and key < -heap[0][0] - 1e-9:
            heapq.heappush(heap, (-key, j)); continue
        idx = cover_of(j); new = idx[~cov[idx]]; cov[new] = True
        if u is not None: cnum += np.bincount(u[new], pop[new], minlength=len(den))
        picks.append(j)
        if phase1 and shortfall() <= 1e-12:
            kmin = len(picks); phase1 = False
            if kmin >= K: break
            heap = [(-gain(jj)[1], jj) for jj in cand]; heapq.heapify(heap)  # 2단계: 도달 최대화
        if not phase1 and len(picks) >= K and kmin is not None: break
        if not phase1 and u is None and len(picks) >= K: break
        if phase1 and len(picks) >= kmin_cap: break
    return picks, kmin, (None if u is None else shortfall())

def evaluate(picks, K=32):
    cov = r_lib.copy()
    for j in picks[:K]: cov[cover_of(j)] = True
    out = {"도달증가": (pop * cov).sum() - (pop * r_lib).sum()}
    for k in ("동", "공식LZ", "구"):
        Cu0 = unit_cov(uid[k], r_lib); Cu = unit_cov(uid[k], cov)
        den = np.bincount(uid[k], pop) > 0
        out[f"{k}_τ미달수"] = int(((Cu < C0) & den).sum())
        out[f"{k}_최저C"] = round(Cu[den].min(), 3)
    # 취약지 귀속: 증가분 중 기준 C<τ 동에 사는 몫
    Cd0 = unit_cov(uid["동"], r_lib)[uid["동"]]
    newg = cov & ~r_lib
    out["증가_취약동몫"] = round((pop[newg] * (Cd0[newg] < C0)).sum() / max(pop[newg].sum(), 1), 3)
    return out


RN = 100; out = []
for rep in range(RN):
    s_rand = pd.Series(index=dong_order, dtype=np.int64)
    for ku, g in kg.items():
        labs = X.random_balanced_partition(g.adj, int(off_k[ku]), rng, size=g.pop)
        s_rand.loc[g.nodes] = labs + ku * 100
    units_all["RAND"] = pd.factorize(s_rand.reindex(M.dong424).to_numpy())[0]
    for m in (0.8, 1.0):
        pk, kmin, _ = run("RAND", C0 * m, 32)
        out.append({"rep": rep, "τ배수": m, "K_min": kmin, **evaluate(pk)})
    if rep % 10 == 0: P(f"  rep {rep}")
N = pd.DataFrame(out); N.to_csv(OUT / "exp2_random_null.csv", index=False, encoding="utf-8-sig")
E = pd.read_csv(OUT / "exp2_library.csv")
for m in (0.8, 1.0):
    n = N[N["τ배수"] == m]
    P(f"τ×{m}: 무작위 K_min 중앙 {n.K_min.median()} (5~95% {n.K_min.quantile(.05)}~{n.K_min.quantile(.95)}), "
      f"도달증가 중앙 {n['도달증가'].median():,.0f}")
    for lv in ("공식LZ", "Leiden"):
        e = E[(E["규칙"] == f"P1 {lv}") & (E["τ배수"].astype(str) == str(m))].iloc[0]
        km = float(e.K_min)
        P(f"   {lv}: K_min {km:.0f} → 무작위보다 작은 비율 {(n.K_min > km).mean():.2f}, 같거나 작음 {(n.K_min >= km).mean():.2f}; 도달증가 {e['도달증가']:,.0f} 분위 {(n['도달증가'] < e['도달증가']).mean():.2f}")
