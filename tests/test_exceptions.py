from __future__ import annotations

import unittest

import pytibero


class ExceptionsTestCase(unittest.TestCase):
    def test_pep249_exception_hierarchy(self) -> None:
        self.assertTrue(issubclass(pytibero.Warning, Exception))
        self.assertTrue(issubclass(pytibero.Error, Exception))
        self.assertTrue(issubclass(pytibero.InterfaceError, pytibero.Error))
        self.assertTrue(issubclass(pytibero.DatabaseError, pytibero.Error))
        self.assertTrue(issubclass(pytibero.DataError, pytibero.DatabaseError))
        self.assertTrue(issubclass(pytibero.OperationalError, pytibero.DatabaseError))
        self.assertTrue(issubclass(pytibero.IntegrityError, pytibero.DatabaseError))
        self.assertTrue(issubclass(pytibero.InternalError, pytibero.DatabaseError))
        self.assertTrue(issubclass(pytibero.ProgrammingError, pytibero.DatabaseError))
        self.assertTrue(issubclass(pytibero.NotSupportedError, pytibero.DatabaseError))

    def test_database_error_repr_includes_optional_fields(self) -> None:
        error = pytibero.DatabaseError("boom", errno=7, sqlstate="HY000")

        self.assertEqual(repr(error), "DatabaseError('boom', errno=7, sqlstate='HY000')")

    def test_warning_and_error_repr(self) -> None:
        warning = pytibero.Warning("warn", code=1)
        error = pytibero.Error("err", code=2)

        self.assertEqual(warning.code, 1)
        self.assertEqual(error.code, 2)
        self.assertEqual(repr(warning), "Warning('warn')")
        self.assertEqual(repr(error), "Error('err')")

    def test_database_error_repr_without_optional_fields(self) -> None:
        error = pytibero.DatabaseError("boom")

        self.assertEqual(repr(error), "DatabaseError('boom')")


if __name__ == "__main__":
    unittest.main()
