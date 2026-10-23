"""Static and isolated filesystem integration tests for installer lifecycle."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALLER_SOURCE = ROOT / "plugin/scripts/install-from-payload.sh"
WRAPPER_SOURCE = ROOT / "plugin/scripts/rp2040-fan-control"
PLG_TEMPLATE = (ROOT / "plugin/rp2040-fan-control.plg.in").read_text(encoding="utf-8")
INSTALLER_TEXT = INSTALLER_SOURCE.read_text(encoding="utf-8")
WRAPPER_TEXT = WRAPPER_SOURCE.read_text(encoding="utf-8")


class InstallerLifecycleTests(unittest.TestCase):
    def test_installer_requires_root_and_valid_payload_layout(self):
        self.assertIn('[ "$(id -u)" -eq 0 ]', INSTALLER_TEXT)
        self.assertIn('"$SOURCE_APP/rp2040_fan_control_webui_dev.py"', INSTALLER_TEXT)
        self.assertIn('"$SOURCE_WEB/pages/index.php"', INSTALLER_TEXT)

    def test_update_stops_only_our_wrapper_and_preserves_local_config(self):
        self.assertIn('"$WRAPPER" stop', INSTALLER_TEXT)
        self.assertIn('cp -p "$APP_DIR/fan_control/site_config_local.py"', INSTALLER_TEXT)
        self.assertIn('site_config.example.py" "$APP_STAGE/fan_control/site_config_local.py"', INSTALLER_TEXT)

    def test_installer_never_enables_service_automatically(self):
        self.assertIn('Startup is intentionally opt-in; never create ENABLE automatically.', INSTALLER_TEXT)
        self.assertNotIn('touch "$PLUGIN_DIR/ENABLE"', INSTALLER_TEXT)
        self.assertIn('[ -f "$ENABLE_MARKER" ]', WRAPPER_TEXT)

    def test_plugin_checks_versioned_payload_checksum_before_extracting(self):
        self.assertIn('<SHA256>&payloadSHA256;</SHA256>', PLG_TEMPLATE)
        self.assertIn('ACTUAL_SHA256="$(sha256sum', PLG_TEMPLATE)
        self.assertIn('tar -xzf "$PAYLOAD" --no-same-owner', PLG_TEMPLATE)

    def test_remove_retains_persistent_configuration_and_logs(self):
        self.assertIn('Keep /boot/config/plugins/rp2040-fan-control/app and logs for safe reinstall.', PLG_TEMPLATE)
        self.assertIn('/boot/config/plugins/rp2040-fan-control/app', PLG_TEMPLATE)

    def test_wrapper_replacement_is_staged_and_rollback_protected(self):
        self.assertIn('WRAPPER_BACKUP="$PLUGIN_SBIN/.rp2040-fan-control-backup.$$"', INSTALLER_TEXT)
        self.assertIn('WRAPPER_SWAPPED=1', INSTALLER_TEXT)
        self.assertIn('mv "$WRAPPER_BACKUP" "$WRAPPER"', INSTALLER_TEXT)
        self.assertIn('WRAPPER_STAGE=$(mktemp "$PLUGIN_SBIN/.rp2040-fan-control.XXXXXX")', INSTALLER_TEXT)

    def test_existing_persistent_dir_permissions_are_not_changed(self):
        self.assertIn('refusing to alter existing permissions', INSTALLER_TEXT)
        self.assertNotIn('chmod 0750 "$PLUGIN_DIR"\n\n# Never replace', INSTALLER_TEXT)
        self.assertIn('refusing to alter permissions.', PLG_TEMPLATE)

    def test_no_world_writable_permissions_in_installer(self):
        self.assertNotRegex(INSTALLER_TEXT, r"(?m)^\s*chmod\s+0777\b")
        self.assertNotRegex(PLG_TEMPLATE, r"(?m)^\s*chmod\s+0777\b")
        self.assertNotIn('chmod 0750 /var/run/rp2040-fan-control', INSTALLER_TEXT)

    def _sandbox(self):
        td = tempfile.TemporaryDirectory(prefix="rp2040-installer-test-")
        root = Path(td.name)
        persistent = root / "boot/config/plugins/rp2040-fan-control"
        web_parent = root / "usr/local/emhttp/plugins"
        web = web_parent / "rp2040-fan-control"
        sbin = root / "usr/local/sbin"
        wrapper = sbin / "rp2040-fan-control"
        for path in (persistent, web_parent, sbin):
            path.mkdir(parents=True, exist_ok=True)
        replacements = [
            ("PLUGIN_DIR=/boot/config/plugins/rp2040-fan-control", f'PLUGIN_DIR="{persistent}"'),
            ("WEB_ROOT=/usr/local/emhttp/plugins", f'WEB_ROOT="{web_parent}"'),
            ("PLUGIN_SBIN=/usr/local/sbin", f'PLUGIN_SBIN="{sbin}"'),
        ]
        script = INSTALLER_TEXT
        for old, new in replacements:
            script = script.replace(old, new)
        installer = root / "install-from-payload.sh"
        installer.write_text(script, encoding="utf-8")
        installer.chmod(0o755)
        stage = root / "payload"
        app = stage / "usr/local/share/rp2040-fan-control/app"
        (app / "fan_control").mkdir(parents=True)
        (app / "fan_control/site_config.example.py").write_text("EXAMPLE = True\n", encoding="utf-8")
        (app / "fan_control/ipc.py").write_text("# ipc\n", encoding="utf-8")
        (app / "rp2040_fan_control_webui_dev.py").write_text("# daemon fixture\n", encoding="utf-8")
        source_web = stage / "usr/local/emhttp/plugins/rp2040-fan-control"
        (source_web / "pages").mkdir(parents=True)
        (source_web / "RP2040FanControl.page").write_text("# page\n", encoding="utf-8")
        (source_web / "pages/index.php").write_text("<?php echo 'fixture';\n", encoding="utf-8")
        source_wrapper = stage / "usr/local/sbin/rp2040-fan-control"
        source_wrapper.parent.mkdir(parents=True)
        source_wrapper.write_text("#!/bin/sh\n[ \"${1:-}\" = stop ] && exit 0\nexit 0\n", encoding="utf-8")
        source_wrapper.chmod(0o755)
        return td, root, persistent, web, wrapper, installer, stage

    def test_sandbox_first_install_creates_example_but_does_not_enable(self):
        td, root, persistent, web, wrapper, installer, stage = self._sandbox()
        with td:
            persistent.chmod(0o700)
            result = subprocess.run([str(installer), str(stage)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((persistent / "app/fan_control/site_config_local.py").exists())
            self.assertIn("EXAMPLE = True", (persistent / "app/fan_control/site_config_local.py").read_text())
            self.assertFalse((persistent / "ENABLE").exists())
            self.assertTrue((web / "pages/index.php").is_file())
            self.assertTrue(wrapper.is_file())
            self.assertEqual(persistent.stat().st_mode & 0o777, 0o700, "existing permissions must remain unchanged")

    def test_sandbox_refuses_group_writable_existing_config_dir(self):
        td, root, persistent, web, wrapper, installer, stage = self._sandbox()
        with td:
            persistent.chmod(0o770)
            result = subprocess.run([str(installer), str(stage)], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("group/world write permission", result.stderr)
            self.assertEqual(persistent.stat().st_mode & 0o777, 0o770, "installer must not silently chmod an unsafe existing directory")

    def test_sandbox_update_preserves_local_config_and_logs(self):
        td, root, persistent, web, wrapper, installer, stage = self._sandbox()
        with td:
            app = persistent / "app"
            (app / "fan_control").mkdir(parents=True)
            (app / "fan_control/site_config_local.py").write_text("HOST_CONFIG = 'keep-me'\n", encoding="utf-8")
            (persistent / "logs").mkdir()
            (persistent / "logs/previous.log").write_text("retain log\n", encoding="utf-8")
            wrapper.write_text("#!/bin/sh\n[ \"${1:-}\" = stop ] && exit 0\nexit 0\n", encoding="utf-8")
            wrapper.chmod(0o755)
            result = subprocess.run([str(installer), str(stage)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("HOST_CONFIG = 'keep-me'", (persistent / "app/fan_control/site_config_local.py").read_text())
            self.assertEqual((persistent / "logs/previous.log").read_text(), "retain log\n")

    def test_sandbox_rolls_back_when_webui_swap_fails(self):
        td, root, persistent, web, wrapper, installer, stage = self._sandbox()
        with td:
            (persistent / "app/fan_control").mkdir(parents=True)
            (persistent / "app/fan_control/site_config_local.py").write_text("OLD_CONFIG = True\n", encoding="utf-8")
            (persistent / "app/rp2040_fan_control_webui_dev.py").write_text("OLD_DAEMON = True\n", encoding="utf-8")
            (web / "pages").mkdir(parents=True)
            (web / "pages/index.php").write_text("OLD_WEB = True\n", encoding="utf-8")
            wrapper.write_text("#!/bin/sh\n[ \"${1:-}\" = stop ] && exit 0\n# OLD_WRAPPER\n", encoding="utf-8")
            wrapper.chmod(0o755)
            fakebin = root / "fakebin"
            fakebin.mkdir()
            mv = fakebin / "mv"
            marker = root / "mv-failed-once"
            mv.write_text(
                "#!/bin/sh\n"
                "last=\nfor arg do last=$arg; done\n"
                f'if [ "$last" = "{web}" ] && [ ! -e "{marker}" ]; then touch "{marker}"; echo injected-mv-failure >&2; exit 73; fi\n'
                "exec /bin/mv \"$@\"\n",
                encoding="utf-8",
            )
            mv.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = f"{fakebin}:{env.get('PATH', '/usr/bin:/bin')}"
            result = subprocess.run([str(installer), str(stage)], text=True, capture_output=True, env=env)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("OLD_CONFIG = True", (persistent / "app/fan_control/site_config_local.py").read_text())
            self.assertIn("OLD_DAEMON = True", (persistent / "app/rp2040_fan_control_webui_dev.py").read_text())
            self.assertIn("OLD_WEB = True", (web / "pages/index.php").read_text())
            self.assertIn("OLD_WRAPPER", wrapper.read_text())
            self.assertFalse(list(persistent.glob(".app-backup.*")), "successful rollback should restore rather than leave app backup")

    def test_sandbox_preserves_backup_if_rollback_itself_fails(self):
        td, root, persistent, web, wrapper, installer, stage = self._sandbox()
        with td:
            (persistent / "app/fan_control").mkdir(parents=True)
            (persistent / "app/fan_control/site_config_local.py").write_text("OLD_CONFIG = True\n", encoding="utf-8")
            (persistent / "app/rp2040_fan_control_webui_dev.py").write_text("OLD_DAEMON = True\n", encoding="utf-8")
            (web / "pages").mkdir(parents=True)
            (web / "pages/index.php").write_text("OLD_WEB = True\n", encoding="utf-8")
            wrapper.write_text("#!/bin/sh\n[ \"${1:-}\" = stop ] && exit 0\n# OLD_WRAPPER\n", encoding="utf-8")
            wrapper.chmod(0o755)
            fakebin = root / "fakebin"
            fakebin.mkdir()
            count_file = root / "web-mv-count"
            mv = fakebin / "mv"
            mv.write_text(
                "#!/bin/sh\nlast=\nfor arg do last=$arg; done\n"
                f'if [ "$last" = "{web}" ]; then count=0; [ ! -f "{count_file}" ] || count=$(cat "{count_file}"); count=$((count+1)); echo "$count" > "{count_file}"; if [ "$count" -le 2 ]; then echo injected-rollback-mv-failure >&2; exit 73; fi; fi\n'
                "exec /bin/mv \"$@\"\n",
                encoding="utf-8",
            )
            mv.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = f"{fakebin}:{env.get('PATH', '/usr/bin:/bin')}"
            result = subprocess.run([str(installer), str(stage)], text=True, capture_output=True, env=env)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("rollback failed; WebUI backup retained", result.stderr)
            backups = list(web.parent.glob(".rp2040-web-backup.*"))
            self.assertEqual(len(backups), 1, "failed rollback must retain the original WebUI backup")
            self.assertIn("OLD_WEB = True", (backups[0] / "pages/index.php").read_text())
            self.assertIn("OLD_CONFIG = True", (persistent / "app/fan_control/site_config_local.py").read_text())

    def test_wrapper_stop_succeeds_when_runtime_directory_is_absent(self):
        with tempfile.TemporaryDirectory(prefix="rp2040-wrapper-test-") as tmp:
            root = Path(tmp)
            persistent = root / "boot/config/plugins/rp2040-fan-control"
            runtime = root / "var/run/rp2040-fan-control"
            script = WRAPPER_TEXT.replace("/boot/config/plugins/rp2040-fan-control", str(persistent))
            script = script.replace("/var/run/rp2040-fan-control/daemon.pid", str(runtime / "daemon.pid"))
            script = script.replace("/var/run/rp2040-fan-control", str(runtime))
            wrapper = root / "wrapper"
            wrapper.write_text(script, encoding="utf-8")
            wrapper.chmod(0o755)
            result = subprocess.run([str(wrapper), "stop"], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("no hay PID registrado", result.stdout)


if __name__ == "__main__":
    unittest.main()
