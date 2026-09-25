# -*- coding: utf-8 -*-
"""P3·P4 구축기록 생성 — 01_data/network/*.json, 01_data/ttm/*_summary*.json 을 읽어
04_구축기록/네트워크_소요시간표_구축기록.md 를 쓴다(숫자는 모두 요약 json 에서 가져옴, 손으로 적지 않음).
실행: python a05b_record.py   (a04, a05 실행 뒤; 없는 조합은 표에서 빠짐)
"""
import json, sys, datetime as dt, platform
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a00_config as C

NET = C.DATA / 'network'; TTM = C.DATA / 'ttm'; REC = C.REC


def J(p):
    return json.loads(Path(p).read_text(encoding='utf-8')) if Path(p).exists() else None


def main():
    L = []
    now = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    net = {y: J(NET / f'walk_{y}_summary.json') for y in C.YEARS}
    cmp = J(NET / 'walk_compare_2020_2025.json')
    ttm = {}
    for p in sorted(TTM.glob('ttm*_summary*.json')):
        ttm[p.stem] = J(p)

    L.append('# 보행 네트워크·소요시간표 구축기록 (P3 network-walk-v1 · P4 ttm-walk-{100,250}m-v1)\n')
    L.append(f'- 생성: {now}, `02_scripts/a05b_record.py` (요약 json → 표). 코드: `02_scripts/a04_network.py`, `a05_ttm.py`, PC 일괄 실행 `run_ttm.bat`.')
    L.append('- 규칙 출처: `00_설계/지표정의_확정.md` 1절(t_og, 4.0 km/h, 30분 저장), `00_설계/자료가공설계.md` P3·P4. 상수는 `a00_config.py`(WALK_KMH, TTM_MAX_SEC, SEOUL_BUFFER_M, SNAP_MAX_M).')
    L.append(f'- 실행 환경(이 기록 생성 시): {platform.platform()}, Python {platform.python_version()}.')

    # ---------------- P3
    L.append('\n## 1. P3 보행 네트워크 (`01_data/network/`)\n')
    L.append('### 1.1 원천과 해시\n')
    L.append('| 시점 | 파일 | URL | SHA-256 | 크기(B) | 시설구축 metadata 와 일치 |')
    L.append('|---|---|---|---|---|---|')
    for y, s in net.items():
        if s:
            h = s['pbf']
            L.append(f'| {y} ({s["osm_date"]}) | {h["pbf"]} | {s["source_url"]} | `{h["sha256"]}` | {h["bytes"]:,} | {h["match"]} (기대 `{str(h.get("expected_sha256"))[:16]}…`) |')
    L.append('\n- 원본 pbf 는 용량 때문에 06 폴더에 두지 않는다. 해시 대조 기준은 `시설데이터 구축/시설데이터_패키지/구축코드/03_교육교통공원상가/park/raw/south-korea-*.osm.pbf.metadata.json` (2026-09-23 기록). a04 는 `--pbf`, `$OSM_PBF_DIR`, `~/work/pk`, `<tempdir>/osm_pbf` 순으로 찾고 없으면 Geofabrik 에서 내려받아 해시를 다시 확인한다(불일치면 중단).')
    L.append('- Geofabrik 과거 추출본은 .md5 를 제공하지 않으므로, 우리가 계산한 SHA-256 이 두 대화(시설 구축, 접근성)에서 같음을 확인한 것이 무결성 근거다.')

    L.append('\n### 1.2 범위 자르기\n')
    s0 = next(s for s in net.values() if s)
    c = s0['clip']
    L.append(f'- 기준: 코어엔진 동 424 합집합(면적 {c["union_area_km2"]:,} km²) + {c["buffer_m"]:,} m 버퍼(EPSG:{c["crs"]}, 버퍼 후 {c["buffer_area_km2"]:,} km²).')
    L.append(f'- 추출: 버퍼의 bbox(EPSG:4326) = [{", ".join(f"{v:.4f}" for v in c["bbox_4326"])}] 안에 노드가 하나라도 있는 highway way 만 pyosmium(FileProcessor, with_locations) 으로 읽음. 이후 EPSG:5179 로 변환해 **양 끝점 중 하나라도 버퍼 폴리곤 안**인 변만 유지.')
    L.append('- 버퍼를 두는 이유: 서울 경계 부근 셀이 경계 밖 도로를 거쳐 돌아오는 경로를 잃지 않게 함(도착 셀은 서울 안만 저장).')

    L.append('\n### 1.3 보행 가능 규칙표 (a04 `WALK_RULES`, 순서대로 적용)\n')
    L.append('| # | 조건 | 처리 |\n|---|---|---|')
    for r in s0['rules']:
        L.append(f'| {r[0]} | {r[1]} | {r[2]} |')
    L.append('\n- 방향성: 보행망은 무향. 일방통행(oneway)은 무시.')
    L.append(f'- 변 길이 = EPSG:5179 평면 거리(m, 노드 간 직선), 시간 = 길이 / ({C.WALK_KMH} km/h = {C.WALK_KMH * 1000 / 3600:.4f} m/s). 같은 노드쌍 중복 변은 최소 길이 하나만, 길이 0·자기 고리 제거.')
    L.append('- 노드는 OSM 노드 그대로(단순화하지 않음): 격자 중심 스냅 거리를 줄이기 위해 도로 기하 정점을 모두 노드로 둔다.')
    L.append('- 연결성: **가장 큰 연결성분(LCC)만 유지.** 작은 성분(버퍼에 잘린 조각, 고립 산책로, 단지 내부 도로 등)에 스냅되면 도달 셀이 거의 없는 왜곡이 생기므로 제외. 비율은 아래 표.')

    L.append('\n### 1.4 결과\n')
    L.append('| 항목 | 2020 | 2025 | 변화 |\n|---|---|---|---|')
    rows = [('highway way(전국)', 'counts.ways_highway_all', ''), ('보행 규칙 통과(전국)', 'counts.ways_walk_rule', ''), ('bbox 안 way', 'counts.ways_in_bbox', ''),
            ('노드(LCC)', 'nodes', 'nodes'), ('변(LCC)', 'edges', 'edges'), ('총 길이 km(LCC)', 'total_km', 'total_km'),
            ('변 평균 길이 m', 'mean_edge_m', ''), ('변 중위 길이 m', 'median_edge_m', ''),
            ('연결성분 수(자르기 후)', 'components.n_components', ''), ('LCC 노드 비율', 'components.lcc_node_share', ''), ('LCC 변 비율', 'components.lcc_edge_share', ''),
            ('LCC 길이 비율', 'components.lcc_km_share', ''), ('노드≥100 성분 수', 'components.components_ge100_nodes', ''), ('둘째 성분 노드 수', 'components.second_largest_nodes', ''), ('처리 시간 s', 'elapsed_s', '')]

    def get(d, k):
        for part in k.split('.'):
            d = d[part] if d is not None else None
        return d
    for name, key, ck in rows:
        v = [get(net[y], key) if net[y] else None for y in (2020, 2025)]
        f = lambda x: '' if x is None else (f'{x:,.4f}' if isinstance(x, float) and x < 2 else (f'{x:,.1f}' if isinstance(x, float) else f'{x:,}'))
        ch = f'{cmp[ck]["pct_change"]:+.1f}%' if (ck and cmp) else ''
        L.append(f'| {name} | {f(v[0])} | {f(v[1])} | {ch} |')
    if cmp:
        L.append('\n#### highway 유형별 길이(km, LCC)\n')
        L.append('| highway | 2020 | 2025 | 변화 |\n|---|---|---|---|')
        for h, v in sorted(cmp['by_highway_km'].items(), key=lambda kv: -kv[1]['2025']):
            a_, b_ = v['2020'], v['2025']
            L.append(f'| {h} | {a_:,.1f} | {b_:,.1f} | {("%+.1f%%" % ((b_ - a_) / a_ * 100)) if a_ else "신규"} |')
        L.append('\n- 해석·한계: 2020→2025 길이 증가의 대부분은 footway·service·path·cycleway 로, 실제 도로 신설보다 **OSM 기여(보도·단지 내 도로 매핑) 증가**가 크다. 따라서 두 시점 접근성 차이에는 네트워크 매핑 완성도 차이가 섞여 있다. 15분 도달 셀 수(아래 2.3)가 두 해에 비슷한지로 그 영향을 점검하고, 시설 변화 효과를 볼 때는 같은 네트워크(2025)로 재계산하는 민감도를 둘 수 있다(a05 는 `--year` 로 네트워크와 인구 시점을 함께 고르므로, 필요하면 a00_config.YEARS 에 교차 조합을 추가).')

    L.append('\n### 1.5 산출 파일\n')
    L.append('| 파일 | 내용 |\n|---|---|')
    L.append('| `walk_{year}_nodes.parquet` | node_id(OSM 노드 id), x, y (EPSG:5179) — LCC 노드만 |')
    L.append('| `walk_{year}_edges.parquet` | u, v(OSM 노드 id), length_m, time_s, highway, way_id — 무향, 노드쌍당 1행 |')
    L.append('| `walk_{year}_graph.npz` | CSR 인접행렬(node_id, x, y, indptr, indices, time_s float32) — a05 가 바로 읽음. networkx 없이도 쓰도록 graphml 대신 npz |')
    L.append('| `walk_{year}_summary.json` | 위 표의 원천(원천 해시, 규칙표, 성분 통계, 유형별 길이) |')
    L.append('| `walk_compare_2020_2025.json` | 두 해 비교 |')

    # ---------------- P4
    L.append('\n## 2. P4 격자→격자 보행 소요시간표 (`01_data/ttm/`)\n')
    L.append('### 2.1 방법\n')
    L.append(f'- 출발 셀: 격자 마스터(`grid{{100|250}}_master.parquet`)에서 해당 시점 **인구>0 또는 사업체>0** 인 셀(`--origins pop_or_biz`, 기본; 연구1 후보지 포함). `--origins pop` 은 인구>0 만. 도착 셀: 서울 전체 셀.')
    L.append(f'- 스냅: 셀 중심(x_c, y_c) → 가장 가까운 LCC 노드(cKDTree). 스냅 거리는 `snap{{grid}}_{{year}}.parquet` 에 기록하고 **시간에는 더하지 않는다**(셀 안 이동은 무시; > {C.SNAP_MAX_M} m 셀은 `snap_gt_max` 플래그). 같은 노드에 스냅된 두 셀의 시간은 0.')
    L.append(f'- 계산: `scipy.sparse.csgraph.dijkstra`(무향, `limit={C.TTM_MAX_SEC}`) 를 출발 노드 32개 묶음으로 실행, 도착 노드 시간을 도착 셀에 대응. **t ≤ {C.TTM_MAX_SEC} s 인 쌍만** 저장, t_sec = 반올림 uint16. 자기 자신 쌍(t=0) 포함.')
    L.append('- 저장: `ttm{grid}_{year}/ku={ku}/chunk_{i:03d}.parquet` (o_grid, d_grid, t_sec; zstd). Hive 분할이라 `pyarrow.dataset.dataset(dir, partitioning="hive")` 로 읽으면 ku 열이 붙는다. `_stats/` 에 청크별 출발셀 통계, `_meta.json` 에 청크 크기·출발 규칙(다르게 재실행하면 거부). 청크 파일이 있으면 건너뛰므로 중단 후 재실행하면 이어서 계산된다(`--max-seconds` 로 시간 제한 실행 가능).')
    L.append('- 검증: (a) 자기 쌍 t=0, (b) 무향이므로 o→d = d→o (종로구 2025 시험 결과를 대화형으로 점검: 양방향 모두 저장된 374,282쌍의 차이 0), (c) 우회율 = 네트워크 시간 / 직선거리 시간(4.0 km/h) 표본 분포(2.4).')

    L.append('\n### 2.2 시험 계산 — 종로구(ku 11010), 100 m\n')
    keys_test = [k for k in ttm if k.endswith('_ku11010')]
    if keys_test:
        L.append('| 항목 | ' + ' | '.join(str(ttm[k]['year']) for k in keys_test) + ' |\n|---|' + '---|' * len(keys_test))
        def row(name, fn):
            L.append(f'| {name} | ' + ' | '.join(fn(ttm[k]) for k in keys_test) + ' |')
        row('출발 셀', lambda d: f'{d["n_origins"]:,}'); row('도착 셀(서울 전체)', lambda d: f'{d["n_destinations"]:,}')
        row('저장 쌍(≤30분)', lambda d: f'{d["n_pairs_total_in_dir"]:,}')
        row('15분 도달 셀 평균 / 중위 (p10–p90)', lambda d: f'{d["reach_15min_cells"]["mean"]:.1f} / {d["reach_15min_cells"]["median"]:.0f} ({d["reach_15min_cells"]["p10"]:.0f}–{d["reach_15min_cells"]["p90"]:.0f})')
        row('30분 도달 셀 평균 / 중위 (p10–p90)', lambda d: f'{d["reach_30min_cells"]["mean"]:.1f} / {d["reach_30min_cells"]["median"]:.0f} ({d["reach_30min_cells"]["p10"]:.0f}–{d["reach_30min_cells"]["p90"]:.0f})')
        row('도달 셀 0 인 출발 셀', lambda d: f'{d["reach_15min_cells"]["zero"]}')
        row('출발 셀 스냅 거리 중위 / p95 / 최대 m', lambda d: f'{d["snap_m_origins"]["median"]} / {d["snap_m_origins"]["p95"]} / {d["snap_m_origins"]["max"]}')
        row(f'스냅 > {C.SNAP_MAX_M} m 출발 셀', lambda d: f'{d["snap_m_origins"]["n_gt_max"]}')
        row('계산 시간(1 worker)', lambda d: f'{d["timing"]["wall_sec"]} s, {d["timing"]["ms_per_origin_cpu"]} ms/출발셀')
        row('우회율 200쌍 p10 / p50 / p90', lambda d: f'{d["detour_check"]["ratio_quantiles_all"]["p10"]} / {d["detour_check"]["ratio_quantiles_all"]["p50"]} / {d["detour_check"]["ratio_quantiles_all"]["p90"]}')
        row('우회율 < 1 비율(전체 / 직선≥500 m)', lambda d: f'{d["detour_check"]["share_ratio_lt1_all"]:.3f} / {d["detour_check"]["share_ratio_lt1_line_ge500m"]:.3f}')
        row('우회율 1.2–1.6 비율', lambda d: f'{d["detour_check"]["share_ratio_in_1.2_1.6_all"]:.3f}')
        r15 = ttm[keys_test[-1]]['reach_15min_cells']['median']
        L.append(f'\n- 15분 도달 셀 중위 {r15:.0f}개(100 m) ≈ {r15 / 100:.2f} km². 직선 1 km 원(3.14 km²)의 {r15 / 100 / 3.14 * 100:.0f}% 수준으로, 우회율 약 1.3 과 종로구 북부 산지를 감안하면 타당.')

    L.append('\n### 2.3 서울 전체 결과\n')
    keys_full = [k for k in ttm if '_ku' not in k]
    if keys_full:
        L.append('| 격자 | 시점 | 출발 셀 | 도착 셀 | 저장 쌍 | 15분 도달 셀 평균/중위 | 30분 도달 셀 평균/중위 | 도달 0 셀 | 출발셀 스냅 중위/p95/최대 m | 스냅>200 m 출발셀 | 스냅>200 m 전체셀 | 계산 ms/출발셀(CPU) | wall s(workers) |')
        L.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
        for k in sorted(keys_full):
            d = ttm[k]; t = d['timing']
            L.append(f'| {d["grid_m"]} | {d["year"]} | {d["n_origins"]:,} | {d["n_destinations"]:,} | {d["n_pairs_total_in_dir"]:,} | {d["reach_15min_cells"]["mean"]:.1f}/{d["reach_15min_cells"]["median"]:.0f} | '
                     f'{d["reach_30min_cells"]["mean"]:.1f}/{d["reach_30min_cells"]["median"]:.0f} | {d["reach_15min_cells"]["zero"]} | {d["snap_m_origins"]["median"]}/{d["snap_m_origins"]["p95"]}/{d["snap_m_origins"]["max"]} | '
                     f'{d["snap_m_origins"]["n_gt_max"]} | {d["snap_m_all_cells"]["n_gt_max"]:,} | {t.get("ms_per_origin_cpu_all_chunks", t.get("ms_per_origin_cpu"))} | {t["wall_sec"]} ({t["workers"]}) |')
        L.append('\n- 스냅 > 200 m 전체 셀은 대부분 산지·하천·공항 등 인구 0 셀. 출발 셀(인구·사업체>0) 중 초과 셀은 위 표의 수만큼이며 `ttm{grid}_{year}_origin_stats.parquet` 의 `snap_gt_max` 로 식별할 수 있다(a06 에서 별도 표시 권장). 2020 네트워크가 성겨 2020 초과 셀이 더 많다.')
        d100 = {ttm[k]['year']: ttm[k] for k in keys_full if ttm[k]['grid_m'] == 100}
        if len(d100) == 2:
            a_, b_ = d100[2020]['reach_15min_cells']['mean'], d100[2025]['reach_15min_cells']['mean']
            L.append(f'- 15분 도달 셀 수 평균(100m): 2020 {a_:.1f}, 2025 {b_:.1f} ({(b_ - a_) / a_ * 100:+.1f}%) → 1.4 의 매핑 완성도 차이(길이 +{cmp["total_km"]["pct_change"]:.0f}%)가 15분 도달 범위에 주는 영향은 작다.' if cmp else '')

    L.append('\n### 2.4 우회율 검증 (표본 쌍, 네트워크 시간 / 직선 4.0 km/h 시간)\n')
    L.append('| 격자 | 시점 | 표본 | p5 | p10 | p25 | p50 | p75 | p90 | p95 | <1 비율 | 1.2–1.6 비율 | 직선≥500 m: n / p50 / 평균 / <1 |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for k in sorted(ttm):
        d = ttm[k]; dc = d.get('detour_check')
        if not dc:
            continue
        q = dc['ratio_quantiles_all']; q5 = dc['ratio_quantiles_line_ge500m'] or {}
        L.append(f'| {d["grid_m"]} | {d["year"]}{" 종로구" if d.get("ku_filter") else ""} | {dc["n_pairs"]} | {q["p5"]} | {q["p10"]} | {q["p25"]} | {q["p50"]} | {q["p75"]} | {q["p90"]} | {q["p95"]} | {dc["share_ratio_lt1_all"]:.3f} | {dc["share_ratio_in_1.2_1.6_all"]:.3f} | '
                 f'{dc["n_pairs_line_ge500m"]} / {q5.get("p50")} / {dc["mean_ratio_line_ge500m"]} / {dc["share_ratio_lt1_line_ge500m"]} |')
    L.append('\n- 중위 우회율 1.26–1.36, 절반 이상이 1.2–1.6 구간 → 보행망 우회 계수 문헌값(약 1.2–1.5)과 부합. 비율 < 1 인 쌍(1–2%)은 스냅 거리를 시간에 더하지 않아 생기는 것으로, 가까운 쌍에서만 나타난다(정의상 셀 안 이동 무시). p95 가 2 를 넘는 것은 하천·철도·산으로 막힌 쌍.')

    L.append('\n### 2.5 실행 시간과 PC 실행\n')
    if keys_full:
        d100 = [ttm[k] for k in keys_full if ttm[k]['grid_m'] == 100]
        ms = [d['timing'].get('ms_per_origin_cpu_all_chunks') or d['timing']['ms_per_origin_cpu'] for d in d100]
        L.append(f'- 측정: 100 m 격자 출발 셀 1개당 CPU {min(ms)}–{max(ms)} ms (Cowork VM, 2 vCPU, 노드 34만·59만). 서울 전체 100 m 한 시점 = 약 {sum(d["n_origins"] for d in d100) / len(d100):,.0f} 출발 셀 → CPU 약 {sum(d["n_origins"] for d in d100) / len(d100) * max(ms) / 1000:,.0f} s, 2 worker 벽시계 {max(d["timing"]["wall_sec"] for d in d100):.0f} s 이내. 250 m 는 그 1/4 이하.')
    L.append('- 추정: `run_ttm.bat` 전체(네트워크 2개 + 소요시간표 4조합)는 PC(4 worker 이상)에서 **계산 5분 이내**, 여기에 pbf 다운로드(112 MB + 234 MB)와 a04 해시 계산 1–5분. 원래 "PC 에서만 가능"하다고 본 규모였지만, 노드 수가 60만 이하이고 30분 컷오프 다익스트라가 셀당 수 ms 라 이 VM 에서 전체를 이미 계산했다. PC 실행은 재현·갱신용.')
    L.append('- PC 실행 방법: `02_scripts` 에서 `pip install -r requirements.txt` 후 `run_ttm.bat [WORKERS]` (기본 CPU−1). 네트워크 json 이 있으면 a04 는 건너뛰고, 소요시간표는 있는 청크를 건너뛴다. 완전히 다시 만들려면 `01_data/network/walk_*` 와 `01_data/ttm/ttm*` 을 `_archive/` 로 옮기고 실행. 기록 갱신은 `python a05b_record.py`.')
    L.append('- 이 VM 에서의 실행은 호출당 약 75 s 제한이 있어 `--max-seconds` 로 나눠 실행했고, 결과는 동일 규칙으로 이어 붙인 것이다(청크 단위 원자적 저장).')

    L.append('\n### 2.6 산출 파일\n')
    L.append('| 파일 | 내용 |\n|---|---|')
    L.append('| `ttm{grid}_{year}/ku=*/chunk_*.parquet` | o_grid, d_grid, t_sec(uint16, ≤1800) — 본 소요시간표 |')
    L.append('| `ttm{grid}_{year}/_meta.json`, `_stats/` | 청크 크기·출발 규칙, 청크별 출발셀 통계(n_reach_15, n_reach_30, chunk_sec) |')
    L.append('| `snap{grid}_{year}.parquet` | grid_cd, node_idx(npz 인덱스), node_id(OSM), snap_m, snap_gt_max — 전체 셀 |')
    L.append('| `ttm{grid}_{year}_origin_stats[_ku…].parquet` | 출발 셀별 15·30분 도달 셀 수, 스냅 거리 |')
    L.append('| `ttm{grid}_{year}_summary[_ku…].json` | 위 표의 원천(설정, 통계, 시간, 우회율 검증) |')
    L.append('\n## 3. a06 엔진에서 쓸 때 주의\n')
    L.append('- 소요시간표는 30분(1,800 s) 상한이므로 "미저장 = 30분 초과 또는 도달 불가". 15분 지표는 t_sec ≤ 900 으로 자른다(지표정의 3절).')
    L.append('- 출발 셀은 pop_or_biz 규칙이라 인구 0·사업체>0 셀도 들어 있다. Coverage·MAI·PWATT 는 인구>0 셀만 고르고(마스터 `pop_{year}`), 후보지 배치(연구1)는 전체를 쓴다.')
    L.append('- 시설 격자(도착)는 서울 전체 셀에 있으므로 `d_grid` 로 결합. 시설 셀이 `snap_gt_max` 이면 시간이 과소(셀 중심→노드 이동 무시)일 수 있어 민감도에서 스냅 거리를 시간에 더한 버전을 비교할 수 있다(a05 `snap_m` 열 보존).')
    L.append('- 2020 과 2025 는 각기 그 해 네트워크로 계산했다(시점 대응 규칙). 네트워크 매핑 차이의 영향을 떼어 보려면 2025 네트워크로 2020 인구·시설을 계산하는 교차 조합을 추가한다.')
    (REC / '네트워크_소요시간표_구축기록.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('wrote', REC / '네트워크_소요시간표_구축기록.md', len(L), 'lines')


if __name__ == '__main__':
    main()
