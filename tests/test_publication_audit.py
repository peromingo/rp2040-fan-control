"""Tests for publication artifact privacy checks; no hardware access."""
import tempfile
import unittest
import tarfile
from pathlib import Path

from tools.audit_publication import audit_tar, audit_tree

ROOT = Path(__file__).resolve().parents[1]


class PublicationAuditTests(unittest.TestCase):
    def test_current_source_tree_passes_structural_audit(self):
        self.assertEqual([], audit_tree(ROOT))

    def test_local_disk_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for rel in (
                "LICENSE",
                "README.md",
                "src/unraid/fan_control/site_config.example.py",
                "docs/GITHUB-PUBLICATION.md",
                ".github/workflows/ci.yml",
            ):
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("example", encoding="utf-8")
            private = root / "src/unraid/fan_control/site_config_local.py"
            private.write_text("# local", encoding="utf-8")
            self.assertTrue(any("site_config_local.py" in issue for issue in audit_tree(root)))

    def test_compiled_python_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for rel in (
                "LICENSE",
                "README.md",
                "src/unraid/fan_control/site_config.example.py",
                "docs/GITHUB-PUBLICATION.md",
                ".github/workflows/ci.yml",
            ):
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("example", encoding="utf-8")
            cache = root / "src/unraid/__pycache__/daemon.pyc"
            cache.parent.mkdir(parents=True)
            cache.write_bytes(b"not real bytecode")
            self.assertTrue(audit_tree(root))

    def test_payload_rejects_private_config_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "payload.tar.gz"
            with tarfile.open(archive, "w:gz") as tf:
                private = Path(temp) / "site_config_local.py"
                private.write_text("# local", encoding="utf-8")
                tf.add(private, arcname="app/fan_control/site_config_local.py")
            self.assertTrue(any("site_config_local.py" in issue for issue in audit_tar(archive)))


if __name__ == "__main__":
    unittest.main()
