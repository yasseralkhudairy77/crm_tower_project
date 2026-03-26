from __future__ import annotations

from datetime import datetime


class ValidationError(ValueError):
    pass


def wajib_isi(value: str | None, label: str) -> None:
    if not str(value or "").strip():
        raise ValidationError(f"{label} wajib diisi.")


def validasi_tanggal(value: str | None, label: str) -> None:
    if not str(value or "").strip():
        raise ValidationError(f"{label} wajib diisi.")
    try:
        datetime.strptime(str(value), "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError(f"{label} harus berformat YYYY-MM-DD.") from exc


def normalisasi_wa(no_wa: str) -> str:
    cleaned = "".join(ch for ch in str(no_wa) if ch.isdigit())
    if cleaned.startswith("62"):
        return cleaned
    if cleaned.startswith("0"):
        return "62" + cleaned[1:]
    return cleaned