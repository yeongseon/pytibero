from __future__ import annotations

import os
import socket
import time
import unittest
import uuid

import pytibero


@unittest.skipUnless(os.getenv("PYTIBERO_RUN_E2E") == "1", "set PYTIBERO_RUN_E2E=1 to run e2e tests")
class TiberoE2ETestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._wait_for_port(os.environ["PYTIBERO_HOST"], int(os.environ["PYTIBERO_PORT"]))
        cls.connection = pytibero.connect(
            host=os.environ["PYTIBERO_HOST"],
            port=int(os.environ["PYTIBERO_PORT"]),
            database=os.environ.get("PYTIBERO_DATABASE", ""),
            user=os.environ.get("PYTIBERO_USER", "tibero"),
            password=os.environ.get("PYTIBERO_PASSWORD", "tmax"),
            driver=os.environ.get("PYTIBERO_DRIVER", "Tibero 7 ODBC Driver"),
        )
        cls.table_name = f"PYTIBERO_E2E_{uuid.uuid4().hex[:8].upper()}"
        cursor = cls.connection.cursor()
        cursor.execute(f"CREATE TABLE {cls.table_name} (id NUMBER PRIMARY KEY, name VARCHAR(50))")
        cls.connection.commit()

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            cursor = cls.connection.cursor()
            cursor.execute(f"DROP TABLE {cls.table_name}")
            cls.connection.commit()
        finally:
            cls.connection.close()

    def test_insert_and_fetch(self) -> None:
        cursor = self.connection.cursor()
        cursor.execute(f"INSERT INTO {self.table_name} (id, name) VALUES (?, ?)", (1, "alpha"))
        self.connection.commit()

        cursor.execute(f"SELECT id, name FROM {self.table_name} ORDER BY id")
        self.assertEqual(cursor.fetchall(), [(1, "alpha")])

    def test_rollback(self) -> None:
        cursor = self.connection.cursor()
        cursor.execute(f"INSERT INTO {self.table_name} (id, name) VALUES (?, ?)", (2, "beta"))
        self.connection.rollback()

        cursor.execute(f"SELECT COUNT(*) FROM {self.table_name} WHERE id = ?", (2,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 0)

    @staticmethod
    def _wait_for_port(host: str, port: int, timeout: int = 120) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with socket.create_connection((host, port), timeout=2):
                    return
            except OSError:
                time.sleep(2)
        raise TimeoutError(f"Tibero service did not become ready on {host}:{port}")
