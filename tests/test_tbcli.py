from __future__ import annotations

import unittest
from unittest.mock import patch

import pytibero
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

            cursor = connection.cursor()
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
            self.assertEqual(connection.native_connection.commit_calls, 1)
            self.assertEqual(connection.native_connection.rollback_calls, 1)
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


if __name__ == "__main__":
    unittest.main()
