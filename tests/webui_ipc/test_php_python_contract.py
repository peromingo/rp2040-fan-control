"""Contract test: PHP publishes a command Python RuntimeIPC can consume."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from fan_control.ipc import RuntimeIPC


class PHPPythonContractTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("php"), "PHP CLI is not installed")
    def test_php_request_is_accepted_by_python_ipc(self):
        helper = Path(__file__).with_name("php_publish_contract.php")
        with tempfile.TemporaryDirectory(prefix="rp2040-php-contract-") as tmp:
            proc = subprocess.run(
                ["php", str(helper), tmp, "SILENT", "req_contract_123"],
                text=True, capture_output=True, timeout=5,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            ipc = RuntimeIPC(tmp)
            request = ipc.take_mode_request()
            self.assertEqual(request, {
                "request_id": "req_contract_123",
                "action": "set_mode",
                "mode": "SILENT",
            })
            self.assertFalse(ipc.command_path.exists())


if __name__ == "__main__":
    unittest.main()
