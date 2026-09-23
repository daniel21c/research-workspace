"""Synthetic repositories only; never uses the actual Research .git."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from research_sync import Sync, Refused, START, END

SCRIPT = Path(__file__).with_name('research_sync.py')


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='research-sync-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / '.research-sync').mkdir()
        self.policy = {'expected_root': str(self.root), 'handoff': 'handoff.md',
                       'tracked_paths': ['a.md', 'b.md', 'handoff.md'],
                       'approved_new_paths': ['new.md']}
        self.write_policy()
        for path, content in {'a.md': 'alpha\n', 'b.md': 'beta\n',
                              'handoff.md': 'Manual decision preserved.\n' + START + '\n' + END + '\n',
                              '.gitignore': '.research-sync/state/\n',
                              '.gitattributes': '* -text\n*.md text eol=lf\n'}.items():
            (self.root / path).write_text(content, encoding='utf-8')
        self.git('init', '-q', '-b', 'codex/test')
        self.git('config', 'user.name', 'Synthetic Test')
        self.git('config', 'user.email', 'synthetic@example.invalid')
        self.git('config', 'core.autocrlf', 'false')
        self.git('add', '--', 'a.md', 'b.md', 'handoff.md', '.gitignore', '.gitattributes')
        self.git('commit', '-qm', 'fixture')
        self.sync = Sync(self.root)
        with self.sync.locked():
            self.sync.setmeta('enabled', True)

    def write_policy(self):
        (self.root / '.research-sync/policy.json').write_text(json.dumps(self.policy), encoding='utf-8')

    def git(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        return subprocess.check_output(['git', '-C', str(self.root), *args], env=env, stderr=subprocess.PIPE)

    def begin(self, task='test', paths=('a.md',)):
        with self.sync.locked():
            self.sync.begin(task, 'codex')
            if paths:
                self.sync.claim(task, list(paths))

    def complete(self, task='test', outcome='completed', dry_run=False):
        with self.sync.locked():
            self.sync.note(task, 'Scoped document change.', 'Synthetic assertion passed.',
                           'Scientific analysis not executed.', 'Read next task request.')
            self.sync.verify(task, 'passed')
            return self.sync.finish(task, outcome, dry_run)

    def change(self, path='a.md', data=b'changed\n'):
        (self.root / path).write_bytes(data)

    def test_completed_commit_is_idempotent_clean_and_preserves_manual_handoff(self):
        self.begin()
        self.change()
        result = self.complete()
        self.assertEqual(result['result'], 'committed')
        self.assertEqual(self.git('diff', 'HEAD', '--name-only'), b'')
        self.assertEqual(self.git('rev-list', '--count', 'HEAD').strip(), b'2')
        self.assertEqual(set(self.git('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').decode().split()), {'a.md', 'handoff.md'})
        self.assertTrue((self.root / 'handoff.md').read_text(encoding='utf-8').startswith('Manual decision preserved.'))
        with self.sync.locked():
            self.assertTrue(self.sync.finish('test')['duplicate'])
        self.assertEqual(self.git('rev-list', '--count', 'HEAD').strip(), b'2')

    def test_baseline_dirty_never_commits(self):
        self.change()
        self.begin()
        self.change(data=b'changed again\n')
        self.assertEqual(self.complete()['result'], 'baseline_dirty')

    def test_staged_unrelated_file_is_preserved_exactly(self):
        self.begin()
        self.change()
        self.change('b.md')
        self.git('add', '--', 'b.md')
        before = (self.root / '.git/index').read_bytes()
        staged = self.git('diff', '--cached', '--binary')
        self.assertEqual(self.complete()['result'], 'unclaimed_changes')
        self.assertEqual((self.root / '.git/index').read_bytes(), before)
        self.assertEqual(self.git('diff', '--cached', '--binary'), staged)

    def test_staged_owned_file_is_preserved_exactly(self):
        self.begin()
        self.change()
        self.git('add', '--', 'a.md')
        before = (self.root / '.git/index').read_bytes()
        self.assertEqual(self.complete()['result'], 'user_staged_owned_path')
        self.assertEqual((self.root / '.git/index').read_bytes(), before)

    def test_interrupted_never_commits(self):
        self.begin()
        self.change()
        self.assertEqual(self.complete(outcome='interrupted')['result'], 'interrupted_or_unknown')
        self.assertEqual(self.git('rev-list', '--count', 'HEAD').strip(), b'1')

    def test_overlap_defers_both_tasks(self):
        self.begin('one')
        self.begin('two', ('b.md',))
        self.change()
        self.change('b.md')
        self.assertEqual(self.complete('one')['result'], 'overlapping_tasks')
        self.assertEqual(self.complete('two')['result'], 'overlapping_tasks')

    def test_claim_after_edit_refused(self):
        self.begin(paths=())
        self.change()
        with self.sync.locked(), self.assertRaisesRegex(Refused, 'precede'):
            self.sync.claim('test', ['a.md'])

    def test_forbidden_traversal_and_control_paths(self):
        for rel in ('../escape.md', 'data/a.md', 'raw/a.py', 'a.csv', 'a.md:stream',
                    'C:/a.md', '/a.md', '.git/a.md', 'tools/backdoor.py', 'AGENTS.md', 'bad|name.md'):
            with self.subTest(rel=rel), self.assertRaises(Refused):
                self.sync.path(rel)

    def test_symlink_refused(self):
        target = self.root / 'a.md'
        link = self.root / 'link.md'
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest('Host denies creation of symlinks')
        with self.assertRaisesRegex(Refused, 'symlink'):
            self.sync.path('link.md')

    def test_exact_root_and_main_branch_guards(self):
        self.policy['expected_root'] = str(self.root / 'other')
        self.write_policy()
        with self.assertRaisesRegex(Refused, 'root_mismatch'):
            Sync(self.root)
        self.git('branch', '-m', 'main')
        with self.sync.locked(), self.assertRaisesRegex(Refused, 'codex_branch'):
            self.sync.begin('test', 'codex')

    def test_no_automatic_untracked_adoption(self):
        self.change('unknown.md')
        self.change('new.md')
        self.begin(paths=())
        with self.sync.locked():
            with self.assertRaisesRegex(Refused, 'allowlisted'):
                self.sync.claim('test', ['unknown.md'])
            with self.assertRaisesRegex(Refused, 'preexisting_untracked'):
                self.sync.claim('test', ['new.md'])

    def test_approved_absent_new_file_can_commit(self):
        self.begin(paths=('new.md',))
        self.change('new.md')
        self.assertEqual(self.complete()['result'], 'committed')
        self.assertIn(b'new.md', self.git('ls-files'))

    def test_secrets_and_notes_contact_refused(self):
        self.begin()
        self.change(data=b'password="abcd1234abcd1234abcd"\n')
        self.assertEqual(self.complete()['result'], 'possible_secret')
        self.begin('two', ())
        with self.sync.locked(), self.assertRaisesRegex(Refused, 'personal_contact'):
            self.sync.note('two', 'person@example.com', 'test', 'none', 'next')

    def test_dry_run_leaves_head_handoff_and_index_unchanged(self):
        self.begin()
        self.change()
        with self.sync.locked():
            self.sync.note('test', 'changed', 'test', 'none', 'next')
            self.sync.verify('test', 'passed')
            before = [(self.root / p).read_bytes() for p in ('handoff.md', '.git/index', '.git/refs/heads/codex/test')]
            self.assertEqual(self.sync.finish('test', dry_run=True)['result'], 'eligible')
            after = [(self.root / p).read_bytes() for p in ('handoff.md', '.git/index', '.git/refs/heads/codex/test')]
            self.assertEqual(before, after)
            self.assertEqual(self.sync.task('test')['status'], 'active')

    def test_pause_missing_verification_and_changed_after_verification(self):
        self.begin()
        self.change()
        with self.sync.locked():
            self.sync.note('test', 'changed', 'test', 'none', 'next')
            self.assertEqual(self.sync.plan(self.sync.task('test'), 'completed')[1], 'verification_missing_or_failed')
            self.sync.verify('test', 'passed')
            self.change(data=b'changed after verification\n')
            self.assertEqual(self.sync.plan(self.sync.task('test'), 'completed')[1], 'changed_after_verification')
            self.sync.setmeta('enabled', False)
            self.assertEqual(self.sync.finish('test')['result'], 'paused')

    def test_head_move_and_git_index_lock_defer(self):
        self.begin()
        self.change('b.md')
        self.git('add', '--', 'b.md')
        self.git('commit', '-qm', 'another writer')
        self.change()
        self.assertEqual(self.complete()['result'], 'head_or_branch_changed')

    def test_index_lock_blocks_commit_and_preserves_files(self):
        self.begin()
        self.change()
        (self.root / '.git/index.lock').write_bytes(b'other writer')
        self.assertEqual(self.complete()['result'], 'git_index_busy')
        self.assertEqual((self.root / '.git/index.lock').read_bytes(), b'other writer')

    def test_crlf_with_autocrlf_true_leaves_clean_tree(self):
        self.git('config', 'core.autocrlf', 'true')
        self.begin()
        self.change(data=b'changed\r\nsecond\r\n')
        self.assertEqual(self.complete()['result'], 'committed')
        self.assertEqual(self.git('diff', 'HEAD', '--name-only'), b'')
        self.assertEqual(self.git('show', 'HEAD:a.md'), b'changed\nsecond\n')

    def test_no_remote_push_or_local_hooks(self):
        remote = self.root / 'remote.git'
        subprocess.check_call(['git', 'init', '--bare', '-q', str(remote)])
        self.git('remote', 'add', 'origin', str(remote))
        hook = self.root / '.git/hooks/post-commit'
        hook.write_text('#!/bin/sh\necho invoked > hook-invoked\n', encoding='utf-8')
        hook.chmod(0o755)
        self.begin()
        self.change()
        self.assertEqual(self.complete()['result'], 'committed')
        self.assertFalse((self.root / 'hook-invoked').exists())
        self.assertEqual(list((remote / 'refs/heads').iterdir()), [])

    def test_concurrent_finish_produces_one_commit(self):
        self.begin()
        self.change()
        with self.sync.locked():
            self.sync.note('test', 'changed', 'test', 'none', 'next')
            self.sync.verify('test', 'passed')
        command = [sys.executable, str(SCRIPT), '--root', str(self.root), 'finish', '--task', 'test']
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        results = []
        for process in processes:
            out, err = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 0, err.decode())
            results.append(json.loads(out))
        self.assertEqual(sum(bool(x.get('duplicate')) for x in results), 1)
        self.assertEqual(self.git('rev-list', '--count', 'HEAD').strip(), b'2')

    def test_verified_handoff_only_task_commits(self):
        self.begin(paths=())
        self.assertEqual(self.complete()['result'], 'committed')
        self.assertEqual(self.git('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').decode().strip(), 'handoff.md')


class PushTests(unittest.TestCase):
    """Authorized constants are patched only inside these synthetic fixtures.

    No CLI flag/config can override the compiled production URL/root guard.
    All transport is to a temporary local bare repository, never the internet.
    """
    setUpFixture = SyncTests.setUp
    git = SyncTests.git
    write_policy = SyncTests.write_policy
    begin = SyncTests.begin
    complete = SyncTests.complete
    change = SyncTests.change

    def setUp(self):
        self.setUpFixture()
        self.git('branch', '-m', 'codex/research-setup')
        self.remote = self.root / 'fixture-remote.git'
        subprocess.check_call(['git', 'init', '--bare', '-q', str(self.remote)])
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('push', '-q', 'origin', 'HEAD:refs/heads/codex/research-setup')
        self.policy['push'] = {'enabled': True, 'url': str(self.remote), 'branch': 'codex/research-setup'}
        self.write_policy()
        self.sync = Sync(self.root)
        for key, value in [('AUTHORIZED_ROOT', self.root), ('AUTHORIZED_URL', str(self.remote))]:
            patcher = mock.patch('research_sync.' + key, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.original_remote = self.remote_sha()

    def remote_sha(self):
        return subprocess.check_output(['git', '--git-dir', str(self.remote), 'rev-parse', 'refs/heads/codex/research-setup']).decode().strip()

    def retry(self):
        with self.sync.locked():
            return self.sync.push_task('test')

    def test_finish_push_verified_and_duplicate_no_commit(self):
        self.begin()
        self.change()
        result = self.complete()
        self.assertEqual(result['result'], 'pushed')
        self.assertEqual(result['push_status'], 'verified')
        self.assertEqual(result['commit'], self.remote_sha())
        self.assertEqual(self.git('rev-parse', 'refs/remotes/origin/codex/research-setup').decode().strip(), result['commit'])
        self.assertEqual(self.git('diff', 'HEAD', '--name-only'), b'')
        self.assertEqual(self.retry()['result'], 'pushed')
        with self.sync.locked():
            self.assertTrue(self.sync.finish('test')['duplicate'])
        self.assertEqual(self.git('rev-list', '--count', 'HEAD').strip(), b'2')

    def test_handoff_only_task_pushes(self):
        self.begin(paths=())
        result = self.complete()
        self.assertEqual(result['result'], 'pushed')
        self.assertEqual(result['commit'], self.remote_sha())

    def test_failure_recorded_retry_without_new_commit_and_begin_blocked(self):
        self.begin()
        self.change()
        original = self.sync.git
        def failing(*args, **kwargs):
            if args[0] == 'push':
                raise Refused('synthetic_push_failure')
            return original(*args, **kwargs)
        with mock.patch.object(self.sync, 'git', side_effect=failing):
            result = self.complete()
        self.assertEqual(result['result'], 'push_failed')
        self.assertEqual(self.remote_sha(), self.original_remote)
        self.assertIn('synthetic_push_failure', (self.root / 'handoff.md').read_text(encoding='utf-8'))
        with self.sync.locked(), self.assertRaisesRegex(Refused, 'pending_task_retry_push'):
            self.sync.begin('next', 'codex')
        self.assertEqual(self.retry()['result'], 'pushed')
        self.assertEqual(self.git('rev-list', '--count', 'HEAD').strip(), b'2')
        self.assertNotIn('synthetic_push_failure', (self.root / 'handoff.md').read_text(encoding='utf-8'))

    def test_remote_mismatch_prevents_unpublished_ancestor_upload(self):
        self.change('b.md')
        self.git('add', '--', 'b.md')
        self.git('commit', '-qm', 'unreviewed ancestor')
        self.begin()
        self.change()
        result = self.complete()
        self.assertEqual(result['push_error'], 'push_remote_not_task_baseline')
        self.assertEqual(self.remote_sha(), self.original_remote)

    def test_changed_head_refuses_retry(self):
        self.begin()
        self.change()
        with mock.patch.object(self.sync, 'remote_head', side_effect=Refused('synthetic_offline')):
            self.complete()
        self.change('b.md')
        self.git('add', '--', 'b.md')
        self.git('commit', '-qm', 'other task')
        self.assertEqual(self.retry()['push_error'], 'push_head_or_branch_changed')
        self.assertEqual(self.remote_sha(), self.original_remote)

    def test_unsafe_destination_settings_fail_before_transport(self):
        mutations = [('remote.origin.pushurl', str(self.remote)),
                     ('url.https://evil.invalid/.insteadOf', str(self.remote)),
                     ('url.https://evil.invalid/.pushInsteadOf', str(self.remote)),
                     ('remote.origin.push', 'HEAD:refs/heads/other')]
        with self.sync.locked():
            for key, value in mutations:
                self.git('config', '--add', key, value)
                with self.subTest(key=key), self.assertRaises(Refused):
                    self.sync.destination()
                self.git('config', '--unset-all', key)
            self.git('remote', 'add', 'other', str(self.remote))
            with self.assertRaisesRegex(Refused, 'unexpected_remote_set'):
                self.sync.destination()
            self.git('remote', 'remove', 'other')
            self.git('config', '--add', 'remote.origin.url', str(self.remote))
            with self.assertRaisesRegex(Refused, 'unexpected_origin_url'):
                self.sync.destination()

    def test_policy_cannot_choose_different_destination(self):
        self.sync.policy['push']['url'] = 'https://evil.invalid/other.git'
        with self.sync.locked(), self.assertRaisesRegex(Refused, 'destination_not_authorized'):
            self.sync.destination()

    def test_post_push_verification_failure_is_retryable_without_resend(self):
        self.begin()
        self.change()
        original = self.sync.remote_head
        calls = 0
        def flaky(url, ref):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise Refused('synthetic_verification_offline')
            return original(url, ref)
        with mock.patch.object(self.sync, 'remote_head', side_effect=flaky):
            result = self.complete()
        self.assertEqual(result['push_status'], 'failed')
        self.assertEqual(result['commit'], self.remote_sha())
        original_git = self.sync.git
        def no_second_push(*args, **kwargs):
            self.assertNotEqual(args[0], 'push')
            return original_git(*args, **kwargs)
        with mock.patch.object(self.sync, 'git', side_effect=no_second_push):
            self.assertEqual(self.retry()['push_status'], 'verified')
        self.assertEqual(self.git('rev-list', '--count', 'HEAD').strip(), b'2')


if __name__ == '__main__':
    unittest.main(verbosity=2)
