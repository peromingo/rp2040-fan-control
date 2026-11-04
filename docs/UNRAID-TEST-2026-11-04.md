# Unraid integration test: 2026-11-04

This records the auditfix21 candidate tested on the Unraid-N100 host. It is
evidence for a development integration candidate, not a general production
readiness claim.

## Candidate

- Package: `plugin/candidates/auditfix21/rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg`
- Package SHA-256: `611d53833b20e9d919cd713c72e57f0b5943c0633553677b118b0edbedaa21b1`
- Internal candidate version: `0.7.13-final-ui-auditfix21`
- The legacy `auditfix19` filename was retained to update the already-registered
  Unraid plugin entry instead of registering a duplicate.

## Verified on the host

- The plugin installed with the daemon disabled; no `ENABLE` file was created.
- The WebUI page loaded with `Menu="Utilities"`, `Type="menu"`, and `Icon="cog"`.
- PHP syntax validation passed after installation.
- The UI exposed daemon controls, stable serial-port selection, and persistent
  FAN1/FAN2 thermal-source selection.
- The live endpoint returned JSON from
  `/plugins/rp2040-fan-control/pages/index.php?rp2040_live=1`; requests through
  the Unraid settings route returned the full HTML shell instead. The page now
  polls the direct plugin endpoint every five seconds.
- The daemon ran with the RP2040 connected on the stable `/dev/serial/by-id/…`
  path. The live status reported `CONNECTED`, `fail_safe=false`, and no serial
  disconnects during the captured check.
- AUTO, SILENT, and TURBO mode requests were exercised; daemon status and
  command results reported the selected modes. The firmware does not return an
  ACK, so a successful serial write is not proof that the physical fans reached
  the requested speed.
- The updated responsive layout grouped service, serial, thermal configuration,
  status, fan metrics, and mode controls into panels/cards.

## Still pending before a stable release

- Uninstall and reinstall of the candidate as a complete lifecycle test.
- Reboot/startup and rollback testing after this exact candidate.
- Source ownership, security, privacy, compatibility and release-artifact review
  listed in `GITHUB-PUBLICATION.md`.

The candidate package is retained for review and reproducibility. Do not treat
it as a stable GitHub Release or as a reproducible build of the newer daemon
sources in the main source tree.
