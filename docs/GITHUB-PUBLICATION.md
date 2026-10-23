# GitHub publication runbook

This document prepares the project for manual publication. No repository has been created, and nothing has been pushed or published by this workflow.

## Before creating the repository

- [ ] Confirm the GitHub account/organization and final repository name.
- [ ] Review source ownership and rights to publish all included code, especially the firmware readback and recovered modules.
- [ ] Review the complete diff and run the checks listed below.
- [ ] Confirm the repository is public only if that is the intended license/disclosure choice.
- [ ] Keep all real disk serials, local configuration, host logs, and production artifacts out of the initial commit.
- [ ] Do not include generated `dist/` archives in source control; attach reviewed artifacts to a GitHub Release later.

## Suggested repository settings

- Repository name: `rp2040-sata-hat` or another name chosen by the maintainer.
- License: MIT (`LICENSE` is already present; verify ownership before publishing).
- Default branch: `main`.
- Enable GitHub Actions for the included CI workflow.
- Keep branch protection and release permissions appropriate to the maintainer's workflow.
- Do not add a `.plg` download URL until a tested release asset exists.

## Local validation

Run the structural publication audit before packaging. It catches common private/local artifacts but is not a secret scanner and does not replace manual review.

```sh
PYTHONDONTWRITEBYTECODE=1 python tools/audit_publication.py .
```

For a generated payload, also run `python tools/audit_publication.py --payload dist/<payload>.tar.gz`.


From the repository root:

```sh
PYTHONPATH=src/unraid python -m unittest discover -s tests -v
python -m compileall -q src tests
php -l plugin/src/usr/local/emhttp/plugins/rp2040-fan-control/pages/index.php
sh -n plugin/scripts/rp2040-fan-control tools/build_unraid_payload.sh
./tools/build_unraid_payload.sh 0.6.0-dev
sha256sum -c dist/rp2040-fan-control-0.6.0-dev-payload.tar.gz.sha256
```

The payload is only a review artifact, not an installer. Do not publish it as a stable release until the `.plg` lifecycle, emhttp permissions, dependencies, and isolated Unraid VM tests are complete.

## First push (manual; not executed)

After creating the empty repository in GitHub and checking its URL, the maintainer can configure the remote and push the reviewed branch. Do not copy/paste a guessed repository URL. Before the first push, inspect `git status`, `git diff --check`, and the staged file list to ensure no private files were added.

## Release blockers

- [ ] Validate the actual PHP/emhttp user and IPC access model on the target Unraid version.
- [ ] Complete persistent configuration and service lifecycle handling.
- [ ] Implement and review the real `.plg` with checksum verification and a real release asset URL.
- [ ] Test install, upgrade, stop, uninstall, and reboot in an isolated Unraid VM.
- [ ] Verify no local config/logs are overwritten or removed by upgrade/uninstall.
