"""Concurrent publication test for the PHP panel's link()-based IPC."""
import json
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


class PHPAtomicPublishRaceTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("php"), "PHP CLI is not installed")
    def test_only_one_concurrent_request_can_publish_command(self):
        worker = Path(__file__).with_name("php_publish_worker.php")
        with tempfile.TemporaryDirectory(prefix="rp2040-php-race-") as tmp:
            root = Path(tmp)
            release = root / "release"
            ready_a = root / "ready-a"
            ready_b = root / "ready-b"
            command = root / "command.json"

            a = subprocess.Popen(
                ["php", str(worker), str(root), "request_A", str(ready_a), str(release)],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            b = subprocess.Popen(
                ["php", str(worker), str(root), "request_B", str(ready_b), str(release)],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            processes = [a, b]
            try:
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline and not (ready_a.exists() and ready_b.exists()):
                    if any(p.poll() is not None for p in processes):
                        break
                    time.sleep(0.01)
                self.assertTrue(ready_a.exists(), "worker A did not reach the race barrier")
                self.assertTrue(ready_b.exists(), "worker B did not reach the race barrier")
                release.touch()
                results = [p.communicate(timeout=5) for p in processes]
                codes = [p.returncode for p in processes]
                self.assertEqual(sorted(codes), [0, 1], msg=repr(results))
                self.assertTrue(command.is_file(), "no command was published")
                payload = json.loads(command.read_text(encoding="utf-8"))
                self.assertIn(payload["request_id"], {"request_A", "request_B"})
                self.assertIn(payload["mode"], {"AUTO", "TURBO"})
            finally:
                release.touch(exist_ok=True)
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=2)


if __name__ == "__main__":
    unittest.main()
