from __future__ import annotations

import unittest
from unittest.mock import patch

import pytibero
from pytibero.exceptions import InterfaceError, OperationalError, ProgrammingError

from tests.fakes import FakeCursor, FakeOperationalError, FakePyodbcModule


class CursorTestCase(unittest.TestCase):
    def test_arraysize_must_be_positive(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            cursor = pytibero.connect().cursor()

            with self.assertRaises(ProgrammingError):
                cursor.arraysize = 0

    def test_fetchmany_uses_arraysize(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            cursor = pytibero.connect().cursor()
            cursor.execute("SELECT 1")
            cursor.arraysize = 1

            self.assertEqual(cursor.fetchmany(), [(1,)])
            self.assertEqual(cursor.fetchall(), [(2,)])
            self.assertIsNone(cursor.fetchone())

    def test_scalar_parameter_is_bound_as_single_value(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            cursor = pytibero.connect().cursor()
            cursor.execute("SELECT ?", 1)

            self.assertEqual(cursor.native_cursor.executed[-1], ("SELECT ?", (1,)))
            self.assertEqual(cursor.description, (("value", 1, None, None, None, None, True),))
            self.assertEqual(cursor.rowcount, 2)

    def test_lastrowid_and_noop_size_methods(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            cursor = pytibero.connect().cursor()
            cursor.native_cursor.lastrowid = 99

            self.assertEqual(cursor.lastrowid, 99)
            cursor.setinputsizes([1, 2, 3])
            cursor.setoutputsize(10, 1)

    def test_callproc_builds_call_statement(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            cursor = pytibero.connect().cursor()
            cursor.callproc("hello_proc", (1, "a"))

            self.assertEqual(cursor.native_cursor.executed[-1], ("CALL hello_proc(?, ?)", (1, "a")))

    def test_callproc_without_parameters_and_context_manager(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            with pytibero.connect().cursor() as cursor:
                returned = cursor.callproc("hello_proc")
                self.assertEqual(returned, ())
                self.assertEqual(cursor.native_cursor.executed[-1], ("CALL hello_proc()", ()))

            with self.assertRaises(InterfaceError):
                cursor.fetchone()

    def test_nextset_delegates_to_backend(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            cursor = pytibero.connect().cursor()
            cursor.nextset()

            self.assertEqual(cursor.native_cursor.nextset_calls, 1)

    def test_iteration_and_close_are_supported(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            cursor = pytibero.connect().cursor()
            cursor.execute("SELECT 1")

            self.assertEqual(next(iter(cursor)), (1,))
            self.assertEqual(next(cursor), (2,))
            with self.assertRaises(StopIteration):
                next(cursor)

            cursor.close()
            cursor.close()

    def test_backend_errors_from_cursor_methods_are_mapped(self) -> None:
        class MethodFailingCursor(FakeCursor):
            def fetchone(self) -> tuple[object, ...] | None:
                raise FakeOperationalError("fetchone failed")

            def executemany(self, operation: str, rows: list[tuple[object, ...]]) -> FakeCursor:
                _ = (operation, rows)
                raise FakeOperationalError("executemany failed")

            def fetchmany(self, size: int) -> list[tuple[object, ...]]:
                _ = size
                raise FakeOperationalError("fetchmany failed")

            def fetchall(self) -> list[tuple[object, ...]]:
                raise FakeOperationalError("fetchall failed")

            def nextset(self) -> None:
                raise FakeOperationalError("nextset failed")

            def close(self) -> None:
                raise FakeOperationalError("close failed")

        fake_pyodbc = FakePyodbcModule(cursor_factory=MethodFailingCursor)

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            cursor = pytibero.connect().cursor()
            cursor.native_cursor._rows = [(1,)]
            with self.assertRaises(OperationalError):
                cursor.fetchone()
            with self.assertRaises(OperationalError):
                cursor.executemany("INSERT INTO t VALUES (?)", [(1,)])
            with self.assertRaises(OperationalError):
                cursor.fetchmany(1)
            with self.assertRaises(OperationalError):
                cursor.fetchall()
            with self.assertRaises(OperationalError):
                cursor.nextset()
            with self.assertRaises(OperationalError):
                cursor.close()

    def test_nextset_returns_none_when_backend_does_not_support_it(self) -> None:
        class NoNextsetCursor(FakeCursor):
            nextset = None

        fake_pyodbc = FakePyodbcModule(cursor_factory=NoNextsetCursor)

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            cursor = pytibero.connect().cursor()

            self.assertIsNone(cursor.nextset())


if __name__ == "__main__":
    unittest.main()
