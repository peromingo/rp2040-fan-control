# Security policy

## Scope

This repository is a development-stage Unraid fan-control integration for an RP2040 SATA HAT. It is not currently a validated production installer.

## Reporting a vulnerability

Please do not publish live host logs, disk serial numbers, IP addresses, credentials, or configuration files in a public issue. Until a private security contact is configured for the repository, do not submit sensitive details publicly; contact the maintainer through a private channel already known to you.

## Safe testing

- Use a disposable Unraid VM or isolated test host.
- Do not test this development daemon against a production RP2040 or live Unraid array.
- Do not make the IPC directory world-writable.
- Treat WebUI commands as requests to the daemon, not as confirmation from the RP2040 firmware. The current firmware does not return an ACK.
