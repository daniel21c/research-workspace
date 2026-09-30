# -*- coding: utf-8 -*-
"""묶음 배치 공통 모듈 (exp14·17·18·19 가 공유). 2026-10-01, 10-02 외부 검토(F02·F04·F06) 반영.
- greedy_free: 목적 f(c)=(c/NC)^P 는 볼록이라 다른 유형을 놓은 뒤 한 후보의 한계이득이 커질 수 있다. 이전에는 지연 갱신 heap(예전 이득을
  상한으로 가정, 25회마다 전체 재계산)을 써서 정확한 탐욕(매 단계 최대 한계이득)이 아니었다(검토 F02, 가상 반례 재현). 지금은 배치할 때마다
  새로 닿은 격자에 걸린 후보와 예산이 소진된 유형의 후보를 전부 다시 계산한다. 한계이득은 그 격자들의 cnt·R 에만 의존하므로 이 재계산은 완전하다
  (test_greedy_exact.py 로 전수 재계산과 일치 확인).
- 결손집단: 이전 "취약 20%"는 도달 범주 수가 정수라 절단점의 동률을 모두 넣어 실제 인구의 45~47%였다(검토 F04). 이제 (a) 결손집단 = 배치 전
  도달 범주 수 ≤ cut 인 동률 포함 집단(인구 비중을 함께 보고), (b) 하위20 = 동률 구간에 분수 가중치를 준 정확한 하위 20% 를 둘 다 낸다.
- run_FLOOR: 하한 단계가 끝난 뒤 미달 권역 수·막힌 권역·잔여 예산을 st.floor_info 에 남긴다(검토 F06: 이 하한은 평균 도달 범주 수 하한이지 완결률 하한이 아니다)."""
import heapq
import numpy as np, pandas as pd
from r1lib import Year

class Ctx:
    def __init__(self, bundle, year, P_EXP=4.0, years=None, pop_year=None, variant="", fac_year=None, kscale=1.0):
        """years: {'2020': Year, '2025': Year} 재사용. fac_year: 기존 시설·후보지를 이 연도 것으로(조건부 전이 평가용). variant: T900|T720|strict_sports|no_sports|no_childcenter|upis_park."""
        self.bundle, self.year, self.P = bundle, year, P_EXP
        Y = years or {}
        for y in ("2020", "2025"):
            if y not in Y: Y[y] = Year(y)
        self.Y = Y; Yr = self.Yr = Y[year]; Y20, Y25 = Y["2020"], Y["2025"]; self.variant = variant
        Yf = Y[fac_year] if fac_year else Yr
        self.pop = Yr.pop; n = self.n = len(Yr.M); self.popped = Yr.popped
        def gidx(sel): return np.unique(Yf.gix.reindex(Yf.F[sel(Yf.F)].grid100_cd.dropna().unique()).dropna().astype(int).to_numpy())
        def growth(name):
            k = len(Y25.fac[name][0]) - len(Y20.fac[name][0]); k = k if k >= 3 else max(3, int(round(0.1 * len(Y20.fac[name][0])))); return max(1, int(round(k * kscale)))
        if bundle == "seoul":
            T = 900 if "T900" in variant else (720 if "T720" in variant else 600)
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
        # 역색인: 출발 격자 i → i 에 닿는 목적지(후보) j (정확 탐욕의 영향 후보 찾기용)
        oo = np.argsort(self.Eo, kind="stable"); self._Do = self.Ed[oo]; eo_s = self.Eo[oo]
        self.Os = np.searchsorted(eo_s, np.arange(n)); self.Oe = np.searchsorted(eo_s, np.arange(n), side="right")
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
        self.candpos = -np.ones(n, int); self.candpos[self.candALL] = np.arange(len(self.candALL))
        self.cnt0 = self.R0.sum(0); self.comp0 = (self.cnt0 == self.NC) & self.popped
        # 결손집단(동률 포함)과 정확한 하위 20%(분수 가중)
        tot = self.pop.sum(); o = np.argsort(self.cnt0 + (~self.popped) * 99, kind="stable"); cw = np.cumsum(self.pop[o])
        cut = int(self.cnt0[o][min(np.searchsorted(cw, 0.2 * tot), n - 1)]); self.POOR_cut = cut
        self.POOR = (self.cnt0 <= cut) & self.popped; self.POOR_share = self.pop[self.POOR].sum() / tot
        below = (self.cnt0 < cut) & self.popped; tie = (self.cnt0 == cut) & self.popped
        alpha = (0.2 * tot - self.pop[below].sum()) / max(self.pop[tie].sum(), 1e-9); alpha = float(np.clip(alpha, 0, 1))
        self.W20 = np.where(below, self.pop, np.where(tie, alpha * self.pop, 0.0)); self.W20_alpha = alpha
        ud = Yr.units["동"]; dd = np.bincount(ud, self.pop); mcd = np.bincount(ud, self.pop * self.cnt0) / np.maximum(dd, 1)
        oo = np.argsort(mcd[dd > 0]); cw = np.cumsum(dd[dd > 0][oo]); self.tau_c = 0.6 * mcd[dd > 0][oo][np.searchsorted(cw, cw[-1] / 2)]
    def f(self, c): return (c / self.NC) ** self.P
    def cover(self, j): return self.Eo[self.Es[j]:self.Ee[j]]
    def dests_of(self, grids):
        """격자들에 닿는 목적지(후보 격자) 집합."""
        if len(grids) == 0: return np.array([], int)
        parts = [self._Do[self.Os[i]:self.Oe[i]] for i in grids]
        d = np.unique(np.concatenate(parts)); return d[self.candpos[d] >= 0]

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
        """배치. 새로 닿게 된 격자(범주별 합집합)를 돌려준다."""
        c = self.c; news = []
        for s in S:
            k = c.SUB[s][0]; idx = c.cover(j); new = idx[~self.R[k, idx]]; self.R[k, new] = True; self.cnt[new] += 1; self.B[s] -= 1; self.placed[s].append(int(j)); news.append(new)
        return np.unique(np.concatenate(news)) if news else np.array([], int)

def greedy_free(st, allowed=None):
    """정확한 탐욕: 매 단계 모든 후보 중 최대 한계이득. 배치 후 새로 닿은 격자에 걸린 후보와 예산 소진 유형의 후보만 다시 계산(완전)."""
    c = st.c; cand = c.candALL; G = np.full(len(cand), -1.0)
    def score(p):
        j = int(cand[p]); S = st.center_set(j, allowed); G[p] = st.gain(j, S) if S else -1.0
    for p in range(len(cand)): score(p)
    while any(st.B[s] > 0 for s in c.SUB if allowed is None or s in allowed):
        p = int(np.argmax(G)); g = G[p]
        if g <= 0: break
        j = int(cand[p]); S = st.center_set(j, allowed)
        if not S: G[p] = -1.0; continue
        new = st.apply(j, S)
        aff = set(c.dests_of(new).tolist()); aff.add(j)
        for s in S:
            if st.B[s] <= 0: aff |= c.candset[s]
        for jj in aff: score(c.candpos[jj])
    return st

def ind_floor(st, s, unit, tau):
    """유형 s: 단위별 자기 범주 도달 하한(부족분 합 최소화) 단계만."""
    c = st.c; k, K, cand = c.SUB[s]; pop = c.pop
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
    return st

def ind_max(st, s):
    """유형 s: 자기 범주 미도달 인구 최대화(MCLP 탐욕). 도달 목적은 한계이득이 줄기만 하므로 지연 갱신 heap 이 정확하다."""
    c = st.c; k, K, cand = c.SUB[s]; pop = c.pop
    heap = [(-(pop[c.cover(j)[~st.R[k, c.cover(j)]]].sum()), int(j)) for j in cand]; heapq.heapify(heap)
    while heap and st.B[s] > 0:
        _, j = heapq.heappop(heap); idx = c.cover(j); g = pop[idx[~st.R[k, idx]]].sum()
        if heap and g < -heap[0][0] - 1e-9: heapq.heappush(heap, (-g, j)); continue
        if g <= 0: break
        st.apply(j, [s])
    return st

def ind_type(st, s, unit=None, tau=None):
    """유형 s 하나를 자기 범주 도달 최대화로 배치. unit·tau 주면 단위별 하한 먼저."""
    if unit is not None: ind_floor(st, s, unit, tau)
    return ind_max(st, s)

def run_IND(ctx):
    st = State(ctx)
    for s in ctx.SUB: ind_type(st, s)
    return st

def run_FLOOR(ctx, u, tau=None):
    """단위 u 의 평균 도달 범주 수 하한(τ = ctx.tau_c) 을 먼저 채우고 남은 예산은 정확 탐욕. 하한 단계 결과를 st.floor_info 에 기록."""
    st = State(ctx); c = ctx; tau = c.tau_c if tau is None else tau; pop = c.pop; den = np.bincount(u, pop); v = den > 0; nz = u.max() + 1; members = {z: c.candALL[u[c.candALL] == z] for z in range(nz)}; stuck = set()
    mc = np.divide(np.bincount(u, pop * st.cnt, minlength=nz), den, out=np.full(nz, 99.0), where=v); n_before = int((v & (mc < tau - 1e-9)).sum())
    while any(st.B[s] > 0 for s in c.SUB):
        mc = np.divide(np.bincount(u, pop * st.cnt, minlength=nz), den, out=np.full(nz, 99.0), where=v)
        below = [z for z in np.argsort(mc) if v[z] and mc[z] < tau - 1e-9 and z not in stuck]
        if not below: break
        z = below[0]; best, bg, bS = None, 0.0, None
        for j in members[z]:
            S = st.center_set(j)
            if not S: continue
            add = 0.0
            for s in S:
                nw = c.cover(j)[~st.R[c.SUB[s][0], c.cover(j)]]; add += pop[nw[u[nw] == z]].sum()
            g = min(add / den[z], tau - mc[z])
            if g > bg: best, bg, bS = j, g, S
        if best is None: stuck.add(z); continue
        st.apply(best, bS)
    mc = np.divide(np.bincount(u, pop * st.cnt, minlength=nz), den, out=np.full(nz, 99.0), where=v)
    st.floor_info = {"하한τ": float(tau), "하한_미달권역_전": n_before, "하한_미달권역_후": int((v & (mc < tau - 1e-9)).sum()), "하한_막힌권역": len(stuck),
                     "하한단계_사용": int(sum(c.SUB[s][1] - st.B[s] for s in c.SUB)), "하한단계_잔여예산": int(sum(st.B[s] for s in c.SUB))}
    return greedy_free(st)

def run_ZONE(ctx, u):
    """단위마다 중심 하나씩 순환 배분(권역을 배분 몫으로 쓰는 규칙)."""
    st = State(ctx); c = ctx; pop = c.pop; nz = u.max() + 1; members = {z: c.candALL[u[c.candALL] == z] for z in range(nz)}; den = np.bincount(u, pop); v = den > 0
    order = list(np.argsort(np.divide(np.bincount(u, pop * c.cnt0, minlength=nz), den, out=np.full(nz, 99.0), where=v))); stuck = set()
    while any(st.B[s] > 0 for s in c.SUB):
        prog = False
        for z in order:
            if z in stuck or not v[z] or len(members[z]) == 0: continue
            best, bg, bS = None, 0.0, None
            for j in members[z]:
                S = st.center_set(j)
                if S:
                    g = st.gain(j, S)
                    if g > bg: best, bg, bS = j, g, S
            if best is None: stuck.add(z); continue
            st.apply(best, bS); prog = True
            if not any(st.B[s] > 0 for s in c.SUB): break
        if not prog: break
    return st

def summarize(st, extra=None):
    c = st.c; pop = c.pop; comp = (st.cnt == c.NC) & c.popped
    r = {"완결률": (pop * comp).sum() / pop.sum(), "평균범주수": (pop * st.cnt).sum() / pop.sum(),
         "결손집단_완결률": pop[c.POOR & comp].sum() / pop[c.POOR].sum(), "결손집단_인구비중": c.POOR_share, "결손집단_cut": c.POOR_cut,
         "하위20_완결률": (c.W20 * comp).sum() / c.W20.sum()}
    if getattr(st, "floor_info", None): r.update(st.floor_info)
    if extra: r.update(extra)
    return r
