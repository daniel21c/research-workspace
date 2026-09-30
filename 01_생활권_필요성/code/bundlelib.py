# -*- coding: utf-8 -*-
"""묶음 배치 공통 모듈 (exp14 의 설정·상태·방식을 함수로; C3·C4·C6 에서 재사용). 2026-10-01.
exp14_bundle_place.py 와 같은 정의를 쓴다(결과 재현 점검: ctx 로 COL 을 다시 돌려 exp14 값과 대조)."""
import heapq
import numpy as np, pandas as pd
from r1lib import Year

class Ctx:
    def __init__(self, bundle, year, P_EXP=4.0, years=None, pop_year=None, variant="", fac_year=None, kscale=1.0):
        """years: {'2020': Year, '2025': Year} 재사용. pop_year: 인구·기존 시설은 이 연도 것으로(시간 외 표본용)."""
        self.bundle, self.year, self.P = bundle, year, P_EXP
        Y = years or {}
        for y in ("2020", "2025"):
            if y not in Y: Y[y] = Year(y)
        self.Y = Y; Yr = self.Yr = Y[year]; Y20, Y25 = Y["2020"], Y["2025"]; self.variant = variant
        Yf = Y[fac_year] if fac_year else Yr   # 기존 시설·후보지 연도(시간 외 표본: 2020 시설 + 2025 인구·망)
        self.pop = Yr.pop; n = self.n = len(Yr.M); self.popped = Yr.popped
        def gidx(sel): return np.unique(Yf.gix.reindex(Yf.F[sel(Yf.F)].grid100_cd.dropna().unique()).dropna().astype(int).to_numpy())
        def growth(name):
            k = len(Y25.fac[name][0]) - len(Y20.fac[name][0]); k = k if k >= 3 else max(3, int(round(0.1 * len(Y20.fac[name][0])))); return max(1, int(round(k * kscale)))
        if bundle == "seoul":
            T = 900 if "T900" in variant else 600
            park = Y["2025"].fac["공원_UPIS2024"][0] if "upis_park" in variant else Yf.fac["공원"][0]
            sports = Yf.fac["공공체육_엄격"][0] if "strict_sports" in variant else Yf.fac["공공체육"][0]
            youth = Yf.fac["청소년수련시설"][0] if "no_childcenter" in variant else np.union1d(Yf.fac["청소년수련시설"][0], Yf.fac["지역아동센터"][0])
            C = [("공원", park, []), ("도서관", Yf.fac["도서관"][0], [("도서관", growth("도서관"))]),
                 ("노인여가", Yf.fac["노인이용시설"][0], [("노인이용시설", growth("노인이용시설"))]),
                 ("청소년아동", youth, [("청소년수련시설", growth("청소년수련시설"))]),
                 ("보육", gidx(lambda f: f["시설"] == "어린이집"), [("국공립어린이집5분", growth("국공립어린이집5분"))])]
            if "no_sports" not in variant: C.append(("공공체육", sports, [("공공체육", growth("공공체육"))]))
        else:
            T = 900
            C = [(c, gidx(lambda f, c=c: f.cat_A == c), []) for c in ["교육", "보육·복지", "생활서비스", "소매", "의료"]]
            C += [("문화", gidx(lambda f: f.cat_A == "문화"), [("도서관", growth("도서관")), ("공공문화시설", growth("공공문화시설"))]),
                  ("행정·안전", gidx(lambda f: f.cat_A == "행정·안전"), [("주민센터", growth("주민센터"))])]
        self.T = T; self.CATS = C; self.NC = len(C); self.names = [c[0] for c in C]
        m = Yr._t_all <= T; self.Eo, self.Ed = Yr._o_all[m], Yr._d_all[m]
        self.Es = np.searchsorted(self.Ed, np.arange(n)); self.Ee = np.searchsorted(self.Ed, np.arange(n), side="right")
        self.R0 = np.zeros((self.NC, n), bool)
        for k, (_, idx, _) in enumerate(C):
            isf = np.zeros(n, bool); isf[idx] = True; self.R0[k, self.Eo[isf[self.Ed]]] = True
        self.SUB = {}
        for k, (_, idx, subs) in enumerate(C):
            for s, K in subs:
                have = set(Yf.fac[s][0].tolist()) | set(idx.tolist())
                c = np.where(((Yf.M["pop"] > 0) | (Yf.M["biz"] > 0)).to_numpy() & (self.Ee > self.Es))[0]
                self.SUB[s] = (k, K, np.array([j for j in c if j not in have]))
        self.candALL = np.unique(np.concatenate([v[2] for v in self.SUB.values()])); self.candset = {s: set(v[2].tolist()) for s, v in self.SUB.items()}
        self.cnt0 = self.R0.sum(0); self.comp0 = (self.cnt0 == self.NC) & self.popped
        o = np.argsort(self.cnt0 + (~self.popped) * 99, kind="stable"); cw = np.cumsum(self.pop[o]); cut = self.cnt0[o][min(np.searchsorted(cw, 0.2 * cw[-1]), n - 1)]
        self.POOR = (self.cnt0 <= cut) & self.popped
        ud = Yr.units["동"]; dd = np.bincount(ud, self.pop); mcd = np.bincount(ud, self.pop * self.cnt0) / np.maximum(dd, 1)
        oo = np.argsort(mcd[dd > 0]); cw = np.cumsum(dd[dd > 0][oo]); self.tau_c = 0.6 * mcd[dd > 0][oo][np.searchsorted(cw, cw[-1] / 2)]
    def f(self, c): return (c / self.NC) ** self.P
    def cover(self, j): return self.Eo[self.Es[j]:self.Ee[j]]

class State:
    def __init__(self, ctx, R0=None, B=None):
        self.c = ctx; self.R = (ctx.R0 if R0 is None else R0).copy(); self.cnt = self.R.sum(0); self.B = dict(B) if B else {s: v[1] for s, v in ctx.SUB.items()}; self.placed = {s: [] for s in ctx.SUB}
    def center_set(self, j, allowed=None):
        out, used = [], set(); c = self.c
        for s, (k, K, _) in c.SUB.items():
            if allowed is not None and s not in allowed: continue
            if k in used or self.B[s] <= 0 or j not in c.candset[s]: continue
            idx = c.cover(j)
            if np.any(~self.R[k, idx] & c.popped[idx]): out.append(s); used.add(k)
        return out
    def gain(self, j, S):
        c = self.c; parts = [c.cover(j)[~self.R[c.SUB[s][0], c.cover(j)]] for s in S]
        g = np.concatenate(parts) if parts else np.array([], int)
        if len(g) == 0: return 0.0
        u, cc = np.unique(g, return_counts=True); old = self.cnt[u]; return float((c.pop[u] * (c.f(old + cc) - c.f(old))).sum())
    def apply(self, j, S):
        c = self.c
        for s in S:
            k = c.SUB[s][0]; idx = c.cover(j); new = idx[~self.R[k, idx]]; self.R[k, new] = True; self.cnt[new] += 1; self.B[s] -= 1; self.placed[s].append(int(j))

def greedy_free(st, allowed=None):
    c = st.c; heap = [(-st.gain(j, S), int(j)) for j in c.candALL for S in [st.center_set(j, allowed)] if S]; heapq.heapify(heap); moves = 0
    while heap and any(st.B[s] > 0 for s in c.SUB if allowed is None or s in allowed):
        _, j = heapq.heappop(heap); S = st.center_set(j, allowed)
        if not S: continue
        g = st.gain(j, S)
        if heap and g < -heap[0][0] - 1e-9: heapq.heappush(heap, (-g, j)); continue
        if g <= 0: break
        st.apply(j, S); moves += 1
        if moves % 25 == 0: heap = [(-st.gain(jj, SS), int(jj)) for jj in c.candALL for SS in [st.center_set(jj, allowed)] if SS]; heapq.heapify(heap)
    return st

def ind_type(st, s, unit=None, tau=None):
    """유형 s 하나를 자기 범주 도달 최대화로 배치. unit·tau 주면 단위별 하한(부족분 합 최소화) 먼저."""
    c = st.c; k, K, cand = c.SUB[s]; pop = c.pop
    if unit is not None:
        den = np.bincount(unit, pop); v = den > 0; nz = unit.max() + 1
        while st.B[s] > 0:
            num = np.bincount(unit, pop * st.R[k], minlength=nz); C = np.divide(num, den, out=np.ones(nz), where=v)
            if not np.any(v & (C < tau - 1e-9)): break
            best, bg = None, 0.0
            for j in cand:
                if j not in c.candset[s] or st.B[s] <= 0: continue
                idx = c.cover(j); new = idx[~st.R[k, idx]]
                if len(new) == 0: continue
                add = np.bincount(unit[new], pop[new], minlength=nz); nzz = np.nonzero(add)[0]
                g = (np.minimum(tau, (num[nzz] + add[nzz]) / den[nzz]) - np.minimum(tau, num[nzz] / den[nzz]))[v[nzz]].sum()
                if g > bg: best, bg = j, g
            if best is None: break
            st.apply(best, [s])
    heap = [(-(pop[c.cover(j)[~st.R[k, c.cover(j)]]].sum()), int(j)) for j in cand]; heapq.heapify(heap)
    while heap and st.B[s] > 0:
        _, j = heapq.heappop(heap); idx = c.cover(j); g = pop[idx[~st.R[k, idx]]].sum()
        if heap and g < -heap[0][0] - 1e-9: heapq.heappush(heap, (-g, j)); continue
        if g <= 0: break
        st.apply(j, [s])
    return st

def run_IND(ctx):
    st = State(ctx)
    for s in ctx.SUB: ind_type(st, s)
    return st

def run_FLOOR(ctx, u):
    st = State(ctx); c = ctx; pop = c.pop; den = np.bincount(u, pop); v = den > 0; nz = u.max() + 1; members = {z: c.candALL[u[c.candALL] == z] for z in range(nz)}; stuck = set()
    while any(st.B[s] > 0 for s in c.SUB):
        mc = np.divide(np.bincount(u, pop * st.cnt, minlength=nz), den, out=np.full(nz, 99.0), where=v)
        below = [z for z in np.argsort(mc) if v[z] and mc[z] < c.tau_c - 1e-9 and z not in stuck]
        if not below: break
        z = below[0]; best, bg, bS = None, 0.0, None
        for j in members[z]:
            S = st.center_set(j)
            if not S: continue
            add = 0.0
            for s in S:
                nw = c.cover(j)[~st.R[c.SUB[s][0], c.cover(j)]]; add += pop[nw[u[nw] == z]].sum()
            g = min(add / den[z], c.tau_c - mc[z])
            if g > bg: best, bg, bS = j, g, S
        if best is None: stuck.add(z); continue
        st.apply(best, bS)
    return greedy_free(st)

def summarize(st, extra=None):
    c = st.c; pop = c.pop; comp = (st.cnt == c.NC) & c.popped
    r = {"완결률": (pop * comp).sum() / pop.sum(), "평균범주수": (pop * st.cnt).sum() / pop.sum(), "취약20_완결률": pop[c.POOR & comp].sum() / pop[c.POOR].sum()}
    if extra: r.update(extra)
    return r
