# Changelog

## 0.2.0

- Mapped `DBAPIType` constants to real ODBC SQL type codes instead of placeholders
- Improved `tbcli` backend: `Decimal` values now bind as `SQL_NUMERIC` instead of `SQL_DOUBLE`
- Added chunked `SQLGetData` loop in `tbcli` backend for large column reads
- Extended type system with `TIMESTAMP WITH TIME ZONE`, `TIMESTAMP WITH LOCAL TIME ZONE`, and `LONG VARCHAR` mappings

## 0.1.0

- Added a DB-API 2.0 compatible package surface for Tibero
- Added a `pyodbc`-backed connection and cursor implementation
- Added Docker-based unit-test and e2e test workflows
- Added project documentation and development guides

