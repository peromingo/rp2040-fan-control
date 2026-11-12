import json
import tempfile
import time
import unittest
from pathlib import Path

from fan_control.ipc import RuntimeIPC


class RuntimeIPCTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ipc = RuntimeIPC(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_status_is_valid_json_and_replaced_atomically(self):
        self.assertTrue(self.ipc.publish_status({"daemon": {"state": "running"}}))
        value = json.loads(self.ipc.status_path.read_text())
        self.assertEqual(value["schema_version"], 1)
        self.assertEqual(value["daemon"]["state"], "running")
        self.assertIn("timestamp", value)

    @unittest.skipUnless(hasattr(__import__("os"), "stat"), "POSIX mode bits unavailable")
    def test_status_file_is_not_world_writable(self):
        import os
        self.assertTrue(self.ipc.publish_status({"daemon": {"state": "running"}}))
        mode = os.stat(self.ipc.status_path).st_mode
        self.assertEqual(mode & 0o777, 0o640)
        self.assertEqual(os.stat(self.ipc.runtime_dir).st_mode & 0o002, 0)

    def test_existing_runtime_directory_permissions_are_not_silently_changed(self):
        import os
        os.chmod(self.ipc.runtime_dir, 0o700)
        self.ipc.ensure_runtime_dir()
        self.assertEqual(os.stat(self.ipc.runtime_dir).st_mode & 0o777, 0o700)

    def test_runtime_directory_rejects_group_writable_permissions(self):
        import os
        os.chmod(self.ipc.runtime_dir, 0o770)
        with self.assertRaises(PermissionError):
            self.ipc.ensure_runtime_dir()
        self.assertEqual(os.stat(self.ipc.runtime_dir).st_mode & 0o777, 0o770,
                         "IPC must reject insecure permissions without silently changing them")

    def test_runtime_directory_rejects_symlink(self):
        import os
        with tempfile.TemporaryDirectory() as parent:
            target = Path(parent) / "real-runtime"
            target.mkdir(mode=0o700)
            link = Path(parent) / "runtime-link"
            link.symlink_to(target, target_is_directory=True)
            ipc = RuntimeIPC(link)
            with self.assertRaises(PermissionError):
                ipc.ensure_runtime_dir()

    def test_new_runtime_directory_is_created_without_group_or_world_write(self):
        import os
        with tempfile.TemporaryDirectory() as parent:
            runtime = Path(parent) / "new-runtime"
            ipc = RuntimeIPC(runtime)
            ipc.ensure_runtime_dir()
            self.assertTrue(runtime.is_dir())
            self.assertEqual(os.stat(runtime).st_mode & 0o022, 0)

    def test_valid_mode_request_is_consumed(self):
        request = {"schema_version": 1, "request_id": "req_12345678",
                   "created_at": time.time(), "action": "set_mode", "mode": "TURBO"}
        self.ipc.command_path.write_text(json.dumps(request))
        got = self.ipc.take_mode_request()
        self.assertEqual(got, {"request_id": "req_12345678", "action": "set_mode", "mode": "TURBO"})
        self.assertFalse(self.ipc.command_path.exists())

    def test_invalid_mode_is_rejected_and_acknowledged(self):
        request = {"schema_version": 1, "request_id": "req_12345678",
                   "created_at": time.time(), "action": "set_mode", "mode": "MAX"}
        self.ipc.command_path.write_text(json.dumps(request))
        self.assertIsNone(self.ipc.take_mode_request())
        result = json.loads(self.ipc.result_path.read_text())
        self.assertFalse(result["ok"])
        self.assertEqual(result["request_id"], "req_12345678")

    def test_replayed_request_id_is_rejected(self):
        request = {"schema_version": 1, "request_id": "req_12345678",
                   "created_at": time.time(), "action": "set_mode", "mode": "AUTO"}
        self.ipc.command_path.write_text(json.dumps(request))
        self.assertIsNotNone(self.ipc.take_mode_request())
        # Reuse the same ID after a different request to verify the replay cache.
        other = {"schema_version": 1, "request_id": "req_87654321",
                 "created_at": time.time(), "action": "set_mode", "mode": "SILENT"}
        self.ipc.command_path.write_text(json.dumps(other))
        self.assertIsNotNone(self.ipc.take_mode_request())
        self.ipc.command_path.write_text(json.dumps(request))
        self.assertIsNone(self.ipc.take_mode_request())

    def test_expired_request_is_rejected(self):
        request = {"schema_version": 1, "request_id": "req_12345678",
                   "created_at": time.time() - 60, "action": "set_mode", "mode": "AUTO"}
        self.ipc.command_path.write_text(json.dumps(request))
        self.assertIsNone(self.ipc.take_mode_request())
        self.assertFalse(json.loads(self.ipc.result_path.read_text())["ok"])

    def test_non_finite_request_timestamps_are_rejected(self):
        for invalid_timestamp in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with self.subTest(created_at=invalid_timestamp):
                request = {
                    "schema_version": 1,
                    "request_id": "req_12345678",
                    "created_at": invalid_timestamp,
                    "action": "set_mode",
                    "mode": "AUTO",
                }
    
                self.ipc.command_path.write_text(json.dumps(request))
    
                self.assertIsNone(self.ipc.take_mode_request())
    
                result = json.loads(self.ipc.result_path.read_text())
                self.assertFalse(result["ok"])
    
    def test_unknown_action_is_rejected(self):
        request = {"schema_version": 1, "request_id": "req_12345678",
                   "created_at": time.time(), "action": "shell", "mode": "AUTO"}
        self.ipc.command_path.write_text(json.dumps(request))
        self.assertIsNone(self.ipc.take_mode_request())

    def test_oversized_request_is_rejected(self):
        self.ipc.command_path.write_text(" " * 4097)
        self.assertIsNone(self.ipc.take_mode_request())
        result = json.loads(self.ipc.result_path.read_text())
        self.assertFalse(result["ok"])

    def test_future_request_is_rejected(self):
        request = {"schema_version": 1, "request_id": "req_12345678",
                   "created_at": time.time() + 60, "action": "set_mode", "mode": "AUTO"}
        self.ipc.command_path.write_text(json.dumps(request))
        self.assertIsNone(self.ipc.take_mode_request())
        result = json.loads(self.ipc.result_path.read_text())
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
