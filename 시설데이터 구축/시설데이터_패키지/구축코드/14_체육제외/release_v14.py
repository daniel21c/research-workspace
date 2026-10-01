"""Bounded offline facility-v1.4 release. stage/verify never overwrite canonical data.

stage: build from unchanged adopted inputs, compare exactly to v1.3 minus sports.
verify: rebuild current v1.4 from preserved inputs; validate sealed historical evidence
and an authorized deletion receipt when v1.3 generated files have been retired.
No API, credentials, 06 writes or Git operations.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from cleanup_evidence import validate_cleanup_state, HISTORY_RELATIVE, RECEIPT_RELATIVE

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent
PKG = BUILD.parent
DATA = PKG / '데이터'
ANALYSIS = '서울시설_2020_2025_분석용.parquet'
INTEGRATED = '통합_신뢰도상_2020_2025.parquet'
FILES = [ANALYSIS, INTEGRATED, '_요약_시설별_수_좌표.csv', '채택목록.csv', '검증결과.json']
SPORT = '체육시설업'
SPORT_FOLDER = '체육시설업_조건부'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def unchanged_inputs():
    baseline = read_json(HERE / 'baseline.json')
    for item in baseline['adopted_inputs']:
        assert sha(PKG / item['path']) == item['sha256'], item['path']
    return len(baseline['adopted_inputs'])


def build(out):
    out.mkdir(exist_ok=True)
    env = dict(os.environ)
    for key in ['FAC_T_DIR', 'FAC_OVERRIDE_DIR', 'FAC_V1_DIR', 'FAC_SELECTION_CONFIG', 'OUT_CSV']:
        env.pop(key, None)
    env.update(OUT_DIR=str(out), PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    for script in ['build_통합.py', 'build_분석용.py']:
        result = subprocess.run([sys.executable, str(BUILD / script)], env=env,
                                capture_output=True, text=True, encoding='utf-8')
        (out / (script + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
        assert result.returncode == 0, f'{script}: see local build log'


def exact_filtered(old_path, new_path, column, value):
    old = pd.read_parquet(old_path)
    new = pd.read_parquet(new_path)
    expected = old.loc[old[column].ne(value)].reset_index(drop=True)
    pd.testing.assert_frame_equal(new, expected, check_exact=True, check_dtype=True,
                                  check_like=False, check_categorical=True)
    assert pq.read_schema(old_path).equals(pq.read_schema(new_path), check_metadata=False)
    # Compare floating point bits as well as values (including the NaN representation).
    for col in new.select_dtypes(include=['float64', 'float32']).columns:
        assert new[col].to_numpy().tobytes() == expected[col].to_numpy().tobytes(), col
    # Parquet dictionaries/metadata can differ after reading and filtering an old
    # file. Compare logical string bytes, not that incidental file encoding.
    for col in new.select_dtypes(include=['string', 'object']).columns:
        assert new[col].isna().equals(expected[col].isna()), col
        assert new[col].fillna('').str.encode('utf-8').tolist() == expected[col].fillna('').str.encode('utf-8').tolist(), col
    return old, new


def stage():
    baseline = read_json(HERE / 'baseline.json')
    assert sha(DATA / ANALYSIS) == baseline['analysis_sha256'], 'Canonical is no longer v1.3'
    count = unchanged_inputs()
    out = HERE / 'staging'
    build(out)
    old, new = exact_filtered(DATA / ANALYSIS, out / ANALYSIS, '시설', SPORT)
    old_merged, merged = exact_filtered(DATA / INTEGRATED, out / INTEGRATED, '시설', SPORT_FOLDER)
    assert len(new) == 584766 and new['시설'].nunique() == 32
    groups = new.groupby(['시설', 'year']).size()
    assert len(groups) == 64 and set(new.year) == {2020, 2025}
    assert all(len(group) == 2 for _, group in groups.groupby(level=0))
    assert len(merged) == len(new) - int(new['시설'].eq('일상소매').sum())
    duplicate = new[new.duplicated(['시설', 'facility_id', 'year'], keep=False)]
    assert set(map(tuple, duplicate[['시설', 'facility_id', 'year']].drop_duplicates().values)) == {
        ('버스정류장', 'BUS_15143', 2020)}
    coords = new[['lon', 'lat', 'x_5179', 'y_5179']]
    assert np.isfinite(coords.stack().dropna()).all()
    assert new.loc[new['분석가능'], ['lon', 'lat', 'x_5179', 'y_5179']].notna().all().all()
    assert new.loc[new['분석가능'], 'inside_seoul'].all()
    adoption = pd.read_csv(DATA / '채택목록.csv')
    # Catalog also retains retail and the non-main public-sports sensitivity row.
    assert len(adoption) == 34 and adoption['시설'].eq(SPORT_FOLDER).sum() == 1
    adoption[adoption['시설'].eq(SPORT_FOLDER)].to_csv(HERE / '근거/제외_이전채택기록.csv', index=False, encoding='utf-8-sig')
    adoption = adoption[adoption['시설'].ne(SPORT_FOLDER)].reset_index(drop=True)
    adoption.to_csv(out / '채택목록.csv', index=False, encoding='utf-8-sig')
    assert len(adoption) == 33
    before = old.groupby(['시설', 'year']).size().rename('before')
    after = new.groupby(['시설', 'year']).size().rename('after')
    comparison = pd.concat([before, after], axis=1).fillna(0).astype(int)
    comparison['removed'] = comparison['before'] - comparison['after']
    assert (comparison.loc[comparison.index.get_level_values(0) != SPORT, 'removed'] == 0).all()
    comparison.to_csv(HERE / '시설연도_전후비교.csv', encoding='utf-8-sig')
    new.groupby(['국가기준_구분', '국가기준_시설', 'year']).size().rename('rows').to_csv(
        HERE / '국가기준_분류수.csv', encoding='utf-8-sig')
    year_counts = {str(y): {'before': int((old.year == y).sum()), 'after': int((new.year == y).sum()),
                            'removed': int(((old.year == y) & old['시설'].eq(SPORT)).sum())}
                   for y in [2020, 2025]}
    summary = {
        'release': 'facility-v1.4', 'PASS': True, 'file': '데이터/' + ANALYSIS,
        'sha256': sha(out / ANALYSIS), 'baseline_release': 'facility-v1.3',
        'baseline_sha256': baseline['analysis_sha256'], 'rows': len(new), 'columns': len(new.columns),
        'n_facility': 32, 'type_year_groups': 64, 'all_32_both_years': True,
        'year_counts': year_counts, 'excluded_exact_type': SPORT, 'excluded_rows': len(old) - len(new),
        'excluded_years': [2020, 2025], 'new_replacement_facilities': 0,
        'remaining_rows_values_schema_order_exact': True, 'numeric_value_bits_and_string_utf8_exact': True,
        'non_sports_row_changes': 0, 'coordinate_changes': 0, 'immutable_adopted_input_files': count,
        'adopted_input_hash_changes': 0, 'active_adopted_types': 31, 'preserved_excluded_adopted_types': 1,
        'catalog_rows': 33, 'catalog_includes_retail_and_nonmain_public_sports': True,
        'integrated_rows': len(merged), 'integrated_types': 31, 'integrated_filtered_values_exact': True,
        'analysis_ready': int(new['분석가능'].sum()), 'analysis_ready_pct': float(new['분석가능'].mean() * 100),
        'remaining_null_coordinates': int(new.lon.isna().sum()),
        'coordinates_finite_where_present': True, 'duplicate_extra_rows': int(new.duplicated(['시설', 'facility_id', 'year']).sum()),
        'allowed_duplicate': ['버스정류장', 'BUS_15143', 2020],
        'functional_categories': 7, 'main_facility_types': 27, 'control_facility_types': 5,
        'new_http_calls': 0, 'credentials_read': False, 'git_mutations': 0, 'accessibility_mutations': 0,
        'consumer_status': '06 access-engine-v3.2 remains facility-v1.3/33 types/8 categories. Separate rebuild required.',
        'time_assumption': 'Public facility nearby-time snapshots are accepted proxies, not exact historical verification.',
        'retail_status': 'Historical original requested but not obtained; current retail unchanged.',
        'excluded_candidate_count_interpretation': 'Recorded candidates are not verified missing physical facilities or measured outcome impact.'}
    write_json(out / '검증결과.json', summary)
    write_json(HERE / 'stage_verification.json', summary)
    files = [{'relative_path': '데이터/' + name,
              'staged_relative_path': (out / name).relative_to(PKG).as_posix(),
              'old_sha256': sha(DATA / name), 'new_sha256': sha(out / name),
              'old_bytes': (DATA / name).stat().st_size, 'new_bytes': (out / name).stat().st_size}
             for name in FILES]
    write_json(HERE / 'promotion_manifest.json', {'release': 'facility-v1.4', 'previous': 'facility-v1.3',
               'file_count': len(files), 'old_total_bytes': sum(f['old_bytes'] for f in files), 'files': files})
    print(json.dumps(summary, ensure_ascii=False))


def verify():
    evidence = validate_cleanup_state(HERE)
    manifest = read_json(HERE / 'promotion_manifest.json')
    for item in manifest['files']:
        assert sha(PKG / item['relative_path']) == item['new_sha256'], item['relative_path']
    archive_items = {item['relative_path']: item for item in evidence['files']}
    if evidence['historical_comparison_available']:
        exact_filtered(archive_items['데이터/' + ANALYSIS]['archive'], DATA / ANALYSIS, '시설', SPORT)
        exact_filtered(archive_items['데이터/' + INTEGRATED]['archive'], DATA / INTEGRATED, '시설', SPORT_FOLDER)
        adoption_old = pd.read_csv(archive_items['데이터/채택목록.csv']['archive'])
        pd.testing.assert_frame_equal(pd.read_csv(DATA / '채택목록.csv'),
            adoption_old[adoption_old['시설'].ne(SPORT_FOLDER)].reset_index(drop=True), check_exact=True)
    count = unchanged_inputs()
    out = HERE / 'rebuild_check'
    build(out)
    for name in [ANALYSIS, INTEGRATED, '_요약_시설별_수_좌표.csv']:
        assert sha(DATA / name) == sha(out / name), name
    result = {
        'release': 'facility-v1.4', 'PASS': True,
        'verified_at_utc': datetime.now(timezone.utc).isoformat(),
        'sha256': sha(DATA / ANALYSIS), 'rows': 584766,
        'canonical_hashes_verified': True, 'adopted_input_files_verified': count,
        'offline_rebuild_hashes_exact': True,
        'historical_comparison_performed_this_run': evidence['historical_comparison_available'],
        'historical_evidence_verified': True, 'historical_evidence_path': HISTORY_RELATIVE,
        'historical_comparison_observed_at_utc': evidence['history']['historical_comparison']['verified_at_utc'],
        'old_generated_files_state': evidence['mode'],
        'deletion_receipt_verified': evidence['receipt_verified'],
        'deletion_receipt_path': RECEIPT_RELATIVE if evidence['receipt_verified'] else None,
        'note': 'Fresh checks cover current v1.4 hashes and offline reproduction. After authorized deletion, exact v1.3 comparison is preserved historical evidence, not rerun.'}
    write_json(HERE / 'final_verification.json', result)
    write_json(HERE / 'build_hashes.json', {str(f.relative_to(PKG)): sha(f) for f in [
        BUILD / 'build_통합.py', BUILD / 'build_분석용.py', BUILD / 'facility_selection.py',
        BUILD / '시설_선택규칙.json', Path(__file__)]})
    print(json.dumps({'PASS': True, 'sha256': result['sha256'], 'rows': result['rows'],
                      'rebuild_exact': True, 'historical_comparison_this_run': result['historical_comparison_performed_this_run'],
                      'old_files_state': evidence['mode'], 'unchanged_inputs': count}))


if __name__ == '__main__':
    assert len(sys.argv) == 2 and sys.argv[1] in ['stage', 'verify']
    {'stage': stage, 'verify': verify}[sys.argv[1]]()
