import os
import tempfile
import unittest
from pathlib import Path

from fan_control.instance_lock import acquire_instance_lock


class InstanceLockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="rp2040-lock-")
        self.path = Path(self.tmp.name) / "daemon.lock"

    def tearDown(self):
        self.tmp.cleanup()

    def test_second_instance_does_not_truncate_locked_file(self):
        first = acquire_instance_lock(str(self.path))
        self.assertIsNotNone(first)
        original = self.path.read_text(encoding="ascii")

        second = acquire_instance_lock(str(self.path))
        self.assertIsNone(second)
        self.assertEqual(self.path.read_text(encoding="ascii"), original)

        first.close()

    def test_lock_can_be_acquired_after_previous_holder_closes(self):
        first = acquire_instance_lock(str(self.path))
        self.assertIsNotNone(first)
        first.close()

        second = acquire_instance_lock(str(self.path))
        self.assertIsNotNone(second)
        self.assertEqual(self.path.read_text(encoding="ascii"), "%d\n" % os.getpid())
        second.close()

    def test_rejects_group_or_world_writable_lock_file(self):
        self.path.write_text("stale\n", encoding="ascii")
        self.path.chmod(0o666)
        with self.assertRaises(OSError):
            acquire_instance_lock(str(self.path))
        self.assertEqual(self.path.read_text(encoding="ascii"), "stale\n")


if __name__ == "__main__":
    unittest.main()
