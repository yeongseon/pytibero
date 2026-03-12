from __future__ import annotations

import unittest
from unittest.mock import patch

import pytibero
from pytibero.connection import Connection
from pytibero.cursor import Cursor
from pytibero.exceptions import InterfaceError, ProgrammingError
from pytibero.config import ConnectionConfig
from pytibero.protocol import build_connection_string
from tests.fakes import FakePyodbcModule


class APITestCase(unittest.TestCase):
    def test_build_connection_string_for_direct_connection(self) -> None:
        config = ConnectionConfig(
            host="localhost",
            port=8629,
            database="sample",
            user="tibero",
            password="tmax",
            dsn=None,
            driver="Tibero 7 ODBC Driver",
            autocommit=False,
            login_timeout=None,
            options={"ApplicationName": "pytibero"},
        )

        value = build_connection_string(config)

        self.assertIn("DRIVER={Tibero 7 ODBC Driver}", value)
        self.assertIn("SERVER=localhost", value)
        self.assertIn("PORT=8629", value)
        self.assertIn("DB=sample", value)
        self.assertIn("UID=tibero", value)
        self.assertIn("PWD=tmax", value)
        self.assertIn("ApplicationName=pytibero", value)

    def test_connect_cursor_execute_and_transactions(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            connection = pytibero.connect(database="sample", password="tmax", login_timeout=3)

            self.assertIsInstance(connection, Connection)
            self.assertFalse(connection.autocommit)
            self.assertEqual(connection.native_connection.timeout, 3)

            cursor = connection.cursor()
            self.assertIsInstance(cursor, Cursor)
            cursor.execute("SELECT ?", [1])
            self.assertEqual(cursor.fetchone(), (1,))
            self.assertEqual(cursor.fetchall(), [(2,)])

            cursor.executemany("INSERT INTO t VALUES (?)", [(1,), (2,)])
            self.assertEqual(cursor.rowcount, 2)

            connection.commit()
            connection.rollback()
            self.assertEqual(connection.native_connection.commit_calls, 1)
            self.assertEqual(connection.native_connection.rollback_calls, 1)

    def test_closed_connection_rejects_cursor_creation(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            connection = pytibero.connect()
            connection.close()

            with self.assertRaises(InterfaceError):
                connection.cursor()

    def test_mapping_parameters_are_rejected(self) -> None:
        fake_pyodbc = FakePyodbcModule()

        with patch("pytibero.connection.import_module", return_value=fake_pyodbc):
            connection = pytibero.connect()
            cursor = connection.cursor()

            with self.assertRaises(ProgrammingError):
                cursor.execute("SELECT ?", {"value": 1})


if __name__ == "__main__":
    unittest.main()
