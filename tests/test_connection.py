from __future__ import annotations

import unittest
from unittest.mock import patch

import pytibero
from pytibero.connection import _map_backend_error
from pytibero.exceptions import Error, InterfaceError, OperationalError

from tests.fakes import (
    ErrorRaisingNativeConnection,
    FakeOperationalError,
    FakePyodbcModule,
    FailingCursor,
)


class ConnectionTestCase(unittest.TestCase):
    def test_missing_pyodbc_raises_interface_error(self) -> None:
        with patch("pytibero.connection.import_module", side_effect=ModuleNotFoundError):
            with self.assertRaises(InterfaceError):
                pytibero.connect()

    def test_autocommit_can_be_toggled(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            connection = pytibero.connect()
            connection.autocommit = True

            self.assertTrue(connection.autocommit)
            self.assertFalse(connection.closed)
            self.assertIs(connection.native_connection, fake_pyodbc.connections[0])

    def test_context_manager_commits_on_success(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            with pytibero.connect() as connection:
                native = connection.native_connection

            self.assertEqual(native.commit_calls, 1)
            self.assertTrue(native.closed)

    def test_context_manager_rolls_back_on_error(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            native = None
            with self.assertRaises(RuntimeError):
                with pytibero.connect() as connection:
                    native = connection.native_connection
                    raise RuntimeError("boom")

            assert native is not None
            self.assertEqual(native.rollback_calls, 1)
            self.assertTrue(native.closed)

    def test_backend_errors_are_mapped(self) -> None:
        fake_pyodbc = FakePyodbcModule(cursor_factory=lambda: FailingCursor(FakeOperationalError("down")))

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            connection = pytibero.connect()
            cursor = connection.cursor()

            with self.assertRaises(OperationalError):
                cursor.execute("SELECT 1")

    def test_autocommit_setter_error_is_mapped(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            connection = pytibero.connect()
            connection._native = ErrorRaisingNativeConnection(
                "dsn",
                autocommit=False,
                autocommit_error=FakeOperationalError("autocommit failed"),
            )

            with self.assertRaises(OperationalError):
                connection.autocommit = True

    def test_cursor_creation_commit_and_rollback_errors_are_mapped(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            connection = pytibero.connect()
            connection._native = ErrorRaisingNativeConnection(
                "dsn",
                cursor_error=FakeOperationalError("cursor failed"),
                commit_error=FakeOperationalError("commit failed"),
                rollback_error=FakeOperationalError("rollback failed"),
            )

            with self.assertRaises(OperationalError):
                connection.cursor()
            with self.assertRaises(OperationalError):
                connection.commit()
            with self.assertRaises(OperationalError):
                connection.rollback()

    def test_close_is_idempotent_and_ignores_cursor_close_errors(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        class BrokenCursor:
            def close(self) -> None:
                raise RuntimeError("broken close")

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            connection = pytibero.connect()
            connection._cursors.add(BrokenCursor())
            connection.close()
            connection.close()

            self.assertTrue(connection.closed)

    def test_close_native_error_is_mapped(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            connection = pytibero.connect()
            connection._native = ErrorRaisingNativeConnection("dsn", close_error=FakeOperationalError("close failed"))

            with self.assertRaises(OperationalError):
                connection.close()

    def test_connect_error_is_mapped(self) -> None:
        class BrokenPyodbc(FakePyodbcModule):
            def connect(self, connection_string: str, **kwargs: object) -> object:
                _ = (connection_string, kwargs)
                raise FakeOperationalError("connect failed")

        with patch("pytibero.connection.import_module", return_value=BrokenPyodbc()):
            with self.assertRaises(OperationalError):
                pytibero.connect()

    def test_map_backend_error_falls_back_to_generic_error(self) -> None:
        mapped = _map_backend_error(RuntimeError("generic"), FakePyodbcModule())

        self.assertIsInstance(mapped, Error)
        self.assertEqual(str(mapped), "generic")


if __name__ == "__main__":
    unittest.main()
