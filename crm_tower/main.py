from __future__ import annotations

import argparse

from . import __version__
from .backup import auto_backup_if_due
from .init_db import initialize_database
from .menus.menu_keluhan import menu_keluhan
from .menus.menu_laporan import menu_laporan
from .menus.menu_member import menu_data_member
from .menus.menu_pengaturan import show_pengaturan
from .menus.menu_platinum import menu_platinum
from .menus.menu_ringkasan import show_ringkasan
from .menus.menu_webinar import menu_webinar
from .services.references import list_pengguna
from .utils.helpers import now_str
from .web import create_app


def run_cli() -> None:
    initialize_database()
    auto_backup_if_due()
    while True:
        print("\n" + "=" * 72)
        print(f"CRM Tower v{__version__}")
        print("=" * 72)
        print("1. Ringkasan")
        print("2. Data Member")
        print("3. Pantauan Setelah Webinar")
        print("4. Pantauan Member Platinum")
        print("5. Keluhan & Pertanyaan")
        print("6. Laporan Tim")
        print("7. Pengaturan Dasar")
        print("0. Keluar")
        choice = input("Pilih menu: ").strip()
        if choice == "1":
            show_ringkasan()
        elif choice == "2":
            menu_data_member()
        elif choice == "3":
            menu_webinar()
        elif choice == "4":
            menu_platinum()
        elif choice == "5":
            menu_keluhan()
        elif choice == "6":
            menu_laporan()
        elif choice == "7":
            show_pengaturan()
        elif choice == "0":
            print("Sampai jumpa. Semoga CRM Tower membantu tim bekerja lebih rapi.")
            break
        else:
            print("Pilihan belum sesuai, coba lagi ya.")


def seed_demo_data() -> None:
    from .services.members import MemberInput, add_member
    from .services.notes import add_note
    from .services.purchases import add_purchase
    from .services.webinar import add_webinar_record
    from .services.obstacles import add_or_update_obstacle
    from .services.tasks import add_task
    from .services.issues import add_issue
    from .database import fetchone
    from .utils.helpers import today_str

    initialize_database()

    sabrina = fetchone("SELECT id_pengguna FROM pengguna WHERE nama_pengguna='Sabrina Aulia'")["id_pengguna"]
    sumber_order = fetchone("SELECT id_sumber FROM sumber_data WHERE nama_sumber='OrderOnline'")["id_sumber"]
    sumber_cs = fetchone("SELECT id_sumber FROM sumber_data WHERE nama_sumber='Histori CS'")["id_sumber"]
    prog_webinar = fetchone("SELECT id_program FROM program WHERE nama_program='Webinar Berani Export Import'")["id_program"]
    prog_platinum = fetchone("SELECT id_program FROM program WHERE nama_program='Member Platinum'")["id_program"]

    demos = [
        {
            "nama": "Budi Santoso", "wa": "081234567890", "kota": "Jakarta", "sumber": sumber_order,
            "pic": sabrina, "status": "Masih Terkendala", "tahap": "Belajar dasar", "praktik": 0,
            "potensi": "Cukup Potensial", "ringkasan": "Sudah beli platinum tapi belum mulai praktik.",
            "langkah": "Gali hambatan dan arahkan langkah awal."
        },
        {
            "nama": "Rina Amelia", "wa": "089876543210", "kota": "Bandung", "sumber": sumber_cs,
            "pic": sabrina, "status": "Sudah Mulai Praktik", "tahap": "Mulai praktik", "praktik": 1,
            "potensi": "Sangat Potensial", "ringkasan": "Aktif bertanya dan mulai menjalankan praktik.",
            "langkah": "Diskusikan kebutuhan pendampingan lanjutan."
        },
    ]

    created = []
    for item in demos:
        try:
            member_id = add_member(MemberInput(
                nama_member=item["nama"],
                nomor_whatsapp=item["wa"],
                email="",
                kota=item["kota"],
                brand_utama="Berani Export Import",
                id_sumber=item["sumber"],
                penanggung_jawab=item["pic"],
                status_member=item["status"],
                tahap_progress=item["tahap"],
                sudah_mulai_praktik=item["praktik"],
                kategori_potensi=item["potensi"],
                tanggal_kontak_terakhir=today_str(),
                tanggal_tindak_lanjut_berikutnya=today_str(),
                ringkasan_kondisi=item["ringkasan"],
                langkah_berikutnya=item["langkah"],
            ))
            created.append(member_id)
        except Exception:
            row = fetchone("SELECT id_member FROM member WHERE nomor_whatsapp = ?", ("62" + item["wa"][1:],))
            if row:
                created.append(row["id_member"])

    if created:
        add_purchase(created[0], prog_platinum, today_str(), "ORD-001", 2500000, "Berani Export Import", "berhasil", "OrderOnline", "Pembelian member platinum")
        add_purchase(created[1], prog_webinar, today_str(), "ORD-002", 0, "Berani Export Import", "berhasil", "OrderOnline", "Webinar gratis")
        add_note(created[0], "Tindak Lanjut", "Member menyampaikan belum paham langkah awal praktik ekspor.", sabrina)
        add_note(created[1], "Hasil Webinar", "Peserta hadir penuh dan aktif bertanya.", sabrina)
        add_webinar_record(created[1], prog_webinar, today_str(), "Hadir Penuh", "Sudah Diminta", "Sangat terbantu", "Sangat Potensial", "Perlu ditindaklanjuti ke kelas premium.")
        add_or_update_obstacle(created[0], "Belum paham langkah awal", "Masih bingung memulai dari impor atau ekspor terlebih dahulu.", "Tinggi", 1, "CRM akan arahkan langkah awal yang sederhana.", "Butuh Bantuan Mentor", sabrina)
        add_task(created[0], "Cek progress member", sabrina, today_str(), "Tinggi", "Hubungi untuk diagnosis hambatan.")
        add_task(created[1], "Bahas program lanjutan", sabrina, today_str(), "Sedang", "Diskusikan kebutuhan pendampingan.")
        add_issue(created[0], "Pertanyaan", "Menanyakan urutan langkah awal ekspor dan impor.", "Sedang", sabrina)


def main() -> None:
    parser = argparse.ArgumentParser(description="CRM Tower CLI")
    parser.add_argument("--init-db", action="store_true", help="Inisialisasi database dan data referensi")
    parser.add_argument("--seed-demo", action="store_true", help="Isi data contoh/demo")
    parser.add_argument("--no-cli", action="store_true", help="Jangan masuk mode interaktif")
    parser.add_argument("--web", action="store_true", help="Jalankan versi webapp")
    parser.add_argument("--host", default="127.0.0.1", help="Host untuk webapp")
    parser.add_argument("--port", type=int, default=5000, help="Port untuk webapp")
    args = parser.parse_args()

    if args.init_db:
        initialize_database()
        print("Database dan data referensi berhasil disiapkan.")

    if args.seed_demo:
        seed_demo_data()
        print("Data demo berhasil disiapkan.")

    if args.web:
        app = create_app()
        app.run(host=args.host, port=args.port, debug=True)
        return

    if not args.no_cli:
        run_cli()


if __name__ == "__main__":
    main()
