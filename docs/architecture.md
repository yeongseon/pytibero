# Architecture

## Layers

1. Application code calls `pytibero.connect(...)`.
2. `pytibero.connection.Connection` builds a Tibero ODBC connection string.
3. `pyodbc` opens the real database connection.
4. `pytibero.cursor.Cursor` delegates execute and fetch operations to the native cursor.
5. Backend exceptions are mapped into package-owned DB-API exception classes.

## Design choices

- `qmark` parameter style matches `pyodbc` and DB-API 2.0 expectations.
- Package-owned exception classes keep the public API stable.
- Connection-string creation is isolated in `protocol.py` so backend behavior is testable.
- Unit tests use a fake `pyodbc` backend; e2e tests validate the real driver path.

