"""01_인허가/README.md 생성 — 모든 수치는 각 유형 qa_<유형>.json 과 _common/crs_check.json 에서 읽는다(손으로 적지 않음)."""
import json
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parent.parent
ORDER = ['의원', '병원급', '약국', '산후조리업', '안전상비의약품판매업소', '안경업', '동물병원', '체육시설업', '공연장', '영화상영관',
         '대규모점포', '식료품소매', '일반음식점', '휴게음식점', '이용업', '미용업', '세탁업', '목욕장업', '주유소']
K = ['2020_01', '2025_01']

def pct(v):
    return '-' if v is None else f'{100 * v:.1f}%'

def official(q):
    oc = q.get('official_comparison', {})
    if 'status' in oc:
        return oc['status']
    if 'error' in oc:
        return 'ERROR ' + oc['error']
    a = oc['2025_01_vs_HIRA_20241231']['by_kind']; b = oc['2020_01_vs_HIRA_20211231_open_le_20191231']['by_kind']
    main = [k for k in a if a[k]['hira'] >= 20] or list(a)
    s1 = ', '.join(f"{k} {a[k]['ours']:,}/{a[k]['hira']:,}({a[k]['ratio_ours_to_hira']:.3f})" for k in main)
    s2 = ', '.join(f"{k} {b[k]['ours']:,}/{b[k]['hira']:,}" for k in main if k in b)
    m = ', '.join(f"{k} {100*a[k]['hira_matched_in_ours_name_or_addr']:.1f}%" for k in main)
    return f"2025: 역산/HIRA 2024.12 = {s1}; HIRA기관 개별매칭률 {m}. 2020: 역산/HIRA 2021.12판 개설≤2019 하한 = {s2}"

def cautions(q):
    c = []
    for k in K:
        a = q[k]; y = k[:4]
        if a.get('flag_bulk_admin_end'):
            c.append(f"{y}: 일괄 직권말소일 이후로 종료가 잡힌 {a['flag_bulk_admin_end']:,}건 포함(flag_bulk_admin_end; 제외 시 {a['n_final_excl_bulk_admin_end']:,})")
        if a.get('closed_nodate_substituted'):
            c.append(f"{y}: 날짜없는 폐업·전출 {a['closed_nodate_substituted']:,}건 최종수정일 대체")
        if a.get('transfer_adjusted_start'):
            c.append(f"{y}: 전출 이관기록 시작일 보정 {a['transfer_adjusted_start']:,}건")
        if a.get('dedup_removed_exact'):
            c.append(f"{y}: 원천 완전중복 {a['dedup_removed_exact']:,}건 제거")
        un = a['coord_method'].get('unresolved', 0)
        if un:
            c.append(f"{y}: 좌표 unresolved {un:,}")
        if a.get('outside_seoul'):
            c.append(f"{y}: 서울 경계 밖 좌표 {a['outside_seoul']}")
    tf = q.get('transfer_fix', {}).get('removed_from_active') or {}
    if any(tf.values()):
        c.append('전출 보정으로 운영수에서 뺀 이중계상 ' + ', '.join(f"{k[:4]} {v:,}" for k, v in tf.items()))
    g = q.get('geocoding', {})
    if g.get('skipped'):
        c.append(g['reason'])
    elif not g.get('enabled'):
        c.append('대용량 → 지오코딩 안 함')
    elif g.get('rows_needing'):
        c.append(f"지오코딩 {g.get('accepted_rows', 0):,}/{g['rows_needing']:,}행 채택(건물번호 일치)")
    fl = q.get('filter')
    if fl:
        c.append(f"필터: {fl['desc']}")
    if 'theater_aggregate' in q:
        c.append('극장단위: ' + ', '.join(f"{k[:4]} {v['n_theaters']}개 극장/{v['n_screens']}관" for k, v in q['theater_aggregate'].items()))
    return '; '.join(c + q.get('notes', []))

def stsum(src):
    out = {}
    for s in src.values():
        for k, v in s['status'].items():
            out[k] = out.get(k, 0) + v
    return out

rows = []; details = []
for T in ORDER:
    p = ROOT / T / f'qa_{T}.json'
    if not p.exists():
        rows.append(f'| {T} | (미구축) | | | | | |'); continue
    q = json.loads(p.read_text(encoding='utf-8'))
    subs = sorted(set(q[K[0]]['by_subtype']) | set(q[K[1]]['by_subtype']))
    sub = '<br>'.join(f"{s}: {q[K[0]]['by_subtype'].get(s, 0):,} → {q[K[1]]['by_subtype'].get(s, 0):,}" for s in subs) if len(subs) <= 8 else f'{len(subs)}개 업태(qa 참조)'
    rows.append(f"| {T} | {q[K[0]]['n_final']:,} | {q[K[1]]['n_final']:,} | {pct(q[K[0]]['coord_rate'])} / {pct(q[K[1]]['coord_rate'])} | {sub} | {official(q)} | {cautions(q)} |")
    src = q['sources']
    details.append(f"- **{T}**: 원천 {sum(v['rows'] for v in src.values()):,}행({', '.join(src)}) → 두 시점 후보 {q['candidates_either_snapshot']:,} → 최종 2020 {q[K[0]]['n_final']:,} / 2025 {q[K[1]]['n_final']:,}. "
                   f"상태 원천분포 {json.dumps(stsum(src), ensure_ascii=False)}; unknown 인허가일 {sum(v['lic_unknown'] for v in src.values()):,}; 원천기준일 {', '.join(sorted(set(str(v['reference_date']) for v in src.values())))}; "
                   f"두 시점 공통 {q['panel']['in_both']:,}, 2020만 {q['panel']['only_2020_01']:,}, 2025만 {q['panel']['only_2025_01']:,}.")
crs = json.loads((ROOT / '_common/crs_check.json').read_text(encoding='utf-8'))
md = f"""# 01_인허가 — 지방행정 인허가(구 LOCALDATA) 기반 시설 (2020_01 · 2025_01)

생성: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · `_common/make_readme.py` 가 각 `qa_<유형>.json` 에서 자동 생성(수치 수기 입력 없음).

## 방법 요약
- 원천: 서울 열린데이터광장 인허가 시트 전체 CSV(병원급만 file.localdata.go.kr 서울판 — 병상·의료인수 열 때문). 각 `raw/` 에 원본과 `.metadata.json`(URL·파라미터·수신시각·sha256·자료기준일).
- 등급 B(현재 전체 이력 역산): 인허가일 ≤ D(2019-12-31 / 2024-12-31), 종료일(폐업일→인허가취소일) 없음 또는 > D. 폐업·취소·전출 상태인데 날짜가 없으면 최종수정일자로 대체(`temporal_reason` 표시). 1900·0001 더미·결측 인허가일은 unknown(제외). 휴업은 시작·종료일이 모두 있고 D가 그 사이일 때만 제외.
- 추가 보정(SPEC 외, 이중계상 방지): ① **자치구 간 전출** 시 새 구 기록이 원 인허가일을 승계해 옛 기록과 동시에 운영으로 잡히는 문제 → 같은 업종·사업장명·인허가일 묶음에서 앞 기록이 전출이면 뒤 기록의 유효 시작일(`eff_start_date`)을 전출일(=최종수정일)로 조정. ② 같은 업종·사업장명·주소·인허가일이 같고 관리번호만 다른 **원천 완전중복**은 하나만 남김(`dedup_removed_*.csv` 에 목록; 영화상영관은 스크린별 등록이라 적용 안 함). ③ 같은 날 {20}건 이상 **일괄 직권말소**된 기록은 `flag_bulk_admin_end=True`(실제 폐업은 더 이전일 가능성 — 민감도 분석용, 행은 유지).
- 좌표: 원천 EPSG:5174 → pyproj(EPSG 기본 Korean1985→WGS84 변환)로 4326·5179. 검증: {crs['n']}개 무작위 표본을 Kakao 주소검색(건물번호 일치)과 비교 — 중앙값 {crs['median_m']} m, 90% {crs['p90_m']} m, 50 m 이내 {100*crs['share_le_50m']:.1f}%, 평균 편차 dx {crs['mean_dx_m']} m / dy {crs['mean_dy_m']} m → **{crs['verdict']}** (`_common/crs_check.json`).
- 좌표 없는 운영 시설: 소·중규모 유형은 Kakao→VWorld 지오코딩(도로명+건물번호 또는 지번 번지 정확 일치만 채택, 응답은 `raw/geocoding/` 캐시, 키 미저장). 일반음식점·휴게음식점·미용업은 지오코딩하지 않음(unresolved).
- 공간 부여: SGIS 2025 2Q 서울 경계(시도 11) 내부 판정, `adm_dong_cd`(행정동 8자리), `oa_cd`(집계구), `grid100_cd`(100 m 격자 '다사'+x3+y3, EPSG:5179 좌하단 기준).
- 규모(`sz_*`)·진료과목(`dept_current_*`)은 **원천 기준일(2026-09) 현재 기록값**이며 과거 시점 값이 아님.
- 재실행: `bash run_all.sh` (또는 각 폴더 `python build_<유형>.py`), 이후 `python _common/make_readme.py`.

## 유형별 결과
| 유형 | 2020_01 | 2025_01 | 좌표율 2020/2025 | subtype (2020 → 2025) | 공식 대조 | 주의점 |
|---|---:|---:|---|---|---|---|
""" + '\n'.join(rows) + """

## 원천→후보→최종 계수
""" + '\n'.join(details) + '\n'
(ROOT / 'README.md').write_text(md, encoding='utf-8')
print('written', len(md))
