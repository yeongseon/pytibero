from __future__ import annotations

import ctypes
import datetime
import decimal
import unittest
from unittest.mock import patch

from pytibero.config import ConnectionConfig
from pytibero.exceptions import DataError, InterfaceError, OperationalError, ProgrammingError
from pytibero.tbcli import (
    CtypesTbcliDriver,
    SQL_HANDLE_DBC,
    SQL_NO_DATA,
    SQL_SUCCESS,
    SQL_TYPE_DATE,
    SQL_TYPE_TIME,
    SQL_TYPE_TIMESTAMP,
    _convert_text_value,
    _make_binding,
    _parse_datetime_value,
    load_tbcli_driver,
)


class TbcliHelpersTestCase(unittest.TestCase):
    def test_load_prefers_explicit_library_and_reports_failure(self) -> None:
        with (
            patch("pytibero.tbcli.ctypes.CDLL", return_value=object()) as cdll,
            patch(
                "pytibero.tbcli.ctypes.util.find_library",
                return_value="libtbcli-discovered.so",
            ),
        ):
            driver = load_tbcli_driver("/opt/tibero/lib/libtbcli.so")

            self.assertIsInstance(driver, CtypesTbcliDriver)
            cdll.assert_called_once_with("/opt/tibero/lib/libtbcli.so")

        with (
            patch("pytibero.tbcli.ctypes.CDLL", side_effect=OSError("missing")),
            patch(
                "pytibero.tbcli.ctypes.util.find_library",
                return_value=None,
            ),
        ):
            with self.assertRaises(InterfaceError):
                load_tbcli_driver()

    def test_check_rc_handles_success_no_data_and_diagnostics(self) -> None:
        class LibWithDiag:
            def SQLGetDiagRec(
                self, handle_type, handle, rec_no, state, native, message, buffer_len, message_len
            ):
                _ = (handle_type, handle, rec_no, buffer_len)
                state.value = b"HY000"
                native._obj.value = 42
                message.value = b"driver error"
                message_len._obj.value = len(message.value)
                return SQL_SUCCESS

        driver = CtypesTbcliDriver(LibWithDiag())
        handle = ctypes.c_void_p(1)

        driver._check_rc(SQL_SUCCESS, SQL_HANDLE_DBC, handle, default_message="ok")

        with self.assertRaises(OperationalError) as no_data:
            driver._check_rc(SQL_NO_DATA, SQL_HANDLE_DBC, handle, default_message="no data")
        self.assertEqual(no_data.exception.sqlstate, "02000")

        with self.assertRaises(OperationalError) as diag:
            driver._check_rc(-1, SQL_HANDLE_DBC, handle, default_message="boom")
        self.assertEqual(diag.exception.sqlstate, "HY000")
        self.assertEqual(diag.exception.errno, 42)
        self.assertEqual(diag.exception.msg, "driver error")

    def test_make_binding_supports_expected_python_types(self) -> None:
        values = [
            None,
            True,
            7,
            1.5,
            decimal.Decimal("2.5"),
            "alpha",
            b"beta",
            bytearray(b"gamma"),
            datetime.date(2026, 4, 2),
            datetime.time(12, 34, 56),
            datetime.datetime(2026, 4, 2, 12, 34, 56),
        ]

        bindings = [_make_binding(value) for value in values]

        self.assertEqual(bindings[0].indicator.value, -1)
        self.assertEqual(bindings[1].keepalive.value, 1)
        self.assertEqual(bindings[2].keepalive.value, 7)
        self.assertAlmostEqual(bindings[3].keepalive.value, 1.5)
        self.assertEqual(bindings[4].keepalive.value, b"2.5")
        self.assertEqual(bindings[5].keepalive.value, b"alpha")
        self.assertEqual(bindings[6].keepalive.raw[:4], b"beta")
        self.assertEqual(bindings[7].keepalive.raw[:5], b"gamma")
        self.assertEqual(bindings[8].keepalive.value, b"2026-04-02")
        self.assertEqual(bindings[9].keepalive.value, b"12:34:56")
        self.assertEqual(bindings[10].keepalive.value, b"2026-04-02 12:34:56")

        with self.assertRaises(ProgrammingError):
            _make_binding(object())

    def test_convert_text_value_and_parse_datetime_cover_supported_shapes(self) -> None:
        self.assertEqual(_convert_text_value("7", 4), 7)
        self.assertEqual(_convert_text_value("2.5", 3), decimal.Decimal("2.5"))
        self.assertEqual(_convert_text_value("1.5", 8), 1.5)
        self.assertEqual(
            _convert_text_value("2026-04-02", SQL_TYPE_DATE), datetime.date(2026, 4, 2)
        )
        self.assertEqual(_convert_text_value("12:34:56", SQL_TYPE_TIME), datetime.time(12, 34, 56))
        self.assertEqual(
            _convert_text_value("2026-04-02 12:34:56", SQL_TYPE_TIMESTAMP),
            datetime.datetime(2026, 4, 2, 12, 34, 56),
        )
        self.assertEqual(_convert_text_value("alpha", 12), "alpha")
        self.assertEqual(
            _parse_datetime_value("2026-04-02T12:34:56", SQL_TYPE_TIMESTAMP),
            datetime.datetime(2026, 4, 2, 12, 34, 56),
        )

        with self.assertRaises(DataError):
            _parse_datetime_value("x", 999)

    def test_connect_builds_tbcli_connection_through_driver(self) -> None:
        class Driver:
            def connect(self, config: ConnectionConfig) -> tuple[str, ConnectionConfig]:
                return ("connected", config)

        config = ConnectionConfig(user="tibero", password="tmax", autocommit=True)
        driver = CtypesTbcliDriver(object())
        driver.connect = Driver().connect  # type: ignore[method-assign]

        tag, returned_config = driver.connect(config)

        self.assertEqual(tag, "connected")
        self.assertIs(returned_config, config)


if __name__ == "__main__":
    unittest.main()
