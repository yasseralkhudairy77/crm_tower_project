from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .database import BASE_DIR, DB_PATH

CONFIG_PATH = BASE_DIR / "crm_tower_config.json"
DEFAULT_AUTO_BACKUP_HOURS = 12


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def get_backup_dir() -> Path | None:
    env_path = os.environ.get("CRM_TOWER_BACKUP_DIR", "").strip()
    if env_path:
        return Path(env_path).expanduser()
    config = load_config()
    path = str(config.get("backup_dir", "")).strip()
    return Path(path).expanduser() if path else None


def set_backup_dir(path: str) -> Path:
    backup_dir = Path(path).expanduser()
    config = load_config()
    config["backup_dir"] = str(backup_dir)
    save_config(config)
    return backup_dir


def list_backups(limit: int = 10) -> list[Path]:
    backup_dir = get_backup_dir()
    if not backup_dir or not backup_dir.exists():
        return []
    items = sorted(
        backup_dir.glob("crm_tower_backup_*.db"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return items[:limit]


def create_backup(backup_dir: str | Path | None = None) -> Path:
    target_dir = Path(backup_dir).expanduser() if backup_dir else get_backup_dir()
    if not target_dir:
        raise ValueError("Folder backup belum dikonfigurasi.")
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target_dir / f"crm_tower_backup_{timestamp}.db"
    latest_path = target_dir / "crm_tower_latest.db"

    with sqlite3.connect(DB_PATH) as source_conn, sqlite3.connect(backup_path) as target_conn:
        source_conn.backup(target_conn)

    with sqlite3.connect(DB_PATH) as source_conn, sqlite3.connect(latest_path) as latest_conn:
        source_conn.backup(latest_conn)

    return backup_path


def create_reset_snapshot() -> Path | None:
    if not DB_PATH.exists():
        return None

    configured_dir = get_backup_dir()
    if configured_dir:
        return create_backup(configured_dir)

    fallback_dir = BASE_DIR / "backup_reset"
    return create_backup(fallback_dir)


def reset_database_file() -> list[str]:
    removed_files: list[str] = []
    db_related_files = [
        DB_PATH,
        DB_PATH.parent / f"{DB_PATH.name}-wal",
        DB_PATH.parent / f"{DB_PATH.name}-shm",
    ]

    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")

    for path in db_related_files:
        if path.exists():
            path.unlink()
            removed_files.append(str(path))

    return removed_files


def reset_database_contents() -> None:
    if not DB_PATH.exists():
        return

    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("PRAGMA foreign_keys = OFF;")
        table_rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()
        view_rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'view' AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()
        trigger_rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'trigger' AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()

        for (name,) in trigger_rows:
            conn.execute(f'DROP TRIGGER IF EXISTS "{name}"')
        for (name,) in view_rows:
            conn.execute(f'DROP VIEW IF EXISTS "{name}"')
        for (name,) in table_rows:
            conn.execute(f'DROP TABLE IF EXISTS "{name}"')

        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("VACUUM;")


def auto_backup_if_due(hours: int = DEFAULT_AUTO_BACKUP_HOURS) -> Path | None:
    backup_dir = get_backup_dir()
    if not backup_dir:
        return None
    backups = list_backups(limit=1)
    if backups:
        latest = backups[0]
        age = datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)
        if age < timedelta(hours=hours):
            return None
    return create_backup(backup_dir)


def backup_status() -> dict[str, Any]:
    backup_dir = get_backup_dir()
    backups = list_backups(limit=10)
    latest = backups[0] if backups else None
    return {
        "configured": backup_dir is not None,
        "backup_dir": str(backup_dir) if backup_dir else "",
        "backup_count": len(backups),
        "latest_backup": str(latest) if latest else "",
        "items": [
            {
                "name": item.name,
                "path": str(item),
                "modified_at": datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "size_kb": round(item.stat().st_size / 1024, 1),
            }
            for item in backups
        ],
    }
