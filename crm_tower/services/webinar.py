from __future__ import annotations

from ..constants import STATUS_KEHADIRAN_WEBINAR, STATUS_TESTIMONI
from ..database import fetchall, get_connection
from ..utils.helpers import now_str
from ..utils.validator import ValidationError, validasi_tanggal


def add_webinar_record(
    member_id: int,
    program_id: int,
    tanggal_webinar: str,
    status_kehadiran: str,
    status_testimoni: str,
    kesan_peserta: str,
    potensi_lanjutan: str,
    catatan_webinar: str,
) -> int:
    if status_kehadiran not in STATUS_KEHADIRAN_WEBINAR:
        raise ValidationError("Status kehadiran tidak valid.")
    if status_testimoni not in STATUS_TESTIMONI:
        raise ValidationError("Status testimoni tidak valid.")
    validasi_tanggal(tanggal_webinar, "Tanggal webinar")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO riwayat_webinar (
                id_member, id_program, tanggal_webinar, status_kehadiran,
                status_testimoni, kesan_peserta, potensi_lanjutan, catatan_webinar,
                dibuat_pada
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                member_id,
                program_id,
                tanggal_webinar,
                status_kehadiran,
                status_testimoni,
                kesan_peserta.strip() or None,
                potensi_lanjutan.strip() or None,
                catatan_webinar.strip() or None,
                now_str(),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_webinar_records():
    return fetchall(
        """
        SELECT rw.*, m.nama_member, pr.nama_program
        FROM riwayat_webinar rw
        JOIN member m ON rw.id_member = m.id_member
        JOIN program pr ON rw.id_program = pr.id_program
        ORDER BY rw.tanggal_webinar DESC, rw.id_webinar_riwayat DESC
        """
    )