"""Wipe all data from the SQLite database without dropping schema.

Use when you want to re-upload fresh data.

Run:
  python wipe_db.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from config import settings


def main() -> None:
    db_path = Path(settings.DATABASE_PATH)
    print(f"DB path: {db_path}")
    if not db_path.exists():
        print("DB does not exist; nothing to wipe.")
        return

    # Timeout helps if another process has a short-lived lock.
    conn = sqlite3.connect(str(db_path), timeout=30)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("PRAGMA journal_mode=WAL")

        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]

        print(f"Found {len(tables)} tables")
        for table in tables:
            conn.execute(f"DELETE FROM {table}")
        conn.commit()

        # Reclaim space
        conn.execute("VACUUM")
        print("Wipe complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
