"""tbCLI-backed native Tibero transport."""

from __future__ import annotations

import ctypes
import ctypes.util
import datetime as _datetime
import decimal as _decimal
from dataclasses import dataclass
from typing import Any

from .config import ConnectionConfig
from .exceptions import DataError, InterfaceError, OperationalError, ProgrammingError
from .types import DATETIME, NUMBER, ROWID, STRING

SQL_SUCCESS = 0
SQL_SUCCESS_WITH_INFO = 1
SQL_NO_DATA = 100
SQL_NTS = -3

SQL_HANDLE_ENV = 1
SQL_HANDLE_DBC = 2
SQL_HANDLE_STMT = 3

SQL_COMMIT = 0
SQL_ROLLBACK = 1

SQL_PARAM_INPUT = 1

SQL_ATTR_ODBC_VERSION = 200
SQL_OV_ODBC3 = 3
SQL_ATTR_AUTOCOMMIT = 102
SQL_ATTR_LOGIN_TIMEOUT = 103
SQL_AUTOCOMMIT_OFF = 0
SQL_AUTOCOMMIT_ON = 1

SQL_CHAR = 1
SQL_NUMERIC = 2
SQL_DECIMAL = 3
SQL_INTEGER = 4
SQL_SMALLINT = 5
SQL_FLOAT = 6
SQL_REAL = 7
SQL_DOUBLE = 8
SQL_VARCHAR = 12
SQL_TYPE_DATE = 91
SQL_TYPE_TIME = 92
SQL_TYPE_TIMESTAMP = 93
SQL_BIGINT = -5
SQL_BINARY = -2
SQL_VARBINARY = -3
SQL_LONGVARBINARY = -4

SQL_C_CHAR = 1
SQL_C_DOUBLE = 8
SQL_C_DATE = 91
SQL_C_TIME = 92
SQL_C_TIMESTAMP = 93
SQL_C_BINARY = -2
SQL_C_SBIGINT = -25

SQL_NULL_DATA = -1

DescriptionItem = tuple[str, int, None, None, None, None, bool | None]


@dataclass(slots=True)
class _Binding:
    c_type: int
    sql_type: int
    value_ptr: Any
    buffer_length: int
    indicator: ctypes.c_ssize_t
    keepalive: object


class CtypesTbcliDriver:
    def __init__(self, library: Any) -> None:
        self._lib = library

    @classmethod
    def load(cls, library_path: str | None = None) -> CtypesTbcliDriver:
        candidates = [
            candidate
            for candidate in (library_path, ctypes.util.find_library("tbcli"), "libtbcli.so")
            if candidate
        ]
        last_error: OSError | None = None
        for candidate in candidates:
            try:
                return cls(ctypes.CDLL(candidate))
            except OSError as exc:
                last_error = exc
        detail = "" if last_error is None else f": {last_error}"
        raise InterfaceError(f"tbcli library could not be loaded{detail}")

    def connect(self, config: ConnectionConfig) -> TbcliConnection:
        return TbcliConnection(self, config)

    def _check_rc(
        self, rc: int, handle_type: int, handle: ctypes.c_void_p, *, default_message: str
    ) -> None:
        if rc in (SQL_SUCCESS, SQL_SUCCESS_WITH_INFO):
            return
        if rc == SQL_NO_DATA:
            raise OperationalError(default_message, sqlstate="02000")
        sqlstate, errno, message = self._get_diag_record(handle_type, handle)
        raise OperationalError(
            message or default_message, code=errno or 0, errno=errno, sqlstate=sqlstate
        )

    def _get_diag_record(
        self, handle_type: int, handle: ctypes.c_void_p
    ) -> tuple[str | None, int | None, str]:
        state = ctypes.create_string_buffer(6)
        native = ctypes.c_int()
        message = ctypes.create_string_buffer(1024)
        message_len = ctypes.c_short()
        func = getattr(self._lib, "SQLGetDiagRec", None)
        if func is None:
            return None, None, ""
        rc = func(
            handle_type,
            handle,
            1,
            state,
            ctypes.byref(native),
            message,
            len(message),
            ctypes.byref(message_len),
        )
        if rc not in (SQL_SUCCESS, SQL_SUCCESS_WITH_INFO):
            return None, None, ""
        text = message.value.decode("utf-8", errors="replace")
        return state.value.decode("ascii", errors="ignore") or None, int(native.value), text

    def _alloc_handle(self, handle_type: int, parent: ctypes.c_void_p | None) -> ctypes.c_void_p:
        handle = ctypes.c_void_p()
        rc = self._lib.SQLAllocHandle(handle_type, parent, ctypes.byref(handle))
        parent_handle = parent if parent is not None else ctypes.c_void_p()
        self._check_rc(
            rc, handle_type, parent_handle, default_message="failed to allocate tbcli handle"
        )
        return handle

    def _free_handle(self, handle_type: int, handle: ctypes.c_void_p | None) -> None:
        if handle is None or not handle.value:
            return
        self._lib.SQLFreeHandle(handle_type, handle)


class TbcliConnection:
    def __init__(self, driver: CtypesTbcliDriver, config: ConnectionConfig) -> None:
        self._driver = driver
        self._config = config
        self._env = driver._alloc_handle(SQL_HANDLE_ENV, None)
        self._dbc = driver._alloc_handle(SQL_HANDLE_DBC, self._env)
        self._closed = False
        self._autocommit = True
        self._configure_environment()
        self._connect()
        self.autocommit = config.autocommit

    @property
    def autocommit(self) -> bool:
        return self._autocommit

    @autocommit.setter
    def autocommit(self, value: bool) -> None:
        enabled = bool(value)
        attr_value = SQL_AUTOCOMMIT_ON if enabled else SQL_AUTOCOMMIT_OFF
        rc = self._driver._lib.SQLSetConnectAttr(
            self._dbc,
            SQL_ATTR_AUTOCOMMIT,
            ctypes.c_void_p(attr_value),
            0,
        )
        self._driver._check_rc(
            rc, SQL_HANDLE_DBC, self._dbc, default_message="failed to set autocommit"
        )
        self._autocommit = enabled

    def _configure_environment(self) -> None:
        rc = self._driver._lib.SQLSetEnvAttr(
            self._env,
            SQL_ATTR_ODBC_VERSION,
            ctypes.c_void_p(SQL_OV_ODBC3),
            0,
        )
        self._driver._check_rc(
            rc, SQL_HANDLE_ENV, self._env, default_message="failed to initialize tbcli environment"
        )
        if self._config.login_timeout is not None:
            rc = self._driver._lib.SQLSetConnectAttr(
                self._dbc,
                SQL_ATTR_LOGIN_TIMEOUT,
                ctypes.c_void_p(int(self._config.login_timeout)),
                0,
            )
            self._driver._check_rc(
                rc, SQL_HANDLE_DBC, self._dbc, default_message="failed to set login timeout"
            )

    def _connect(self) -> None:
        user = self._config.user.encode("utf-8")
        password = self._config.password.encode("utf-8")
        if self._config.dsn:
            dsn = self._config.dsn.encode("utf-8")
            rc = self._driver._lib.SQLConnect(
                self._dbc,
                ctypes.c_char_p(dsn),
                SQL_NTS,
                ctypes.c_char_p(user),
                SQL_NTS,
                ctypes.c_char_p(password),
                SQL_NTS,
            )
        else:
            from .protocol import build_connection_string

            connection_string = build_connection_string(self._config).encode("utf-8")
            out_length = ctypes.c_short()
            rc = self._driver._lib.SQLDriverConnect(
                self._dbc,
                None,
                ctypes.c_char_p(connection_string),
                SQL_NTS,
                None,
                0,
                ctypes.byref(out_length),
                0,
            )
        self._driver._check_rc(
            rc, SQL_HANDLE_DBC, self._dbc, default_message="failed to connect via tbcli"
        )

    def cursor(self) -> TbcliCursor:
        self._ensure_open()
        stmt = self._driver._alloc_handle(SQL_HANDLE_STMT, self._dbc)
        return TbcliCursor(self, self._driver, stmt)

    def commit(self) -> None:
        self._ensure_open()
        rc = self._driver._lib.SQLEndTran(SQL_HANDLE_DBC, self._dbc, SQL_COMMIT)
        self._driver._check_rc(rc, SQL_HANDLE_DBC, self._dbc, default_message="tbcli commit failed")

    def rollback(self) -> None:
        self._ensure_open()
        rc = self._driver._lib.SQLEndTran(SQL_HANDLE_DBC, self._dbc, SQL_ROLLBACK)
        self._driver._check_rc(
            rc, SQL_HANDLE_DBC, self._dbc, default_message="tbcli rollback failed"
        )

    def getinfo(self, code: int) -> object:
        self._ensure_open()
        buffer = ctypes.create_string_buffer(512)
        length = ctypes.c_short()
        rc = self._driver._lib.SQLGetInfo(
            self._dbc, int(code), buffer, len(buffer), ctypes.byref(length)
        )
        self._driver._check_rc(
            rc, SQL_HANDLE_DBC, self._dbc, default_message="tbcli getinfo failed"
        )
        raw = bytes(buffer[: max(int(length.value), 0)])
        if not raw:
            return ""
        return raw.rstrip(b"\x00").decode("utf-8", errors="replace")

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._driver._lib.SQLDisconnect(self._dbc)
        finally:
            self._driver._free_handle(SQL_HANDLE_DBC, self._dbc)
            self._driver._free_handle(SQL_HANDLE_ENV, self._env)
            self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise InterfaceError("connection is closed")


class TbcliCursor:
    def __init__(
        self, connection: TbcliConnection, driver: CtypesTbcliDriver, statement: ctypes.c_void_p
    ) -> None:
        self.connection = connection
        self._driver = driver
        self._statement = statement
        self._closed = False
        self.description: tuple[DescriptionItem, ...] | None = None
        self.rowcount = -1
        self.arraysize = 1
        self.lastrowid = None
        self._rows: list[tuple[Any, ...]] = []
        self._bindings: list[_Binding] = []

    def close(self) -> None:
        if self._closed:
            return
        self._driver._free_handle(SQL_HANDLE_STMT, self._statement)
        self._closed = True

    def execute(self, operation: str, *params: object) -> TbcliCursor:
        self._ensure_open()
        self._rows.clear()
        self._bindings.clear()
        sql = operation.encode("utf-8")
        if params:
            rc = self._driver._lib.SQLPrepare(self._statement, ctypes.c_char_p(sql), SQL_NTS)
            self._driver._check_rc(
                rc, SQL_HANDLE_STMT, self._statement, default_message="tbcli prepare failed"
            )
            self._bind_parameters(params)
            rc = self._driver._lib.SQLExecute(self._statement)
            self._driver._check_rc(
                rc, SQL_HANDLE_STMT, self._statement, default_message="tbcli execute failed"
            )
        else:
            rc = self._driver._lib.SQLExecDirect(self._statement, ctypes.c_char_p(sql), SQL_NTS)
            self._driver._check_rc(
                rc, SQL_HANDLE_STMT, self._statement, default_message="tbcli execute failed"
            )
        self._refresh_metadata()
        return self

    def executemany(self, operation: str, rows: list[tuple[object, ...]]) -> TbcliCursor:
        self._ensure_open()
        total = 0
        for row in rows:
            self.execute(operation, *row)
            if self.rowcount > 0:
                total += self.rowcount
        self.rowcount = total
        return self

    def fetchone(self) -> tuple[Any, ...] | None:
        self._ensure_open()
        if self.description is None:
            return None
        rc = self._driver._lib.SQLFetch(self._statement)
        if rc == SQL_NO_DATA:
            return None
        self._driver._check_rc(
            rc, SQL_HANDLE_STMT, self._statement, default_message="tbcli fetch failed"
        )
        return tuple(
            self._get_data(index + 1, item[1]) for index, item in enumerate(self.description)
        )

    def fetchmany(self, size: int) -> list[tuple[Any, ...]]:
        rows: list[tuple[Any, ...]] = []
        for _ in range(size):
            row = self.fetchone()
            if row is None:
                break
            rows.append(row)
        return rows

    def fetchall(self) -> list[tuple[Any, ...]]:
        rows: list[tuple[Any, ...]] = []
        while True:
            row = self.fetchone()
            if row is None:
                return rows
            rows.append(row)

    def _bind_parameters(self, params: tuple[object, ...]) -> None:
        for index, value in enumerate(params, start=1):
            binding = _make_binding(value)
            self._bindings.append(binding)
            rc = self._driver._lib.SQLBindParameter(
                self._statement,
                index,
                SQL_PARAM_INPUT,
                binding.c_type,
                binding.sql_type,
                0,
                0,
                binding.value_ptr,
                binding.buffer_length,
                ctypes.byref(binding.indicator),
            )
            self._driver._check_rc(
                rc, SQL_HANDLE_STMT, self._statement, default_message="tbcli bind failed"
            )

    def _refresh_metadata(self) -> None:
        rowcount = ctypes.c_longlong()
        rc = self._driver._lib.SQLRowCount(self._statement, ctypes.byref(rowcount))
        self._driver._check_rc(
            rc, SQL_HANDLE_STMT, self._statement, default_message="tbcli rowcount failed"
        )
        self.rowcount = int(rowcount.value)

        column_count = ctypes.c_short()
        rc = self._driver._lib.SQLNumResultCols(self._statement, ctypes.byref(column_count))
        self._driver._check_rc(
            rc, SQL_HANDLE_STMT, self._statement, default_message="tbcli metadata failed"
        )
        if column_count.value <= 0:
            self.description = None
            return

        description: list[DescriptionItem] = []
        for index in range(1, int(column_count.value) + 1):
            name = ctypes.create_string_buffer(256)
            name_len = ctypes.c_short()
            data_type = ctypes.c_short()
            column_size = ctypes.c_longlong()
            decimal_digits = ctypes.c_short()
            nullable = ctypes.c_short()
            rc = self._driver._lib.SQLDescribeCol(
                self._statement,
                index,
                name,
                len(name),
                ctypes.byref(name_len),
                ctypes.byref(data_type),
                ctypes.byref(column_size),
                ctypes.byref(decimal_digits),
                ctypes.byref(nullable),
            )
            self._driver._check_rc(
                rc, SQL_HANDLE_STMT, self._statement, default_message="tbcli describe column failed"
            )
            description.append(
                (
                    name.value.decode("utf-8", errors="replace"),
                    int(data_type.value),
                    None,
                    None,
                    None,
                    None,
                    None if nullable.value < 0 else bool(nullable.value),
                )
            )
        self.description = tuple(description)

    def _get_data(self, column_index: int, sql_type: int) -> object:
        if sql_type in {SQL_BINARY, SQL_VARBINARY, SQL_LONGVARBINARY}:
            binary_chunks: list[bytes] = []
            while True:
                buffer = ctypes.create_string_buffer(4096)
                indicator = ctypes.c_ssize_t()
                rc = self._driver._lib.SQLGetData(
                    self._statement,
                    column_index,
                    SQL_C_BINARY,
                    buffer,
                    len(buffer),
                    ctypes.byref(indicator),
                )
                if rc == SQL_NO_DATA or indicator.value == SQL_NULL_DATA:
                    return None if not binary_chunks else b"".join(binary_chunks)
                self._driver._check_rc(
                    rc, SQL_HANDLE_STMT, self._statement, default_message="tbcli getdata failed"
                )
                chunk_length = (
                    len(buffer) if rc == SQL_SUCCESS_WITH_INFO else max(int(indicator.value), 0)
                )
                binary_chunks.append(bytes(buffer[:chunk_length]))
                if rc != SQL_SUCCESS_WITH_INFO:
                    return b"".join(binary_chunks)

        text_chunks: list[str] = []
        while True:
            buffer = ctypes.create_string_buffer(4096)
            indicator = ctypes.c_ssize_t()
            rc = self._driver._lib.SQLGetData(
                self._statement,
                column_index,
                SQL_C_CHAR,
                buffer,
                len(buffer),
                ctypes.byref(indicator),
            )
            if rc == SQL_NO_DATA or indicator.value == SQL_NULL_DATA:
                return (
                    None if not text_chunks else _convert_text_value("".join(text_chunks), sql_type)
                )
            self._driver._check_rc(
                rc, SQL_HANDLE_STMT, self._statement, default_message="tbcli getdata failed"
            )
            text_chunks.append(buffer.value.decode("utf-8", errors="replace"))
            if rc != SQL_SUCCESS_WITH_INFO:
                return _convert_text_value("".join(text_chunks), sql_type)

    def _ensure_open(self) -> None:
        if self._closed:
            raise InterfaceError("cursor is closed")
        self.connection._ensure_open()


def load_tbcli_driver(library_path: str | None = None) -> CtypesTbcliDriver:
    return CtypesTbcliDriver.load(library_path)


def _make_binding(value: object) -> _Binding:
    if value is None:
        buffer = ctypes.create_string_buffer(1)
        return _Binding(SQL_C_CHAR, SQL_VARCHAR, buffer, 0, ctypes.c_ssize_t(SQL_NULL_DATA), buffer)
    if isinstance(value, bool):
        number = ctypes.c_longlong(int(value))
        return _Binding(
            SQL_C_SBIGINT,
            SQL_BIGINT,
            ctypes.byref(number),
            ctypes.sizeof(number),
            ctypes.c_ssize_t(ctypes.sizeof(number)),
            number,
        )
    if isinstance(value, int):
        number = ctypes.c_longlong(value)
        return _Binding(
            SQL_C_SBIGINT,
            SQL_BIGINT,
            ctypes.byref(number),
            ctypes.sizeof(number),
            ctypes.c_ssize_t(ctypes.sizeof(number)),
            number,
        )
    if isinstance(value, float):
        number = ctypes.c_double(value)
        return _Binding(
            SQL_C_DOUBLE,
            SQL_DOUBLE,
            ctypes.byref(number),
            ctypes.sizeof(number),
            ctypes.c_ssize_t(ctypes.sizeof(number)),
            number,
        )
    if isinstance(value, _decimal.Decimal):
        encoded = str(value).encode("utf-8")
        buffer = ctypes.create_string_buffer(encoded)
        return _Binding(
            SQL_C_CHAR, SQL_NUMERIC, buffer, len(encoded), ctypes.c_ssize_t(len(encoded)), buffer
        )
    if isinstance(value, str):
        encoded = str(value).encode("utf-8")
        buffer = ctypes.create_string_buffer(encoded)
        return _Binding(
            SQL_C_CHAR, SQL_VARCHAR, buffer, len(encoded), ctypes.c_ssize_t(len(encoded)), buffer
        )
    if isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
        buffer = ctypes.create_string_buffer(raw)
        return _Binding(
            SQL_C_BINARY, SQL_VARBINARY, buffer, len(raw), ctypes.c_ssize_t(len(raw)), buffer
        )
    if isinstance(value, _datetime.datetime):
        encoded = value.isoformat(sep=" ").encode("utf-8")
        buffer = ctypes.create_string_buffer(encoded)
        return _Binding(
            SQL_C_CHAR,
            SQL_TYPE_TIMESTAMP,
            buffer,
            len(encoded),
            ctypes.c_ssize_t(len(encoded)),
            buffer,
        )
    if isinstance(value, _datetime.date):
        encoded = value.isoformat().encode("utf-8")
        buffer = ctypes.create_string_buffer(encoded)
        return _Binding(
            SQL_C_CHAR, SQL_TYPE_DATE, buffer, len(encoded), ctypes.c_ssize_t(len(encoded)), buffer
        )
    if isinstance(value, _datetime.time):
        encoded = value.isoformat().encode("utf-8")
        buffer = ctypes.create_string_buffer(encoded)
        return _Binding(
            SQL_C_CHAR, SQL_TYPE_TIME, buffer, len(encoded), ctypes.c_ssize_t(len(encoded)), buffer
        )
    raise ProgrammingError(f"unsupported tbcli parameter type: {type(value).__name__}")


def _convert_text_value(text: str, sql_type: int) -> object:
    if sql_type in NUMBER.values or sql_type in {SQL_SMALLINT, SQL_INTEGER, SQL_BIGINT}:
        try:
            return int(text)
        except ValueError:
            return _decimal.Decimal(text)
    if sql_type in {SQL_FLOAT, SQL_REAL, SQL_DOUBLE}:
        return float(text)
    if (
        sql_type in DATETIME.values
        or sql_type == SQL_TYPE_DATE
        or sql_type == SQL_TYPE_TIME
        or sql_type == SQL_TYPE_TIMESTAMP
    ):
        return _parse_datetime_value(text, sql_type)
    if sql_type in STRING.values or sql_type in ROWID.values:
        return text
    return text


def _parse_datetime_value(text: str, sql_type: int) -> object:
    if sql_type == SQL_TYPE_DATE:
        return _datetime.date.fromisoformat(text)
    if sql_type == SQL_TYPE_TIME:
        return _datetime.time.fromisoformat(text)
    if sql_type == SQL_TYPE_TIMESTAMP:
        return _datetime.datetime.fromisoformat(text.replace("T", " "))
    raise DataError(f"unsupported tbcli datetime type: {sql_type}")
