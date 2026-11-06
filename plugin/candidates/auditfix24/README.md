# Auditfix24 boot-support review candidate

Version: `0.7.16-boot-auditfix24`. The existing auditfix19 PLG basename is retained so that Unraid updates the registered plugin instead of creating another entry.

The installer explicitly accepts the standard `/var/run -> /run` alias, validates `/run/rp2040-fan-control` through the canonical path, and rejects unexpected runtime symlinks. This corrects auditfix23, which rejected the system alias.

The installer permits reconstruction with an existing regular ENABLE file only when both the RAM service wrapper and IPC directory are absent. It refuses installation when a matching daemon is running, and refuses enabled updates against an existing runtime. Installation preserves ENABLE and does not launch the daemon.

The executable `event/startup/rp2040-autostart` hook starts the service after plugin installation, independently of array start. It requires ENABLE and no pending recovery journal. The wrapper validates the configuration and dependencies before starting. Startup output is appended to `logs/boot.log`; a 30-second timeout bounds the event so an error cannot indefinitely block emhttp initialization. No array-stop hook is added.

The new hook participates in the installer's backup, rollback, checksum and uninstall verification. This candidate uses its own `webui-integration-serial-port-conf-auditfix24` baseline.

Rebuild from the retained auditfix22 candidate using Python 3.11 or newer:

```sh
python3 tools/build_boot_candidate.py plugin/candidates/auditfix22/rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg /tmp/auditfix24-build
python3 tools/test_boot_candidate.py /tmp/auditfix24-build
```

The output directory must be empty. The builder writes inspectable payload sources and install/remove scripts beside the package. The tests use isolated filesystem roots and stub service invocations; they never start hardware control. They cover disabled installation, enabled-update refusal, RAM reconstruction with ENABLE preserved, ENABLE/recovery guards in startup, untracked daemon detection NEW/EXISTING hook uninstall restoration, canonical IPC refusal, the standard runtime alias and unexpected-symlink rejection. macOS adapters accommodate Linux CLI syntax; real timeout behavior and a complete Unraid reboot remain on-target validation requirements.

This is a development candidate. A real reboot test and review remain required before declaring boot support verified on Unraid. Python 3, smartctl, timeout, and the existing installer dependencies must be available. The source-tree architecture and integration candidates remain separate as described in docs/GITHUB-PUBLICATION.md.
