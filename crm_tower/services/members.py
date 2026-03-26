from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..constants import STATUS_MEMBER, TAHAP_PROGRESS, KATEGORI_POTENSI
from ..database import fetchall, fetchone, get_connection
from ..services.brands import BRAND_OPTIONS
from ..utils.helpers import now_str, score_potensi, status_keterlambatan
from ..utils.validator import ValidationError, normalisasi_wa, validasi_tanggal, wajib_isi


@dataclass
class MemberInput:
    nama_member: str
    nomor_whatsapp: str
    email: str
    kota: str
    brand_utama: str
    id_sumber: int
    penanggung_jawab: int
    status_member: str
    tahap_progress: str
    sudah_mulai_praktik: int
    kategori_potensi: str
    tanggal_kontak_terakhir: str
    tanggal_tindak_lanjut_berikutnya: str
    ringkasan_kondisi: str
    langkah_berikutnya: str


def validate_member_input(data: MemberInput) -> None:
    wajib_isi(data.nama_member, "Nama member")
    wajib_isi(data.nomor_whatsapp, "Nomor WhatsApp")
    wajib_isi(str(data.id_sumber), "Sumber data")
    wajib_isi(str(data.penanggung_jawab), "Penanggung jawab")
    if data.brand_utama and data.brand_utama not in BRAND_OPTIONS and data.brand_utama != "Umum":
        raise ValidationError("Brand utama tidak valid.")
    if data.status_member not in STATUS_MEMBER:
        raise ValidationError("Status member tidak valid.")
    if data.tahap_progress not in TAHAP_PROGRESS:
        raise ValidationError("Tahap progress tidak valid.")
    if data.kategori_potensi not in KATEGORI_POTENSI:
        raise ValidationError("Kategori potensi tidak valid.")
    validasi_tanggal(data.tanggal_tindak_lanjut_berikutnya, "Tanggal tindak lanjut berikutnya")
    if data.tanggal_kontak_terakhir:
        validasi_tanggal(data.tanggal_kontak_terakhir, "Tanggal kontak terakhir")


def validate_member_updates(updates: dict) -> None:
    if "status_member" in updates and updates["status_member"] not in STATUS_MEMBER:
        raise ValidationError("Status member tidak valid.")
    if "tahap_progress" in updates and updates["tahap_progress"] not in TAHAP_PROGRESS:
        raise ValidationError("Tahap progress tidak valid.")
    if "kategori_potensi" in updates and updates["kategori_potensi"] not in KATEGORI_POTENSI:
        raise ValidationError("Kategori potensi tidak valid.")
    if "tanggal_tindak_lanjut_berikutnya" in updates:
        validasi_tanggal(updates["tanggal_tindak_lanjut_berikutnya"], "Tanggal tindak lanjut berikutnya")
    if "tanggal_kontak_terakhir" in updates and updates["tanggal_kontak_terakhir"]:
        validasi_tanggal(updates["tanggal_kontak_terakhir"], "Tanggal kontak terakhir")
    if "brand_utama" in updates and updates["brand_utama"] and updates["brand_utama"] not in BRAND_OPTIONS and updates["brand_utama"] != "Umum":
        raise ValidationError("Brand utama tidak valid.")


def add_member(data: MemberInput) -> int:
    validate_member_input(data)
    now = now_str()
    no_wa = normalisasi_wa(data.nomor_whatsapp)
    nilai_potensi = score_potensi(data.kategori_potensi)
    status_tl = status_keterlambatan(data.tanggal_tindak_lanjut_berikutnya)

    with get_connection() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO member (
                    nama_member, nomor_whatsapp, email, kota, brand_utama, id_sumber, penanggung_jawab,
                    status_member, tahap_progress, sudah_mulai_praktik, kategori_potensi,
                    nilai_potensi, tanggal_kontak_terakhir, tanggal_tindak_lanjut_berikutnya,
                    status_keterlambatan, ringkasan_kondisi, langkah_berikutnya, aktif,
                    dibuat_pada, diupdate_pada
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    data.nama_member.strip(),
                    no_wa,
                    data.email.strip() or None,
                    data.kota.strip() or None,
                    data.brand_utama.strip() or None,
                    data.id_sumber,
                    data.penanggung_jawab,
                    data.status_member,
                    data.tahap_progress,
                    int(data.sudah_mulai_praktik),
                    data.kategori_potensi,
                    nilai_potensi,
                    data.tanggal_kontak_terakhir or None,
                    data.tanggal_tindak_lanjut_berikutnya,
                    status_tl,
                    data.ringkasan_kondisi.strip(),
                    data.langkah_berikutnya.strip(),
                    now,
                    now,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
        except Exception as exc:
            if "UNIQUE constraint failed: member.nomor_whatsapp" in str(exc):
                raise ValidationError("Nomor WhatsApp sudah ada di database.") from exc
            raise


def update_member(member_id: int, updates: dict) -> None:
    if not updates:
        return
    allowed = {
        "email", "kota", "penanggung_jawab", "status_member", "tahap_progress",
        "sudah_mulai_praktik", "kategori_potensi", "nilai_potensi",
        "tanggal_kontak_terakhir", "tanggal_tindak_lanjut_berikutnya",
        "status_keterlambatan", "ringkasan_kondisi", "langkah_berikutnya", "aktif", "brand_utama"
    }
    cleaned = {k: v for k, v in updates.items() if k in allowed}
    if not cleaned:
        return
    validate_member_updates(cleaned)
    if "kategori_potensi" in cleaned and "nilai_potensi" not in cleaned:
        cleaned["nilai_potensi"] = score_potensi(cleaned["kategori_potensi"])
    if "tanggal_tindak_lanjut_berikutnya" in cleaned and "status_keterlambatan" not in cleaned:
        cleaned["status_keterlambatan"] = status_keterlambatan(cleaned["tanggal_tindak_lanjut_berikutnya"])
    for key in {"email", "kota", "ringkasan_kondisi", "langkah_berikutnya", "brand_utama"}:
        if key in cleaned:
            cleaned[key] = str(cleaned[key]).strip() or None
    cleaned["diupdate_pada"] = now_str()

    set_clause = ", ".join(f"{key} = ?" for key in cleaned)
    params = list(cleaned.values()) + [member_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE member SET {set_clause} WHERE id_member = ?", params)
        conn.commit()


def refresh_overdue_flags() -> None:
    rows = fetchall("SELECT id_member, tanggal_tindak_lanjut_berikutnya FROM member WHERE aktif = 1")
    with get_connection() as conn:
        for row in rows:
            conn.execute(
                "UPDATE member SET status_keterlambatan = ?, diupdate_pada = ? WHERE id_member = ?",
                (
                    status_keterlambatan(row["tanggal_tindak_lanjut_berikutnya"]),
                    now_str(),
                    row["id_member"],
                ),
            )
        conn.commit()


def list_members():
    refresh_overdue_flags()
    return fetchall(
        """
        SELECT m.*, p.nama_pengguna, s.nama_sumber
        FROM member m
        LEFT JOIN pengguna p ON m.penanggung_jawab = p.id_pengguna
        LEFT JOIN sumber_data s ON m.id_sumber = s.id_sumber
        ORDER BY m.id_member DESC
        """
    )


def search_members(keyword: str):
    refresh_overdue_flags()
    term = f"%{keyword.strip()}%"
    return fetchall(
        """
        SELECT m.*, p.nama_pengguna, s.nama_sumber
        FROM member m
        LEFT JOIN pengguna p ON m.penanggung_jawab = p.id_pengguna
        LEFT JOIN sumber_data s ON m.id_sumber = s.id_sumber
        WHERE m.nama_member LIKE ? OR m.nomor_whatsapp LIKE ?
        ORDER BY m.id_member DESC
        """,
        (term, term),
    )


def get_member_detail(member_id: int):
    refresh_overdue_flags()
    member = fetchone(
        """
        SELECT m.*, p.nama_pengguna, p.peran, s.nama_sumber
        FROM member m
        LEFT JOIN pengguna p ON m.penanggung_jawab = p.id_pengguna
        LEFT JOIN sumber_data s ON m.id_sumber = s.id_sumber
        WHERE m.id_member = ?
        """,
        (member_id,),
    )
    if not member:
        return None
    pembelian = fetchall(
        """
        SELECT rp.*, pr.nama_program, pr.jenis_program
        FROM riwayat_pembelian rp
        JOIN program pr ON rp.id_program = pr.id_program
        WHERE rp.id_member = ?
        ORDER BY rp.tanggal_beli DESC, rp.id_pembelian DESC
        """,
        (member_id,),
    )
    catatan = fetchall(
        """
        SELECT cm.*, u.nama_pengguna
        FROM catatan_member cm
        JOIN pengguna u ON cm.dibuat_oleh = u.id_pengguna
        WHERE cm.id_member = ?
        ORDER BY cm.tanggal_catatan DESC, cm.id_catatan DESC
        """,
        (member_id,),
    )
    kendala_terbaru = fetchone(
        """
        SELECT km.*, u.nama_pengguna
        FROM kendala_member km
        LEFT JOIN pengguna u ON km.dicatat_oleh = u.id_pengguna
        WHERE km.id_member = ?
        ORDER BY km.tanggal_update DESC, km.id_kendala DESC
        LIMIT 1
        """,
        (member_id,),
    )
    return {
        "member": member,
        "pembelian": pembelian,
        "catatan": catatan,
        "kendala_terbaru": kendala_terbaru,
    }
