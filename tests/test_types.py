from __future__ import annotations

import datetime
import unittest

import pytibero


class TypesTestCase(unittest.TestCase):
    def test_type_objects_compare_to_type_codes(self) -> None:
        self.assertEqual(pytibero.STRING, 1)
        self.assertEqual(pytibero.BINARY, 2)
        self.assertEqual(pytibero.NUMBER, 3)
        self.assertEqual(pytibero.DATETIME, 8)
        self.assertEqual(pytibero.ROWID, 15)

    def test_constructors(self) -> None:
        self.assertEqual(pytibero.Date(2026, 3, 12), datetime.date(2026, 3, 12))
        self.assertEqual(pytibero.Time(8, 30, 0), datetime.time(8, 30, 0))
        self.assertEqual(
            pytibero.Timestamp(2026, 3, 12, 8, 30, 0),
            datetime.datetime(2026, 3, 12, 8, 30, 0),
        )
        self.assertEqual(pytibero.Binary("abc"), b"abc")

    def test_tick_constructors_and_binary_type_validation(self) -> None:
        ticks = 1_741_769_200

        self.assertEqual(pytibero.DateFromTicks(ticks), datetime.date.fromtimestamp(ticks))
        self.assertEqual(pytibero.TimeFromTicks(ticks), datetime.datetime.fromtimestamp(ticks).time())
        self.assertEqual(pytibero.TimestampFromTicks(ticks), datetime.datetime.fromtimestamp(ticks))

        with self.assertRaises(TypeError):
            pytibero.Binary(123)  # type: ignore[arg-type]

    def test_dbapi_type_dunders_and_binary_inputs(self) -> None:
        self.assertEqual(pytibero.STRING, pytibero.STRING)
        self.assertNotEqual(pytibero.STRING, pytibero.BINARY)
        self.assertNotEqual(pytibero.STRING, "x")
        self.assertEqual(hash(pytibero.STRING), hash(pytibero.STRING))
        self.assertEqual(repr(pytibero.STRING), "DBAPIType('STRING')")
        self.assertEqual(pytibero.Binary(b"abc"), b"abc")
        self.assertEqual(pytibero.Binary(bytearray(b"abc")), b"abc")


if __name__ == "__main__":
    unittest.main()
