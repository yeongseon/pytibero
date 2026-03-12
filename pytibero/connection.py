"""PEP 249 connection implementation for pytibero."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .config import ConnectionConfig
from .exceptions import (
    DataError,
    DatabaseError,
    Error,
    IntegrityError,
    InterfaceError,
    InternalError,
    NotSupportedError,
    OperationalError,
    ProgrammingError,
)
from .protocol import build_connection_string


class Connection:
    """Connection object backed by a pyodbc connection."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        dsn: str | None = None,
        driver: str = "Tibero 7 ODBC Driver",
        autocommit: bool = False,
        login_timeout: int | None = None,
        **kwargs: Any,
    ) -> None:
        self.config = ConnectionConfig(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            dsn=dsn,
            driver=driver,
            autocommit=autocommit,
            login_timeout=login_timeout,
            options=dict(kwargs),
        )
        self._pyodbc = self._load_pyodbc()
        self._native = self._open_native_connection()
        self._closed = False
        self._cursors: set[object] = set()

    @property
    def closed(self) -> bool:
        """Return whether the connection has been closed."""
        return self._closed or self._native is None

    @property
    def autocommit(self) -> bool:
        """Return the autocommit setting."""
        self._ensure_open()
        return bool(self._native.autocommit)

    @autocommit.setter
    def autocommit(self, value: bool) -> None:
        self._ensure_open()
        enabled = bool(value)
        try:
            self._native.autocommit = enabled
            self.config.autocommit = enabled
        except Exception as exc:
            self._reraise_backend_error(exc)

    @property
    def native_connection(self) -> object:
        """Expose the wrapped pyodbc connection."""
        self._ensure_open()
        return self._native

    def cursor(self) -> object:
        """Create a new cursor bound to this connection."""
        self._ensure_open()
        from .cursor import Cursor

        try:
            native_cursor = self._native.cursor()
        except Exception as exc:
            self._reraise_backend_error(exc)
        cursor = Cursor(self, native_cursor)
        self._cursors.add(cursor)
        return cursor

    def commit(self) -> None:
        """Commit the current transaction."""
        self._ensure_open()
        try:
            self._native.commit()
        except Exception as exc:
            self._reraise_backend_error(exc)

    def rollback(self) -> None:
        """Roll back the current transaction."""
        self._ensure_open()
        try:
            self._native.rollback()
        except Exception as exc:
            self._reraise_backend_error(exc)

    def close(self) -> None:
        """Close the connection and any tracked cursors."""
        if self._closed:
            return

        for cursor in list(self._cursors):
            try:
                cursor.close()
            except Exception:
                pass
        self._cursors.clear()
        try:
            if self._native is not None:
                self._native.close()
        except Exception as exc:
            self._reraise_backend_error(exc)
        finally:
            self._native = None
        self._closed = True

    def _ensure_open(self) -> None:
        if self.closed:
            raise InterfaceError("connection is closed")

    def __enter__(self) -> Connection:
        self._ensure_open()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        _ = (exc, tb)
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()

    def _load_pyodbc(self) -> Any:
        try:
            return import_module("pyodbc")
        except ModuleNotFoundError as exc:
            raise InterfaceError(
                "pyodbc is required to use pytibero. Install pyodbc and a Tibero ODBC driver."
            ) from exc

    def _open_native_connection(self) -> object:
        connection_string = build_connection_string(self.config)
        connect_kwargs: dict[str, object] = {"autocommit": self.config.autocommit}
        if self.config.login_timeout is not None:
            connect_kwargs["timeout"] = self.config.login_timeout

        try:
            return self._pyodbc.connect(connection_string, **connect_kwargs)
        except Exception as exc:
            self._reraise_backend_error(exc)

    def _reraise_backend_error(self, error: Exception) -> None:
        raise _map_backend_error(error, self._pyodbc) from error


def _map_backend_error(error: Exception, pyodbc_module: Any) -> Error:
    mappings = [
        ("InterfaceError", InterfaceError),
        ("DataError", DataError),
        ("IntegrityError", IntegrityError),
        ("InternalError", InternalError),
        ("ProgrammingError", ProgrammingError),
        ("NotSupportedError", NotSupportedError),
        ("OperationalError", OperationalError),
        ("DatabaseError", DatabaseError),
        ("Error", Error),
    ]

    for backend_name, local_exc in mappings:
        backend_cls = getattr(pyodbc_module, backend_name, None)
        if backend_cls is not None and isinstance(error, backend_cls):
            return local_exc(str(error))
    return Error(str(error))
