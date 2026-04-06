# pytibero

Unofficial Python DB-API 2.0 connector for Tibero.

## Key features

- Python DB-API 2.0 compatible interface for Tibero
- Direct host/port and DSN-based connection options
- Optional `tbcli` backend for native Tibero client usage
- Familiar cursor and transaction workflow via a Pythonic API

## Quick install

```bash
pip install pytibero
```

## Connect in seconds

```python
import pytibero

with pytibero.connect(
    host="localhost",
    port=8629,
    database="test",
    user="tibero",
    password="tmax",
) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM dual")
    print(cursor.fetchall())
```

## Documentation

- [Getting Started](installation.md)
- [Development](testing.md)

## Project links

- [GitHub](https://github.com/yeongseon/pytibero)
- [PyPI](https://pypi.org/project/pytibero/)
- [Changelog](https://github.com/yeongseon/pytibero/blob/main/CHANGELOG.md)
- [Contributing](https://github.com/yeongseon/pytibero/blob/main/CONTRIBUTING.md)
