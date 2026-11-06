"""Regression tests for integrated configuration, control and direct PHP safety."""
import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fan_control.configuration import validate_payload, save_configuration
from fan_control.fan_controller import FanController
from fan_control.ipc import RuntimeIPC, finalize_mode_request
from fan_control.serial_manager import SerialManager
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]

class IntegratedFeatureTests(unittest.TestCase):
    def payload(self):
        return {'schema_version': 1, 'fans': {
            'fan1': {'disks': [{'model': 'EXAMPLE_MODEL', 'serial': 'EXAMPLE_SERIAL'}], 'use_cpu': False},
            'fan2': {'disks': [], 'use_cpu': True}}}

    def test_configuration_roundtrip_and_exclusive_disk_assignment(self):
        data = self.payload()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'config.json'
            save_configuration(data, path)
            self.assertEqual(json.loads(path.read_text()), validate_payload(data))
            invalid = copy.deepcopy(data)
            invalid['fans']['fan2']['disks'] = invalid['fans']['fan1']['disks']
            with self.assertRaises(ValueError):
                save_configuration(invalid, path)
            self.assertEqual(json.loads(path.read_text()), validate_payload(data))

    def test_missing_all_thermal_sources_is_rejected_in_config(self):
        data = self.payload()
        data['fans']['fan2']['use_cpu'] = False
        with self.assertRaises(ValueError):
            validate_payload(data)

    def test_mode_failure_rolls_back_and_retries_result_without_new_request(self):
        with tempfile.TemporaryDirectory() as td:
            ipc = RuntimeIPC(td)
            request = {'request_id': 'req_source_rc_123', 'mode': 'SILENT'}
            with patch.object(ipc, '_atomic_json', side_effect=OSError('simulated disk error')):
                mode = finalize_mode_request(ipc, request, 'AUTO', 'SILENT', False, True)
            self.assertEqual(mode, 'AUTO')
            self.assertFalse(ipc.result_path.exists())
            self.assertTrue(ipc.retry_pending_result())
            result = json.loads(ipc.result_path.read_text())
            self.assertFalse(result['ok'])
            self.assertEqual(result['request_id'], request['request_id'])

    def test_thermal_alert_and_source_loss_bypass_ramp(self):
        control = FanController([(30, 30), (50, 100)], 50, 45, 40, 10, 10, 1)
        self.assertEqual(control.smooth_control_output(30, 100, None), 100)
        self.assertEqual(control.smooth_control_output(30, 100, 55), 100)
        self.assertEqual(control.smooth_control_output(70, 40, 35), 60)

    def test_short_serial_write_enters_failsafe(self):
        manager = SerialManager(115200, 5, 15, 5, 30)
        port = Mock()
        port.write.return_value = 1
        manager.port = port
        self.assertFalse(manager.send('TEST@100,100'))
        self.assertTrue(manager.fail_safe)
        port.close.assert_called_once()

    def test_multiple_serial_devices_require_explicit_selection(self):
        manager = SerialManager(115200, 5, 15, 5, 30)
        with patch.dict('os.environ', {}, clear=True), patch('fan_control.serial_manager.glob.glob', side_effect=[[], ['/dev/ttyACM0', '/dev/ttyACM1']]):
            self.assertIsNone(manager.find_port())

    @unittest.skipUnless(shutil.which('php'), 'PHP CLI is not installed')
    def test_direct_php_post_is_rejected_before_privileged_actions(self):
        page = ROOT / 'plugin/src/usr/local/emhttp/plugins/rp2040-fan-control/pages/index.php'
        code = '$_SERVER["REQUEST_METHOD"]="POST"; $_SERVER["SCRIPT_FILENAME"]=$argv[1]; include $argv[1];'
        result = subprocess.run(['php', '-r', code, str(page)], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('página de Unraid', result.stdout)
        self.assertNotIn('<form', result.stdout)

if __name__ == '__main__':
    unittest.main()
