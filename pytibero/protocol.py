"""ODBC connection-string helpers for pytibero."""

from __future__ import annotations

from .config import ConnectionConfig


def build_connection_string(config: ConnectionConfig) -> str:
    """Build a Tibero ODBC connection string from connection settings."""
    attributes: list[tuple[str, str]] = []

    if config.dsn:
        attributes.append(("DSN", config.dsn))
    else:
        attributes.append(("DRIVER", config.driver))
        attributes.append(("SERVER", config.host))
        attributes.append(("PORT", str(config.port)))
        if config.database:
            attributes.append(("DB", config.database))

    if config.user:
        attributes.append(("UID", config.user))
    if config.password:
        attributes.append(("PWD", config.password))

    for key, value in config.options.items():
        if value is None:
            continue
        attributes.append((str(key), _stringify_option(value)))

    parts: list[str] = []
    for key, value in attributes:
        parts.append(f"{key}={_escape_value(value, force_braces=key.upper() == 'DRIVER')}")
    return ";".join(parts) + ";"


def _stringify_option(value: object) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def _escape_value(value: str, force_braces: bool = False) -> str:
    if not value:
        return value
    if force_braces or any(char in value for char in ";{} ") or value != value.strip():
        return "{" + value.replace("}", "}}") + "}"
    return value
