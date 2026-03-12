"""PEP 249 type objects and constructors for pytibero."""

from __future__ import annotations

import datetime


class DBAPIType:
    """DB-API 2.0 type object.

    The integer codes are provisional placeholders until Tibero metadata mapping
    is implemented in the transport backend.
    """

    def __init__(self, name: str, values: frozenset[int]) -> None:
        self.name = name
        self.values = values

    def __eq__(self, other: object) -> bool:
        if isinstance(other, int):
            return other in self.values
        if isinstance(other, DBAPIType):
            return self.values == other.values
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self) -> int:
        return hash(self.values)

    def __repr__(self) -> str:
        return f"DBAPIType({self.name!r})"


STRING = DBAPIType("STRING", frozenset({1, 12, 13}))
BINARY = DBAPIType("BINARY", frozenset({2, 14}))
NUMBER = DBAPIType("NUMBER", frozenset({3, 4, 5, 6, 7}))
DATETIME = DBAPIType("DATETIME", frozenset({8, 9, 10, 11}))
ROWID = DBAPIType("ROWID", frozenset({15}))


def Date(year: int, month: int, day: int) -> datetime.date:
    """Construct a date value."""
    return datetime.date(year, month, day)


def Time(hour: int, minute: int, second: int) -> datetime.time:
    """Construct a time value."""
    return datetime.time(hour, minute, second)


def Timestamp(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    second: int,
) -> datetime.datetime:
    """Construct a datetime value."""
    return datetime.datetime(year, month, day, hour, minute, second)


def DateFromTicks(ticks: float) -> datetime.date:
    """Construct a date value from Unix ticks."""
    return datetime.date.fromtimestamp(ticks)


def TimeFromTicks(ticks: float) -> datetime.time:
    """Construct a time value from Unix ticks."""
    return datetime.datetime.fromtimestamp(ticks).time()


def TimestampFromTicks(ticks: float) -> datetime.datetime:
    """Construct a datetime value from Unix ticks."""
    return datetime.datetime.fromtimestamp(ticks)


def Binary(value: bytes | bytearray | str) -> bytes:
    """Construct a binary value."""
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        return value.encode("utf-8")
    msg = f"Binary() argument must be bytes, bytearray, or str, not {type(value).__name__}"
    raise TypeError(msg)

