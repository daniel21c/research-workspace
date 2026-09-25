# -*- coding: utf-8 -*-
"""
x8_citywide_leiden.py — D 구 경계 없이 서울 전체(424동) Leiden
===============================================================
정본은 구마다 따로 나눈다(생활권이 구 계획단위이므로). 여기서는 구 경계를 풀면 이동 구조가 어떻게 묶이는지,
그리고 "서울 전체가 스스로 고르는 개수"가 116 과 얼마나 다른지 본다.

절차
  - 424동 무방향 그래프 (w_ij + w_ji, 자기 루프 포함 — 정본과 같은 구성). 서울 안 통행 전체.
  - 해상도 γ = 0.2~40 (로그 간격 100개; 116개 근처는 γ≈15) 마다 Leiden(RBConfiguration) 을 n_iter 번(기본 100, 반복별 시드) 돌려 Q 최대 분할을 취함.
    (탐색용이라 3,000회 합의는 하지 않음)
  - 해상도마다: 개수 k, Q, 서울 IFR(= 같은 커뮤니티 안 통행 / 서울 전체 통행), 두 개 이상 구에 걸친 커뮤니티 수,
    그런 커뮤니티에 속한 동 비율, 공간적으로 끊긴 커뮤니티 수, ARI(공식 생활권 / Leiden 정본 / 자치구 25개).
  - 비교 기준: 공식 116, Leiden 정본 116, 자치구 25 의 서울 IFR·Q.
  - 보고: Q 최대 해상도, k 가 116 에 가장 가까운 해상도, k 가 25 에 가장 가까운 해상도.

출력: output/exploration/x8/citywide_scan.csv, citywide_labels.csv(세 해상도), citywide_reference.csv, x8_report.md
실행: python x8_citywide_leiden.py --workers 8 [--n-iter 100] [--seed 20260924]
"""
import argparse
import concurrent.futures as cf
from xcommon import *

RES = np.round(np.geomspace(0.2, 40.0, 100), 4)   # 서울 전체는 116개 근처에 γ≈15 가 필요 → 로그 간격
_G = {}


def city_graph(year):
    dong, od = load_dong(), load_od(year)
    nodes = dong["Dong"].tolist(); ix = {d: i for i, d in enumerate(nodes)}; n = len(nodes)
    od = od[od["dong_O"].isin(ix) & od["dong_D"].isin(ix)]
    W = np.zeros((n, n))
    np.add.at(W, (od["dong_O"].map(ix).values, od["dong_D"].map(ix).values), od["flow"].values)
    S = W + W.T
    iu = np.triu_indices(n, 1)
    m = S[iu] > 0
    E = np.vstack([np.column_stack([np.arange(n), np.arange(n)])[np.diag(W) > 0], np.column_stack([iu[0][m], iu[1][m]])])
    w = np.concatenate([np.diag(W)[np.diag(W) > 0], S[iu][m]])
    sidx = dong.sindex
    adj = [sorted(int(j) for j in sidx.query(geom, predicate="touches") if j != i) for i, geom in enumerate(dong.geometry.values)]
    return dong, W, E.astype(np.int64), w, adj


def _init(year):
    _G["year"] = year
    _G["dong"], _G["W"], _G["E"], _G["w"], _G["adj"] = city_graph(year)


def scan_one(args):
    j, res, n_iter, seed = args
    import igraph as ig, leidenalg
    E, w = _G["E"], _G["w"]; n = len(_G["W"])
    G = ig.Graph(n=n, edges=E.tolist()); G.es["weight"] = list(map(float, w))
    best = (-1, None)
    for k in range(n_iter):
        p = leidenalg.find_partition(G, leidenalg.RBConfigurationVertexPartition, resolution_parameter=float(res),
                                     weights="weight", seed=int(seed + j * n_iter + k) % (2**31 - 1))
        lab = np.asarray(p.membership); q = modularity_q(E, w, lab)
        if q > best[0]:
            best = (q, lab)
    return j, res, best[0], best[1]


def describe(lab, W, E, w, dong, adj, lz, lei):
    lab = np.asarray(pd.factorize(lab)[0])
    ku = dong["Ku"].values
    nk = pd.Series(ku).groupby(lab).nunique()
    cross = nk[nk > 1].index
    broken = 0
    for c in np.unique(lab):
        mem = set(np.where(lab == c)[0]); start = next(iter(mem)); seen = {start}; st = [start]
        while st:
            u = st.pop()
            for v in adj[u]:
                if v in mem and v not in seen:
                    seen.add(v); st.append(v)
        broken += len(seen) < len(mem)
    same = lab[:, None] == lab[None, :]
    return {"k": int(lab.max()) + 1, "Q": modularity_q(E, w, lab), "IFR_서울": float((W * same).sum() / W.sum()),
            "구걸침_커뮤니티": int(len(cross)), "구걸침_동비율": float(np.isin(lab, cross).mean()), "끊긴_커뮤니티": int(broken),
            "ARI_vs_공식": ari(lab, lz), "ARI_vs_Leiden": ari(lab, lei), "ARI_vs_자치구": ari(lab, pd.factorize(ku)[0])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=C.N_WORKERS)
    ap.add_argument("--n-iter", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20260924)
    a = ap.parse_args()
    lzmap = load_lz()
    rows, refs, labs = [], [], []
    for year in YEARS:
        dong, W, E, w, adj = city_graph(year)
        m, _ = load_leiden(year)
        lz = pd.factorize(lzmap["life_zone_id"].reindex(dong["Dong"]).values)[0]
        lei = pd.factorize(m["global_community_id"].reindex(dong["Dong"]).values)[0]
        for name, lab in (("공식 생활권", lz), ("Leiden 정본", lei), ("자치구", pd.factorize(dong["Ku"].values)[0])):
            refs.append({"year": year, "경계": name, **describe(lab, W, E, w, dong, adj, lz, lei)})
        tasks = [(j, r, a.n_iter, a.seed + int(year) * 1_000_000) for j, r in enumerate(RES)]
        out = {}
        with cf.ProcessPoolExecutor(max_workers=a.workers, initializer=_init, initargs=(year,)) as ex:
            for i, f in enumerate(cf.as_completed([ex.submit(scan_one, t) for t in tasks]), 1):
                j, res, q, lab = f.result(); out[j] = (res, lab)
                if i % 10 == 0:
                    print(f"{year} {i}/{len(tasks)}", flush=True)
        for j in sorted(out):
            res, lab = out[j]
            rows.append({"year": year, "resolution": res, **describe(lab, W, E, w, dong, adj, lz, lei)})
        d = pd.DataFrame([r for r in rows if r["year"] == year])
        pick = {"Q최대": d["Q"].idxmax(), "k≈116": (d["k"] - C.N_LZ).abs().idxmin(), "k≈25": (d["k"] - 25).abs().idxmin()}
        for tag, i in pick.items():
            res = d.loc[i, "resolution"]; lab = out[int(np.where(RES == res)[0][0])][1]
            labs += [{"year": year, "선택": tag, "resolution": res, "Dong": dd, "Ku": kk, "label": int(l)}
                     for dd, kk, l in zip(dong["Dong"], dong["Ku"], pd.factorize(lab)[0])]
    d = pd.DataFrame(rows); ref = pd.DataFrame(refs)
    save(d, "citywide_scan", "x8"); save(ref, "citywide_reference", "x8"); save(pd.DataFrame(labs), "citywide_labels", "x8")
    cols = ["k", "Q", "IFR_서울", "구걸침_커뮤니티", "구걸침_동비율", "끊긴_커뮤니티", "ARI_vs_공식", "ARI_vs_Leiden", "ARI_vs_자치구"]
    L = ["# x8 — D 서울 전체 424동 Leiden (구 경계 없음)", "",
         f"해상도 {RES[0]}~{RES[-1]} ({len(RES)}개) × {a.n_iter}회, 해상도마다 Q 최대 분할. 탐색용(합의 없음).", ""]
    for y in YEARS:
        x = d[d.year == y].reset_index(drop=True)
        sel = pd.concat([x.loc[[x["Q"].idxmax()]].assign(선택="Q최대"),
                         x.loc[[(x["k"] - C.N_LZ).abs().idxmin()]].assign(선택="k≈116"),
                         x.loc[[(x["k"] - 25).abs().idxmin()]].assign(선택="k≈25")])
        r = ref[ref.year == y].rename(columns={"경계": "선택"}).assign(resolution=np.nan)
        L += [f"## {y}", "", md_table(pd.concat([sel, r])[["선택", "resolution"] + cols]), "",
              f"- Q 최대 해상도 γ={sel.iloc[0]['resolution']}: {int(sel.iloc[0]['k'])}개, 그중 구에 걸친 커뮤니티 "
              f"{int(sel.iloc[0]['구걸침_커뮤니티'])}개 (동 {sel.iloc[0]['구걸침_동비율']:.0%})",
              f"- k≈116 (γ={sel.iloc[1]['resolution']}, {int(sel.iloc[1]['k'])}개): 구에 걸친 커뮤니티 {int(sel.iloc[1]['구걸침_커뮤니티'])}개, "
              f"ARI 공식 {sel.iloc[1]['ARI_vs_공식']:.3f} / Leiden 정본 {sel.iloc[1]['ARI_vs_Leiden']:.3f}", ""]
    (out_dir("x8") / "x8_report.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join([l for l in L if l.startswith("- ") or l.startswith("## ")]))


if __name__ == "__main__":
    main()
