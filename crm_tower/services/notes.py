from __future__ import annotations

from ..constants import JENIS_CATATAN
from ..database import fetchall, get_connection
from ..utils.helpers import now_str
from ..utils.validator import ValidationError, wajib_isi


def add_note(member_id: int, jenis_catatan: str, isi_catatan: str, dibuat_oleh: int) -> int:
    wajib_isi(str(member_id), "Member")
    if jenis_catatan not in JENIS_CATATAN:
        raise ValidationError("Jenis catatan tidak valid.")
    wajib_isi(isi_catatan, "Isi catatan")
    wajib_isi(str(dibuat_oleh), "Pembuat catatan")

    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO catatan_member (
                id_member, jenis_catatan, isi_catatan, dibuat_oleh, tanggal_catatan
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (member_id, jenis_catatan, isi_catatan.strip(), dibuat_oleh, now_str()),
        )
        conn.commit()
        return int(cur.lastrowid)


def latest_notes(limit: int = 20):
    return fetchall(
        """
        SELECT cm.*, m.nama_member, u.nama_pengguna
        FROM catatan_member cm
        JOIN member m ON cm.id_member = m.id_member
        JOIN pengguna u ON cm.dibuat_oleh = u.id_pengguna
        ORDER BY cm.tanggal_catatan DESC, cm.id_catatan DESC
        LIMIT ?
        """,
        (limit,),
    )