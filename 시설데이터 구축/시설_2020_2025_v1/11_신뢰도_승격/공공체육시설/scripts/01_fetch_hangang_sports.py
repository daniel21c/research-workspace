"""미래한강본부 한강공원 시설지도(체육시설) 목록 수집: https://hangang.seoul.go.kr/www/facility/map.tab?opt2=SPORTS&opt3=DM_SPORTS
목록 레이어(/www/facility/mapList.layer, POST opt2=SPORTS&opt3=DM_SPORTS, 100건/쪽)에서 시설명·주소·위치설명·위경도·운영상태 파싱. robots.txt 없음(404)."""
import re, time, json, hashlib, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parents[1]; RAW = HERE / 'raw'; RAW.mkdir(exist_ok=True)
URL = 'https://hangang.seoul.go.kr/www/facility/mapList.layer'
rows, pages = [], []
for p in range(1, 30):
    data = urllib.parse.urlencode(dict(opt2='SPORTS', opt3='DM_SPORTS', pageNo=p, perPageCnt=100)).encode()
    with urllib.request.urlopen(urllib.request.Request(URL, data=data, headers={'Referer': 'https://hangang.seoul.go.kr/www/facility/map.tab'}), timeout=30) as h:
        t = h.read().decode('utf-8')
    (RAW / 'hangang_sports').mkdir(exist_ok=True); (RAW / 'hangang_sports' / f'mapList_p{p:02d}.html').write_text(t, encoding='utf-8')
    items = re.findall(r"<li class=\"fac-listitem\" data-key='(\d+)'.*?<span class=\"state[^\"]*\"[^>]*>([^<]*)</span>.*?<strong class=\"fac-name\">([^<]*)</strong>(.*?)</li>\s*<script>\s*if\(\"([\d.]*)\" != \"\"\)\{\s*setFcltMaker\(\"\d+\", \"[^\"]*\",\"([\d.]*)\",\"([\d.]*)\"", t, re.S)
    for key, st, nm, info, _, lat, lon in items:
        dd = dict(re.findall(r'<dt>·\s*([^:<]+?)\s*:</dt>\s*<dd>([^<]*)</dd>', info))
        rows.append(dict(fclt_cd=key, status=st.strip(), name=nm.strip(), kind=dd.get('구분', ''), address=dd.get('주소', ''), location=dd.get('위치', ''), lat=lat, lon=lon))
    pages.append(len(items)); time.sleep(0.3)
    if len(items) < 100: break
d = pd.DataFrame(rows).drop_duplicates('fclt_cd'); d.to_csv(RAW / 'hangang_sports_facilities_20260924.csv', index=False, encoding='utf-8-sig')
json.dump(dict(url=URL, method='POST', params=dict(opt2='SPORTS', opt3='DM_SPORTS', perPageCnt=100), page_counts=pages, rows=len(d),
               download_utc=datetime.now(timezone.utc).isoformat(), ref_date='현재판(2026-09-24 조회)', note='미래한강본부 한강공원 시설지도 체육시설 목록(좌표 포함)'),
          open(RAW / 'hangang_sports_facilities_20260924.csv.metadata.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(pages, len(d)); print(d.name.str.replace(r'\d+.*$', '', regex=True).str.split().str[-1].value_counts().head(30).to_dict())
