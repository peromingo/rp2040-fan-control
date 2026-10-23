# Source baseline and limitations

## Verified firmware
`firmware/rp2040/main.py` is the byte-identical readback supplied for review. Its SHA-256 is recorded in `firmware/rp2040/README.md`.

## Verified Unraid daemon
The recovered active daemon's SHA-256 was `cc05574e9ae8f4ec2c9f43f83b029638d7ecc06e25c3aa4c09ac1ee6c0083a65`. The public staging daemon is a modified copy: machine-specific disk identities were removed in favor of a local configuration module, and installation paths were made configurable. The recovered production daemon is intentionally not included because it contains private disk serial numbers.

## Package comparison
The recovered `fan_control` package contains ten Python modules. Nine match the initial source-review archive byte-for-byte. `config.py` differs because the staging copy replaces fixed installation paths with configurable paths. All ten recovered module checksums were validated against the supplied `SHA256SUMS`.

## Limitations
This repository is a staging baseline, not a release. The daemon's hardware integration and fail-safe behavior still need review and tests in an isolated environment. Do not deploy it to a live Unraid host yet.
