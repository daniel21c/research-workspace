# -*- coding: utf-8 -*-
"""02_명부/README.md 생성: 모든 수치는 각 유형 qa_<유형>.json과 facilities CSV에서 읽는다(손으로 적지 않음)."""
import json
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
TYPES = ['공공도서관', '문화기반시설', '공공체육시설', '노인복지시설', '장애인복지시설', '가족센터', '청소년수련시설', '보건소', '응급의료기관']
SNAPS = ['2020_01', '2025_01']


def official_summary(t, q, s):
    v = q['snapshots'][s]
    if t == '공공도서관':
        o = v['official_check']; return f"총람 공공도서관 {o['chongram_public_library_seoul']} / 명부 {o['libsta_seoul']} (총람 행 {o['chongram_rows_matched_by_name_or_address']}개 명칭·주소 일치)"
    if t == '문화기반시설':
        o = q.get('official_check', {}).get(s, {}); return f"총람 시트 행수 = 공식 수. 공공도서관 총람 {o.get('chongram_public_library')} / 국가도서관통계 {o.get('libsta_public_library')}"
    if t == '공공체육시설':
        o = v['official_total']; bad = {k: x for k, x in v['official_check'].items() if x['diff']}
        return f"시도별현황 서울 개별시설 {o['official_individual']} / 명부 {o['parsed_individual']} (종목별 차이 {len(bad)}개), 간이운동장 {o['official_village']}개소는 구별 표"
    if t == '노인복지시설':
        oc = v['official_check']; tot_o = sum(x['book_table_total'] for x in oc.values()); tot_p = sum(x['parsed'] for x in oc.values())
        bad = {k: x['diff'] for k, x in oc.items() if x['diff']}
        return f"책자 표 합계 {tot_o:.0f} / 명부 {tot_p}" + (f" (차이: {bad}, 책자 일련번호 중복·누락)" if bad else '')
    if t == '장애인복지시설':
        cmp = {k: x for k, x in q['official_check'].get('comparison', {}).items() if k.startswith(s)}
        if not cmp:
            return '2020판 총괄표는 PDF 글자 추출 불가 → 대조 없음(설치신고일 최댓값 ' + str(v.get('max_install_date')) + ')'
        return '; '.join(f"{k.split(' ', 1)[1]} {x['official']:.0f}/{x['parsed']}" for k, x in cmp.items())
    if t == '가족센터':
        o = q['official_check'][s]
        return (f"주소록 서울 {o.get('official_seoul_가족센터')}개 / 본점 행 {o.get('parsed_main_sites')}" if s == '2025_01'
                else f"명부 {o.get('parsed_rows')}행(별도 집계 없음)")
    if t == '청소년수련시설':
        o = v['official_check']; return f"총괄표 서울 {o['total_official']} / 명부 {o['parsed']}"
    if t == '보건소':
        o = v['official_check']; of = o['data_go_kr_15127903_seoul'] or {}
        return f"{o['official_year']}년 시도별 수: 보건소 {of.get('보건소')}·보건지소 {of.get('보건지소')} / 명부 " + '·'.join(f"{k} {n}" for k, n in o['parsed'].items())
    if t == '응급의료기관':
        o = v['official_check']; of = o['data_go_kr_15044540_seoul'] or {}
        return f"{o['year']}년말 시도별 {of.get('계')}(전문 {of.get('전문응급의료센터')}·중앙 {of.get('중앙응급의료센터')} 포함) / 명부 응급의료기관 {o['parsed_emergency_institutions']}"
    return ''


def main():
    rows = []; notes = []
    for t in TYPES:
        qp = HERE / t / f'qa_{t}.json'
        if not qp.exists():
            rows.append(f'| {t} | (미구축) | | | | | | | |'); continue
        q = json.load(open(qp, encoding='utf-8'))
        for s in SNAPS:
            v = q['snapshots'][s]
            d = pd.read_csv(HERE / t / f'facilities_{t}_{s}.csv', keep_default_na=False, low_memory=False, nrows=5)
            ref = d['source_reference_date'].iloc[0] if len(d) else ''
            dl = d['reference_month_delta'].iloc[0] if len(d) else ''
            g = v['geocoding']
            src = v.get('source_file') or ', '.join(v.get('source_files', []))
            rows.append(f"| {t} | {s} | {q['grade']} | {ref} ({dl:+d}) | {v.get('source_rows_seoul')} | {v['final_rows']} | "
                        f"{g['coord_rate'] * 100:.1f}% ({g['coord_rows']}/{g['rows']}) | {g['outside_seoul']} | {official_summary(t, q, s)} | `{src}` |"
                        if isinstance(dl, (int,)) or str(dl).lstrip('-').isdigit() else '')
        m = q.get('id_matching', {})
        notes.append(f"- **{t}**: 두 시점 같은 id {m.get('matched', m.get('same_code'))}개, 2020만 {m.get('only_2020')}, 2025만 {m.get('only_2025')}. 규칙: {q.get('facility_id_rule', '')}")
    head = ['# 02_명부: 공식 명부(연간·기준일 배포본) 그룹', '',
            '서울 시설 명부를 2020_01·2025_01 두 시점으로 정리했다. 명부에는 좌표가 없어, 과거 명부 주소를 2026-09 현재 지오코더(Kakao 우선, VWorld 보조)로 좌표화했다. '
            '도로명+건물번호나 지번 번지가 맞는 결과만 받았고(coord_method=geocode_kakao_exact|geocode_vworld_exact), 나머지는 unresolved로 남겼다. '
            '주소가 그 뒤 바뀌었거나 없어진 시설은 좌표가 비거나 현재 위치로 찍힐 수 있다.', '',
            '이 파일은 `make_readme.py`가 각 유형의 `qa_<유형>.json`에서 만든다. 아래 수치를 손으로 고치지 말 것.', '',
            '| 유형 | 시점 | 등급 | 원천 기준일(월 차) | 서울 원천 행 | 최종 행 | 좌표 보유 | 서울 밖 | 공식 집계 대조 | 원천 파일 |',
            '|---|---|---|---|---:|---:|---:|---:|---|---|']
    sp = json.load(open(HERE / '공공체육시설' / 'qa_공공체육시설.json', encoding='utf-8'))
    cf = ['', '## 공공체육시설 좌표 보완(2026-09-24 승인)', '',
          '주소 없는 행이 많아 1) 주소 표기 정리 후 재조회 → 2) OA-1115 주소·OA-21779 명칭+자치구+종목 일치 차용(`borrowed_official_list_name_gu`, `borrow_source`) '
          '→ 3) Kakao 키워드 검색(`kakao_place_name_gu`, `place_match_score`, `place_name`) 순서로 보완했다. 2·3단계 좌표는 명칭 대응에 기댄 것이라 정확 주소 지오코딩보다 오차 가능성이 크다. `coord_stage` 열로 구분.', '']
    for s_ in SNAPS:
        c = sp['snapshots'][s_]['coord_fill']
        cf.append(f"- {s_}: 단계별 {c['stage_counts']} → 최종 좌표율 {c['final_coord_rate'] * 100:.1f}%, 방법별 {c['by_method']}")
    tail = cf + ['', '## 두 시점 facility_id 매칭', ''] + notes + ['',
            '## 공통', '',
            '- 열: SPEC 공통 열 + `sz_` 규모 변수 + 유형별 보조 열(geocode_detail, id_match_rule 등). CSV는 UTF-8-BOM, 같은 내용의 parquet 동반.',
            '- 공간 결합: 2025 2분기 행정동(8자리)·집계구, SGIS 100m 격자 코드(다사+x3+y3). 서울 밖 좌표는 inside_seoul=False.',
            '- 원본: 각 `<유형>/raw/`에 원본과 `.metadata.json`(URL·요청 방식·시각·HTTP 상태·크기·sha256·자료 기준일). 지오코딩 응답 캐시는 `raw/geocoding/`(키 미포함).',
            '- 다시 만들기: `python <유형>/build_<유형>.py` (공통 모듈 `_lib/mb.py`, HWP/HWPX 표 추출 `_lib/hwptable.py`). 캐시가 있으면 API를 다시 부르지 않는다.',
            '- 공공체육시설 간이운동장(마을체육시설)은 개별 명부가 없어 `공공체육시설/간이운동장_구별_<시점>.csv`에 자치구 집계만 둔다.']
    (HERE / 'README.md').write_text('\n'.join(head + [r for r in rows if r] + tail) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
    print((HERE / 'README.md').read_text(encoding='utf-8'))
