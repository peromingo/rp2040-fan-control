# RP2040 SATA HAT fan control for Unraid

Development controller and WebUI for RP2040 fan control. The firmware does not return serial ACK: a successful command confirms daemon acceptance and a completed serial write, not measured fan RPM.

The source-built review candidate is **0.8.0-source-rc2**. Its runtime combines persistent JSON disk/CPU assignments, serial-port selection, live WebUI, source warnings and opt-in boot startup with protected instance locking and Python interpreter diagnostics. It is not a stable release; this consolidated runtime requires target validation.

## Build the installable review PLG

With Python 3.11 or newer:

```sh
python3 tools/build_integration_plg.py /tmp/rp2040-source-rc2
```

The builder downloads the official pyserial 3.5 wheel if necessary and checks its pinned SHA-256 before packaging. For an offline build, supply `--wheel /path/to/pyserial-3.5-py2.py3-none-any.whl`. No pip installation is performed on Unraid.

Outputs include the self-contained `.plg`, its `.sha256`, `payload.tar.gz`, and inspectable installation/removal scripts. The payload is built directly from `src/unraid`, `plugin/src` and `plugin/scripts`. Transaction templates live in `plugin/templates`. The verifier compares every extracted file, permission and installer block against its source or the pinned dependency wheel. A `build-manifest.json` is included in the app payload.

The legacy `rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg` basename is deliberately retained for the existing integration-plugin upgrade path. The internal version identifies the candidate. Do not install additional copies under alternative basenames.

```sh
python3 tools/build_integration_plg.py /tmp/rp2040-source-rc2 \
  --wheel /path/to/pyserial-3.5-py2.py3-none-any.whl \
  --verify /tmp/rp2040-source-rc2/rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg
```

## Development checks

Install `requirements.txt` in a development environment. PHP CLI enables the PHP integration tests.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/unraid \
  RP2040_TEST_WHEEL=/path/to/pyserial-3.5-py2.py3-none-any.whl \
  python3 -m unittest discover -s tests -v
python3 tools/test_boot_candidate.py /tmp/rp2040-source-rc2
```

Tests use temporary filesystems and fake service/serial operations. They do not start hardware control. CI runs Python 3.11/3.12, PHP syntax and protocol checks, source/publication audits, lifecycle simulations, source/payload verification and deterministic rebuild comparison.

## Unraid lifecycle

Manual installation requires the existing service stopped and ENABLE absent. Installation preserves configuration and logs and leaves the service disabled. The startup event starts only with ENABLE present and no pending recovery. On reboot the installer can restore missing RAM files while preserving ENABLE; enabled updates against an existing runtime are refused. The standard `/var/run -> /run` alias is supported.

Use the WebUI helper to stop the service before an update. Uninstall restores that candidate's verified baseline, removes ENABLE, and preserves persistent configuration/logs/backups. A failed recovery retains `recovery-pending` for inspection. First installation uses example placeholders and must be configured before starting.

The main WebUI route processes mutating forms through Unraid. Direct POST requests to the PHP live endpoint are rejected; direct GET polling is read-only. PHP invokes a fixed-action privileged helper under the supplied sudoers policy.

## Publication

Integration artifacts auditfix21–24 are retained as historical candidates. The source-built candidate supersedes their build process; its runtime changes still need target validation. Automatic update checking (`pluginURL`) will be configured with a stable release channel. No stable release is published by this build command.

See `docs/SOURCE-PACKAGE-REVIEW.md`, `docs/GITHUB-PUBLICATION.md`, `CONTRIBUTING.md` and `SECURITY.md`. Source ownership/license/security review remains required for release approval. Firmware is included for reference; building/installing the Unraid package does not flash it.

The older `plugin/rp2040-fan-control.plg.in`, `tools/render_unraid_plg.py`, and `plugin/scripts/install-from-payload.sh` are historical prototype/reference code, not the deployment path for this candidate.
