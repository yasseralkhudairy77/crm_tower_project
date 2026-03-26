from __future__ import annotations

from ..constants import JENIS_MASALAH, PRIORITAS, STATUS_PENANGANAN
from ..services import references
from ..services.issues import add_issue, list_issues, update_issue
from ..services.members import list_members
from .menu_helpers import header, pilih_id, pilih_opsi


def lihat_keluhan(active_only: bool = False):
    header("Keluhan & Pertanyaan")
    rows = list_issues(active_only=active_only)
    if not rows:
        print("Belum ada data keluhan/pertanyaan.")
        return
    for row in rows:
        print(
            f"#{row['id_keluhan']} | {row['nama_member']} | {row['jenis_masalah']} | "
            f"{row['prioritas']} | {row['status_penanganan']} | PIC: {row['nama_pengguna']}"
        )


def tambah_keluhan():
    member_id = pilih_id(list_members(), "id_member", "nama_member", "Pilih Member")
    if not member_id:
        return
    pic_id = pilih_id(references.list_pengguna(), "id_pengguna", "nama_pengguna", "Pilih PIC")
    if not pic_id:
        return
    jenis = pilih_opsi("Jenis masalah", JENIS_MASALAH)
    detail = input("Detail masalah: ").strip()
    prioritas = pilih_opsi("Prioritas", PRIORITAS)
    add_issue(member_id, jenis, detail, prioritas, pic_id)
    print("Keluhan/pertanyaan berhasil dicatat.")


def update_keluhan():
    issue_id = input("Masukkan ID keluhan: ").strip()
    if not issue_id.isdigit():
        print("ID keluhan harus angka.")
        return
    status = pilih_opsi("Status penanganan", STATUS_PENANGANAN)
    catatan = input("Catatan penyelesaian (opsional): ").strip()
    update_issue(int(issue_id), status, catatan)
    print("Status keluhan berhasil diperbarui.")


def menu_keluhan():
    while True:
        header("Keluhan & Pertanyaan")
        print("1. Lihat semua keluhan")
        print("2. Lihat keluhan yang belum selesai")
        print("3. Tambah keluhan/pertanyaan")
        print("4. Update penanganan keluhan")
        print("0. Kembali")
        choice = input("Pilih menu: ").strip()
        if choice == "1":
            lihat_keluhan(False)
        elif choice == "2":
            lihat_keluhan(True)
        elif choice == "3":
            tambah_keluhan()
        elif choice == "4":
            update_keluhan()
        elif choice == "0":
            break
        else:
            print("Pilihan belum sesuai, coba lagi ya.")