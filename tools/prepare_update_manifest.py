#!/usr/bin/env python3
"""Add preview-update metadata to an already verified PLG without changing its code."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

PLG_NAME = 'rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg'
PREVIEW_URL = ('https://raw.githubusercontent.com/peromingo/rp2040-fan-control/'
               'source-tree-review/plugin/channels/preview/' + PLG_NAME)
ADDITION = (' pluginURL="' + PREVIEW_URL + '"').encode('ascii')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def checked_source(path, expected_sha256):
    if not re.fullmatch(r'[a-f0-9]{64}', expected_sha256):
        raise ValueError('Expected source SHA-256 must contain 64 lowercase hex digits')
    data = Path(path).read_bytes()
    if sha256(data) != expected_sha256:
        raise ValueError('Reviewed source PLG checksum mismatch')
    root = ET.fromstring(data)
    if root.tag != 'PLUGIN' or not root.findall('FILE'):
        raise ValueError('Source is not an executable Unraid plugin definition')
    if 'pluginURL' in root.attrib:
        raise ValueError('Source already has pluginURL; use the reviewed source-built artifact')
    if not re.fullmatch(r'[A-Za-z0-9._+-]+', root.attrib.get('version', '')):
        raise ValueError('Invalid plugin version')
    return data, root


def metadata_bytes(source, expected_sha256):
    data, root = checked_source(source, expected_sha256)
    match = re.search(br'<PLUGIN\b[^>]*>', data)
    if not match or match[0].endswith(b'/>'):
        raise ValueError('Cannot locate plugin opening tag')
    result = data[:match.end()-1] + ADDITION + data[match.end()-1:]
    # The only allowed difference is the one attribute on the opening tag.
    if result.replace(ADDITION, b'', 1) != data:
        raise ValueError('Plugin code changed while adding metadata')
    parsed = ET.fromstring(result)
    attrs = dict(parsed.attrib)
    if attrs.pop('pluginURL', None) != PREVIEW_URL or attrs != root.attrib:
        raise ValueError('Unexpected plugin attributes')
    return result, root.attrib['version']


def record_for(source_hash, data, version):
    return {'schema_version': 1, 'channel': 'preview', 'version': version,
            'plugin_url': PREVIEW_URL, 'filename': PLG_NAME,
            'source_package_sha256': source_hash, 'manifest_sha256': sha256(data)}


def prepare(source, expected_sha256, output):
    data, version = metadata_bytes(source, expected_sha256)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    targets = [output / PLG_NAME, output / (PLG_NAME + '.sha256'), output / 'manifest.json']
    if any(p.is_symlink() for p in targets):
        raise ValueError('Refusing symlinked output files')
    targets[0].write_bytes(data)
    targets[1].write_text(sha256(data) + '  ' + PLG_NAME + '\n')
    targets[2].write_text(json.dumps(record_for(expected_sha256, data, version), sort_keys=True, indent=2) + '\n')
    verify(source, expected_sha256, output)
    return targets[0]


def verify(source, expected_sha256, output):
    expected, version = metadata_bytes(source, expected_sha256)
    output = Path(output)
    actual = (output / PLG_NAME).read_bytes()
    if actual != expected:
        raise ValueError('Preview definition differs from the reviewed plugin beyond pluginURL')
    if (output / (PLG_NAME + '.sha256')).read_text() != sha256(actual) + '  ' + PLG_NAME + '\n':
        raise ValueError('Preview checksum sidecar mismatch')
    record = json.loads((output / 'manifest.json').read_text())
    if record != record_for(expected_sha256, expected, version):
        raise ValueError('Preview provenance record mismatch')
    return version


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--expected-sha256', required=True)
    p.add_argument('--verify', action='store_true')
    args = p.parse_args()
    if args.verify:
        print('Verified preview metadata for ' + verify(args.source, args.expected_sha256, args.output))
    else:
        path = prepare(args.source, args.expected_sha256, args.output)
        print(str(path) + '\nSHA-256: ' + sha256(path.read_bytes()))

if __name__ == '__main__':
    main()
