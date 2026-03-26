from __future__ import annotations

from ..constants import KATEGORI_POTENSI, STATUS_PELUANG
from ..database import fetchall, get_connection
from ..utils.helpers import now_str
from ..utils.validator import ValidationError, wajib_isi


def add_opportunity(
    member_id: int,
    tingkat_potensi: str,
    alasan_potensial: str,
    masalah_utama_member: str,
    target_member: str,
    solusi_yang_cocok: str,
    status_penawaran: str,
    penanggung_jawab: int,
) -> int:
    if tingkat_potensi not in KATEGORI_POTENSI:
        raise ValidationError("Tingkat potensi tidak valid.")
    if status_penawaran not in STATUS_PELUANG:
        raise ValidationError("Status penawaran tidak valid.")
    wajib_isi(alasan_potensial, "Alasan potensi")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO peluang_lanjutan (
                id_member, tingkat_potensi, alasan_potensial, masalah_utama_member,
                target_member, solusi_yang_cocok, status_penawaran, penanggung_jawab,
                tanggal_update
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                member_id, tingkat_potensi, alasan_potensial.strip(),
                masalah_utama_member.strip() or None,
                target_member.strip() or None,
                solusi_yang_cocok.strip() or None,
                status_penawaran, penanggung_jawab, now_str()
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_opportunities():
    return fetchall(
        """
        SELECT pl.*, m.nama_member, u.nama_pengguna
        FROM peluang_lanjutan pl
        JOIN member m ON pl.id_member = m.id_member
        JOIN pengguna u ON pl.penanggung_jawab = u.id_pengguna
        ORDER BY pl.tingkat_potensi DESC, pl.tanggal_update DESC
        """
    )


def update_opportunity_status(opportunity_id: int, status_penawaran: str, alasan_tidak_lanjut: str = "") -> None:
    if status_penawaran not in STATUS_PELUANG:
        raise ValidationError("Status penawaran tidak valid.")
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE peluang_lanjutan
            SET status_penawaran = ?, alasan_tidak_lanjut = ?, tanggal_update = ?
            WHERE id_peluang = ?
            """,
            (status_penawaran, alasan_tidak_lanjut.strip() or None, now_str(), opportunity_id),
        )
        conn.commit()