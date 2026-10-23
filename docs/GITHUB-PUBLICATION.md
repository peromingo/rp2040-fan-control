# GitHub Publication and Release Checklist

## Current repository status

The repository is available at:

- Repository: `peromingo/rp2040-fan-control`
- Working branch: `source-tree-review`
- Default branch: `main`
- License: MIT, subject to confirmation that all included source code and firmware can legally be published.

The source tree has been uploaded to GitHub. The CI workflow and `.gitignore` are included in the working branch.

This document tracks publication readiness. A successful CI run validates the checks implemented in the workflow, but does not establish that the software is production-ready or that it works correctly on every Unraid installation.

Do not merge the working branch into `main` or publish a stable release until the applicable reviews and release blockers below have been addressed.

## 1. Source and security review

- [ ] Review the complete branch diff before merging.
- [ ] Confirm ownership and publication rights for all source files, recovered modules and firmware readback material.
- [ ] Verify that no real disk serial numbers, host-specific configuration, production logs, credentials or other private artifacts are included.
- [ ] Confirm that `site_config_local.py`, `site_config.py`, `.env`, logs, Python caches and generated `dist/` files are excluded from source control as appropriate.
- [ ] Review `.gitignore` and `tools/audit_publication.py`; neither replaces a manual security review or a dedicated secret scan.
- [ ] Confirm that the example configuration contains only safe placeholder values.
- [ ] Review the README, license, contribution guidance and security policy for consistency with the actual project.

## 2. Continuous integration

The workflow is located at `.github/workflows/ci.yml`.

It is configured to run on pushes, pull requests and manual dispatch. Its checks include:

- Python syntax compilation on Python 3.11 and 3.12.
- Unit and integration-contract tests.
- Publication source-tree audit.
- PHP syntax validation.
- Shell syntax validation.
- Payload generation and SHA-256 checksum verification.
- Audit of the generated payload.
- Deterministic payload comparison.

Before merging:

- [ ] Confirm the latest relevant GitHub Actions run has completed successfully.
- [ ] Confirm that all matrix jobs have passed, not merely that no red status is visible.
- [ ] Investigate any skipped, cancelled or missing jobs.
- [ ] Review the test output and verify that failures have not been hidden or bypassed.

CI passing is necessary but does not replace hardware testing or isolated Unraid integration testing.

## 3. Local validation

Run the following commands from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python tools/audit_publication.py .
PYTHONPATH=src/unraid python -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/rp2040-pycache python -m compileall -q src tests tools
php -l plugin/src/usr/local/emhttp/plugins/rp2040-fan-control/pages/index.php
sh -n plugin/scripts/rp2040-fan-control plugin/scripts/install-from-payload.sh tools/build_unraid_payload.sh
```

To build and verify a review payload:

```sh
./tools/build_unraid_payload.sh 0.6.0-dev
(
  cd dist
  sha256sum -c rp2040-fan-control-0.6.0-dev-payload.tar.gz.sha256
)
python tools/audit_publication.py --payload dist/rp2040-fan-control-0.6.0-dev-payload.tar.gz
```

Use a version identifier appropriate to the current development stage. Confirm the exact generated filenames before running checksum verification.

The payload is a review artifact, not a production installer.

## 4. Unraid integration and operational safety

The following items require validation on an isolated Unraid test system before a stable release:

- [ ] Confirm the actual PHP/emhttp execution identity and permissions.
- [ ] Validate inter-process communication and command/status file access.
- [ ] Verify persistent configuration creation, validation and migration.
- [ ] Verify daemon start, stop, restart and failure recovery.
- [ ] Verify service startup and shutdown behaviour across reboot.
- [ ] Confirm that upgrades preserve user configuration and do not overwrite local settings.
- [ ] Confirm that uninstall does not remove user data or unrelated system files.
- [ ] Test fan-control behaviour, telemetry, error handling and safe fallback behaviour.
- [ ] Test supported hardware and document known limitations.
- [ ] Verify installation, upgrade, rollback and uninstall in an isolated Unraid VM or equivalent test environment.

Do not test unverified installation or service changes against a production server or live storage array.

## 5. Plugin and release artifact

- [ ] Implement and review the actual `.plg` installer.
- [ ] Ensure that the installer verifies the checksum of downloaded release artifacts.
- [ ] Use a real, versioned GitHub Release asset URL; do not publish placeholder URLs.
- [ ] Verify dependency handling and installation paths.
- [ ] Test install, upgrade, stop, uninstall and reboot.
- [ ] Verify that user configuration and logs are preserved where required.
- [ ] Document the supported Unraid versions and recovery procedure.
- [ ] Attach only reviewed, reproducible release artifacts to the GitHub Release.

Do not label a generated payload as a stable release or advertise an installable `.plg` until the complete lifecycle has been tested.

## 6. Branch and merge procedure

Keep development changes on `source-tree-review` until review is complete.

Before creating or approving a pull request:

1. Inspect the branch diff against `main`.
2. Run `git diff --check`.
3. Review the staged and committed file lists for private or generated artifacts.
4. Confirm that the latest CI checks passed.
5. Resolve documentation discrepancies and security-review findings.
6. Record any remaining limitations explicitly in the pull request.

Do not force-push or merge changes without reviewing the impact on the target branch.

## 7. Release readiness

A stable release is blocked until the following are complete:

- [ ] Source ownership and publication rights confirmed.
- [ ] Security and privacy review completed.
- [ ] CI checks pass on the reviewed commit.
- [ ] Unraid permissions and IPC model validated.
- [ ] Persistent configuration and service lifecycle verified.
- [ ] Actual `.plg` installer implemented and reviewed.
- [ ] Installation, upgrade, rollback, uninstall and reboot tested.
- [ ] No private configuration, production logs or hardware identifiers exposed.
- [ ] Release payload and checksums verified.
- [ ] README and release notes accurately describe tested functionality and limitations.

Once these requirements are satisfied, the maintainer can approve the merge and prepare a versioned release.

## 8. Known limitations

A successful source audit or CI run does not prove:

- Compatibility with every Unraid release.
- Correct permissions under the target emhttp/PHP execution environment.
- Safe operation with every RP2040 firmware version or SATA HAT revision.
- Correct behaviour under hardware failure or communication loss.
- Completion of the real installation and uninstall lifecycle.

These claims must be supported by testing and documented evidence before they are presented as verified features.
