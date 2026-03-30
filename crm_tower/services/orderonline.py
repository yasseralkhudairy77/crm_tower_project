from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode

from ..database import fetchall, fetchone, get_connection
from ..services.brands import detect_brand, is_followup_product, classify_funnel
from ..services.members import MemberInput, add_member
from ..services.notes import add_note
from ..services.tasks import add_task
from ..utils.helpers import now_str, today_str
from ..utils.validator import ValidationError, normalisasi_wa


FOLLOWUP_STATUS_OPTIONS = [
    "Belum Dihubungi",
    "Sudah Dihubungi",
    "Tertarik",
    "Perlu Follow Up Lagi",
    "Tidak Tertarik",
    "Closing After Sales",
]
FOLLOWUP_RESULT_OPTIONS = [
    "Belum Ada Respon",
    "Respon Positif",
    "Respon Negatif",
    "Minta Info Lanjutan",
    "Jadwalkan Follow Up Lagi",
    "Kendala Budget",
    "Tidak Tertarik",
    "Closing",
]
CONTACT_CHANNEL_OPTIONS = ["WhatsApp", "Telepon", "Email", "Manual"]
NEGATIVE_FOLLOWUP_RESULTS = ("Respon Negatif", "Tidak Tertarik")
FOLLOWUP_MESSAGE_TEMPLATES = {
    "Belum Dihubungi": (
        "Halo {name}, saya dari tim CRM. Terima kasih sudah membeli {product}. "
        "Saya ingin bantu follow up kebutuhan Anda setelah mengikuti program ini, termasuk jika Anda tertarik ke program lanjutan atau after-sales."
    ),
    "Sudah Dihubungi": (
        "Halo {name}, saya follow up kembali terkait {product}. "
        "Kalau boleh tahu, saat ini Anda paling butuh bantuan di bagian mana agar kami bisa arahkan program lanjutan yang paling cocok?"
    ),
    "Tertarik": (
        "Halo {name}, terima kasih sudah merespons terkait {product}. "
        "Saya bisa bantu jelaskan opsi program lanjutan atau after-sales yang paling sesuai dengan kebutuhan Anda."
    ),
    "Perlu Follow Up Lagi": (
        "Halo {name}, saya izin follow up lagi terkait {product}. "
        "Kalau sekarang sudah lebih siap, saya bisa bantu arahkan next step atau program lanjutan yang relevan."
    ),
    "Tidak Tertarik": (
        "Halo {name}, terima kasih sudah mengikuti {product}. "
        "Kalau nanti Anda butuh program lanjutan atau pendampingan after-sales, kami siap bantu kapan saja."
    ),
    "Closing After Sales": (
        "Halo {name}, terima kasih sudah melanjutkan proses setelah {product}. "
        "Kami siap bantu pastikan Anda mendapat pengalaman after-sales yang nyaman dan terarah."
    ),
}


@dataclass
class ImportResult:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0


def detect_latest_orderonline_csv() -> Path | None:
    downloads = Path.home() / "Downloads"
    candidates = sorted(
        downloads.glob("orderonline_orders_*.csv"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def detect_orderonline_csv_files() -> list[Path]:
    downloads = Path.home() / "Downloads"
    return sorted(
        downloads.glob("orderonline_orders_*.csv"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def _strip_orderonline_timezone(raw: str) -> str:
    cleaned = str(raw or "").strip().replace("T", " ")
    cleaned = re.sub(r"([.,]\d+)(?=\s*(?:Z|[+-]\d{2}:?\d{2})?$)", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*(?:Z|[+-]\d{2}:?\d{2})$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def normalize_orderonline_datetime(value: str) -> tuple[str | None, str | None, str | None]:
    raw = str(value or "").strip()
    if not raw:
        return None, None, None

    candidates = []
    for candidate in (raw, _strip_orderonline_timezone(raw)):
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    formats = (
        ("%d-%m-%Y - %H:%M", "%d-%m-%Y - %H:%M"),
        ("%d-%m-%Y - %H:%M:%S", "%d-%m-%Y - %H:%M:%S"),
        ("%d-%m-%Y %H:%M", "%d-%m-%Y - %H:%M"),
        ("%d-%m-%Y %H:%M:%S", "%d-%m-%Y - %H:%M:%S"),
        ("%Y-%m-%d %H:%M", "%d-%m-%Y - %H:%M"),
        ("%Y-%m-%d %H:%M:%S", "%d-%m-%Y - %H:%M:%S"),
    )
    for candidate in candidates:
        for input_format, output_format in formats:
            try:
                parsed = datetime.strptime(candidate, input_format)
                return (
                    parsed.strftime(output_format),
                    parsed.strftime("%Y-%m-%d"),
                    parsed.strftime("%Y-%m-%d %H:%M:%S"),
                )
            except ValueError:
                continue
    return raw, None, None


def parse_orderonline_datetime(value: str) -> tuple[str | None, str | None]:
    _display, iso_date, iso_datetime = normalize_orderonline_datetime(value)
    return iso_date, iso_datetime


def display_orderonline_datetime(raw_value: str | None, iso_value: str | None) -> str:
    display_value, _iso_date, _iso_datetime = normalize_orderonline_datetime(raw_value or iso_value or "")
    return display_value or "-"


def is_followup_eligible(row: dict) -> bool:
    payment_status = str(row.get("payment_status", "")).strip().lower()
    order_status = str(row.get("status", "")).strip().lower()
    return is_followup_product(
        product=str(row.get("product", "")),
        product_code=str(row.get("product_code", "")),
    ) and payment_status == "paid" and order_status == "completed"


def import_orderonline_csv(file_bytes: bytes, source_file: str) -> ImportResult:
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    result = ImportResult()
    now = now_str()

    with get_connection() as conn:
        for row in reader:
            if not is_followup_eligible(row):
                result.skipped += 1
                continue
            phone = normalisasi_wa(row.get("phone", ""))
            if not phone:
                result.skipped += 1
                continue

            created_raw, _created_date, created_dt = normalize_orderonline_datetime(row.get("created_at", ""))
            paid_raw, _paid_date, paid_dt = normalize_orderonline_datetime(row.get("paid_at", ""))
            brand_name = detect_brand(
                row.get("product", "").strip(),
                row.get("product_code", "").strip(),
                source_file,
            )
            funnel_type = classify_funnel(
                row.get("product", "").strip(),
                row.get("product_code", "").strip(),
                source_file,
            )
            payload = (
                row.get("product", "").strip(),
                row.get("product_code", "").strip() or None,
                row.get("name", "").strip(),
                row.get("email", "").strip() or None,
                phone,
                row.get("city", "").strip() or None,
                brand_name,
                funnel_type,
                row.get("status", "").strip() or None,
                row.get("payment_status", "").strip() or None,
                row.get("payment_method", "").strip() or None,
                float(row.get("product_price") or 0),
                int(row.get("quantity") or 1),
                created_raw or None,
                created_dt,
                paid_raw or None,
                paid_dt,
                source_file,
                source_file,
                now,
            )
            existing = conn.execute(
                "SELECT id_import FROM orderonline_followup WHERE order_id = ?",
                (row.get("order_id", "").strip(),),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE orderonline_followup
                    SET product = ?, product_code = ?, customer_name = ?, email = ?, phone = ?, city = ?,
                        brand_name = ?, funnel_type = ?, order_status = ?, payment_status = ?, payment_method = ?, product_price = ?, quantity = ?,
                        created_at_raw = ?, created_at_iso = ?, paid_at_raw = ?, paid_at_iso = ?, source_file = ?,
                        source_path = ?, last_seen_at = ?
                    WHERE order_id = ?
                    """,
                    payload + (row.get("order_id", "").strip(),),
                )
                result.updated += 1
            else:
                conn.execute(
                    """
                    INSERT INTO orderonline_followup (
                        product, product_code, customer_name, email, phone, city, brand_name, funnel_type, order_status, payment_status,
                        payment_method, product_price, quantity, created_at_raw, created_at_iso, paid_at_raw,
                        paid_at_iso, source_file, source_path, last_seen_at, order_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    payload + (row.get("order_id", "").strip(),),
                )
                result.inserted += 1
        conn.commit()
    return result


def auto_import_latest_orderonline_csv() -> dict:
    files = detect_orderonline_csv_files()
    if not files:
        raise ValueError("File OrderOnline terbaru tidak ditemukan di folder Downloads.")
    inserted = 0
    updated = 0
    skipped = 0
    for path in files:
        result = import_orderonline_csv(path.read_bytes(), str(path))
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


def _parse_iso_datetime(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _iso_date_only(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return raw[:10]


def _compute_priority(row) -> tuple[str, int]:
    score = 0
    payment_date = _parse_iso_datetime(row["paid_at_iso"])
    followup_date = _parse_iso_datetime(row["followup_at"])
    status = str(row["followup_status"] or "Belum Dihubungi")

    if status == "Belum Dihubungi":
        score += 50
    elif status == "Perlu Follow Up Lagi":
        score += 40
    elif status == "Tertarik":
        score += 35
    elif status == "Sudah Dihubungi":
        score += 20
    elif status == "Closing After Sales":
        score += 5

    if float(row["product_price"] or 0) >= 90000:
        score += 20

    if payment_date:
        age_days = (datetime.now() - payment_date).days
        if age_days <= 1:
            score += 20
        elif age_days <= 3:
            score += 12
        elif age_days <= 7:
            score += 6

    if followup_date:
        stale_days = (datetime.now() - followup_date).days
        if stale_days >= 2:
            score += 18
        elif stale_days >= 1:
            score += 8

    if score >= 70:
        return "Tinggi", score
    if score >= 40:
        return "Sedang", score
    return "Rendah", score


def _compute_reminder(row) -> str:
    status = str(row["followup_status"] or "Belum Dihubungi")
    payment_date = _parse_iso_datetime(row["paid_at_iso"])
    followup_date = _parse_iso_datetime(row["followup_at"])
    now = datetime.now()

    if status == "Belum Dihubungi" and payment_date and (now - payment_date).days >= 2:
        return "Belum dihubungi lebih dari 2 hari sejak pembelian."
    if status in {"Sudah Dihubungi", "Perlu Follow Up Lagi", "Tertarik"} and followup_date and (now - followup_date).days >= 2:
        return "Sudah lebih dari 2 hari sejak follow up terakhir."
    next_followup = str(row["next_followup_date"] or "").strip()
    if next_followup and next_followup <= today_str():
        return "Jadwal follow up berikutnya sudah jatuh tempo."
    return ""


def _age_segment(row) -> str:
    payment_date = _parse_iso_datetime(row["paid_at_iso"])
    if not payment_date:
        return "Tanggal Tidak Lengkap"
    age_days = (datetime.now() - payment_date).days
    if age_days <= 1:
        return "0-1 Hari"
    if age_days <= 3:
        return "2-3 Hari"
    if age_days <= 7:
        return "4-7 Hari"
    return "> 7 Hari"


def whatsapp_message(phone: str, customer_name: str, product: str, followup_status: str = "Belum Dihubungi") -> str:
    template = FOLLOWUP_MESSAGE_TEMPLATES.get(
        followup_status,
        FOLLOWUP_MESSAGE_TEMPLATES["Belum Dihubungi"],
    )
    return template.format(name=customer_name, product=product)


def whatsapp_link(phone: str, customer_name: str, product: str, followup_status: str = "Belum Dihubungi") -> str:
    cleaned = normalisasi_wa(phone)
    message = whatsapp_message(phone, customer_name, product, followup_status)
    return f"https://wa.me/{cleaned}?{urlencode({'text': message})}"


def enrich_followup_rows(rows):
    enriched = []
    for row in rows:
        item = dict(row)
        priority_label, priority_score = _compute_priority(row)
        item["order_date_raw"] = display_orderonline_datetime(item.get("created_at_raw"), item.get("created_at_iso"))
        item["order_date_iso"] = item.get("created_at_iso") or item.get("paid_at_iso") or ""
        item["payment_date_raw"] = display_orderonline_datetime(item.get("paid_at_raw"), item.get("paid_at_iso"))
        item["payment_date_iso"] = item.get("paid_at_iso") or item.get("created_at_iso") or ""
        item["priority_label"] = priority_label
        item["priority_score"] = priority_score
        item["reminder_text"] = _compute_reminder(row)
        item["age_segment"] = _age_segment(row)
        item["whatsapp_template"] = whatsapp_message(
            item["phone"],
            item["customer_name"],
            item["product"],
            item.get("followup_status") or "Belum Dihubungi",
        )
        enriched.append(item)
    enriched.sort(key=lambda item: (-int(item["priority_score"]), item.get("paid_at_iso") or "", -int(item["id_import"])))
    return enriched


def _followed_up_sql_condition(alias: str = "orderonline_followup") -> str:
    return f"""
        (
            COALESCE(TRIM({alias}.followup_status), 'Belum Dihubungi') <> 'Belum Dihubungi'
            OR TRIM(COALESCE({alias}.followup_result, '')) <> ''
            OR TRIM(COALESCE({alias}.followup_notes, '')) <> ''
            OR TRIM(COALESCE({alias}.followup_at, '')) <> ''
            OR EXISTS (
                SELECT 1
                FROM orderonline_followup_log oofl
                WHERE oofl.id_import = {alias}.id_import
            )
        )
    """


def _needs_followup_sql_condition(alias: str = "orderonline_followup") -> str:
    followed_up_condition = _followed_up_sql_condition(alias)
    return f"""
        (
            NOT ({followed_up_condition})
            OR ({alias}.next_followup_date IS NOT NULL AND date({alias}.next_followup_date) <= date('now'))
        )
    """


def is_followup_recorded(row) -> bool:
    data = dict(row)
    if str(data.get("followup_status") or "Belum Dihubungi").strip() != "Belum Dihubungi":
        return True
    if str(data.get("followup_result") or "").strip():
        return True
    if str(data.get("followup_notes") or "").strip():
        return True
    if str(data.get("followup_at") or "").strip():
        return True
    return bool(data.get("log_count") or data.get("has_followup_log"))


def list_followup_orders(
    sync_status: str = "",
    keyword: str = "",
    followup_status: str = "",
    followup_result: str = "",
    contact_state: str = "",
    brand_name: str = "",
    order_date_from: str = "",
    order_date_to: str = "",
):
    query = """
        SELECT oof.*, m.nama_member, u.nama_pengguna
        FROM orderonline_followup oof
        LEFT JOIN member m ON oof.imported_member_id = m.id_member
        LEFT JOIN tugas_crm t ON oof.imported_task_id = t.id_tugas
        LEFT JOIN pengguna u ON t.penanggung_jawab = u.id_pengguna
        WHERE 1 = 1
    """
    params: list = []
    if sync_status:
        if sync_status == "Belum Di Follow Up":
            query += f" AND NOT ({_followed_up_sql_condition('oof')})"
        else:
            query += " AND oof.sync_status = ?"
            params.append(sync_status)
    if followup_status:
        if followup_status == "Belum Dihubungi":
            query += f" AND NOT ({_followed_up_sql_condition('oof')})"
        else:
            query += " AND oof.followup_status = ?"
            params.append(followup_status)
    if followup_result:
        query += " AND oof.followup_result = ?"
        params.append(followup_result)
    if contact_state == "not_contacted":
        query += f" AND NOT ({_followed_up_sql_condition('oof')})"
    elif contact_state == "followed_up":
        query += f" AND ({_followed_up_sql_condition('oof')})"
    elif contact_state == "needs_followup":
        query += f" AND ({_needs_followup_sql_condition('oof')})"
    if brand_name:
        query += " AND COALESCE(oof.brand_name, 'Umum') = ?"
        params.append(brand_name)
    if order_date_from:
        query += " AND date(COALESCE(oof.created_at_iso, oof.paid_at_iso)) >= date(?)"
        params.append(order_date_from)
    if order_date_to:
        query += " AND date(COALESCE(oof.created_at_iso, oof.paid_at_iso)) <= date(?)"
        params.append(order_date_to)
    if keyword.strip():
        term = f"%{keyword.strip()}%"
        query += " AND (oof.customer_name LIKE ? OR oof.phone LIKE ? OR oof.product LIKE ?)"
        params.extend([term, term, term])
    query += " ORDER BY COALESCE(oof.paid_at_iso, oof.created_at_iso) DESC, oof.id_import DESC"
    return enrich_followup_rows(fetchall(query, params))


def followup_summary(brand_name: str = "") -> dict:
    where = ""
    params: tuple = ()
    if brand_name:
        where = " WHERE COALESCE(brand_name, 'Umum') = ?"
        params = (brand_name,)
    followed_up_condition = _followed_up_sql_condition("orderonline_followup")
    return {
        "total": fetchone(f"SELECT COUNT(*) AS total FROM orderonline_followup{where}", params)["total"],
        "new": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup{where}{' AND' if where else ' WHERE'} sync_status = 'Baru'",
            params,
        )["total"],
        "imported": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup{where}{' AND' if where else ' WHERE'} sync_status = 'Sudah Masuk CRM'",
            params,
        )["total"],
        "existing_member": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup{where}{' AND' if where else ' WHERE'} sync_status = 'Sudah Ada Member'",
            params,
        )["total"],
        "not_contacted": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup{where}{' AND' if where else ' WHERE'} NOT ({followed_up_condition})",
            params,
        )["total"],
        "followed_up": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup{where}{' AND' if where else ' WHERE'} ({followed_up_condition})",
            params,
        )["total"],
        "closing": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup{where}{' AND' if where else ' WHERE'} followup_status = 'Closing After Sales'",
            params,
        )["total"],
    }


def today_followup_dashboard(brand_name: str = "") -> dict:
    today = today_str()
    brand_clause = ""
    params: tuple = (today,)
    simple_params: tuple = ()
    if brand_name:
        brand_clause = " AND COALESCE(brand_name, 'Umum') = ?"
        params = (today, brand_name)
        simple_params = (brand_name,)
    return {
        "contacted_today": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup WHERE substr(COALESCE(followup_at,''),1,10) = ?{brand_clause}",
            params,
        )["total"],
        "need_followup_today": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup WHERE followup_status IN ('Belum Dihubungi', 'Perlu Follow Up Lagi'){brand_clause}",
            simple_params,
        )["total"],
        "closing_after_sales": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup WHERE followup_status = 'Closing After Sales'{brand_clause}",
            simple_params,
        )["total"],
        "latest_contacts": enrich_followup_rows(fetchall(
            """
            SELECT *
            FROM orderonline_followup
            WHERE substr(COALESCE(followup_at,''),1,10) = ?
            """ + brand_clause + """
            ORDER BY followup_at DESC, id_import DESC
            LIMIT 10
            """,
            params,
        )),
        "overdue_reminders": enrich_followup_rows(fetchall(
            """
            SELECT *
            FROM orderonline_followup
            WHERE (
                (followup_status = 'Belum Dihubungi' AND paid_at_iso IS NOT NULL AND date(paid_at_iso) <= date('now','-2 day'))
                OR
                (followup_status IN ('Sudah Dihubungi', 'Perlu Follow Up Lagi', 'Tertarik') AND followup_at IS NOT NULL AND date(followup_at) <= date('now','-2 day'))
            )
            """ + brand_clause + """
            ORDER BY COALESCE(followup_at, paid_at_iso) ASC, id_import DESC
            LIMIT 10
            """
            ,
            simple_params,
        )),
        "result_breakdown": fetchall(
            """
            SELECT COALESCE(followup_result, 'Belum Diisi') AS label, COUNT(*) AS total
            FROM orderonline_followup
            """ + (f"WHERE COALESCE(brand_name, 'Umum') = ? " if brand_name else "") + """
            GROUP BY COALESCE(followup_result, 'Belum Diisi')
            ORDER BY total DESC, label ASC
            """,
            simple_params,
        ),
    }


def followup_kpi_dashboard(brand_name: str = "") -> dict:
    today = today_str()
    join_clause = ""
    where_brand = ""
    params_today: tuple = (today,)
    params_simple: tuple = ()
    if brand_name:
        join_clause = " JOIN orderonline_followup oof ON oof.id_import = orderonline_followup_log.id_import"
        where_brand = " AND COALESCE(oof.brand_name, 'Umum') = ?"
        params_today = (today, brand_name)
        params_simple = (brand_name,)
    return {
        "contacted_today": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup_log{join_clause} WHERE substr(orderonline_followup_log.created_at,1,10) = ?{where_brand}",
            params_today,
        )["total"],
        "positive_today": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup_log{join_clause} WHERE substr(orderonline_followup_log.created_at,1,10) = ? AND outcome IN ('Respon Positif', 'Minta Info Lanjutan', 'Closing'){where_brand}",
            params_today,
        )["total"],
        "closing_today": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup_log{join_clause} WHERE substr(orderonline_followup_log.created_at,1,10) = ? AND outcome = 'Closing'{where_brand}",
            params_today,
        )["total"],
        "not_interested_today": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup_log{join_clause} WHERE substr(orderonline_followup_log.created_at,1,10) = ? AND outcome IN ({','.join('?' for _ in NEGATIVE_FOLLOWUP_RESULTS)}){where_brand}",
            (today, *NEGATIVE_FOLLOWUP_RESULTS, brand_name) if brand_name else (today, *NEGATIVE_FOLLOWUP_RESULTS),
        )["total"],
        "channel_breakdown": fetchall(
            """
            SELECT COALESCE(contact_channel, 'Manual') AS label, COUNT(*) AS total
            FROM orderonline_followup_log
            """ + (f"JOIN orderonline_followup oof ON oof.id_import = orderonline_followup_log.id_import " if brand_name else "") + """
            WHERE substr(orderonline_followup_log.created_at,1,10) = ?
            """ + (where_brand if brand_name else "") + """
            GROUP BY COALESCE(contact_channel, 'Manual')
            ORDER BY total DESC, label ASC
            """,
            params_today,
        ),
        "weekly_status_breakdown": fetchall(
            """
            SELECT COALESCE(followup_status, 'Belum Dihubungi') AS label, COUNT(*) AS total
            FROM orderonline_followup
            """ + (f"WHERE COALESCE(brand_name, 'Umum') = ? " if brand_name else "") + """
            GROUP BY COALESCE(followup_status, 'Belum Dihubungi')
            ORDER BY total DESC, label ASC
            """,
            params_simple,
        ),
        "age_segments": fetchall(
            """
            SELECT
                CASE
                    WHEN paid_at_iso IS NULL THEN 'Tanggal Tidak Lengkap'
                    WHEN julianday('now') - julianday(paid_at_iso) <= 1 THEN '0-1 Hari'
                    WHEN julianday('now') - julianday(paid_at_iso) <= 3 THEN '2-3 Hari'
                    WHEN julianday('now') - julianday(paid_at_iso) <= 7 THEN '4-7 Hari'
                    ELSE '> 7 Hari'
                END AS label,
                COUNT(*) AS total
            FROM orderonline_followup
            """ + (f"WHERE COALESCE(brand_name, 'Umum') = ? " if brand_name else "") + """
            GROUP BY label
            ORDER BY total DESC, label ASC
            """,
            params_simple,
        ),
    }


def _ensure_program(conn, product_name: str, product_code: str | None) -> int:
    row = conn.execute("SELECT id_program FROM program WHERE nama_program = ?", (product_name,)).fetchone()
    if row:
        return int(row["id_program"])
    cur = conn.execute(
        """
        INSERT INTO program (nama_program, jenis_program, status_program, dibuat_pada)
        VALUES (?, 'Webinar', 'Aktif', ?)
        """,
        (product_name, now_str()),
    )
    conn.commit()
    return int(cur.lastrowid)


def import_followup_to_crm(import_id: int, pic_id: int) -> dict:
    row = fetchone("SELECT * FROM orderonline_followup WHERE id_import = ?", (import_id,))
    if not row:
        raise ValidationError("Data OrderOnline tidak ditemukan.")

    existing_imported_member_id = int(row["imported_member_id"] or 0)
    existing_imported_task_id = int(row["imported_task_id"] or 0)
    if existing_imported_member_id:
        existing_member_row = fetchone("SELECT id_member FROM member WHERE id_member = ?", (existing_imported_member_id,))
        existing_task_row = None
        if existing_imported_task_id:
            existing_task_row = fetchone("SELECT id_tugas FROM tugas_crm WHERE id_tugas = ?", (existing_imported_task_id,))
        if existing_member_row and existing_task_row:
            return {
                "member_id": existing_imported_member_id,
                "task_id": existing_imported_task_id,
                "created_member": False,
                "already_synced": True,
            }

    phone = normalisasi_wa(row["phone"])
    existing_member = fetchone("SELECT id_member FROM member WHERE nomor_whatsapp = ?", (phone,))
    paid_date = _iso_date_only(row["paid_at_iso"]) or _iso_date_only(row["created_at_iso"]) or today_str()
    brand_name = row["brand_name"] or detect_brand(row["product"], row["product_code"], row["source_file"])
    source = fetchone("SELECT id_sumber FROM sumber_data WHERE nama_sumber = 'OrderOnline'")
    if not source:
        raise ValidationError("Sumber OrderOnline belum tersedia.")

    with get_connection() as conn:
        program_id = _ensure_program(conn, row["product"], row["product_code"])

    created_member = False
    if existing_member:
        member_id = int(existing_member["id_member"])
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE member
                SET brand_utama = COALESCE(NULLIF(brand_utama, ''), ?), diupdate_pada = ?
                WHERE id_member = ?
                """,
                (brand_name, now_str(), member_id),
            )
            conn.commit()
        sync_status = "Sudah Ada Member"
    else:
        member_id = add_member(
            MemberInput(
                nama_member=row["customer_name"],
                nomor_whatsapp=phone,
                email=row["email"] or "",
                kota=row["city"] or "",
                brand_utama=brand_name,
                id_sumber=int(source["id_sumber"]),
                penanggung_jawab=pic_id,
                status_member="Data Baru",
                tahap_progress="Belum dimulai",
                sudah_mulai_praktik=0,
                kategori_potensi="Cukup Potensial",
                tanggal_kontak_terakhir=paid_date,
                tanggal_tindak_lanjut_berikutnya=today_str(),
                ringkasan_kondisi=f"Pembeli {row['product']} dari OrderOnline dan perlu follow up after-sales.",
                langkah_berikutnya="Hubungi untuk menawarkan produk lanjutan atau program after-sales.",
            )
        )
        created_member = True
        sync_status = "Sudah Masuk CRM"

    if existing_imported_member_id and member_id != existing_imported_member_id:
        member_id = existing_imported_member_id

    purchase_exists = fetchone(
        "SELECT id_pembelian FROM riwayat_pembelian WHERE nomor_order = ?",
        (row["order_id"],),
    )
    if not purchase_exists:
        from .purchases import add_purchase

        add_purchase(
            member_id=member_id,
            program_id=program_id,
            tanggal_beli=paid_date,
            nomor_order=row["order_id"],
            nilai_transaksi=float(row["product_price"] or 0),
            brand_name=brand_name,
            status_pembelian="berhasil",
            sumber_transaksi="OrderOnline",
            catatan_pembelian=f"Import dari CSV OrderOnline untuk {row['product']}.",
        )

    note_exists = fetchone(
        """
        SELECT id_catatan
        FROM catatan_member
        WHERE id_member = ?
          AND jenis_catatan = 'Catatan Awal'
          AND isi_catatan LIKE ?
        LIMIT 1
        """,
        (member_id, f"%Order ID: {row['order_id']}.%"),
    )
    if not note_exists:
        add_note(
            member_id=member_id,
            jenis_catatan="Catatan Awal",
            isi_catatan=f"Lead after-sales diimpor dari OrderOnline. Brand: {brand_name}. Produk: {row['product']}. Order ID: {row['order_id']}.",
            dibuat_oleh=pic_id,
        )

    existing_task = None
    if existing_imported_task_id:
        existing_task = fetchone("SELECT id_tugas FROM tugas_crm WHERE id_tugas = ?", (existing_imported_task_id,))
    if existing_task:
        task_id = existing_imported_task_id
    else:
        task_id = add_task(
            member_id=member_id,
            jenis_tugas="Bahas program lanjutan",
            penanggung_jawab=pic_id,
            tanggal_jatuh_tempo=today_str(),
            prioritas="Sedang",
            catatan_tugas=f"Follow up pembeli {row['product']} untuk penawaran after-sales/produk lanjutan.",
        )

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE orderonline_followup
            SET sync_status = ?, imported_member_id = ?, imported_task_id = ?, sync_notes = ?, imported_at = ?
            WHERE id_import = ?
            """,
            (
                sync_status,
                member_id,
                task_id,
                "Member dan tugas follow up berhasil dibuat." if created_member else "Member sudah ada, tugas follow up baru dibuat.",
                now_str(),
                import_id,
            ),
        )
        conn.commit()
    return {"member_id": member_id, "task_id": task_id, "created_member": created_member}


def bulk_import_followup_to_crm(pic_id: int, sync_status: str = "Baru") -> dict:
    rows = list_followup_orders(sync_status=sync_status)
    imported = 0
    skipped = 0
    for row in rows:
        try:
            import_followup_to_crm(int(row["id_import"]), pic_id)
            imported += 1
        except Exception:
            skipped += 1
    return {"imported": imported, "skipped": skipped}


def add_followup_log(
    import_id: int,
    pic_id: int,
    action_type: str,
    contact_channel: str = "",
    outcome: str = "",
    notes: str = "",
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO orderonline_followup_log (
                id_import, action_type, contact_channel, outcome, notes, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                import_id,
                action_type,
                contact_channel.strip() or None,
                outcome.strip() or None,
                notes.strip() or None,
                pic_id,
                now_str(),
            ),
        )
        conn.commit()


def update_followup_status(
    import_id: int,
    followup_status: str,
    pic_id: int,
    followup_notes: str = "",
    followup_result: str = "",
    next_followup_date: str = "",
    contact_channel: str = "",
) -> None:
    if followup_status not in FOLLOWUP_STATUS_OPTIONS:
        raise ValidationError("Status follow up tidak valid.")
    if followup_result and followup_result not in FOLLOWUP_RESULT_OPTIONS:
        raise ValidationError("Hasil follow up tidak valid.")
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE orderonline_followup
            SET followup_status = ?, followup_notes = ?, followup_by = ?, followup_at = ?,
                followup_result = ?, next_followup_date = ?
            WHERE id_import = ?
            """,
            (
                followup_status,
                followup_notes.strip() or None,
                pic_id,
                now_str(),
                followup_result.strip() or None,
                next_followup_date.strip() or None,
                import_id,
            ),
        )
        conn.commit()
    add_followup_log(
        import_id=import_id,
        pic_id=pic_id,
        action_type="Update Follow Up",
        contact_channel=contact_channel,
        outcome=followup_result,
        notes=followup_notes,
    )


def quick_mark_whatsapp(import_id: int, pic_id: int) -> None:
    row = fetchone("SELECT followup_notes FROM orderonline_followup WHERE id_import = ?", (import_id,))
    if not row:
        raise ValidationError("Lead OrderOnline tidak ditemukan.")
    note_prefix = "Sudah kirim WhatsApp follow up."
    existing = str(row["followup_notes"] or "").strip()
    notes = note_prefix if not existing else f"{note_prefix} {existing}"
    update_followup_status(
        import_id,
        "Sudah Dihubungi",
        pic_id,
        notes,
        followup_result="Belum Ada Respon",
        contact_channel="WhatsApp",
    )


def bulk_update_followup_records(
    import_ids: list[int],
    pic_id: int | None = None,
    sync_status: str = "",
    followup_status: str = "",
) -> dict:
    valid_ids = [int(item) for item in import_ids if int(item) > 0]
    if not valid_ids:
        raise ValidationError("Minimal pilih satu prospek.")
    if followup_status and followup_status not in FOLLOWUP_STATUS_OPTIONS:
        raise ValidationError("Status follow up tidak valid.")

    updated = 0
    now = now_str()
    with get_connection() as conn:
        for import_id in valid_ids:
            fields = []
            params: list = []
            if pic_id:
                fields.append("followup_by = ?")
                params.append(pic_id)
            if sync_status:
                fields.append("sync_status = ?")
                params.append(sync_status)
            if followup_status:
                fields.extend(["followup_status = ?", "followup_at = ?"])
                params.extend([followup_status, now])
            if not fields:
                continue
            params.append(import_id)
            conn.execute(f"UPDATE orderonline_followup SET {', '.join(fields)} WHERE id_import = ?", params)
            updated += 1
        conn.commit()

    if followup_status and pic_id:
        for import_id in valid_ids:
            add_followup_log(
                import_id=import_id,
                pic_id=pic_id,
                action_type="Bulk Update Follow Up",
                notes=f"Status diubah massal menjadi {followup_status}.",
            )
    return {"updated": updated}


def export_followup_csv(
    sync_status: str = "",
    keyword: str = "",
    followup_status: str = "",
    followup_result: str = "",
    contact_state: str = "",
    brand_name: str = "",
    pic_id: str = "",
    product: str = "",
    priority: str = "",
    order_date_from: str = "",
    order_date_to: str = "",
    import_ids: list[int] | None = None,
) -> str:
    rows = list_followup_orders(
        sync_status=sync_status,
        keyword=keyword,
        followup_status=followup_status,
        followup_result=followup_result,
        contact_state=contact_state,
        brand_name=brand_name,
        order_date_from=order_date_from,
        order_date_to=order_date_to,
    )
    if product:
        rows = [row for row in rows if str(row["product"]).strip() == product]
    if priority:
        rows = [row for row in rows if str(row.get("priority_label", "")).strip() == priority]
    if pic_id:
        rows = [row for row in rows if str(row.get("followup_by") or "") == pic_id]
    if import_ids:
        selected = {int(item) for item in import_ids}
        rows = [row for row in rows if int(row["id_import"]) in selected]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "customer_name",
        "phone",
        "email",
        "brand_name",
        "product",
        "order_id",
        "paid_at",
        "payment_status",
        "sync_status",
        "followup_status",
        "followup_result",
        "next_followup_date",
        "followup_notes",
        "whatsapp_link",
    ])
    for row in rows:
        writer.writerow([
            row["customer_name"],
            row["phone"],
            row["email"] or "",
            row["brand_name"] or "",
            row["product"],
            row["order_id"],
            row["paid_at_raw"] or row["created_at_raw"] or "",
            row["payment_status"] or "",
            row["sync_status"] or "",
            row["followup_status"] or "",
            row.get("followup_result") or "",
            row.get("next_followup_date") or "",
            row["followup_notes"] or "",
            whatsapp_link(row["phone"], row["customer_name"], row["product"], row["followup_status"] or "Belum Dihubungi"),
        ])
    return output.getvalue()


def get_followup_detail(import_id: int) -> dict | None:
    row = fetchone("SELECT * FROM orderonline_followup WHERE id_import = ?", (import_id,))
    if not row:
        return None
    logs = fetchall(
        """
        SELECT l.*, u.nama_pengguna
        FROM orderonline_followup_log l
        LEFT JOIN pengguna u ON l.created_by = u.id_pengguna
        WHERE l.id_import = ?
        ORDER BY l.created_at DESC, l.id_log DESC
        """,
        (import_id,),
    )
    detail = dict(enrich_followup_rows([row])[0])
    detail["logs"] = [dict(item) for item in logs]
    return detail


def weekly_supervisor_dashboard(brand_name: str = "") -> dict:
    join_clause = ""
    where_brand = ""
    params: tuple = ()
    if brand_name:
        join_clause = " JOIN orderonline_followup oof ON oof.id_import = l.id_import"
        where_brand = " AND COALESCE(oof.brand_name, 'Umum') = ?"
        params = (brand_name,)
    return {
        "weekly_contacts": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup_log l{join_clause} WHERE date(l.created_at) >= date('now','-6 day'){where_brand}",
            params,
        )["total"],
        "weekly_unique_contacts": fetchone(
            f"SELECT COUNT(DISTINCT l.id_import) AS total FROM orderonline_followup_log l{join_clause} WHERE date(l.created_at) >= date('now','-6 day'){where_brand}",
            params,
        )["total"],
        "weekly_positive": fetchone(
            """
            SELECT COUNT(*) AS total
            FROM orderonline_followup_log l
            """ + join_clause + """
            WHERE date(l.created_at) >= date('now','-6 day')
              AND outcome IN ('Respon Positif', 'Minta Info Lanjutan', 'Closing')
            """ + where_brand,
            params,
        )["total"],
        "weekly_closing": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup_log l{join_clause} WHERE date(l.created_at) >= date('now','-6 day') AND outcome = 'Closing'{where_brand}",
            params,
        )["total"],
        "weekly_not_interested": fetchone(
            f"SELECT COUNT(*) AS total FROM orderonline_followup_log l{join_clause} WHERE date(l.created_at) >= date('now','-6 day') AND outcome IN ({','.join('?' for _ in NEGATIVE_FOLLOWUP_RESULTS)}){where_brand}",
            (*NEGATIVE_FOLLOWUP_RESULTS, brand_name) if brand_name else NEGATIVE_FOLLOWUP_RESULTS,
        )["total"],
        "weekly_pic_breakdown": fetchall(
            """
            SELECT COALESCE(u.nama_pengguna, 'Belum Ada PIC') AS label, COUNT(*) AS total
            FROM orderonline_followup_log l
            """ + join_clause + """
            LEFT JOIN pengguna u ON l.created_by = u.id_pengguna
            WHERE date(l.created_at) >= date('now','-6 day')
            """ + where_brand + """
            GROUP BY COALESCE(u.nama_pengguna, 'Belum Ada PIC')
            ORDER BY total DESC, label ASC
            """,
            params,
        ),
    }


def generate_due_followup_tasks() -> dict:
    rows = fetchall(
        """
        SELECT *
        FROM orderonline_followup
        WHERE imported_member_id IS NOT NULL
          AND next_followup_date IS NOT NULL
          AND next_followup_date <= ?
          AND (last_generated_task_date IS NULL OR last_generated_task_date <> next_followup_date)
        ORDER BY next_followup_date ASC, id_import DESC
        """,
        (today_str(),),
    )
    created = 0
    skipped = 0
    for row in rows:
        pic_id = row["followup_by"]
        if not pic_id:
            skipped += 1
            continue
        task_id = add_task(
            member_id=int(row["imported_member_id"]),
            jenis_tugas="Bahas program lanjutan",
            penanggung_jawab=int(pic_id),
            tanggal_jatuh_tempo=row["next_followup_date"],
            prioritas="Sedang",
            catatan_tugas=f"Auto-task follow up dari OrderOnline untuk {row['customer_name']} ({row['product']}).",
        )
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE orderonline_followup
                SET last_generated_task_date = ?, last_generated_task_id = ?
                WHERE id_import = ?
                """,
                (row["next_followup_date"], task_id, row["id_import"]),
            )
            conn.commit()
        created += 1
    return {"created": created, "skipped": skipped}
