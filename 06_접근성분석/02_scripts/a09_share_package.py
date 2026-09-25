# -*- coding: utf-8 -*-
"""교수님·공동연구자용 공유 패키지(05_공유패키지/) 만들기 — 지표 정의, 코드, 결과 CSV, 해시.

원본 파일을 복사만 한다(내용 변경 없음). 복사본마다 SHA-256 을 다시 계산해 원본과 같은지 확인하고
05_공유패키지/파일목록_SHA256.csv 와 README.md(목록·읽는 순서)를 쓴다. 압축 파일은 만들지 않는다.
넣지 않는 것: 입력 자료(01_data: 격자·시설·보행망·소요시간표·경계, 약 600 MB), 격자 단위 결과 parquet(grid_access_*),
작업기록(내부 메모). 이들의 해시는 4_기록/manifest_sha256.csv 에 있다.
다시 만들 때 목록에서 빠진 옛 파일은 지우지 않고 _archive/ 로 옮긴다.
실행: python a09_share_package.py
"""
import datetime as dt
import shutil
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a00_config as C  # noqa: E402
import a99_manifest as M  # noqa: E402

PKG = C.ROOT / '05_공유패키지'
TAGS = ['main', 'sens_net2025', 'sens_T600', 'sens_speed36', 'sens_grid250', 'sens_A4', 'sens_retail_without', 'sens_union', 'natstd_B']


def items():
    """(패키지 안 경로, 원본 경로, 설명) 목록."""
    R = C.ROOT; L = []
    add = lambda dst, src, note: L.append((dst, R / src, note))
    add('1_정의/지표정의_확정.md', '00_설계/지표정의_확정.md', 'Coverage·MAI·도달시간의 유일한 정의 출처(확정 2026-09-24)')
    add('1_정의/자료가공설계.md', '00_설계/자료가공설계.md', '자료 가공 단계 P1~P7, 연구별 사용')
    for f in sorted((R / '02_scripts').glob('*.py')):
        add(f'2_코드/{f.name}', f'02_scripts/{f.name}', '코드(단계 번호 순서로 실행)')
    for f in ['run_engine.bat', 'run_ttm.bat', 'requirements.txt']:
        add(f'2_코드/{f}', f'02_scripts/{f}', 'PC 재현용 배치·패키지 목록')
    for f in sorted((R / '02_scripts' / 'tests').glob('*.py')):
        add(f'2_코드/tests/{f.name}', f'02_scripts/tests/{f.name}', '단위시험(손계산 예제·독립 구현 대조)')
    for tag in TAGS:
        d = R / '03_output' / tag
        for f in sorted(d.glob('*.csv')) + sorted(d.glob('run_meta_*.json')) + sorted(d.glob('summary_*.md')):
            note = {'.csv': '결과표', '.json': '실행 설정·입력 수·불변조건·해시', '.md': '요약'}[f.suffix]
            add(f'3_결과/{tag}/{f.name}', f'03_output/{tag}/{f.name}', note)
    add('3_결과/summary_sensitivity.md', '03_output/summary_sensitivity.md', '민감도 비교·네트워크 고정 분해')
    for sub in ['tables', 'figures']:
        for f in sorted((R / '03_output' / sub).glob('*')):
            if f.is_file():
                add(f'3_결과/{sub}/{f.name}', f'03_output/{sub}/{f.name}', '연구3 표·그림, 구별 비교')
    for f in ['접근성엔진_구축기록.md', '네트워크_소요시간표_구축기록.md', '격자마스터_구축기록.md', '시설경계연결_구축기록.md', '경계기하지표_구축기록.md', 'manifest_sha256.csv']:
        add(f'4_기록/{f}', f'04_구축기록/{f}', '구축기록(원천·해시·규칙·검증값)' if f.endswith('.md') else '전체 산출물·입력 해시 목록')
    add('4_기록/seunghoon_2026_kpa_seoul_values.csv', '01_data/external/seunghoon_2026_kpa_seoul_values.csv', '승훈 씨 원고 인쇄값 전사(비교용, 쪽수 포함)')
    return L


README = """# 06 접근성 엔진 공유 패키지 (교수님·공동연구자용)

- 만든 날: {date} · 만든 코드: `2_코드/a09_share_package.py` · 원본 폴더: `00_박사논문_연구체계/06_접근성분석/`
- 내용: 서울 시설 접근성(Coverage·MAI·도달시간) 2020·2025, 경계 조건 5종(없음·동 424·공식 생활권 116·Leiden 116·구 25)의 **지표 정의, 코드, 결과 CSV, 해시**.
- 모든 파일은 원본의 복사본이며 내용을 바꾸지 않았다. 파일마다 SHA-256을 `파일목록_SHA256.csv`에 적었고, 복사 직후 원본과 같은지 확인했다({n}개 모두 일치).
- 숫자를 인용할 때는 `3_결과/`의 CSV를 기준으로 한다. 요약 md의 값도 그 CSV에서 코드로 만든 것이다.

## 읽는 순서

1. `1_정의/지표정의_확정.md` — 세 지표의 식, 33종 시설 → 기능 카테고리 8개, 경계 조건, 민감도 목록. 정의는 이 문서만 따른다.
2. `4_기록/접근성엔진_구축기록.md` — 구현 규칙, 입력 해시, 검증(단위시험 11개·독립 구현 대조·불변조건), 한계, 7절 네트워크 고정 민감도.
3. `3_결과/main/summary_main.md` — 본 분석 요약(서울 종합값, 카테고리별 값, 동별 Δ(Leiden − 공식), 2020→2025 변화).
4. `3_결과/summary_sensitivity.md` — 민감도 비교(10분, 3.6 km/h, 250m, 카테고리 4개, 일상소매 제외, 합집합, 국가 최저기준, 네트워크 고정)와 2020→2025 변화의 네트워크 몫 분해.
5. 연구3 표·그림: `3_결과/tables/T5_category_delta_LD_LZ.md`(T5), `3_결과/figures/F3_dong_dCOV_dMAI_2025.png`(F3, 지도 자료 `tables/F3_dong_delta_2025.csv`), 부록 `figures/F3s_dong_delta_by_category_2025.png`.
6. `3_결과/tables/ku_compare_seunghoon.md` — 경계 조건을 끈 구별 COV·MAI와 김승훈 외(2026 국토학회 춘계) 원고 값의 차이·원인 기록(일치를 요구하지 않음).
7. 코드: `2_코드/a00_config.py`(경로·상수) → `a06_engine.py`(계산) → `tests/test_engine.py`(검증) → `a06b_summary.py`·`a07_study3_outputs.py`·`a08_ku_compare.py`(표·그림). 실행 순서는 `run_engine.bat`.
8. `파일목록_SHA256.csv`로 받은 파일이 같은지 확인한다(PowerShell `Get-FileHash <파일> -Algorithm SHA256`, 또는 `python -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <파일>`).

## 결과 CSV 열 (unit_access_{{연도}}_{{격자}}.csv)

`year, grid_m, T_sec, speed_kmh, catset, retail, unit_level(dong424·lz116·ld·ku·seoul), unit_id, b(none·dong424·lz116·ld·ku), cat(8개+종합), pop_total, pop_reach, COV, MAI, PWATT_sec, n_cat_mai` (+ sens_union은 UNI, UNI_allpop). 상위 단위는 모두 격자 값의 분자합/분모합이다. 묶음 B(국가 최저기준)는 `natstd_B/nat_standard_coverage_*.csv`.

## 폴더

| 폴더 | 내용 | 파일 수 |
|---|---|---|
{folders}

## 들어 있지 않은 것

- 입력 자료(`01_data/`: 100m·250m 격자 마스터, 경계 붙은 시설 33종, OSM 보행망, 격자→격자 소요시간표, 경계 사본; 약 600 MB)와 격자 단위 결과(`grid_access_*.parquet`). 해시는 `4_기록/manifest_sha256.csv`에 있다. 다시 계산하려면 이 입력이 필요하므로 요청하면 따로 전달한다.
- `4_기록/manifest_sha256.csv`는 패키지를 만들기 직전 판이다(이 README와 파일목록 자체의 해시는 원본 폴더 manifest에 추가됨).

## 필수 문구

MAI는 경계 안에서 해당 카테고리 시설에 도달한 인구만을 대상으로 한 조건부·상한 지표이며, 실제 통행사슬을 재현하지 않는다. 도달하지 못한 인구의 값은 0이 아니라 정의되지 않으며, 그 사정은 Coverage가 보여 준다.
"""

FOLDER_NOTE = {'1_정의': '지표 정의·자료 가공 설계', '2_코드': '전체 코드·배치·단위시험', '3_결과': '실행 세트별 결과 CSV·요약, 연구3 표·그림, 구별 비교',
               '4_기록': '구축기록, 해시 목록, 비교용 원고 인쇄값'}


def main():
    now = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    L = items()
    PKG.mkdir(exist_ok=True)
    keep = {PKG / d for d, _, _ in L} | {PKG / 'README.md', PKG / '파일목록_SHA256.csv'}
    stale = [p for p in PKG.rglob('*') if p.is_file() and p not in keep]
    if stale:                                          # 지우지 않고 보관
        arch = C.ROOT / '_archive' / f'{now[:10]}_공유패키지_옛파일'
        for p in stale:
            q = arch / p.relative_to(PKG); q.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(p), str(q))
    rows = []
    for dst, src, note in L:
        out = PKG / dst; out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        h0, h1 = M.sha256(src), M.sha256(out)
        if h0 != h1:
            sys.exit(f'복사 해시 불일치: {src}')
        rows.append({'패키지 경로': dst, '원본 경로(06_접근성분석 기준)': str(src.relative_to(C.ROOT)).replace('\\', '/'), 'sha256': h1,
                     'bytes': out.stat().st_size, '설명': note})
    t = pd.DataFrame(rows)
    t.to_csv(PKG / '파일목록_SHA256.csv', index=False, encoding='utf-8-sig', lineterminator='\n')
    t['폴더'] = t['패키지 경로'].str.split('/').str[0]
    folders = '\n'.join(f'| `{k}/` | {FOLDER_NOTE[k]} | {int(v)} |' for k, v in t.groupby('폴더').size().items())
    (PKG / 'README.md').write_text(README.format(date=now[:10], n=len(t), folders=folders), encoding='utf-8', newline='\n')
    M.update([M.row(PKG / 'README.md', 'a09_share_package.py', '', now), M.row(PKG / '파일목록_SHA256.csv', 'a09_share_package.py', len(t), now)])
    print(f'패키지 {len(t)}개 파일, {t.bytes.sum() / 1e6:.1f} MB, 옛 파일 이동 {len(stale)}개 → {PKG}')


if __name__ == '__main__':
    main()
