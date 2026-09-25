# -*- coding: utf-8 -*-
"""소상공인시장진흥공단 상가(상권)정보 전국 zip 원본 다운로드(data.go.kr 15083033 과거판). build_retail_daily.py가 호출."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import fac
F = {'20191231': 'FILE_000000003547804', '20200331': 'FILE_000000003547855', '20241231': 'FILE_000000003676580',
     '20250331': 'FILE_000000003676583'}
def get(k):
    return fac.fetch('https://www.data.go.kr/cmm/cmm/fileDownload.do', HERE / 'raw' / f'sbiz_상가상권정보_{k}.zip',
                     params=dict(atchFileId=F[k], fileDetailSn=1), ref_date=f'{k[:4]}-{k[4:6]}-{k[6:]}', timeout=1800,
                     note='소상공인시장진흥공단_상가(상권)정보 (data.go.kr 15083033) 과거판. 2019·2020판은 2025-11 재작성본(신분류, 2022-08 이후 부여 번호)')
if __name__ == '__main__':
    for k in (sys.argv[1:] or F):
        print(k, get(k).get('bytes'), flush=True)
