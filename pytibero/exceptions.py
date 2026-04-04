"""PEP 249 exception hierarchy for pytibero."""

from __future__ import annotations


class Warning(Exception):
    """Exception raised for important warnings."""

    def __init__(self, msg: str = "", code: int = 0) -> None:
        self.msg = msg
        self.code = code
        super().__init__(msg)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.msg!r})"


class Error(Exception):
    """Base class for all pytibero errors."""

    def __init__(self, msg: str = "", code: int = 0) -> None:
        self.msg = msg
        self.code = code
        super().__init__(msg)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.msg!r})"


class InterfaceError(Error):
    """Raised for database interface usage errors."""


class DatabaseError(Error):
    """Raised for database-side failures."""

    def __init__(
        self,
        msg: str = "",
        code: int = 0,
        errno: int | None = None,
        sqlstate: str | None = None,
    ) -> None:
        super().__init__(msg, code)
        self.errno = errno
        self.sqlstate = sqlstate

    def __repr__(self) -> str:
        parts = [repr(self.msg)]
        if self.errno is not None:
            parts.append(f"errno={self.errno}")
        if self.sqlstate is not None:
            parts.append(f"sqlstate={self.sqlstate!r}")
        return f"{self.__class__.__name__}({', '.join(parts)})"


class DataError(DatabaseError):
    """Raised for problems with processed data."""


class OperationalError(DatabaseError):
    """Raised for operational database errors."""


class IntegrityError(DatabaseError):
    """Raised when relational integrity is affected."""


class InternalError(DatabaseError):
    """Raised when the database reports an internal error."""


class ProgrammingError(DatabaseError):
    """Raised for invalid SQL or API usage."""


class NotSupportedError(DatabaseError):
    """Raised when a requested API surface is not implemented or supported."""
