# Contributing

Thank you for helping review the RP2040 SATA HAT fan-control project. This repository is a development baseline, not a release-ready Unraid plugin.

## Before opening a pull request

1. Keep host-specific disk serials, hostnames, logs, credentials, and local configuration out of commits.
2. Do not add `site_config_local.py`; edit `site_config.example.py` only when changing the documented configuration contract.
3. Run the test suite and syntax checks from the repository root:

   ```sh
   PYTHONPATH=src/unraid python -m unittest discover -s tests -v
   python -m compileall -q src tests
   php -l plugin/src/usr/local/emhttp/plugins/rp2040-fan-control/pages/index.php
   sh -n plugin/scripts/rp2040-fan-control tools/build_unraid_payload.sh
   ```

4. Add tests for behavior changes, especially IPC validation, fail-safe handling, serial transmission outcomes, and service lifecycle.
5. Do not claim firmware receipt: the current RP2040 firmware does not send an ACK.
6. Do not test on the production Unraid host or modify firmware unless a separate, explicit hardware test plan has been approved.

## Pull request scope

Explain the change, how it was tested, and any remaining limitations. Clearly separate simulated tests from tests performed on real Unraid hardware.
