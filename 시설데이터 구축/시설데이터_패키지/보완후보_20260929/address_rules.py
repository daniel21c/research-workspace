"""Pure address parser extracted from reviewed mb.py; no credentials/network."""
import re,unicodedata
import pandas as pd
def nfc(s):
    return unicodedata.normalize('NFC', str(s)) if s is not None else ''

def clean(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ''
    s = nfc(s).replace('\u3000', ' ').replace('\xa0', ' ')
    return re.sub('\\s+', ' ', s).strip()

GU = ['종로구', '중구', '용산구', '성동구', '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구', '노원구', '은평구', '서대문구', '마포구', '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구', '관악구', '서초구', '강남구', '송파구', '강동구']

ROAD_RE = re.compile('([가-힣A-Za-z0-9·.]+(?:로|길))\\s*,?\\s*(?:지하\\s*)?(\\d+)(?:\\s*-\\s*(\\d+))?(?!\\d)(?!\\s*(?:가(?:\\s|$|\\d)|번?길(?![가-힣])|로(?![가-힣])))')

JIBUN_RE = re.compile('(?<![0-9A-Za-z가-힣])([가-힣][가-힣0-9·.]*(?:동|가|리))\\s*(산\\s*)?(\\d+)(?:\\s*-\\s*(\\d+))?(?!\\d)')

# Prevent substring parses: 구로1동 must not become road 구로 1, and
# 명동13길 must not become parcel 명동 13. A subnumber cannot be backtracked away.
ROAD_RE = re.compile(ROAD_RE.pattern + r'(?![0-9가-힣-])(?!\s*-\s*\d)')
JIBUN_RE = re.compile(JIBUN_RE.pattern + r'(?![0-9가-힣-])(?!\s*-\s*\d)')

def _norm_variants(a):
    a = clean(a)
    a0 = re.sub('\\([^)]*\\)', ' ', a)
    a0 = re.sub('\\s+', ' ', a0).strip()
    a0 = re.sub('(로|길)\\s+(\\d+[가-힣]?)\\s*(번?길)(?=\\s|\\d|$|,)', '\\1\\2\\3', a0)
    a0 = re.sub('(\\d)\\s*번지', '\\1', a0)
    a0 = re.sub('(?<![가-힣])(' + '|'.join(sorted(GU, key=len, reverse=True)) + ')(?=[가-힣0-9])', '\\1 ', a0)
    vs = [a0]
    a1 = re.sub('([가-힣]+\\d*(?:동|가))(?=[가-힣]{2,}\\d*[가-힣]?(?:로|길)\\s*\\d)', '\\1 ', a0)
    a2 = re.sub('(?<![가-힣])([가-힣]{2,}(?<![구시동읍면리가]))\\s+(\\d+[가-힣]?(?:번?길))(?=\\s|\\d|$|,)', '\\1\\2', a0)
    for v in (a1, a2):
        if v not in vs:
            vs.append(v)
    return vs

def parse_addr(a):
    """주소를 '시 구 도로명 번호' 또는 '시 구 동 번지' 검색문과 기대 번호로 바꾼다(여러 후보, 순서대로 시도)."""
    out = []
    seen = set()
    for a0 in _norm_variants(a):
        for c in _parse_one(a0):
            if c['query'] not in seen:
                seen.add(c['query'])
                out.append(c)
    return [c for c in out if c['kind'] == 'road'] + [c for c in out if c['kind'] == 'jibun']

OTHER_SIDO = re.compile('(경기도|경기|인천광역시|인천시|인천|강원도|강원특별자치도|충청북도|충청남도|충북|충남|부산광역시|대구광역시|대전광역시|광주광역시|울산광역시|세종특별자치시|전라북도|전북특별자치도|전라남도|경상북도|경상남도|제주특별자치도)\\s+([가-힣]+(?:시|군|구))(?:\\s+([가-힣]+구)(?=\\s))?')

def _parse_one(a0):
    out = []
    mo = OTHER_SIDO.search(a0)
    if mo:
        pre = ' '.join((x for x in mo.groups() if x))
        rest = a0[mo.end():]
        for c in _parse_one_core(rest, pre):
            out.append(c)
        return out
    gu = next((g for g in GU if re.search('(^|\\s)' + g + '(\\s|$)', a0)), '')
    return _parse_one_core(a0, ' '.join((x for x in ['서울특별시', gu] if x)))

def _parse_one_core(a0, prefix):
    out = []
    m = ROAD_RE.search(a0)
    if m:
        q = prefix
        q = f'{q} {m.group(1)} {m.group(2)}' + (f'-{m.group(3)}' if m.group(3) else '')
        out.append(dict(kind='road', query=q.strip(), road=m.group(1), main=int(m.group(2)), sub=int(m.group(3)) if m.group(3) else 0))
    m2 = JIBUN_RE.search(a0)
    if m2 and (not re.search('(로|길)$', m2.group(1))):
        dongs = [m2.group(1)]
        mh = re.match('^(\\D+?)\\d+동$', m2.group(1))
        if mh:
            dongs.append(mh.group(1) + '동')
        for dg in dongs:
            q = prefix
            q = f"{q} {dg} {('산 ' if m2.group(2) else '')}{m2.group(3)}" + (f'-{m2.group(4)}' if m2.group(4) else '')
            out.append(dict(kind='jibun', query=q.strip(), dong=dg, main=int(m2.group(3)), sub=int(m2.group(4)) if m2.group(4) else 0, san=bool(m2.group(2))))
    return out
