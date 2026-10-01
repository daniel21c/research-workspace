# -*- coding: utf-8 -*-
"""Word 수식(OMML) 조판. MathML을 Office의 MML2OMML.XSL로 변환해 문단에 넣는다.
- 표시 수식: EQ[키] → 가운데 정렬 수식 + 오른쪽 식 번호(탭 정렬)
- 본문 인라인: 아래 규칙에 맞는 기호(p_o, r_oc^b, w_ij, IFR(b)=…, ΔL, ΔQ)를 인라인 수식으로, 단독 변수 L·Q는 이탤릭으로.
"""
import copy
import re
from pathlib import Path

from docx.enum.text import WD_TAB_ALIGNMENT
from docx.shared import Cm
from lxml import etree

MNS = 'http://www.w3.org/1998/Math/MathML'
_XSL_PATH = Path(r'C:/Program Files/Microsoft Office/root/Office16/MML2OMML.XSL')
_XSL = etree.XSLT(etree.parse(str(_XSL_PATH)))


def omml(inner):
    """MathML 내용(math 태그 안쪽) → m:oMath 요소."""
    root = etree.fromstring(f'<math xmlns="{MNS}">{inner}</math>')
    out = _XSL(root).getroot()
    return out


# ---------------------------------------------------------------- MathML 조각
def mi(x):
    return f'<mi>{x}</mi>' if len(x) == 1 else f'<mi mathvariant="italic">{x}</mi>'


def up(x):
    return f'<mi mathvariant="normal">{x}</mi>'


def mo(x):
    return f'<mo>{x}</mo>'


def mn(x):
    return f'<mn>{x}</mn>'


def sub(b, s):
    return f'<msub>{b}{s}</msub>'


def subsup(b, s, p):
    return f'<msubsup>{b}{s}{p}</msubsup>'


def sup(b, p):
    return f'<msup>{b}{p}</msup>'


def frac(a, b):
    return f'<mfrac><mrow>{a}</mrow><mrow>{b}</mrow></mfrac>'


def row(*xs):
    return '<mrow>' + ''.join(xs) + '</mrow>'


def idx(s):
    return mn(s) if s.isdigit() else mi(s)


def token(base, s=None, p=None):
    b = mi(base)
    if s is not None and p is not None:
        return subsup(b, idx(s), idx(p))
    if s is not None:
        return sub(b, idx(s))
    if p is not None:
        return sup(b, idx(p))
    return b


def bracket(inner, l='[', r=']'):
    return f'<mrow><mo fence="true">{l}</mo>{inner}<mo fence="true">{r}</mo></mrow>'


# ---------------------------------------------------------------- 표시 수식
def eq_L(and_word):
    ind = row(mn('1'), bracket(mo('\u2203') + mi('c') + mo(':') + token('r', 'oc') + mo('=') + mn('1') +
                               f'<mtext>\u2009{and_word}\u2009</mtext>' + token('r', 'oc', 'b') + mo('=') + mn('0')))
    return row(mi('L'), bracket(mi('b'), '(', ')'), mo('='), f'<munder>{mo("\u2211")}{mi("o")}</munder>', token('p', 'o'), mo('\u22c5'), ind)


def eq_dQ():
    lhs = row(up('\u0394'), mi('Q'))
    t1 = frac(row(token('k', 'vz'), mo('\u2212'), token('k', 'va')), mi('m'))
    sq = lambda a, op, b: sup(bracket(row(token('d', a), mo(op), token('d', b)), '(', ')'), mn('2'))  # noqa: E731
    num = row(sq('a', '\u2212', 'v'), mo('+'), sq('z', '+', 'v'), mo('\u2212'), subsup(mi('d'), mi('a'), mn('2')), mo('\u2212'), subsup(mi('d'), mi('z'), mn('2')))
    t2 = frac(num, row(mn('4'), sup(mi('m'), mn('2'))))
    return row(lhs, mo('='), t1, mo('\u2212'), t2)


def eq_IFR():
    s = '<munder>' + mo('∑') + row(mi('i'), mi('j')) + '</munder>'
    ind = row(mn('1'), bracket(row(mi('b'), bracket(mi('i'), '(', ')'), mo('='), mi('b'), bracket(mi('j'), '(', ')'))))
    return row(up('IFR'), bracket(mi('b'), '(', ')'), mo('='), frac(row(s, token('f', 'ij'), ind), row(s, token('f', 'ij'))))


EQ = {'EQ1': (lambda lang: eq_L('and' if lang == 'en' else '이고'), '(1)'), 'EQ3': (lambda lang: eq_IFR(), '(2)'), 'EQ2': (lambda lang: eq_dQ(), '(3)')}  # 번호 = 본문 등장 순서


def display_equation(d, key, lang, text_width_cm=16.0):
    """테두리 없는 1x3 표: 가운데 셀에 oMathPara(디스플레이 모드), 오른쪽 셀에 식 번호."""
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    fn, num = EQ[key]
    t = d.add_table(rows=1, cols=3); t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
    b = OxmlElement('w:tblBorders')
    for e in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement(f'w:{e}'); el.set(qn('w:val'), 'nil'); b.append(el)
    t._tbl.tblPr.append(b)
    for j, w in enumerate((1.6, text_width_cm - 3.2, 1.6)):
        c = t.cell(0, j); c.width = Cm(w)
        va = OxmlElement('w:vAlign'); va.set(qn('w:val'), 'center'); c._tc.get_or_add_tcPr().append(va)
    mid = t.cell(0, 1).paragraphs[0]; mid.alignment = WD_ALIGN_PARAGRAPH.CENTER
    mp = etree.SubElement(mid._p, '{http://schemas.openxmlformats.org/officeDocument/2006/math}oMathPara')
    mp.append(omml(fn(lang)))
    rp = t.cell(0, 2).paragraphs[0]; rp.alignment = WD_ALIGN_PARAGRAPH.RIGHT; rp.add_run(num)
    return t


# ---------------------------------------------------------------- 인라인 수식
_IFR = 'IFR(b) = \u03a3_ij f_ij 1[b(i) = b(j)] / \u03a3_ij f_ij'


def _ifr_mathml():
    s = '<msub>' + mo('\u2211') + row(mi('i'), mi('j')) + '</msub>'
    ind = row(mn('1'), bracket(row(mi('b'), bracket(mi('i'), '(', ')'), mo('='), mi('b'), bracket(mi('j'), '(', ')'))))
    return row(up('IFR'), bracket(mi('b'), '(', ')'), mo('='), s, token('f', 'ij'), ind, mo('/'), s, token('f', 'ij'))


_BASE = r'(' + re.escape(_IFR) + r')|(\u0394[LQ])|(?<![A-Za-z0-9])([A-Za-z])_([A-Za-z0-9]+)(?:\^([A-Za-z0-9]+))?(?![A-Za-z0-9])'
# 단일 문자 변수. 영문 a·A·m·P·W·F는 관사·단위와 겹치므로 문맥 규칙으로만 잡는다.
_Q = "\u2019'"
_SINGLE_EN = (r'|(?<![A-Za-z0-9À-ɏ' + _Q + r'])([LQocbvzdkijNR])(?![A-Za-z0-9À-ɏ' + _Q + r'])'
              r'|(?<=zone )(a)(?![A-Za-z])|(?<=, and )(m)(?= is)'
              r'|\b(A)(?= and P\b)|(?<=A and )(P)\b|\b(W)(?= (?:and|on) F\b)|(?<=W and )(F)\b|(?<=W on )(F)\b')
_SINGLE_KO = r'|(?<![A-Za-z0-9À-ɏ])(?<!\d )(?<!부록 )(?<!표 )([LQocbvzdkijNRaAPWFm])(?![A-Za-z0-9À-ɏ])(?!\.\d)'
INLINE = {'en': re.compile(_BASE + _SINGLE_EN), 'ko': re.compile(_BASE + _SINGLE_KO)}


def math_paragraph(p, text, lang='en'):
    """문단 p(비어 있음)에 text를 넣되, 수식 기호·변수는 인라인 OMML로."""
    pos = 0
    for m in INLINE[lang].finditer(text):
        if m.start() > pos:
            p.add_run(text[pos:m.start()])
        if m.group(1):
            p._p.append(omml(_ifr_mathml()))
        elif m.group(2):
            p._p.append(omml(row(up('\u0394'), mi(m.group(2)[1]))))
        elif m.group(3):
            p._p.append(omml(token(m.group(3), m.group(4), m.group(5))))
        else:
            letter = next(g for g in m.groups()[5:] if g)
            p._p.append(omml(mi(letter)))
        pos = m.end()
    if pos < len(text):
        p.add_run(text[pos:])
    return p
