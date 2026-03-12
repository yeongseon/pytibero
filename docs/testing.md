# Testing

## Unit tests

Unit tests run in Docker and enforce at least `95%` line coverage.

```bash
make test-docker
```

The unit-test container installs development dependencies and runs:

```bash
python -m pytest --cov=pytibero --cov-report=term-missing --cov-fail-under=95
```

## End-to-end tests

End-to-end tests are Docker-based and require a licensed Tibero image plus a
valid license file.

### Required environment variables

- `TIBERO_LICENSE_FILE`
- `TIBERO_IMAGE` (optional, defaults to `tiberoofficial/tibero:latest`)
- `TIBERO_PORT` (optional, defaults to `8629`)
- `TIBERO_DATABASE` (optional)
- `TIBERO_USER` (optional)
- `TIBERO_PASSWORD` (optional)
- `TIBERO_DRIVER` (optional)

### Run e2e

```bash
make test-e2e-docker
```

The e2e test runner waits for the database port and then runs the package smoke
tests against the live service.

