"""Update metadata must preserve the complete reviewed plugin byte for byte."""
import hashlib
import json
from pathlib import Path
import tempfile
import re
import xml.etree.ElementTree as ET
import unittest
from tools.prepare_update_manifest import ADDITION, LEGACY_NAME, PLUGIN_ID, PLG_NAME, PREVIEW_URL, metadata_bytes, prepare, verify

class UpdateManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / 'reviewed.plg'
        self.data = b'<?xml version="1.0"?>\n<PLUGIN name="RP2040 SATA HAT Fan Control" version="0.8.0-source-rc2"><FILE Run="/bin/bash"><INLINE><![CDATA[echo "synthetic fixture"\n]]></INLINE></FILE></PLUGIN>\n'
        self.source.write_bytes(self.data)
        self.hash = hashlib.sha256(self.data).hexdigest()
        self.output = self.root / 'preview'

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_name_and_plugin_url_attributes_change(self):
        path = prepare(self.source, self.hash, self.output)
        self.assertEqual(path.read_bytes().replace(ADDITION, b'', 1).replace((' name="' + PLUGIN_ID + '"').encode(), (' name="' + LEGACY_NAME + '"').encode(), 1), self.data)
        self.assertEqual(verify(self.source, self.hash, self.output), '0.8.0-source-rc2')
        self.assertIn(PREVIEW_URL.encode(), path.read_bytes())

    def test_internal_name_is_safe_for_unraid_id_selectors(self):
        path = prepare(self.source, self.hash, self.output)
        root = ET.fromstring(path.read_bytes())
        self.assertEqual(root.attrib['name'], PLUGIN_ID)
        self.assertRegex('sid-' + root.attrib['name'], r'^[A-Za-z][A-Za-z0-9_-]*$')

    def test_rename_is_limited_to_opening_tag(self):
        data = self.data.replace(b'synthetic fixture', LEGACY_NAME.encode())
        self.source.write_bytes(data)
        result, _ = metadata_bytes(self.source, hashlib.sha256(data).hexdigest())
        self.assertIn(b'echo "' + LEGACY_NAME.encode() + b'"', result)
        self.assertEqual(result[result.index(b'<FILE'):], data[data.index(b'<FILE'):])

    def test_rejects_unexpected_plugin_identity(self):
        data = self.data.replace(LEGACY_NAME.encode(), b'other-plugin', 1)
        self.source.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'identity'):
            metadata_bytes(self.source, hashlib.sha256(data).hexdigest())

    def test_rejects_unreviewed_input_hash(self):
        with self.assertRaisesRegex(ValueError, 'checksum'):
            prepare(self.source, '0' * 64, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_source_with_an_existing_update_channel(self):
        data = self.data.replace(b'<PLUGIN ', b'<PLUGIN pluginURL="https://outside.invalid/plugin.plg" ', 1)
        self.source.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'already has'):
            metadata_bytes(self.source, hashlib.sha256(data).hexdigest())

    def test_rejects_changed_plugin_code(self):
        path = prepare(self.source, self.hash, self.output)
        path.write_bytes(path.read_bytes().replace(b'synthetic fixture', b'unexpected code'))
        with self.assertRaisesRegex(ValueError, 'beyond allowed'):
            verify(self.source, self.hash, self.output)

    def test_rejects_changed_checksum_or_record(self):
        prepare(self.source, self.hash, self.output)
        sidecar = self.output / (PLG_NAME + '.sha256')
        sidecar.write_text('0' * 64 + '  ' + PLG_NAME + '\n')
        with self.assertRaisesRegex(ValueError, 'sidecar'):
            verify(self.source, self.hash, self.output)
        prepare(self.source, self.hash, self.output)
        record = self.output / 'manifest.json'
        data = json.loads(record.read_text());data['source_package_sha256'] = '0' * 64
        record.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'provenance'):
            verify(self.source, self.hash, self.output)

    def test_generation_is_deterministic(self):
        a = prepare(self.source, self.hash, self.output)
        b = prepare(self.source, self.hash, self.root / 'second')
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_refuses_symlinked_output(self):
        self.output.mkdir()
        (self.output / PLG_NAME).symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, 'symlinked'):
            prepare(self.source, self.hash, self.output)
        self.assertEqual(self.source.read_bytes(), self.data)
