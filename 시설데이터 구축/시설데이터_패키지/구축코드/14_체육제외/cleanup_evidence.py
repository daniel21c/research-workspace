"""Fail-closed evidence gate for the authorized retirement of v1.3 generated files.

The historical comparison is a sealed prior observation, never a fresh test after
deletion. Expected digest anchors are committed as source constants after review.
"""
import hashlib
import json
from pathlib import Path

HISTORY_SHA256 = '87088f4155bdab48f0137d07dc8ce8a9239e79d3b8ebcf4eef7d4a859f4cd31a'
RECEIPT_SHA256 = '6ad9ac61c2bb7b7c3296c21a4144d14bccf4bd0d4d06afca190565189f21d43b'
HISTORY_RELATIVE = 'cleanup_20260929/historical_evidence.json'
RECEIPT_RELATIVE = 'cleanup_20260929/deletion_receipt.json'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_sealed(path, expected):
    if not expected or not Path(path).is_file():
        raise AssertionError(f'Missing required sealed evidence: {Path(path).name}')
    if digest(path) != expected:
        raise AssertionError(f'Evidence digest mismatch: {Path(path).name}')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def validate_cleanup_state(here):
    here = Path(here)
    history = load_sealed(here / HISTORY_RELATIVE, HISTORY_SHA256)
    assert history['historical_comparison']['PASS'] is True
    assert history['historical_comparison']['performed_before_deletion'] is True
    assert history['old_analysis_sha256'] == '1a097e954a134d4440a64bf668252943de0ace6a0bc38ec5b5f499c36be17a47'
    assert history['new_analysis_sha256'] == 'c0857567127210d823bb57cea01799f2cc46917ab636be84ab441556f97158cb'
    for item in history['sealed_files']:
        path = here / item['relative_path']
        assert path.is_file() and digest(path) == item['sha256'], f"Evidence changed: {item['relative_path']}"
    files = history['old_generated_files']
    assert len(files) == 5 and sum(item['old_bytes'] for item in files) == 76782692
    exists = [Path(item['archive']).exists() for item in files]
    receipt_path = here / RECEIPT_RELATIVE
    if all(exists):
        assert not receipt_path.exists(), 'Deletion receipt conflicts with existing old files'
        assert RECEIPT_SHA256 is None, 'Deletion seal conflicts with existing old files'
        for item in files:
            path = Path(item['archive'])
            assert path.is_file() and path.stat().st_size == item['old_bytes'] and digest(path) == item['old_sha256']
        return {'mode': 'old_files_present', 'history': history, 'files': files,
                'historical_comparison_available': True, 'receipt_verified': False}
    assert not any(exists), 'Partial or unexplained loss of old comparison files'
    receipt = load_sealed(receipt_path, RECEIPT_SHA256)
    assert receipt['status'] == 'deleted' and receipt['deleted_file_count'] == 5
    assert receipt['deleted_bytes'] == 76782692 and receipt['historical_evidence_sha256'] == HISTORY_SHA256
    assert receipt['authorization'] == 'user_authorized_after_access_v3.3_validation'
    assert receipt['files'] == files, 'Receipt file scope differs from the sealed history'
    assert receipt['all_targets_absent_after'] is True
    assert receipt['all_old_hashes_sizes_verified_before'] is True
    assert receipt['canonical_sha256_verified'] == history['new_analysis_sha256']
    return {'mode': 'authorized_deletion_with_sealed_history', 'history': history, 'files': files,
            'historical_comparison_available': False, 'receipt_verified': True}
