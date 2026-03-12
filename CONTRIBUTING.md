# Contributing

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Useful Commands

```bash
make test
make test-docker
make test-e2e-docker
ruff check .
ruff format .
```

## Notes

- Keep the public API aligned with Python DB-API 2.0 (PEP 249).
- Keep unit tests Docker-runnable and maintain at least 95% line coverage.
- Keep e2e tests Docker-based and isolated from unit-test concerns.
- Add or update tests with each behavioral change.
