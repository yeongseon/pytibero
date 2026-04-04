from __future__ import annotations

import unittest
from unittest.mock import patch

import pytibero
from pytibero.connection import _extract_backend_error_details, _map_backend_error
from pytibero.exceptions import Error, InterfaceError, NotSupportedError, OperationalError

from tests.fakes import (
    ErrorRaisingNativeConnection,
    FakeOperationalError,
    FakePyodbcModule,
    FailingCursor,
)


class ConnectionTestCase(unittest.TestCase):
    def test_unsupported_backend_raises_interface_error(self) -> None:
        with self.assertRaises(InterfaceError):
            pytibero.connect(backend="unsupported")

    def test_connect_routes_pyodbc_connect_kwargs(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            connection = pytibero.connect(
                autocommit=True,
                readonly=True,
                ansi=False,
                ApplicationName="pytibero-tests",
            )

            native = connection.native_connection
            self.assertTrue(connection.autocommit)
            self.assertEqual(native.connect_kwargs, {"readonly": True, "ansi": False})
            self.assertIn("ApplicationName=pytibero-tests", native.connection_string)
            self.assertNotIn("readonly", native.connection_string)
            self.assertNotIn("ansi", native.connection_string)

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

    def test_execute_creates_and_returns_a_cursor(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            connection = pytibero.connect()

            cursor = connection.execute("SELECT ?", (1,))

            self.assertEqual(cursor.native_cursor.executed[-1], ("SELECT ?", (1,)))
            self.assertIs(cursor.connection, connection)

    def test_getinfo_passthrough_is_supported(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            connection = pytibero.connect()

            self.assertEqual(connection.getinfo(7), "info:7")

    def test_native_passthrough_helpers_delegate_and_missing_methods_raise(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        class NativeWithHelpers(fake_pyodbc.connections.__class__):  # type: ignore[misc, valid-type]
            pass

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            connection = pytibero.connect()
            native = connection.native_connection
            native.setencoding = lambda *args, **kwargs: ("setencoding", args, kwargs)
            native.setdecoding = lambda *args, **kwargs: ("setdecoding", args, kwargs)
            native.add_output_converter = lambda *args, **kwargs: ("add", args, kwargs)
            native.clear_output_converters = lambda: "cleared"
            native.remove_output_converter = lambda *args, **kwargs: ("remove", args, kwargs)

            self.assertEqual(connection.setencoding("utf-8"), ("setencoding", ("utf-8",), {}))
            self.assertEqual(
                connection.setdecoding(1, encoding="utf-8"),
                ("setdecoding", (1,), {"encoding": "utf-8"}),
            )
            self.assertEqual(
                connection.add_output_converter(7, object()), ("add", (7, unittest.mock.ANY), {})
            )
            self.assertEqual(connection.clear_output_converters(), "cleared")
            self.assertEqual(connection.remove_output_converter(7), ("remove", (7,), {}))

            del native.clear_output_converters
            with self.assertRaises(NotSupportedError):
                connection.clear_output_converters()

    def test_native_passthrough_helper_errors_are_mapped(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            connection = pytibero.connect()
            connection.native_connection.setencoding = lambda *args, **kwargs: (
                _ for _ in ()
            ).throw(FakeOperationalError("setencoding failed"))

            with self.assertRaises(OperationalError):
                connection.setencoding("utf-8")

    def test_backend_errors_are_mapped(self) -> None:
        fake_pyodbc = FakePyodbcModule(
            cursor_factory=lambda: FailingCursor(FakeOperationalError("down"))
        )

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
            connection._native = ErrorRaisingNativeConnection(
                "dsn", close_error=FakeOperationalError("close failed")
            )

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

    def test_map_backend_error_preserves_database_details(self) -> None:
        class DetailedBackendError(FakeOperationalError):
            def __init__(self) -> None:
                super().__init__("HY000", "[HY000] [Tibero] syntax error", 11023)

        mapped = _map_backend_error(DetailedBackendError(), FakePyodbcModule())

        self.assertIsInstance(mapped, OperationalError)
        self.assertEqual(mapped.sqlstate, "HY000")
        self.assertEqual(mapped.errno, 11023)
        self.assertEqual(mapped.code, 11023)
        self.assertIn("syntax error", mapped.msg)

    def test_extract_backend_error_details_handles_empty_and_blank_messages(self) -> None:
        self.assertEqual(_extract_backend_error_details(Exception()), ("", 0, None, None))

        error = RuntimeError("HY000", "", 9)
        self.assertEqual(_extract_backend_error_details(error), ("9", 9, 9, "HY000"))


if __name__ == "__main__":
    unittest.main()
