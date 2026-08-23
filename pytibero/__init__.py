"""pytibero public DB-API surface."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .exceptions import (
    DatabaseError,
    DataError,
    Error,
    IntegrityError,
    InterfaceError,
    InternalError,
    NotSupportedError,
    OperationalError,
    ProgrammingError,
    Warning,
)
from .types import (
    BINARY,
    DATETIME,
    NUMBER,
    ROWID,
    STRING,
    Binary,
    Date,
    DateFromTicks,
    Time,
    TimeFromTicks,
    Timestamp,
    TimestampFromTicks,
)

if TYPE_CHECKING:
    from .connection import Connection

__version__ = "0.2.0"

apilevel = "2.0"
threadsafety = 1
paramstyle = "qmark"


def connect(
    host: str = "localhost",
    port: int = 8629,
    database: str = "",
    user: str = "tibero",
    password: str = "",
    dsn: str | None = None,
    driver: str = "Tibero 7 ODBC Driver",
    backend: str = "pyodbc",
    tbcli_library: str | None = None,
    autocommit: bool = False,
    login_timeout: int | None = None,
    **kwargs: object,
) -> Connection:
    """Create a Tibero connection object."""
    from .connection import Connection

    return Connection(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        dsn=dsn,
        driver=driver,
        backend=backend,
        tbcli_library=tbcli_library,
        autocommit=autocommit,
        login_timeout=login_timeout,
        **kwargs,
    )


__all__ = [
    "BINARY",
    "DATETIME",
    "NUMBER",
    "ROWID",
    "STRING",
    "Binary",
    "DataError",
    "DatabaseError",
    "Date",
    "DateFromTicks",
    "Error",
    "IntegrityError",
    "InterfaceError",
    "InternalError",
    "NotSupportedError",
    "OperationalError",
    "ProgrammingError",
    "Time",
    "TimeFromTicks",
    "Timestamp",
    "TimestampFromTicks",
    "Warning",
    "__version__",
    "apilevel",
    "connect",
    "paramstyle",
    "threadsafety",
]
