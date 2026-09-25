# -*- coding: utf-8 -*-
"""
x5_sbm_mdl.py — B2 확률블록모형(SBM) + 최소 기술 길이(MDL)로 개수 고르기  [graph-tool 필요 → 클라우드에서 실행]
=====================================================================================================================
Leiden 의 해상도 γ 같은 손잡이 없이, "이 통행 네트워크를 가장 짧게 설명하는 묶음 수"를 고른다 (Peixoto 2014, 2017).
  - 모형: 차수 보정 SBM(deg_corr=True), 간선 가중치(통행량 f_ij+f_ji, 자기 루프 포함)를 실수-지수분포 공변량으로 모형화.
  - minimize_blockmodel_dl 을 여러 번(기본 20) 돌려 기술 길이(entropy, nats)가 가장 작은 해를 채택 → 블록 수 B*.
  - 공식 개수로 B 를 고정한 해의 기술 길이와 비교: ΔDL = DL(B=공식 k) − DL(B*). 작을수록 공식 개수도 데이터로 설명 가능.
  - pp: 동류(assortative)만 허용하는 계획분할 모형(Zhang & Peixoto 2020). 통행량/scale 을 정수 다중간선으로 쓴다(scale 에 따라 결과가 달라짐).
  - 채택된 분할의 IFR·Q, 공식 생활권·Leiden 정본과의 ARI.
주의: 구 하나가 동 10~30개라 표본이 작다. MDL 은 증거가 약하면 적은 블록 수를 고르는 경향이 있다.

실행 (graph-tool 환경): micromamba run -r /home/claude/mamba -n gt python x5_sbm_mdl.py [--restarts 20] [--model exp|lognormal|pp] [--scale 31]
출력: output/exploration/x5/sbm_kstar_{model}.csv, sbm_labels_{model}.csv, x5_report_{model}.md
"""
import sys, argparse
from pathlib import Path
import numpy as np
import pandas as pd

EXP = Path(__file__).resolve().parent
sys.path.insert(0, str(EXP.parent / "scripts"))
import config as C                                                  # noqa: E402
from s03_leiden_consensus import ari, modularity_q                 # noqa: E402

OUT = C.OUTPUT_DIR / "exploration" / "x5"


def ku_matrix(od, nodes):
    ix = {d: i for i, d in enumerate(nodes)}; n = len(nodes)
    sub = od[od["dong_O"].isin(ix)]
    tot = sub.groupby("dong_O")["flow"].sum().reindex(nodes).fillna(0).values
    inn = sub[sub["dong_D"].isin(ix)]
    W = np.zeros((n, n))
    np.add.at(W, (inn["dong_O"].map(ix).values, inn["dong_D"].map(ix).values), inn["flow"].values)
    return W, tot


def edges_of(W):
    S = W + W.T; n = len(W); E, w = [], []
    for i in range(n):
        if W[i, i] > 0:
            E.append((i, i)); w.append(W[i, i])
        for j in range(i + 1, n):
            if S[i, j] > 0:
                E.append((i, j)); w.append(S[i, j])
    return np.asarray(E), np.asarray(w)


def fit(E, w, n, restarts, B=None, model="exp", scale=31.0):
    """model: 'exp' = 가중치 실수-지수 공변량, 'lognormal' = log(가중치) 실수-정규 공변량,
              'pp' = 동류(assortative) 계획분할 모형 PPBlockState, 통행량/scale 을 반올림한 정수 다중간선으로 사용"""
    import graph_tool.all as gt
    g = gt.Graph(directed=False); g.add_vertex(n)
    g.add_edge_list(E)
    if model == "pp":
        ew = g.new_ep("int"); ew.a = np.maximum(1, np.rint(w / scale)).astype(int)
    else:
        ew = g.new_ep("double")
    if model == "pp":
        rt = None
    elif model == "exp":
        ew.a = w / w.mean(); rt = "real-exponential"        # 척도만 맞춤 (지수분포 모수는 척도 불변)
    else:
        ew.a = np.log(w); rt = "real-normal"
    best = None
    for r in range(restarts):
        gt.seed_rng(1000 + r); np.random.seed(1000 + r)
        if model == "pp":
            kw = dict(state=gt.PPBlockState, state_args=dict(eweight=ew, deg_corr=True))
        else:
            kw = dict(state=gt.WeightedBlockState, state_args=dict(rec=[ew], rec_types=[rt], deg_corr=True))
        if B is not None:
            kw["multilevel_mcmc_args"] = dict(B_min=B, B_max=B)
        st = gt.minimize_blockmodel_dl(g, **kw)
        dl = st.entropy()
        if best is None or dl < best[0]:
            best = (dl, np.array(st.get_blocks().a, copy=True))   # .a 는 뷰 → 상태가 해제되면 덮어써짐. 반드시 복사
    lab = pd.factorize(best[1])[0]
    return best[0], lab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--restarts", type=int, default=20)
    ap.add_argument("--model", choices=["exp", "lognormal", "pp"], default="exp")
    ap.add_argument("--scale", type=float, default=31.0, help="pp: 통행량을 이 값으로 나눈 정수를 간선 수로 (31 = 하루 평균 통행)")
    a = ap.parse_args()
    tag = a.model if a.model != "pp" else f"pp_s{int(a.scale)}"
    OUT.mkdir(parents=True, exist_ok=True)
    lz = pd.read_csv(C.DONG_LZ_MAP).set_index("Dong")
    rows, labs = [], []
    for year in C.YEARS:
        od = pd.read_parquet(C.od_daily_path(year))
        ld = pd.read_csv(C.LEIDEN_OUT / year / "metrics" / f"leiden_mapping_{year}.csv").set_index("Dong")
        for ku in sorted(C.TARGET_COMMUNITIES):
            nodes = sorted(lz.index[lz["Ku"] == ku]); k0 = C.TARGET_COMMUNITIES[ku]
            W, tot = ku_matrix(od, nodes); E, w = edges_of(W)
            dl_best, lab = fit(E, w, len(nodes), a.restarts, model=a.model, scale=a.scale)
            dl_k0, lab_k0 = fit(E, w, len(nodes), max(5, a.restarts // 2), B=k0, model=a.model, scale=a.scale)
            ifr = lambda L: float((W * (L[:, None] == L[None, :])).sum() / tot.sum())
            off = pd.factorize(lz.loc[nodes, "life_zone_id"].values)[0]
            lei = pd.factorize(ld.loc[nodes, "global_community_id"].values)[0]
            rows.append({"year": year, "구": C.KU_NAME[ku], "공식k": k0, "k_SBM": int(lab.max()) + 1,
                         "DL_best": dl_best, "DL_공식k": dl_k0, "ΔDL": dl_k0 - dl_best,
                         "IFR_SBM": ifr(lab), "Q_SBM": modularity_q(E, w, lab), "IFR_SBM공식k": ifr(lab_k0),
                         "ARI_SBM_vs_공식": ari(lab, off), "ARI_SBM_vs_Leiden": ari(lab, lei),
                         "ARI_SBM공식k_vs_Leiden": ari(lab_k0, lei)})
            for d, l1, l2 in zip(nodes, lab, lab_k0):
                labs.append({"year": year, "Dong": d, "Ku": ku, "sbm_free": int(l1), "sbm_k0": int(l2)})
            print(year, C.KU_NAME[ku], "B*", rows[-1]["k_SBM"], "공식", k0, f"ΔDL {rows[-1]['ΔDL']:.1f}", flush=True)
    d = pd.DataFrame(rows)
    d["model"] = tag
    d.to_csv(OUT / f"sbm_kstar_{tag}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(labs).to_csv(OUT / f"sbm_labels_{tag}.csv", index=False, encoding="utf-8-sig")
    L = [f"# x5 — B2 SBM·MDL 로 개수 고르기 (모형: {tag})", "",
         (f"동류 계획분할 모형(PPBlockState, 차수 보정), 간선 수 = round(통행량/{a.scale:g}). " if a.model == "pp" else
          f"차수 보정 SBM(WeightedBlockState), 가중치 공변량 = {'실수-지수' if a.model == 'exp' else 'log 가중치의 실수-정규'}. ") + f"재시작 {a.restarts}회 중 기술 길이 최소 해. ΔDL = DL(공식 개수 고정) − DL(최적), 단위 nats.", ""]
    for y in C.YEARS:
        x = d[d.year == y]
        L += [f"## {y}", "",
              f"- SBM 개수 합계 {x['k_SBM'].sum()} (공식 116). 공식과 같은 구 {int((x['k_SBM'] == x['공식k']).sum())}/25, "
              f"적은 구 {int((x['k_SBM'] < x['공식k']).sum())}/25, 많은 구 {int((x['k_SBM'] > x['공식k']).sum())}/25",
              f"- ΔDL 중앙값 {x['ΔDL'].median():.1f} nats (ΔDL<3 인 구 {int((x['ΔDL'] < 3).sum())}/25)",
              f"- ARI 평균: SBM vs 공식 {x['ARI_SBM_vs_공식'].mean():.3f}, SBM vs Leiden {x['ARI_SBM_vs_Leiden'].mean():.3f}, "
              f"SBM(공식 k 고정) vs Leiden {x['ARI_SBM공식k_vs_Leiden'].mean():.3f}", ""]
        cols = ["구", "공식k", "k_SBM", "ΔDL", "IFR_SBM", "Q_SBM", "ARI_SBM_vs_공식", "ARI_SBM_vs_Leiden", "ARI_SBM공식k_vs_Leiden"]
        L.append("| " + " | ".join(cols) + " |"); L.append("|" + "---|" * len(cols))
        for _, r in x.iterrows():
            L.append("| " + " | ".join(f"{r[c]:.3f}" if isinstance(r[c], float) else str(r[c]) for c in cols) + " |")
        L.append("")
    (OUT / f"x5_report_{tag}.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join([l for l in L if l.startswith("- ") or l.startswith("## ")]))


if __name__ == "__main__":
    main()
