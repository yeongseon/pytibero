# pytibero

[![CI](https://github.com/yeongseon/pytibero/actions/workflows/ci.yml/badge.svg)](https://github.com/yeongseon/pytibero/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/pytibero)](https://pypi.org/project/pytibero/)
[![docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://yeongseon.github.io/pytibero/)

**Unofficial Python DB-API 2.0 connector for Tibero**

`pytibero` provides a Pythonic DB-API 2.0 interface for Tibero databases. The
current implementation uses `pyodbc` as the transport backend and wraps Tibero
ODBC connectivity behind a clean, package-owned API surface.

This is an independent community project and is not officially supported by
TmaxSoft. This project is not affiliated with TmaxSoft.

## Why pytibero

- Python DB-API 2.0 compatible module surface
- Direct host/port or DSN-based Tibero ODBC connections
- Optional `tbcli` backend for Tibero's native client library path
- Explicit `autocommit` plus routed `pyodbc.connect(...)` keyword support
- Package-owned exception hierarchy and type constructors
- Safe access to common `pyodbc` connection metadata such as `getinfo(...)`
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

### Native `tbcli` backend

```python
import pytibero

conn = pytibero.connect(
    host="localhost",
    port=8629,
    database="test",
    user="tibero",
    password="tmax",
    backend="tbcli",
    tbcli_library="/opt/tibero7/client/lib/libtbcli.so",
)
```

`backend="tbcli"` uses Tibero's native CLI library instead of `pyodbc`. This
path is intended for environments where the vendor client library is available
locally.

### Advanced connection options

```python
import pytibero

conn = pytibero.connect(
    host="localhost",
    user="tibero",
    password="tmax",
    autocommit=True,
    readonly=True,
    ansi=False,
    ApplicationName="pytibero-app",
)

print(conn.getinfo(17))
```

`readonly`, `ansi`, and similar `pyodbc.connect(...)` options are forwarded as
native connect kwargs, while additional values such as `ApplicationName` stay in
the ODBC connection string.

## Testing

### Unit tests in Docker

```bash
make test-docker
```

This runs the package test suite inside Docker and enforces a `95%` coverage
threshold.

### End-to-end tests in Docker

```bash
export TIBERO_LICENSE_FILE=/abs/path/to/license.xml
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
    tbcli.py
tests/
docs/
```

## License

Apache License 2.0. See [LICENSE](LICENSE).
