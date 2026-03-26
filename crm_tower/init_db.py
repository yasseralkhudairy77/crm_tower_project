from __future__ import annotations

import sqlite3

from .database import get_connection
from .services.brands import detect_brand, classify_funnel
from .utils.helpers import now_str


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pengguna (
    id_pengguna INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_pengguna TEXT NOT NULL UNIQUE,
    peran TEXT NOT NULL,
    tim TEXT,
    aktif INTEGER NOT NULL DEFAULT 1,
    dibuat_pada TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sumber_data (
    id_sumber INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_sumber TEXT NOT NULL UNIQUE,
    keterangan TEXT,
    dibuat_pada TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS program (
    id_program INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_program TEXT NOT NULL UNIQUE,
    jenis_program TEXT NOT NULL,
    status_program TEXT NOT NULL DEFAULT 'Aktif',
    dibuat_pada TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS member (
    id_member INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_member TEXT NOT NULL,
    nomor_whatsapp TEXT NOT NULL UNIQUE,
    email TEXT,
    kota TEXT,
    brand_utama TEXT,
    id_sumber INTEGER NOT NULL,
    penanggung_jawab INTEGER NOT NULL,
    status_member TEXT NOT NULL,
    tahap_progress TEXT NOT NULL,
    sudah_mulai_praktik INTEGER NOT NULL DEFAULT 0,
    kategori_potensi TEXT NOT NULL,
    nilai_potensi INTEGER NOT NULL DEFAULT 0,
    tanggal_kontak_terakhir TEXT,
    tanggal_tindak_lanjut_berikutnya TEXT NOT NULL,
    status_keterlambatan TEXT NOT NULL,
    ringkasan_kondisi TEXT,
    langkah_berikutnya TEXT,
    aktif INTEGER NOT NULL DEFAULT 1,
    dibuat_pada TEXT NOT NULL,
    diupdate_pada TEXT NOT NULL,
    FOREIGN KEY (id_sumber) REFERENCES sumber_data(id_sumber),
    FOREIGN KEY (penanggung_jawab) REFERENCES pengguna(id_pengguna)
);

CREATE TABLE IF NOT EXISTS riwayat_pembelian (
    id_pembelian INTEGER PRIMARY KEY AUTOINCREMENT,
    id_member INTEGER NOT NULL,
    id_program INTEGER NOT NULL,
    tanggal_beli TEXT NOT NULL,
    nomor_order TEXT,
    nilai_transaksi REAL,
    brand_name TEXT,
    status_pembelian TEXT NOT NULL,
    sumber_transaksi TEXT,
    catatan_pembelian TEXT,
    dibuat_pada TEXT NOT NULL,
    FOREIGN KEY (id_member) REFERENCES member(id_member) ON DELETE CASCADE,
    FOREIGN KEY (id_program) REFERENCES program(id_program)
);

CREATE TABLE IF NOT EXISTS riwayat_webinar (
    id_webinar_riwayat INTEGER PRIMARY KEY AUTOINCREMENT,
    id_member INTEGER NOT NULL,
    id_program INTEGER NOT NULL,
    tanggal_webinar TEXT NOT NULL,
    status_kehadiran TEXT NOT NULL,
    status_testimoni TEXT NOT NULL DEFAULT 'Belum Diminta',
    kesan_peserta TEXT,
    potensi_lanjutan TEXT,
    catatan_webinar TEXT,
    dibuat_pada TEXT NOT NULL,
    FOREIGN KEY (id_member) REFERENCES member(id_member) ON DELETE CASCADE,
    FOREIGN KEY (id_program) REFERENCES program(id_program)
);

CREATE TABLE IF NOT EXISTS catatan_member (
    id_catatan INTEGER PRIMARY KEY AUTOINCREMENT,
    id_member INTEGER NOT NULL,
    jenis_catatan TEXT NOT NULL,
    isi_catatan TEXT NOT NULL,
    dibuat_oleh INTEGER NOT NULL,
    tanggal_catatan TEXT NOT NULL,
    FOREIGN KEY (id_member) REFERENCES member(id_member) ON DELETE CASCADE,
    FOREIGN KEY (dibuat_oleh) REFERENCES pengguna(id_pengguna)
);

CREATE TABLE IF NOT EXISTS kendala_member (
    id_kendala INTEGER PRIMARY KEY AUTOINCREMENT,
    id_member INTEGER NOT NULL,
    kategori_kendala TEXT NOT NULL,
    detail_kendala TEXT NOT NULL,
    tingkat_urgensi TEXT NOT NULL,
    perlu_bantuan_mentor INTEGER NOT NULL DEFAULT 0,
    solusi_awal TEXT,
    status_kendala TEXT NOT NULL,
    dicatat_oleh INTEGER NOT NULL,
    tanggal_dicatat TEXT NOT NULL,
    tanggal_update TEXT NOT NULL,
    FOREIGN KEY (id_member) REFERENCES member(id_member) ON DELETE CASCADE,
    FOREIGN KEY (dicatat_oleh) REFERENCES pengguna(id_pengguna)
);

CREATE TABLE IF NOT EXISTS tugas_crm (
    id_tugas INTEGER PRIMARY KEY AUTOINCREMENT,
    id_member INTEGER NOT NULL,
    jenis_tugas TEXT NOT NULL,
    penanggung_jawab INTEGER NOT NULL,
    tanggal_jatuh_tempo TEXT NOT NULL,
    prioritas TEXT NOT NULL,
    status_tugas TEXT NOT NULL,
    catatan_tugas TEXT,
    tanggal_selesai TEXT,
    dibuat_pada TEXT NOT NULL,
    FOREIGN KEY (id_member) REFERENCES member(id_member) ON DELETE CASCADE,
    FOREIGN KEY (penanggung_jawab) REFERENCES pengguna(id_pengguna)
);

CREATE TABLE IF NOT EXISTS peluang_lanjutan (
    id_peluang INTEGER PRIMARY KEY AUTOINCREMENT,
    id_member INTEGER NOT NULL,
    tingkat_potensi TEXT NOT NULL,
    alasan_potensial TEXT NOT NULL,
    masalah_utama_member TEXT,
    target_member TEXT,
    solusi_yang_cocok TEXT,
    status_penawaran TEXT NOT NULL,
    alasan_tidak_lanjut TEXT,
    penanggung_jawab INTEGER NOT NULL,
    tanggal_update TEXT NOT NULL,
    FOREIGN KEY (id_member) REFERENCES member(id_member) ON DELETE CASCADE,
    FOREIGN KEY (penanggung_jawab) REFERENCES pengguna(id_pengguna)
);

CREATE TABLE IF NOT EXISTS keluhan_member (
    id_keluhan INTEGER PRIMARY KEY AUTOINCREMENT,
    id_member INTEGER NOT NULL,
    jenis_masalah TEXT NOT NULL,
    detail_masalah TEXT NOT NULL,
    prioritas TEXT NOT NULL,
    penanggung_jawab INTEGER NOT NULL,
    status_penanganan TEXT NOT NULL,
    tanggal_masuk TEXT NOT NULL,
    tanggal_selesai TEXT,
    catatan_penyelesaian TEXT,
    FOREIGN KEY (id_member) REFERENCES member(id_member) ON DELETE CASCADE,
    FOREIGN KEY (penanggung_jawab) REFERENCES pengguna(id_pengguna)
);

CREATE TABLE IF NOT EXISTS orderonline_followup (
    id_import INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL UNIQUE,
    product TEXT NOT NULL,
    product_code TEXT,
    customer_name TEXT NOT NULL,
    email TEXT,
    phone TEXT NOT NULL,
    city TEXT,
    brand_name TEXT,
    funnel_type TEXT,
    order_status TEXT,
    payment_status TEXT,
    payment_method TEXT,
    product_price REAL,
    quantity INTEGER NOT NULL DEFAULT 1,
    created_at_raw TEXT,
    created_at_iso TEXT,
    paid_at_raw TEXT,
    paid_at_iso TEXT,
    source_file TEXT,
    sync_status TEXT NOT NULL DEFAULT 'Baru',
    imported_member_id INTEGER,
    imported_task_id INTEGER,
    sync_notes TEXT,
    imported_at TEXT,
    last_seen_at TEXT NOT NULL,
    FOREIGN KEY (imported_member_id) REFERENCES member(id_member),
    FOREIGN KEY (imported_task_id) REFERENCES tugas_crm(id_tugas)
);

CREATE TABLE IF NOT EXISTS orderonline_followup_log (
    id_log INTEGER PRIMARY KEY AUTOINCREMENT,
    id_import INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    contact_channel TEXT,
    outcome TEXT,
    notes TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (id_import) REFERENCES orderonline_followup(id_import) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES pengguna(id_pengguna)
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_member_pic_active ON member(penanggung_jawab, aktif);
CREATE INDEX IF NOT EXISTS idx_member_status_active ON member(status_member, aktif);
CREATE INDEX IF NOT EXISTS idx_member_overdue_active ON member(status_keterlambatan, aktif);
CREATE INDEX IF NOT EXISTS idx_member_brand_active ON member(brand_utama, aktif);
CREATE INDEX IF NOT EXISTS idx_member_next_followup ON member(tanggal_tindak_lanjut_berikutnya, aktif);
CREATE INDEX IF NOT EXISTS idx_member_created_at ON member(dibuat_pada);

CREATE INDEX IF NOT EXISTS idx_purchase_member_date ON riwayat_pembelian(id_member, tanggal_beli DESC);
CREATE INDEX IF NOT EXISTS idx_purchase_order ON riwayat_pembelian(nomor_order);
CREATE INDEX IF NOT EXISTS idx_purchase_brand_date ON riwayat_pembelian(brand_name, tanggal_beli DESC);

CREATE INDEX IF NOT EXISTS idx_note_member_date ON catatan_member(id_member, tanggal_catatan DESC);
CREATE INDEX IF NOT EXISTS idx_note_created_by_date ON catatan_member(dibuat_oleh, tanggal_catatan DESC);

CREATE INDEX IF NOT EXISTS idx_issue_member_date ON keluhan_member(id_member, tanggal_masuk DESC);
CREATE INDEX IF NOT EXISTS idx_issue_status_priority ON keluhan_member(status_penanganan, prioritas);
CREATE INDEX IF NOT EXISTS idx_issue_pic_status ON keluhan_member(penanggung_jawab, status_penanganan);
CREATE INDEX IF NOT EXISTS idx_issue_date ON keluhan_member(tanggal_masuk DESC);
CREATE INDEX IF NOT EXISTS idx_issue_status_priority_date ON keluhan_member(status_penanganan, prioritas, tanggal_masuk DESC);

CREATE INDEX IF NOT EXISTS idx_obstacle_member_date ON kendala_member(id_member, tanggal_update DESC);
CREATE INDEX IF NOT EXISTS idx_obstacle_status_urgency ON kendala_member(status_kendala, tingkat_urgensi);
CREATE INDEX IF NOT EXISTS idx_obstacle_pic_status ON kendala_member(dicatat_oleh, status_kendala);
CREATE INDEX IF NOT EXISTS idx_obstacle_mentor_status ON kendala_member(perlu_bantuan_mentor, status_kendala);
CREATE INDEX IF NOT EXISTS idx_obstacle_update_date ON kendala_member(tanggal_update DESC);
CREATE INDEX IF NOT EXISTS idx_obstacle_status_urgency_date ON kendala_member(status_kendala, tingkat_urgensi, tanggal_update DESC);

CREATE INDEX IF NOT EXISTS idx_task_member_status_due ON tugas_crm(id_member, status_tugas, tanggal_jatuh_tempo);
CREATE INDEX IF NOT EXISTS idx_task_pic_status_due ON tugas_crm(penanggung_jawab, status_tugas, tanggal_jatuh_tempo);
CREATE INDEX IF NOT EXISTS idx_task_done_date ON tugas_crm(tanggal_selesai);

CREATE INDEX IF NOT EXISTS idx_followup_brand_status ON orderonline_followup(brand_name, followup_status, sync_status);
CREATE INDEX IF NOT EXISTS idx_followup_phone ON orderonline_followup(phone);
CREATE INDEX IF NOT EXISTS idx_followup_member ON orderonline_followup(imported_member_id);
CREATE INDEX IF NOT EXISTS idx_followup_pic_status ON orderonline_followup(followup_by, followup_status);
CREATE INDEX IF NOT EXISTS idx_followup_next_date ON orderonline_followup(next_followup_date);
CREATE INDEX IF NOT EXISTS idx_followup_paid_date ON orderonline_followup(paid_at_iso DESC);
CREATE INDEX IF NOT EXISTS idx_followup_funnel_brand ON orderonline_followup(funnel_type, brand_name);
CREATE INDEX IF NOT EXISTS idx_followup_brand_status_paid ON orderonline_followup(brand_name, followup_status, paid_at_iso DESC);

CREATE INDEX IF NOT EXISTS idx_followup_log_import_date ON orderonline_followup_log(id_import, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_followup_log_creator_date ON orderonline_followup_log(created_by, created_at DESC);
"""


DEFAULT_PENGGUNA = [
    ("Sabrina Aulia", "PIC CRM", "CRM"),
]

DEFAULT_SUMBER = [
    ("OrderOnline", "Data transaksi dari aplikasi order online"),
    ("Histori CS", "Data hasil obrolan awal dari CS"),
    ("Webinar", "Data peserta webinar"),
    ("Input Manual", "Data yang dimasukkan manual oleh tim"),
    ("Referral", "Rujukan atau rekomendasi"),
]

DEFAULT_PROGRAM = [
    ("Webinar Berani Export Import", "Webinar"),
    ("Member Platinum", "Membership"),
    ("Kelas Premium", "Premium"),
    ("Training Berani Export Import", "Training"),
]


def create_schema() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


def create_indexes() -> None:
    with get_connection() as conn:
        conn.executescript(INDEX_SQL)
        conn.commit()


def ensure_orderonline_columns() -> None:
    additions = {
        "brand_name": "TEXT",
        "funnel_type": "TEXT",
        "followup_status": "TEXT NOT NULL DEFAULT 'Belum Dihubungi'",
        "followup_notes": "TEXT",
        "followup_at": "TEXT",
        "followup_by": "INTEGER",
        "source_path": "TEXT",
        "followup_result": "TEXT",
        "next_followup_date": "TEXT",
        "last_generated_task_date": "TEXT",
        "last_generated_task_id": "INTEGER",
    }
    with get_connection() as conn:
        try:
            rows = conn.execute("PRAGMA table_info(orderonline_followup)").fetchall()
        except sqlite3.OperationalError:
            return
        existing = {row[1] for row in rows}
        for column, definition in additions.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE orderonline_followup ADD COLUMN {column} {definition}")
        conn.commit()


def ensure_brand_columns() -> None:
    additions = {
        "member": {"brand_utama": "TEXT"},
        "riwayat_pembelian": {"brand_name": "TEXT"},
    }
    with get_connection() as conn:
        for table_name, columns in additions.items():
            try:
                rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            except sqlite3.OperationalError:
                continue
            existing = {row[1] for row in rows}
            for column, definition in columns.items():
                if column not in existing:
                    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column} {definition}")
        conn.commit()


def backfill_brand_metadata() -> None:
    with get_connection() as conn:
        order_rows = conn.execute(
            """
            SELECT id_import, product, product_code, source_file
            FROM orderonline_followup
            """
        ).fetchall()
        for row in order_rows:
            brand_name = detect_brand(row["product"], row["product_code"], row["source_file"])
            funnel_type = classify_funnel(row["product"], row["product_code"], row["source_file"])
            conn.execute(
                """
                UPDATE orderonline_followup
                SET brand_name = ?, funnel_type = ?
                WHERE id_import = ?
                """,
                (brand_name, funnel_type, row["id_import"]),
            )

        purchase_rows = conn.execute(
            """
            SELECT rp.id_pembelian, rp.brand_name, pr.nama_program
            FROM riwayat_pembelian rp
            JOIN program pr ON rp.id_program = pr.id_program
            """
        ).fetchall()
        for row in purchase_rows:
            brand_name = row["brand_name"] or detect_brand(row["nama_program"])
            conn.execute(
                "UPDATE riwayat_pembelian SET brand_name = ? WHERE id_pembelian = ?",
                (brand_name, row["id_pembelian"]),
            )

        member_rows = conn.execute(
            """
            SELECT m.id_member, m.brand_utama, pr.nama_program, rp.tanggal_beli
            FROM member m
            LEFT JOIN riwayat_pembelian rp ON rp.id_member = m.id_member
            LEFT JOIN program pr ON rp.id_program = pr.id_program
            ORDER BY m.id_member ASC, rp.tanggal_beli DESC, rp.id_pembelian DESC
            """
        ).fetchall()
        member_brand_map: dict[int, str] = {}
        for row in member_rows:
            member_id = int(row["id_member"])
            if member_id in member_brand_map:
                continue
            member_brand_map[member_id] = row["brand_utama"] or detect_brand(row["nama_program"] or "")
        for member_id, brand_name in member_brand_map.items():
            conn.execute("UPDATE member SET brand_utama = ? WHERE id_member = ?", (brand_name, member_id))
        conn.commit()


def seed_defaults() -> None:
    now = now_str()
    with get_connection() as conn:
        for nama, peran, tim in DEFAULT_PENGGUNA:
            conn.execute(
                """
                INSERT OR IGNORE INTO pengguna (nama_pengguna, peran, tim, aktif, dibuat_pada)
                VALUES (?, ?, ?, 1, ?)
                """,
                (nama, peran, tim, now),
            )
        for nama, ket in DEFAULT_SUMBER:
            conn.execute(
                """
                INSERT OR IGNORE INTO sumber_data (nama_sumber, keterangan, dibuat_pada)
                VALUES (?, ?, ?)
                """,
                (nama, ket, now),
            )
        for nama, jenis in DEFAULT_PROGRAM:
            conn.execute(
                """
                INSERT OR IGNORE INTO program (nama_program, jenis_program, status_program, dibuat_pada)
                VALUES (?, ?, 'Aktif', ?)
                """,
                (nama, jenis, now),
            )
        conn.commit()


def ensure_single_pic_user() -> None:
    now = now_str()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO pengguna (nama_pengguna, peran, tim, aktif, dibuat_pada)
            VALUES ('Sabrina Aulia', 'PIC CRM', 'CRM', 1, ?)
            """,
            (now,),
        )
        sabrina_id = conn.execute(
            "SELECT id_pengguna FROM pengguna WHERE nama_pengguna = 'Sabrina Aulia'"
        ).fetchone()[0]
        conn.execute(
            """
            UPDATE pengguna
            SET peran = 'PIC CRM', tim = 'CRM', aktif = 1
            WHERE id_pengguna = ?
            """,
            (sabrina_id,),
        )

        foreign_keys = [
            ("member", "penanggung_jawab"),
            ("catatan_member", "dibuat_oleh"),
            ("kendala_member", "dicatat_oleh"),
            ("tugas_crm", "penanggung_jawab"),
            ("peluang_lanjutan", "penanggung_jawab"),
            ("keluhan_member", "penanggung_jawab"),
            ("orderonline_followup", "followup_by"),
            ("orderonline_followup_log", "created_by"),
        ]
        for table_name, column_name in foreign_keys:
            conn.execute(
                f"UPDATE {table_name} SET {column_name} = ? WHERE {column_name} IS NOT NULL AND {column_name} != ?",
                (sabrina_id, sabrina_id),
            )

        conn.execute(
            "UPDATE pengguna SET aktif = 0 WHERE id_pengguna != ?",
            (sabrina_id,),
        )
        conn.commit()


def initialize_database() -> None:
    create_schema()
    ensure_orderonline_columns()
    ensure_brand_columns()
    create_indexes()
    seed_defaults()
    ensure_single_pic_user()
    backfill_brand_metadata()
    optimize_sqlite()


def optimize_sqlite() -> None:
    with get_connection() as conn:
        conn.execute("PRAGMA optimize;")
        conn.execute("ANALYZE;")
        conn.commit()
