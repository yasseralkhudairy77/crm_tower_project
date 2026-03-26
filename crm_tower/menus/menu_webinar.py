from __future__ import annotations

from ..constants import STATUS_KEHADIRAN_WEBINAR, STATUS_TESTIMONI
from ..services import references
from ..services.members import list_members
from ..services.webinar import add_webinar_record, list_webinar_records
from .menu_helpers import header, input_tanggal, pilih_id, pilih_opsi


def tambah_riwayat_webinar():
    member_id = pilih_id(list_members(), "id_member", "nama_member", "Pilih Member")
    if not member_id:
        return
    program_id = pilih_id(references.list_program(), "id_program", "nama_program", "Pilih Webinar/Program")
    if not program_id:
        return
    tanggal = input_tanggal("Tanggal webinar (YYYY-MM-DD): ")
    kehadiran = pilih_opsi("Status kehadiran", STATUS_KEHADIRAN_WEBINAR)
    testimoni = pilih_opsi("Status testimoni", STATUS_TESTIMONI)
    kesan = input("Kesan peserta (opsional): ").strip()
    potensi = input("Potensi lanjutan (opsional): ").strip()
    catatan = input("Catatan webinar (opsional): ").strip()
    add_webinar_record(member_id, program_id, tanggal, kehadiran, testimoni, kesan, potensi, catatan)
    print("Riwayat webinar berhasil disimpan.")


def tampilkan_webinar():
    header("Pantauan Setelah Webinar")
    rows = list_webinar_records()
    if not rows:
        print("Belum ada data webinar.")
        return
    for row in rows:
        print(
            f"#{row['id_webinar_riwayat']} | {row['nama_member']} | {row['nama_program']} | "
            f"{row['tanggal_webinar']} | {row['status_kehadiran']} | Testimoni: {row['status_testimoni']}"
        )


def menu_webinar():
    while True:
        header("Pantauan Setelah Webinar")
        print("1. Lihat riwayat webinar")
        print("2. Tambah riwayat webinar")
        print("0. Kembali")
        choice = input("Pilih menu: ").strip()
        if choice == "1":
            tampilkan_webinar()
        elif choice == "2":
            tambah_riwayat_webinar()
        elif choice == "0":
            break
        else:
            print("Pilihan belum sesuai, coba lagi ya.")