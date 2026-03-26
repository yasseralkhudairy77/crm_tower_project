from __future__ import annotations

import os
import sqlite3

from flask import Flask, flash, jsonify, make_response, redirect, render_template, request, url_for

from . import __version__
from .backup import auto_backup_if_due, backup_status, create_backup, create_reset_snapshot, reset_database_contents, set_backup_dir
from .constants import (
    JENIS_CATATAN,
    JENIS_MASALAH,
    JENIS_TUGAS,
    KATEGORI_KENDALA,
    KATEGORI_POTENSI,
    PRIORITAS,
    STATUS_KENDALA,
    STATUS_MEMBER,
    STATUS_PENANGANAN,
    TAHAP_PROGRESS,
    TINGKAT_URGENSI,
)
from .database import fetchall
from .init_db import initialize_database
from .services.brands import BRAND_OPTIONS
from .services.issues import add_issue, bulk_update_issues, get_issue_detail, list_issues, update_issue
from .services.member_imports import auto_import_latest_member_csv, export_members_csv, import_member_orderonline_csv
from .services.members import (
    MemberInput,
    add_member,
    get_member_detail,
    list_members,
    search_members,
    update_member,
)
from .services.notes import add_note, latest_notes
from .services.obstacles import add_or_update_obstacle, bulk_update_obstacles, get_obstacle_detail, list_obstacles, list_obstacles_open, update_obstacle
from .services.orderonline import (
    FOLLOWUP_STATUS_OPTIONS,
    FOLLOWUP_RESULT_OPTIONS,
    auto_import_latest_orderonline_csv,
    bulk_update_followup_records,
    bulk_import_followup_to_crm,
    export_followup_csv,
    followup_summary,
    followup_kpi_dashboard,
    generate_due_followup_tasks,
    get_followup_detail,
    import_followup_to_crm,
    import_orderonline_csv,
    list_followup_orders,
    quick_mark_whatsapp,
    today_followup_dashboard,
    update_followup_status,
    whatsapp_link,
    weekly_supervisor_dashboard,
)
from .services.purchases import add_purchase
from .services.references import list_pengguna, list_program, list_sumber_data
from .services.reports import build_period_report, build_report_dashboard, dashboard_summary, important_lists
from .services.tasks import add_task, complete_task, list_tasks_overdue, list_tasks_today
from .utils.helpers import today_str
from .utils.validator import ValidationError


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("CRM_TOWER_SECRET_KEY", "crm-tower-dev-secret")

    initialize_database()
    auto_backup_if_due()

    @app.context_processor
    def inject_globals() -> dict:
        return {
            "app_version": __version__,
            "field_value": _field_value,
            "status_tone": _status_tone,
            "today_str": today_str,
            "wa_link": whatsapp_link,
        }

    @app.get("/")
    def dashboard():
        brand = request.args.get("brand", "").strip()
        all_member_rows = list_members()
        all_followup_rows = list_followup_orders()
        member_rows = _filter_members(all_member_rows, brand=brand)
        followup_rows = [row for row in all_followup_rows if not brand or str(row.get("brand_name") or "Umum") == brand]
        summary = dashboard_summary()
        followup_stats = followup_summary(brand_name=brand)
        today_followup = today_followup_dashboard(brand_name=brand)
        weekly_supervisor = weekly_supervisor_dashboard(brand_name=brand)
        brand_overview = []
        for option in BRAND_OPTIONS:
            member_count = sum(1 for row in all_member_rows if str(_field_value(row, "brand_utama", "Umum")) == option)
            prospect_count = sum(1 for row in all_followup_rows if str(row.get("brand_name") or "Umum") == option)
            pending_count = sum(
                1
                for row in all_followup_rows
                if str(row.get("brand_name") or "Umum") == option and str(row.get("followup_status") or "") == "Belum Dihubungi"
            )
            brand_overview.append(
                {
                    "brand": option,
                    "members": member_count,
                    "prospects": prospect_count,
                    "pending": pending_count,
                    "active": option == brand,
                }
            )
        member_ids = {int(row["id_member"]) for row in member_rows}
        latest_note_rows = latest_notes(30)
        if brand:
            latest_note_rows = [row for row in latest_note_rows if int(row["id_member"]) in member_ids]
        member_followup_today = sum(1 for row in member_rows if str(row["tanggal_tindak_lanjut_berikutnya"] or "") == today_str())
        member_overdue = sum(1 for row in member_rows if str(row["status_keterlambatan"] or "") == "Terlambat")
        member_blocked = sum(1 for row in member_rows if str(row["status_member"] or "") == "Masih Terkendala")
        attention_rows = [
            row for row in member_rows
            if row["status_keterlambatan"] in {"Hari Ini", "Terlambat"} or row["status_member"] == "Masih Terkendala"
        ]
        member_attention = _sort_member_rows(
            attention_rows,
            sort_by="next_followup",
            sort_dir="asc",
        )[:6]
        prospect_rows = _sort_followup_rows(
            followup_rows,
            sort_by="priority",
            sort_dir="desc",
        )[:8]
        followup_overdue = _sort_followup_rows(
            today_followup.get("overdue_reminders", []),
            sort_by="priority",
            sort_dir="desc",
        )[:6]
        dashboard_cards = [
            {
                "label": "Total Member Aktif",
                "value": len(member_rows),
                "meta": "Member yang sedang dipantau relasinya",
            },
            {
                "label": "Prospek Program Lanjutan",
                "value": followup_stats["total"],
                "meta": f"{followup_stats['not_contacted']} belum dihubungi",
            },
            {
                "label": "Follow Up Hari Ini",
                "value": today_followup.get("need_followup_today", 0),
                "meta": "Perlu ditindaklanjuti hari ini",
            },
            {
                "label": "Sudah Dihubungi Hari Ini",
                "value": today_followup.get("contacted_today", 0),
                "meta": "Aktivitas follow up yang sudah tercatat",
            },
            {
                "label": "Member Perlu Perhatian",
                "value": len(attention_rows),
                "meta": "Terlambat follow up atau masih terkendala",
            },
            {
                "label": "Closing Mingguan",
                "value": weekly_supervisor.get("weekly_closing", 0),
                "meta": "Prospek yang closing after-sales minggu ini",
            },
        ]
        return render_template(
            "dashboard.html",
            summary=summary,
            dashboard_cards=dashboard_cards,
            followup_summary=followup_stats,
            today_followup=today_followup,
            weekly_supervisor=weekly_supervisor,
            latest_notes=latest_note_rows[:6],
            member_attention=member_attention,
            latest_members=member_rows[:6],
            top_prospects=prospect_rows,
            followup_overdue=followup_overdue,
            overdue_obstacles=list_obstacles_open()[:5],
            selected_brand=brand,
            brand_options=BRAND_OPTIONS,
            brand_overview=brand_overview,
            member_followup_today=member_followup_today,
            member_overdue=member_overdue,
            member_blocked=member_blocked,
        )

    @app.route("/members", methods=["GET", "POST"])
    def members_page():
        if request.method == "POST":
            action = request.form.get("action", "upload")
            try:
                if action == "upload":
                    file = request.files.get("csv_file")
                    if not file or not file.filename:
                        raise ValueError("File CSV wajib dipilih.")
                    result = import_member_orderonline_csv(file.read(), file.filename)
                    flash(
                        f"Import member selesai. Baru: {result.inserted}, update: {result.updated}, skip: {result.skipped}.",
                        "success",
                    )
                elif action == "auto_import":
                    result = auto_import_latest_member_csv()
                    flash(
                        f"Auto-import member selesai dari {result['file_count']} file. Terakhir diproses: {result['file']}. Baru: {result['inserted']}, update: {result['updated']}, skip: {result['skipped']}.",
                        "success",
                    )
                elif action == "quick_update":
                    member_id = int(request.form.get("member_id", "0"))
                    update_member(
                        member_id,
                        {
                            "penanggung_jawab": int(request.form.get("penanggung_jawab", "0")),
                            "status_member": request.form.get("status_member", ""),
                            "tahap_progress": request.form.get("tahap_progress", ""),
                            "sudah_mulai_praktik": 1 if request.form.get("sudah_mulai_praktik") == "1" else 0,
                            "kategori_potensi": request.form.get("kategori_potensi", ""),
                            "tanggal_kontak_terakhir": request.form.get("tanggal_kontak_terakhir", ""),
                            "tanggal_tindak_lanjut_berikutnya": request.form.get("tanggal_tindak_lanjut_berikutnya", ""),
                            "ringkasan_kondisi": request.form.get("ringkasan_kondisi", ""),
                            "langkah_berikutnya": request.form.get("langkah_berikutnya", ""),
                        },
                    )
                    flash("Data member berhasil diperbarui.", "success")
                elif action == "bulk_apply":
                    selected_ids = [
                        int(item)
                        for item in request.form.get("selected_ids", "").split(",")
                        if str(item).strip().isdigit()
                    ]
                    if not selected_ids:
                        raise ValueError("Minimal pilih satu member.")
                    bulk_action = request.form.get("bulk_action", "").strip()
                    updated = 0
                    for member_id in selected_ids:
                        if bulk_action == "assign_pic":
                            update_member(member_id, {"penanggung_jawab": int(request.form.get("penanggung_jawab", "0"))})
                        elif bulk_action == "status_member":
                            update_member(member_id, {"status_member": request.form.get("status_member", "")})
                        elif bulk_action == "schedule_followup":
                            update_member(member_id, {"tanggal_tindak_lanjut_berikutnya": request.form.get("tanggal_tindak_lanjut_berikutnya", "")})
                        else:
                            raise ValueError("Aksi bulk member belum valid.")
                        updated += 1
                    flash(f"Bulk action member berhasil diterapkan ke {updated} data.", "success")
            except (ValidationError, ValueError) as exc:
                flash(str(exc), "error")
            return redirect(url_for("members_page"))

        users = list_pengguna()
        keyword = request.args.get("q", "").strip()
        status = request.args.get("status", "").strip()
        pic_id = request.args.get("pic_id", "").strip()
        brand = request.args.get("brand", "").strip()
        overdue_only = request.args.get("overdue_only", "").strip() == "1"
        sort_by = request.args.get("sort", "next_followup").strip()
        sort_dir = request.args.get("dir", "asc").strip()
        page = _safe_positive_int(request.args.get("page", "1"), 1)
        per_page = _safe_per_page(request.args.get("per_page", "25"))
        members = _filter_members(
            search_members(keyword) if keyword else list_members(),
            status=status,
            pic_id=pic_id,
            brand=brand,
            overdue_only=overdue_only,
        )
        members = _sort_member_rows(members, sort_by=sort_by, sort_dir=sort_dir)
        page_members, pagination = _paginate_rows(members, page=page, per_page=per_page)
        return render_template(
            "members.html",
            members=page_members,
            keyword=keyword,
            selected_status=status,
            selected_pic_id=pic_id,
            selected_brand=brand,
            overdue_only=overdue_only,
            users=users,
            brand_options=BRAND_OPTIONS,
            status_options=STATUS_MEMBER,
            progress_options=TAHAP_PROGRESS,
            potential_options=KATEGORI_POTENSI,
            sort_by=sort_by,
            sort_dir=sort_dir,
            pagination=pagination,
            per_page_options=[20, 25, 50, 100],
            member_stats={
                "total": len(members),
                "today_due": sum(1 for row in members if row["status_keterlambatan"] == "Hari Ini"),
                "overdue": sum(1 for row in members if row["status_keterlambatan"] == "Terlambat"),
                "practicing": sum(1 for row in members if int(row["sudah_mulai_praktik"] or 0) == 1),
                "blocked": sum(1 for row in members if row["status_member"] == "Masih Terkendala"),
                "need_attention": sum(
                    1
                    for row in members
                    if row["status_keterlambatan"] in {"Hari Ini", "Terlambat"} or row["status_member"] == "Masih Terkendala"
                ),
            },
        )

    @app.get("/members/export")
    def members_export():
        keyword = request.args.get("q", "").strip()
        status = request.args.get("status", "").strip()
        pic_id = request.args.get("pic_id", "").strip()
        brand = request.args.get("brand", "").strip()
        overdue_only = request.args.get("overdue_only", "").strip() == "1"
        export_ids = [
            int(item)
            for item in request.args.get("ids", "").split(",")
            if str(item).strip().isdigit()
        ]
        rows = _filter_members(
            search_members(keyword) if keyword else list_members(),
            status=status,
            pic_id=pic_id,
            brand=brand,
            overdue_only=overdue_only,
        )
        if export_ids:
            selected = set(export_ids)
            rows = [row for row in rows if int(row["id_member"]) in selected]
        content = export_members_csv(rows)
        response = make_response(content)
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = f'attachment; filename="member_relasi_{today_str()}.csv"'
        return response

    @app.route("/members/new", methods=["GET", "POST"])
    def member_create():
        form_data = _member_form_data()
        if request.method == "POST":
            try:
                member_id = add_member(_member_input_from_form(request.form))
                flash("Member berhasil ditambahkan.", "success")
                return redirect(url_for("member_detail", member_id=member_id))
            except ValidationError as exc:
                flash(str(exc), "error")
                form_data["values"] = request.form
        return render_template("member_form.html", mode="create", **form_data)

    @app.route("/members/<int:member_id>")
    def member_detail(member_id: int):
        detail = get_member_detail(member_id)
        if not detail:
            flash("Member tidak ditemukan.", "error")
            return redirect(url_for("members_page"))

        webinar_records = fetchall(
            """
            SELECT rw.*, pr.nama_program
            FROM riwayat_webinar rw
            JOIN program pr ON rw.id_program = pr.id_program
            WHERE rw.id_member = ?
            ORDER BY rw.tanggal_webinar DESC, rw.id_webinar_riwayat DESC
            """,
            (member_id,),
        )
        issues = fetchall(
            """
            SELECT km.*, u.nama_pengguna
            FROM keluhan_member km
            JOIN pengguna u ON km.penanggung_jawab = u.id_pengguna
            WHERE km.id_member = ?
            ORDER BY km.tanggal_masuk DESC
            """,
            (member_id,),
        )
        tasks = fetchall(
            """
            SELECT t.*, u.nama_pengguna
            FROM tugas_crm t
            JOIN pengguna u ON t.penanggung_jawab = u.id_pengguna
            WHERE t.id_member = ?
            ORDER BY t.tanggal_jatuh_tempo ASC, t.id_tugas DESC
            """,
            (member_id,),
        )
        cross_brand_followups = fetchall(
            """
            SELECT brand_name, product, order_id, paid_at_raw, created_at_raw, followup_status, sync_status
            FROM orderonline_followup
            WHERE phone = ?
            ORDER BY COALESCE(paid_at_iso, created_at_iso) DESC, id_import DESC
            LIMIT 12
            """,
            (detail["member"]["nomor_whatsapp"],),
        )
        known_brands = []
        brand_counts: dict[str, dict[str, int]] = {}
        for purchase in detail["pembelian"]:
            brand_name = str(purchase["brand_name"] or detail["member"]["brand_utama"] or "Umum")
            if brand_name not in brand_counts:
                known_brands.append(brand_name)
                brand_counts[brand_name] = {"purchases": 0, "followups": 0}
            brand_counts[brand_name]["purchases"] += 1
        for followup in cross_brand_followups:
            brand_name = str(followup["brand_name"] or "Umum")
            if brand_name not in brand_counts:
                known_brands.append(brand_name)
                brand_counts[brand_name] = {"purchases": 0, "followups": 0}
            brand_counts[brand_name]["followups"] += 1
        brand_summary = [
            {
                "brand": brand_name,
                "purchases": brand_counts[brand_name]["purchases"],
                "followups": brand_counts[brand_name]["followups"],
            }
            for brand_name in known_brands
        ]
        return render_template(
            "member_detail.html",
            detail=detail,
            webinar_records=webinar_records,
            issues=issues,
            tasks=tasks,
            cross_brand_followups=cross_brand_followups,
            brand_summary=brand_summary,
            note_types=JENIS_CATATAN,
            users=list_pengguna(),
            programs=list_program(),
            brand_options=BRAND_OPTIONS,
        )

    @app.post("/members/<int:member_id>/notes")
    def member_add_note(member_id: int):
        try:
            add_note(
                member_id=member_id,
                jenis_catatan=request.form.get("jenis_catatan", ""),
                isi_catatan=request.form.get("isi_catatan", ""),
                dibuat_oleh=int(request.form.get("dibuat_oleh", "0")),
            )
            flash("Catatan berhasil ditambahkan.", "success")
        except (ValidationError, ValueError) as exc:
            flash(str(exc), "error")
        return redirect(url_for("member_detail", member_id=member_id))

    @app.post("/members/<int:member_id>/purchases")
    def member_add_purchase(member_id: int):
        try:
            nilai_raw = request.form.get("nilai_transaksi", "").strip()
            add_purchase(
                member_id=member_id,
                program_id=int(request.form.get("program_id", "0")),
                tanggal_beli=request.form.get("tanggal_beli", ""),
                nomor_order=request.form.get("nomor_order", ""),
                nilai_transaksi=float(nilai_raw) if nilai_raw else None,
                brand_name=request.form.get("brand_name", ""),
                status_pembelian=request.form.get("status_pembelian", ""),
                sumber_transaksi=request.form.get("sumber_transaksi", ""),
                catatan_pembelian=request.form.get("catatan_pembelian", ""),
            )
            flash("Riwayat pembelian berhasil ditambahkan.", "success")
        except (ValidationError, ValueError) as exc:
            flash(str(exc), "error")
        return redirect(url_for("member_detail", member_id=member_id))

    @app.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
    def member_edit(member_id: int):
        detail = get_member_detail(member_id)
        if not detail:
            flash("Member tidak ditemukan.", "error")
            return redirect(url_for("members_page"))

        member = detail["member"]
        form_data = _member_form_data(member)
        if request.method == "POST":
            try:
                update_member(
                    member_id,
                    {
                        "kota": request.form.get("kota", ""),
                        "email": request.form.get("email", ""),
                        "penanggung_jawab": int(request.form.get("penanggung_jawab", "0")),
                        "status_member": request.form.get("status_member", ""),
                        "tahap_progress": request.form.get("tahap_progress", ""),
                        "sudah_mulai_praktik": 1 if request.form.get("sudah_mulai_praktik") == "1" else 0,
                        "kategori_potensi": request.form.get("kategori_potensi", ""),
                        "tanggal_kontak_terakhir": request.form.get("tanggal_kontak_terakhir", ""),
                        "tanggal_tindak_lanjut_berikutnya": request.form.get("tanggal_tindak_lanjut_berikutnya", ""),
                        "ringkasan_kondisi": request.form.get("ringkasan_kondisi", ""),
                        "langkah_berikutnya": request.form.get("langkah_berikutnya", ""),
                        "aktif": 1 if request.form.get("aktif") == "1" else 0,
                    },
                )
                flash("Data member berhasil diperbarui.", "success")
                return redirect(url_for("member_detail", member_id=member_id))
            except (ValidationError, ValueError) as exc:
                flash(str(exc), "error")
                form_data["values"] = request.form

        return render_template("member_form.html", mode="edit", member=member, **form_data)

    @app.get("/tasks")
    def tasks_page():
        status = request.args.get("status", "").strip()
        pic_id = request.args.get("pic_id", "").strip()
        all_tasks = _filter_tasks(
            fetchall(
            """
            SELECT t.*, m.nama_member, u.nama_pengguna
            FROM tugas_crm t
            JOIN member m ON t.id_member = m.id_member
            JOIN pengguna u ON t.penanggung_jawab = u.id_pengguna
            ORDER BY CASE t.status_tugas
                WHEN 'Terlambat' THEN 1
                WHEN 'Belum Dikerjakan' THEN 2
                WHEN 'Sedang Dikerjakan' THEN 3
                ELSE 4 END,
                t.tanggal_jatuh_tempo ASC,
                t.id_tugas DESC
            """
            ),
            status=status,
            pic_id=pic_id,
        )
        return render_template(
            "tasks.html",
            tasks_today=list_tasks_today(),
            tasks_overdue=list_tasks_overdue(),
            all_tasks=all_tasks,
            members=list_members(),
            users=list_pengguna(),
            task_types=JENIS_TUGAS,
            priorities=PRIORITAS,
            selected_status=status,
            selected_pic_id=pic_id,
            task_stats={
                "total": len(all_tasks),
                "overdue": sum(1 for row in all_tasks if row["status_tugas"] == "Terlambat"),
                "done": sum(1 for row in all_tasks if row["status_tugas"] == "Selesai"),
            },
        )

    @app.post("/tasks")
    def tasks_create():
        try:
            add_task(
                member_id=int(request.form.get("member_id", "0")),
                jenis_tugas=request.form.get("jenis_tugas", ""),
                penanggung_jawab=int(request.form.get("penanggung_jawab", "0")),
                tanggal_jatuh_tempo=request.form.get("tanggal_jatuh_tempo", ""),
                prioritas=request.form.get("prioritas", ""),
                catatan_tugas=request.form.get("catatan_tugas", ""),
            )
            flash("Tugas berhasil ditambahkan.", "success")
        except (ValidationError, ValueError) as exc:
            flash(str(exc), "error")
        return redirect(url_for("tasks_page"))

    @app.post("/tasks/<int:task_id>/complete")
    def tasks_complete(task_id: int):
        complete_task(task_id)
        flash("Tugas ditandai selesai.", "success")
        return redirect(url_for("tasks_page"))

    @app.route("/issues", methods=["GET", "POST"])
    def issues_page():
        if request.method == "POST":
            action = request.form.get("action", "create")
            try:
                if action == "update_status":
                    update_issue(
                        issue_id=int(request.form.get("issue_id", "0")),
                        status_penanganan=request.form.get("status_penanganan", ""),
                        catatan_penyelesaian=request.form.get("catatan_penyelesaian", ""),
                    )
                    flash("Status keluhan berhasil diperbarui.", "success")
                elif action == "bulk_apply":
                    selected_ids = [
                        int(item)
                        for item in request.form.get("selected_ids", "").split(",")
                        if str(item).strip().isdigit()
                    ]
                    bulk_action = request.form.get("bulk_action", "").strip()
                    if bulk_action == "assign_pic":
                        outcome = bulk_update_issues(
                            selected_ids,
                            penanggung_jawab=int(request.form.get("penanggung_jawab", "0")),
                        )
                        flash(f"Bulk assign PIC selesai untuk {outcome['updated']} keluhan.", "success")
                    elif bulk_action == "status":
                        outcome = bulk_update_issues(
                            selected_ids,
                            status_penanganan=request.form.get("status_penanganan", ""),
                        )
                        flash(f"Bulk update status selesai untuk {outcome['updated']} keluhan.", "success")
                    else:
                        raise ValueError("Aksi bulk keluhan belum valid.")
                else:
                    add_issue(
                        member_id=int(request.form.get("member_id", "0")),
                        jenis_masalah=request.form.get("jenis_masalah", ""),
                        detail_masalah=request.form.get("detail_masalah", ""),
                        prioritas=request.form.get("prioritas", ""),
                        penanggung_jawab=int(request.form.get("penanggung_jawab", "0")),
                    )
                    flash("Keluhan atau pertanyaan berhasil ditambahkan.", "success")
            except (ValidationError, ValueError) as exc:
                flash(str(exc), "error")
            return redirect(url_for("issues_page"))

        keyword = request.args.get("q", "").strip()
        status = request.args.get("status", "").strip()
        priority = request.args.get("priority", "").strip()
        pic_id = request.args.get("pic_id", "").strip()
        brand = request.args.get("brand", "").strip()
        issue_type = request.args.get("issue_type", "").strip()
        sort_by = request.args.get("sort", "date").strip()
        sort_dir = request.args.get("dir", "desc").strip()
        page = _safe_positive_int(request.args.get("page", "1"), 1)
        per_page = _safe_per_page(request.args.get("per_page", "25"))
        issues = _filter_issues(
            list_issues(),
            keyword=keyword,
            status=status,
            priority=priority,
            pic_id=pic_id,
            brand=brand,
            issue_type=issue_type,
        )
        issues = _sort_issue_rows(issues, sort_by=sort_by, sort_dir=sort_dir)
        page_rows, pagination = _paginate_rows(issues, page=page, per_page=per_page)
        return render_template(
            "issues.html",
            issues=page_rows,
            members=list_members(),
            users=list_pengguna(),
            brand_options=BRAND_OPTIONS,
            issue_types=JENIS_MASALAH,
            priorities=PRIORITAS,
            status_options=STATUS_PENANGANAN,
            selected_status=status,
            selected_priority=priority,
            selected_pic_id=pic_id,
            selected_brand=brand,
            selected_issue_type=issue_type,
            keyword=keyword,
            sort_by=sort_by,
            sort_dir=sort_dir,
            pagination=pagination,
            per_page_options=[20, 25, 50, 100],
            issue_stats={
                "total": len(issues),
                "open": sum(1 for row in issues if row["status_penanganan"] != "Selesai"),
                "high": sum(1 for row in issues if row["prioritas"] == "Tinggi"),
                "new": sum(1 for row in issues if row["status_penanganan"] == "Baru"),
                "handling": sum(1 for row in issues if row["status_penanganan"] == "Sedang Ditangani"),
                "done": sum(1 for row in issues if row["status_penanganan"] == "Selesai"),
            },
        )

    @app.route("/obstacles", methods=["GET", "POST"])
    def obstacles_page():
        if request.method == "POST":
            try:
                action = request.form.get("action", "create")
                if action == "update":
                    update_obstacle(
                        obstacle_id=int(request.form.get("obstacle_id", "0")),
                        tingkat_urgensi=request.form.get("tingkat_urgensi", ""),
                        status_kendala=request.form.get("status_kendala", ""),
                        perlu_bantuan_mentor=1 if request.form.get("perlu_bantuan_mentor") == "1" else 0,
                        solusi_awal=request.form.get("solusi_awal", ""),
                    )
                    flash("Kendala berhasil diperbarui.", "success")
                elif action == "bulk_apply":
                    selected_ids = [
                        int(item)
                        for item in request.form.get("selected_ids", "").split(",")
                        if str(item).strip().isdigit()
                    ]
                    bulk_action = request.form.get("bulk_action", "").strip()
                    if bulk_action == "assign_pic":
                        outcome = bulk_update_obstacles(
                            selected_ids,
                            dicatat_oleh=int(request.form.get("dicatat_oleh", "0")),
                        )
                        flash(f"Bulk assign PIC selesai untuk {outcome['updated']} kendala.", "success")
                    elif bulk_action == "status":
                        outcome = bulk_update_obstacles(
                            selected_ids,
                            status_kendala=request.form.get("status_kendala", ""),
                        )
                        flash(f"Bulk update status selesai untuk {outcome['updated']} kendala.", "success")
                    else:
                        raise ValueError("Aksi bulk kendala belum valid.")
                else:
                    add_or_update_obstacle(
                        member_id=int(request.form.get("member_id", "0")),
                        kategori_kendala=request.form.get("kategori_kendala", ""),
                        detail_kendala=request.form.get("detail_kendala", ""),
                        tingkat_urgensi=request.form.get("tingkat_urgensi", ""),
                        perlu_bantuan_mentor=1 if request.form.get("perlu_bantuan_mentor") == "1" else 0,
                        solusi_awal=request.form.get("solusi_awal", ""),
                        status_kendala=request.form.get("status_kendala", ""),
                        dicatat_oleh=int(request.form.get("dicatat_oleh", "0")),
                    )
                    flash("Kendala berhasil dicatat.", "success")
            except (ValidationError, ValueError) as exc:
                flash(str(exc), "error")
            return redirect(url_for("obstacles_page"))

        keyword = request.args.get("q", "").strip()
        urgency = request.args.get("urgency", "").strip()
        status = request.args.get("status", "").strip()
        brand = request.args.get("brand", "").strip()
        pic_id = request.args.get("pic_id", "").strip()
        category = request.args.get("category", "").strip()
        sort_by = request.args.get("sort", "date").strip()
        sort_dir = request.args.get("dir", "desc").strip()
        page = _safe_positive_int(request.args.get("page", "1"), 1)
        per_page = _safe_per_page(request.args.get("per_page", "25"))
        obstacles = _filter_obstacles(
            list_obstacles(include_closed=True),
            keyword=keyword,
            urgency=urgency,
            status=status,
            brand=brand,
            pic_id=pic_id,
            category=category,
        )
        obstacles = _sort_obstacle_rows(obstacles, sort_by=sort_by, sort_dir=sort_dir)
        page_rows, pagination = _paginate_rows(obstacles, page=page, per_page=per_page)
        return render_template(
            "obstacles.html",
            obstacles=page_rows,
            members=list_members(),
            users=list_pengguna(),
            brand_options=BRAND_OPTIONS,
            obstacle_categories=KATEGORI_KENDALA,
            urgency_levels=TINGKAT_URGENSI,
            obstacle_statuses=STATUS_KENDALA,
            selected_urgency=urgency,
            selected_status=status,
            selected_brand=brand,
            selected_pic_id=pic_id,
            selected_category=category,
            keyword=keyword,
            sort_by=sort_by,
            sort_dir=sort_dir,
            pagination=pagination,
            per_page_options=[20, 25, 50, 100],
            obstacle_stats={
                "total": len(obstacles),
                "urgent": sum(1 for row in obstacles if row["tingkat_urgensi"] == "Tinggi"),
                "mentor": sum(1 for row in obstacles if int(row["perlu_bantuan_mentor"] or 0) == 1),
                "open": sum(1 for row in obstacles if row["status_kendala"] != "Selesai"),
                "needs_help": sum(1 for row in obstacles if row["status_kendala"] == "Butuh Bantuan Mentor"),
                "done": sum(1 for row in obstacles if row["status_kendala"] == "Selesai"),
            },
        )

    @app.get("/reports")
    def reports_page():
        period = request.args.get("period", "daily")
        brand = request.args.get("brand", "").strip()
        try:
            report_text = build_period_report(period, brand=brand)
            report_data = build_report_dashboard(period, brand=brand)
        except ValueError:
            period = "daily"
            report_text = build_period_report(period, brand=brand)
            report_data = build_report_dashboard(period, brand=brand)
        return render_template(
            "reports.html",
            report=report_text,
            report_data=report_data,
            period=period,
            selected_brand=brand,
            brand_options=BRAND_OPTIONS,
        )

    @app.route("/peluang-lanjutan", methods=["GET", "POST"])
    @app.route("/orderonline", methods=["GET", "POST"])
    def orderonline_page():
        if request.method == "POST":
            action = request.form.get("action", "upload")
            try:
                if action == "upload":
                    file = request.files.get("csv_file")
                    if not file or not file.filename:
                        raise ValueError("File CSV wajib dipilih.")
                    result = import_orderonline_csv(file.read(), file.filename)
                    flash(
                        f"Import CSV selesai. Baru: {result.inserted}, update: {result.updated}, skip: {result.skipped}.",
                        "success",
                    )
                elif action == "auto_import":
                    result = auto_import_latest_orderonline_csv()
                    flash(
                        f"Auto-import selesai dari {result['file_count']} file. Terakhir diproses: {result['file']}. Baru: {result['inserted']}, update: {result['updated']}, skip: {result['skipped']}.",
                        "success",
                    )
                elif action == "sync_one":
                    import_id = int(request.form.get("import_id", "0"))
                    pic_id = int(request.form.get("pic_id", "0"))
                    outcome = import_followup_to_crm(import_id, pic_id)
                    flash(
                        f"Lead berhasil masuk CRM. Member #{outcome['member_id']}, tugas #{outcome['task_id']}.",
                        "success",
                    )
                elif action == "sync_bulk":
                    pic_id = int(request.form.get("pic_id", "0"))
                    outcome = bulk_import_followup_to_crm(pic_id, sync_status=request.form.get("sync_status", "Baru"))
                    flash(
                        f"Bulk import selesai. Berhasil: {outcome['imported']}, skip: {outcome['skipped']}.",
                        "success",
                    )
                elif action == "followup_status":
                    update_followup_status(
                        import_id=int(request.form.get("import_id", "0")),
                        followup_status=request.form.get("followup_status", ""),
                        pic_id=int(request.form.get("pic_id", "0")),
                        followup_notes=request.form.get("followup_notes", ""),
                        followup_result=request.form.get("followup_result", ""),
                        next_followup_date=request.form.get("next_followup_date", ""),
                        contact_channel=request.form.get("contact_channel", ""),
                    )
                    flash("Status follow up berhasil diperbarui.", "success")
                elif action == "quick_wa":
                    quick_mark_whatsapp(
                        import_id=int(request.form.get("import_id", "0")),
                        pic_id=int(request.form.get("pic_id", "0")),
                    )
                    flash("Lead ditandai sudah dihubungi via WhatsApp.", "success")
                elif action == "bulk_apply":
                    selected_ids = [
                        int(item)
                        for item in request.form.get("selected_ids", "").split(",")
                        if str(item).strip().isdigit()
                    ]
                    bulk_action = request.form.get("bulk_action", "").strip()
                    if bulk_action == "assign_pic":
                        outcome = bulk_update_followup_records(
                            selected_ids,
                            pic_id=int(request.form.get("pic_id", "0")),
                        )
                        flash(f"Bulk assign PIC selesai untuk {outcome['updated']} prospek.", "success")
                    elif bulk_action == "sync_status":
                        outcome = bulk_update_followup_records(
                            selected_ids,
                            sync_status=request.form.get("sync_status", ""),
                        )
                        flash(f"Bulk update sync status selesai untuk {outcome['updated']} prospek.", "success")
                    elif bulk_action == "followup_status":
                        outcome = bulk_update_followup_records(
                            selected_ids,
                            pic_id=int(request.form.get("pic_id", "0")),
                            followup_status=request.form.get("followup_status", ""),
                        )
                        flash(f"Bulk update follow up selesai untuk {outcome['updated']} prospek.", "success")
                    else:
                        raise ValueError("Aksi bulk belum valid.")
            except (ValidationError, ValueError) as exc:
                flash(str(exc), "error")
            return redirect(url_for("orderonline_page"))

        users = list_pengguna()
        keyword = request.args.get("q", "").strip()
        sync_status = request.args.get("sync_status", "").strip()
        followup_status = request.args.get("followup_status", "").strip()
        brand = request.args.get("brand", "").strip()
        pic_id = request.args.get("pic_id", "").strip()
        product = request.args.get("product", "").strip()
        priority = request.args.get("priority", "").strip()
        sort_by = request.args.get("sort", "order_date").strip()
        sort_dir = request.args.get("dir", "desc").strip()
        page = _safe_positive_int(request.args.get("page", "1"), 1)
        per_page = _safe_per_page(request.args.get("per_page", "25"))
        auto_task_result = generate_due_followup_tasks()
        all_rows = list_followup_orders(sync_status=sync_status, keyword=keyword, followup_status=followup_status, brand_name=brand)
        product_options = sorted({str(row["product"]).strip() for row in all_rows if str(row["product"]).strip()})
        rows = _filter_followup_rows(
            all_rows,
            pic_id=pic_id,
            brand=brand,
            product=product,
            priority=priority,
            users=users,
        )
        rows = _sort_followup_rows(rows, sort_by=sort_by, sort_dir=sort_dir)
        page_rows, pagination = _paginate_rows(rows, page=page, per_page=per_page)
        return render_template(
            "orderonline.html",
            rows=page_rows,
            total_rows=len(rows),
            keyword=keyword,
            sync_status=sync_status,
            followup_status=followup_status,
            brand=brand,
            pic_id=pic_id,
            product=product,
            priority=priority,
            sort_by=sort_by,
            sort_dir=sort_dir,
            pagination=pagination,
            summary=followup_summary(brand_name=brand),
            today_dashboard=today_followup_dashboard(brand_name=brand),
            kpi_dashboard=followup_kpi_dashboard(brand_name=brand),
            weekly_supervisor=weekly_supervisor_dashboard(brand_name=brand),
            auto_task_result=auto_task_result,
            users=users,
            brand_options=BRAND_OPTIONS,
            product_options=product_options,
            priority_options=["Tinggi", "Sedang", "Rendah"],
            per_page_options=[20, 25, 50, 100],
            sync_status_options=["Baru", "Sudah Masuk CRM", "Sudah Ada Member"],
            followup_status_options=FOLLOWUP_STATUS_OPTIONS,
            followup_result_options=FOLLOWUP_RESULT_OPTIONS,
            contact_channel_options=["WhatsApp", "Telepon", "Email", "Manual"],
        )

    @app.get("/peluang-lanjutan/<int:import_id>")
    @app.get("/orderonline/<int:import_id>")
    def orderonline_detail(import_id: int):
        detail = get_followup_detail(import_id)
        if not detail:
            flash("Data peluang lanjutan tidak ditemukan.", "error")
            return redirect(url_for("orderonline_page"))
        return render_template(
            "orderonline_detail.html",
            detail=detail,
            users=list_pengguna(),
            followup_status_options=FOLLOWUP_STATUS_OPTIONS,
            followup_result_options=FOLLOWUP_RESULT_OPTIONS,
            contact_channel_options=["WhatsApp", "Telepon", "Email", "Manual"],
        )

    @app.get("/peluang-lanjutan/export")
    @app.get("/orderonline/export")
    def orderonline_export():
        sync_status = request.args.get("sync_status", "").strip()
        keyword = request.args.get("q", "").strip()
        brand = request.args.get("brand", "").strip()
        import_ids = [
            int(item)
            for item in request.args.get("ids", "").split(",")
            if str(item).strip().isdigit()
        ]
        default_followup = "" if import_ids else "Belum Dihubungi"
        followup_status = request.args.get("followup_status", default_followup).strip()
        content = export_followup_csv(
            sync_status=sync_status,
            keyword=keyword,
            followup_status=followup_status,
            brand_name=brand,
            import_ids=import_ids,
        )
        response = make_response(content)
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = f'attachment; filename="orderonline_followup_{today_str()}.csv"'
        return response

    @app.route("/settings/backup", methods=["GET", "POST"])
    def backup_settings_page():
        if request.method == "POST":
            action = request.form.get("action", "save")
            try:
                if action == "save":
                    backup_dir = request.form.get("backup_dir", "").strip()
                    if not backup_dir:
                        raise ValueError("Folder backup wajib diisi.")
                    set_backup_dir(backup_dir)
                    flash("Folder backup berhasil disimpan.", "success")
                elif action == "run":
                    create_backup()
                    flash("Backup database berhasil dibuat.", "success")
                elif action == "reset":
                    confirmation = request.form.get("reset_confirmation", "").strip().upper()
                    if confirmation != "RESET OLEH SABRINA AULIA":
                        raise ValueError("Ketik RESET OLEH SABRINA AULIA untuk mengonfirmasi reset database.")
                    snapshot_path = create_reset_snapshot()
                    reset_database_contents()
                    initialize_database()
                    if snapshot_path:
                        flash(f"Database berhasil direset. Backup pengaman dibuat di {snapshot_path}.", "success")
                    else:
                        flash("Database berhasil direset dan diinisialisasi ulang.", "success")
            except (ValueError, OSError, sqlite3.Error) as exc:
                flash(str(exc), "error")
            return redirect(url_for("backup_settings_page"))

        return render_template("backup_settings.html", backup=backup_status())

    @app.get("/api/dashboard")
    def api_dashboard():
        return jsonify(
            {
                "summary": _serialize(dashboard_summary()),
                "lists": _serialize(important_lists()),
                "latest_notes": _serialize(latest_notes(10)),
                "open_obstacles": _serialize(list_obstacles_open()[:10]),
                "brands": BRAND_OPTIONS,
            }
        )

    @app.get("/api/references")
    def api_references():
        return jsonify(
            {
                "users": _serialize(list_pengguna()),
                "sources": _serialize(list_sumber_data()),
                "programs": _serialize(list_program()),
                "constants": {
                    "status_member": STATUS_MEMBER,
                    "progress": TAHAP_PROGRESS,
                    "potentials": KATEGORI_POTENSI,
                    "task_types": JENIS_TUGAS,
                    "priorities": PRIORITAS,
                    "issue_statuses": STATUS_PENANGANAN,
                    "issue_types": JENIS_MASALAH,
                    "obstacle_statuses": STATUS_KENDALA,
                    "obstacle_categories": KATEGORI_KENDALA,
                    "urgency_levels": TINGKAT_URGENSI,
                    "brands": BRAND_OPTIONS,
                },
            }
        )

    @app.get("/api/members")
    def api_members():
        keyword = request.args.get("q", "").strip()
        rows = _filter_members(
            search_members(keyword) if keyword else list_members(),
            status=request.args.get("status", "").strip(),
            pic_id=request.args.get("pic_id", "").strip(),
            brand=request.args.get("brand", "").strip(),
            overdue_only=request.args.get("overdue_only", "").strip() == "1",
        )
        return jsonify({"items": _serialize(rows), "total": len(rows)})

    @app.post("/api/members")
    def api_create_member():
        try:
            payload = _request_payload()
            member_id = add_member(_member_input_from_form(payload))
            return jsonify({"ok": True, "member_id": member_id}), 201
        except (ValidationError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/members/<int:member_id>")
    def api_member_detail(member_id: int):
        detail = get_member_detail(member_id)
        if not detail:
            return jsonify({"ok": False, "error": "Member tidak ditemukan."}), 404
        webinar_records = fetchall(
            """
            SELECT rw.*, pr.nama_program
            FROM riwayat_webinar rw
            JOIN program pr ON rw.id_program = pr.id_program
            WHERE rw.id_member = ?
            ORDER BY rw.tanggal_webinar DESC, rw.id_webinar_riwayat DESC
            """,
            (member_id,),
        )
        tasks = fetchall(
            """
            SELECT t.*, u.nama_pengguna
            FROM tugas_crm t
            JOIN pengguna u ON t.penanggung_jawab = u.id_pengguna
            WHERE t.id_member = ?
            ORDER BY t.tanggal_jatuh_tempo ASC, t.id_tugas DESC
            """,
            (member_id,),
        )
        return jsonify(
            {
                "ok": True,
                "detail": _serialize(detail),
                "webinar_records": _serialize(webinar_records),
                "tasks": _serialize(tasks),
            }
        )

    @app.patch("/api/members/<int:member_id>")
    def api_update_member(member_id: int):
        try:
            payload = _request_payload()
            update_member(member_id, _member_updates_from_payload(payload))
            return jsonify({"ok": True, "member_id": member_id})
        except (ValidationError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/tasks")
    def api_tasks():
        rows = _filter_tasks(
            fetchall(
                """
                SELECT t.*, m.nama_member, u.nama_pengguna
                FROM tugas_crm t
                JOIN member m ON t.id_member = m.id_member
                JOIN pengguna u ON t.penanggung_jawab = u.id_pengguna
                ORDER BY t.tanggal_jatuh_tempo ASC, t.id_tugas DESC
                """
            ),
            status=request.args.get("status", "").strip(),
            pic_id=request.args.get("pic_id", "").strip(),
        )
        return jsonify({"items": _serialize(rows), "total": len(rows)})

    @app.post("/api/tasks")
    def api_create_task():
        try:
            payload = _request_payload()
            task_id = add_task(
                member_id=int(payload.get("member_id", "0")),
                jenis_tugas=payload.get("jenis_tugas", ""),
                penanggung_jawab=int(payload.get("penanggung_jawab", "0")),
                tanggal_jatuh_tempo=payload.get("tanggal_jatuh_tempo", ""),
                prioritas=payload.get("prioritas", ""),
                catatan_tugas=payload.get("catatan_tugas", ""),
            )
            return jsonify({"ok": True, "task_id": task_id}), 201
        except (ValidationError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/tasks/<int:task_id>/complete")
    def api_complete_task(task_id: int):
        complete_task(task_id)
        return jsonify({"ok": True, "task_id": task_id})

    @app.get("/api/issues")
    def api_issues():
        rows = _filter_issues(
            list_issues(),
            keyword=request.args.get("q", "").strip(),
            status=request.args.get("status", "").strip(),
            priority=request.args.get("priority", "").strip(),
            pic_id=request.args.get("pic_id", "").strip(),
            brand=request.args.get("brand", "").strip(),
            issue_type=request.args.get("issue_type", "").strip(),
        )
        return jsonify({"items": _serialize(rows), "total": len(rows)})

    @app.get("/api/issues/<int:issue_id>")
    def api_issue_detail(issue_id: int):
        detail = get_issue_detail(issue_id)
        if not detail:
            return jsonify({"ok": False, "error": "Keluhan tidak ditemukan."}), 404
        return jsonify({"ok": True, "detail": _serialize(detail)})

    @app.post("/api/issues")
    def api_create_issue():
        try:
            payload = _request_payload()
            issue_id = add_issue(
                member_id=int(payload.get("member_id", "0")),
                jenis_masalah=payload.get("jenis_masalah", ""),
                detail_masalah=payload.get("detail_masalah", ""),
                prioritas=payload.get("prioritas", ""),
                penanggung_jawab=int(payload.get("penanggung_jawab", "0")),
            )
            return jsonify({"ok": True, "issue_id": issue_id}), 201
        except (ValidationError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.patch("/api/issues/<int:issue_id>")
    def api_update_issue(issue_id: int):
        try:
            payload = _request_payload()
            update_issue(
                issue_id=issue_id,
                status_penanganan=payload.get("status_penanganan", ""),
                catatan_penyelesaian=payload.get("catatan_penyelesaian", ""),
            )
            return jsonify({"ok": True, "issue_id": issue_id})
        except (ValidationError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/obstacles")
    def api_obstacles():
        rows = _filter_obstacles(
            list_obstacles(include_closed=True),
            keyword=request.args.get("q", "").strip(),
            urgency=request.args.get("urgency", "").strip(),
            status=request.args.get("status", "").strip(),
            brand=request.args.get("brand", "").strip(),
            pic_id=request.args.get("pic_id", "").strip(),
            category=request.args.get("category", "").strip(),
        )
        return jsonify({"items": _serialize(rows), "total": len(rows)})

    @app.get("/api/obstacles/<int:obstacle_id>")
    def api_obstacle_detail(obstacle_id: int):
        detail = get_obstacle_detail(obstacle_id)
        if not detail:
            return jsonify({"ok": False, "error": "Kendala tidak ditemukan."}), 404
        return jsonify({"ok": True, "detail": _serialize(detail)})

    @app.post("/api/obstacles")
    def api_create_obstacle():
        try:
            payload = _request_payload()
            obstacle_id = add_or_update_obstacle(
                member_id=int(payload.get("member_id", "0")),
                kategori_kendala=payload.get("kategori_kendala", ""),
                detail_kendala=payload.get("detail_kendala", ""),
                tingkat_urgensi=payload.get("tingkat_urgensi", ""),
                perlu_bantuan_mentor=1 if str(payload.get("perlu_bantuan_mentor", "0")) == "1" else 0,
                solusi_awal=payload.get("solusi_awal", ""),
                status_kendala=payload.get("status_kendala", ""),
                dicatat_oleh=int(payload.get("dicatat_oleh", "0")),
            )
            return jsonify({"ok": True, "obstacle_id": obstacle_id}), 201
        except (ValidationError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/reports")
    def api_reports():
        period = request.args.get("period", "daily")
        brand = request.args.get("brand", "").strip()
        try:
            return jsonify(
                {
                    "ok": True,
                    "period": period,
                    "brand": brand,
                    "report": build_period_report(period, brand=brand),
                    "dashboard": _serialize(build_report_dashboard(period, brand=brand)),
                }
            )
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/orderonline")
    def api_orderonline():
        rows = list_followup_orders(
            sync_status=request.args.get("sync_status", "").strip(),
            keyword=request.args.get("q", "").strip(),
            followup_status=request.args.get("followup_status", "").strip(),
            brand_name=request.args.get("brand", "").strip(),
        )
        return jsonify({
            "ok": True,
            "summary": followup_summary(brand_name=request.args.get("brand", "").strip()),
            "today_dashboard": _serialize(today_followup_dashboard(brand_name=request.args.get("brand", "").strip())),
            "kpi_dashboard": _serialize(followup_kpi_dashboard(brand_name=request.args.get("brand", "").strip())),
            "weekly_supervisor": _serialize(weekly_supervisor_dashboard(brand_name=request.args.get("brand", "").strip())),
            "auto_task_result": _serialize(generate_due_followup_tasks()),
            "items": _serialize(rows),
            "total": len(rows),
        })

    @app.get("/api/orderonline/<int:import_id>")
    def api_orderonline_detail(import_id: int):
        detail = get_followup_detail(import_id)
        if not detail:
            return jsonify({"ok": False, "error": "Lead OrderOnline tidak ditemukan."}), 404
        return jsonify({"ok": True, "detail": _serialize(detail)})

    @app.post("/api/orderonline/auto-import")
    def api_orderonline_auto_import():
        try:
            return jsonify({"ok": True, **auto_import_latest_orderonline_csv()})
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.patch("/api/orderonline/<int:import_id>/followup")
    def api_orderonline_followup(import_id: int):
        try:
            payload = _request_payload()
            update_followup_status(
                import_id=import_id,
                followup_status=payload.get("followup_status", ""),
                pic_id=int(payload.get("pic_id", "0")),
                followup_notes=payload.get("followup_notes", ""),
                followup_result=payload.get("followup_result", ""),
                next_followup_date=payload.get("next_followup_date", ""),
                contact_channel=payload.get("contact_channel", ""),
            )
            return jsonify({"ok": True, "import_id": import_id})
        except (ValidationError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/orderonline/<int:import_id>/quick-wa")
    def api_orderonline_quick_wa(import_id: int):
        try:
            payload = _request_payload()
            quick_mark_whatsapp(import_id=import_id, pic_id=int(payload.get("pic_id", "0")))
            return jsonify({"ok": True, "import_id": import_id})
        except (ValidationError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/orderonline/generate-tasks")
    def api_orderonline_generate_tasks():
        return jsonify({"ok": True, **generate_due_followup_tasks()})

    @app.get("/api/settings/backup")
    def api_backup_status():
        return jsonify({"ok": True, "backup": backup_status()})

    @app.post("/api/settings/backup")
    def api_backup_settings():
        try:
            payload = _request_payload()
            backup_dir = str(payload.get("backup_dir", "")).strip()
            if not backup_dir:
                raise ValueError("Folder backup wajib diisi.")
            set_backup_dir(backup_dir)
            return jsonify({"ok": True, "backup": backup_status()})
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/settings/backup/run")
    def api_run_backup():
        try:
            backup_path = create_backup()
            return jsonify({"ok": True, "backup_path": str(backup_path)})
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    return app


def _member_form_data(member=None) -> dict:
    return {
        "users": list_pengguna(),
        "sources": list_sumber_data(),
        "brand_options": BRAND_OPTIONS,
        "status_member_options": STATUS_MEMBER,
        "progress_options": TAHAP_PROGRESS,
        "potential_options": KATEGORI_POTENSI,
        "values": member,
    }


def _member_input_from_form(form) -> MemberInput:
    return MemberInput(
        nama_member=form.get("nama_member", ""),
        nomor_whatsapp=form.get("nomor_whatsapp", ""),
        email=form.get("email", ""),
        kota=form.get("kota", ""),
        brand_utama=form.get("brand_utama", "Umum"),
        id_sumber=int(form.get("id_sumber", "0")),
        penanggung_jawab=int(form.get("penanggung_jawab", "0")),
        status_member=form.get("status_member", ""),
        tahap_progress=form.get("tahap_progress", ""),
        sudah_mulai_praktik=1 if form.get("sudah_mulai_praktik") == "1" else 0,
        kategori_potensi=form.get("kategori_potensi", ""),
        tanggal_kontak_terakhir=form.get("tanggal_kontak_terakhir", ""),
        tanggal_tindak_lanjut_berikutnya=form.get("tanggal_tindak_lanjut_berikutnya", ""),
        ringkasan_kondisi=form.get("ringkasan_kondisi", ""),
        langkah_berikutnya=form.get("langkah_berikutnya", ""),
    )


def _member_updates_from_payload(payload) -> dict:
    return {
        "kota": payload.get("kota", ""),
        "brand_utama": payload.get("brand_utama", ""),
        "email": payload.get("email", ""),
        "penanggung_jawab": int(payload.get("penanggung_jawab", "0")),
        "status_member": payload.get("status_member", ""),
        "tahap_progress": payload.get("tahap_progress", ""),
        "sudah_mulai_praktik": 1 if str(payload.get("sudah_mulai_praktik", "0")) == "1" else 0,
        "kategori_potensi": payload.get("kategori_potensi", ""),
        "tanggal_kontak_terakhir": payload.get("tanggal_kontak_terakhir", ""),
        "tanggal_tindak_lanjut_berikutnya": payload.get("tanggal_tindak_lanjut_berikutnya", ""),
        "ringkasan_kondisi": payload.get("ringkasan_kondisi", ""),
        "langkah_berikutnya": payload.get("langkah_berikutnya", ""),
        "aktif": 1 if str(payload.get("aktif", "1")) == "1" else 0,
    }


def _request_payload():
    return request.get_json(silent=True) or request.form


def _serialize(value):
    if hasattr(value, "keys"):
        return {key: _serialize(value[key]) for key in value.keys()}
    if isinstance(value, dict):
        return {key: _serialize(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


def _filter_members(rows, status: str = "", pic_id: str = "", brand: str = "", overdue_only: bool = False):
    filtered = list(rows)
    if status:
        filtered = [row for row in filtered if row["status_member"] == status]
    if pic_id:
        filtered = [row for row in filtered if str(row["penanggung_jawab"]) == pic_id]
    if brand:
        filtered = [row for row in filtered if str(_field_value(row, "brand_utama", "Umum")) == brand]
    if overdue_only:
        filtered = [row for row in filtered if row["status_keterlambatan"] == "Terlambat"]
    return filtered


def _sort_member_rows(rows, sort_by: str = "next_followup", sort_dir: str = "asc"):
    reverse = sort_dir == "desc"

    def sort_key(row):
        if sort_by == "name":
            return str(_field_value(row, "nama_member", "")).lower()
        if sort_by == "status":
            return str(_field_value(row, "status_member", ""))
        if sort_by == "last_contact":
            return str(_field_value(row, "tanggal_kontak_terakhir", ""))
        if sort_by == "pic":
            return str(_field_value(row, "nama_pengguna", ""))
        if sort_by == "progress":
            return str(_field_value(row, "tahap_progress", ""))
        return str(_field_value(row, "tanggal_tindak_lanjut_berikutnya", ""))

    return sorted(rows, key=sort_key, reverse=reverse)


def _filter_tasks(rows, status: str = "", pic_id: str = ""):
    filtered = list(rows)
    if status:
        filtered = [row for row in filtered if row["status_tugas"] == status]
    if pic_id:
        filtered = [row for row in filtered if str(row["penanggung_jawab"]) == pic_id]
    return filtered


def _filter_issues(
    rows,
    keyword: str = "",
    status: str = "",
    priority: str = "",
    pic_id: str = "",
    brand: str = "",
    issue_type: str = "",
):
    filtered = list(rows)
    if keyword:
        term = keyword.lower()
        filtered = [
            row for row in filtered
            if term in str(_field_value(row, "nama_member", "")).lower()
            or term in str(_field_value(row, "detail_masalah", "")).lower()
            or term in str(_field_value(row, "nomor_whatsapp", "")).lower()
        ]
    if status:
        filtered = [row for row in filtered if row["status_penanganan"] == status]
    if priority:
        filtered = [row for row in filtered if row["prioritas"] == priority]
    if pic_id:
        filtered = [row for row in filtered if str(_field_value(row, "penanggung_jawab", "")) == pic_id]
    if brand:
        filtered = [row for row in filtered if str(_field_value(row, "brand_utama", "Umum")) == brand]
    if issue_type:
        filtered = [row for row in filtered if str(_field_value(row, "jenis_masalah", "")) == issue_type]
    return filtered


def _sort_issue_rows(rows, sort_by: str = "date", sort_dir: str = "desc"):
    reverse = sort_dir != "asc"

    def sort_key(row):
        if sort_by == "name":
            return str(_field_value(row, "nama_member", "")).lower()
        if sort_by == "priority":
            weight = {"Tinggi": 3, "Sedang": 2, "Rendah": 1}
            return weight.get(str(_field_value(row, "prioritas", "")), 0)
        if sort_by == "status":
            return str(_field_value(row, "status_penanganan", ""))
        if sort_by == "brand":
            return str(_field_value(row, "brand_utama", ""))
        if sort_by == "pic":
            return str(_field_value(row, "nama_pengguna", ""))
        return str(_field_value(row, "tanggal_masuk", ""))

    return sorted(rows, key=sort_key, reverse=reverse)


def _filter_obstacles(
    rows,
    keyword: str = "",
    urgency: str = "",
    status: str = "",
    brand: str = "",
    pic_id: str = "",
    category: str = "",
):
    filtered = list(rows)
    if keyword:
        term = keyword.lower()
        filtered = [
            row for row in filtered
            if term in str(_field_value(row, "nama_member", "")).lower()
            or term in str(_field_value(row, "detail_kendala", "")).lower()
            or term in str(_field_value(row, "nomor_whatsapp", "")).lower()
        ]
    if urgency:
        filtered = [row for row in filtered if row["tingkat_urgensi"] == urgency]
    if status:
        filtered = [row for row in filtered if row["status_kendala"] == status]
    if brand:
        filtered = [row for row in filtered if str(_field_value(row, "brand_utama", "Umum")) == brand]
    if pic_id:
        filtered = [row for row in filtered if str(_field_value(row, "dicatat_oleh", "")) == pic_id]
    if category:
        filtered = [row for row in filtered if str(_field_value(row, "kategori_kendala", "")) == category]
    return filtered


def _sort_obstacle_rows(rows, sort_by: str = "date", sort_dir: str = "desc"):
    reverse = sort_dir != "asc"

    def sort_key(row):
        if sort_by == "name":
            return str(_field_value(row, "nama_member", "")).lower()
        if sort_by == "urgency":
            weight = {"Tinggi": 3, "Sedang": 2, "Rendah": 1}
            return weight.get(str(_field_value(row, "tingkat_urgensi", "")), 0)
        if sort_by == "status":
            return str(_field_value(row, "status_kendala", ""))
        if sort_by == "brand":
            return str(_field_value(row, "brand_utama", ""))
        if sort_by == "pic":
            return str(_field_value(row, "nama_pengguna", ""))
        return str(_field_value(row, "tanggal_update", ""))

    return sorted(rows, key=sort_key, reverse=reverse)


def _filter_followup_rows(rows, pic_id: str = "", brand: str = "", product: str = "", priority: str = "", users=None):
    filtered = list(rows)
    if brand:
        filtered = [row for row in filtered if str(row.get("brand_name") or "Umum").strip() == brand]
    if product:
        filtered = [row for row in filtered if str(row["product"]).strip() == product]
    if priority:
        filtered = [row for row in filtered if str(row.get("priority_label", "")).strip() == priority]
    if pic_id:
        active_user_name = ""
        if users:
            for user in users:
                if str(user["id_pengguna"]) == pic_id:
                    active_user_name = str(user["nama_pengguna"])
                    break
        filtered = [
            row for row in filtered
            if str(row.get("followup_by") or "") == pic_id
            or str(row.get("nama_pengguna") or "") == active_user_name
            or (active_user_name and not row.get("nama_pengguna"))
        ]
    return filtered


def _sort_followup_rows(rows, sort_by: str = "order_date", sort_dir: str = "desc"):
    reverse = sort_dir != "asc"

    def sort_key(row):
        if sort_by == "name":
            return str(row.get("customer_name") or "").lower()
        if sort_by == "priority":
            return int(row.get("priority_score") or 0)
        if sort_by == "followup_at":
            return str(row.get("followup_at") or row.get("paid_at_iso") or row.get("created_at_iso") or "")
        if sort_by == "sync":
            return str(row.get("sync_status") or "")
        if sort_by == "status":
            return str(row.get("followup_status") or "")
        return str(row.get("paid_at_iso") or row.get("created_at_iso") or "")

    return sorted(rows, key=sort_key, reverse=reverse)


def _safe_positive_int(raw_value: str, default: int) -> int:
    try:
        value = int(raw_value)
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


def _safe_per_page(raw_value: str) -> int:
    value = _safe_positive_int(raw_value, 25)
    return value if value in {20, 25, 50, 100} else 25


def _paginate_rows(rows, page: int = 1, per_page: int = 25):
    total = len(rows)
    total_pages = max(1, (total + per_page - 1) // per_page)
    current_page = min(max(1, page), total_pages)
    start_idx = (current_page - 1) * per_page
    end_idx = start_idx + per_page
    page_rows = rows[start_idx:end_idx]
    return page_rows, {
        "page": current_page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "start": 0 if total == 0 else start_idx + 1,
        "end": min(end_idx, total),
        "has_prev": current_page > 1,
        "has_next": current_page < total_pages,
        "prev_page": current_page - 1,
        "next_page": current_page + 1,
    }


def _status_tone(value: str) -> str:
    normalized = str(value or "").strip().lower()
    danger_values = {
        "terlambat", "masih terkendala", "tinggi", "baru", "tidak jadi", "tidak aktif",
        "belum dibantu", "belum dikerjakan",
    }
    success_values = {
        "selesai", "sudah mulai praktik", "berhasil ambil", "sudah diberi", "aktif",
    }
    warning_values = {
        "hari ini", "sedang ditangani", "sedang dikerjakan", "sedang dipertimbangkan",
        "cukup potensial", "sedang", "sudah ditawarkan", "butuh bantuan mentor",
    }
    info_values = {
        "data baru", "sudah dihubungi", "sedang dipantau", "terjadwal", "sangat potensial",
        "pertanyaan", "feedback",
    }
    if normalized in danger_values:
        return "critical"
    if normalized in success_values:
        return "positive"
    if normalized in warning_values:
        return "warning"
    if normalized in info_values:
        return "info"
    return "neutral"


def _field_value(source, key: str, default=""):
    if source is None:
        return default
    if hasattr(source, "get"):
        value = source.get(key, default)
    else:
        try:
            value = source[key]
        except (KeyError, IndexError, TypeError):
            value = getattr(source, key, default)
    return default if value is None else value


if __name__ == "__main__":
    create_app().run(debug=True)
