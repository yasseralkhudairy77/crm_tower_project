from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

from ..database import get_connection
from ..utils.helpers import now_str, parse_iso_date, score_potensi, status_keterlambatan, today_str
from ..utils.validator import normalisasi_wa
from .brands import detect_brand, is_member_product
from .orderonline import parse_orderonline_datetime


@dataclass
class MemberImportResult:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0


def detect_latest_member_csv() -> Path | None:
    downloads = Path.home() / "Downloads"
    candidates = sorted(
        downloads.glob("orderonline_orders_*.csv"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def detect_member_csv_files() -> list[Path]:
    downloads = Path.home() / "Downloads"
    return sorted(
        downloads.glob("orderonline_orders_*.csv"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def is_member_order_eligible(row: dict) -> bool:
    payment_status = str(row.get("payment_status", "")).strip().lower()
    order_status = str(row.get("status", "")).strip().lower()
    return is_member_product(
        product=str(row.get("product", "")),
        product_code=str(row.get("product_code", "")),
    ) and payment_status == "paid" and order_status == "completed"


def _ensure_program(conn, product_name: str) -> int:
    row = conn.execute("SELECT id_program FROM program WHERE nama_program = ?", (product_name,)).fetchone()
    if row:
        return int(row["id_program"])
    cur = conn.execute(
        """
        INSERT INTO program (nama_program, jenis_program, status_program, dibuat_pada)
        VALUES (?, 'Membership', 'Aktif', ?)
        """,
        (product_name, now_str()),
    )
    return int(cur.lastrowid)


def _default_pic_id(conn) -> int:
    row = conn.execute(
        """
        SELECT id_pengguna
        FROM pengguna
        WHERE aktif = 1
        ORDER BY CASE WHEN nama_pengguna = 'Sabrina Aulia' THEN 0 ELSE 1 END, id_pengguna ASC
        LIMIT 1
        """
    ).fetchone()
    return int(row["id_pengguna"])


def _order_date(row: dict) -> str:
    for field in ("paid_at", "completed_at", "created_at"):
        value = row.get(field, "")
        iso_date, _iso_dt = parse_orderonline_datetime(value)
        if iso_date:
            return iso_date
    return today_str()


def _insert_member(
    conn,
    customer_name: str,
    phone: str,
    email: str,
    city: str,
    brand_name: str,
    source_id: int,
    pic_id: int,
    order_date: str,
    product_name: str,
) -> int:
    now = now_str()
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
            customer_name,
            phone,
            email or None,
            city or None,
            brand_name,
            source_id,
            pic_id,
            "Data Baru",
            "Belum dimulai",
            0,
            "Sangat Potensial",
            score_potensi("Sangat Potensial"),
            order_date,
            today_str(),
            status_keterlambatan(today_str()),
            (
                f"Member membeli {product_name} dari OrderOnline. CRM perlu menjaga relasi, "
                "menanyakan perkembangan belajar, praktik, dan kendala pasca pembelian."
            ),
            (
                "Hubungi member untuk cek perkembangan kelas, apakah sudah praktik, ada kesulitan, "
                "dan apakah butuh arahan lanjutan."
            ),
            now,
            now,
        ),
    )
    return int(cur.lastrowid)


def _update_member_context(conn, member_id: int, existing_member, city: str, email: str, order_date: str, brand_name: str) -> None:
    updates = {}
    if city and not existing_member["kota"]:
        updates["kota"] = city
    if email and not existing_member["email"]:
        updates["email"] = email
    if brand_name and not existing_member["brand_utama"]:
        updates["brand_utama"] = brand_name
    existing_contact = parse_iso_date(existing_member["tanggal_kontak_terakhir"])
    new_contact = parse_iso_date(order_date)
    if new_contact and (not existing_contact or new_contact > existing_contact):
        updates["tanggal_kontak_terakhir"] = order_date
    if not updates:
        return
    updates["diupdate_pada"] = now_str()
    set_clause = ", ".join(f"{key} = ?" for key in updates)
    params = list(updates.values()) + [member_id]
    conn.execute(f"UPDATE member SET {set_clause} WHERE id_member = ?", params)


def _insert_purchase_note_task(
    conn,
    member_id: int,
    program_id: int,
    pic_id: int,
    customer_name: str,
    product_name: str,
    brand_name: str,
    order_id: str,
    order_date: str,
    price: float,
) -> None:
    now = now_str()
    today = today_str()
    conn.execute(
        """
        INSERT INTO riwayat_pembelian (
            id_member, id_program, tanggal_beli, nomor_order, nilai_transaksi, brand_name,
            status_pembelian, sumber_transaksi, catatan_pembelian, dibuat_pada
        )
        VALUES (?, ?, ?, ?, ?, ?, 'berhasil', 'OrderOnline', ?, ?)
        """,
        (
            member_id,
            program_id,
            order_date,
            order_id or None,
            price,
            brand_name,
            f"Import harian dari OrderOnline untuk {product_name}.",
            now,
        ),
    )
    conn.execute(
        """
        INSERT INTO catatan_member (
            id_member, jenis_catatan, isi_catatan, dibuat_oleh, tanggal_catatan
        )
        VALUES (?, 'Catatan Awal', ?, ?, ?)
        """,
        (
            member_id,
            (
                f"Import member program lanjutan dari OrderOnline. Brand: {brand_name}. Produk: {product_name}. "
                f"Order ID: {order_id}. Fokus CRM: jaga relasi, cek praktik, dan gali kendala member."
            ),
            pic_id,
            now,
        ),
    )
    open_task = conn.execute(
        """
        SELECT id_tugas
        FROM tugas_crm
        WHERE id_member = ?
          AND jenis_tugas = 'Cek progress member'
          AND status_tugas IN ('Belum Dikerjakan', 'Sedang Dikerjakan', 'Terlambat')
        LIMIT 1
        """,
        (member_id,),
    ).fetchone()
    if open_task:
        return
    conn.execute(
        """
        INSERT INTO tugas_crm (
            id_member, jenis_tugas, penanggung_jawab, tanggal_jatuh_tempo,
            prioritas, status_tugas, catatan_tugas, dibuat_pada
        )
        VALUES (?, 'Cek progress member', ?, ?, 'Sedang', 'Belum Dikerjakan', ?, ?)
        """,
        (
            member_id,
            pic_id,
            today,
            (
                f"Follow up member {customer_name} setelah pembelian {product_name}. "
                "Tanyakan progres belajar, praktik, dan kendala yang sedang dihadapi."
            ),
            now,
        ),
    )


def import_member_orderonline_csv(file_bytes: bytes, source_file: str) -> MemberImportResult:
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    result = MemberImportResult()
    today = today_str()

    with get_connection() as conn:
        source = conn.execute("SELECT id_sumber FROM sumber_data WHERE nama_sumber = 'OrderOnline'").fetchone()
        if not source:
            raise ValueError("Sumber OrderOnline belum tersedia.")
        source_id = int(source["id_sumber"])
        pic_id = _default_pic_id(conn)

        for row in reader:
            if not is_member_order_eligible(row):
                result.skipped += 1
                continue

            customer_name = str(row.get("name", "")).strip()
            phone = normalisasi_wa(row.get("phone", ""))
            if not customer_name or not phone:
                result.skipped += 1
                continue

            order_id = str(row.get("order_id", "")).strip()
            product_name = str(row.get("product", "")).strip() or "Member Platinum Sekolah Seller"
            brand_name = detect_brand(product_name, str(row.get("product_code", "")), source_file)
            order_date = _order_date(row)
            city = str(row.get("city", "")).strip()
            email = str(row.get("email", "")).strip()
            program_id = _ensure_program(conn, product_name)

            existing_member = conn.execute(
                "SELECT id_member, tanggal_kontak_terakhir, kota, email, brand_utama FROM member WHERE nomor_whatsapp = ?",
                (phone,),
            ).fetchone()

            if existing_member:
                member_id = int(existing_member["id_member"])
                _update_member_context(conn, member_id, existing_member, city, email, order_date, brand_name)
                result.updated += 1
            else:
                member_id = _insert_member(conn, customer_name, phone, email, city, brand_name, source_id, pic_id, order_date, product_name)
                result.inserted += 1

            purchase = conn.execute(
                "SELECT id_pembelian FROM riwayat_pembelian WHERE nomor_order = ?",
                (order_id,),
            ).fetchone()
            if purchase:
                continue

            _insert_purchase_note_task(
                conn,
                member_id,
                program_id,
                pic_id,
                customer_name,
                product_name,
                brand_name,
                order_id,
                order_date,
                float(row.get("product_price") or 0),
            )

        conn.commit()

    return result


def auto_import_latest_member_csv() -> dict:
    files = detect_member_csv_files()
    if not files:
        raise ValueError("File OrderOnline terbaru untuk member tidak ditemukan di folder Downloads.")
    inserted = 0
    updated = 0
    skipped = 0
    for path in files:
        result = import_member_orderonline_csv(path.read_bytes(), str(path))
        inserted += result.inserted
        updated += result.updated
        skipped += result.skipped
    return {
        "file": str(files[0]),
        "file_count": len(files),
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
    }


def export_members_csv(rows) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id_member",
            "nama_member",
            "nomor_whatsapp",
            "kota",
            "status_member",
            "tahap_progress",
            "sudah_mulai_praktik",
            "kategori_potensi",
            "brand_utama",
            "penanggung_jawab",
            "tanggal_kontak_terakhir",
            "tanggal_tindak_lanjut_berikutnya",
            "status_keterlambatan",
            "ringkasan_kondisi",
            "langkah_berikutnya",
            "sumber_data",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["id_member"],
                row["nama_member"],
                row["nomor_whatsapp"],
                row["kota"] or "",
                row["status_member"],
                row["tahap_progress"],
                "Ya" if int(row["sudah_mulai_praktik"] or 0) == 1 else "Belum",
                row["kategori_potensi"],
                row["brand_utama"] or "",
                row["nama_pengguna"] or "",
                row["tanggal_kontak_terakhir"] or "",
                row["tanggal_tindak_lanjut_berikutnya"] or "",
                row["status_keterlambatan"] or "",
                row["ringkasan_kondisi"] or "",
                row["langkah_berikutnya"] or "",
                row["nama_sumber"] or "",
            ]
        )
    return output.getvalue()
