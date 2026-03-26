from __future__ import annotations

from ..constants import KATEGORI_POTENSI, STATUS_PELUANG
from ..services import references
from ..services.members import list_members
from ..services.opportunities import add_opportunity, list_opportunities, update_opportunity_status
from .menu_helpers import header, pilih_id, pilih_opsi


def lihat_peluang():
    header("Peluang Program Lanjutan")
    rows = list_opportunities()
    if not rows:
        print("Belum ada peluang program lanjutan.")
        return
    for row in rows:
        print(
            f"#{row['id_peluang']} | {row['nama_member']} | {row['tingkat_potensi']} | "
            f"{row['status_penawaran']} | PIC: {row['nama_pengguna']}"
        )


def tambah_peluang():
    member_id = pilih_id(list_members(), "id_member", "nama_member", "Pilih Member")
    if not member_id:
        return
    pic_id = pilih_id(references.list_pengguna(), "id_pengguna", "nama_pengguna", "Pilih PIC")
    if not pic_id:
        return
    tingkat = pilih_opsi("Tingkat potensi", KATEGORI_POTENSI)
    alasan = input("Alasan member dinilai potensial: ").strip()
    masalah = input("Masalah utama member (opsional): ").strip()
    target = input("Target member (opsional): ").strip()
    solusi = input("Solusi yang cocok (opsional): ").strip()
    status = pilih_opsi("Status penawaran", STATUS_PELUANG)
    add_opportunity(member_id, tingkat, alasan, masalah, target, solusi, status, pic_id)
    print("Peluang program lanjutan berhasil dicatat.")


def ubah_status_peluang():
    peluang_id = input("Masukkan ID peluang: ").strip()
    if not peluang_id.isdigit():
        print("ID peluang harus angka.")
        return
    status = pilih_opsi("Status penawaran baru", STATUS_PELUANG)
    alasan = ""
    if status == "Tidak Jadi":
        alasan = input("Alasan tidak lanjut: ").strip()
    update_opportunity_status(int(peluang_id), status, alasan)
    print("Status peluang berhasil diperbarui.")


def menu_peluang():
    while True:
        header("Peluang Program Lanjutan")
        print("1. Lihat peluang")
        print("2. Tambah peluang baru")
        print("3. Ubah status peluang")
        print("0. Kembali")
        choice = input("Pilih menu: ").strip()
        if choice == "1":
            lihat_peluang()
        elif choice == "2":
            tambah_peluang()
        elif choice == "3":
            ubah_status_peluang()
        elif choice == "0":
            break
        else:
            print("Pilihan belum sesuai, coba lagi ya.")