from __future__ import annotations

from ..constants import KATEGORI_KENDALA, STATUS_KENDALA, TINGKAT_URGENSI
from ..database import fetchall, fetchone, get_connection
from ..utils.helpers import now_str
from ..utils.validator import ValidationError, wajib_isi


def add_or_update_obstacle(
    member_id: int,
    kategori_kendala: str,
    detail_kendala: str,
    tingkat_urgensi: str,
    perlu_bantuan_mentor: int,
    solusi_awal: str,
    status_kendala: str,
    dicatat_oleh: int,
) -> int:
    if kategori_kendala not in KATEGORI_KENDALA:
        raise ValidationError("Kategori kendala tidak valid.")
    if tingkat_urgensi not in TINGKAT_URGENSI:
        raise ValidationError("Tingkat urgensi tidak valid.")
    if status_kendala not in STATUS_KENDALA:
        raise ValidationError("Status kendala tidak valid.")
    wajib_isi(detail_kendala, "Detail kendala")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO kendala_member (
                id_member, kategori_kendala, detail_kendala, tingkat_urgensi,
                perlu_bantuan_mentor, solusi_awal, status_kendala, dicatat_oleh,
                tanggal_dicatat, tanggal_update
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                member_id,
                kategori_kendala,
                detail_kendala.strip(),
                tingkat_urgensi,
                int(perlu_bantuan_mentor),
                solusi_awal.strip() or None,
                status_kendala,
                dicatat_oleh,
                now_str(),
                now_str(),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_obstacles(include_closed: bool = False):
    query = """
        SELECT km.*, m.nama_member, m.nomor_whatsapp, m.brand_utama, u.nama_pengguna
        FROM kendala_member km
        JOIN member m ON km.id_member = m.id_member
        JOIN pengguna u ON km.dicatat_oleh = u.id_pengguna
    """
    if not include_closed:
        query += " WHERE km.status_kendala <> 'Selesai'"
    query += " ORDER BY km.tanggal_update DESC"
    return fetchall(query)


def list_obstacles_open():
    return list_obstacles(include_closed=False)


def get_obstacle_detail(obstacle_id: int):
    return fetchone(
        """
        SELECT km.*, m.nama_member, m.nomor_whatsapp, m.brand_utama, u.nama_pengguna
        FROM kendala_member km
        JOIN member m ON km.id_member = m.id_member
        JOIN pengguna u ON km.dicatat_oleh = u.id_pengguna
        WHERE km.id_kendala = ?
        """,
        (obstacle_id,),
    )


def update_obstacle(
    obstacle_id: int,
    tingkat_urgensi: str,
    status_kendala: str,
    perlu_bantuan_mentor: int,
    solusi_awal: str = "",
) -> None:
    if tingkat_urgensi not in TINGKAT_URGENSI:
        raise ValidationError("Tingkat urgensi tidak valid.")
    if status_kendala not in STATUS_KENDALA:
        raise ValidationError("Status kendala tidak valid.")
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE kendala_member
            SET tingkat_urgensi = ?, status_kendala = ?, perlu_bantuan_mentor = ?,
                solusi_awal = ?, tanggal_update = ?
            WHERE id_kendala = ?
            """,
            (
                tingkat_urgensi,
                status_kendala,
                int(perlu_bantuan_mentor),
                solusi_awal.strip() or None,
                now_str(),
                obstacle_id,
            ),
        )
        conn.commit()


def bulk_update_obstacles(
    obstacle_ids: list[int],
    status_kendala: str = "",
    dicatat_oleh: int | None = None,
) -> dict:
    valid_ids = [int(item) for item in obstacle_ids if int(item) > 0]
    if not valid_ids:
        raise ValidationError("Minimal pilih satu kendala.")
    if status_kendala and status_kendala not in STATUS_KENDALA:
        raise ValidationError("Status kendala tidak valid.")
    updated = 0
    with get_connection() as conn:
        for obstacle_id in valid_ids:
            fields = []
            params: list = []
            if status_kendala:
                fields.append("status_kendala = ?")
                params.append(status_kendala)
            if dicatat_oleh:
                fields.append("dicatat_oleh = ?")
                params.append(dicatat_oleh)
            if not fields:
                continue
            fields.append("tanggal_update = ?")
            params.append(now_str())
            params.append(obstacle_id)
            conn.execute(f"UPDATE kendala_member SET {', '.join(fields)} WHERE id_kendala = ?", params)
            updated += 1
        conn.commit()
    return {"updated": updated}
