import importlib.util
from pathlib import Path
import unittest

EXAMPLE = Path(__file__).parents[1] / "src" / "unraid" / "fan_control" / "site_config.example.py"

class ExampleConfigTests(unittest.TestCase):
    def test_example_config_contains_placeholders_and_validation(self):
        spec = importlib.util.spec_from_file_location("site_config_example", EXAMPLE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(module.FAN1_DISKS)
        self.assertTrue(module.FAN2_DISKS)
        with self.assertRaises(RuntimeError):
            module.validate_disk_config()

if __name__ == "__main__":
    unittest.main()
