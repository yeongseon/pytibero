# Agent Playbook

## Source Of Truth
- `README.md` for installation, quick start, and test workflow.
- `CONTRIBUTING.md` for local development commands.
- `pyproject.toml` and `Makefile` for package and verification truth.

## Repository Map
- `pytibero/` package code.
- `tests/` unit and end-to-end coverage.
- `docs/` supplementary documentation.

## Change Workflow
1. Check whether the change affects DB-API semantics, DSN handling, or docs only.
2. Keep README examples current when public connection or cursor behavior changes.
3. Use Docker-backed tests for changes that require a live database.
4. Avoid expanding dependencies without updating packaging and docs together.

## Validation
- `make test`
- `make lint`
- `make format`
- `make test-docker`
- `make test-e2e-docker`
