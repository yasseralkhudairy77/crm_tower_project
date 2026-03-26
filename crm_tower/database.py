from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Sequence

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "crm_tower.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA cache_size = -20000;")
    return conn


def execute(query: str, params: Sequence | None = None) -> None:
    with get_connection() as conn:
        conn.execute(query, params or [])
        conn.commit()


def executemany(query: str, rows: Iterable[Sequence]) -> None:
    with get_connection() as conn:
        conn.executemany(query, rows)
        conn.commit()


def fetchone(query: str, params: Sequence | None = None):
    with get_connection() as conn:
        cur = conn.execute(query, params or [])
        return cur.fetchone()


def fetchall(query: str, params: Sequence | None = None):
    with get_connection() as conn:
        cur = conn.execute(query, params or [])
        return cur.fetchall()
