# -*- coding: utf-8 -*-
"""data.go.kr 파일데이터 다운로더(보건의료 승격 작업 공용). 현재판/과거판 모두. 메타데이터 json 기록."""
import re, json, hashlib, datetime, sys
from pathlib import Path
import requests
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'
B = 'https://www.data.go.kr'

def page_info(pk, S=None):
    S = S or requests.Session(); S.headers['User-Agent'] = UA
    t = S.get(f'{B}/data/{pk}/fileData.do', timeout=60).text
    dpk = re.search(r'id="publicDataDetailPk"[^>]*value="([^"]+)"', t).group(1)
    title = re.search(r'<title>([^<|]+)', t).group(1).strip()
    h = S.post(f'{B}/tcs/dss/selectHistAndCsvData.do', data=dict(publicDataPk=pk, publicDataDetailPk=dpk), timeout=60).text
    hist = re.findall(r'data-public-pk="([^"]+)"\s*data-public-detail-sn="(\d+)">\s*([^<]+?)\s*</a>\s*</td>\s*<td>([^<]+)</td>', h)
    return dict(pk=pk, detail_pk=dpk, title=title, hist=[dict(detail_pk=a, sn=b, name=c.strip(), reg=d.strip()) for a, b, c, d in hist]), S

def resolve(pk, dpk, sn='1', S=None):
    r = S.post(f'{B}/tcs/dss/selectFileDataDownload.do', data=dict(publicDataDetailPk=dpk, publicDataPk=pk, atchFileId='',
               fileDetailSn='1', publicDataTyCode='PR0051'), timeout=60)
    j = r.json() if r.text.strip().startswith('{') else json.loads(r.text)
    return j

def hist_detail(dpk, sn, S):
    h = S.post(f'{B}/tcs/dss/selectDpkDetailInfo.do', data=dict(publicDataDetailPk=dpk, publicDataHistSn=sn), timeout=60).text
    return sorted(set(re.findall(r"(FILE_\d{15})", h))), h

def fetch(atch, out, ref_date, note, S, sn='1'):
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    r = S.get(f'{B}/cmm/cmm/fileDownload.do', params=dict(atchFileId=atch, fileDetailSn=sn), timeout=120)
    out.write_bytes(r.content)
    meta = dict(url=f'{B}/cmm/cmm/fileDownload.do', params=dict(atchFileId=atch, fileDetailSn=sn), http_status=r.status_code,
                content_disposition=requests.utils.unquote(r.headers.get('Content-Disposition', '')), bytes=len(r.content),
                sha256=hashlib.sha256(r.content).hexdigest(), download_utc=datetime.datetime.utcnow().isoformat() + 'Z',
                reference_date=ref_date, note=note)
    Path(str(out) + '.metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    return meta
