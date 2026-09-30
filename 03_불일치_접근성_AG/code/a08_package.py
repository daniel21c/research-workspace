# -*- coding: utf-8 -*-
"""공동연구자 공유 패키지(AG 확정본). 작업 폴더와 같은 이름(code/results/manuscript)을 유지해 패키지 안에서 코드가 그대로 돈다.
원자료·격자 단위 중간 산출(results/_cache)은 넣지 않는다.
실행: python code/a08_package.py     출력: package/AG_확정본_공동연구자패키지_20260930/ 와 같은 이름의 zip.
빌드 후 zip을 새 폴더에 풀어 code/a07_claims_check.py를 실행해 결과 대조가 패키지 안에서도 통과하는지 확인한다(아래 selfcheck).
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

AG = Path(__file__).resolve().parents[1]; NAME = 'AG_확정본_공동연구자패키지_20260930'; OUT = AG / 'package' / NAME
MS = AG / 'manuscript'; RES = AG / 'results'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pdf(docx, target):
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(AG / 'code' / 'export_pdf.ps1'), '-Docx', str(docx), '-Pdf', str(target)], check=True)


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / 'manuscript').mkdir(parents=True)
    for f in ('AG_manuscript_anonymised.docx', 'AG_title_page.docx', 'AG_highlights.docx', 'AG_supplementary_appendix.docx', 'AG_cover_letter.docx', 'AG_한국어_원고.docx', 'values_used.json', 'word_count.json'):
        shutil.copy2(MS / f, OUT / 'manuscript' / f)
    for f in ('AG_manuscript_anonymised', 'AG_한국어_원고', 'AG_supplementary_appendix'):
        pdf(MS / f'{f}.docx', OUT / 'manuscript' / f'{f}.pdf')
    shutil.copytree(MS / 'figures', OUT / 'manuscript' / 'figures')
    for y in ('2020', '2025', 'appendix'):
        shutil.copytree(RES / y, OUT / 'results' / y)
    for f in ('claims_check.json', '_check_a01_vs_previous.json', 'a02_reproduction_check.json'):
        shutil.copy2(RES / f, OUT / 'results' / f)
    (OUT / 'code').mkdir()
    for f in sorted((AG / 'code').glob('*')):
        if f.suffix in ('.py', '.ps1'):
            shutil.copy2(f, OUT / 'code' / f.name)
    (OUT / 'docs').mkdir(); shutil.copy2(AG / '연구설계.md', OUT / 'docs' / '연구설계_AG확정본.md'); shutil.copy2(AG / '검수의견_대응표_20260930.md', OUT / 'docs' / '검수의견_대응표_20260930.md')
    shutil.copy2(AG / 'package' / 'README_패키지.md', OUT / 'README.md')
    rows = ['path,bytes,sha256']
    for p in sorted(OUT.rglob('*')):
        if p.is_file():
            rows.append(f'{p.relative_to(OUT).as_posix()},{p.stat().st_size},{sha(p)}')
    (OUT / 'MANIFEST.csv').write_text('\n'.join(rows) + '\n', encoding='utf-8-sig')
    z = AG / 'package' / f'{NAME}.zip'
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():
                zf.write(p, f'{NAME}/{p.relative_to(OUT).as_posix()}')
    return z, len(rows) - 1


def selfcheck(z):
    """zip을 임시 폴더에 풀고, 그 안의 code/a07_claims_check.py를 실행한다(원자료 불필요). 종료 코드 0이어야 한다."""
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(z) as zf:
            zf.extractall(td)
        root = Path(td) / NAME
        r = subprocess.run([sys.executable, '-B', str(root / 'code' / 'a07_claims_check.py')], capture_output=True, text=True, encoding='utf-8', errors='replace')
        chk = json.loads((root / 'results' / 'claims_check.json').read_text(encoding='utf-8')) if r.returncode == 0 else {}
        return {'exit_code': r.returncode, 'n_checks': chk.get('n_checks'), 'n_fail': chk.get('n_fail'), 'stderr_tail': r.stderr[-400:]}


def main():
    z, n = build(); sc = selfcheck(z)
    out = {'files': n, 'zip_bytes': z.stat().st_size, 'zip': str(z), 'selfcheck_in_fresh_extract': sc}
    assert sc['exit_code'] == 0, '패키지 안에서 a07이 실행되지 않음'
    txt = json.dumps(out, ensure_ascii=False, indent=1); (AG / 'package' / 'package_selfcheck.json').write_text(txt, encoding='utf-8')
    with zipfile.ZipFile(z, 'a', zipfile.ZIP_DEFLATED) as zf:  # 자체 점검 결과를 zip 안에도 남김(MANIFEST에는 없음)
        zf.writestr(f'{NAME}/results/package_selfcheck.json', txt)
    out['zip_bytes'] = z.stat().st_size; print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
