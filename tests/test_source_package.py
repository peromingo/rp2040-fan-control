"""Build correspondence and tamper rejection without any hardware access."""
import os
from pathlib import Path
import tempfile
import unittest
from tools.build_integration_plg import build, collect_files, payload_bytes, render_plg, verify, APP

WHEEL = os.environ.get('RP2040_TEST_WHEEL')

@unittest.skipUnless(WHEEL, 'Set RP2040_TEST_WHEEL to the pinned pyserial wheel')
class SourcePackageTests(unittest.TestCase):
    def test_two_builds_are_identical_and_verify_against_source(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first, second = build(a, WHEEL), build(b, WHEEL)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertGreater(verify(first, WHEEL), 0)

    def test_changed_payload_is_rejected_even_with_valid_embedded_hash(self):
        files = collect_files(WHEEL)
        name = APP + 'fan_control/fan_controller.py'
        data, mode = files[name]
        files[name] = (data + b'\n# simulated tampering\n', mode)
        forged, _ = render_plg(payload_bytes(files))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'forged.plg'
            p.write_bytes(forged)
            with self.assertRaisesRegex(ValueError, 'payload mismatch'):
                verify(p, WHEEL)

    def test_changed_installer_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = build(td, WHEEL)
            p.write_bytes(p.read_bytes().replace(b'set -eu', b'set -eu\n# unexpected installer edit', 1))
            with self.assertRaisesRegex(ValueError, 'templates'):
                verify(p, WHEEL)

    def test_wrong_dependency_wheel_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'wrong.whl'
            p.write_bytes(b'not the pinned dependency')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                collect_files(p)
