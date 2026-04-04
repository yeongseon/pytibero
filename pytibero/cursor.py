"""PEP 249 cursor implementation for pytibero."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .exceptions import InterfaceError, NotSupportedError, ProgrammingError

DescriptionItem = tuple[str, int, None, None, None, None, bool | None]


class Cursor:
    """Cursor object implementing the DB-API surface."""

    def __init__(self, connection: Any, native_cursor: object) -> None:
        self._connection = connection
        self._native = native_cursor
        self._closed = False
        self._rownumber: int | None = None

    @property
    def connection(self) -> object:
        self._ensure_ready()
        return self._connection

    @property
    def description(self) -> tuple[DescriptionItem, ...] | None:
        self._ensure_ready()
        return self._native.description

    @property
    def rowcount(self) -> int:
        self._ensure_ready()
        return int(self._native.rowcount)

    @property
    def arraysize(self) -> int:
        self._ensure_ready()
        return int(getattr(self._native, "arraysize", 1))

    @arraysize.setter
    def arraysize(self, value: int) -> None:
        self._ensure_ready()
        if value < 1:
            raise ProgrammingError("arraysize must be greater than zero")
        self._native.arraysize = value

    @property
    def rownumber(self) -> int | None:
        self._ensure_ready()
        return self._rownumber

    @property
    def lastrowid(self) -> object | None:
        self._ensure_ready()
        return getattr(self._native, "lastrowid", None)

    @property
    def native_cursor(self) -> object:
        self._ensure_ready()
        return self._native

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._native.close()
        except Exception as exc:
            self._connection._reraise_backend_error(exc)
        finally:
            self._connection._cursors.discard(self)
            self._closed = True

    def execute(
        self,
        operation: str,
        parameters: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> Cursor:
        self._ensure_ready()
        bound_parameters = _normalize_parameters(parameters)
        try:
            self._native.execute(operation, *bound_parameters)
        except Exception as exc:
            self._connection._reraise_backend_error(exc)
        self._sync_rownumber_after_execute()
        return self

    def executemany(
        self,
        operation: str,
        seq_of_parameters: Sequence[Sequence[Any] | Mapping[str, Any]],
    ) -> Cursor:
        self._ensure_ready()
        rows = [_normalize_parameters(parameters) for parameters in seq_of_parameters]
        try:
            self._native.executemany(operation, rows)
        except Exception as exc:
            self._connection._reraise_backend_error(exc)
        self._sync_rownumber_after_execute()
        return self

    def fetchone(self) -> tuple[Any, ...] | None:
        self._ensure_ready()
        try:
            row = self._native.fetchone()
        except Exception as exc:
            self._connection._reraise_backend_error(exc)
        if row is None:
            return None
        if self._rownumber is None:
            self._rownumber = 1
        else:
            self._rownumber += 1
        return tuple(row)

    def fetchmany(self, size: int | None = None) -> list[tuple[Any, ...]]:
        self._ensure_ready()
        fetch_size = self.arraysize if size is None else size
        try:
            rows = self._native.fetchmany(fetch_size)
        except Exception as exc:
            self._connection._reraise_backend_error(exc)
        converted_rows = [tuple(row) for row in rows]
        self._advance_rownumber(len(converted_rows))
        return converted_rows

    def fetchall(self) -> list[tuple[Any, ...]]:
        self._ensure_ready()
        try:
            rows = self._native.fetchall()
        except Exception as exc:
            self._connection._reraise_backend_error(exc)
        converted_rows = [tuple(row) for row in rows]
        self._advance_rownumber(len(converted_rows))
        return converted_rows

    def setinputsizes(self, sizes: Any) -> None:
        _ = sizes

    def setoutputsize(self, size: int, column: int | None = None) -> None:
        _ = (size, column)

    def callproc(self, procname: str, parameters: Sequence[Any] = ()) -> Sequence[Any]:
        placeholders = ", ".join("?" for _ in parameters)
        sql = f"CALL {procname}({placeholders})" if placeholders else f"CALL {procname}()"
        self.execute(sql, parameters)
        return parameters

    def nextset(self) -> None:
        self._ensure_ready()
        nextset = getattr(self._native, "nextset", None)
        if nextset is None:
            return None
        try:
            result = nextset()
        except Exception as exc:
            self._connection._reraise_backend_error(exc)
        self._sync_rownumber_after_execute()
        return result

    def scroll(self, value: int, mode: str = "relative") -> None:
        self._ensure_ready()
        native_scroll = getattr(self._native, "scroll", None)
        if native_scroll is None:
            raise NotSupportedError("scroll is not supported by the active cursor")
        try:
            native_scroll(value, mode=mode)
        except Exception as exc:
            self._connection._reraise_backend_error(exc)
        self._update_rownumber_after_scroll(value, mode)

    def __iter__(self) -> Cursor:
        return self

    def __next__(self) -> tuple[Any, ...]:
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row

    def __enter__(self) -> Cursor:
        self._ensure_ready()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        _ = (exc_type, exc, tb)
        self.close()

    def _check_open(self) -> None:
        if self._closed:
            raise InterfaceError("cursor is closed")

    def _ensure_ready(self) -> None:
        self._check_open()
        self._connection._ensure_open()

    def _sync_rownumber_after_execute(self) -> None:
        self._rownumber = 0 if getattr(self._native, "description", None) is not None else None

    def _advance_rownumber(self, rows_read: int) -> None:
        if rows_read == 0:
            return
        if self._rownumber is None:
            self._rownumber = rows_read
        else:
            self._rownumber += rows_read

    def _update_rownumber_after_scroll(self, value: int, mode: str) -> None:
        if mode == "absolute":
            self._rownumber = value
            return
        if mode == "relative":
            base = 0 if self._rownumber is None else self._rownumber
            self._rownumber = base + value


def _normalize_parameters(
    parameters: Sequence[Any] | Mapping[str, Any] | None,
) -> tuple[Any, ...]:
    if parameters is None:
        return ()
    if isinstance(parameters, Mapping):
        raise ProgrammingError("mapping parameters are not supported with qmark paramstyle")
    if isinstance(parameters, Sequence) and not isinstance(parameters, (str, bytes, bytearray)):
        return tuple(parameters)
    return (parameters,)
