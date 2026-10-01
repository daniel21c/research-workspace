"""Explicit, versioned facility selection; historical adopted inputs stay immutable."""
import json
import os
from pathlib import Path


def load_selection():
    path = Path(os.environ.get('FAC_SELECTION_CONFIG') or
                Path(__file__).with_name('시설_선택규칙.json'))
    rule = json.loads(path.read_text(encoding='utf-8'))
    assert rule['release'] == 'facility-v1.4'
    assert rule['excluded'] == [{
        'adopted_folder': '체육시설업_조건부',
        'analysis_facility': '체육시설업',
        'years': [2020, 2025],
    }], 'Unexpected exclusion scope'
    return rule


SELECTION = load_selection()


def excluded(folder, year):
    return any(folder == item['adopted_folder'] and int(year) in item['years']
               for item in SELECTION['excluded'])
