"""Isolated one-cycle simulation of PHP -> IPC -> daemon -> serial -> result.

This deliberately uses a fake serial manager and temporary runtime directory; it
never imports or starts the production daemon and never opens a serial device.
"""
import json
import tempfile
import time
import unittest

from fan_control.ipc import RuntimeIPC, acknowledge_transmitted_mode


class FakeSerialManager:
    def __init__(self, send_result=True, fail_safe=False):
        self.send_result = send_result
        self.fail_safe = fail_safe
        self.packets = []

    def send(self, packet):
        self.packets.append(packet)
        return self.send_result


class ModeCycleSimulationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="rp2040-cycle-sim-")
        self.ipc = RuntimeIPC(self.tmp.name)
        self.request_id = "req_cycle_123456"
        self.ipc.command_path.write_text(json.dumps({
            "schema_version": 1,
            "request_id": self.request_id,
            "created_at": time.time(),
            "action": "set_mode",
            "mode": "SILENT",
        }), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_one_cycle(self, serial):
        request = self.ipc.take_mode_request()
        self.assertIsNotNone(request)
        current_mode = request["mode"]
        packet = "TEST FAN COMMAND!MODE|%s@100,100\\n" % current_mode
        tx_ok = serial.send(packet)
        acknowledge_transmitted_mode(
            self.ipc, request, current_mode, tx_ok, serial.fail_safe
        )
        result = json.loads(self.ipc.result_path.read_text(encoding="utf-8"))
        return current_mode, result

    def test_cycle_reports_success_only_after_fake_serial_send(self):
        serial = FakeSerialManager(send_result=True, fail_safe=False)
        mode, result = self.run_one_cycle(serial)
        self.assertEqual(mode, "SILENT")
        self.assertEqual(len(serial.packets), 1)
        self.assertIn("!MODE|SILENT", serial.packets[0])
        self.assertTrue(result["ok"])
        self.assertEqual(result["request_id"], self.request_id)

    def test_cycle_reports_failure_when_fake_serial_send_fails(self):
        serial = FakeSerialManager(send_result=False, fail_safe=True)
        mode, result = self.run_one_cycle(serial)
        self.assertEqual(mode, "SILENT")
        self.assertEqual(len(serial.packets), 1)
        self.assertFalse(result["ok"])
        self.assertNotIn("applied_mode", result)

    def test_cycle_reports_failure_in_failsafe_even_if_send_returns_true(self):
        serial = FakeSerialManager(send_result=True, fail_safe=True)
        _, result = self.run_one_cycle(serial)
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
