from __future__ import annotations

import sqlite3

from config import settings


def main() -> None:
    conn = sqlite3.connect(settings.DATABASE_PATH)
    try:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        print("tables:", tables)
        for table in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table}: {count}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
