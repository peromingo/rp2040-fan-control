"""Exercise actual installer scripts in a private root, without hardware or services."""
import fcntl
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

from tools.build_integration_plg import build, source_version

WHEEL = os.environ.get('RP2040_TEST_WHEEL')


@unittest.skipUnless(WHEEL, 'Set RP2040_TEST_WHEEL to the pinned pyserial wheel')
class TransactionRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build_dir = tempfile.TemporaryDirectory(prefix='rp2040-rc3-build-')
        cls.work = Path(cls.build_dir.name).resolve()
        build(cls.work, WHEEL)

    @classmethod
    def tearDownClass(cls):
        cls.build_dir.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rp2040-transaction-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.root = self.home / 'root'
        self.shim = self.home / 'shim'
        self.shim.mkdir()
        for name, body in {'sudo': 'exit ${FAIL_AUTH:-0}', 'visudo': 'exit 0', 'sync': 'exit 0',
                           'pgrep': '[ "${SIM_ACTIVE:-0}" = 1 ] && exit 0\nexit 1', 'php': 'exit 0'}.items():
            self.script(name, '#!/bin/sh\n' + body + '\n')
        if sys.platform == 'darwin':
            self.script('base64', '#!/bin/sh\nshift\nexec /usr/bin/base64 -D -i "$1"\n')
        if not shutil.which('flock'):
            self.script('flock', '#!' + sys.executable + '\nimport fcntl,sys\n'
                        'try: fcntl.flock(int(sys.argv[-1]), fcntl.LOCK_EX|fcntl.LOCK_NB)\n'
                        'except BlockingIOError: sys.exit(1)\n')
        self.script('install', '''#!/bin/sh
for arg do last="$arg"; done
case "$last" in
 */pages/index.php)
  case "${PAGE_FAULT:-}" in
   fail) exit 1 ;;
   crash) kill -KILL "$PPID"; exit 1 ;;
  esac ;;
esac
exec /usr/bin/install "$@"
''')
        self.script('cp', '''#!/bin/sh
case "${FAIL_RESTORE:-0}:$2" in
 1:*.transaction/files/*) exit 1 ;;
esac
# The real installer runs as root. In this unprivileged fixture, allow copying
# over an owned read-only sudoers file, then let cp -p restore the source mode.
for arg do last="$arg"; done
if [ -f "$last" ] && [ ! -w "$last" ]; then chmod u+w "$last" || exit 1; fi
exec /bin/cp "$@"
''')
        (self.root / 'etc/sudoers.d').mkdir(parents=True)
        (self.root / 'usr/local/sbin').mkdir(parents=True)
        (self.root / 'etc/sudoers').write_text('#includedir /etc/sudoers.d\n')
        self.base = self.root / 'boot/config/plugins/rp2040-fan-control'
        (self.base / 'logs').mkdir(parents=True)
        (self.base / 'config.json').write_bytes(b'{"fixture":"preserve"}\n')
        (self.base / 'logs/test.log').write_bytes(b'fixture log\n')
        self.baseline = self.base / ('backup/webui-integration-source-' + source_version())
        self.transaction = Path(str(self.baseline) + '.transaction')
        self.wrapper = self.root / 'usr/local/sbin/rp2040-fan-control'
        self.env = dict(os.environ, RP2040_PLG_TEST_ROOT=str(self.root),
                        TMPDIR=str(self.home), PATH=str(self.shim) + ':' + os.environ['PATH'])

    def script(self, name, text):
        p = self.shim / name
        p.write_text(text)
        p.chmod(0o755)

    def run_block(self, block=0, **extra):
        return subprocess.run(['bash', str(self.work / f'candidate-block{block}.sh')],
                              env=dict(self.env, **extra), text=True, capture_output=True, timeout=120)

    def install_ok(self):
        r = self.run_block()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(self.transaction.exists())

    def snapshot(self, directory=None):
        directory = directory or self.root
        return {p.relative_to(directory).as_posix(): (p.read_bytes(), stat.S_IMODE(p.stat().st_mode))
                for p in directory.rglob('*') if p.is_file()
                and (directory != self.root or 'backup' not in p.relative_to(self.root).parts)}

    def preceding_runtime(self):
        self.install_ok()
        # A preceding runtime differs from the candidate's historic uninstall baseline.
        self.wrapper.write_text('#!/bin/sh\n[ "$1" = status ] && exit 1\nexit 0\n')
        self.wrapper.chmod(0o750)
        p = self.base / 'app/fan_control/version.py'
        p.write_text('__version__ = "preceding-fixture"\n')
        p.chmod(0o600)
        return self.snapshot()

    def test_repeat_install_failure_restores_immediate_state_and_keeps_uninstall_baseline(self):
        self.preceding_runtime()
        policy = self.root / 'etc/sudoers.d/rp2040-fan-control-webui'
        policy.chmod(0o600)
        policy.write_bytes(policy.read_bytes() + b'\n# preceding policy fixture\n')
        policy.chmod(0o440)
        previous = self.snapshot()
        baseline = self.snapshot(self.baseline)
        for fault in ({'PAGE_FAULT': 'fail'}, {'FAIL_AUTH': '1'}):
            with self.subTest(fault=fault):
                r = self.run_block(**fault)
                self.assertNotEqual(r.returncode, 0)
                self.assertEqual(self.snapshot(), previous)
                self.assertEqual(self.snapshot(self.baseline), baseline)
                self.assertFalse(self.transaction.exists())
                self.assertFalse(list((self.base / 'backup').rglob('recovery-pending')))
        # The original all-NEW baseline still removes the runtime on uninstall.
        r = self.run_block(1)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(self.wrapper.exists())
        self.assertEqual((self.base / 'config.json').read_bytes(), b'{"fixture":"preserve"}\n')
        self.assertEqual((self.base / 'logs/test.log').read_bytes(), b'fixture log\n')

    def test_first_install_failure_removes_new_runtime_and_example_config(self):
        previous = self.snapshot()
        r = self.run_block(PAGE_FAULT='fail')
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.snapshot(), previous)
        self.assertFalse(self.transaction.exists())

    def test_killed_install_is_recovered_before_any_new_install_or_uninstall(self):
        previous = self.preceding_runtime()
        r = self.run_block(PAGE_FAULT='crash')
        self.assertNotEqual(r.returncode, 0)
        journal = self.transaction / 'recovery-pending'
        self.assertTrue(journal.is_file(), r.stdout + r.stderr)
        interrupted = self.snapshot()
        r = self.run_block(SIM_ACTIVE='1')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('daemon activo', r.stderr)
        self.assertEqual(self.snapshot(), interrupted)
        self.assertTrue(journal.is_file(), r.stdout + r.stderr)
        r = self.run_block(1)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.snapshot(), interrupted)
        r = self.run_block()
        self.assertNotEqual(r.returncode, 0, 'Recovery must require a separate installation')
        self.assertIn('Transacción recuperada y verificada', r.stdout, r.stderr)
        self.assertEqual(self.snapshot(), previous)
        self.assertFalse(self.transaction.exists())
        self.install_ok()

    def test_failed_rollback_retains_journal_and_can_be_retried(self):
        previous = self.preceding_runtime()
        r = self.run_block(PAGE_FAULT='fail', FAIL_RESTORE='1')
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue((self.transaction / 'recovery-pending').is_file(), r.stdout + r.stderr)
        r = self.run_block()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Transacción recuperada y verificada', r.stdout, r.stderr)
        self.assertEqual(self.snapshot(), previous)
        self.assertFalse(self.transaction.exists())

    def test_shared_lock_blocks_both_lifecycle_operations_without_changes(self):
        previous = self.preceding_runtime()
        with (self.base / 'backup/.lifecycle.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for block in (0, 1):
                r = self.run_block(block)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn('otra operación', r.stderr)
                self.assertEqual(self.snapshot(), previous)
        self.install_ok()

    def test_another_candidates_pending_recovery_blocks_both_operations(self):
        previous = self.preceding_runtime()
        journal = self.base / 'backup/another-candidate/recovery-pending'
        journal.parent.mkdir()
        journal.write_text('recovery-v1\nstarted=2026-01-01T00:00:00Z\nsource=installer\n')
        for block in (0, 1):
            r = self.run_block(block)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('recuperación pendiente', r.stderr)
            self.assertEqual(self.snapshot(), previous)
            self.assertTrue(journal.is_file(), r.stdout + r.stderr)

    def test_killed_first_install_recovers_example_config_side_effect(self):
        previous = self.snapshot()
        r = self.run_block(PAGE_FAULT='crash')
        self.assertNotEqual(r.returncode, 0)
        journal = self.transaction / 'recovery-pending'
        self.assertIn('local-config-created=1', journal.read_text())
        self.assertTrue((self.base / 'app/fan_control/site_config_local.py').exists())
        r = self.run_block()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Transacción recuperada y verificada', r.stdout, r.stderr)
        self.assertEqual(self.snapshot(), previous)
        self.assertFalse(self.transaction.exists())

    def test_installed_license_texts_match_originals(self):
        from tools.build_integration_plg import ROOT
        self.install_ok()
        licenses = self.base / 'app/LICENSES'
        self.assertEqual((licenses / 'project-MIT.txt').read_bytes(), (ROOT / 'LICENSE').read_bytes())
        self.assertEqual((licenses / 'pyserial-3.5-BSD-3-Clause.txt').read_bytes(),
                         (ROOT / 'third_party/pyserial/LICENSE.txt').read_bytes())
