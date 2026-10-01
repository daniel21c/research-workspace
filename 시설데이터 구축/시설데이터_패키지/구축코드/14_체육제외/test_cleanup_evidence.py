"""Synthetic bounded checks; never move or delete production evidence or data."""
import copy
import json
from pathlib import Path
from datetime import datetime, timezone
import cleanup_evidence as gate

HERE = Path(__file__).resolve().parent
BASE = HERE / 'cleanup_20260929' / 'negative_test_fixtures'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def fixture(label):
    root = BASE / label
    root.mkdir(parents=True, exist_ok=True)
    history = json.loads((HERE / gate.HISTORY_RELATIVE).read_text(encoding='utf-8'))
    for item in history['old_generated_files']:
        item['archive'] = str(root / 'synthetic_absent_old_files' / Path(item['archive']).name)
    child = root / 'synthetic_evidence.json'
    write(child, {'synthetic': True})
    history['sealed_files'] = [{'relative_path': child.name, 'sha256': gate.digest(child)}]
    write(root / gate.HISTORY_RELATIVE, history)
    gate.HISTORY_SHA256 = gate.digest(root / gate.HISTORY_RELATIVE)
    receipt = {'status': 'deleted', 'deleted_file_count': 5, 'deleted_bytes': 76782692,
               'historical_evidence_sha256': gate.HISTORY_SHA256,
               'authorization': 'user_authorized_after_access_v3.3_validation',
               'files': copy.deepcopy(history['old_generated_files']),
               'all_targets_absent_after': True, 'all_old_hashes_sizes_verified_before': True,
               'canonical_sha256_verified': history['new_analysis_sha256']}
    write(root / gate.RECEIPT_RELATIVE, receipt)
    gate.RECEIPT_SHA256 = gate.digest(root / gate.RECEIPT_RELATIVE)
    return root, history, receipt


def tests():
    original = gate.HISTORY_SHA256, gate.RECEIPT_SHA256
    results = []
    try:
        root, _, _ = fixture('valid_recorded_deletion')
        result = gate.validate_cleanup_state(root)
        assert result['mode'] == 'authorized_deletion_with_sealed_history'
        assert not result['historical_comparison_available'] and result['receipt_verified']
        results.append({'test': 'valid_receipt_uses_history_without_fresh_comparison', 'PASS': True})
        for label in ['missing_history', 'tampered_history', 'missing_receipt', 'tampered_receipt',
                      'tampered_child_evidence', 'receipt_wrong_scope', 'partial_old_files', 'unsealed_receipt']:
            root, history, receipt = fixture(label)
            # Missing-file tests redirect the module path to a nonexistent fixture;
            # no production or fixture file is deleted.
            history_relative, receipt_relative = gate.HISTORY_RELATIVE, gate.RECEIPT_RELATIVE
            try:
                if label == 'missing_history': gate.HISTORY_RELATIVE = 'absent.json'
                elif label == 'tampered_history': (root / gate.HISTORY_RELATIVE).write_text('{}', encoding='utf-8')
                elif label == 'missing_receipt': gate.RECEIPT_RELATIVE = 'absent.json'
                elif label == 'tampered_receipt': (root / gate.RECEIPT_RELATIVE).write_text('{}', encoding='utf-8')
                elif label == 'tampered_child_evidence': (root / 'synthetic_evidence.json').write_text('{}', encoding='utf-8')
                elif label == 'receipt_wrong_scope':
                    receipt['files'] = receipt['files'][:-1]
                    write(root / gate.RECEIPT_RELATIVE, receipt)
                    gate.RECEIPT_SHA256 = gate.digest(root / gate.RECEIPT_RELATIVE)
                elif label == 'partial_old_files':
                    path = Path(history['old_generated_files'][0]['archive'])
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b'synthetic')
                elif label == 'unsealed_receipt': gate.RECEIPT_SHA256 = None
                try:
                    gate.validate_cleanup_state(root)
                except AssertionError:
                    results.append({'test': label, 'PASS': True, 'rejected': True})
                else:
                    raise AssertionError(f'Negative case incorrectly passed: {label}')
            finally:
                gate.HISTORY_RELATIVE, gate.RECEIPT_RELATIVE = history_relative, receipt_relative
    finally:
        gate.HISTORY_SHA256, gate.RECEIPT_SHA256 = original
    output = {'PASS': True, 'tests': len(results), 'synthetic_only': True,
              'production_mutations': 0, 'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'results': results}
    write(HERE / 'cleanup_20260929/negative_tests.json', output)
    print(json.dumps({'PASS': True, 'tests': len(results), 'negative_cases': 8, 'production_mutations': 0}))


if __name__ == '__main__':
    tests()
