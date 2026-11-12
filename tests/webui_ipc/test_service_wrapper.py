"""Static safety checks for the Unraid service wrapper; never starts hardware."""
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugin" / "scripts" / "rp2040-fan-control"


class ServiceWrapperSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_disabled_without_explicit_enable_marker(self):
        self.assertIn('ENABLE_MARKER="$PLUGIN_DIR/ENABLE"', self.source)
        self.assertIn('[ -f "$ENABLE_MARKER" ]', self.source)

    def test_refuses_placeholder_disk_configuration(self):
        self.assertIn("grep -q 'REPLACE_WITH_'", self.source)

    def test_does_not_grant_world_write_permissions(self):
        self.assertIn('chmod 0750 "$RUNTIME_DIR"', self.source)
        import re
        self.assertNotRegex(self.source, r"(?m)^\s*chmod\s+0777\b")

    def test_existing_runtime_directory_is_checked_not_chmodded(self):
        self.assertIn("stat -c '%u'", self.source)
        self.assertIn("stat -c '%a'", self.source)
        create_branch = self.source.index('if [ ! -e "$RUNTIME_DIR" ]; then')
        chmod_line = self.source.index('chmod 0750 "$RUNTIME_DIR"')
        existing_owner_check = self.source.index("owner=\"$(stat -c '%u' \"$RUNTIME_DIR\"")
        self.assertLess(create_branch, chmod_line)
        self.assertLess(chmod_line, existing_owner_check)
        self.assertIn('el directorio IPC existente permite escritura global', self.source)

    def test_daemon_lock_uses_stable_runtime_path(self):
        self.assertIn('export RP2040_LOCK_FILE="$RUNTIME_DIR/daemon.lock"', self.source)
        self.assertNotIn('rp2040_fan_control.lock', self.source)

    def test_pid_file_is_written_with_private_permissions(self):
        umask_line = self.source.index("    umask 077")
        pid_write = self.source.index('printf \'%s\\n\' "$pid" > "$PID_FILE"')
        self.assertLess(umask_line, pid_write)

    def test_stop_checks_process_identity_before_signal(self):
        self.assertIn('is_our_pid "$pid"', self.source)
        self.assertIn('kill -TERM "$pid"', self.source)
        self.assertNotIn('kill -9', self.source)

    def test_requires_dependencies_before_start(self):
        self.assertIn("import serial", self.source)
        self.assertIn('PYTHONPATH="$APP_DIR/vendor:$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"', self.source)
        self.assertIn('command -v smartctl', self.source)
        self.assertIn('check_dependencies ||', self.source)

    def test_has_read_only_dependency_diagnostic_command(self):
        self.assertIn('check-deps) check_dependencies ;;', self.source)
        self.assertIn('python-path', self.source)
        self.assertIn('RP2040_PYTHON', self.source)
        self.assertIn('configure $PYTHON_CONFIG o RP2040_PYTHON', self.source)


if __name__ == "__main__":
    unittest.main()
