import json
import tempfile
import unittest
from pathlib import Path

from fan_control.ipc import RuntimeIPC, acknowledge_transmitted_mode


class TransmissionAckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ipc = RuntimeIPC(self.tmp.name)
        self.request = {"request_id": "req_abcdefgh", "action": "set_mode", "mode": "TURBO"}

    def tearDown(self):
        self.tmp.cleanup()

    def result(self):
        return json.loads(self.ipc.result_path.read_text(encoding="utf-8"))

    def test_success_requires_serial_write_and_no_failsafe(self):
        acknowledge_transmitted_mode(self.ipc, self.request, "TURBO", True, False)
        result = self.result()
        self.assertTrue(result["ok"])
        self.assertEqual(result["applied_mode"], "TURBO")
        self.assertIn("no devuelve ACK", result["message"])

    def test_failed_serial_write_is_not_acknowledged_as_success(self):
        acknowledge_transmitted_mode(self.ipc, self.request, "TURBO", False, True)
        result = self.result()
        self.assertFalse(result["ok"])
        self.assertNotIn("applied_mode", result)
        self.assertIn("fail-safe", result["message"])

    def test_failsafe_blocks_success_even_if_send_reports_true(self):
        acknowledge_transmitted_mode(self.ipc, self.request, "AUTO", True, True)
        self.assertFalse(self.result()["ok"])


if __name__ == "__main__":
    unittest.main()
