# -*- coding: utf-8 -*-
"""원고 본문 수치 대조(k24) 회귀시험: 현재 원고는 통과하고, 숫자를 틀리게 바꾸거나 주장을 지우면 반드시 실패한다."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C
import k24_text_claims as K

_mds = sorted(C.MK.glob("국토계획_원고_*.md"))
assert _mds, f"원고 md가 없다: {C.MK}"
MD = _mds[-1].read_text(encoding="utf-8")
V = K.values()


def test_current_manuscript_passes():
    bad = [c["ID"] for c in K.check(MD, V) if not c["일치"]]
    assert not bad, bad


def test_changed_number_fails():   # 외부 재점검의 변조 예: 39.6 → 99.9, 48개 → 999개
    for old, new in (("39.6", "99.9"), (f"{V['common']}개", "999개")):
        assert old in MD
        bad = [c["ID"] for c in K.check(MD.replace(old, new), V) if not c["일치"]]
        assert bad, (old, new)


def test_every_claim_detects_mutation_and_deletion():
    r = K.mutation_test(MD, V)
    assert r["숫자변조"] == r["숫자변조_감지"] > 0 and r["삭제"] == r["삭제_감지"] > 0 and not r["감지못함"], r


def test_claim_is_context_bound():   # 같은 숫자가 다른 절에만 있으면 통과하지 않는다
    sec = K.sections(MD)
    exp = [e for i, w, e in K.spec(V) if i == "r5_2020"][0]
    moved = MD.replace(exp, "").replace("# Ⅵ. 결론\n", "# Ⅵ. 결론\n" + exp + "\n")
    r = {c["ID"]: c["일치"] for c in K.check(moved, V)}
    assert not r["r5_2020"]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    n = 0
    for name, f in list(globals().items()):
        if name.startswith("test_") and callable(f):
            f(); print("ok", name); n += 1
    print(f"{n}/{n} 통과")
