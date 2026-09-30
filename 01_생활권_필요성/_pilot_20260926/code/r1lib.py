# -*- coding: utf-8 -*-
"""연구1 실험 공통 모듈 (설계 검토용). 확정 자료를 읽기만 한다."""
import sys, heapq
from pathlib import Path
import numpy as np, pandas as pd, pyarrow.dataset as ds

ROOT = Path(r"D:\Research\00_박사논문_연구체계")
PKG = ROOT / "06_접근성분석" / "접근성분석_패키지" / "데이터"
sys.path.insert(0, str(ROOT / "00_공통_코어엔진" / "exploration"))
import xcommon as X  # noqa

OUT = Path(__file__).parent.parent / "results"; OUT.mkdir(exist_ok=True)
POPY = {"2020": "2019", "2025": "2024"}
LDCOL = {"2020": "ld2020", "2025": "ld2025"}
# 시설 집합: (이름, 선택 함수, 임계 초)
FACSETS = {
    "도서관": (lambda f: f["시설"] == "공공도서관", 900),
    "문화": (lambda f: f["cat_A"] == "문화", 900),
    "행정안전": (lambda f: f["cat_A"] == "행정·안전", 900),
    "유치원10분": (lambda f: f["시설"].str.contains("유치원", na=False), 600),
    "어린이집5분": (lambda f: f["시설"].str.contains("어린이집", na=False), 300),
    "도서관10분": (lambda f: f["시설"] == "공공도서관", 600),
}


class Year:
    def __init__(self, year):
        self.year = year; py = POPY[year]
        M = pd.read_parquet(PKG / "입력/grid/grid100_master.parquet")
        M = M[["grid_cd", "dong424", "lz116", LDCOL[year], "ku", f"pop_{py}", f"biz_{py}"]]
        M.columns = ["grid_cd", "dong", "lz", "ld", "ku", "pop", "biz"]
        self.M = M = M.reset_index(drop=True)
        self.gix = pd.Series(np.arange(len(M)), index=M.grid_cd)
        self.pop = M["pop"].to_numpy(float); self.popped = self.pop > 0
        self.units = {"동": pd.factorize(M.dong)[0], "공식LZ": pd.factorize(M.lz)[0],
                      "Leiden": pd.factorize(M.ld)[0], "구": pd.factorize(M.ku)[0]}
        # 소요시간 ≤ 900s
        tt = ds.dataset(PKG / f"입력/ttm/ttm100_{year}", format="parquet", partitioning="hive").to_table(
            columns=["o_grid", "d_grid", "t_sec"], filter=ds.field("t_sec") <= 900).to_pandas()
        o = self.gix.reindex(tt.o_grid).to_numpy(); d = self.gix.reindex(tt.d_grid).to_numpy()
        ok = ~(np.isnan(o) | np.isnan(d))
        self.o = o[ok].astype(np.int64); self.d = d[ok].astype(np.int64); self.t = tt.t_sec.to_numpy()[ok]
        order = np.argsort(self.d, kind="stable"); self.o, self.d, self.t = self.o[order], self.d[order], self.t[order]
        n = len(M); self.starts = np.searchsorted(self.d, np.arange(n)); self.ends = np.searchsorted(self.d, np.arange(n), side="right")
        # 시설
        F = pd.read_parquet(PKG / "입력/facility/facility_2020_2025_units.parquet",
                            columns=["year", "시설", "cat_A", "분석가능", "grid100_cd"])
        F = F[(F.year == int(year)) & F["분석가능"]]
        self.fac = {}
        for name, (sel, T) in FACSETS.items():
            g = F[sel(F)].grid100_cd.dropna().unique()
            idx = self.gix.reindex(g).dropna().astype(int).to_numpy()
            self.fac[name] = (np.unique(idx), T)
        self.F = F
        # 동 그래프(무작위 구획용)
        self.dong_gdf = X.load_dong().set_index("Dong")
        self.kg = X.all_ku_graphs(year, with_pop=True)
        self.od = X.load_od(year)
        self.lz_map = X.load_lz()["life_zone_id"]
        self.ld_map = X.load_leiden(year)[0]["global_community_id"]
        self.off_k = self.lz_map.groupby(self.dong_gdf["Ku"]).nunique()
        self.n_dong_ku = self.dong_gdf.groupby("Ku").size()

    # ── 도달 ─────────────────────────────────────────────────────────────
    def reach(self, name, u=None):
        """시설 집합 name 에 임계 안 도달. u 주면 같은 단위 안 시설만."""
        idx, T = self.fac[name]
        isf = np.zeros(len(self.M), bool); isf[idx] = True
        m = isf[self.d] & (self.t <= T)
        o, d = self.o[m], self.d[m]
        if u is not None:
            s = u[o] == u[d]; o = o[s]
        r = np.zeros(len(self.M), bool); r[o] = True
        return r

    def cov(self, r): return (self.pop * r).sum() / self.pop.sum()

    def unit_cov(self, u, r):
        num = np.bincount(u, self.pop * r); den = np.bincount(u, self.pop)
        return np.divide(num, den, out=np.zeros_like(num), where=den > 0), den

    def H(self, u, r, tau):
        Cu, _ = self.unit_cov(u, r); Cu = Cu[u]; un = (~r) & self.popped
        return (self.pop[un] * (Cu[un] >= tau)).sum() / max(self.pop[un].sum(), 1)

    def H_curve(self, u, r, C=None, ms=np.linspace(0.5, 1.5, 11)):
        C = self.cov(r) if C is None else C
        return np.array([self.H(u, r, min(C * m, 0.9999)) for m in ms])

    def within_share(self, u, r):
        x = r.astype(float); mu = self.cov(r); tot = (self.pop * (x - mu) ** 2).sum()
        Cu, _ = self.unit_cov(u, r); return 1 - (self.pop * (Cu[u] - mu) ** 2).sum() / tot

    # ── IFR ──────────────────────────────────────────────────────────────
    def ifr(self, s):
        od = self.od; a = s.reindex(od.dong_O).to_numpy(); b = s.reindex(od.dong_D).to_numpy()
        return (od.flow.to_numpy() * (a == b)).sum() / od.flow.sum()

    def dong_series_to_units(self, s):
        return pd.factorize(s.reindex(self.M.dong).to_numpy())[0]

    # ── 무작위 연접 구획 ──────────────────────────────────────────────────
    def random_partition(self, k_total, rng, balance="pop"):
        """구 안에서 연접 병합. k_total 을 구별 동 수에 비례 배분(최소 1, 최대 동 수). k_total==116 이면 공식 개수."""
        if k_total == 116: kk = self.off_k
        else:
            raw = k_total * self.n_dong_ku / self.n_dong_ku.sum()
            kk = np.maximum(1, np.floor(raw)).astype(int)
            rem = k_total - kk.sum(); frac = (raw - np.floor(raw)).sort_values(ascending=False)
            for ku in frac.index:
                if rem <= 0: break
                if kk[ku] < self.n_dong_ku[ku]: kk[ku] += 1; rem -= 1
            kk = kk.clip(upper=self.n_dong_ku)
        s = pd.Series(index=self.dong_gdf.index, dtype=np.int64)
        for ku, g in self.kg.items():
            k = int(kk[ku])
            if k >= g.n: labs = np.arange(g.n)
            elif balance == "pop": labs = X.random_balanced_partition(g.adj, k, rng, size=g.pop)
            else: labs = X.random_connected_partition(g.adj, k, rng)
            s.loc[g.nodes] = labs + ku * 1000
        return s

    # ── 배치 (탐욕법) ─────────────────────────────────────────────────────
    def cover_of(self, j): return self.o[self.starts[j]:self.ends[j]]

    def candidates(self, name="도서관"):
        idx, _ = self.fac[name]; have = set(idx.tolist())
        c = np.where(((self.M["pop"] > 0) | (self.M["biz"] > 0)).to_numpy() & (self.ends > self.starts))[0]
        return np.array([j for j in c if j not in have])

    def place(self, r0, u, tau, K, cand, kcap=600):
        """P1: 1단계 단위별 하한 부족분 최소화(탐욕), 2단계 도달 최대화. u=None 이면 P0. 반환 (선택, K_min, 부족분)."""
        pop = self.pop; cov = r0.copy()
        if u is not None:
            den = np.bincount(u, pop); cnum = np.bincount(u, pop * cov, minlength=len(den)); valid = den > 0
        def shortfall():
            Cu = np.divide(cnum, den, out=np.zeros_like(cnum), where=den > 0)
            return np.maximum(0, tau - Cu)[valid].sum()
        def gain(j):
            idx = self.cover_of(j); new = idx[~cov[idx]]; g = pop[new].sum()
            if u is None or len(new) == 0: return (g, g) if u is None else (0.0, 0.0)
            add = np.bincount(u[new], pop[new], minlength=len(den)); nz = np.nonzero(add)[0]
            C_old = cnum[nz] / den[nz]; C_new = (cnum[nz] + add[nz]) / den[nz]
            return (np.minimum(tau, C_new) - np.minimum(tau, C_old))[valid[nz]].sum(), g
        picks, kmin = [], None
        phase1 = u is not None and shortfall() > 1e-12
        def key(dS, g): return dS * 1e12 + g if phase1 else g
        heap = [(-key(*gain(j)), j) for j in cand]; heapq.heapify(heap)
        while heap:
            if phase1 and len(picks) >= kcap: break
            if not phase1 and len(picks) >= K: break
            negk, j = heapq.heappop(heap); kv = key(*gain(j))
            if heap and kv < -heap[0][0] - 1e-9: heapq.heappush(heap, (-kv, j)); continue
            if kv <= 0 and not phase1: break
            idx = self.cover_of(j); new = idx[~cov[idx]]; cov[new] = True
            if u is not None: cnum += np.bincount(u[new], pop[new], minlength=len(den))
            picks.append(j)
            if phase1 and shortfall() <= 1e-12:
                kmin = len(picks); phase1 = False
                if kmin >= K: break
                heap = [(-gain(jj)[1], jj) for jj in cand]; heapq.heapify(heap)
        return picks, kmin, (None if u is None else shortfall())

    def cov_after(self, r0, picks, K):
        cov = r0.copy()
        for j in picks[:K]: cov[self.cover_of(j)] = True
        return cov

    # ── 나눠 쓰기(2SFCA 격자값) ───────────────────────────────────────────
    def sfca_grid(self, item="공공도서관"):
        g = ds.dataset(PKG / f"결과/main/grid_sfca_{self.year}_100.parquet").to_table(
            filter=(ds.field("b") == "none") & (ds.field("item") == item), columns=["grid_cd", "A_per10k"]).to_pandas()
        A = np.full(len(self.M), np.nan); ix = self.gix.reindex(g.grid_cd).to_numpy(); ok = ~np.isnan(ix)
        A[ix[ok].astype(int)] = g.A_per10k.to_numpy()[ok]
        return np.nan_to_num(A, nan=0.0)

    def unit_mean(self, u, x):
        num = np.bincount(u, self.pop * x); den = np.bincount(u, self.pop)
        return np.divide(num, den, out=np.zeros_like(num), where=den > 0), den

    # ── 행정 대리지표 ────────────────────────────────────────────────────
    def catchment_spans(self, u, name="도서관"):
        """시설 격자마다 임계 안 도달권(인구>0 격자)이 걸치는 단위 수의 평균"""
        idx, T = self.fac[name]; out = []
        for j in idx:
            s, e = self.starts[j], self.ends[j]; oo = self.o[s:e][self.t[s:e] <= T]; oo = oo[self.popped[oo]]
            out.append(len(np.unique(u[oo])) if len(oo) else 0)
        return float(np.mean(out))


def md(df, fmt="{:.3f}"): return X.md_table(df, fmt)
