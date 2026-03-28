from __future__ import annotations

from pathlib import Path

from ..database import fetchall, fetchone
from ..services.members import refresh_overdue_flags
from ..services.tasks import refresh_task_statuses
from ..utils.helpers import now_str, today_str


def _period_filter(column: str, period: str) -> tuple[str, tuple]:
    date_expr = f"date(substr({column}, 1, 10))"
    if period == "daily":
        return (f"{date_expr} = date(?)", (today_str(),))
    if period == "weekly":
        return (f"{date_expr} >= date(?,'-6 day') AND {date_expr} <= date(?)", (today_str(), today_str()))
    if period == "monthly":
        return (f"substr({column}, 1, 7) = substr(?, 1, 7)", (today_str(),))
    raise ValueError("Period report tidak valid.")


def _period_label(period: str) -> str:
    if period == "daily":
        return "Harian"
    if period == "weekly":
        return "Mingguan"
    if period == "monthly":
        return "Bulanan"
    raise ValueError("Period report tidak valid.")


def _brand_member_clause(alias: str, brand: str) -> tuple[str, tuple]:
    if not brand:
        return "", ()
    return f" AND COALESCE({alias}.brand_utama, 'Umum') = ?", (brand,)


def _brand_followup_clause(alias: str, brand: str) -> tuple[str, tuple]:
    if not brand:
        return "", ()
    return f" AND COALESCE({alias}.brand_name, 'Umum') = ?", (brand,)


def dashboard_summary() -> dict:
    refresh_overdue_flags()
    refresh_task_statuses()
    return {
        "total_member_aktif": fetchone("SELECT COUNT(*) AS total FROM member WHERE aktif = 1")["total"],
        "member_baru_hari_ini": fetchone(
            "SELECT COUNT(*) AS total FROM member WHERE substr(dibuat_pada,1,10) = ?",
            (today_str(),),
        )["total"],
        "tindak_lanjut_hari_ini": fetchone(
            "SELECT COUNT(*) AS total FROM member WHERE tanggal_tindak_lanjut_berikutnya = ? AND aktif = 1",
            (today_str(),),
        )["total"],
        "member_terlambat": fetchone(
            "SELECT COUNT(*) AS total FROM member WHERE status_keterlambatan = 'Terlambat' AND aktif = 1"
        )["total"],
        "member_terkendala": fetchone(
            "SELECT COUNT(DISTINCT id_member) AS total FROM kendala_member WHERE status_kendala <> 'Selesai'"
        )["total"],
        "peluang_sangat_potensial": 0,
        "keluhan_belum_selesai": fetchone(
            "SELECT COUNT(*) AS total FROM keluhan_member WHERE status_penanganan <> 'Selesai'"
        )["total"],
    }


def important_lists() -> dict:
    refresh_overdue_flags()
    refresh_task_statuses()
    return {
        "tugas_mendesak": fetchall(
            """
            SELECT t.id_tugas, t.jenis_tugas, t.prioritas, t.tanggal_jatuh_tempo, m.nama_member
            FROM tugas_crm t
            JOIN member m ON t.id_member = m.id_member
            WHERE t.status_tugas IN ('Belum Dikerjakan', 'Sedang Dikerjakan', 'Terlambat')
            ORDER BY CASE t.prioritas WHEN 'Tinggi' THEN 1 WHEN 'Sedang' THEN 2 ELSE 3 END,
                     t.tanggal_jatuh_tempo ASC
            LIMIT 5
            """
        ),
        "member_perhatian": fetchall(
            """
            SELECT id_member, nama_member, status_member, tanggal_tindak_lanjut_berikutnya, status_keterlambatan
            FROM member
            WHERE aktif = 1 AND (
                status_keterlambatan = 'Terlambat' OR
                status_member = 'Masih Terkendala'
            )
            ORDER BY status_keterlambatan DESC, tanggal_tindak_lanjut_berikutnya ASC
            LIMIT 5
            """
        ),
        "peluang_top": [],
    }


def build_report_dashboard(period: str, brand: str = "") -> dict:
    refresh_overdue_flags()
    refresh_task_statuses()
    label = _period_label(period)

    member_filter, member_params = _period_filter("m.dibuat_pada", period)
    followup_import_filter, followup_import_params = _period_filter("oof.imported_at", period)
    followup_contact_filter, followup_contact_params = _period_filter("l.created_at", period)
    issue_filter, issue_params = _period_filter("km.tanggal_masuk", period)
    issue_resolved_filter, issue_resolved_params = _period_filter("km.tanggal_selesai", period)
    obstacle_filter, obstacle_params = _period_filter("km.tanggal_dicatat", period)
    obstacle_update_filter, obstacle_update_params = _period_filter("km.tanggal_update", period)
    purchase_filter, purchase_params = _period_filter("rp.tanggal_beli", period)

    member_brand_clause, member_brand_params = _brand_member_clause("m", brand)
    followup_brand_clause, followup_brand_params = _brand_followup_clause("oof", brand)
    issue_brand_clause, issue_brand_params = _brand_member_clause("m", brand)
    obstacle_brand_clause, obstacle_brand_params = _brand_member_clause("m", brand)
    purchase_brand_clause = ""
    purchase_brand_params: tuple = ()
    if brand:
        purchase_brand_clause = " AND COALESCE(rp.brand_name, COALESCE(m.brand_utama, 'Umum')) = ?"
        purchase_brand_params = (brand,)

    active_members = fetchone(
        f"SELECT COUNT(*) AS total FROM member m WHERE m.aktif = 1{member_brand_clause}",
        member_brand_params,
    )["total"]
    new_members = fetchone(
        f"SELECT COUNT(*) AS total FROM member m WHERE {member_filter}{member_brand_clause}",
        member_params + member_brand_params,
    )["total"]
    followup_due = fetchone(
        f"SELECT COUNT(*) AS total FROM member m WHERE m.aktif = 1 AND m.tanggal_tindak_lanjut_berikutnya = ?{member_brand_clause}",
        (today_str(),) + member_brand_params,
    )["total"]
    overdue_members = fetchone(
        f"SELECT COUNT(*) AS total FROM member m WHERE m.aktif = 1 AND m.status_keterlambatan = 'Terlambat'{member_brand_clause}",
        member_brand_params,
    )["total"]
    new_prospects = fetchone(
        f"SELECT COUNT(*) AS total FROM orderonline_followup oof WHERE {followup_import_filter}{followup_brand_clause}",
        followup_import_params + followup_brand_params,
    )["total"]
    contacted = fetchone(
        f"""
        SELECT COUNT(*) AS total
        FROM orderonline_followup_log l
        JOIN orderonline_followup oof ON oof.id_import = l.id_import
        WHERE {followup_contact_filter}{followup_brand_clause}
        """,
        followup_contact_params + followup_brand_params,
    )["total"]
    closing = fetchone(
        f"""
        SELECT COUNT(*) AS total
        FROM orderonline_followup_log l
        JOIN orderonline_followup oof ON oof.id_import = l.id_import
        WHERE {followup_contact_filter}{followup_brand_clause}
          AND l.outcome = 'Closing'
        """,
        followup_contact_params + followup_brand_params,
    )["total"]
    issues_new = fetchone(
        f"""
        SELECT COUNT(*) AS total
        FROM keluhan_member km
        JOIN member m ON km.id_member = m.id_member
        WHERE {issue_filter}{issue_brand_clause}
        """,
        issue_params + issue_brand_params,
    )["total"]
    issues_open = fetchone(
        f"""
        SELECT COUNT(*) AS total
        FROM keluhan_member km
        JOIN member m ON km.id_member = m.id_member
        WHERE km.status_penanganan <> 'Selesai'{issue_brand_clause}
        """,
        issue_brand_params,
    )["total"]
    issues_resolved = fetchone(
        f"""
        SELECT COUNT(*) AS total
        FROM keluhan_member km
        JOIN member m ON km.id_member = m.id_member
        WHERE km.status_penanganan = 'Selesai' AND {issue_resolved_filter}{issue_brand_clause}
        """,
        issue_resolved_params + issue_brand_params,
    )["total"]
    obstacles_new = fetchone(
        f"""
        SELECT COUNT(*) AS total
        FROM kendala_member km
        JOIN member m ON km.id_member = m.id_member
        WHERE {obstacle_filter}{obstacle_brand_clause}
        """,
        obstacle_params + obstacle_brand_params,
    )["total"]
    obstacles_open = fetchone(
        f"""
        SELECT COUNT(*) AS total
        FROM kendala_member km
        JOIN member m ON km.id_member = m.id_member
        WHERE km.status_kendala <> 'Selesai'{obstacle_brand_clause}
        """,
        obstacle_brand_params,
    )["total"]
    mentor_needed = fetchone(
        f"""
        SELECT COUNT(*) AS total
        FROM kendala_member km
        JOIN member m ON km.id_member = m.id_member
        WHERE km.status_kendala <> 'Selesai' AND km.perlu_bantuan_mentor = 1{obstacle_brand_clause}
        """,
        obstacle_brand_params,
    )["total"]
    purchases = fetchone(
        f"""
        SELECT COUNT(*) AS total
        FROM riwayat_pembelian rp
        JOIN member m ON rp.id_member = m.id_member
        WHERE {purchase_filter}{purchase_brand_clause}
        """,
        purchase_params + purchase_brand_params,
    )["total"]

    kpi_cards = [
        {"label": "Member Aktif", "value": active_members, "meta": "Member aktif di CRM"},
        {"label": f"Member Baru {label}", "value": new_members, "meta": "Masuk pada periode ini"},
        {"label": f"Prospek Masuk {label}", "value": new_prospects, "meta": "Peluang lanjutan yang terimpor"},
        {"label": f"Kontak CRM {label}", "value": contacted, "meta": "Aktivitas follow up tercatat"},
        {"label": f"Closing {label}", "value": closing, "meta": "Closing after-sales tercatat"},
        {"label": "Follow Up Hari Ini", "value": followup_due, "meta": "Perlu disentuh hari ini"},
        {"label": "Member Terlambat", "value": overdue_members, "meta": "Belum ditindaklanjuti tepat waktu"},
        {"label": f"Pembelian {label}", "value": purchases, "meta": "Riwayat pembelian pada periode ini"},
    ]

    brand_breakdown = fetchall(
        """
        SELECT brand, SUM(member_count) AS member_count, SUM(prospect_count) AS prospect_count, SUM(issue_open) AS issue_open, SUM(obstacle_open) AS obstacle_open
        FROM (
            SELECT COALESCE(m.brand_utama, 'Umum') AS brand, COUNT(*) AS member_count, 0 AS prospect_count, 0 AS issue_open, 0 AS obstacle_open
            FROM member m
            WHERE m.aktif = 1
            GROUP BY COALESCE(m.brand_utama, 'Umum')
            UNION ALL
            SELECT COALESCE(oof.brand_name, 'Umum') AS brand, 0, COUNT(*), 0, 0
            FROM orderonline_followup oof
            GROUP BY COALESCE(oof.brand_name, 'Umum')
            UNION ALL
            SELECT COALESCE(m.brand_utama, 'Umum') AS brand, 0, 0, COUNT(*), 0
            FROM keluhan_member km
            JOIN member m ON km.id_member = m.id_member
            WHERE km.status_penanganan <> 'Selesai'
            GROUP BY COALESCE(m.brand_utama, 'Umum')
            UNION ALL
            SELECT COALESCE(m.brand_utama, 'Umum') AS brand, 0, 0, 0, COUNT(*)
            FROM kendala_member km
            JOIN member m ON km.id_member = m.id_member
            WHERE km.status_kendala <> 'Selesai'
            GROUP BY COALESCE(m.brand_utama, 'Umum')
        )
        GROUP BY brand
        ORDER BY member_count DESC, prospect_count DESC, brand ASC
        """
    )

    issue_by_type = fetchall(
        f"""
        SELECT km.jenis_masalah AS label, COUNT(*) AS total
        FROM keluhan_member km
        JOIN member m ON km.id_member = m.id_member
        WHERE {issue_filter}{issue_brand_clause}
        GROUP BY km.jenis_masalah
        ORDER BY total DESC, label ASC
        """,
        issue_params + issue_brand_params,
    )
    obstacle_by_category = fetchall(
        f"""
        SELECT km.kategori_kendala AS label, COUNT(*) AS total
        FROM kendala_member km
        JOIN member m ON km.id_member = m.id_member
        WHERE {obstacle_update_filter}{obstacle_brand_clause}
        GROUP BY km.kategori_kendala
        ORDER BY total DESC, label ASC
        LIMIT 6
        """,
        obstacle_update_params + obstacle_brand_params,
    )
    followup_status_breakdown = fetchall(
        f"""
        SELECT COALESCE(oof.followup_status, 'Belum Dihubungi') AS label, COUNT(*) AS total
        FROM orderonline_followup oof
        WHERE 1 = 1{followup_brand_clause}
        GROUP BY COALESCE(oof.followup_status, 'Belum Dihubungi')
        ORDER BY total DESC, label ASC
        """,
        followup_brand_params,
    )
    followup_contact_breakdown = [
        {
            "label": "Total Data yang Belum di Follow Up",
            "total": sum(
                int(row["total"])
                for row in followup_status_breakdown
                if str(row["label"] or "").strip() == "Belum Dihubungi"
            ),
        },
        {
            "label": "Total Data yang Sudah di Follow Up",
            "total": sum(
                int(row["total"])
                for row in followup_status_breakdown
                if str(row["label"] or "").strip() != "Belum Dihubungi"
            ),
        },
    ]
    active_users = fetchall("SELECT id_pengguna, nama_pengguna FROM pengguna WHERE aktif = 1 ORDER BY nama_pengguna ASC")
    pic_breakdown = []
    for user in active_users:
        user_id = int(user["id_pengguna"])
        new_members_by_pic = fetchone(
            f"SELECT COUNT(*) AS total FROM member m WHERE {member_filter} AND m.penanggung_jawab = ?{member_brand_clause}",
            member_params + (user_id,) + member_brand_params,
        )["total"]
        issues_by_pic = fetchone(
            f"""
            SELECT COUNT(*) AS total
            FROM keluhan_member km
            JOIN member m ON km.id_member = m.id_member
            WHERE {issue_filter} AND km.penanggung_jawab = ?{issue_brand_clause}
            """,
            issue_params + (user_id,) + issue_brand_params,
        )["total"]
        obstacles_by_pic = fetchone(
            f"""
            SELECT COUNT(*) AS total
            FROM kendala_member km
            JOIN member m ON km.id_member = m.id_member
            WHERE {obstacle_filter} AND km.dicatat_oleh = ?{obstacle_brand_clause}
            """,
            obstacle_params + (user_id,) + obstacle_brand_params,
        )["total"]
        pic_breakdown.append(
            {
                "label": user["nama_pengguna"],
                "new_members": new_members_by_pic,
                "issues": issues_by_pic,
                "obstacles": obstacles_by_pic,
            }
        )
    recent_activity = fetchall(
        f"""
        SELECT 'Follow Up' AS activity_type, oof.customer_name AS subject, COALESCE(oof.brand_name, 'Umum') AS brand, l.created_at AS activity_at, COALESCE(l.outcome, l.action_type) AS detail
        FROM orderonline_followup_log l
        JOIN orderonline_followup oof ON oof.id_import = l.id_import
        WHERE {followup_contact_filter}{followup_brand_clause}
        UNION ALL
        SELECT 'Keluhan' AS activity_type, m.nama_member AS subject, COALESCE(m.brand_utama, 'Umum') AS brand, km.tanggal_masuk AS activity_at, km.jenis_masalah AS detail
        FROM keluhan_member km
        JOIN member m ON km.id_member = m.id_member
        WHERE {issue_filter}{issue_brand_clause}
        UNION ALL
        SELECT 'Kendala' AS activity_type, m.nama_member AS subject, COALESCE(m.brand_utama, 'Umum') AS brand, km.tanggal_update AS activity_at, km.kategori_kendala AS detail
        FROM kendala_member km
        JOIN member m ON km.id_member = m.id_member
        WHERE {obstacle_update_filter}{obstacle_brand_clause}
        ORDER BY activity_at DESC
        LIMIT 10
        """,
        followup_contact_params + followup_brand_params + issue_params + issue_brand_params + obstacle_update_params + obstacle_brand_params,
    )

    insights = []
    if closing > 0:
        insights.append(f"Terdapat {closing} closing after-sales pada periode {label.lower()}.")
    if overdue_members > 0:
        insights.append(f"Ada {overdue_members} member terlambat follow up yang perlu perhatian khusus.")
    if mentor_needed > 0:
        insights.append(f"Terdapat {mentor_needed} kendala aktif yang membutuhkan bantuan mentor.")
    if issues_open > 0:
        insights.append(f"Masih ada {issues_open} keluhan terbuka yang perlu dituntaskan.")
    if not insights:
        insights.append("Operasional relatif stabil pada periode ini dan tidak ada indikator kritis yang menonjol.")

    return {
        "title": f"Laporan KPI CRM {label}",
        "subtitle": f"Ringkasan performa CRM {label.lower()} untuk monitoring member, peluang lanjutan, keluhan, dan kendala.",
        "period": period,
        "brand": brand,
        "generated_at": now_str(),
        "kpi_cards": kpi_cards,
        "crm_health": {
            "issues_open": issues_open,
            "issues_resolved": issues_resolved,
            "obstacles_open": obstacles_open,
            "mentor_needed": mentor_needed,
        },
        "brand_breakdown": brand_breakdown,
        "followup_contact_breakdown": followup_contact_breakdown,
        "followup_status_breakdown": followup_status_breakdown,
        "issue_by_type": issue_by_type,
        "obstacle_by_category": obstacle_by_category,
        "pic_breakdown": pic_breakdown,
        "recent_activity": recent_activity,
        "insights": insights,
    }


def build_period_report(period: str, brand: str = "") -> str:
    report = build_report_dashboard(period, brand=brand)
    lines = [
        report["title"],
        "=" * len(report["title"]),
        f"Dibuat pada: {report['generated_at']}",
        f"Brand fokus: {brand or 'Semua brand'}",
        "",
        "KPI Utama:",
    ]
    for card in report["kpi_cards"]:
        lines.append(f"- {card['label']}: {card['value']} ({card['meta']})")

    lines += ["", "Kesehatan CRM:"]
    lines.append(f"- Keluhan terbuka: {report['crm_health']['issues_open']}")
    lines.append(f"- Keluhan selesai: {report['crm_health']['issues_resolved']}")
    lines.append(f"- Kendala terbuka: {report['crm_health']['obstacles_open']}")
    lines.append(f"- Butuh bantuan mentor: {report['crm_health']['mentor_needed']}")

    lines += ["", "Breakdown Brand:"]
    for row in report["brand_breakdown"]:
        lines.append(
            f"- {row['brand']}: member={row['member_count']}, prospek={row['prospect_count']}, keluhan aktif={row['issue_open']}, kendala aktif={row['obstacle_open']}"
        )

    lines += ["", "Insight:"]
    for line in report["insights"]:
        lines.append(f"- {line}")
    return "\n".join(lines)


def export_period_report(period: str, output_dir: Path) -> Path:
    content = build_period_report(period)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"laporan_{period}_{today_str()}.txt"
    filename.write_text(content, encoding="utf-8")
    return filename


def build_supervisor_dashboard(period: str = "weekly", brand: str = "") -> dict:
    refresh_overdue_flags()
    refresh_task_statuses()
    label = _period_label(period)
    member_brand_clause, member_brand_params = _brand_member_clause("m", brand)
    followup_brand_clause, followup_brand_params = _brand_followup_clause("oof", brand)
    task_brand_clause, task_brand_params = _brand_member_clause("m", brand)

    task_period_filter, task_period_params = _period_filter("t.dibuat_pada", period)
    task_done_filter, task_done_params = _period_filter("t.tanggal_selesai", period)
    issue_period_filter, issue_period_params = _period_filter("km.tanggal_masuk", period)
    obstacle_period_filter, obstacle_period_params = _period_filter("km.tanggal_update", period)
    followup_log_filter, followup_log_params = _period_filter("l.created_at", period)

    overview_cards = [
        {
            "label": "Follow Up Hari Ini",
            "value": fetchone(
                f"SELECT COUNT(*) AS total FROM member m WHERE m.aktif = 1 AND m.tanggal_tindak_lanjut_berikutnya = ?{member_brand_clause}",
                (today_str(),) + member_brand_params,
            )["total"],
            "meta": "Member yang jatuh tempo follow up hari ini",
        },
        {
            "label": "Member Terlambat",
            "value": fetchone(
                f"SELECT COUNT(*) AS total FROM member m WHERE m.aktif = 1 AND m.status_keterlambatan = 'Terlambat'{member_brand_clause}",
                member_brand_params,
            )["total"],
            "meta": "Perlu perhatian supervisor",
        },
        {
            "label": "Tugas Hari Ini",
            "value": fetchone(
                f"""
                SELECT COUNT(*) AS total
                FROM tugas_crm t
                JOIN member m ON t.id_member = m.id_member
                WHERE t.status_tugas <> 'Selesai' AND t.tanggal_jatuh_tempo = ?{task_brand_clause}
                """,
                (today_str(),) + task_brand_params,
            )["total"],
            "meta": "Task aktif jatuh tempo hari ini",
        },
        {
            "label": "Tugas Terlambat",
            "value": fetchone(
                f"""
                SELECT COUNT(*) AS total
                FROM tugas_crm t
                JOIN member m ON t.id_member = m.id_member
                WHERE t.status_tugas = 'Terlambat'{task_brand_clause}
                """,
                task_brand_params,
            )["total"],
            "meta": "Pekerjaan yang belum selesai tepat waktu",
        },
        {
            "label": f"Kontak CRM {label}",
            "value": fetchone(
                f"""
                SELECT COUNT(*) AS total
                FROM orderonline_followup_log l
                JOIN orderonline_followup oof ON oof.id_import = l.id_import
                WHERE {followup_log_filter}{followup_brand_clause}
                """,
                followup_log_params + followup_brand_params,
            )["total"],
            "meta": "Aktivitas follow up yang tercatat",
        },
        {
            "label": f"Closing {label}",
            "value": fetchone(
                f"""
                SELECT COUNT(*) AS total
                FROM orderonline_followup_log l
                JOIN orderonline_followup oof ON oof.id_import = l.id_import
                WHERE {followup_log_filter}{followup_brand_clause} AND l.outcome = 'Closing'
                """,
                followup_log_params + followup_brand_params,
            )["total"],
            "meta": "Closing after-sales pada periode ini",
        },
    ]

    performance_snapshot = {
        "new_members": fetchone(
            f"SELECT COUNT(*) AS total FROM member m WHERE { _period_filter('m.dibuat_pada', period)[0] }{member_brand_clause}",
            _period_filter("m.dibuat_pada", period)[1] + member_brand_params,
        )["total"],
        "tasks_created": fetchone(
            f"""
            SELECT COUNT(*) AS total
            FROM tugas_crm t
            JOIN member m ON t.id_member = m.id_member
            WHERE {task_period_filter}{task_brand_clause}
            """,
            task_period_params + task_brand_params,
        )["total"],
        "tasks_done": fetchone(
            f"""
            SELECT COUNT(*) AS total
            FROM tugas_crm t
            JOIN member m ON t.id_member = m.id_member
            WHERE t.status_tugas = 'Selesai' AND {task_done_filter}{task_brand_clause}
            """,
            task_done_params + task_brand_params,
        )["total"],
        "issues_new": fetchone(
            f"""
            SELECT COUNT(*) AS total
            FROM keluhan_member km
            JOIN member m ON km.id_member = m.id_member
            WHERE {issue_period_filter}{member_brand_clause}
            """,
            issue_period_params + member_brand_params,
        )["total"],
        "issues_open": fetchone(
            f"""
            SELECT COUNT(*) AS total
            FROM keluhan_member km
            JOIN member m ON km.id_member = m.id_member
            WHERE km.status_penanganan <> 'Selesai'{member_brand_clause}
            """,
            member_brand_params,
        )["total"],
        "obstacles_open": fetchone(
            f"""
            SELECT COUNT(*) AS total
            FROM kendala_member km
            JOIN member m ON km.id_member = m.id_member
            WHERE km.status_kendala <> 'Selesai'{member_brand_clause}
            """,
            member_brand_params,
        )["total"],
        "mentor_needed": fetchone(
            f"""
            SELECT COUNT(*) AS total
            FROM kendala_member km
            JOIN member m ON km.id_member = m.id_member
            WHERE km.status_kendala <> 'Selesai' AND km.perlu_bantuan_mentor = 1{member_brand_clause}
            """,
            member_brand_params,
        )["total"],
        "obstacles_updated": fetchone(
            f"""
            SELECT COUNT(*) AS total
            FROM kendala_member km
            JOIN member m ON km.id_member = m.id_member
            WHERE {obstacle_period_filter}{member_brand_clause}
            """,
            obstacle_period_params + member_brand_params,
        )["total"],
    }

    pic_scorecards = fetchall(
        f"""
        SELECT
            u.id_pengguna,
            u.nama_pengguna,
            (
                SELECT COUNT(*)
                FROM orderonline_followup_log l
                JOIN orderonline_followup oof ON oof.id_import = l.id_import
                WHERE l.created_by = u.id_pengguna
                  AND {followup_log_filter}{followup_brand_clause}
            ) AS followups_logged,
            (
                SELECT COUNT(*)
                FROM orderonline_followup_log l
                JOIN orderonline_followup oof ON oof.id_import = l.id_import
                WHERE l.created_by = u.id_pengguna
                  AND {followup_log_filter}{followup_brand_clause}
                  AND l.outcome IN ('Respon Positif', 'Minta Info Lanjutan', 'Closing')
            ) AS positive_outcomes,
            (
                SELECT COUNT(*)
                FROM orderonline_followup_log l
                JOIN orderonline_followup oof ON oof.id_import = l.id_import
                WHERE l.created_by = u.id_pengguna
                  AND {followup_log_filter}{followup_brand_clause}
                  AND l.outcome = 'Closing'
            ) AS closing_total,
            (
                SELECT COUNT(*)
                FROM tugas_crm t
                JOIN member m ON t.id_member = m.id_member
                WHERE t.penanggung_jawab = u.id_pengguna
                  AND t.status_tugas <> 'Selesai'{task_brand_clause}
            ) AS active_tasks,
            (
                SELECT COUNT(*)
                FROM tugas_crm t
                JOIN member m ON t.id_member = m.id_member
                WHERE t.penanggung_jawab = u.id_pengguna
                  AND t.status_tugas = 'Terlambat'{task_brand_clause}
            ) AS overdue_tasks,
            (
                SELECT COUNT(*)
                FROM member m
                WHERE m.penanggung_jawab = u.id_pengguna
                  AND m.aktif = 1
                  AND m.status_keterlambatan = 'Terlambat'{member_brand_clause}
            ) AS overdue_members
        FROM pengguna u
        WHERE u.aktif = 1
        ORDER BY u.nama_pengguna ASC
        """,
        followup_log_params + followup_brand_params
        + followup_log_params + followup_brand_params
        + followup_log_params + followup_brand_params
        + task_brand_params
        + task_brand_params
        + member_brand_params,
    )

    urgent_tasks = fetchall(
        f"""
        SELECT t.id_tugas, t.jenis_tugas, t.prioritas, t.status_tugas, t.tanggal_jatuh_tempo, m.nama_member, u.nama_pengguna
        FROM tugas_crm t
        JOIN member m ON t.id_member = m.id_member
        JOIN pengguna u ON t.penanggung_jawab = u.id_pengguna
        WHERE t.status_tugas IN ('Belum Dikerjakan', 'Sedang Dikerjakan', 'Terlambat'){task_brand_clause}
        ORDER BY
            CASE t.status_tugas WHEN 'Terlambat' THEN 0 WHEN 'Sedang Dikerjakan' THEN 1 ELSE 2 END,
            CASE t.prioritas WHEN 'Tinggi' THEN 0 WHEN 'Sedang' THEN 1 ELSE 2 END,
            t.tanggal_jatuh_tempo ASC,
            t.id_tugas DESC
        LIMIT 8
        """,
        task_brand_params,
    )
    overdue_members = fetchall(
        f"""
        SELECT id_member, nama_member, nomor_whatsapp, status_member, tanggal_tindak_lanjut_berikutnya, status_keterlambatan, nama_pengguna
        FROM (
            SELECT m.id_member, m.nama_member, m.nomor_whatsapp, m.status_member, m.tanggal_tindak_lanjut_berikutnya, m.status_keterlambatan, u.nama_pengguna
            FROM member m
            LEFT JOIN pengguna u ON m.penanggung_jawab = u.id_pengguna
            WHERE m.aktif = 1
              AND (m.status_keterlambatan = 'Terlambat' OR m.status_member = 'Masih Terkendala'){member_brand_clause}
        )
        ORDER BY status_keterlambatan DESC, tanggal_tindak_lanjut_berikutnya ASC, id_member DESC
        LIMIT 8
        """,
        member_brand_params,
    )
    pending_followups = fetchall(
        f"""
        SELECT oof.id_import, oof.customer_name, oof.phone, oof.product, oof.followup_status, oof.followup_result, oof.next_followup_date, COALESCE(u.nama_pengguna, 'Belum Ada PIC') AS nama_pengguna
        FROM orderonline_followup oof
        LEFT JOIN pengguna u ON oof.followup_by = u.id_pengguna
        WHERE (
            oof.followup_status = 'Belum Dihubungi'
            OR (oof.next_followup_date IS NOT NULL AND oof.next_followup_date <= ?)
        ){followup_brand_clause}
        ORDER BY
            CASE COALESCE(oof.followup_status, 'Belum Dihubungi')
                WHEN 'Belum Dihubungi' THEN 0
                WHEN 'Perlu Follow Up Lagi' THEN 1
                WHEN 'Tertarik' THEN 2
                ELSE 3
            END,
            COALESCE(oof.next_followup_date, substr(COALESCE(oof.paid_at_iso, oof.created_at_iso), 1, 10)) ASC,
            oof.id_import DESC
        LIMIT 8
        """,
        (today_str(),) + followup_brand_params,
    )
    recent_activity = fetchall(
        f"""
        SELECT activity_type, subject, pic_name, detail, activity_at
        FROM (
            SELECT 'Follow Up' AS activity_type, oof.customer_name AS subject, COALESCE(u.nama_pengguna, 'Belum Ada PIC') AS pic_name, COALESCE(l.outcome, l.action_type, 'Update') AS detail, l.created_at AS activity_at
            FROM orderonline_followup_log l
            JOIN orderonline_followup oof ON oof.id_import = l.id_import
            LEFT JOIN pengguna u ON l.created_by = u.id_pengguna
            WHERE {followup_log_filter}{followup_brand_clause}
            UNION ALL
            SELECT 'Tugas' AS activity_type, m.nama_member AS subject, COALESCE(u.nama_pengguna, 'Belum Ada PIC') AS pic_name, t.status_tugas AS detail, COALESCE(t.tanggal_selesai, t.dibuat_pada) AS activity_at
            FROM tugas_crm t
            JOIN member m ON t.id_member = m.id_member
            LEFT JOIN pengguna u ON t.penanggung_jawab = u.id_pengguna
            WHERE ({task_period_filter} OR {task_done_filter}){task_brand_clause}
            UNION ALL
            SELECT 'Kendala' AS activity_type, m.nama_member AS subject, COALESCE(u.nama_pengguna, 'Belum Ada PIC') AS pic_name, km.kategori_kendala AS detail, km.tanggal_update AS activity_at
            FROM kendala_member km
            JOIN member m ON km.id_member = m.id_member
            LEFT JOIN pengguna u ON km.dicatat_oleh = u.id_pengguna
            WHERE {obstacle_period_filter}{member_brand_clause}
        )
        ORDER BY activity_at DESC
        LIMIT 12
        """,
        followup_log_params + followup_brand_params
        + task_period_params + task_done_params + task_brand_params
        + obstacle_period_params + member_brand_params,
    )

    supervision_notes = []
    overdue_task_total = overview_cards[3]["value"]
    overdue_member_total = overview_cards[1]["value"]
    if overdue_task_total:
        supervision_notes.append(f"Ada {overdue_task_total} tugas terlambat yang perlu dibahas supervisor.")
    if overdue_member_total:
        supervision_notes.append(f"Ada {overdue_member_total} member overdue atau masih terkendala yang perlu diprioritaskan.")
    if performance_snapshot["mentor_needed"]:
        supervision_notes.append(f"{performance_snapshot['mentor_needed']} kendala aktif sedang membutuhkan bantuan mentor.")
    if not supervision_notes:
        supervision_notes.append("Operasional CRM relatif stabil dan tidak ada indikator kritis yang menonjol saat ini.")

    return {
        "title": "Dashboard Monitoring Supervisor",
        "subtitle": f"Pantau progres kerja CRM, beban follow up, dan kualitas penyelesaian masalah pada periode {label.lower()}.",
        "period": period,
        "brand": brand,
        "generated_at": now_str(),
        "overview_cards": overview_cards,
        "performance_snapshot": performance_snapshot,
        "pic_scorecards": pic_scorecards,
        "urgent_tasks": urgent_tasks,
        "overdue_members": overdue_members,
        "pending_followups": pending_followups,
        "recent_activity": recent_activity,
        "notes": supervision_notes,
    }
