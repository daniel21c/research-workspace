# -*- coding: utf-8 -*-
"""서울 통계(stat.eseoul.go.kr, KOSIS 엔진) 통계표 CSV 내려받기. 화면 기본 선택 + 수록기간 전체(periodCo=99) 시도."""
import re, sys, json, hashlib, datetime, html
from pathlib import Path
import requests
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'
B = 'https://stat.eseoul.go.kr'

def form_fields(t):
    i = t.find('id="ParamInfo"'); j = t.find('</form>', i); f = t[i:j]
    out = []
    for m in re.finditer(r'<input[^>]*>', f):
        tag = m.group(0)
        n = re.search(r'name="([^"]+)"', tag); v = re.search(r'value="([^"]*)"', tag)
        if n: out.append((n.group(1), html.unescape(v.group(1)) if v else ''))
    return out

def download(tbl, out, org='201', extra=None):
    S = requests.Session(); S.headers['User-Agent'] = UA
    u = f'{B}/statHtml/statHtml.do?orgId={org}&tblId={tbl}&conn_path=I2'
    t = S.get(u, timeout=60).text
    fl = form_fields(t); d = {}
    for k, v in fl: d.setdefault(k, v)
    d.update(dict(view='csv', viewSubKind='2_3', viewKind='2', smblYn='N', periodCo='99'))
    if extra: d.update(extra)
    r = S.post(f'{B}/statHtml/downGrid.do', data=d, headers={'Referer': u}, timeout=120)
    fn = r.json()['file']
    r2 = S.post(f'{B}/statHtml/downNormal.do', data=dict(d, file=fn), headers={'Referer': u}, timeout=120)
    Path(out).write_bytes(r2.content)
    meta = dict(url=u, method='POST /statHtml/downGrid.do → /statHtml/downNormal.do (csv, 화면 기본 선택, periodCo=99)', http_status=r2.status_code,
                content_disposition=requests.utils.unquote(r2.headers.get('Content-Disposition', '')), bytes=len(r2.content),
                sha256=hashlib.sha256(r2.content).hexdigest(), download_utc=datetime.datetime.utcnow().isoformat() + 'Z')
    Path(str(out) + '.metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    return meta, [k for k, _ in fl]
if __name__ == '__main__':
    m, keys = download(sys.argv[1], sys.argv[2]); print(m); print(keys)
