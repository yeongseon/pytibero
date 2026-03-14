# AGENTS.md

## Purpose
`pytibero` is an unofficial Python DB-API 2.0 connector for Tibero.

## Read First
- `README.md`
- `CONTRIBUTING.md`
- `docs/agent-playbook.md`

## Working Rules
- Preserve DB-API behavior and documented connection patterns unless a contract change is intentional.
- Keep test guidance and Docker workflows aligned with actual commands.
- Prefer compatibility-safe changes to exceptions, cursor behavior, and connection handling.
- Add tests for every driver behavior change.

## Validation
- `make test`
- `make lint`
- `make test-docker` or `make test-e2e-docker` when database-backed paths change
