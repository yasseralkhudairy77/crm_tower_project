from __future__ import annotations

from ..constants import JENIS_TUGAS, PRIORITAS, STATUS_TUGAS
from ..database import fetchall, fetchone, get_connection
from ..utils.helpers import now_str, today_str
from ..utils.validator import ValidationError, validasi_tanggal, wajib_isi


def add_task(
    member_id: int,
    jenis_tugas: str,
    penanggung_jawab: int,
    tanggal_jatuh_tempo: str,
    prioritas: str,
    catatan_tugas: str,
) -> int:
    if jenis_tugas not in JENIS_TUGAS:
        raise ValidationError("Jenis tugas tidak valid.")
    if prioritas not in PRIORITAS:
        raise ValidationError("Prioritas tidak valid.")
    validasi_tanggal(tanggal_jatuh_tempo, "Tanggal jatuh tempo")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO tugas_crm (
                id_member, jenis_tugas, penanggung_jawab, tanggal_jatuh_tempo,
                prioritas, status_tugas, catatan_tugas, dibuat_pada
            ) VALUES (?, ?, ?, ?, ?, 'Belum Dikerjakan', ?, ?)
            """,
            (member_id, jenis_tugas, penanggung_jawab, tanggal_jatuh_tempo, prioritas, catatan_tugas.strip() or None, now_str()),
        )
        conn.commit()
        return int(cur.lastrowid)


def refresh_task_statuses() -> None:
    today = today_str()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE tugas_crm
            SET status_tugas = 'Terlambat'
            WHERE status_tugas IN ('Belum Dikerjakan', 'Sedang Dikerjakan')
              AND tanggal_jatuh_tempo < ?
            """,
            (today,),
        )
        conn.commit()


def list_tasks_today():
    refresh_task_statuses()
    return fetchall(
        """
        SELECT t.*, m.nama_member, u.nama_pengguna
        FROM tugas_crm t
        JOIN member m ON t.id_member = m.id_member
        JOIN pengguna u ON t.penanggung_jawab = u.id_pengguna
        WHERE t.tanggal_jatuh_tempo = ? AND t.status_tugas <> 'Selesai'
        ORDER BY t.prioritas DESC, t.id_tugas DESC
        """,
        (today_str(),),
    )


def list_tasks_overdue():
    refresh_task_statuses()
    return fetchall(
        """
        SELECT t.*, m.nama_member, u.nama_pengguna
        FROM tugas_crm t
        JOIN member m ON t.id_member = m.id_member
        JOIN pengguna u ON t.penanggung_jawab = u.id_pengguna
        WHERE t.status_tugas = 'Terlambat'
        ORDER BY t.tanggal_jatuh_tempo ASC, t.id_tugas DESC
        """
    )


def complete_task(task_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE tugas_crm
            SET status_tugas = 'Selesai', tanggal_selesai = ?
            WHERE id_tugas = ?
            """,
            (now_str(), task_id),
        )
        conn.commit()


def list_tasks_by_pic(pic_id: int):
    refresh_task_statuses()
    return fetchall(
        """
        SELECT t.*, m.nama_member, u.nama_pengguna
        FROM tugas_crm t
        JOIN member m ON t.id_member = m.id_member
        JOIN pengguna u ON t.penanggung_jawab = u.id_pengguna
        WHERE t.penanggung_jawab = ?
        ORDER BY t.tanggal_jatuh_tempo ASC
        """,
        (pic_id,),
    )