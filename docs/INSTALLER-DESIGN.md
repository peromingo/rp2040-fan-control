# Unraid installer design — pre-release

## Current status

The project does not yet have a release-ready `.plg`. `tools/build_unraid_payload.sh` creates a reproducible **payload preview archive** for code review only. It is deliberately not an `installpkg` package and must not be installed directly on Unraid.

## Planned file placement

- UI page: `/usr/local/emhttp/plugins/rp2040-fan-control/`
- Service wrapper: `/usr/local/sbin/rp2040-fan-control`
- Persistent application copy and local hardware configuration: `/boot/config/plugins/rp2040-fan-control/app/`
- Runtime IPC: `/var/run/rp2040-fan-control/` (ephemeral; recreated after boot)
- Persistent logs: `/boot/config/plugins/rp2040-fan-control/logs/`

The payload stages application source under `/usr/local/share/rp2040-fan-control/app/`. A future `.plg` must copy that source into the persistent application directory on install/update, without overwriting `site_config_local.py` once it exists.

## Required `.plg` behavior before release

1. Verify archive checksum before extracting or installing.
2. Stop only this plugin's daemon before update/uninstall; validate PID identity.
3. Copy new application files while preserving local config and logs.
4. Create example local config only if no local config exists; keep startup disabled until explicit opt-in and completed validation.
5. Never change disk assignments, array state, firmware, or `/boot/config/go`.
6. On uninstall, remove only plugin-owned transient files and service registration; preserve persistent configuration and logs unless the user explicitly requests their removal.
7. Fail closed on unknown PHP/emhttp permissions. No world-writable IPC directory.
8. Test install, upgrade, stop, uninstall and reboot behavior in an isolated Unraid VM before release.

## Release blocker

A genuine distribution URL/repository release is not known yet. Do not substitute a guessed GitHub URL. Until the project repository and release URL are provided, a `.plg` cannot fetch a verifiable payload, so no installable plugin is generated.

## Pre-release installer implementation

- `plugin/rp2040-fan-control.plg.in` is a template, not an installable plugin.
- `tools/render_unraid_plg.py` renders a `.plg` only when supplied with a SemVer-like version, real HTTPS URLs for the plugin/payload/support page, and a 64-character payload SHA-256. It validates XML and rejects unresolved placeholders.
- `tools/build_unraid_payload.sh` now includes `usr/local/share/rp2040-fan-control/install.sh`. The helper stages the application, preserves an existing `site_config_local.py` and logs, creates an example-based local config only on first install, and does not create `ENABLE`.
- The `.plg` uses a versioned payload cache, verifies SHA-256 before extraction, rejects unsafe archive paths, and has a conservative remove hook. Removal keeps persistent config and logs.

This remains pre-release. The rendered `.plg` must not be produced with guessed URLs and must not be installed on the production host. The service wrapper and installer have isolated temporary-filesystem integration tests plus static/syntax and unit-test coverage (53 tests at the latest local run); they have not been executed against a real Unraid filesystem or plugin manager. PHP/emhttp write permissions for the IPC directory remain unresolved and are intentionally not loosened.


## Runtime dependencies and IPC permissions

The service wrapper currently requires an executable `python3`, importable `pyserial`, and `smartctl`. The installer does not install Python or pip packages; dependency provisioning must be documented and validated for the selected Unraid version before release. Existing IPC directories are no longer chmodded automatically: a newly created directory receives mode 0750, while an existing directory must be root-owned and not world-writable or the wrapper refuses to start. This still does not prove that PHP/emhttp can publish commands; that must be tested on the target Unraid release.


## Dependency preflight (development)

The service wrapper exposes `check-deps`, which only reports the selected Python interpreter, its `pyserial` import, and whether `smartctl` is on `PATH`; it does not install packages or access the RP2040 serial device. The Python interpreter can be selected by setting `RP2040_PYTHON` for a manual invocation or by placing its absolute executable path on the first line of `/boot/config/plugins/rp2040-fan-control/python-path`. The persistent file is read as data, never sourced as shell code.

Do not assume Python 3 is present in every Unraid installation, and do not install arbitrary Slackware packages or run `pip` against the system interpreter from this plugin. One current option listed in Community Applications is the third-party **Python 3 for UNRAID** plugin, which advertises Python, pip and uv for Unraid 6/7: https://ca.unraid.net/apps/python-3-for-unraid-1yap4lr1a085yr. Its presence, interpreter path, persistence and `pyserial` availability must be checked on the target system. This project does not install or update that dependency automatically.

Before any future release, run `/usr/local/sbin/rp2040-fan-control check-deps` on an isolated Unraid test host after configuring the selected interpreter. This command is diagnostic only; it is not evidence that PHP/emhttp permissions or serial communication work.
