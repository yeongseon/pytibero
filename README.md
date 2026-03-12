# pytibero

**Unofficial Python DB-API 2.0 connector for Tibero**

`pytibero` provides a Pythonic DB-API 2.0 interface for Tibero databases. The
current implementation uses `pyodbc` as the transport backend and wraps Tibero
ODBC connectivity behind a clean, package-owned API surface.

This is an independent community project and is not officially supported by
TmaxSoft. This project is not affiliated with TmaxSoft.

## Why pytibero

- Python DB-API 2.0 compatible module surface
- Direct host/port or DSN-based Tibero ODBC connections
- Package-owned exception hierarchy and type constructors
- Dockerized unit-test workflow with a 95% coverage target
- Docker-based end-to-end test harness for licensed Tibero environments

## Installation

### Python package

```bash
pip install pytibero
```

### System requirements

- Python 3.10+
- `pyodbc`
- unixODBC or an equivalent ODBC manager
- A Tibero ODBC driver installed on the host or in the container

## Quick Start

```python
import pytibero

with pytibero.connect(
    host="localhost",
    port=8629,
    database="test",
    user="tibero",
    password="tmax",
) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM dual")
    print(cursor.fetchall())
```

### DSN connection

```python
import pytibero

conn = pytibero.connect(dsn="TIBERO_TEST", user="tibero", password="tmax")
```

## Testing

### Unit tests in Docker

```bash
make test-docker
```

This runs the package test suite inside Docker and enforces a `95%` coverage
threshold.

### End-to-end tests in Docker

```bash
make test-e2e-docker
```

The e2e flow expects a licensed Tibero Docker image and a valid license file.
See [docs/testing.md](docs/testing.md) for the required environment variables.

## Documentation

- [docs/README.md](docs/README.md)
- [docs/installation.md](docs/installation.md)
- [docs/testing.md](docs/testing.md)
- [docs/architecture.md](docs/architecture.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)

## Project Layout

```text
pytibero/
    __init__.py
    connection.py
    cursor.py
    exceptions.py
    types.py
    protocol.py
    config.py
tests/
docs/
```

## License

Apache License 2.0. See [LICENSE](LICENSE).
