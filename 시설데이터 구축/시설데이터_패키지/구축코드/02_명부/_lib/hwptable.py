# -*- coding: utf-8 -*-
"""HWP(5.0 바이너리)·HWPX 표 추출기: 표마다 [행][열] 셀 텍스트 목록을 돌려준다(병합 셀은 좌상단에만 값)."""
import olefile, zlib, struct, zipfile, re

TAG_PARA_HEADER, TAG_PARA_TEXT, TAG_CTRL_HEADER, TAG_LIST_HEADER = 66, 67, 71, 72


def _para_text(b):
    t = []; j = 0
    while j < len(b):
        c = struct.unpack_from('<H', b, j)[0]
        if c in (1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23):
            j += 16; continue
        if c in (4, 5, 6, 7, 8, 9, 19, 20):
            j += 16; t.append(' ' if c == 9 else ''); continue
        if c < 32:
            t.append('\n' if c in (10, 13) else ''); j += 2; continue
        t.append(chr(c)); j += 2
    return ''.join(t)


def _records(d):
    i = 0
    while i < len(d):
        h = struct.unpack_from('<I', d, i)[0]; tag = h & 0x3ff; lvl = (h >> 10) & 0x3ff; sz = h >> 20; i += 4
        if sz == 0xfff:
            sz = struct.unpack_from('<I', d, i)[0]; i += 4
        yield tag, lvl, d[i:i + sz]
        i += sz


def hwp_tables(fn):
    o = olefile.OleFileIO(fn)
    comp = o.openstream('FileHeader').read()[36] & 1
    secs = sorted([s for s in o.listdir() if s[0] == 'BodyText'], key=lambda s: int(s[1][7:]))
    tables = []
    for s in secs:
        d = o.openstream(s).read()
        if comp:
            d = zlib.decompress(d, -15)
        stack = []  # 열린 표: dict(level, cells{(r,c):text}, cur)
        ctx = []
        for tag, lvl, b in _records(d):
            while stack and lvl <= stack[-1]['level']:
                tables.append(stack.pop())
            if tag == TAG_CTRL_HEADER and b[:4] == b' lbt':
                stack.append(dict(level=lvl, cells={}, cur=None, ctx=list(ctx[-12:])))
                continue
            if not stack:
                if tag == TAG_PARA_TEXT:
                    tx = _para_text(b).strip()
                    if tx:
                        ctx.append(tx)
                continue
            t = stack[-1]
            if tag == TAG_LIST_HEADER and lvl == t['level'] + 1:
                col, row, cs, rs = struct.unpack_from('<HHHH', b, 8)
                t['cur'] = (row, col); t['cells'][(row, col)] = []
            elif tag == TAG_PARA_TEXT and t['cur'] is not None and lvl >= t['level'] + 2:
                t['cells'][t['cur']].append(_para_text(b).strip())
        while stack:
            tables.append(stack.pop())
    return [dict(ctx=t['ctx'], grid=_grid(t['cells'])) for t in tables if t['cells']]


def _grid(cells):
    R = max(r for r, c in cells) + 1; C = max(c for r, c in cells) + 1
    g = [[''] * C for _ in range(R)]
    for (r, c), v in cells.items():
        g[r][c] = ' '.join(x for x in v if x).strip()
    return g


def hwpx_tables(fn):
    z = zipfile.ZipFile(fn)
    out = []
    for n in sorted(z.namelist(), key=lambda s: (len(s), s)):
        if not (n.startswith('Contents/section') and n.endswith('.xml')):
            continue
        x = z.read(n).decode('utf-8', 'ignore')
        out.extend(_hwpx_parse(x))
    return out


def _hwpx_parse(x):
    # 중첩 표 고려: 태그 토큰 순회
    res = []
    stack = []
    ctx = []
    in_t_out = False
    for m in re.finditer(r'<(/?)hp:(tbl|tc|cellAddr|t)\b([^>]*?)(/?)>|(<[^>]*>)|([^<]+)', x):
        close, tag, attrs, selfclose, other, text = m.groups()
        if other is not None:
            if ('fwSpace' in other or 'lineBreak' in other or 'tab' in other) and stack and stack[-1].get('in_t') \
                    and stack[-1].get('cur') is not None:
                stack[-1]['cells'][stack[-1]['cur']].append(' ')
            continue
        if text is not None:
            import html as _h
            text = _h.unescape(text)
        if text is not None:
            if stack and stack[-1].get('in_t') and stack[-1].get('cur') is not None:
                stack[-1]['cells'][stack[-1]['cur']].append(text)
            elif not stack and in_t_out and text.strip():
                ctx.append(text.strip())
            continue
        if tag == 't' and not stack:
            if not selfclose:
                in_t_out = not close
            continue
        if tag == 'tbl':
            if not close:
                stack.append(dict(cells={}, cur=None, in_t=False, pend=None, ctx=list(ctx[-12:])))
            else:
                t = stack.pop()
                if t['cells']:
                    res.append(dict(ctx=t['ctx'], grid=_grid({k: [''.join(v)] for k, v in t['cells'].items()})))
        elif not stack:
            continue
        elif tag == 'tc':
            if not close:
                stack[-1]['pend'] = []
                stack[-1]['cur'] = ('pending', id(m))
                stack[-1]['cells'][stack[-1]['cur']] = []
            else:
                stack[-1]['cur'] = None
        elif tag == 'cellAddr':
            a = dict(re.findall(r'(\w+)="([^"]*)"', attrs))
            t = stack[-1]
            if t['cur'] is not None:
                v = t['cells'].pop(t['cur'])
                t['cur'] = (int(a['rowAddr']), int(a['colAddr']))
                t['cells'][t['cur']] = v
        elif tag == 't':
            if selfclose:
                continue
            stack[-1]['in_t'] = not close
            if not close and stack[-1]['cur'] is not None and stack[-1]['cells'][stack[-1]['cur']]:
                stack[-1]['cells'][stack[-1]['cur']].append(' ')
    return res
