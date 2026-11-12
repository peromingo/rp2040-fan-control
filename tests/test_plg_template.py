"""Unit tests for release-manifest rendering; no .plg is emitted during tests."""
import unittest
import xml.etree.ElementTree as ET

from tools.render_unraid_plg import render_plg

GOOD = {
    "version": "0.6.0-dev.1",
    "plugin_url": "https://github.com/sergio-peromingo/rp2040-sata-hat/releases/download/v0.6.0-dev.1/rp2040-fan-control.plg",
    "payload_url": "https://github.com/sergio-peromingo/rp2040-sata-hat/releases/download/v0.6.0-dev.1/rp2040-fan-control-0.6.0-dev.1-payload.tar.gz",
    "payload_sha256": "a" * 64,
    "support_url": "https://github.com/sergio-peromingo/rp2040-sata-hat/issues",
}


class PlgTemplateTests(unittest.TestCase):
    def render(self, **overrides):
        values = dict(GOOD)
        values.update(overrides)
        return render_plg(**values)

    def test_renders_well_formed_xml_without_placeholders(self):
        rendered = self.render()
        ET.fromstring(rendered)
        self.assertNotRegex(rendered, r"__[A-Z][A-Z0-9_]*__")
        self.assertIn("a" * 64, rendered)

    def test_rejects_http_urls(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            self.render(payload_url="http://github.com/sergio-peromingo/rp2040-sata-hat/payload.tar.gz")

    def test_rejects_invalid_checksum(self):
        with self.assertRaisesRegex(ValueError, "64 hexadecimal"):
            self.render(payload_sha256="not-a-hash")

    def test_rejects_bad_version(self):
        with self.assertRaisesRegex(ValueError, "SemVer-like"):
            self.render(version="latest")

    def test_rejects_embedded_url_credentials(self):
        with self.assertRaisesRegex(ValueError, "credentials"):
            self.render(plugin_url="https://user:pass@github.com/sergio-peromingo/rp2040-sata-hat/plugin.plg")

    def test_rejects_reserved_placeholder_domains(self):
        with self.assertRaisesRegex(ValueError, "placeholder hostname"):
            self.render(payload_url="https://downloads.example.com/payload.tar.gz")


if __name__ == "__main__":
    unittest.main()
