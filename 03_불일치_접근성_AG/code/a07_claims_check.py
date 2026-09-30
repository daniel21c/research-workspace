# -*- coding: utf-8 -*-
"""원고 수치 대조: manuscript/values_used.json(원고에 채운 값)을 요약 JSON이 아니라 원자료 표(상태·표본·쌍 CSV)에서 다시 계산한 값과 비교한다.
또 원고 docx 본문에 그 값이 실제로 들어갔는지, 원고에 남은 {키} 자리표시가 없는지 확인한다.
실행: python code/a07_claims_check.py     출력: results/claims_check.json (하나라도 불일치면 종료 코드 1)
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from docx import Document
from scipy.stats import rankdata

AG = Path(__file__).resolve().parents[1]; RES = AG / 'results'; MS = AG / 'manuscript'


def presid(v, C):
    X = np.column_stack([np.ones(len(v))] + [rankdata(c) for c in C]); r = rankdata(v); return r - X @ np.linalg.lstsq(X, r, rcond=None)[0]


def pcorr(d, cols):
    return float(np.corrcoef(presid(d.W.to_numpy(), [d[c].to_numpy() for c in cols]), presid(d.F.to_numpy(), [d[c].to_numpy() for c in cols]))[0, 1])


def num(s):
    return float(str(s).replace(',', '').replace('−', '-').replace('+', ''))


def main():
    V = json.load(open(MS / 'values_used.json', encoding='utf-8')); rows = []

    def chk(key, expect, tol=0.5):
        got = num(V[key]); ok = abs(got - expect) <= tol; rows.append({'key': key, 'manuscript': V[key], 'recomputed': expect, 'ok': bool(ok)})

    for y in (2020, 2025):
        t = str(y)[2:]; R = pd.read_csv(RES / str(y) / 'a01_states.csv'); fl = R[R.strategy == 'FLOW'].sort_values('k'); rd = R[R.strategy == 'RAND']; K = int(fl.k.max())
        L0 = float(fl[fl.k == 0].L.iloc[0]); chk(f'L{t}', L0)
        end_r = rd[rd.k == K]; chk(f'rm{t}', end_r.dL.median()); chk(f'fe{t}', float(fl[fl.k == K].dL.iloc[0])); chk(f'fmin{t}', -fl.dL.min()); chk(f'fk{t}', float(fl.loc[fl.dL.idxmin(), 'k']), 0)
        chk(f'fn{t}', float(fl[fl.k == K].new.iloc[0])); chk(f'fr{t}', float(fl[fl.k == K].resolved.iloc[0])); chk(f'rn{t}', end_r.new.median()); chk(f'rr{t}', end_r.resolved.median())
        chk(f'fp{t}', float(fl[fl.k == K].moved_pop.iloc[0])); chk(f'rp{t}', end_r.moved_pop.median()); chk(f'nm{t}', K, 0)
        chk(f'ifr{t}', 100 * float(fl[fl.k == 0].IFR.iloc[0]), 0.05); chk(f'fifr{t}', 100 * float(fl[fl.k == K].IFR.iloc[0]), 0.05); chk(f'rifr{t}', 100 * end_r.IFR.median(), 0.05)
        below = [int(k) for k in range(1, K + 1) if (rd[rd.k == k].dL > float(fl[fl.k == k].dL.iloc[0])).all()]
        first = next(k for k in range(1, K + 1) if all(j in below for j in range(k, K + 1))); chk(f'k{t}', first, 0)
        s10 = 100 * float((rd[rd.k == 10].dL < float(fl[fl.k == 10].dL.iloc[0])).mean()); chk(f's10_{t}', s10, 0.5)
        P = pd.read_csv(RES / str(y) / 'a03_ensemble_plans.csv'); E = P[P.plan.str.startswith('E')]; LZ = float(P[P.plan == 'LZ'].L.iloc[0])
        assert abs(LZ - L0) < 0.5, 'a01과 a03의 공식 L 불일치'
        chk(f'g{t}', float((E.L > LZ + 0.5).sum()), 0); chk(f'med{t}', E.L.median()); chk(f'dmed{t}', E.L.median() - LZ); chk(f'dmin{t}', E.L.min() - LZ)
        O = pd.read_csv(RES / str(y) / 'a04_mechanism_pairs.csv'); chk(f'np{t}', len(O), 0); chk(f'nd{t}', O.i.nunique(), 0)
        chk(f'pc{t}', pcorr(O, ['A', 'P']), 0.0005); chk(f'pz{t}', pcorr(O, ['A', 'P', 'logZpop', 'logZemp']), 0.0005)
        for key, c in (('h', '의료'), ('r', '소매'), ('s', '생활서비스')):
            dd = O.dropna(subset=[f'F_{c}']).rename(columns={'F': 'Fm'}).rename(columns={f'F_{c}': 'F'}); chk(f'{key}{t}', pcorr(dd, ['A', 'P', 'logZpop', 'logZemp']), 0.005)
    # 원고 본문 반영 확인
    texts = {}
    for f in ('AG_manuscript_anonymised.docx', 'AG_한국어_원고.docx'):
        d = Document(MS / f); tx = '\n'.join(p.text for p in d.paragraphs) + '\n'.join(c.text for t in d.tables for r in t.rows for c in r.cells); texts[f] = tx
        left = re.findall(r'\{[a-zA-Z0-9_]+\}', tx); rows.append({'key': f'{f}: unfilled placeholders', 'manuscript': left, 'recomputed': [], 'ok': not left})
    sys.path.insert(0, str(AG / 'code')); import a06_text_en as EN, a06_text_ko as KO  # noqa: E401
    used = {f: set(re.findall(r'\{(\w+)\}', ' '.join(x for _, x in M.BODY))) for f, M in (('AG_manuscript_anonymised.docx', EN), ('AG_한국어_원고.docx', KO))}
    for r in list(rows):
        if r['key'] in V and isinstance(V[r['key']], str) and len(V[r['key']]) >= 3:
            for f, tx in texts.items():
                if r['key'] not in used[f]:
                    continue
                rows.append({'key': f'{f} contains {r["key"]}', 'manuscript': V[r['key']], 'recomputed': None, 'ok': V[r['key']] in tx})
    bad = [r for r in rows if not r['ok']]
    out = {'n_checks': len(rows), 'n_fail': len(bad), 'fails': bad, 'checks': rows}
    (RES / 'claims_check.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    print(json.dumps({'n_checks': len(rows), 'n_fail': len(bad), 'fails': bad[:10]}, ensure_ascii=False, default=str))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
