from __future__ import annotations

import ctypes
import decimal
import unittest
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

import pytibero
from pytibero import tbcli
from pytibero.exceptions import InterfaceError

from tests.fakes import FakeTbcliDriver


class TbcliBackendTestCase(unittest.TestCase):
    def test_tbcli_backend_supports_connect_execute_fetch_and_transactions(self) -> None:
        fake_tbcli = FakeTbcliDriver()

        with patch("pytibero.connection.load_tbcli_driver", return_value=fake_tbcli):
            connection = pytibero.connect(
                host="localhost",
                port=8629,
                database="sample",
                user="tibero",
                password="tmax",
                backend="tbcli",
            )

            self.assertEqual(fake_tbcli.connect_modes, ["driver"])
            self.assertFalse(connection.autocommit)

            cursor = cast(Any, connection.cursor())
            cursor.execute("SELECT id, name FROM demo WHERE id > ?", 0)

            self.assertEqual(
                cursor.description,
                (
                    ("id", 4, None, None, None, None, False),
                    ("name", 12, None, None, None, None, True),
                ),
            )
            self.assertEqual(cursor.fetchone(), (1, "alpha"))
            self.assertEqual(cursor.fetchall(), [(2, "beta")])

            connection.commit()
            connection.rollback()
            native_connection = cast(Any, connection.native_connection)
            self.assertEqual(native_connection.commit_calls, 1)
            self.assertEqual(native_connection.rollback_calls, 1)
            self.assertEqual(connection.getinfo(17), "tbcli-info:17")

            connection.autocommit = True
            self.assertEqual(fake_tbcli.autocommit_updates, [True])

    def test_tbcli_backend_uses_dsn_connect_mode(self) -> None:
        fake_tbcli = FakeTbcliDriver()

        with patch("pytibero.connection.load_tbcli_driver", return_value=fake_tbcli):
            connection = pytibero.connect(
                dsn="TIBERO_TEST",
                user="tibero",
                password="tmax",
                backend="tbcli",
            )

            self.assertEqual(fake_tbcli.connect_modes, ["dsn"])
            connection.close()
            self.assertTrue(connection.closed)

    def test_tbcli_driver_load_errors_surface_as_interface_errors(self) -> None:
        with patch(
            "pytibero.connection.load_tbcli_driver",
            side_effect=InterfaceError("tbcli is unavailable"),
        ):
            with self.assertRaises(InterfaceError):
                pytibero.connect(backend="tbcli")


class TbcliModuleTestCase(unittest.TestCase):
    def test_make_binding_uses_numeric_sql_type_for_decimal(self) -> None:
        binding = tbcli._make_binding(decimal.Decimal("12.34"))

        self.assertEqual(binding.c_type, tbcli.SQL_C_CHAR)
        self.assertIn(binding.sql_type, {tbcli.SQL_NUMERIC, tbcli.SQL_DECIMAL})
        self.assertEqual(binding.buffer_length, len(b"12.34"))

    def test_get_data_reads_chunked_text_until_complete(self) -> None:
        first_chunk = b"a" * 4095
        second_chunk = b"bcdef"

        class ChunkedTextLib:
            def __init__(self) -> None:
                self.calls = 0
                self.chunks = [
                    (
                        tbcli.SQL_SUCCESS_WITH_INFO,
                        first_chunk,
                        len(first_chunk) + len(second_chunk),
                    ),
                    (tbcli.SQL_SUCCESS, second_chunk, len(second_chunk)),
                ]

            def SQLGetData(self, statement, column_index, c_type, buffer, buffer_length, indicator):
                _ = (statement, column_index, buffer_length)
                rc, chunk, total_length = self.chunks[self.calls]
                self.calls += 1
                self.assertEqual(c_type, tbcli.SQL_C_CHAR)
                buffer.value = chunk
                ctypes.cast(
                    indicator, ctypes.POINTER(ctypes.c_ssize_t)
                ).contents.value = total_length
                return rc

            def assertEqual(self, left: object, right: object) -> None:
                if left != right:
                    raise AssertionError(f"{left!r} != {right!r}")

        cursor = tbcli.TbcliCursor(
            cast(tbcli.TbcliConnection, cast(object, SimpleNamespace(_ensure_open=lambda: None))),
            tbcli.CtypesTbcliDriver(ChunkedTextLib()),
            ctypes.c_void_p(1),
        )

        self.assertEqual(
            cursor._get_data(1, tbcli.SQL_VARCHAR), (first_chunk + second_chunk).decode()
        )

    def test_get_data_reads_chunked_binary_until_complete(self) -> None:
        first_chunk = b"a" * 4096
        second_chunk = b"bcdef"

        class ChunkedBinaryLib:
            def __init__(self) -> None:
                self.calls = 0
                self.chunks = [
                    (
                        tbcli.SQL_SUCCESS_WITH_INFO,
                        first_chunk,
                        len(first_chunk) + len(second_chunk),
                    ),
                    (tbcli.SQL_SUCCESS, second_chunk, len(second_chunk)),
                ]

            def SQLGetData(self, statement, column_index, c_type, buffer, buffer_length, indicator):
                _ = (statement, column_index)
                rc, chunk, reported_length = self.chunks[self.calls]
                self.calls += 1
                self.assertEqual(c_type, tbcli.SQL_C_BINARY)
                ctypes.memmove(buffer, chunk, len(chunk))
                ctypes.cast(indicator, ctypes.POINTER(ctypes.c_ssize_t)).contents.value = (
                    buffer_length if rc == tbcli.SQL_SUCCESS_WITH_INFO else reported_length
                )
                return rc

            def assertEqual(self, left: object, right: object) -> None:
                if left != right:
                    raise AssertionError(f"{left!r} != {right!r}")

        cursor = tbcli.TbcliCursor(
            cast(tbcli.TbcliConnection, cast(object, SimpleNamespace(_ensure_open=lambda: None))),
            tbcli.CtypesTbcliDriver(ChunkedBinaryLib()),
            ctypes.c_void_p(1),
        )

        self.assertEqual(cursor._get_data(1, tbcli.SQL_LONGVARBINARY), first_chunk + second_chunk)


if __name__ == "__main__":
    unittest.main()
