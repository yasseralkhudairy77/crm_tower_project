from __future__ import annotations

from ..constants import JENIS_MASALAH, PRIORITAS, STATUS_PENANGANAN
from ..database import fetchall, fetchone, get_connection
from ..utils.helpers import now_str
from ..utils.validator import ValidationError, wajib_isi


def add_issue(
    member_id: int,
    jenis_masalah: str,
    detail_masalah: str,
    prioritas: str,
    penanggung_jawab: int,
) -> int:
    if jenis_masalah not in JENIS_MASALAH:
        raise ValidationError("Jenis masalah tidak valid.")
    if prioritas not in PRIORITAS:
        raise ValidationError("Prioritas tidak valid.")
    wajib_isi(detail_masalah, "Detail masalah")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO keluhan_member (
                id_member, jenis_masalah, detail_masalah, prioritas,
                penanggung_jawab, status_penanganan, tanggal_masuk
            ) VALUES (?, ?, ?, ?, ?, 'Baru', ?)
            """,
            (member_id, jenis_masalah, detail_masalah.strip(), prioritas, penanggung_jawab, now_str()),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_issues(active_only: bool = False):
    query = """
        SELECT km.*, m.nama_member, m.nomor_whatsapp, m.brand_utama, u.nama_pengguna
        FROM keluhan_member km
        JOIN member m ON km.id_member = m.id_member
        JOIN pengguna u ON km.penanggung_jawab = u.id_pengguna
    """
    params = ()
    if active_only:
        query += " WHERE km.status_penanganan <> 'Selesai'"
    query += " ORDER BY km.tanggal_masuk DESC"
    return fetchall(query, params)


def get_issue_detail(issue_id: int):
    row = fetchone(
        """
        SELECT km.*, m.nama_member, m.nomor_whatsapp, m.brand_utama, u.nama_pengguna
        FROM keluhan_member km
        JOIN member m ON km.id_member = m.id_member
        JOIN pengguna u ON km.penanggung_jawab = u.id_pengguna
        WHERE km.id_keluhan = ?
        """,
        (issue_id,),
    )
    return row


def update_issue(issue_id: int, status_penanganan: str, catatan_penyelesaian: str = "") -> None:
    if status_penanganan not in STATUS_PENANGANAN:
        raise ValidationError("Status penanganan tidak valid.")
    tanggal_selesai = now_str() if status_penanganan == "Selesai" else None
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE keluhan_member
            SET status_penanganan = ?, tanggal_selesai = ?, catatan_penyelesaian = ?
            WHERE id_keluhan = ?
            """,
            (status_penanganan, tanggal_selesai, catatan_penyelesaian.strip() or None, issue_id),
        )
        conn.commit()


def bulk_update_issues(issue_ids: list[int], status_penanganan: str = "", penanggung_jawab: int | None = None) -> dict:
    valid_ids = [int(item) for item in issue_ids if int(item) > 0]
    if not valid_ids:
        raise ValidationError("Minimal pilih satu keluhan.")
    if status_penanganan and status_penanganan not in STATUS_PENANGANAN:
        raise ValidationError("Status penanganan tidak valid.")
    updated = 0
    with get_connection() as conn:
        for issue_id in valid_ids:
            fields = []
            params: list = []
            if status_penanganan:
                fields.append("status_penanganan = ?")
                params.append(status_penanganan)
                fields.append("tanggal_selesai = ?")
                params.append(now_str() if status_penanganan == "Selesai" else None)
            if penanggung_jawab:
                fields.append("penanggung_jawab = ?")
                params.append(penanggung_jawab)
            if not fields:
                continue
            params.append(issue_id)
            conn.execute(f"UPDATE keluhan_member SET {', '.join(fields)} WHERE id_keluhan = ?", params)
            updated += 1
        conn.commit()
    return {"updated": updated}
