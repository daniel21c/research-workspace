#!/usr/bin/env python3
"""Local, fail-closed Research task ledger. No network or model calls.

This is cooperative task attribution, not a filesystem provenance oracle. Writers
must claim paths before edits. Unknown writers, missing starts and interrupted
tasks never authorize a commit. Native hook Stop means a turn stopped, not that
the scientific task was validated; verification must be recorded separately.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

START = '<!-- research-sync:begin -->'
END = '<!-- research-sync:end -->'
SAFE_EXT = {'.md', '.py', '.txt'}
DENIED_PARTS = {'data', 'raw', 'output', 'outputs', 'cache', 'logs', '.git', '.env',
                '_secrets', 'secrets', 'node_modules', '__pycache__', '0_raw', '1_output'}
SECRET = re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{24,})|(?:api[_-]?key|password|secret|token)\s*[:=]\s*[\"\'][A-Za-z0-9_+/=-]{16,}[\"\']', re.I)


class Refused(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def ident(value):
    if not re.fullmatch(r'[A-Za-z0-9_.:@-]{1,160}', value or ''):
        raise Refused('invalid_identifier')
    return value


def no_links(path):
    for part in [path, *path.parents]:
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise Refused('symlink_or_reparse_point')


@contextlib.contextmanager
def file_lock(path, timeout=15):
    """OS advisory lock, automatically released on process death."""
    no_links(path)
    with open(path, 'a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    raise Refused('ledger_busy')
                time.sleep(.05)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class Sync:
    def __init__(self, root):
        self.root = Path(root).absolute()
        no_links(self.root)
        self.config = self.root / '.research-sync/policy.json'
        no_links(self.config)
        self.policy = json.loads(self.config.read_text(encoding='utf-8'))
        if self.root.resolve() != Path(self.policy['expected_root']).resolve():
            raise Refused('expected_root_mismatch')
        self.state = self.root / '.research-sync/state'
        no_links(self.state)
        self.state.mkdir(parents=True, exist_ok=True)
        self.handoff = self.policy['handoff']
        self.allow = set(self.policy['tracked_paths'])
        self.new_allow = set(self.policy.get('approved_new_paths', []))
        for rel in self.allow | self.new_allow | {self.handoff}:
            self.path(rel)
        self.empty_hooks = self.state / 'empty-hooks'
        self.empty_hooks.mkdir(exist_ok=True)
        self.conn = None

    def path(self, rel):
        if not isinstance(rel, str) or '\\' in rel or ':' in rel or any(c in rel for c in '\r\n\t|'):
            raise Refused('invalid_path')
        p = PurePosixPath(rel)
        if p.is_absolute() or str(p) != rel or '..' in p.parts or any(x.endswith((' ', '.')) for x in p.parts):
            raise Refused('path_traversal')
        if any(x.lower() in DENIED_PARTS for x in p.parts) or p.suffix.lower() not in SAFE_EXT:
            raise Refused('forbidden_file_type_or_directory')
        # Automation control surfaces must be reviewed separately, never self-committed.
        if rel.startswith(('tools/', '.research-sync/', '.codex/')) or rel in {'AGENTS.md', 'GEMINI.md'}:
            raise Refused('automation_control_path')
        path = self.root.joinpath(*p.parts)
        no_links(path)
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise Refused('path_outside_root')
        return path

    def git(self, *args, env=None, data=None, check=True):
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        if env:
            clean_env.update(env)
        proc = subprocess.run(['git', '-c', f'core.hooksPath={self.empty_hooks}',
                               '-c', 'core.fsmonitor=false', '-c', 'core.quotePath=false',
                               '-c', 'commit.gpgSign=false', '-C', str(self.root), *args],
                              input=data, capture_output=True, env=clean_env, timeout=30)
        if check and proc.returncode:
            raise Refused('git_command_failed:' + args[0])
        return proc.stdout if check else proc

    def repository(self):
        actual = Path(self.git('rev-parse', '--show-toplevel').decode().strip()).resolve()
        if actual != self.root.resolve() or not (self.root / '.git').is_dir():
            raise Refused('exact_standalone_git_root_required')
        no_links(self.root / '.git')
        branch = self.git('symbolic-ref', '--quiet', '--short', 'HEAD').decode().strip()
        if not branch.startswith('codex/'):
            raise Refused('codex_branch_required')
        head = self.git('rev-parse', '--verify', 'HEAD').decode().strip()
        return branch, head

    @contextlib.contextmanager
    def locked(self):
        with file_lock(self.state / 'ledger.lock'):
            no_links(self.state / 'ledger.sqlite3')
            self.conn = sqlite3.connect(self.state / 'ledger.sqlite3')
            self.conn.executescript('''
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, session TEXT, app TEXT,
                  started TEXT, status TEXT, body TEXT);
                CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, at TEXT, task TEXT,
                  event TEXT, result TEXT);
            ''')
            try:
                yield
                self.conn.commit()
            finally:
                self.conn.close()
                self.conn = None

    def meta(self, key, default=None):
        row = self.conn.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def setmeta(self, key, value):
        self.conn.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', (key, json.dumps(value)))

    def event(self, event_id, task, name, result):
        self.conn.execute('INSERT OR IGNORE INTO events VALUES (?,?,?,?,?)',
                          (ident(event_id), now(), task, name, result))

    def task(self, task_id):
        row = self.conn.execute('SELECT body FROM tasks WHERE id=?', (ident(task_id),)).fetchone()
        if not row:
            raise Refused('missing_begin')
        return json.loads(row[0])

    def save(self, task):
        self.conn.execute('INSERT OR REPLACE INTO tasks VALUES (?,?,?,?,?,?)',
                          (task['id'], task['session'], task['app'], task['started'],
                           task['status'], json.dumps(task, ensure_ascii=False)))

    def content(self, rel, normalize=False):
        path = self.path(rel)
        if not path.exists():
            return None
        if not path.is_file() or path.stat().st_size > self.policy.get('max_file_bytes', 1048576):
            raise Refused('file_too_large_or_not_regular')
        data = path.read_bytes()
        text = data.decode('utf-8-sig')
        if '\0' in text:
            raise Refused('binary_file')
        if normalize and rel == self.handoff:
            text = self.unmanaged(text)
            data = text.encode('utf-8')
        return data

    @staticmethod
    def unmanaged(text):
        text = text.replace('\r\n', '\n')
        if text.count(START) != 1 or text.count(END) != 1:
            raise Refused('handoff_markers_invalid')
        before, tail = text.split(START)
        _, after = tail.split(END)
        return before + START + END + after

    def fingerprint(self, rel):
        data = self.content(rel, normalize=True)
        return digest(data) if data is not None else None

    def tracked(self):
        return set(self.git('ls-files', '-z').decode('utf-8').rstrip('\0').split('\0')) - {''}

    def dirty(self):
        result = self.git('diff', 'HEAD', '--name-only', '-z').decode('utf-8')
        dirty = set(result.rstrip('\0').split('\0')) - {''}
        if self.handoff in dirty:
            original = self.git('show', f'HEAD:{self.handoff}').decode('utf-8-sig')
            if digest(self.unmanaged(original).encode()) == self.fingerprint(self.handoff):
                dirty.remove(self.handoff)
        return sorted(dirty)

    def begin(self, task_id, app, session=None):
        ident(task_id)
        session = ident(session or task_id)
        if app not in {'codex', 'antigravity', 'manual'}:
            raise Refused('unknown_app')
        existing = self.conn.execute('SELECT body FROM tasks WHERE id=?', (task_id,)).fetchone()
        if existing:
            return json.loads(existing[0])
        branch, head = self.repository()
        tracked = self.tracked()
        snapshots = {p: self.fingerprint(p) for p in sorted((self.allow & tracked) | self.new_allow | {self.handoff})}
        active = self.conn.execute("SELECT body FROM tasks WHERE status='active'").fetchall()
        for (raw,) in active:
            other = json.loads(raw)
            other['overlap'] = True
            self.save(other)
        task = dict(id=task_id, app=app, session=session, started=now(), status='active',
                    branch=branch, head=head, baseline=snapshots, baseline_dirty=self.dirty(),
                    claimed=[], overlap=bool(active), verification='not_run', result='started')
        self.save(task)
        self.event(task_id + ':begin', task_id, 'begin', 'started')
        self.render()
        return task

    def claim(self, task_id, paths):
        task = self.task(task_id)
        if task['status'] != 'active':
            raise Refused('task_not_active')
        for rel in paths:
            self.path(rel)
            if rel not in self.allow | self.new_allow or rel == self.handoff:
                raise Refused('path_not_explicitly_allowlisted')
            if rel not in task['baseline']:
                raise Refused('new_path_not_approved_before_begin')
            if rel in self.new_allow and rel not in self.tracked() and task['baseline'][rel] is not None:
                raise Refused('preexisting_untracked_file')
            if self.fingerprint(rel) != task['baseline'][rel]:
                raise Refused('claim_must_precede_edit')
        task['claimed'] = sorted(set(task['claimed']) | set(paths))
        self.save(task)
        return {'claimed': task['claimed']}

    def note(self, task_id, summary, evidence, remaining, next_step):
        task = self.task(task_id)
        if task['status'] != 'active':
            raise Refused('task_not_active')
        notes = {}
        for key, value in dict(summary=summary, evidence=evidence, remaining=remaining, next_step=next_step).items():
            if not value.strip() or len(value) > 600 or SECRET.search(value):
                raise Refused('note_missing_too_long_or_possible_secret')
            if re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b01[016789][- ]?\d{3,4}[- ]?\d{4}\b', value):
                raise Refused('note_contains_personal_contact')
            notes[key] = ' '.join(value.split()).replace('|', '/').replace('<', '&lt;').replace('>', '&gt;')
        task['notes'] = notes
        self.save(task)
        self.render()
        return {'notes_recorded': True}

    def verify(self, task_id, value):
        task = self.task(task_id)
        if task['status'] != 'active' or value not in {'passed', 'not_required', 'failed', 'not_run'}:
            raise Refused('invalid_verification')
        task['verification'] = value
        task['verified_snapshot'] = {p: self.fingerprint(p) for p in task['claimed']}
        self.save(task)
        return {'verification': value}

    def plan(self, task, outcome):
        if outcome != 'completed':
            return [], 'interrupted_or_unknown'
        if not self.meta('enabled', False):
            return [], 'paused'
        branch, head = self.repository()
        if branch != task['branch'] or head != task['head']:
            return [], 'head_or_branch_changed'
        if task['baseline_dirty']:
            return [], 'baseline_dirty'
        if task['overlap']:
            return [], 'overlapping_tasks'
        if not task.get('notes'):
            return [], 'handoff_notes_missing'
        if task['verification'] not in {'passed', 'not_required'}:
            return [], 'verification_missing_or_failed'
        if not task['claimed']:
            return [], 'no_explicit_path_claim'
        changed = [p for p in task['claimed'] if self.fingerprint(p) != task['baseline'][p]]
        dirty = self.dirty()
        if set(dirty) - set(task['claimed']):
            return [], 'unclaimed_changes'
        if self.fingerprint(self.handoff) != task['baseline'][self.handoff]:
            return [], 'handoff_manual_edit'
        if any(self.fingerprint(p) != task.get('verified_snapshot', {}).get(p) for p in task['claimed']):
            return [], 'changed_after_verification'
        staged = set(self.git('diff', '--cached', '--name-only', '-z').decode().rstrip('\0').split('\0')) - {''}
        if staged & (set(changed) | {self.handoff}):
            return [], 'user_staged_owned_path'
        for rel in changed:
            data = self.content(rel)
            if data is None:
                return [], 'deletion_requires_manual_commit'
            if SECRET.search(data.decode('utf-8-sig')):
                return [], 'possible_secret'
        return changed, 'eligible' if changed else 'no_changes'

    def finish(self, task_id, outcome='completed', dry_run=False):
        task = self.task(task_id)
        if task['status'] != 'active':
            return {'result': task['result'], 'commit': task.get('commit'), 'duplicate': True}
        paths, reason = self.plan(task, outcome)
        if dry_run:
            return {'result': reason, 'paths': paths, 'dry_run': True}
        task['status'] = 'completed' if outcome == 'completed' else 'interrupted'
        task['result'] = reason
        task['changed'] = paths
        self.save(task)
        self.event(task_id + ':finish', task_id, outcome, reason)
        self.render()
        # Persist intent before git writes. A crash after ref update is diagnosed,
        # never retried automatically; no duplicate commit can then be produced.
        self.conn.commit()
        if reason == 'eligible':
            try:
                task['commit'] = self.commit(task, paths + [self.handoff])
                task['result'] = 'committed'
            except Refused as error:
                task['result'] = str(error)
                self.save(task)
                self.render()
            self.save(task)
        return {'result': task['result'], 'commit': task.get('commit'), 'paths': paths}

    def commit(self, task, paths):
        """Build commit using immutable blobs and private indexes; preserve staging.

        Hold Git's real index.lock; update only previously UNSTAGED committed
        entries in a copy of the real index. Unrelated staged entries are kept.
        Git hooks, clean filters, signing and external diff programs are not run.
        """
        gitdir = self.root / '.git'
        index = gitdir / 'index'
        lock = gitdir / 'index.lock'
        no_links(index)
        no_links(lock)
        snapshots = {p: self.content(p) for p in paths}
        if any(data is None or SECRET.search(data.decode('utf-8-sig')) for data in snapshots.values()):
            raise Refused('unsafe_commit_content')
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise Refused('git_index_busy')
        ref_updated = False
        try:
            old_index = index.read_bytes() if index.exists() else None
            branch, head = self.repository()
            if (branch, head) != (task['branch'], task['head']):
                raise Refused('head_or_branch_changed')
            staged = set(self.git('diff', '--cached', '--name-only', '-z').decode().rstrip('\0').split('\0')) - {''}
            if staged & set(paths):
                raise Refused('user_staged_owned_path')
            with tempfile.TemporaryDirectory(prefix='indexes-', dir=self.state) as tmp:
                candidate = str(Path(tmp) / 'commit-index')
                preserved = str(Path(tmp) / 'preserved-index')
                self.git('read-tree', head, env={'GIT_INDEX_FILE': candidate})
                if old_index is not None:
                    Path(preserved).write_bytes(old_index)
                else:
                    self.git('read-tree', head, env={'GIT_INDEX_FILE': preserved})
                for rel, data in snapshots.items():
                    attrs = self.git('check-attr', '-z', 'text', 'eol', 'filter', 'working-tree-encoding', '--', rel).decode().split('\0')
                    values = dict(zip(attrs[1::3], attrs[2::3]))
                    if values != {'text': 'set', 'eol': 'lf', 'filter': 'unspecified', 'working-tree-encoding': 'unspecified'}:
                        raise Refused('unsupported_git_attributes')
                    blob = self.git('hash-object', '-w', '--stdin', data=data.replace(b'\r\n', b'\n')).decode().strip()
                    entry = self.git('ls-tree', head, '--', rel).decode().strip()
                    mode = entry.split(' ', 1)[0] if entry else '100644'
                    if mode not in {'100644', '100755'}:
                        raise Refused('non_regular_git_entry')
                    for private in (candidate, preserved):
                        self.git('update-index', '--add', '--cacheinfo', mode, blob, rel,
                                 env={'GIT_INDEX_FILE': private})
                tree = self.git('write-tree', env={'GIT_INDEX_FILE': candidate}).decode().strip()
                commit = self.git('commit-tree', tree, '-p', head,
                                  data=f'research: {task["app"]} task {task["id"][:48]}\n'.encode()).decode().strip()
                if any(self.content(p) != data for p, data in snapshots.items()):
                    raise Refused('files_changed_during_commit')
                if (index.read_bytes() if index.exists() else None) != old_index:
                    raise Refused('index_changed_during_commit')
                journal = dict(task=task['id'], old=head, new=commit, branch=branch, stage='prepared')
                self.setmeta('commit_journal', journal)
                self.conn.commit()
                with os.fdopen(descriptor, 'wb') as out:
                    descriptor = None
                    out.write(Path(preserved).read_bytes())
                    out.flush()
                    os.fsync(out.fileno())
                self.git('update-ref', f'refs/heads/{branch}', commit, head)
                ref_updated = True
                os.replace(lock, index)
                self.setmeta('commit_journal', None)
                return commit
        finally:
            if descriptor is not None:
                os.close(descriptor)
            # If interrupted between ref and index, retain the lock and journal
            # for an explicit repair. Never overwrite potentially new user work.
            if not ref_updated and lock.exists():
                lock.unlink()

    def render(self):
        path = self.path(self.handoff)
        data = path.read_bytes()
        text = data.decode('utf-8-sig')
        self.unmanaged(text)
        rows = self.conn.execute('SELECT body FROM tasks ORDER BY started DESC, rowid DESC LIMIT 12').fetchall()
        lines = [START, '', '자동 기록은 에이전트가 실행한 작업 명령과 직접 입력한 인수인계입니다. 연구 완료·타당성 판정이 아닙니다.',
                 '`eligible`은 커밋 준비 판정입니다. 실제 커밋 해시와 보류 원인은 `tools/research_sync.py status`에서 확인합니다.', '',
                 '| UTC 시작 | 앱 | 작업 식별자 | 상태 / 로컬 커밋 판정 | 검증 | 파일 |',
                 '|---|---|---|---|---|---|']
        for (raw,) in rows:
            task = json.loads(raw)
            files = ', '.join(task.get('changed') or task.get('claimed') or []) or '—'
            lines.append(f'| {task["started"]} | {task["app"]} | `{task["id"]}` | {task["status"]} / {task["result"]} | {task["verification"]} | {files} |')
        for (raw,) in rows:
            task = json.loads(raw)
            notes = task.get('notes')
            if notes:
                lines.extend(['', f'**{task["app"]} / {task["id"]}**',
                              f'- 실제 변경·결정: {notes["summary"]}',
                              f'- 확인 근거: {notes["evidence"]}',
                              f'- 미해결·한계: {notes["remaining"]}',
                              f'- 다음 단계: {notes["next_step"]}'])
        lines.extend(['', END])
        before, tail = text.split(START)
        _, after = tail.split(END)
        result = (before + '\n'.join(lines) + after).encode('utf-8')
        if result != data:
            if path.read_bytes() != data:
                raise Refused('handoff_changed_during_render')
            temporary = self.state / 'handoff.tmp'
            no_links(temporary)
            temporary.write_bytes(result)
            os.replace(temporary, path)

    def status(self):
        tasks = [json.loads(r[0]) for r in self.conn.execute('SELECT body FROM tasks ORDER BY rowid DESC LIMIT 12')]
        return dict(enabled=self.meta('enabled', False), expected_root=str(self.root),
                    tasks=[{k: t.get(k) for k in ('id', 'app', 'status', 'result', 'commit', 'claimed', 'verification')} for t in tasks],
                    commit_journal=self.meta('commit_journal'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(Path(__file__).resolve().parents[1]))
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('enable', 'pause', 'disable', 'status'):
        sub.add_parser(name)
    begin = sub.add_parser('begin')
    begin.add_argument('--task', required=True)
    begin.add_argument('--app', choices=['codex', 'antigravity', 'manual'], required=True)
    begin.add_argument('--session')
    claim = sub.add_parser('claim')
    claim.add_argument('--task', required=True)
    claim.add_argument('paths', nargs='+')
    note = sub.add_parser('note')
    note.add_argument('--task', required=True)
    for name in ('summary', 'evidence', 'remaining', 'next-step'):
        note.add_argument('--' + name, required=True)
    verify = sub.add_parser('verify')
    verify.add_argument('--task', required=True)
    verify.add_argument('--result', choices=['passed', 'not_required', 'failed', 'not_run'], required=True)
    finish = sub.add_parser('finish')
    finish.add_argument('--task', required=True)
    finish.add_argument('--outcome', choices=['completed', 'interrupted', 'unknown'], default='completed')
    finish.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        sync = Sync(args.root)
        with sync.locked():
            if sync.meta('commit_journal') and args.command not in {'status', 'pause', 'disable'}:
                raise Refused('unresolved_commit_journal_requires_review')
            if args.command == 'enable':
                sync.repository()
                sync.setmeta('enabled', True)
                result = {'enabled': True}
            elif args.command in {'pause', 'disable'}:
                sync.setmeta('enabled', False)
                result = {'enabled': False}
            elif args.command == 'begin':
                task = sync.begin(args.task, args.app, args.session)
                result = {k: task[k] for k in ('id', 'result', 'baseline_dirty', 'overlap')}
            elif args.command == 'claim':
                result = sync.claim(args.task, args.paths)
            elif args.command == 'note':
                result = sync.note(args.task, args.summary, args.evidence, args.remaining, args.next_step)
            elif args.command == 'verify':
                result = sync.verify(args.task, args.result)
            elif args.command == 'finish':
                result = sync.finish(args.task, args.outcome, args.dry_run)
            else:
                result = sync.status()
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (Refused, OSError, ValueError, sqlite3.Error, subprocess.TimeoutExpired) as error:
        # Do not echo raw payloads, git stderr or file contents.
        print(json.dumps({'error': str(error) if isinstance(error, Refused) else type(error).__name__}))
        return 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
