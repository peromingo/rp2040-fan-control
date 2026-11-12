#!/usr/bin/env python3
"""Build a self-contained review PLG directly from tracked runtime sources."""
from __future__ import annotations
import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PYSERIAL_LICENSE_SHA256 = 'f91cb9813de6a5b142b8f7f2dede630b5134160aedaeaf55f4d6a7e2593ca3f3'
WHEEL_NAME = 'pyserial-3.5-py2.py3-none-any.whl'
WHEEL_SHA256 = 'c4451db6ba391ca6ca299fb3ec7bae67a5c55dde170964c7a14ceefec02f2cf0'
WHEEL_URL = 'https://files.pythonhosted.org/packages/07/bc/587a445451b253b285629263eb51c2d8e9bcea4fc97826266d186f96f558/' + WHEEL_NAME
# Preserve the existing registered basename for upgrades of integration candidates.
PLG_NAME = 'rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg'
APP = 'usr/local/share/rp2040-fan-control/app/'
WEB = 'usr/local/emhttp/plugins/rp2040-fan-control/'
MANIFEST = APP + 'build-manifest.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_version(root=ROOT):
    value = (root / 'src/unraid/fan_control/version.py').read_text()
    m = re.fullmatch(r'__version__ = "([A-Za-z0-9._+-]+)"\s*', value)
    if not m:
        raise ValueError('Invalid version.py; use a literal version string')
    return m[1]


def source_files(root=ROOT):
    """Map payload names to source paths and intended installed modes."""
    files = {APP + 'rp2040_fan_control_webui_dev.py': ('src/unraid/rp2040_fan_control_webui_dev.py', 0o644)}
    for p in sorted((root / 'src/unraid/fan_control').glob('*.py')):
        if p.name in {'site_config.py', 'site_config_local.py'}:
            continue
        files[APP + 'fan_control/' + p.name] = (p.relative_to(root).as_posix(), 0o644)
    web = root / 'plugin/src' / WEB
    for p in sorted(web.rglob('*')):
        if p.is_symlink():
            raise ValueError('Symlink in source tree: ' + str(p))
        if p.is_file():
            name = WEB + p.relative_to(web).as_posix()
            files[name] = (p.relative_to(root).as_posix(), 0o755 if '/event/' in name else 0o644)
    for name in ['rp2040-fan-control', 'rp2040-fan-control-webui']:
        files['usr/local/sbin/' + name] = ('plugin/scripts/' + name, 0o755)
    files['etc/sudoers.d/rp2040-fan-control-webui'] = ('plugin/src/etc/sudoers.d/rp2040-fan-control-webui', 0o440)
    files[APP + 'LICENSES/project-MIT.txt'] = ('LICENSE', 0o644)
    files[APP + 'LICENSES/pyserial-3.5-BSD-3-Clause.txt'] = ('third_party/pyserial/LICENSE.txt', 0o644)
    files[APP + 'THIRD_PARTY_NOTICES.md'] = ('THIRD_PARTY_NOTICES.md', 0o644)
    if digest((root / 'third_party/pyserial/LICENSE.txt').read_bytes()) != PYSERIAL_LICENSE_SHA256:
        raise ValueError('pyserial license checksum mismatch')
    for _, (rel, _) in files.items():
        if (root / rel).is_symlink() or not (root / rel).is_file():
            raise ValueError('Source is missing or is a symlink: ' + rel)
    return files


def wheel_files(wheel):
    data = Path(wheel).read_bytes()
    if digest(data) != WHEEL_SHA256:
        raise ValueError('pyserial wheel checksum mismatch')
    files = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for item in archive.infolist():
            name = item.filename
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or ((item.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError('Unsafe wheel member: ' + name)
            if item.is_dir():
                continue
            if name.startswith('serial/') or name.startswith('pyserial-3.5.dist-info/'):
                if name.endswith('/RECORD'):
                    continue
                files[APP + 'vendor/' + name] = (archive.read(item), 0o644)
    if APP + 'vendor/serial/__init__.py' not in files:
        raise ValueError('Wheel lacks pyserial sources')
    return files


def collect_files(wheel, root=ROOT):
    version = source_version(root)
    files = wheel_files(wheel)
    sources = source_files(root)
    record = {}
    for target, (rel, mode) in sources.items():
        data = (root / rel).read_bytes()
        files[target] = (data, mode)
        record[target] = {'source': rel, 'sha256': digest(data), 'mode': oct(mode)}
    manifest = {'schema_version': 1, 'version': version, 'pyserial_wheel_sha256': WHEEL_SHA256, 'sources': record}
    files[MANIFEST] = ((json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode(), 0o644)
    return files


def payload_bytes(files):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.GNU_FORMAT) as archive:
        for name, (data, mode) in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), mode
            info.mtime = info.uid = info.gid = 0
            info.uname = info.gname = ''
            archive.addfile(info, io.BytesIO(data))
    # Fix the gzip OS byte as well as timestamp across supported Python versions.
    out = bytearray(gzip.compress(stream.getvalue(), mtime=0))
    out[9] = 255
    return bytes(out)


def render_plg(payload, root=ROOT):
    version = source_version(root)
    blocks = []
    for name in ['integration-install.sh.in', 'integration-remove.sh.in']:
        template = (root / 'plugin/templates' / name).read_text()
        block = template.replace('@@VERSION@@', version).replace('@@PAYLOAD_SHA256@@', digest(payload)).replace('@@PAYLOAD_BASE64@@', base64.b64encode(payload).decode())
        if '@@' in block:
            raise ValueError('Unresolved installer placeholder')
        blocks.append(block)
    text = ('<?xml version="1.0"?>\n'
            '<PLUGIN name="rp2040-fan-control" author="peromingo" version="' + version + '" launch="Settings/RP2040FanControl" pluginURL="https://raw.githubusercontent.com/peromingo/rp2040-fan-control/source-tree-review/plugin/channels/preview/rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg">\n'
            '<CHANGES>\nSource-built review candidate: JSON and serial configuration, live WebUI, protected instance locking, persistent Python selection, opt-in startup restoration, per-install rollback snapshots and bundled MIT/BSD licenses. Firmware does not return serial ACK.\n</CHANGES>\n'
            '<FILE Run="/bin/bash"><INLINE><![CDATA[' + blocks[0] + ']]></INLINE></FILE>\n'
            '<FILE Run="/bin/bash" Method="remove"><INLINE><![CDATA[' + blocks[1] + ']]></INLINE></FILE>\n</PLUGIN>\n')
    return text.encode(), blocks


def verify(plg, wheel, root=ROOT):
    text = Path(plg).read_text()
    import xml.etree.ElementTree as ET
    xml = ET.fromstring(text)
    if xml.attrib['version'] != source_version(root):
        raise ValueError('PLG/source version mismatch')
    match = re.search(r"<<'__PAYLOAD_EOF__'\n(.*?)\n__PAYLOAD_EOF__", text, re.S)
    if not match:
        raise ValueError('Missing embedded payload')
    payload = base64.b64decode(match[1], validate=True)
    if digest(payload) not in text:
        raise ValueError('Missing payload checksum')
    expected = collect_files(wheel, root)
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
        members = archive.getmembers()
        if len(members) != len(expected) or {m.name for m in members} != set(expected):
            raise ValueError('Unexpected/missing/duplicate payload members')
        for member in members:
            data, mode = expected[member.name]
            if not member.isfile() or member.mode != mode or archive.extractfile(member).read() != data:
                raise ValueError('Source/wheel payload mismatch: ' + member.name)
    if payload != payload_bytes(expected):
        raise ValueError('Payload is not the deterministic source build')
    expected_plg, _ = render_plg(payload, root)
    if Path(plg).read_bytes() != expected_plg:
        raise ValueError('Installer templates do not match the PLG')
    return len(expected)


def build(output, wheel, root=ROOT):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    payload = payload_bytes(collect_files(wheel, root))
    plg, blocks = render_plg(payload, root)
    path = output / PLG_NAME
    path.write_bytes(plg)
    (output / (PLG_NAME + '.sha256')).write_text(digest(plg) + '  ' + PLG_NAME + '\n')
    (output / 'payload.tar.gz').write_bytes(payload)
    for i, block in enumerate(blocks):
        (output / f'candidate-block{i}.sh').write_text(block)
    count = verify(path, wheel, root)
    print(f'Built {path}\nSHA-256: {digest(plg)}\nVerified {count} payload files against sources and pinned wheel')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--wheel', type=Path, help='Existing pyserial wheel; checksum is mandatory')
    parser.add_argument('--verify', type=Path, help='Verify an existing PLG instead of building')
    args = parser.parse_args()
    wheel = args.wheel
    if wheel is None:
        wheel = args.output / WHEEL_NAME
        wheel.parent.mkdir(parents=True, exist_ok=True)
        if not wheel.exists():
            with urllib.request.urlopen(WHEEL_URL, timeout=60) as response:
                wheel.write_bytes(response.read())
    if args.verify:
        print(f'Verified {verify(args.verify, wheel)} payload files and installer templates')
    else:
        build(args.output, wheel)

if __name__ == '__main__':
    main()
