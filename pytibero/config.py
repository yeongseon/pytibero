"""Configuration primitives for pytibero."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ConnectionConfig:
    """Connection settings accepted by :func:`pytibero.connect`."""

    host: str = "localhost"
    port: int = 8629
    database: str = ""
    user: str = "tibero"
    password: str = ""
    dsn: str | None = None
    driver: str = "Tibero 7 ODBC Driver"
    autocommit: bool = False
    login_timeout: int | None = None
    options: dict[str, object] = field(default_factory=dict)
