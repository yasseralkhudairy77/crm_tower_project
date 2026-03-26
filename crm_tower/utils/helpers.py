from __future__ import annotations

from datetime import date, datetime
from typing import Optional


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def status_keterlambatan(tanggal_tindak_lanjut_berikutnya: Optional[str]) -> str:
    target = parse_iso_date(tanggal_tindak_lanjut_berikutnya)
    if target is None:
        return "Belum Dijadwalkan"
    today = date.today()
    if target < today:
        return "Terlambat"
    if target == today:
        return "Hari Ini"
    return "Terjadwal"


def bool_label(value: int | bool | None) -> str:
    return "Ya" if int(value or 0) == 1 else "Belum"


def to_int_bool(label: str) -> int:
    return 1 if str(label).strip().lower() in {"1", "y", "ya", "yes"} else 0


def score_potensi(kategori: str) -> int:
    mapping = {
        "Potensi Rendah": 30,
        "Cukup Potensial": 60,
        "Sangat Potensial": 90,
    }
    return mapping.get(kategori, 0)