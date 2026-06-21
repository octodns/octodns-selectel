# Developer Agent Guide for octoDNS Selectel Provider

This repository contains the Selectel provider for octoDNS. It supports planning, syncing, and applying DNS record states to both Selectel DNS API v1 and v2.

> [!IMPORTANT]
> **Core Workflow and Guidelines**
>
> All agents working on this repository must read and follow the general instructions and workflow guidelines defined in the core octoDNS `AGENTS.md` file.
> - **Local check**: Look for the file at `../octodns/AGENTS.md`.
> - **Remote check**: If the local file is not available, fetch it from GitHub: [octoDNS Core AGENTS.md](https://github.com/octodns/octodns/raw/refs/heads/main/AGENTS.md).
>
> You must align your code structure, style, pull request guidelines, and overall development workflows with the instructions specified there.

## Repository & Module Information

### Key Components

- **V2 Provider Class**: [SelectelProvider](file:///home/ross/octodns/octodns-selectel/octodns_selectel/v2/provider.py#L18-L197) (defined in [octodns_selectel/v2/provider.py](file:///home/ross/octodns/octodns-selectel/octodns_selectel/v2/provider.py)). This is the newer provider mapping records to Selectel's API v2 structure.
- **V2 Client Class**: [DNSClient](file:///home/ross/octodns/octodns-selectel/octodns_selectel/v2/dns_client.py) communicates with Selectel's DNS API v2, managing zones and resource record sets (rrsets).
- **V1 Provider Class**: [SelectelProvider](file:///home/ross/octodns/octodns-selectel/octodns_selectel/v1/provider.py#L22-L136) (defined in [octodns_selectel/v1/provider.py](file:///home/ross/octodns/octodns-selectel/octodns_selectel/v1/provider.py)). This is the legacy provider mapping to Selectel's API v1.

### Key Workflows & Features

1. **Supported Record Types**: `A`, `AAAA`, `ALIAS`, `CAA`, `CNAME`, `DNAME`, `MX`, `NS`, `TXT`, `SRV`, `SSHFP`.
2. **Authentication**: Authenticates using the account API Token via the `token` argument.
3. **Minimum TTL Constraint**: Enforces a minimum TTL limit of `60` seconds (`MIN_TTL = 60`), clamping new values below that to `60` to avoid unnecessary API errors.
4. **SSHFP Fingerprint Lowercasing**: Automatically normalizes SSHFP record fingerprints to lowercase before checking updates to prevent casing-only updates.
5. **Dynamic Routing**: Not supported (`SUPPORTS_DYNAMIC=False`, `SUPPORTS_GEO=False`).
6. **Dynamic Subnets**: Not supported (`SUPPORTS_DYNAMIC_SUBNETS=False`).
7. **Pool Value Status**: Not supported (`SUPPORTS_POOL_VALUE_STATUS=False`).

## Development & Testing

- **Setup Script**: Run `./script/bootstrap` to create a virtual environment, install dependencies (including `black`, `isort`, `pyflakes`, and `pytest`), and configure pre-commit hooks.
- **Test Suite**: Run unit tests using `pytest` via `./script/test` (or `pytest tests/`). Test files are located in [tests/](file:///home/ross/octodns/octodns-selectel/tests).
- **Code Coverage**: Verify code coverage using `./script/coverage`.

## Key Constraints & Behaviors

- **Python Version**: Targets Python `>=3.9`.
- **Formatting**: Code formatting is enforced via `black` (version `>=26.0.0,<27.0.0`) and `isort`.
