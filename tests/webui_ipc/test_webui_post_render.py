"""Exercise the actual PHP mode handler inside an already rendered Unraid shell."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / 'plugin/src/usr/local/emhttp/plugins/rp2040-fan-control/pages/index.php'

@unittest.skipUnless(shutil.which('php'), 'PHP CLI is not installed')
class WebUIPostRenderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rp2040-post-render-')
        self.root = Path(self.tmp.name)
        self.ipc = self.root / 'ipc'
        self.ipc.mkdir()
        (self.ipc / 'status.json').write_text(json.dumps({'timestamp': time.time(), 'mode': 'AUTO'}))
        ini = self.root / 'var.ini'
        ini.write_text('csrf_token="synthetic_test_token"\n')
        helper = self.root / 'helper'
        helper.write_text('#!/bin/sh\nprintf "null\\n"\n')
        helper.chmod(0o755)
        source = PAGE.read_text()
        source = source.replace('/var/run/rp2040-fan-control/', self.ipc.as_posix() + '/')
        source = source.replace('/var/local/emhttp/var.ini', ini.as_posix())
        source = source.replace('sudo -n /usr/local/sbin/rp2040-fan-control-webui', helper.as_posix())
        self.page = self.root / 'index.php'
        self.page.write_text(source)

    def tearDown(self):
        self.tmp.cleanup()

    def php(self, code, *args):
        r = subprocess.run(['php', '-d', 'output_buffering=0', '-r', code, str(self.page), *args], capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn('headers already sent', r.stderr.lower())
        return r.stdout

    def post(self, uri='/Settings/RP2040FanControl'):
        return self.php('echo "UNRAID_SHELL"; flush(); $_SERVER["REQUEST_METHOD"]="POST"; $_SERVER["SCRIPT_FILENAME"]="/synthetic-router.php"; $_SERVER["REQUEST_URI"]=$argv[2]; $_POST=["mode"=>"SILENT"]; include $argv[1];', uri)

    def test_emitted_shell_does_not_leave_blank_page_after_publishing_command(self):
        html = self.post()
        request = json.loads((self.ipc / 'command.json').read_text())
        self.assertEqual(request['mode'], 'SILENT')
        self.assertIn('<div class="rp2040-fan-control">', html)
        self.assertIn('window.location.replace(', html)
        self.assertIn('request_id=' + request['request_id'], html)
        self.assertIn('<form', html)

    def test_pending_command_is_not_overwritten_and_page_still_renders(self):
        path = self.ipc / 'command.json'
        path.write_text('{"sentinel":true}')
        html = self.post()
        self.assertEqual(path.read_text(), '{"sentinel":true}')
        self.assertIn('solicitud pendiente', html)
        self.assertIn('<div class="rp2040-fan-control">', html)
        self.assertNotIn('window.location.replace(', html)

    def test_redirect_stays_on_plugin_route(self):
        html = self.post('//outside.invalid/anything')
        self.assertNotIn('outside.invalid', html)
        self.assertIn('Settings', html)
        self.assertIn('RP2040FanControl', html)

    def test_live_status_returns_only_the_tracked_command_result(self):
        request_id = 'a' * 32
        result = {'request_id': request_id, 'ok': True, 'message': 'confirmed', 'applied_mode': 'SILENT'}
        (self.ipc / 'command-result.json').write_text(json.dumps(result))
        code = '$_SERVER["REQUEST_METHOD"]="GET"; $_GET=["rp2040_live"=>"1","request_id"=>$argv[2]]; include $argv[1];'
        self.assertEqual(json.loads(self.php(code, request_id))['command_result'], result)
        self.assertIsNone(json.loads(self.php(code, 'b' * 32))['command_result'])
        self.assertFalse((self.ipc / 'command.json').exists())
