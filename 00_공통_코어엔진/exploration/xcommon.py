# -*- coding: utf-8 -*-
"""
xcommon.py — 탐색 분석(x1~x9) 공통 함수
==========================================
정본(data/, output/leiden/{연도}/)을 읽기만 한다. 결과는 모두 output/exploration/ 에 쓴다.
"""
import sys, json, glob
from pathlib import Path

import numpy as np
import pandas as pd

EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXP_DIR.parent / "scripts"))
import config as C                                   # noqa: E402
from s03_leiden_consensus import ari, modularity_q, canonical_labels   # noqa: E402,F401

OUT = C.OUTPUT_DIR / "exploration"
CACHE = OUT / "_cache"
YEARS = list(C.YEARS)
POP_YEAR = {"2020": "2019", "2025": "2024"}          # 이동 1월 자료 ↔ 직전 연도 11.1 기준 인구
KU_ORDER = sorted(C.TARGET_COMMUNITIES)


def out_dir(name: str) -> Path:
    p = OUT / name
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── 정본 읽기 ────────────────────────────────────────────────────────────────
def load_dong():
    import geopandas as gpd
    g = gpd.read_file(C.DONG_GPKG, layer="epsg5179").sort_values("Dong").reset_index(drop=True)
    g["Dong"] = g["Dong"].astype(int); g["Ku"] = g["Ku"].astype(int)
    return g


def load_lz():
    return pd.read_csv(C.DONG_LZ_MAP).set_index("Dong")


def load_od(year):
    od = pd.read_parquet(C.od_daily_path(year))
    od["dong_O"] = od["dong_O"].astype(int); od["dong_D"] = od["dong_D"].astype(int)
    return od


def load_leiden(year):
    d = C.LEIDEN_OUT / year
    m = pd.read_csv(d / "metrics" / f"leiden_mapping_{year}.csv").set_index("Dong")
    met = pd.read_csv(d / "metrics" / f"leiden_metrics_{year}.csv").set_index("ku_code")
    return m, met


def load_scan(year, ku):
    f = glob.glob(str(C.LEIDEN_OUT / year / "resolution_scan_logs" / f"{ku}_*_{year}.csv"))
    return pd.read_csv(f[0]) if f else None


# ── 인구 (SGIS 행정구역 총인구 → 424동) ──────────────────────────────────────
def _sgis_dir():
    cands = [C.THESIS_ROOT / "시설데이터 구축" / "시설데이터_패키지" / "SGIS_인구경계_2019_2024" / "03_행정구역",
             C.CORE_DIR / "sgis"]                    # (클라우드 점검용 복사본)
    for c in cands:
        if c.exists():
            return c
    raise SystemExit("SGIS 인구 자료 폴더를 찾을 수 없습니다: " + " / ".join(map(str, cands)))


def load_pop(year):
    """year = 이동자료 연도('2020'/'2025'). SGIS 426동(2025 경계) 총인구를 대표점 공간결합으로 424동에 합산."""
    import geopandas as gpd
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / f"pop_dong424_{year}.csv"
    if cache.exists():
        return pd.read_csv(cache).set_index("Dong")["pop"]
    base = _sgis_dir()
    py = POP_YEAR[year]
    stat = [p for p in base.rglob(f"*{py}년_인구총괄(총인구).csv")]
    shp = [p for p in base.rglob("bnd_dong_00_2025_2Q.shp")]
    if not stat or not shp:
        raise SystemExit(f"SGIS 파일 없음: {py}년 총인구 csv 또는 2025 동 경계")
    s = pd.read_csv(stat[0], header=None, encoding="cp949", dtype=str, names=["yr", "code", "item", "val"])
    s = s[(s["item"] == "to_in_001") & (s["code"].str.len() == 8)]
    s["pop"] = pd.to_numeric(s["val"])
    b = gpd.read_file(shp[0], encoding="cp949")
    code_col = [c for c in b.columns if c.upper() in ("ADM_CD", "ADM_DR_CD")][0]
    b = b[b[code_col].astype(str).str.startswith("11")].to_crs(C.CRS_PROJECTED)
    b["pt"] = b.geometry.representative_point()
    pts = gpd.GeoDataFrame(b[[code_col]].rename(columns={code_col: "code"}), geometry=b["pt"], crs=b.crs)
    pts["code"] = pts["code"].astype(str)
    dong = load_dong()
    j = gpd.sjoin(pts, dong[["Dong", "geometry"]], predicate="within", how="left")
    miss = j["Dong"].isna().sum()
    if miss:
        raise SystemExit(f"SGIS 동 대표점 {miss}개가 424동 폴리곤 밖에 있음")
    j = j.merge(s[["code", "pop"]], on="code", how="left")
    pop = j.groupby("Dong")["pop"].sum().astype(float)
    pop = pop.reindex(dong["Dong"]).fillna(0.0)
    tot_stat = float(s["pop"].sum())
    if abs(pop.sum() - tot_stat) > 1:
        raise SystemExit(f"인구 합 불일치 {pop.sum()} vs {tot_stat}")
    pop.rename("pop").reset_index().to_csv(cache, index=False)
    return pop


# ── 구 단위 그래프 ────────────────────────────────────────────────────────────
class KuGraph:
    """구 하나의 동 목록, 방향 OD 행렬 W, 무방향 간선(+자기 루프), 인접, 인구"""
    def __init__(self, ku, dong, od, pop=None):
        self.ku = ku
        g = dong[dong["Ku"] == ku].sort_values("Dong").reset_index(drop=True)
        self.nodes = g["Dong"].tolist()
        self.names = g["ADM_NM"].tolist()
        self.n = n = len(self.nodes)
        ix = {d: i for i, d in enumerate(self.nodes)}
        self.ix = ix
        sub = od[od["dong_O"].isin(ix)]
        self.total_out = sub.groupby("dong_O")["flow"].sum().reindex(self.nodes).fillna(0).values   # 서울 전체로의 출발
        inn = sub[sub["dong_D"].isin(ix)]
        W = np.zeros((n, n))
        np.add.at(W, (inn["dong_O"].map(ix).values, inn["dong_D"].map(ix).values), inn["flow"].values)
        self.W = W
        self.total_in_from_seoul = od[od["dong_D"].isin(ix)].groupby("dong_D")["flow"].sum().reindex(self.nodes).fillna(0).values
        S = W + W.T
        E, Wt = [], []
        for i in range(n):
            if C.INCLUDE_SELF_LOOPS and W[i, i] > 0:
                E.append((i, i)); Wt.append(W[i, i])
            for j in range(i + 1, n):
                if S[i, j] > 0:
                    E.append((i, j)); Wt.append(S[i, j])
        self.edges = np.asarray(E, dtype=np.int64).reshape(-1, 2)
        self.weights = np.asarray(Wt, dtype=float)
        # 인접 (공간)
        sidx = g.sindex
        self.adj = [sorted(int(j) for j in sidx.query(geom, predicate="touches") if j != i) for i, geom in enumerate(g.geometry.values)]
        self.geom = g
        self.pop = None if pop is None else pop.reindex(self.nodes).values.astype(float)

    def igraph(self, edges=None, weights=None):
        import igraph as ig
        e = self.edges if edges is None else edges
        w = self.weights if weights is None else weights
        G = ig.Graph(n=self.n, edges=e.tolist(), directed=False)
        G.es["weight"] = list(map(float, w))
        return G

    def ifr(self, labels):
        """구 IFR = Σ(출발·도착 같은 커뮤니티) / Σ(출발이 구인 서울 전체 통행). 정본 s03 과 같은 정의"""
        same = labels[:, None] == labels[None, :]
        return float((self.W * same).sum() / self.total_out.sum())

    def zone_ifr(self, labels):
        """커뮤니티별 (출발 기준) IFR"""
        out = {}
        for c in np.unique(labels):
            m = labels == c
            out[int(c)] = float(self.W[np.ix_(m, m)].sum() / self.total_out[m].sum()) if self.total_out[m].sum() > 0 else 0.0
        return out

    def q(self, labels):
        return modularity_q(self.edges, self.weights, np.asarray(labels))

    def labels_from_mapping(self, series):
        v = series.reindex(self.nodes).values
        return np.asarray(pd.factorize(v)[0])


def all_ku_graphs(year, with_pop=False):
    dong, od = load_dong(), load_od(year)
    pop = load_pop(year) if with_pop else None
    return {ku: KuGraph(ku, dong, od, pop) for ku in KU_ORDER}


# ── 무작위 연결 분할 (A2) ────────────────────────────────────────────────────
def random_connected_partition(adj, k, rng, max_tries=200):
    """인접 그래프에서 k개의 연결된 조각으로 무작위 분할 (무작위 씨앗 + 무작위 경계 확장)."""
    n = len(adj)
    for _ in range(max_tries):
        seeds = rng.choice(n, size=k, replace=False)
        lab = -np.ones(n, dtype=int)
        lab[seeds] = np.arange(k)
        frontier = [(s, u) for s in seeds for u in adj[s] if lab[u] < 0]
        while frontier:
            t = rng.integers(len(frontier))
            s, u = frontier.pop(t)
            if lab[u] >= 0:
                continue
            lab[u] = lab[s]
            frontier.extend((u, v) for v in adj[u] if lab[v] < 0)
        if (lab >= 0).all():
            return lab
    return None


def random_balanced_partition(adj, k, rng, size=None, max_tries=200):
    """크기가 고르게 되도록 키우는 무작위 연결 분할: 매 단계 현재 가장 작은(size 합 기준) 조각이 인접 동 하나를 무작위로 가져간다.
    size=None 이면 동 개수, 인구 배열을 주면 인구 기준으로 균형."""
    n = len(adj)
    w = np.ones(n) if size is None else np.asarray(size, float)
    for _ in range(max_tries):
        seeds = rng.choice(n, size=k, replace=False)
        lab = -np.ones(n, dtype=int); lab[seeds] = np.arange(k)
        tot = w[seeds].copy()
        active = set(range(k))
        while (lab < 0).any() and active:
            c = min(active, key=lambda r: tot[r] + rng.random() * 1e-9)
            members = np.where(lab == c)[0]
            cand = sorted({u for v in members for u in adj[v] if lab[u] < 0})
            if not cand:
                active.discard(c); continue
            u = cand[rng.integers(len(cand))]
            lab[u] = c; tot[c] += w[u]
        if (lab >= 0).all():
            return lab
    return None


def md_table(df: pd.DataFrame, floatfmt="{:.4f}") -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.astype(object).iterrows():        # object 로 바꿔 정수 열이 실수로 바뀌지 않게
        out.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else
                                      (floatfmt.format(v) if isinstance(v, float) else str(v)) for v in r) + " |")
    return "\n".join(out)


def save(df: pd.DataFrame, name: str, sub: str):
    d = out_dir(sub)
    df.to_csv(d / f"{name}.csv", index=False, encoding="utf-8-sig")
    return d / f"{name}.csv"
