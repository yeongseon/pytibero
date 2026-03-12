from __future__ import annotations

import unittest

from pytibero.config import ConnectionConfig
from pytibero.protocol import build_connection_string


class ProtocolTestCase(unittest.TestCase):
    def test_dsn_connection_string(self) -> None:
        config = ConnectionConfig(
            dsn="TIBERO_TEST",
            user="tibero",
            password="tmax",
            options={"ApplicationName": "test-suite"},
        )

        value = build_connection_string(config)

        self.assertEqual(value, "DSN=TIBERO_TEST;UID=tibero;PWD=tmax;ApplicationName=test-suite;")

    def test_values_with_spaces_and_braces_are_escaped(self) -> None:
        config = ConnectionConfig(
            driver="Tibero 7 ODBC Driver",
            host="localhost",
            port=8629,
            database="sample name",
            user="user",
            password="pw}1",
        )

        value = build_connection_string(config)

        self.assertIn("DRIVER={Tibero 7 ODBC Driver}", value)
        self.assertIn("DB={sample name}", value)
        self.assertIn("PWD={pw}}1}", value)

    def test_boolean_options_are_stringified_and_none_is_skipped(self) -> None:
        config = ConnectionConfig(options={"Pooling": True, "Ignored": None})

        value = build_connection_string(config)

        self.assertIn("Pooling=1", value)
        self.assertNotIn("Ignored", value)


if __name__ == "__main__":
    unittest.main()
