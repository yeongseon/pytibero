from __future__ import annotations

from dataclasses import dataclass


class FakePyodbcError(Exception):
    pass


class FakeInterfaceError(FakePyodbcError):
    pass


class FakeDatabaseError(FakePyodbcError):
    pass


class FakeDataError(FakeDatabaseError):
    pass


class FakeOperationalError(FakeDatabaseError):
    pass


class FakeIntegrityError(FakeDatabaseError):
    pass


class FakeInternalError(FakeDatabaseError):
    pass


class FakeProgrammingError(FakeDatabaseError):
    pass


class FakeNotSupportedError(FakeDatabaseError):
    pass


class FakeCursor:
    def __init__(self) -> None:
        self.description = None
        self.rowcount = -1
        self.arraysize = 1
        self.lastrowid = None
        self.scroll_calls: list[tuple[int, str]] = []
        self._rows: list[tuple[object, ...]] = []
        self.closed = False
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.executemany_calls: list[tuple[str, list[tuple[object, ...]]]] = []
        self.nextset_calls = 0

    def execute(self, operation: str, *params: object) -> FakeCursor:
        self.executed.append((operation, params))
        self.description = (("value", 1, None, None, None, None, True),)
        self.rowcount = 2
        self._rows = [(1,), (2,)]
        return self

    def executemany(self, operation: str, rows: list[tuple[object, ...]]) -> FakeCursor:
        self.executemany_calls.append((operation, rows))
        self.rowcount = len(rows)
        return self

    def fetchone(self) -> tuple[object, ...] | None:
        if not self._rows:
            return None
        return self._rows.pop(0)

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        rows = self._rows[:size]
        self._rows = self._rows[size:]
        return rows

    def fetchall(self) -> list[tuple[object, ...]]:
        rows = list(self._rows)
        self._rows.clear()
        return rows

    def nextset(self) -> None:
        self.nextset_calls += 1
        return None

    def scroll(self, value: int, mode: str = "relative") -> None:
        self.scroll_calls.append((value, mode))

    def close(self) -> None:
        self.closed = True


class FailingCursor(FakeCursor):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self._error = error

    def execute(self, operation: str, *params: object) -> FakeCursor:
        _ = (operation, params)
        raise self._error


class FakeNativeConnection:
    def __init__(
        self,
        connection_string: str,
        autocommit: bool = False,
        timeout: int | None = None,
        cursor_factory: type[FakeCursor] = FakeCursor,
        **kwargs: object,
    ) -> None:
        self.connection_string = connection_string
        self.autocommit = autocommit
        self.timeout = timeout
        self.connect_kwargs = dict(kwargs)
        self.closed = False
        self.commit_calls = 0
        self.rollback_calls = 0
        self.cursor_instances: list[FakeCursor] = []
        self.cursor_factory = cursor_factory

    def cursor(self) -> FakeCursor:
        cursor = self.cursor_factory()
        self.cursor_instances.append(cursor)
        return cursor

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.closed = True

    def getinfo(self, code: int) -> str:
        return f"info:{code}"


class ErrorRaisingNativeConnection(FakeNativeConnection):
    def __init__(
        self,
        connection_string: str,
        autocommit: bool = False,
        timeout: int | None = None,
        cursor_factory: type[FakeCursor] = FakeCursor,
        *,
        cursor_error: Exception | None = None,
        commit_error: Exception | None = None,
        rollback_error: Exception | None = None,
        close_error: Exception | None = None,
        autocommit_error: Exception | None = None,
    ) -> None:
        self.cursor_error = cursor_error
        self.commit_error = commit_error
        self.rollback_error = rollback_error
        self.close_error = close_error
        self.autocommit_error = None
        self._autocommit_value = autocommit
        super().__init__(
            connection_string, autocommit=autocommit, timeout=timeout, cursor_factory=cursor_factory
        )
        self.autocommit_error = autocommit_error

    @property
    def autocommit(self) -> bool:
        return self._autocommit_value

    @autocommit.setter
    def autocommit(self, value: bool) -> None:
        if self.autocommit_error is not None:
            raise self.autocommit_error
        self._autocommit_value = value

    def cursor(self) -> FakeCursor:
        if self.cursor_error is not None:
            raise self.cursor_error
        return super().cursor()

    def commit(self) -> None:
        if self.commit_error is not None:
            raise self.commit_error
        super().commit()

    def rollback(self) -> None:
        if self.rollback_error is not None:
            raise self.rollback_error
        super().rollback()

    def close(self) -> None:
        if self.close_error is not None:
            raise self.close_error
        super().close()


class FakePyodbcModule:
    Error = FakePyodbcError
    InterfaceError = FakeInterfaceError
    DatabaseError = FakeDatabaseError
    DataError = FakeDataError
    OperationalError = FakeOperationalError
    IntegrityError = FakeIntegrityError
    InternalError = FakeInternalError
    ProgrammingError = FakeProgrammingError
    NotSupportedError = FakeNotSupportedError

    def __init__(self, cursor_factory: type[FakeCursor] = FakeCursor) -> None:
        self.connections: list[FakeNativeConnection] = []
        self.cursor_factory = cursor_factory

    def connect(self, connection_string: str, **kwargs: object) -> FakeNativeConnection:
        connection = FakeNativeConnection(
            connection_string, cursor_factory=self.cursor_factory, **kwargs
        )
        self.connections.append(connection)
        return connection


@dataclass
class FakeTbcliStatement:
    sql: str | None = None
    prepared_sql: str | None = None
    bound_params: tuple[object, ...] = ()
    rows: list[tuple[object, ...]] | None = None
    description: tuple[tuple[str, int, None, None, None, None, bool | None], ...] | None = None
    rowcount: int = -1
    closed: bool = False


class FakeTbcliConnection:
    def __init__(self, driver: FakeTbcliDriver, config: object) -> None:
        self.driver = driver
        self.config = config
        self.closed = False
        self._autocommit = bool(getattr(config, "autocommit", False))
        self.commit_calls = 0
        self.rollback_calls = 0
        self.statements: list[FakeTbcliStatement] = []

    @property
    def autocommit(self) -> bool:
        return self._autocommit

    @autocommit.setter
    def autocommit(self, value: bool) -> None:
        self.driver.autocommit_updates.append(bool(value))
        self._autocommit = bool(value)

    def cursor(self) -> FakeTbcliCursor:
        statement = FakeTbcliStatement()
        self.statements.append(statement)
        return FakeTbcliCursor(self, statement)

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.closed = True

    def getinfo(self, code: int) -> str:
        self.driver.getinfo_calls.append(code)
        return f"tbcli-info:{code}"


class FakeTbcliCursor:
    def __init__(self, connection: FakeTbcliConnection, statement: FakeTbcliStatement) -> None:
        self.connection = connection
        self.statement = statement
        self.arraysize = 1
        self.lastrowid = None

    @property
    def description(
        self,
    ) -> tuple[tuple[str, int, None, None, None, None, bool | None], ...] | None:
        return self.statement.description

    @property
    def rowcount(self) -> int:
        return self.statement.rowcount

    def execute(self, operation: str, *params: object) -> FakeTbcliCursor:
        self.statement.sql = operation
        self.statement.prepared_sql = operation if params else None
        self.statement.bound_params = tuple(params)
        if operation.upper().startswith("SELECT"):
            self.statement.description = (
                ("id", 4, None, None, None, None, False),
                ("name", 12, None, None, None, None, True),
            )
            self.statement.rows = [(1, "alpha"), (2, "beta")]
            self.statement.rowcount = len(self.statement.rows)
        else:
            self.statement.description = None
            self.statement.rows = []
            self.statement.rowcount = 1
        return self

    def executemany(self, operation: str, rows: list[tuple[object, ...]]) -> FakeTbcliCursor:
        self.statement.sql = operation
        self.statement.bound_params = tuple(rows)
        self.statement.description = None
        self.statement.rows = []
        self.statement.rowcount = len(rows)
        return self

    def fetchone(self) -> tuple[object, ...] | None:
        rows = self.statement.rows or []
        if not rows:
            return None
        return rows.pop(0)

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        rows = self.statement.rows or []
        result = rows[:size]
        self.statement.rows = rows[size:]
        return result

    def fetchall(self) -> list[tuple[object, ...]]:
        rows = list(self.statement.rows or [])
        self.statement.rows = []
        return rows

    def close(self) -> None:
        self.statement.closed = True


class FakeTbcliDriver:
    def __init__(self) -> None:
        self.connections: list[FakeTbcliConnection] = []
        self.getinfo_calls: list[int] = []
        self.autocommit_updates: list[bool] = []
        self.connect_modes: list[str] = []

    def connect(self, config: object) -> FakeTbcliConnection:
        self.connect_modes.append("dsn" if getattr(config, "dsn", None) else "driver")
        connection = FakeTbcliConnection(self, config)
        self.connections.append(connection)
        return connection
